#!/usr/bin/env python3
"""What a page shows to name a Guwahati High Court judgment: court, bench, title, case number, date, link. Reads the stored fields of the index (the `src` of a docs row);
never invents a word. No network, no cost.

Three faults of the stored fields are mended here, not in the index (nothing in the index is rewritten):
  * the 758 court files of 2010-2017 (scope ghc_court) were stored with the title and case number as ghc/parse_court_lists.py read them, which left a judge's name after the
    respondent, or the statute's year, in 385 of them and swallowed the parties into the case number in 18 more (ghc/reparse_court_lists.py reads the lists by position;
    ghc/build_court_file_labels.py turns that into ghc/court_lists/court_file_labels.csv, which clean_label looks up by the judgment's address);
  * the bench was never shown: it is in the bucket's file path (bench=nlghccis ...) for the judgments of 2018 on and for part of the earlier ones, and in the bracketed code of
    the court's own case numbers (77(AT)/2010) for the court files;
  * double spaces in titles.
"""
import csv, os, re, urllib.parse

COURT = "Gauhati High Court"
TABLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ghc", "court_lists", "court_file_labels.csv")
BENCH_PATH = {"asghccis": ("Guwahati", "Assam"), "arghccis": ("Itanagar", "Arunachal Pradesh"), "nlghccis": ("Kohima", "Nagaland"), "azghccis": ("Aizawl", "Mizoram")}   # the bucket's file path; each checked against the state named in the titles
BENCH_SUFFIX = {"K": ("Kohima", "Nagaland"), "AP": ("Itanagar", "Arunachal Pradesh"), "AZ": ("Aizawl", "Mizoram"), "SH": ("Shillong", "Meghalaya"), "AT": ("Agartala", "Tripura"), "IM": ("Imphal", "Manipur")}   # the code in a case number of the court's lists
FORMER = {"Shillong", "Agartala", "Imphal"}     # benches that ended on 23 March 2013, when Meghalaya, Tripura and Manipur got High Courts of their own
OTHER_STATE = re.compile(r"NAGALAND|MIZORAM|ARUNACHAL|MEGHALAYA|MANIPUR|TRIPURA|AGARTALA|SHILLONG|IMPHAL|KOHIMA|AIZAWL|ITANAGAR", re.I)
CASE_NO = re.compile(r"^(.*?\d+\s*(?:\(\s*[A-Za-z]+\s*\))?\s*/\s*\d{4})\b")
SUFFIX = re.compile(r"\d+\s*\(\s*([A-Za-z]+)\s*\)\s*/\s*\d{4}")
_tables = {}


def squash(s):
    return re.sub(r"\s+", " ", s or "").strip()


def leaf(url):
    """The file name of a judgment's address, the key ghc/store_court_files.py uses."""
    return re.sub(r"\s+", "", urllib.parse.unquote(url.rsplit("/", 1)[-1])).lower()


def case_numbers(citation):
    """The case numbers of a stored citation, each cut where the party names that were swallowed with it begin: 'CRL.REVN 33(SH)/2009 SHRI JOSE PULLAN VS ...' -> 'CRL.REVN 33(SH)/2009'."""
    out = []
    for seg in (citation or "").split(" ; "):
        m = CASE_NO.match(squash(seg)); n = m.group(1).strip() if m else squash(seg)
        if n and n not in out: out.append(n)
    return " ; ".join(out)


def court_file_bench(case_no, title):
    """(bench, state) of a 2010-2017 court file, or None. The bracketed code names an outstation bench. A case number without one was heard at the principal seat in Guwahati
    (of the 5,049 such list rows the bucket also holds, 5,042 are Assam bench and 7 Arunachal), unless the parties name another state."""
    m = SUFFIX.search(case_no or "")
    if m: return BENCH_SUFFIX.get(m.group(1).upper())
    return None if OTHER_STATE.search(title or "") else ("Guwahati", "Assam")


def bench_of(src, title=None):
    """(bench, state) from the bucket's file path, else from the case number of a court file; None when neither says."""
    m = re.search(r"bench=([a-z0-9]+)", src.get("path") or "")
    if m: return BENCH_PATH.get(m.group(1))
    if src.get("scope") == "ghc_court": return court_file_bench(case_numbers(src.get("citation")), src.get("title") if title is None else title)
    return None


def bench_label(bench, state):
    return "principal seat, Guwahati" if bench == "Guwahati" else f"{bench} bench ({state})" + (", until March 2013" if bench in FORMER else "")


def load_table(path=TABLE):
    """{file name of the judgment's address: row} from court_file_labels.csv; {} when the file is absent."""
    if path not in _tables:
        _tables[path] = {leaf(r["url"]): r for r in csv.DictReader(open(path, encoding="utf-8", newline=""))} if os.path.exists(path) else {}
    return _tables[path]


def clean_label(src, table=None):
    """{"court", "title", "case_no", "date", "url", "bench", "state", "bench_label", "fixed"} for the `src` of a docs row. A court file takes its title, case number and bench from the
    table (the lists read by position); every other judgment keeps its stored title and case number with the spaces mended. `fixed` is True when the title or case number differs from the stored one by more than spaces."""
    t = (load_table() if table is None else table).get(leaf(src["url"])) if src.get("scope") == "ghc_court" and src.get("url") else None
    if t: title, case_no, b = t["title"], t["case_number"], ((t["bench"], t["state"]) if t["bench"] else None)
    else:
        title = squash(src.get("title")); case_no = case_numbers(src.get("citation")) if src.get("scope") == "ghc_court" else squash(src.get("citation")); b = bench_of(src, title)
    return {"court": src.get("court") or COURT, "title": title, "case_no": case_no, "date": src.get("date"), "url": src.get("url"), "bench": b[0] if b else None, "state": b[1] if b else None,
            "bench_label": bench_label(*b) if b else None, "fixed": squash(src.get("title")) != title or squash(src.get("citation")) != case_no}
