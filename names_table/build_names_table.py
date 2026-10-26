"""The names table: one row per judgment in the search index, with a readable case name, the date, citations and a link to the judgment's PDF.

    python names_table/build_names_table.py [--index DIR] [--crawl DIR] [--out names_table/names_table.json.gz]
    python names_table/build_names_table.py --verify-links 150   # polite HEAD checks of a random sample (needs network)

Sources, in order of trust:
  crawl judgments (index doc id below 1,000,000,000; the id IS the court's archive number): the parties and date are read from the judgment's own opening by goodlaw/headers.py (the parser the
      good-law checker uses); the index's own case record is used when the parse fails. Link: https://api.sci.gov.in/jonew/judis/<id>.pdf (the file the crawler downloaded).
  bucket judgments (the open Supreme Court bucket, CC-BY-4.0, Dattam Labs): title, parties, date, citation and INSC number from the bucket's own metadata (coverage/bucket_match/worklist.csv.gz).
      Link: the PDF in the bucket (https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/<key>). This is a public mirror, not the court's website.
  side-index judgments: the title in the side index's manifest; the link is the one recorded when it was fetched (a crawl id, a bucket path or the court's URL).
A row whose name could not be read has name=None and review=True: the site must show the date and the link instead of inventing a name. Nothing here says anything about whether a case is good law.
"""
import argparse
import collections
import csv
import glob
import gzip
import hashlib
import io
import json
import os
import random
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from goodlaw import headers as H  # noqa: E402

SCHEMA = "names-table-1"
JUDIS_URL = "https://api.sci.gov.in/jonew/judis/{id}.pdf"
BUCKET_HOST = "https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/"
BUCKET_BASE = 1_000_000_000
NEWER_BASE = 2_000_000_000                  # documents added after the first index (2026-10): the index's own `src` record carries their title, date, citation, link and court
NO_COURT = "Court not recorded"
SC_COURT = "Supreme Court of India"         # every document below NEWER_BASE, and every side-index document unless its manifest says otherwise
NEWER_LINK_KIND = {"sci_newer": "court_site_pdf", "ghc_post2017": "high_court_bucket_pdf", "ghc_bucket": "high_court_bucket_pdf", "ghc_court": "high_court_site_pdf"}
SMALL = {"of", "and", "the", "for", "in", "on", "by", "to", "at", "a", "an", "vs", "v", "or", "etc"}
ACRONYMS = {"UOI", "CBI", "NCT", "NIA", "NDPS", "UP", "MP", "HP", "AP", "TN", "J&K", "BSNL", "LIC", "SEBI", "RBI", "ONGC", "CRPF", "BSF", "CISF", "DDA", "MCD", "NHAI", "AIIMS", "IAS", "IPS", "IFS", "SBI", "PNB", "HDFC", "ICICI",
            "II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII", "LTD", "PVT", "NCERT", "UGC", "AICTE", "CPI", "CPM", "BJP", "INC", "DMK", "AIADMK"}


def display_name(pet, resp):
    """'Petitioner v. Respondent', title-cased when the source is in capitals (initials such as U.P. and known acronyms are kept)."""
    def one(s):
        s = re.sub(r"^(?:[\d/\s.]*\)|\])\s*", "", re.sub(r"\s+", " ", s or "").strip())      # the tail of a caption line: '1505/2008) Name' or '] Name'
        s = re.sub(r"^\d+(?=[A-Za-z])", "", s)      # a page or paragraph number glued to the first word
        letters = [c for c in s if c.isalpha()]
        if letters and sum(c.isupper() for c in letters) / len(letters) >= 0.6:
            out = []
            for i, w in enumerate(s.split(" ")):
                core = re.sub(r"[^A-Za-z&/]", "", w)
                if core.upper() == "M/S":
                    out.append("M/s" + w[3:] if len(w) > 3 else "M/s")
                elif core.upper() in ACRONYMS or ("." in w and re.search(r"\b[A-Z]\.", w)) or re.fullmatch(r"[A-Z]", core or "a"):
                    out.append(w if core.upper() in ACRONYMS or "." in w else w)
                elif core.lower() in SMALL and i:
                    out.append(w.lower())
                elif core.upper() in ("ORS", "ANR"):
                    out.append(w.capitalize())
                else:
                    out.append(re.sub(r"[A-Za-z]+", lambda m: m.group(0).capitalize(), w))
            s = " ".join(out)
        return s
    p, r = one(pet), one(resp)
    return f"{p} v. {r}" if p and r else None


def split_parties(title):
    """('Petitioner', 'Respondent') from a title written 'X versus Y' or 'X Vs Y' (the High Court bucket's form); (None, None) when it has no such word."""
    parts = re.split(r"\s+(?:versus|vs\.?|v/s)\s+", re.sub(r"\s+", " ", title or "").strip(), maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return None, None
    resp = re.split(r"\.\s*(?:MR|MRS|MS|HON'?BLE|JUSTICE)\b", parts[1], maxsplit=1, flags=re.I)[0]           # the court site's titles sometimes end with the bench: 'THE STATE OF ASSAM. MR MADAN B. LOKUR GOSWAMI'
    return H.clean_name(parts[0]), H.clean_name(resp)


def judis_url(doc):
    return JUDIS_URL.format(id=int(doc))


def bucket_url(key):
    return BUCKET_HOST + key


def _iso(d):
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", (d or "").strip())
    return H.to_iso(m[1], m[2], m[3]) if m else (d if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d or "") else None)


def suspicious(pet, resp):
    """True when a parsed name looks wrong enough that a person should look: missing, very long, or containing caption words."""
    if not pet or not resp:
        return True
    bad = re.compile(r"J\s?U\s?D\s?G\s?M\s?E\s?N\s?T|JURISDICTION|SUPREME COURT OF|APPEAL NO|\(?\s*PETITION[^A-Za-z]{0,3}\(?\w*\)?\s*NO|\bNO\.?\s*\d|\bOF\s+(?:19|20)\d\d|ARISING OUT|REPORTABLE", re.I)
    return len(pet) > 160 or len(resp) > 160 or bool(bad.search(pet) or bad.search(resp))


_ROLE_PET = r"(?:Appell?ants?|Petitioners?|Applicants?|Complainants?|Revisionists?|Plaintiffs?)"
_ROLE_RESP = r"(?:Respon\w*|Opposite\s+Parties|Opposite\s+Party|Defendants?|Accused)"
_VS_ANY = re.compile(r"[:\s.…-]*(?:\bVERSUS\b|\bVersus\b|\bVs\b\.?|\bVS\b\.?|\bvs\b\.?|\bV/s\b)[:\s.…-]*")
_ANCHOR = re.compile(r"(?:OF\s+(?:19|20)\d\d\s*\]?\)?|\(\s*[Aa]rising[^)]*\)|\[\s*[Aa]rising[^\]]*\]|JURISDICTION|\bNo\.?\s*\d+(?:\s*/\s*\d+)?\b(?:\s*of\s*(?:19|20)\d\d)?|\bNON-?REPORTABLE\b|\bREPORTABLE\b|\bPage\s+\d+\b|\bJUDGMENT\b|\(CRL\.?\)|\(Crl\.?\))", re.I)


def caption_fallback(flat):
    """Parties from a flattened modern caption that goodlaw/headers.py did not read ('Shankaraya Naik & Ors. ....Appellants Vs. State of Karnataka ....Respondent'). (None, None) when it cannot."""
    for vm in _VS_ANY.finditer(flat[:1500]):
        before, after = flat[:vm.start()], flat[vm.end():]
        before = re.sub(r"[.…\s:]*(?:\(\s*s\s*\)\s*)?$", "", before)
        before = re.sub(r"[.…\s:]*" + _ROLE_PET + r"\s*(?:\(\s*s\s*\)\s*)?$", "", before, flags=re.I)
        anchors = list(_ANCHOR.finditer(before))
        pet = before[anchors[-1].end():] if anchors else before
        rm = re.search(r"[.…\s:]*" + _ROLE_RESP, after[:400], re.I) or re.search(r"\bJ\s?U\s?D\s?G\s?M\s?E\s?N\s?T\b|\bO\s?R\s?D\s?E\s?R\b", after[:400])
        if not rm:
            continue
        resp = after[:rm.start()]
        pet, resp = H.clean_name(pet[-200:]), H.clean_name(resp[:240])
        if ")" in pet and pet.count(")") > pet.count("("):         # the tail of an "(Arising out of SLP(Crl.) No...)" or "(From the judgment ...)" line
            pet = pet[pet.rindex(")") + 1:]
        pet = re.sub(r"^[\d\s.)]+(?=[A-Za-z])", "", pet)
        if len(pet) >= 2 and len(resp) >= 2:
            return pet, resp
    return None, None


def read_index(index_dir):
    """({doc: {'case': {...} or None, 'src': {...} or None}} for every document with passages, in the index)."""
    have = set()
    for f in glob.glob(os.path.join(index_dir, "index", "*.meta.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    have.add(int(json.loads(line)["doc"]))
    docs = {d: {"case": None, "src": None} for d in have}
    for f in glob.glob(os.path.join(index_dir, "index", "*.docs.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    d = int(r["doc"])
                    if d in docs:
                        docs[d]["case"] = r.get("case") or docs[d]["case"]
                        docs[d]["src"] = r.get("src") if isinstance(r.get("src"), dict) else docs[d]["src"]
    return docs


def read_crawl(crawl_dir, wanted):
    """{id: parse dict (+ 'bytes')} for the wanted crawl ids, read from the crawl shards."""
    out = {}
    for f in sorted(glob.glob(os.path.join(crawl_dir, "shards", "*.jsonl.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                try:
                    d = int(r["id"])
                except (KeyError, ValueError):
                    continue
                if d in wanted and r.get("text"):
                    p = H.parse_crawl(r["text"])
                    p["bytes"] = int(float(r.get("bytes") or 0))
                    p["head"] = re.sub(r"\s+", " ", r["text"][:300])
                    p["head_long"] = re.sub(r"\s+", " ", r["text"][:1800])
                    out[d] = p
    return out


def read_bucket_shards(bucket_dir):
    """{path: metadata row} from the bucket data branch's shards (this is where judgments added by the monthly refresh are listed; the worklist predates them)."""
    out = {}
    for f in sorted(glob.glob(os.path.join(bucket_dir, "shards", "*.jsonl.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    if r.get("path") and r.get("key"):
                        out[r["path"]] = r
    return out


def read_worklist(path):
    raw = open(path, "rb").read()
    text = gzip.decompress(raw).decode("utf-8") if raw[:2] == b"\x1f\x8b" else raw.decode("utf-8")
    return {r["path"]: r for r in csv.DictReader(io.StringIO(text))}


def build(index_dir, crawl_dir, work, side_dirs=(), root=ROOT):
    docs = read_index(index_dir)
    crawl_ids = {d for d in docs if d < BUCKET_BASE}
    crawl = read_crawl(crawl_dir, crawl_ids)
    twins = {int(float(w['best_crawl_id'])): w for w in work.values() if w.get('in_crawl') == 'yes' and w.get('best_crawl_id')}
    rows, stats = [], collections.Counter()
    for d in sorted(docs):
        rec, src = docs[d]["case"], docs[d]["src"]
        row = {"doc": d, "name": None, "petitioner": None, "respondent": None, "date": None, "year": None, "citations": {}, "name_source": None, "link": None, "link_kind": None, "review": False, "court": SC_COURT}
        if d >= NEWER_BASE and src and src.get("source") in NEWER_LINK_KIND:
            pet, resp = split_parties(src.get("title"))
            row["petitioner"], row["respondent"], row["name_source"] = pet, resp, "index_src_title"
            row["name"] = display_name(pet, resp) if pet and resp and not suspicious(pet, resp) else None
            row["date"] = _iso(src.get("date"))
            cite, neutral = str(src.get("citation") or "").strip(), str(src.get("neutral_citation") or "").strip()
            cits = {}
            if re.search(r"\bINSC\b", cite):
                cits["insc"] = cite
            elif cite:
                cits["case_no"] = cite
            if neutral and neutral != "None":
                cits["neutral"] = neutral
            if src.get("case_id") and str(src["case_id"]) != cite:
                cits["case_id"] = str(src["case_id"])
            row["citations"] = cits
            url = str(src.get("url") or src.get("bucket_url") or "")
            row["link"] = url if url.startswith(("http://", "https://")) else None
            row["link_kind"] = NEWER_LINK_KIND[src["source"]] if row["link"] else None
            row["court"] = str(src.get("court") or "").strip() or NO_COURT
            row["review"] = row["court"] == NO_COURT                   # a document whose court is not recorded is flagged for a person and never labelled as the Supreme Court
        elif d < BUCKET_BASE:
            p = crawl.get(d)
            pet = resp = None
            if p and not suspicious(p["pet"], p["resp"]):
                pet, resp, row["name_source"] = p["pet"], p["resp"], "header_parsed"
            elif rec and (rec.get("pet") or rec.get("resp")):
                pet, resp, row["name_source"] = H.clean_name(rec.get("pet")), H.clean_name(rec.get("resp")), "index_case_record"
                if suspicious(pet, resp):
                    pet = resp = None
            if not (pet and resp) and p:
                pet, resp = caption_fallback(p.get("head_long", ""))
                if pet and resp and not suspicious(pet, resp):
                    row["name_source"] = "header_fallback"
                else:
                    pet = resp = None
            if not (pet and resp) and d in twins:
                tw = twins[d]
                pet, resp = H.clean_name(tw.get("petitioner")), H.clean_name(tw.get("respondent"))
                row["name_source"] = "bucket_twin_metadata"
                if suspicious(pet, resp):
                    pet = resp = None
            row["petitioner"], row["respondent"] = pet, resp
            row["name"] = display_name(pet, resp) if pet and resp else None
            row["date"] = (p or {}).get("date") or _iso((rec or {}).get("date")) or (_iso(twins[d].get("decision_date")) if d in twins else None)
            if p:
                row["citations"] = {k: v for k, v in (("air", p["cite_air"]), ("scr", p["cite_scr"]), ("scc", p["cite_scc"])) if v}
            row["link"], row["link_kind"] = judis_url(d), "court_archive_pdf"
        else:
            w = work.get((src or {}).get("path"))
            if w:
                pet, resp = H.clean_name(w.get("petitioner")), H.clean_name(w.get("respondent"))
                if not pet or not resp:
                    parts = re.split(r"\s+versus\s+", w.get("title") or "", flags=re.I)
                    if len(parts) == 2:
                        pet, resp = H.clean_name(parts[0]), H.clean_name(parts[1])
                row["petitioner"], row["respondent"], row["name_source"] = pet, resp, "bucket_metadata"
                row["name"] = display_name(pet, resp) if pet and resp and not suspicious(pet, resp) else None
                row["date"] = _iso(w.get("decision_date"))
                row["citations"] = {k: v for k, v in (("scr", w.get("citation")), ("insc", w.get("case_id")), ("cnr", w.get("cnr"))) if v}
                row["link"], row["link_kind"] = bucket_url(w["key"]), "open_bucket_pdf"
            elif src and src.get("title"):
                parts = re.split(r"\s+versus\s+", src["title"], flags=re.I)
                if len(parts) == 2:
                    row["petitioner"], row["respondent"] = H.clean_name(parts[0]), H.clean_name(parts[1])
                    row["name"] = display_name(row["petitioner"], row["respondent"])
                row["name_source"] = "index_src_title"
                row["date"] = _iso(src.get("date"))
                row["citations"] = {k: v for k, v in (("scr", src.get("citation")), ("insc", src.get("case_id"))) if v}
        row["year"] = int(row["date"][:4]) if row["date"] else None
        row["review"] = row["review"] or row["name"] is None
        stats[(row["name_source"] or "none", row["name"] is not None)] += 1
        rows.append(row)
    sides = []
    for sd in side_dirs:
        man = json.load(open(os.path.join(sd, "SUPPLEMENT.json"), encoding="utf-8"))
        lp = os.path.join(root, man["docs_list"]) if man.get("docs_list") else None
        listed = {int(e["index_doc"]): e for e in json.load(open(lp, encoding="utf-8"))["docs"]} if lp and os.path.exists(lp) else {}
        for e in man.get("documents_detail", []):
            d = int(e["doc"])
            if d in docs:
                continue
            l = listed.get(d, {})
            title = re.sub(r"\s+", " ", l.get("title") or e["title"])
            parts = re.split(r"\s+(?:versus|v\.)\s+", title, maxsplit=1, flags=re.I)
            pet, resp = (H.clean_name(parts[0]), H.clean_name(re.sub(r"\s*\(.*$", "", parts[1]))) if len(parts) == 2 else (None, None)
            if d < BUCKET_BASE:
                link, kind = judis_url(d), "court_archive_pdf"
            elif l.get("url"):
                link, kind = l["url"], "court_pdf_as_fetched"
            elif l.get("bucket_path"):
                w = work.get(l["bucket_path"])
                link, kind = (bucket_url(w["key"]), "open_bucket_pdf") if w else (None, None)
            else:
                link, kind = None, None
            rows.append({"doc": d, "name": display_name(pet, resp) if pet and resp else title, "petitioner": pet, "respondent": resp, "date": l.get("date"), "year": l.get("year"),
                         "citations": {"insc": l["insc"]} if l.get("insc") else {}, "name_source": "side_index_manifest", "link": link, "link_kind": kind, "review": link is None,
                         "court": l.get("court") or e.get("court") or SC_COURT})
            sides.append(d)
    return rows, stats, len(sides)


def write(rows, out, meta):
    doc = {"schema": SCHEMA, "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **meta, "rows": rows}
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
    return doc


def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        doc = json.load(fh)
    return doc, {r["doc"]: r for r in doc["rows"]}


def verify_links(rows, crawl, work_by_key, n, seed=5, pause=1.0, head=None):
    """Polite HEAD requests on a random sample of links. A crawl link passes when the file is a PDF whose size equals the size the crawler stored for that id; a bucket link when it is a PDF of the size
    the bucket's listing gave. Returns {'checked', 'ok', 'bad': [...]} per link kind."""
    head = head or _head
    rnd = random.Random(seed)
    out = {}
    for kind in ("court_archive_pdf", "open_bucket_pdf"):
        pool = [r for r in rows if r["link_kind"] == kind]
        pick = rnd.sample(pool, min(n, len(pool)))
        res = {"checked": 0, "ok": 0, "bad": []}
        for r in pick:
            status, ctype, length = head(r["link"])
            want = crawl.get(r["doc"]) if kind == "court_archive_pdf" else work_by_key.get(r["link"])
            good = status == 200 and "pdf" in (ctype or "").lower() and (not want or length == want)
            res["checked"] += 1
            res["ok"] += bool(good)
            if not good:
                res["bad"].append({"doc": r["doc"], "link": r["link"], "status": status, "type": ctype, "length": length, "expected": want})
            time.sleep(pause)
        out[kind] = res
    return out


def _head(url, timeout=30):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Recourse-research-crawler/1.0 (low-rate link check)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type"), int(r.headers.get("Content-Length") or 0)
    except Exception as e:  # noqa: BLE001
        return getattr(e, "code", 0), None, 0


def review_sample(rows, crawl, n, seed=21):
    """n random named rows plus every unnamed row, for a person to check: what the table says beside what the judgment's own opening says. Returns CSV rows."""
    rnd = random.Random(seed)
    named = [r for r in rows if r["name"]]
    pick = rnd.sample(named, min(n, len(named))) + [r for r in rows if not r["name"]]
    out = []
    for r in pick:
        out.append({"doc": r["doc"], "table_name": r["name"] or "(NOT READ - needs a person)", "date": r["date"], "how_read": r["name_source"],
                    "judgment_opens_with": (crawl.get(r["doc"], {}).get("head") or "")[:260], "link": r["link"], "person_says": "", "correct_name_if_wrong": ""})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index", default=os.path.normpath(os.path.join(ROOT, "..", "recourse-sci-index")))
    ap.add_argument("--crawl", default=os.path.normpath(os.path.join(ROOT, "..", "recourse-sci-pool-data")))
    ap.add_argument("--bucket", default=os.path.normpath(os.path.join(ROOT, "..", "recourse-sci-bucket-data")))
    ap.add_argument("--worklist", default=os.path.join(ROOT, "coverage", "bucket_match", "worklist.csv.gz"))
    ap.add_argument("--out", default=os.path.join(HERE, "names_table.json.gz"))
    ap.add_argument("--sides", default=os.path.join(ROOT, "review_data", "side_index", "*"), help="glob of the side-index folders (default: the three made for index 3c80a26)")
    ap.add_argument("--index-commit", default=None, help="the index's commit when the index folder is not a git checkout (a downloaded archive)")
    ap.add_argument("--review-sample", type=int, default=0, help="write names_table/review_sample.csv with this many random named rows plus every unnamed one")
    ap.add_argument("--verify-links", type=int, default=0, help="HEAD-check this many random links of each kind (about one second apiece)")
    a = ap.parse_args(argv)
    sides = sorted(glob.glob(a.sides))
    work = read_worklist(a.worklist)
    work.update(read_bucket_shards(a.bucket))
    rows, stats, n_side = build(a.index, a.crawl, work, sides)
    head = a.index_commit or subprocess_head(a.index)
    named = sum(1 for r in rows if r["name"])
    meta = {"index_commit": head, "documents": len(rows), "named": named, "to_review": len(rows) - named, "side_index_documents": n_side,
            "by_source": {f"{k[0]}:{'named' if k[1] else 'unnamed'}": v for k, v in sorted(stats.items(), key=str)},
            "link_kinds": dict(collections.Counter(r["link_kind"] for r in rows)),
            "courts": dict(collections.Counter(r.get("court") for r in rows)),
            "bucket_credit": "Bucket judgments: open Supreme Court judgments bucket, CC-BY-4.0, Dattam Labs (s3://indian-supreme-court-judgments).",
            "high_court_bucket_credit": "High Court bucket judgments: open Indian High Court Judgments bucket (AWS Open Data, Dattam Labs; s3://indian-high-court-judgments). Licence terms to be confirmed before public use."}
    doc = write(rows, a.out, meta)
    print(json.dumps({k: v for k, v in doc.items() if k != "rows"}, indent=1))
    if a.review_sample:
        crawl = read_crawl(a.crawl, {r["doc"] for r in doc["rows"] if r["doc"] < BUCKET_BASE})
        sample = review_sample(doc["rows"], crawl, a.review_sample)
        with open(os.path.join(HERE, "review_sample.csv"), "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(sample[0]))
            w.writeheader()
            w.writerows(sample)
        print(f"review_sample.csv: {len(sample)} rows")
    if a.verify_links:
        crawl_sizes = {}
        crawl = read_crawl(a.crawl, {r["doc"] for r in rows if r["link_kind"] == "court_archive_pdf"})
        crawl_sizes = {d: p["bytes"] for d, p in crawl.items()}
        by_key = {bucket_url(w["key"]): int(float(w.get("bytes") or w.get("size") or 0)) for w in work.values() if (w.get("bytes") or w.get("size"))}
        res = verify_links(rows, crawl_sizes, by_key, a.verify_links)
        json.dump(res, open(os.path.join(HERE, "link_check.json"), "w"), indent=1)
        print(json.dumps({k: {"checked": v["checked"], "ok": v["ok"], "bad": len(v["bad"])} for k, v in res.items()}))
    return 0


def subprocess_head(path):
    import subprocess
    try:
        return subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


if __name__ == "__main__":
    sys.exit(main())
