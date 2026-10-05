"""Tests for goodlaw/corpus.py (small synthetic crawl and bucket shards, no network). Run: python test_goodlaw_corpus.py"""
import csv
import gzip
import io
import json
import os
import shutil
import tempfile

from goodlaw import corpus as K

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def judis(pet, resp, date, bench, air, scr, body, citator=""):
    b = "\n".join(bench)
    return (f"http://JUDIS.NIC.IN\nSUPREME COURT OF INDIA\nPage 1 of 4\nPETITIONER:\n{pet}\n        Vs.\nRESPONDENT:\n{resp}\nDATE OF JUDGMENT:\n{date}\nBENCH:\n{bench[0]}\nBENCH:\n{b}\n"
            f"CITATION:\n {air}            {scr}\n{citator}ACT:\nSome Act.\nHEADNOTE:\nHeadnote words here that are not the court's.\nJUDGMENT:\n{body}\n")


def caption(pet, resp, body, tail):
    return f"IN THE SUPREME COURT OF INDIA\nCIVIL APPELLATE JURISDICTION\nCIVIL APPEAL NO. 5 OF 2009\n{pet}\n … Appellant\nVersus\n{resp}\n … Respondent\nJ U D G M E N T\n{body}\n{tail}"


LONG = " ".join(f"word{i}" for i in range(400))
LONG2 = " ".join(f"other{i}" for i in range(400))
CRAWL = {
    1: judis("A. K. GOPALAN", "STATE OF MADRAS", "19/05/1950", ["KANIA, C.J.", "FAZL ALI, S."], "1950 AIR 27", "1950 SCR 88", "The petition under Art. 32 fails. habeas corpus " + LONG),
    2: judis("MANEKA GANDHI", "UNION OF INDIA", "25/01/1978", ["BEG, M. HAMEEDULLAH (CJ)", "CHANDRACHUD, Y.V.", "BHAGWATI, P.N.", "UNTWALIA, N.L.", "KRISHNAIYER, V.R.", "FAZALALI, SYED MURTAZA", "KAILASAM, P.S."], "1978 AIR 597", "1978 SCR (2) 621",
             "Passport case. " + LONG2, citator=" CITATOR INFO :\n F          1980 SC 898  (15)\n O          1985 SC 1416  (3)\n"),
    3: caption("RAM LAL", "STATE OF U.P.", "R.V. RAVEENDRAN, J. The appeal is dismissed. " + LONG, "........................J.\n(R.V. RAVEENDRAN)\n........................J.\n(P. SATHASIVAM)\nNew Delhi;\nMarch 11, 2008."),
    4: caption("RAM LAL", "STATE OF U.P.", "R.V. RAVEENDRAN, J. The appeal is dismissed. " + LONG, "........................J.\n(R.V. RAVEENDRAN)\nNew Delhi;\nMarch 11, 2008."),            # a second copy of 3
    5: caption("RAM LAL", "STATE OF U.P.", "SOMEONE ELSE, J. A different appeal about a different land. " + LONG2, "New Delhi;\nMarch 12, 2008."),                                                # same parties, same year, different text
    6: caption("SHYAM", "KRISHNA", "J. The appeal is allowed. " + LONG, "the order dated 3.6.2005 was set aside. Appeal allowed.\nDated: 5 July 2008"),                                      # tail_any date: not trusted
    7: caption("GOPAL", "HARI", "J. Fine. " + LONG2, "New Delhi;\nApril 02, 2010."),
}
BUCKET = [
    dict(path="2019_5_569_578", title="STATE OF RAJASTHAN versus KANHAIYA LAL", petitioner="STATE OF RAJASTHAN", respondent="KANHAIYA LAL", decision_date="10-04-2019",
         citation="[2019] 5 S.C.R. 569", case_id="2019 INSC 510", nc_display="2019INSC510", judge="L. NAGESWARA RAO", scope="after",
         text="[L. NAGESWARA RAO AND HEMANT GUPTA, JJ.]\nHeadnote words.\nThe Judgment of the Court was delivered by\nNAGESWARA RAO, J. Leave granted. [2019] 5 S.C.R. 570 State of Rajasthan v. Kanhaiya Lal; as held in [2018] 3 S.C.R. 11 and (2010) 11 SCC 441. " + LONG),
    dict(path="1978_2_621_700", title="MANEKA GANDHI versus UNION OF INDIA", petitioner="MANEKA GANDHI", respondent="UNION OF INDIA", decision_date="25-01-1978",
         citation="[1978] 2 S.C.R. 621", case_id="1978 INSC 10", nc_display="1978INSC10", judge="", scope="none", text="Maneka text in bucket"),                    # also in crawl (yes)
    dict(path="1994_1_1_9", title="OLD ONE versus STATE", petitioner="OLD ONE", respondent="STATE", decision_date="01-02-1994", citation="[1994] 1 S.C.R. 1", case_id="1994 INSC 3",
         nc_display="", judge="", scope="none", text="A judgment the crawl lacks. " + LONG),
    dict(path="1995_1_1_9", title="MAYBE ONE versus STATE", petitioner="MAYBE ONE", respondent="STATE", decision_date="01-03-1995", citation="[1995] 1 S.C.R. 1", case_id="",
         nc_display="", judge="", scope="none", text="Maybe in the crawl. " + LONG2),
]


def write_gz(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write(text)


def csv_text(rows, cols):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


base = tempfile.mkdtemp(prefix="corpus_test_")
crawl_dir, bucket_dir = os.path.join(base, "crawl"), os.path.join(base, "bucket")
write_gz(os.path.join(crawl_dir, "shards", "000000-000249.ok7.gap0.err0.jsonl.gz"),
         "".join(json.dumps({"id": i, "status": "ok", "text": t, "pages": 3}) + "\n" for i, t in CRAWL.items()) + json.dumps({"id": 8, "status": "gap"}) + "\n")
by_scope = {}
for r in BUCKET:
    by_scope.setdefault(r["scope"], []).append(dict(r, status="ok", key="k", bytes=1, sha256="x", pages=2, scan_pages=0))
for scope, recs in by_scope.items():
    write_gz(os.path.join(bucket_dir, "shards", f"{scope}-0000.ok{len(recs)}.miss0.err0.jsonl.gz"), "".join(json.dumps(r) + "\n" for r in recs))
cols = ["decision_date", "title", "path", "tier", "citation", "case_id", "crawl_ids"]
reg = [dict(decision_date="25-01-1978", title="MANEKA GANDHI versus UNION OF INDIA", path="1978_2_621_700", tier="none", citation="[1978] 2 S.C.R. 621", case_id="1978 INSC 10", crawl_ids=""),
       dict(decision_date="19-05-1950", title="A.K. GOPALAN versus STATE OF MADRAS", path="1950_1_88_120", tier="T1", citation="[1950] 1 S.C.R. 88", case_id="1950 INSC 20", crawl_ids="1"),
       dict(decision_date="11-03-2008", title="RAM LAL versus STATE OF U.P.", path="2008_3_5_9", tier="T3", citation="[2008] 3 S.C.R. 5", case_id="2008 INSC 99", crawl_ids="3;4"),
       dict(decision_date="01-01-2000", title="AMBIGUOUS versus X", path="2000_1_1_9", tier="T3x", citation="", case_id="", crawl_ids="5;6")]
write_gz(os.path.join(base, "registry.csv.gz"), csv_text(reg, cols))
nr = [dict(path="1978_2_621_700", title="MANEKA GANDHI versus UNION OF INDIA", decision_date="25-01-1978", key="k", status="ok", best_crawl_id="2", shared_runs=300, frac=0.7, in_crawl="yes"),
      dict(path="1994_1_1_9", title="OLD ONE versus STATE", decision_date="01-02-1994", key="k", status="ok", best_crawl_id="", shared_runs=3, frac=0.0, in_crawl="no"),
      dict(path="1995_1_1_9", title="MAYBE ONE versus STATE", decision_date="01-03-1995", key="k", status="ok", best_crawl_id="7", shared_runs=60, frac=0.25, in_crawl="uncertain")]
write_gz(os.path.join(base, "none_resolution.csv.gz"), csv_text(nr, ["path", "title", "decision_date", "key", "status", "best_crawl_id", "shared_runs", "frac", "in_crawl"]))

out = os.path.join(base, "corpus.sqlite")
stats = K.build(crawl_dir, bucket_dir, os.path.join(base, "registry.csv.gz"), os.path.join(base, "none_resolution.csv.gz"), out, workers=1, log=lambda *_: None)
cp = K.Corpus(out)

check(stats["crawl"] == 7 and stats["bucket"] == 3, "7 crawled texts and 3 bucket texts are stored (the empty ID 8 and the Maneka copy the crawl already holds are not)")
check(cp.get("c8") is None and cp.get("b1978_2_621_700") is None, "a gap record and a bucket text the crawl already holds are left out")
check(stats["bucket_skipped_because_crawl_holds_them"] == 1, "the skip count is reported")

g = cp.get("c1")
check(g["date"] == "1950-05-19" and g["date_source"] == "bucket" and g["bucket_path"] == "1950_1_88_120" and g["insc"] == "1950 INSC 20" and g["scr_cite"] == "[1950] 1 S.C.R. 88",
      "a crawl text linked to a bucket row takes its exact date, neutral citation and law-report citation")
check("air:1950:27" in g["cites"] and "scr:1950::88" in g["cites"] and "insc:1950:20" in g["cites"], "its citation keys gather the header's AIR and SCR and the bucket's neutral citation")
check(g["pet"] == "A. K. GOPALAN" and g["resp"] == "STATE OF MADRAS" and g["title"] == "A. K. GOPALAN v. STATE OF MADRAS", "parties and title come from the header")
check(g["bench_size"] == 2 and g["bench_source"] == "header_full" and g["body_start"] is not None and g["text"][g["body_start"]:].strip().startswith("The petition"), "bench size and the start of the court's own words come from the JUDIS layout")
m = cp.get("c2")
check(m["bench_size"] == 7 and [c["code"] for c in m["citator"]] == ["F", "O"] and m["citator"][1]["cite"] == "1985 SC 1416" and m["scr_cite"] == "[1978] 2 S.C.R. 621",
      "a text the none-resolution marks 'yes' is linked to the crawl text, whose citator is kept")
check(m["date"] == "1978-01-25" and m["bucket_path"] == "1978_2_621_700", "and it carries the bucket's path and date")

# second copies
d3, d4, d5 = cp.get("c3", False), cp.get("c4", False), cp.get("c5", False)
check(d4["dup_of"] == "c3" and d3["dup_of"] is None, "two crawl texts with the same parties, year and body are copies; the longer one is read")
check(d5["dup_of"] is None, "a text with the same parties and year but a different body is not a copy")
check(stats["crawl_second_copies"] == 1, "one second copy is counted")
check(d3["date"] == "2008-03-11" and d3["date_source"] in ("tail_place", "bucket"), "a caption-layout text is dated from the end of the judgment (or the bucket link)")
check(d3["bench_size"] == 2 and d3["bench_source"] == "signatures", "its bench comes from the signature lines")

# dates that are not trusted, neighbour years
d6 = cp.get("c6", False)
check(d6["date"] is None and d6["date_source"] == "neighbours" and d6["year"] in (2008, 2010), "a date found only by 'the last date in the tail' is dropped and the year estimated from neighbouring ids")

# bucket-only
b1 = cp.get("b2019_5_569_578")
check(b1["source"] == "bucket" and b1["date"] == "2019-04-10" and b1["bench_size"] == 2 and b1["bench_source"] == "report_line" and "scr:2019:5:569" in b1["cites"] and "insc:2019:510" in b1["cites"],
      "a bucket-only text keeps its date, a bench read from the law report's line and its citations")
b2 = cp.get("b1994_1_1_9")
check(b2["maybe_dup_of"] is None and b2["source"] == "bucket", "a bucket text the crawl lacks is stored plainly")
b3 = cp.get("b1995_1_1_9")
check(b3["maybe_dup_of"] == "c7", "an uncertain one is stored and points at the crawl text it may duplicate")

# search
check([d["doc_key"] for d in cp.search('"habeas corpus"')] == ["c1"], "full-text phrase search finds the text")
check("c4" not in [d["doc_key"] for d in cp.search("word5")] and "c4" in [d["doc_key"] for d in cp.search("word5", canonical_only=False)], "searches skip second copies unless asked")
check([d["doc_key"] for d in cp.find_title("maneka gandhi")] == ["c2"], "title search finds the case")
check([d["doc_key"] for d in cp.by_cite("scr:2019:5:569")] == ["b2019_5_569_578"] and [d["doc_key"] for d in cp.by_cite("air:1950:27")] == ["c1"], "a citation key finds the judgment that bears it")
check(cp.stats()["docs"] == 10, "stats are kept in the store")
check(len(list(cp.iter_docs())) == 9, "iter_docs yields the 9 canonical texts")

# neighbour years need reliable dates around them
docs = [dict(id=i, date=f"{1990 + i // 10}-01-01" if i % 3 else None, date_source="header" if i % 3 else None) for i in range(1, 60)]
est = K.neighbour_years(docs)
check(all(est[i] == 1990 + i // 10 or abs(est[i] - (1990 + i // 10)) <= 1 for i in est) and len(est) == len([d for d in docs if not d["date"]]), "neighbour years follow the ids' dates")

# the citation index and lookups by citation
cp.con.close()
K.index_cites(out, workers=1, chunk=3, log=lambda *_: None)
cp = K.Corpus(out)
check(cp.has_cite_index, "the citation index file is found and attached")
check([d["doc_key"] for d in cp.docs_citing(["air:1950:27"])] == ["c1"], "docs_citing finds the text that bears the AIR citation in its header")
check([d["doc_key"] for d in cp.docs_citing(["scr:1978::621"])] == ["c2"] and [d["doc_key"] for d in cp.docs_citing(["scr:1978:2:621"])] == ["c2"], "an SCR citation matches with or without its volume")
check(cp.docs_citing(["scc:1999:9:9"]) == [], "a citation nobody has gives nothing")
check(cp.docs_citing(["scr:2019:5:570"]) == [] and [d["doc_key"] for d in cp.docs_citing(["scr:2018:3:11"])] == ["b2019_5_569_578"] and [d["doc_key"] for d in cp.docs_citing(["scc:2010:11:441"])] == ["b2019_5_569_578"],
      "a bucket text's own running page headers are not counted as citations, but the cases it cites are")
check(cp.doc_frequency("habeas") == 1 and cp.doc_frequency("nonexistentwordzz") == 0, "document frequency of a word comes from the full-text index")

cp.con.close()
shutil.rmtree(base, ignore_errors=True)
print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
