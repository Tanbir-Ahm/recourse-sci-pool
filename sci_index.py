"""Passage index builder: turns crawled Supreme Court judgments into clean, tagged, embedded passages, saved block by block.

For each block of 250 IDs from the crawl (branch claude/sci-pool, read-only), it
  cleans the text, splits it into real paragraphs (or sentence groups with a page number), tags each passage
  (facts / argument / reasoning / order / statute_text / header), skips duplicates, civil cases and junk,
  embeds the rest slowly with Voyage voyage-law-2, and saves three files per block on branch claude/sci-index.
The saved files ARE the ledger: a block is done exactly when its files are committed. Safe to stop and re-run at any time.
It never spends past a token ceiling, and stops cleanly (keeping everything saved) if the service refuses.
"""
import argparse
import collections
import csv
import glob
import gzip
import hashlib
import heapq
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from bisect import bisect_right
from datetime import date, datetime, timezone

import numpy as np

import chunk_judgments as cj

PREP_VERSION = "p2"                   # p2: non-breaking spaces and running page headers removed, very short numbered paragraphs joined (p1 blocks lack both)
BLOCK_SIZE = 250
DEFAULT_CEILING = 40_000_000          # new tokens this job may spend; 44.15M of the free allowance was left on 2026-10-01 and the live site shares it, so ~4M stays in reserve
CHARS_PER_TOKEN = 3.87                # measured against the real service
TOKEN_CALIBRATION = 1.062             # measured on a real cloud block (2026-10-01, 044750-044999): estimate 398,003 vs real 429,448 at 0.984
MODEL = "voyage-law-2"
LEGACY_MODEL = "voyage-law-2"         # blocks saved before an index had a MODEL marker file were all made with this one
MAX_BATCH_TOKENS = 60_000             # the service refuses a batch over 120,000 real tokens; one batch ran 27%+ over its estimate (127,389 real vs at most 100,000 estimated, 2026-10-02), so keep 2x headroom
MIN_DOC_CHARS = 1500
DENSITY_THRESHOLD = 10.0              # criminal-law wording per 10,000 characters

_POOL_RE = re.compile(r"^(\d{6})-(\d{6})\.ok(\d+)\.gap(\d+)\.err(\d+)\.jsonl\.gz$")
_IDX_RE = re.compile(r"^(\d{6,12})-(\d{6,12})\.docs(\d+)\.pass(\d+)\.tok(\d+)\.meta\.jsonl\.gz$")      # 6 digits for crawl blocks, 10 for bucket blocks (BUCKET_BASE and up)


# ================================================================ cleaning
HDR_LINE = re.compile(r"(?im)^[ \t]*(?:http://JUDIS\.NIC\.IN|SUPREME COURT OF INDIA|Page \d+(?: of \d+)?|JUDGMENT|REPORTABLE|NON-REPORTABLE|\d{1,3})[ \t]*$")
HDR_INLINE = re.compile(r"(?:http://JUDIS\.NIC\.IN\s+)?(?:SUPREME COURT OF INDIA\s+)?Page \d+ of \d+|\bPage \d+\s+JUDGMENT\b|http://JUDIS\.NIC\.IN")
ESC = {"021": "'", "022": "'", "023": '"', "024": '"', "025": "'", "026": "-", "027": "-"}


ODD_SPACES = re.compile(r"[\u00a0\u2002\u2003\u2007\u2009\u202f]")   # the PDFs use non-breaking spaces, which hid 99% of the "Page 4" markers from the patterns above


def clean_page(p):
    p = p.replace("\ufffd", "'")
    p = ODD_SPACES.sub(" ", p).replace("\u200b", "")
    p = HDR_INLINE.sub(" ", p)
    p = HDR_LINE.sub("", p)
    return re.sub(r"\n{3,}", "\n\n", p)


def strip_running_headers(pages):
    """A line that sits at the top or bottom of many pages is a running header or footer (for example
    'Criminal Appeal No.714 of 2015 @ SLP (Crl.) No.431 of 2015'); it is not part of the judgment, so drop it."""
    if len(pages) < 4:
        return pages
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    count = collections.Counter()
    for pg in pages:
        lines = [norm(x) for x in pg.split("\n") if x.strip()]
        for x in set(lines[:3] + lines[-3:]):
            if 3 <= len(x) <= 150:
                count[x] += 1
    need = max(3, int(0.3 * len(pages)))
    drop = {x for x, c in count.items() if c >= need}
    if not drop:
        return pages
    return ["\n".join(x for x in pg.split("\n") if norm(x) not in drop) for pg in pages]


def fix_text(t):
    return re.sub(r"\\(0\d\d)", lambda m: ESC.get(m.group(1), " "), t)


def unwrap(t):
    t = re.sub(r"(?<=\w)-\n(?=[a-z])", "", t)
    t = re.sub(r"\s*\n\s*", " ", t)
    return re.sub(r"[ \t]{2,}", " ", t).strip()


OLD_HDR = re.compile(r"^\W*(?:CASE NO\.?:?\s*(?P<caseno>.*?)\s+)?PETITIONER:\s*(?P<pet>.*?)\s+RESPONDENT:\s*(?P<resp>.*?)\s+DATE OF JUDGMENT:?\s*(?P<date>\S+)\s+BENCH:\s*(?P<bench>.*?)\s+(?:JUDGMENT:|CITATION:).*?(?:delivered by\s+(?P<author>[^,]{1,60}?)\s*,\s*J\.?|J\s?U\s?D\s?G\s?M\s?E\s?N\s?T)", re.S)


def split_old_header(first_page):
    """Old-style judgments open with a CASE NO / PETITIONER / RESPONDENT block: keep it as data, not as a passage."""
    m = OLD_HDR.match(first_page.strip())
    if m and m.end() < 1500:
        meta = {k: re.sub(r"\s+", " ", v).strip() for k, v in m.groupdict().items() if v}
        return meta, first_page.strip()[m.end():].strip()
    return None, first_page


SENT = re.compile(r"(?<=[.?!;])\s+(?=[A-Z\"\u201c(\d])")


def windows(text, target=1300, cap=2600):
    """Sentence-aligned windows with one sentence of overlap; never cuts mid-sentence unless one sentence is huge."""
    sents = SENT.split(text)
    out, cur, curlen = [], [], 0
    for s in sents:
        while len(s) > cap:
            if cur:
                out.append(" ".join(cur))
                cur, curlen = [], 0
            out.append(s[:cap])
            s = s[cap:]
        if curlen + len(s) > cap and cur:
            out.append(" ".join(cur))
            cur = [cur[-1]] if len(cur[-1]) < 400 else []
            curlen = sum(map(len, cur))
        cur.append(s)
        curlen += len(s)
        if curlen >= target:
            out.append(" ".join(cur))
            cur = [s] if len(s) < 400 else []
            curlen = sum(map(len, cur))
    if cur:
        tail = " ".join(cur)
        if not out or tail not in out[-1]:
            out.append(tail)
    return [o for o in out if len(o.strip()) >= 40]


# ================================================================ structure tags
def _R(p):
    return re.compile(p, re.I)


ARG = _R(r"\b(?:learned|Mr\.|Shri|Ms\.|Dr\.|Smt\.)[^.]{0,70}?\b(?:submit|contend|argu|urge|plead|relied|relies)\w*|\b(?:it|he|she|they)\s+(?:was|is|has been|have been)?\s*(?:further |also |then |strenuously |vehemently )?(?:submitted|contended|argued|urged)\b|\b(?:submits?|contends?|urges?|argues?)\s+that\b|\bthe contention (?:of|that|raised|put forward|advanced)|\b(?:contended|submitted|urged|argued) that\b|\bcounsel (?:for|appearing|submitted)\b|\bhas been (?:contended|urged|argued)\b|\bpressed (?:into service|upon)\b|\b(?:appellant|respondent|petitioner)s?[^.]{0,40}\b(?:contends?|submits?|urges?)\b")
HOLD = _R(r"\bwe (?:are of the (?:considered |firm )?(?:view|opinion)|hold|find|are unable|agree|do not agree|are satisfied|have no hesitation|are not (?:inclined|persuaded)|think|answer)|\bin our (?:considered |humble )?(?:view|opinion|judgment)|\bit is (?:well|now|also|a |trite|clear)[ -]*(?:settled|established|trite)|\bthe law is (?:well )?settled|\bthe test is\b|\bthe question (?:that |which )?(?:arises|falls|is whether)|\bwe must (?:hold|note|bear)|\bthe principle(?:s)? (?:is|are|laid)\b|\bthus,? we\b|\btherefore,? we\b|\baccordingly,? we\b|\bwe are, therefore\b")
OPER = _R(r"\bappeals? (?:is|are|stands?|shall be|must be|deserves? to be)? ?(?:hereby )?(?:allowed|dismissed|disposed)|\bin the result\b|\bordered accordingly\b|\bno order as to costs\b|\bstand(?:s)? (?:allowed|dismissed|disposed)\b|\bpending applications?\b|\bwe (?:direct|order) that\b")
FACT = _R(r"\bthe (?:prosecution|complainant)(?:'s)? case\b|\bbrief facts\b|\bfacts (?:of the case|giving rise|leading)\b|\bfacts are (?:as under|briefly|that)\b|\bwas registered\b|\bfirst information report\b|\bFIR\b|\bleave granted\b|\bthis appeal (?:is|has been) (?:directed|filed|preferred)|\bchallenge(?:d)? (?:in this appeal|the (?:judgment|order))|\bhaving (?:been )?(?:heard|perused)|\bheard the learned\b")
PREC = _R(r"\b(?:SCC|AIR|SCR|SCALE|Cri\.? ?L\.? ?J|JT|ALL ?ER)\b|\b(?:v\.|vs\.?|versus)\s+[A-Z]|\bthis court (?:in|has|had|held|observed)\b|\bit was (?:held|observed)\b|\bthe court (?:held|observed)\b")
HDR_A = re.compile(r"^\W*(?:Page \d+\s+)?(?:IN THE SUPREME COURT OF INDIA|CASE NO\.?:)", re.I)
HDR_B = re.compile(r"PETITIONER:.{0,300}RESPONDENT:.{0,300}(?:DATE OF JUDGMENT|BENCH)", re.S)
STAT_INTRO = _R(r"\b(?:reads?|read|runs|extracted|set out|provides?|provided|is as follows|are as follows|relevant (?:part|portion|provisions?))\b[^.]{0,60}\b(?:under|follows|thus|hereunder|below|as under)\b")
STAT_IDIOM = _R(r"\b(?:shall be punish|whoever|shall mean|notwithstanding anything|shall not be|imprisonment which may extend|liable to fine|shall be deemed)\b")
STAT_START = re.compile(r"^\s*\d{0,3}\.?\s*[\"\u201c]?(?:Section\s+)?\d{1,3}[A-Z]?\.\s*[\u2014\-\u2013]?\s*[A-Z]")
HOLD_HINT = _R(r"\bwe (?:hold|find|are of|think|are satisfied|agree)\b|\bin our (?:view|opinion)\b|\bit is (?:well )?settled\b")


def _is_header(text, pos):
    head = text[:700]
    return pos <= 0.06 and (bool(HDR_A.match(head)) or bool(HDR_B.search(head)))


def _is_statute_text(text):
    if HOLD_HINT.search(text):
        return False
    idioms = len(STAT_IDIOM.findall(text))
    return idioms >= 1 and (bool(STAT_INTRO.search(text[:400])) or bool(STAT_START.match(text)) or idioms >= 3)


def tag_doc(passages):
    """Judgments usually run: header -> facts -> arguments -> the court's own analysis -> order.
    Wording gives the evidence; 'argument' needs clear lawyer-reporting wording; with no wording evidence early
    passages are facts and later ones the court's own analysis. Tags are soft signals, never filters."""
    n = len(passages)
    seen_hold = False
    for i, p in enumerate(passages):
        t = p["text"]
        pos = i / max(n - 1, 1)
        p["pos"] = round(pos, 3)
        a, h, o, f = len(ARG.findall(t)), len(HOLD.findall(t)), len(OPER.findall(t)), len(FACT.findall(t))
        p["prec"] = int(len(PREC.findall(t)) >= 2)
        if p["pn"] == "preamble":
            p["section"], p["basis"] = "header", "position"
            continue
        if o and pos > 0.6 and o >= h:
            lab, basis = "order", "cue"
        elif a >= 1 and a > h and not (p["prec"] and a == 1):
            lab, basis = "argument", "cue"
        elif h >= 1:
            lab, basis = "reasoning", "cue"
        elif f >= 1 and not seen_hold:
            lab, basis = "facts", "cue"
        elif pos <= 0.25 and not seen_hold:
            lab, basis = "facts", "position"
        else:
            lab, basis = "reasoning", "default"
        if lab == "reasoning" and basis == "cue":
            seen_hold = True
        p["section"], p["basis"] = lab, basis
    for p in passages:
        t = p["text"]
        if p["section"] != "header" and _is_header(t, p["pos"]):
            p["section"] = "header"
        elif p["section"] in ("reasoning", "facts", "argument") and _is_statute_text(t):
            p["section"] = "statute_text"
        words = len(t.split())
        alpha = sum(ch.isalpha() for ch in t) / max(len(t), 1)
        p["noise"] = int(words < 12 or alpha < 0.62 or len(re.findall(r"\b(?:SLP|CC|No|Nos)\b", t)) >= 6)
    return passages


MERGE_BELOW = 200                     # chars: a numbered paragraph shorter than this is joined with the one after it (a very short passage is almost unfindable by meaning)


def merge_short(passages, below=MERGE_BELOW, cap=2600):
    """Joins runs of very short numbered paragraphs (a list of conclusions, a one-line order) into one passage, so each has
    enough text to be found by meaning. The joined passage keeps the first page and is numbered like '1-3'."""
    out, buf, first = [], None, None
    for p in passages:
        if (buf is not None and below and len(buf["text"]) < below and buf["method"] == "para" and p["method"] == "para"
                and not str(buf["pn"]).startswith("preamble") and not str(p["pn"]).startswith("preamble")
                and len(buf["text"]) + 1 + len(p["text"]) <= cap):
            buf["text"] += " " + p["text"]
            buf["pn"] = f"{first}-{p['pn']}"
        else:
            if buf is not None:
                out.append(buf)
            buf, first = dict(p), p["pn"]
    if buf is not None:
        out.append(buf)
    return out


def make_passages(text, merge_below=MERGE_BELOW):
    """One judgment -> (passages, old-header data). Passages carry text, paragraph number (or None), page, method, tags."""
    pages = strip_running_headers([clean_page(x) for x in text.split("\f")])
    meta = None
    if pages:
        meta, pages[0] = split_old_header(pages[0])
    starts, doc, off = [], [], 0
    for pg in pages:
        starts.append(off)
        doc.append(pg)
        off += len(pg) + 1
    full = "\n".join(doc)
    chs = cj.chunk_judgment({"case_name": "x", "citation": "", "source_url": "", "source_type": "x", "text": full})
    out, search = [], 0
    if chs and all(c["chunk_method"] == "paragraph_number" for c in chs):
        for c in chs:
            k = full.find(c["text"][:80], search)
            if k >= 0:
                search = k
            page = bisect_right(starts, max(k, 0))
            body = fix_text(unwrap(c["text"]))
            pieces = windows(body) if len(body) > 3000 else [body]
            for j, pc in enumerate(pieces):
                if len(pc) >= 40:
                    out.append({"pn": c["paragraph_number"] + (f"/{j + 1}" if len(pieces) > 1 else ""), "page": page, "method": "para", "text": pc})
    else:
        flat, fstarts, o = [], [], 0
        for pg in doc:
            u = fix_text(unwrap(pg))
            fstarts.append(o)
            flat.append(u)
            o += len(u) + 1
        ftxt = " ".join(flat)
        search = 0
        for w in windows(ftxt):
            idx = ftxt.find(w[:60], search)
            if idx >= 0:
                search = max(search, idx)
            page = bisect_right(fstarts, max(idx, 0))
            out.append({"pn": None, "page": page, "method": "sentences", "text": w})
    return tag_doc(merge_short(out, merge_below)), meta


# ================================================================ the bucket (law-report text, 2017 on, plus older judgments the crawl lacks)
# A bucket shard (branch claude/sci-bucket) is read like a crawl block, with these differences. Its judgments get ids of their own, so they can never collide with a crawl id:
# a block's start is BUCKET_BASE + ordinal * BLOCK_SIZE and a judgment's id is its block's start plus its position in the shard file (the shard is immutable once committed,
# so the id is stable). The shard's own text is the law report's: it opens with the editors' headnote and has margin letters A to H, which are cut (the same rules as
# sci_bucket.clean_text, kept here so an index session needs nothing but this file). Judgments the crawl already holds are skipped (see load_skip_paths).
BUCKET_BASE = 1_000_000_000
REFRESH_EPOCH = date(2026, 1, 1)
_BUCKET_RE = re.compile(r"^([a-z0-9_]+)-(\d{4})\.ok(\d+)\.miss(\d+)\.err(\d+)\.jsonl\.gz$")
_BUCKET_HEADERS = (re.compile(r"^[A-H]$"), re.compile(r"^\d{1,4}$"), re.compile(r"(?i)^SUPREME COURT REPORTS$"),
                   re.compile(r"^\[\d{4}\]\s*\d+\s*S\.?C\.?R\.?(?:\s*\d+)?(?:\s*:\s*\d{4}\s+INSC\s+\d+)?$"))
DEFAULT_SKIP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coverage", "bucket_match", "none_resolution.csv.gz")


def bucket_ordinal(scope, n):
    """Where a shard sits in the id space. Newest first when blocks are taken in descending order: refreshes, then `after` (judgments after 4 May 2017), then `none` (older ones
    the name match did not find in the crawl). A refresh scope is `refresh_YYYYMMDD` and may have up to 50 blocks."""
    if scope == "none":
        return n
    if scope == "after":
        return 1000 + n
    m = re.match(r"^refresh_(\d{4})(\d{2})(\d{2})$", scope)
    if m:
        days = (date(int(m[1]), int(m[2]), int(m[3])) - REFRESH_EPOCH).days
        if days < 0 or n >= 50:
            raise ValueError(f"bucket scope {scope!r} block {n} is outside the id space (a refresh must be dated {REFRESH_EPOCH} or later and have fewer than 50 blocks)")
        return 2000 + days * 50 + n
    raise ValueError(f"unknown bucket scope {scope!r} (expected after, none or refresh_YYYYMMDD)")


def bucket_blocks(bucket_dir):
    """{block start: {end, ok, gap, err, path, kind, scope, start}} for every bucket shard that holds at least one saved judgment."""
    out = {}
    for path in glob.glob(os.path.join(bucket_dir, "shards", "*.jsonl.gz")):
        m = _BUCKET_RE.match(os.path.basename(path))
        if not m:
            continue
        scope, n, ok, miss, err = m[1], int(m[2]), int(m[3]), int(m[4]), int(m[5])
        start = BUCKET_BASE + bucket_ordinal(scope, n) * BLOCK_SIZE
        out[start] = {"start": start, "end": start + BLOCK_SIZE - 1, "ok": ok, "gap": miss, "err": err, "path": path, "kind": "bucket", "scope": scope}
    return out


def load_skip_paths(path=None):
    """Bucket paths the crawl already holds (none_resolution.csv.gz, column in_crawl == 'yes'); embedding them again would pay twice for the same judgment. Refuses if the file
    is missing: a bucket run without it would silently re-embed about 3,000 judgments."""
    path = path or DEFAULT_SKIP_FILE
    if not os.path.exists(path):
        raise ValueError(f"the skip file {path} is missing (it lists the bucket judgments the crawl already holds); pass --skip-file")
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", newline="") as fh:
        return {r["path"] for r in csv.DictReader(fh) if (r.get("in_crawl") or "").strip().lower() == "yes"}


def bucket_pages(rec):
    """(text with pages joined by form feeds and the law report's headnote, margin letters and running headers cut, number of pages before the cut)."""
    text = rec.get("text") or ""
    start = rec.get("body_start") or 0
    offset = text.count("\f", 0, start)
    pages = []
    for pg in text[start:].split("\f"):
        lines = [ln.strip() for ln in pg.split("\n")]
        pages.append("\n".join(ln for ln in lines if ln and not any(rx.match(ln) for rx in _BUCKET_HEADERS)))
    return "\f".join(pages), offset


def read_block(info, skip_paths=frozenset()):
    """The records of one block in the shape prepare_block reads: {id, status, text, pages, ...}. A crawl block is read as it is. A bucket block gets its ids from its position,
    the cleaned text, the raw text (to decide criminal or not, and for the header a duplicate check compares) and, for each judgment, where it came from."""
    recs = _read_pool_block(info["path"])
    if info.get("kind") == "extra":
        if len(recs) > BLOCK_SIZE:
            raise ValueError(f"{info['path']} holds {len(recs)} records; a block has at most {BLOCK_SIZE}")
        return [{"id": info["start"] + i, "status": "ok", "text": r["text"], "pages": r.get("pages"), "raw_text": r["text"], "in_crawl": False,
                 "src": {"source": r.get("source_kind") or info["scope"], "scope": info["scope"], "path": r.get("path"), "title": r.get("title"), "date": r.get("decision_date"),
                         "citation": r.get("citation"), "case_id": r.get("case_id"), "url": r.get("url"), "court": r.get("court")}}
                for i, r in enumerate(recs) if r.get("status") == "ok" and r.get("text")]
    if info.get("kind") != "bucket":
        return recs
    if len(recs) > BLOCK_SIZE:
        raise ValueError(f"{info['path']} holds {len(recs)} records; a block has at most {BLOCK_SIZE}")
    out = []
    for i, r in enumerate(recs):
        if r.get("status") != "ok" or not r.get("text"):
            continue
        text, offset = bucket_pages(r)
        out.append({"id": info["start"] + i, "status": "ok", "text": text, "pages": r.get("pages"), "raw_text": r["text"], "page_offset": offset,
                    "in_crawl": r.get("path") in skip_paths,
                    "src": {"source": "bucket", "scope": info["scope"], "path": r.get("path"), "title": r.get("title"), "date": r.get("decision_date"),
                            "citation": r.get("citation"), "case_id": r.get("case_id"), "headnote_cut": bool(r.get("body_start"))}})
    return out


# ---------------------------------------------------------------- extra sources (owner's decision 2026-10-22: add to this index)
# Judgments the crawl and the open bucket do not hold: the Supreme Court's newer archive (5 May 2017 on) and the Gauhati High Court. A source keeps its prepared records in
# `index_blocks/<scope>-<NNNN>.ok<n>.miss0.err0.jsonl.gz` on its own data branch (immutable once written, at most BLOCK_SIZE records per file, like a bucket shard), attached read-only
# as an `--extra-dir`. A block's start is EXTRA_BASE + ordinal * BLOCK_SIZE and a judgment's id is its block's start plus its position in the file. No headnote or margin-letter
# cutting (these are court PDFs, not law reports). Ids at EXTRA_BASE and up never clash with crawl or bucket ids.
EXTRA_BASE = 2_000_000_000
_EXTRA_RE = re.compile(r"^(sci_newer|ghc_court|ghc_bucket)-(\d{4})\.ok(\d+)\.miss(\d+)\.err(\d+)\.jsonl\.gz$")
_EXTRA_OFFSET = {"ghc_court": 0, "sci_newer": 1000, "ghc_bucket": 2000}


def extra_blocks(extra_dir):
    """{block start: {end, ok, gap, err, path, kind, scope, start}} for every prepared-records file under <extra_dir>/index_blocks that holds at least one judgment."""
    out = {}
    for path in glob.glob(os.path.join(extra_dir, "index_blocks", "*.jsonl.gz")):
        m = _EXTRA_RE.match(os.path.basename(path))
        if not m:
            continue
        scope, n, ok, miss, err = m[1], int(m[2]), int(m[3]), int(m[4]), int(m[5])
        if n >= 1000:
            raise ValueError(f"{path}: block number {n} is outside the id space of its scope (at most 1,000 blocks)")
        start = EXTRA_BASE + (_EXTRA_OFFSET[scope] + n) * BLOCK_SIZE
        out[start] = {"start": start, "end": start + BLOCK_SIZE - 1, "ok": ok, "gap": miss, "err": err, "path": path, "kind": "extra", "scope": scope}
    return out


def all_blocks(pool_dir=None, bucket_dir=None, extra_dirs=None):
    blocks = pool_blocks(pool_dir) if pool_dir else {}
    if bucket_dir:
        blocks.update(bucket_blocks(bucket_dir))
    for d in extra_dirs or ():
        blocks.update(extra_blocks(d))
    return blocks


# ================================================================ which judgments to keep
CRH = re.compile(r"CRIMINAL\s+(?:APPELLATE|ORIGINAL|REVISION)|Appeal\s*\(\s*crl|\(\s*Crl\.?\s*\)|Crl\.?\s*A\.?\s*No|Criminal\s+Appeal|SLP\s*\(\s*Crl|Writ Petition\s*\(\s*Crl|Crl\.M\.P|CRIMINAL\s+MISC", re.I)
CUE = re.compile(r"\b(?:accused|prosecution|I\.?P\.?C|Cr\.?\s?P\.?\s?C|N\.?D\.?P\.?S|Negotiable Instruments|F\.?I\.?R|offences?|bail|cognizable|conviction|acquittal|complainant)\b", re.I)


def is_criminal(text):
    """Criminal-law judgment? Yes if the opening block says so, or the wording is dense with criminal-law terms."""
    flat = text.replace("\f", " ")
    density = len(CUE.findall(flat)) / max(len(flat), 1) * 10000
    return bool(CRH.search(flat[:1500])) or density >= DENSITY_THRESHOLD, round(density, 1)


def doc_hash(text):
    return hashlib.sha1(re.sub(r"\s+", " ", text.replace("\f", " ")).strip().encode("utf-8", "replace")).hexdigest()


def prepare_block(records, seen):
    """Records of one crawl block -> docs (kept or skipped, with the reason) and the passages to embed. `seen` maps
    content hash -> first doc id and is updated in place (so identical copies are never paid for twice)."""
    docs, passages = [], []
    skipped = {"not_criminal": 0, "duplicate": 0, "short": 0, "in_crawl": 0}
    for r in records:
        if r.get("status") != "ok" or not r.get("text"):
            continue
        id_, text = r["id"], r["text"]
        h = doc_hash(text)
        row = {"doc": id_, "hash": h, "pages": r.get("pages"), "v": PREP_VERSION}
        if r.get("src"):
            row["src"] = r["src"]                  # a bucket judgment: where it came from (path, title, date, citation)
        if r.get("in_crawl"):
            row.update(skip="in_crawl")            # the crawl already holds this judgment; it is not embedded again and its hash is not recorded
        elif h in seen:
            row.update(skip="duplicate", of=seen[h])
        else:
            seen[h] = id_
            crim, dens = is_criminal(r.get("raw_text") or text)       # a law report's headnote names the statutes, so the criminal test reads the raw text
            row["density"] = dens
            if len(text) < MIN_DOC_CHARS:
                row["skip"] = "short"
            elif not crim:
                row["skip"] = "not_criminal"
        if "skip" in row:
            skipped[row["skip"]] += 1
            docs.append(row)
            continue
        ps, meta = make_passages(text)
        if meta:
            row["case"] = meta
        for p in ps:
            p["page"] += r.get("page_offset", 0)       # pages cut with the headnote still count towards the page number
        keep = [p for p in ps if not p["noise"]]
        row["passages"], row["noise"] = len(keep), len(ps) - len(keep)
        docs.append(row)
        for i, p in enumerate(keep):
            passages.append({"doc": id_, "i": i, "pn": p["pn"], "page": p["page"], "method": p["method"], "section": p["section"],
                             "basis": p["basis"], "pos": p["pos"], "prec": p["prec"], "h": hashlib.sha1(p["text"].encode("utf-8", "replace")).hexdigest()[:16],
                             "text": p["text"]})
    est = sum(len(p["text"]) for p in passages) / CHARS_PER_TOKEN * TOKEN_CALIBRATION
    return {"docs": docs, "passages": passages,
            "stats": {"docs_kept": sum(1 for d in docs if "skip" not in d), "skipped": skipped, "passages": len(passages), "est_tokens": int(est)}}


# ================================================================ embedding
class EmbedStop(Exception):
    def __init__(self, reason, used=0):
        super().__init__(reason)
        self.reason, self.used = reason, used


_FATAL = {"AuthenticationError", "InvalidRequestError", "MalformedRequestError"}
_ALLOWANCE = re.compile(r"payment|billing|credit|quota|free token|free tier|allowance", re.I)


def batch_texts(texts, max_tokens=MAX_BATCH_TOKENS, max_items=500):
    batches, cur, curtok = [], [], 0.0
    for i, t in enumerate(texts):
        e = len(t) / CHARS_PER_TOKEN
        if cur and (curtok + e > max_tokens or len(cur) >= max_items):
            batches.append(cur)
            cur, curtok = [], 0.0
        cur.append(i)
        curtok += e
    if cur:
        batches.append(cur)
    return batches


def _embed_once(client, texts, sleep, model):
    for attempt in range(5):
        try:
            return client.embed(texts, model=model, input_type="document")
        except Exception as e:
            name, msg = type(e).__name__, str(e)[:300]
            if name in _FATAL:
                raise EmbedStop(f"service refused the request (retrying will not help): {name}: {msg}")
            if _ALLOWANCE.search(msg):
                raise EmbedStop(f"the service says the allowance is used up or payment is needed: {msg}")
            if attempt == 4:
                raise EmbedStop(f"5 failed attempts in a row ({name}: {msg})")
            sleep(65 if name == "RateLimitError" else 10 * (attempt + 1))
    raise EmbedStop("5 failed attempts in a row")


def embed_texts(client, texts, *, sleep=time.sleep, pause=2.0, max_tokens=MAX_BATCH_TOKENS, max_items=500, budget_tokens=None, model=MODEL):
    """Embeds in small batches with a pause between them. Returns (float16 vectors in order, tokens the service charged).
    Raises EmbedStop (carrying the tokens already spent) on refusal, repeated failure, or if a batch would pass the budget."""
    vectors, used = [None] * len(texts), 0
    for b in batch_texts(texts, max_tokens, max_items):
        est = sum(len(texts[i]) for i in b) / CHARS_PER_TOKEN * TOKEN_CALIBRATION
        if budget_tokens is not None and used + est > budget_tokens:
            raise EmbedStop(f"token ceiling reached (the next batch would pass the {budget_tokens:,}-token limit for this block)", used)
        try:
            resp = _embed_once(client, [texts[i] for i in b], sleep, model)
        except EmbedStop as e:
            e.used = used
            raise
        for i, v in zip(b, resp.embeddings):
            vectors[i] = v
        used += resp.total_tokens
        sleep(pause)
    arr = np.asarray(vectors, dtype=np.float16) if vectors else np.zeros((0, 0), dtype=np.float16)
    return arr, used


# ================================================================ ledger (the saved files)
def _idx_dir(index_dir):
    return os.path.join(index_dir, "index")


def write_block_files(index_dir, start, block_size, docs, passages, vectors, tokens):
    d = _idx_dir(index_dir)
    os.makedirs(d, exist_ok=True)
    base = f"{start:06d}-{start + block_size - 1:06d}.docs{len(docs)}.pass{len(passages)}.tok{tokens}"
    pairs = [(".docs.jsonl.gz", docs), (".meta.jsonl.gz", passages)]
    for suffix, rows in pairs:
        tmp = os.path.join(d, ".tmp-" + base + suffix)
        with gzip.open(tmp, "wt", encoding="utf-8", errors="replace") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, os.path.join(d, base + suffix))
    if len(passages):
        tmp = os.path.join(d, ".tmp-" + base + ".vec.npy")
        with open(tmp, "wb") as fh:
            np.save(fh, np.asarray(vectors, dtype=np.float16))
        os.replace(tmp, os.path.join(d, base + ".vec.npy"))
    return base


def ledger(index_dir):
    """{block start: {docs, passages, tokens, base}} for blocks whose three files are present and consistent."""
    found = {}
    d = _idx_dir(index_dir)
    for path in glob.glob(os.path.join(d, "*.meta.jsonl.gz")):
        m = _IDX_RE.match(os.path.basename(path))
        if not m:
            continue
        start, end, docs, passes, tok = (int(x) for x in m.groups())
        base = os.path.basename(path)[: -len(".meta.jsonl.gz")]
        if not os.path.exists(os.path.join(d, base + ".docs.jsonl.gz")):
            continue
        if passes:
            vp = os.path.join(d, base + ".vec.npy")
            if not os.path.exists(vp):
                continue
            try:
                if np.load(vp, mmap_mode="r").shape[0] != passes:
                    continue
            except Exception:
                continue
        found[start] = {"docs": docs, "passages": passes, "tokens": tok, "base": base, "end": end}
    return found


def _model_marker(index_dir):
    return os.path.join(_idx_dir(index_dir), "MODEL")


def check_model(index_dir, model):
    """One index holds vectors from ONE model; vectors from different models cannot be compared, so mixing them would silently
    break search. Returns a refusal text, or None if `model` may be used with this index."""
    if os.path.exists(_model_marker(index_dir)):
        with open(_model_marker(index_dir), encoding="utf-8") as fh:
            have = fh.read().strip()
    elif ledger(index_dir):
        have = LEGACY_MODEL
    else:
        return None
    return None if have == model else f"this index holds {have} vectors; refusing to add or search with {model} (use a separate index folder)"


def _claim_model(index_dir, model):
    """The first block of a new, empty index records which model made its vectors. True if the marker was just written."""
    if os.path.exists(_model_marker(index_dir)) or ledger(index_dir):
        return False
    os.makedirs(_idx_dir(index_dir), exist_ok=True)
    with open(_model_marker(index_dir), "w", encoding="utf-8") as fh:
        fh.write(model + "\n")
    return True


def _shift_logs(index_dir):
    return sorted(glob.glob(os.path.join(index_dir, "state", "shifts", "*.json")))


def tokens_spent(index_dir):
    """Everything charged so far: saved blocks plus tokens spent on blocks that had to be discarded."""
    total = sum(v["tokens"] for v in ledger(index_dir).values())
    for p in _shift_logs(index_dir):
        try:
            with open(p, encoding="utf-8") as fh:
                total += int(json.load(fh).get("wasted_tokens", 0))
        except Exception:
            pass
    return total


def load_seen(index_dir):
    seen = {}
    for v in ledger(index_dir).values():
        with gzip.open(os.path.join(_idx_dir(index_dir), v["base"] + ".docs.jsonl.gz"), "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if r.get("hash") and "of" not in r:
                    seen.setdefault(r["hash"], r["doc"])
    return seen


def pool_blocks(pool_dir):
    out = {}
    for path in glob.glob(os.path.join(pool_dir, "shards", "*.jsonl.gz")):
        m = _POOL_RE.match(os.path.basename(path))
        if m:
            start, end, ok, gap, err = (int(x) for x in m.groups())
            out[start] = {"end": end, "ok": ok, "gap": gap, "err": err, "path": path}
    return out


def _read_pool_block(path):
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# ================================================================ git helpers (same discipline as sci_relay)
def _git(d, *args):
    return subprocess.run(["git", "-C", d, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


def _last_line(proc):
    lines = (proc.stderr or proc.stdout or "").strip().splitlines()
    return lines[-1] if lines else "no message"


def _sync(d):
    if not _git(d, "remote").stdout.split():
        return True, ""
    branch = _git(d, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if _git(d, "ls-remote", "--exit-code", "--heads", "origin", branch).returncode != 0:
        return True, ""
    p = _git(d, "pull", "--rebase", "origin", branch)
    return p.returncode == 0, _last_line(p)


def _push(d):
    p = _git(d, "push", "origin", "HEAD")
    if p.returncode != 0 and _sync(d)[0]:
        p = _git(d, "push", "origin", "HEAD")
    return p.returncode == 0, _last_line(p)


def _commit(d, paths, message):
    for args in (("add", "--", *paths), ("commit", "-m", message)):
        p = _git(d, *args)
        if p.returncode != 0:
            raise RuntimeError(f"git {args[0]} failed: {_last_line(p)}")


BRANCH = "claude/sci-index"


def init_index_branch(code_repo, index_dir):
    """Attach the index branch as its own folder (never mixed with code). Creates it empty (an orphan branch) the first time."""
    _git(code_repo, "fetch", "origin")
    if _git(code_repo, "ls-remote", "--exit-code", "--heads", "origin", BRANCH).returncode == 0:
        p = _git(code_repo, "worktree", "add", "-B", BRANCH, index_dir, f"origin/{BRANCH}")
        if p.returncode != 0:
            raise RuntimeError(f"could not attach {BRANCH}: {_last_line(p)}")
        return f"attached existing {BRANCH}"
    for args, where in ((("worktree", "add", "--detach", index_dir), code_repo), (("checkout", "--orphan", BRANCH), index_dir),
                        (("rm", "-rf", "-q", "."), index_dir), (("commit", "--allow-empty", "-m", "start of the index branch"), index_dir),
                        (("push", "-u", "origin", BRANCH), index_dir)):
        p = _git(where, *args)
        if p.returncode != 0:
            raise RuntimeError(f"git {args[0]} failed: {_last_line(p)}")
    return f"created {BRANCH}"


def active_check(code_repo, now=None, max_age=1500, ref=f"origin/{BRANCH}"):
    p = _git(code_repo, "log", "-1", "--format=%ct%x09%s", ref)
    if p.returncode != 0 or not p.stdout.strip():
        return "IDLE (no index branch yet)"
    ts, _, subject = p.stdout.strip().partition("\t")
    age = (now if now is not None else time.time()) - int(ts)
    if subject.startswith("index block") and age < max_age:
        return f"ACTIVE (last block committed {int(age)}s ago)"
    return f"IDLE (newest commit: '{subject}', {int(age)}s ago)"


# ================================================================ the shift
def shift(pool_dir, index_dir, minutes=50, ceiling=DEFAULT_CEILING, client=None, sleep=time.sleep, clock=time.monotonic,
          out=print, pause=2.0, block_size=BLOCK_SIZE, est_block_seconds=120, max_blocks=None, batch_items=500,
          from_id=None, to_id=None, model=MODEL, bucket_dir=None, skip_paths=None, max_new_tokens=None, extra_dirs=None):
    """One time-boxed run: embeds the blocks not yet in the ledger, newest first. With `bucket_dir` the bucket's shards are blocks too (ids from BUCKET_BASE up; `skip_paths` are the
    bucket judgments the crawl already holds, loaded from the default skip file when not given). `ceiling` is a limit on everything ever spent on the index; `max_new_tokens` also
    limits what THIS run may spend, whatever was spent before (the lower of the two applies)."""
    if _git(index_dir, "rev-parse", "--is-inside-work-tree").returncode != 0:
        raise ValueError(f"{index_dir} is not a git repository")
    if bucket_dir and skip_paths is None:
        skip_paths = load_skip_paths()
    skip_paths = skip_paths or frozenset()
    started_iso, t0 = datetime.now(timezone.utc).isoformat(timespec="seconds"), clock()
    totals = {"blocks_done": 0, "docs_embedded": 0, "passages": 0, "tokens": 0, "wasted_tokens": 0}
    reason, est = None, est_block_seconds
    stop_file = os.path.join(index_dir, "STOP")
    ok, msg = _sync(index_dir)
    wrong_model = check_model(index_dir, model)
    if not ok:
        reason = f"could not update from the remote: {msg}"
    elif os.path.exists(stop_file):
        reason = "STOP file present in the index folder"
    elif wrong_model:
        reason = wrong_model
    try:
        if not reason:
            if client is None:
                client = make_client()
            done = set(ledger(index_dir))
            seen = load_seen(index_dir)
            spent = tokens_spent(index_dir)
            if max_new_tokens is not None:
                ceiling = min(ceiling, spent + max_new_tokens)
            blocks = all_blocks(pool_dir, bucket_dir, extra_dirs)
            todo = sorted((s for s in blocks if s not in done and blocks[s]["ok"] > 0 and (from_id is None or s <= from_id) and (to_id is None or s >= to_id)), reverse=True)
            if not todo:
                reason = "nothing left to do (every crawled block is already indexed)"
        for start in ([] if reason else todo):
            if os.path.exists(stop_file):
                reason = "STOP file present in the index folder"
                break
            if max_blocks is not None and totals["blocks_done"] >= max_blocks:
                reason = f"reached the --max-blocks limit ({max_blocks})"
                break
            remaining = minutes * 60 - (clock() - t0)
            if remaining < est:
                reason = f"time budget used up ({remaining:.0f}s left, a block takes about {est:.0f}s)"
                break
            b0 = clock()
            info = blocks[start]
            bsize = info["end"] - start + 1
            local_seen = dict(seen)
            blk = prepare_block(read_block(info, skip_paths), local_seen)
            need = blk["stats"]["est_tokens"]
            if spent + need > ceiling:
                reason = f"token ceiling reached ({spent:,} spent, next block needs about {need:,}, limit {ceiling:,}); nothing was sent for it"
                break
            try:
                vectors, tokens = embed_texts(client, [p["text"] for p in blk["passages"]], sleep=sleep, pause=pause,
                                              max_items=batch_items, budget_tokens=ceiling - spent, model=model)
            except EmbedStop as e:
                totals["wasted_tokens"] += e.used
                spent += e.used
                reason = f"stopped inside block {start}: {e.reason} (that block is discarded and will be redone)"
                break
            marked = _claim_model(index_dir, model)
            base = write_block_files(index_dir, start, bsize, blk["docs"], blk["passages"], vectors, tokens)
            rel = [os.path.join("index", base + s) for s in (".docs.jsonl.gz", ".meta.jsonl.gz") + ((".vec.npy",) if blk["passages"] else ())]
            if marked:
                rel.append(os.path.join("index", "MODEL"))
            _commit(index_dir, rel, f"index block {start:06d}-{start + bsize - 1:06d}")
            seen = local_seen
            spent += tokens
            st = blk["stats"]
            totals["blocks_done"] += 1
            totals["docs_embedded"] += st["docs_kept"]
            totals["passages"] += st["passages"]
            totals["tokens"] += tokens
            secs = clock() - b0
            est = max(secs * 1.25, 30)
            sk = st["skipped"]
            out(f"block {start:06d}: kept {st['docs_kept']} docs (skipped: civil {sk['not_criminal']}, copies {sk['duplicate']}, tiny {sk['short']}, held by the crawl {sk['in_crawl']}) | {st['passages']} passages | {tokens:,} tokens | total spent {spent:,} ({secs:.0f}s)")
            pushed_ok, pmsg = _push(index_dir)
            if not pushed_ok:
                reason = f"push failed: {pmsg}"
                break
        if reason is None:
            reason = "completed all pending blocks"
    except Exception as e:
        reason = f"internal error: {type(e).__name__}: {e}"[:300]

    seconds = round(clock() - t0, 1)
    log = dict(started_at=started_iso, ended_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), minutes=minutes, ceiling=ceiling,
               stop_reason=reason, seconds=seconds, **totals)
    log_rel = os.path.join("state", "shifts", f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:4]}.json")
    pushed = False
    try:
        os.makedirs(os.path.join(index_dir, "state", "shifts"), exist_ok=True)
        with open(os.path.join(index_dir, log_rel), "w", encoding="utf-8") as fh:
            json.dump(log, fh, indent=1)
        _commit(index_dir, [log_rel], "shift log")
        pushed, pmsg = _push(index_dir)
        if not pushed and "push failed" not in reason:
            reason += f"; push failed: {pmsg}"
    except Exception as e:
        reason += f"; could not save the shift log: {e}"[:200]
    return {**totals, "stop_reason": reason, "seconds": seconds, "pushed": pushed}


def status_summary(pool_dir, index_dir, ceiling=DEFAULT_CEILING, bucket_dir=None, extra_dirs=None):
    led = ledger(index_dir)
    blocks = pool_blocks(pool_dir)
    spent = tokens_spent(index_dir)
    logs = _shift_logs(index_dir)
    last = None
    if logs:
        with open(logs[-1], encoding="utf-8") as fh:
            last = json.load(fh)
    crawl = {s_: v for s_, v in led.items() if s_ < BUCKET_BASE}
    bucket = {s_: v for s_, v in led.items() if BUCKET_BASE <= s_ < EXTRA_BASE}
    extra = {s_: v for s_, v in led.items() if s_ >= EXTRA_BASE}
    out = {"blocks_done": len(crawl), "docs_embedded": sum(v["docs"] for v in crawl.values()), "passages": sum(v["passages"] for v in crawl.values()),
           "tokens_spent": spent, "ceiling": ceiling, "ceiling_left": ceiling - spent,
           "blocks_pending": len([s_ for s_ in blocks if s_ not in led and blocks[s_]["ok"] > 0]), "lowest_id_done": min(crawl) if crawl else None,
           "highest_id_done": max(v["end"] for v in crawl.values()) if crawl else None, "shifts": len(logs), "last_shift": last}
    if bucket or bucket_dir:                       # the bucket's blocks are counted apart, so the crawl figures above mean what they always meant
        bb = bucket_blocks(bucket_dir) if bucket_dir else {}
        out["bucket"] = {"blocks_done": len(bucket), "docs_embedded": sum(v["docs"] for v in bucket.values()), "passages": sum(v["passages"] for v in bucket.values()),
                         "tokens": sum(v["tokens"] for v in bucket.values()), "blocks_pending": (len([s_ for s_ in bb if s_ not in led and bb[s_]["ok"] > 0]) if bucket_dir else None)}
    if extra or extra_dirs:                        # court archive and High Court blocks, counted apart again
        eb = all_blocks(None, None, extra_dirs) if extra_dirs else {}
        out["extra"] = {"blocks_done": len(extra), "docs_embedded": sum(v["docs"] for v in extra.values()), "passages": sum(v["passages"] for v in extra.values()),
                        "tokens": sum(v["tokens"] for v in extra.values()), "blocks_pending": (len([s_ for s_ in eb if s_ not in led and eb[s_]["ok"] > 0]) if extra_dirs else None)}
    return out


def plan_bucket(bucket_dir, index_dir, skip_paths=None, ceiling=DEFAULT_CEILING, out=print):
    """What indexing the bucket would cost, found by preparing every pending bucket block exactly as a shift would, without calling the service (spends nothing, needs no key).
    Judgments already in the index (same text) are recognised, so run it against the real index folder."""
    skip_paths = load_skip_paths() if skip_paths is None else skip_paths
    led = ledger(index_dir)
    seen = load_seen(index_dir)
    blocks = bucket_blocks(bucket_dir)
    spent = tokens_spent(index_dir)
    tot = collections.Counter()
    per_scope = collections.defaultdict(collections.Counter)
    for start in sorted(blocks, reverse=True):
        if start in led or blocks[start]["ok"] == 0:
            continue
        blk = prepare_block(read_block(blocks[start], skip_paths), seen)
        st = blk["stats"]
        row = per_scope[blocks[start]["scope"] if not blocks[start]["scope"].startswith("refresh") else "refresh"]
        for key, val in (("blocks", 1), ("judgments", sum(1 for d in blk["docs"])), ("kept", st["docs_kept"]), ("passages", st["passages"]), ("est_tokens", st["est_tokens"]),
                         ("civil", st["skipped"]["not_criminal"]), ("copies", st["skipped"]["duplicate"]), ("tiny", st["skipped"]["short"]), ("held_by_crawl", st["skipped"]["in_crawl"])):
            row[key] += val
            tot[key] += val
    for scope, row in sorted(per_scope.items()):
        out(f"{scope:8}: {row['blocks']} blocks, {row['judgments']} judgments | kept {row['kept']} (civil {row['civil']}, copies {row['copies']}, tiny {row['tiny']}, held by the crawl {row['held_by_crawl']}) | {row['passages']} passages | about {row['est_tokens']:,} tokens")
    out(f"TOTAL: {tot['blocks']} blocks, kept {tot['kept']} judgments, {tot['passages']} passages, about {tot['est_tokens']:,} tokens; spent so far {spent:,}; ceiling {ceiling:,}; "
        f"{'fits under' if spent + tot['est_tokens'] <= ceiling else 'DOES NOT fit under'} the ceiling (this says nothing about the service's own allowance)")
    return {"per_scope": {k: dict(v) for k, v in per_scope.items()}, "total": dict(tot), "spent": spent, "ceiling": ceiling}


def make_client():
    key = os.environ.get("VOYAGE_API_KEY")
    if not key:
        raise RuntimeError("VOYAGE_API_KEY is not set in this environment")
    import voyageai
    return voyageai.Client(api_key=key)


# ================================================================ evaluation against the verified landmarks
W = {"reasoning": 1.0, "facts": 0.8, "argument": 0.85, "order": 0.6, "header": 0.3, "statute_text": 0.75}
STOP = set("the a an and or of to in on for is are was were be been can could would should must may might will shall do does did not that this with from by as at it its who what when how which if any all have has had than then them they their there these those under into about over after before while where whether such just only also more most other some".split())


def shingles(t, n=8):
    w = re.sub(r"[^a-z0-9 ]", " ", t.lower()).split()
    return {" ".join(w[i:i + n]) for i in range(max(len(w) - n + 1, 1))}


def is_pinned(text, pinned_sets):
    s = shingles(text)
    for ps in pinned_sets:
        inter = len(s & ps)
        if inter and inter / max(min(len(s), len(ps)), 1) >= 0.30:
            return True
    return False


def section_numbers(q):
    nums = set()
    for m in re.finditer(r"(?:sections?|s\.)\s+(\d{1,3}[A-Z]?(?:\s*(?:,|and|&)\s*\d{1,3}[A-Z]?)*)", q, re.I):
        nums |= set(re.findall(r"\d{1,3}[A-Z]?", m.group(1)))
    nums |= set(re.findall(r"\b\d{2,3}[A-Z]\b", q))
    return nums


def has_section(text, nums):
    for n in nums:
        if re.search(rf"\b(?:sections?|s\.|ss\.)\s*(?:[\w()]+\s*(?:,|and|&|or)\s*)*{n}(?!\d)", text, re.I):
            return True
    return False


def _load_index(index_dir):
    metas, vecs, docs_with = [], [], set()
    for start in sorted(ledger(index_dir)):
        v = ledger(index_dir)[start]
        d = _idx_dir(index_dir)
        if not v["passages"]:
            continue
        with gzip.open(os.path.join(d, v["base"] + ".meta.jsonl.gz"), "rt", encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh]
        metas.extend(rows)
        vecs.append(np.load(os.path.join(d, v["base"] + ".vec.npy")))
        docs_with.update(r["doc"] for r in rows)
    M = np.vstack(vecs) if vecs else np.zeros((0, 0), dtype=np.float16)
    return metas, M, docs_with


def run_eval(index_dir, client, landmarks_path=None, out=print, top_docs=5, model=MODEL):
    """The known-answer test: for each verified landmark (that is already embedded), ask its questions and see whether the
    case is in the top 5 AND the project's verified paragraph is among its top 3 passages. Same method as the local test.
    `model` must be the model that made the index's vectors (the questions are embedded with it)."""
    wrong_model = check_model(index_dir, model)
    if wrong_model:
        raise ValueError(wrong_model)
    landmarks_path = landmarks_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "landmarks.json")
    lm = json.load(open(landmarks_path, encoding="utf-8"))["landmarks"]
    metas, M, docs_with = _load_index(index_dir)
    results = []
    if len(metas):
        fts = sqlite3.connect(":memory:")
        fts.execute("create virtual table f using fts5(text, tokenize='porter unicode61')")
        fts.executemany("insert into f(rowid, text) values(?,?)", ((i, m["text"]) for i, m in enumerate(metas)))
    for L in lm:
        if L["doc"] not in docs_with:
            for q in L["questions"]:
                results.append({"name": L["name"], "kind": q["kind"], "status": "not_embedded_yet"})
            continue
        pins = [shingles(p["text"]) for p in L["pinned"]]
        for q in L["questions"]:
            question = q["q"]
            qv = np.asarray(client.embed([question], model=model, input_type="query").embeddings[0], dtype=np.float32)
            qv /= (np.linalg.norm(qv) or 1.0)
            sims = np.concatenate([M[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(M), 50000)])
            top = np.argsort(-sims)[:100]
            sem = [int(i) for i in top]
            toks = list(dict.fromkeys(t for t in re.findall(r"[A-Za-z0-9]{4,}", question.lower()) if t not in STOP))[:12]
            kw = [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (" OR ".join(f'"{t}"' for t in toks),))] if toks else []
            nums = section_numbers(question)
            sc = []
            for n in nums:
                sc += [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 30", (f'"section {n}"',))]
            rr = {}
            for lst in (sem, kw, sc):
                for rank, rid in enumerate(lst):
                    rr[rid] = rr.get(rid, 0.0) + 1.0 / (60 + rank)
            cand = [r for r, _ in sorted(rr.items(), key=lambda x: -x[1])][:60]
            resp = client.rerank(question, [metas[r]["text"][:3500] for r in cand], model="rerank-2", top_k=len(cand))
            rs = {cand[x.index]: x.relevance_score for x in resp.results}
            w = lambda rid: W.get(metas[rid]["section"], 1.0) * (1.10 if nums and has_section(metas[rid]["text"], nums) else 1.0)
            row = {"name": L["name"], "kind": q["kind"], "status": "tested"}
            for label, scored in (("meaning_only", [(r, float(sims[r])) for r in sem]), ("final", [(r, s * w(r)) for r, s in rs.items()])):
                order = [r for r, _ in sorted(scored, key=lambda x: -x[1])]
                seen_docs, ranked = set(), []
                for r in order:
                    if metas[r]["doc"] not in seen_docs:
                        seen_docs.add(metas[r]["doc"])
                        ranked.append(metas[r]["doc"])
                rank = ranked.index(L["doc"]) + 1 if L["doc"] in ranked else None
                own = [r for r in order if metas[r]["doc"] == L["doc"]][:3]
                pinned = any(is_pinned(metas[r]["text"], pins) for r in own)
                row[label] = {"doc_rank": rank, "pinned_in_top3": pinned, "success": bool(rank and rank <= top_docs and pinned)}
            row["doc_rank"], row["pinned_in_top3"], row["success"] = row["final"]["doc_rank"], row["final"]["pinned_in_top3"], row["final"]["success"]
            results.append(row)
            out(f"[{q['kind']:5}] {L['name'][:40]:40} meaning-only: #{row['meaning_only']['doc_rank']}{'/P' if row['meaning_only']['pinned_in_top3'] else ''} | final: #{row['final']['doc_rank']}{'/P' if row['final']['pinned_in_top3'] else ''}")
    tested = [r for r in results if r["status"] == "tested"]
    summary = {"tested": len(tested), "not_embedded_yet": len(results) - len(tested),
               "case_top5": sum(1 for r in tested if r["doc_rank"] and r["doc_rank"] <= top_docs),
               "pinned_top3": sum(1 for r in tested if r["pinned_in_top3"]), "full_success": sum(1 for r in tested if r["success"]),
               "meaning_only_full_success": sum(1 for r in tested if r["meaning_only"]["success"]),
               "passages_searched": int(len(metas))}
    out(f"SUMMARY: {summary}")
    return {"model": model, "results": results, "summary": summary}


# ================================================================ command line
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("--index-dir", required=True)
    p = sub.add_parser("shift")
    p.add_argument("--pool-dir", required=True)
    p.add_argument("--index-dir", required=True)
    p.add_argument("--bucket-dir", default=None, help="also index the bucket's shards (a checkout of branch claude/sci-bucket)")
    p.add_argument("--skip-file", default=None, help="list of bucket judgments the crawl already holds (default: coverage/bucket_match/none_resolution.csv.gz)")
    p.add_argument("--minutes", type=float, default=50)
    p.add_argument("--ceiling", type=int, default=DEFAULT_CEILING, help="limit on everything ever spent on the index (the total on file counts)")
    p.add_argument("--max-new-tokens", type=int, default=None, help="limit on what this run may spend, whatever was spent before")
    p.add_argument("--pause", type=float, default=2.0)
    p.add_argument("--max-blocks", type=int, default=None)
    p.add_argument("--from-id", type=int, default=None)
    p.add_argument("--to-id", type=int, default=None)
    p.add_argument("--model", default=MODEL)
    p.add_argument("--extra-dir", action="append", default=None, help="also index the prepared judgments under <dir>/index_blocks (a checkout of a data branch); may be given more than once")
    p = sub.add_parser("status")
    p.add_argument("--pool-dir", required=True)
    p.add_argument("--index-dir", required=True)
    p.add_argument("--bucket-dir", default=None)
    p.add_argument("--extra-dir", action="append", default=None)
    p.add_argument("--ceiling", type=int, default=DEFAULT_CEILING)
    p = sub.add_parser("plan-bucket", help="what indexing the bucket would cost; prepares every pending block, calls nothing, spends nothing")
    p.add_argument("--bucket-dir", required=True)
    p.add_argument("--index-dir", required=True)
    p.add_argument("--skip-file", default=None)
    p.add_argument("--ceiling", type=int, default=DEFAULT_CEILING)
    sub.add_parser("active-check")
    p = sub.add_parser("eval")
    p.add_argument("--index-dir", required=True)
    p.add_argument("--landmarks", default=None)
    p.add_argument("--push", action="store_true")
    p.add_argument("--model", default=MODEL)
    a = ap.parse_args(argv)
    if a.cmd == "init":
        print(init_index_branch(os.getcwd(), a.index_dir))
    elif a.cmd == "active-check":
        print(active_check(os.getcwd()))
    elif a.cmd == "status":
        print(json.dumps(status_summary(a.pool_dir, a.index_dir, a.ceiling, a.bucket_dir, a.extra_dir), indent=1))
    elif a.cmd == "plan-bucket":
        plan_bucket(a.bucket_dir, a.index_dir, load_skip_paths(a.skip_file), a.ceiling)
    elif a.cmd == "shift":
        skip = load_skip_paths(a.skip_file) if a.bucket_dir else None
        r = shift(a.pool_dir, a.index_dir, minutes=a.minutes, ceiling=a.ceiling, pause=a.pause, max_blocks=a.max_blocks, from_id=a.from_id, to_id=a.to_id, model=a.model,
                  bucket_dir=a.bucket_dir, skip_paths=skip, max_new_tokens=a.max_new_tokens, extra_dirs=a.extra_dir)
        print(f"Blocks done: {r['blocks_done']} | docs embedded: {r['docs_embedded']} | passages: {r['passages']} | tokens: {r['tokens']:,} | wasted: {r['wasted_tokens']:,}")
        print(f"Reason: {r['stop_reason']}")
    elif a.cmd == "eval":
        res = run_eval(a.index_dir, make_client(), landmarks_path=a.landmarks, model=a.model)
        rel = os.path.join("eval", f"landmark-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}.json")
        os.makedirs(os.path.join(a.index_dir, "eval"), exist_ok=True)
        with open(os.path.join(a.index_dir, rel), "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1)
        if a.push:
            _commit(a.index_dir, [rel], "landmark evaluation")
            print("pushed" if _push(a.index_dir)[0] else "push failed")


if __name__ == "__main__":
    main()
