"""The cases Recourse can show a user, and which judgment in our collection each one is.

The live site answers from a library of judgments (the registry behind `retrieval._JUDGMENT_CHUNK_FILES`, 68 cases when this was written) plus a pilot pool (16 cases,
8 of them also in the registry). Each case reaches the answer step as the exact `case_name` string printed on its chunks, and Recourse's own currency records are looked up by
that string. To precompute a currency card for each case we need three things: the list (`snapshot`), a judgment in our collection for each Supreme Court case
(`match_case`), and an honest status for the rest (a High Court decision, a case we do not hold, a case we cannot tell apart from another).

A wrong match is the worst error here (a card about the wrong judgment would be attached to the right case name), so a match is accepted only on a citation that agrees with
the name, or on both parties' names plus the year; anything else is reported as ambiguous and left for a person. `goodlaw/targets/library_overrides.json` holds a person's decisions.
"""
import datetime
import json
import os
import re
import subprocess
import sys

from . import cites as C
from . import mentions as M

_STOP = {"v", "vs", "versus", "of", "the", "and", "anr", "ors", "another", "others", "m", "s", "mr", "mrs", "ms", "dr", "shri", "smt", "ltd", "limited", "pvt", "private",
         "co", "company", "through", "by", "etc", "in", "re", "a", "an", "for", "to", "on"}

# Runs inside the Recourse checkout (its own code knows its library); prints one JSON document after the marker. Nothing is written there (no bytecode).
_SNAPSHOT_SCRIPT = r'''
import sys, json, glob, os
sys.dont_write_bytecode = True
sys.path.insert(0, ".")
import retrieval as r
import citation_currency as cc
names = cc._build_case_name_to_case_key()
reg = r._JUDGMENT_CHUNK_FILES
core = {}
for p in glob.glob("corpus/*.json"):
    d = json.load(open(p, encoding="utf-8"))
    if "case_name" in d:
        core[d["case_name"]] = d
cases = {}
for name, key in names.items():
    first = json.load(open(reg[key], encoding="utf-8"))[0]
    c = core.get(name, {})
    cases[name] = {"case_name": name, "case_key": key, "citation": c.get("citation") or first.get("citation"), "court": c.get("court"),
                   "source_url": c.get("source_url") or first.get("source_url"), "pools": ["library"], "recourse_currency": []}
for p in sorted(glob.glob("pilot_chunks/*_chunks.json")):
    first = json.load(open(p, encoding="utf-8"))[0]
    name = first["case_name"]
    if name in cases:
        cases[name]["pools"].append("pilot_tier")
    else:
        cases[name] = {"case_name": name, "case_key": None, "citation": first.get("citation"), "court": None, "source_url": first.get("source_url"), "pools": ["pilot_tier"], "recourse_currency": []}
    cases[name]["topic"] = first.get("topic")
inv = {v: k for k, v in names.items()}
for dk, rec in cc.CITATION_CURRENCY_MAP.items():
    ck = r.JUDGMENT_CITATION_MAP.get(dk, {}).get("case_key")
    nm = inv.get(ck)
    if nm in cases:
        cases[nm]["recourse_currency"].append({"doctrine_key": dk, "status": rec.get("status"), "last_checked_date": rec.get("last_checked_date")})
print("@@JSON@@" + json.dumps(list(cases.values())))
'''


def snapshot(recourse_dir, today=None):
    """{"snapshot": {...}, "cases": [...]} read from a Recourse checkout by running its own registry code in a subprocess (nothing is written there)."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    done = subprocess.run([sys.executable, "-c", _SNAPSHOT_SCRIPT], cwd=recourse_dir, env=env, capture_output=True, text=True, timeout=600)
    marker = "@@JSON@@"
    if done.returncode != 0 or marker not in done.stdout:
        raise RuntimeError(f"could not read the library from {recourse_dir}: {(done.stderr or done.stdout)[-400:]}")
    cases = json.loads(done.stdout.split(marker, 1)[1])
    commit = None
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=recourse_dir, capture_output=True, text=True)
    if git.returncode == 0:
        commit = git.stdout.strip()
    for c in cases:
        c["court_class"] = court_class(c)
        c["year"] = year_of(c.get("citation") or "")
    cases.sort(key=lambda c: c["case_name"].lower())
    return {"snapshot": {"read_from": "Recourse checkout (registry, pilot pool and curated currency records)", "recourse_commit": commit, "date": today or datetime.date.today().isoformat(),
                         "cases": len(cases)}, "cases": cases}


def court_class(case):
    """'SC' (Supreme Court), 'HC' (a High Court), 'OTHER' or 'UNKNOWN' (the entry does not say and the citation does not show it)."""
    court = (case.get("court") or "").lower()
    if court:
        if court.startswith("supreme court"):
            return "SC"
        if "high court" in court:
            return "HC"
        return "OTHER"
    cite = case.get("citation") or ""
    if re.search(r"SCC\s*OnLine\s+(?!SC\b)[A-Z][a-z]+", cite):
        return "HC"
    if re.search(r"\bSC\b|SCC|S\.C\.R|\bSCR\b|INSC|Supreme Court|AIR\s*SCW|AIRONLINE\s+\d{4}\s+SC", cite, re.I):
        return "SC"
    if "sci.gov.in" in (case.get("source_url") or ""):
        return "SC"
    return "UNKNOWN"


def year_of(citation):
    """The first year in a citation or case number ("(2010) 11 SCC 441", "Criminal Appeal No. 511 of 2022"), or None."""
    m = re.search(r"\b((?:19|20)\d\d)\b", citation or "")
    return int(m.group(1)) if m else None


def split_name(case_name):
    """(first party, second party) of a case name written "A v B"; the second is '' when there is no 'v'."""
    parts = re.split(r"\s+(?:v\.?|vs\.?|versus)\s+", case_name or "", maxsplit=1, flags=re.I)
    return parts[0], (parts[1] if len(parts) > 1 else "")


_ABBREV = [(r"\bu\.\s?p\b\.?", "uttar pradesh"), (r"(?<=state of )up\b\.?", "uttar pradesh"), (r"\bm\.\s?p\b\.?", "madhya pradesh"), (r"(?<=state of )mp\b\.?", "madhya pradesh"), (r"\ba\.\s?p\b\.?", "andhra pradesh"), (r"\bt\.\s?n\b\.?", "tamil nadu"),
           (r"\bw\.\s?b\b\.?", "west bengal"), (r"\bh\.\s?p\b\.?", "himachal pradesh"), (r"\bgovt\b\.?", "government"), (r"\bdept\b\.?", "department"),
           (r"\bcorpn\b\.?", "corporation"), (r"\badmn\b\.?", "administration"), (r"\bassn\b\.?", "association"), (r"\bltd\b\.?", "limited"), (r"\bpvt\b\.?", "private")]
_ABBREV = [(re.compile(rx, re.I), to) for rx, to in _ABBREV]


def _expand(s):
    """Lower-case text with the usual abbreviations in case names written out ("State of U.P." -> "state of uttar pradesh", "Govt." -> "government")."""
    s = (s or "").lower()
    for rx, to in _ABBREV:
        s = rx.sub(to, s)
    return s


def _squash(s):
    return re.sub(r"[^a-z0-9]", "", _expand(s))


def _tokens(party):
    """A party's words, initials included (without them "D.K. Basu" would match every other Basu); stock words are left out."""
    return [w for w in re.findall(r"[a-z0-9]+", _expand(M.clean_party(party))) if w not in _STOP]


_ABBREVIATED = {"uttar", "pradesh", "madhya", "andhra", "tamil", "nadu", "west", "bengal", "himachal", "government", "department", "corporation", "administration",
                "association", "limited", "private"}   # words a title may print in short form ("U.P.", "Govt.", "Ltd."), so they cannot be searched for


def _query_words(case_name):
    """Words to look for in a title: the longest distinctive words of both parties (three letters or more), leaving out words a title may abbreviate."""
    pet, resp = split_name(case_name)
    words = {w for w in _tokens(pet) + _tokens(resp) if len(w) >= 3}
    safe = words - _ABBREVIATED
    return sorted(safe or words, key=len, reverse=True)


def name_score(case_name, doc):
    """0 to 1: how well both parties of the library's case name are found in the document's title (and its petitioner and respondent fields). A party's whole cleaned
    name found with spaces and punctuation removed counts as 1 (so "Mohan Lal" finds "MOHANLAL"); otherwise the weighted share of its words found, a word of one or two
    letters (an initial, "Md") counting half. The lower of the two parties' scores is returned, so both sides must agree."""
    text = " ".join([doc.get("title") or "", doc.get("pet") or "", doc.get("resp") or ""])
    squashed = _squash(text)
    words = set(re.findall(r"[a-z0-9]+", _expand(text)))
    scores = []
    for party in split_name(case_name):
        cleaned = M.clean_party(party)
        if not cleaned:
            continue
        sq = _squash(cleaned)
        if len(sq) >= 4 and sq in squashed:
            scores.append(1.0)
            continue
        toks = _tokens(party)
        if not toks:
            continue
        weight = [0.5 if len(t) <= 2 else 1.0 for t in toks]
        hit = sum(w for t, w in zip(toks, weight) if t in words or (len(t) >= 6 and t in squashed))
        scores.append(hit / sum(weight))
    return min(scores) if scores else 0.0


def _slim(d, score=None):
    return {"doc_key": d["doc_key"], "title": d["title"], "date": d.get("date"), "year": d.get("year"), "bench_size": d.get("bench_size"), "score": None if score is None else round(score, 2)}


def _drop_second_copies(docs):
    """A bucket text that may be a second copy of a crawl text already among the candidates is not a separate candidate."""
    keys = {d["doc_key"] for d in docs}
    return [d for d in docs if not (d.get("maybe_dup_of") and d["maybe_dup_of"] in keys)]


def match_case(corpus, case, overrides=None):
    """Which judgment in the collection is this library case? -> dict(status, doc_key, method, confidence, note, candidates).

    status: MATCHED, NOT_CHECKABLE_HIGH_COURT, NOT_IN_COLLECTION or AMBIGUOUS_MATCH.
    A match needs a citation the judgment is known by AND names that agree ('citation'), or both parties' names and the year within one of the citation's ('name_year').
    Cases of another court are not looked for. A person's decision in `overrides` ({case_name: {"doc_key": ..} | {"not_in_collection": reason}}) wins."""
    name = case["case_name"]
    ov = (overrides or {}).get(name)
    if ov:
        if ov.get("doc_key"):
            d = corpus.get(ov["doc_key"], with_text=False)
            if not d:
                return {"status": "AMBIGUOUS_MATCH", "doc_key": None, "method": "override", "confidence": None, "note": f"override names {ov['doc_key']}, which is not in the collection", "candidates": []}
            return {"status": "MATCHED", "doc_key": d["doc_key"], "method": "override", "confidence": "person", "note": ov.get("note") or "chosen by a person", "candidates": [_slim(d)]}
        if ov.get("not_in_collection"):
            return {"status": "NOT_IN_COLLECTION", "doc_key": None, "method": "override", "confidence": "person", "note": ov["not_in_collection"], "candidates": []}
    klass = case.get("court_class") or court_class(case)
    if klass in ("HC", "OTHER"):
        return {"status": "NOT_CHECKABLE_HIGH_COURT", "doc_key": None, "method": None, "confidence": None,
                "note": f"decided by {case.get('court') or 'a court other than the Supreme Court'}; the collection holds only Supreme Court judgments", "candidates": []}
    year = case.get("year") or year_of(case.get("citation") or "")
    keys = [k for k, _, _ in C.find_cites(case.get("citation") or "")]
    tol = 0 if any(k.startswith("insc:") for k in keys) else 1          # a neutral citation's year is the year of decision; a report's year may be the next one

    # 0. the court's own file for the judgment: .../judis/<id>.pdf is crawl id <id>
    m_id = re.search(r"/judis/(\d+)", case.get("source_url") or "")
    if m_id:
        d = corpus.get(f"c{m_id.group(1)}", with_text=False)
        if d:
            sc = name_score(name, d)
            if sc >= 0.5:
                return {"status": "MATCHED", "doc_key": d["doc_key"], "method": "source_url", "confidence": "high", "note": None, "candidates": [_slim(d, sc)]}
            return {"status": "AMBIGUOUS_MATCH", "doc_key": None, "method": "source_url", "confidence": None, "note": "the court-site file named in the library is a judgment with different names",
                    "candidates": [_slim(d, sc)]}

    # 1. a citation the judgment is known by, with names that agree
    by_key = {}
    for k in keys:
        for v in C.key_variants(k):
            for d in corpus.by_cite(v):
                by_key[d["doc_key"]] = d
    cite_docs = _drop_second_copies(list(by_key.values()))
    good = [d for d in cite_docs if name_score(name, d) >= 0.5]
    if len(good) == 1:
        return {"status": "MATCHED", "doc_key": good[0]["doc_key"], "method": "citation", "confidence": "high", "note": None, "candidates": [_slim(good[0], name_score(name, good[0]))]}
    if len(good) > 1:
        return {"status": "AMBIGUOUS_MATCH", "doc_key": None, "method": "citation", "confidence": None, "note": "the citation fits more than one judgment in the collection",
                "candidates": [_slim(d, name_score(name, d)) for d in good]}

    # 2. both parties' names and the year
    words = _query_words(name)
    found = {}
    for k in (4, 3, 2, 1):
        if not words:
            break
        rows = corpus.find_title(" ".join(words[:k]), 120)
        if year:
            rows = [d for d in rows if d.get("year") and abs(d["year"] - year) <= tol]
        if rows:
            found = {d["doc_key"]: d for d in rows}
            break
    scored = [(name_score(name, d), d) for d in _drop_second_copies(list(found.values()))]
    strong = [(s, d) for s, d in scored if s >= 0.8]
    if len(strong) > 1:
        top = max(s for s, _ in strong)
        best = [(s, d) for s, d in strong if s >= top - 1e-9]
        if year and len(best) > 1:
            gap = min(abs(d["year"] - year) for _, d in best)
            best = [(s, d) for s, d in best if abs(d["year"] - year) == gap]
        strong = best
    if len(strong) == 1:
        s, d = strong[0]
        conf = "high" if (s >= 0.999 and d.get("year") == year) else "medium"
        return {"status": "MATCHED", "doc_key": d["doc_key"], "method": "name_year", "confidence": conf, "note": None, "candidates": [_slim(d, s)]}
    if len(strong) > 1:
        return {"status": "AMBIGUOUS_MATCH", "doc_key": None, "method": "name_year", "confidence": None, "note": "more than one judgment has these parties in that year",
                "candidates": [_slim(d, s) for s, d in strong]}
    if cite_docs:
        return {"status": "AMBIGUOUS_MATCH", "doc_key": None, "method": "citation", "confidence": None, "note": "the citation fits a judgment whose title does not match the names",
                "candidates": [_slim(d, name_score(name, d)) for d in cite_docs]}
    near = sorted(scored, key=lambda x: -x[0])[:3]
    return {"status": "NOT_IN_COLLECTION", "doc_key": None, "method": None, "confidence": None, "note": "no judgment with these parties and year" if year else "no judgment with these parties",
            "candidates": [_slim(d, s) for s, d in near if s >= 0.5]}


def load_overrides(path):
    if path and os.path.exists(path):
        return {k: v for k, v in json.load(open(path, encoding="utf-8")).items() if not k.startswith("_")}
    return {}
