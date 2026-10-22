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


def raises_(fn, *a):
    """None if fn(*a) returns, else the name of the exception it raised."""
    try:
        fn(*a)
    except Exception as e:                       # noqa: BLE001
        return type(e).__name__
    return None


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

# ---- the court's newer archive ------------------------------------------------------------------------------------------------------------------------------------------------------------
print("the newer archive")
first_ids = {k: cp.get(k, False)["id"] for k in ("c1", "c2", "c3", "c7", "b2019_5_569_578", "b1994_1_1_9", "b1995_1_1_9")}
n_before = cp.stats()["docs"]
cp.con.close()
REG, NONE = os.path.join(base, "registry.csv.gz"), os.path.join(base, "none_resolution.csv.gz")
ALPHA = " ".join(f"alpha{i}" for i in range(400))
BETA = " ".join(f"beta{i}" for i in range(400))
GAMMA = " ".join(f"gamma{i}" for i in range(400))
SOLO = " ".join(f"solo{i}" for i in range(400))


def newer(diary, date, pet, resp, text, in_bucket="no", bucket_title="", nc="", sha=None):
    return dict(pdf_url=f"https://court.example/supremecourt/{diary}_{date}.pdf", diary_no=diary, decision_date=date, case_name=f"{pet} versus {resp}", petitioner=pet, respondent=resp,
                case_number="CA 1 of 2018", neutral_citation=nc, reportable="REPORTABLE", pages=3, sha256=sha or f"sha-{diary}", in_bucket=in_bucket, bucket_title=bucket_title,
                source="Supreme Court of India (newer archive)", fetched_on="2026-10-21", text=text)


N1 = newer("100/2018", "2019-03-04", "NEW CASE", "STATE OF GOA", "[A, B AND C, JJ.]\nJ U D G M E N T\nzebraquartz was held. " + ALPHA + " as one of us (Aftab Alam, J.) held.\n........................J.\n(R.V. RAVEENDRAN)\n........................J.\n(P. SATHASIVAM)\nNew Delhi;",
         nc="2019 INSC 77", sha="same-file")
N2 = newer("200/2018", "2019-04-10", "STATE OF RAJASTHAN", "KANHAIYA LAL", "The court's own copy. " + BETA, in_bucket="yes", bucket_title="STATE OF RAJASTHAN v")
N3 = newer("101/2018", "2019-03-04", "NEW CASE", "STATE OF GOA", N1["text"], sha="same-file")
N4 = newer("300/2018", "2019-05-06", "SAME PARTY", "OTHER SIDE", "Appeal allowed. " + GAMMA)
N5 = newer("301/2018", "2019-05-06", "SAME PARTY", "OTHER SIDE", "Appeal allowed. " + GAMMA + " one more closing sentence added by the reporter.")
N6 = newer("302/2018", "2019-09-09", "SAME PARTY", "OTHER SIDE", "Appeal allowed. " + GAMMA + " one more closing sentence added by the reporter.")
N7 = newer("400/2018", "2019-04-10", "STATE OF RAJASTHAN", "KANHAIYA LAL", "A different judgment the same day between the same parties. " + SOLO)
N9 = newer("600/2018", "2019-12-12", "NOWHERE", "STATE", "The archive says the bucket holds it but none fits. " + ALPHA + " nowhere", in_bucket="yes", bucket_title="NOWHERE")
newer_dir = os.path.join(base, "newer")


def write_newer(recs):
    shutil.rmtree(newer_dir, ignore_errors=True)
    by_month = {}
    for r in recs:
        by_month.setdefault(r["decision_date"][:7], []).append(r)
    for month, rs in by_month.items():
        write_gz(os.path.join(newer_dir, "shards", f"{month}.jsonl.gz"), "".join(json.dumps(r) + "\n" for r in rs))


def build_with(recs, name, nd=None):
    if recs is not None:
        write_newer(recs)
    return K.build(crawl_dir, bucket_dir, REG, NONE, os.path.join(base, name), workers=1, log=lambda *_: None, newer_dir=nd or newer_dir)


st2 = build_with([N1, N2, N3, N4, N5, N6, N7, N9], "corpus2.sqlite")
c2 = K.Corpus(os.path.join(base, "corpus2.sqlite"))
check(all(c2.get(k, False)["id"] == i for k, i in first_ids.items()) and st2["docs"] == n_before + 8, "the 8 newer texts are added after every other row: no row that was already there changed its id")
check(st2["court"] == 8 and st2["court_copies_of_bucket"] == 1 and st2["court_second_copies_inside"] == 2 and st2["court_judgments"] == 5 and st2["court_uncertain"] == 1,
      "all 8 are stored: 1 is a copy of a bucket text, 2 are second copies inside the archive, 5 are judgments, 1 of those uncertain")
n1 = c2.get("n100_2018_2019-03-04")
check(n1["source"] == "court" and n1["layout"] == "court" and n1["date"] == "2019-03-04" and n1["date_source"] == "court" and n1["year"] == 2019 and n1["dup_of"] is None and n1["maybe_dup_of"] is None,
      "a text the bucket lacks is stored as a judgment of its own, dated from the archive")
check(n1["title"] == "NEW CASE versus STATE OF GOA" and n1["pet"] == "NEW CASE" and n1["resp"] == "STATE OF GOA" and n1["insc"] == "2019 INSC 77" and n1["cites"] == ["insc:2019:77"] and n1["src_id"].endswith("100/2018_2019-03-04.pdf"),
      "its title, parties, neutral citation (as a citation key) and the court's link are kept")
check(n1["text_len"] == len(N1["text"]) and n1["text"] == N1["text"], "its text is stored whole")
check(n1["bench_size"] == 2 and n1["bench_source"] == "signatures", "its bench is the signature lines' count, a lower bound: a bracketed judge list or 'one of us (Name' in the body is not read as a complete bench")
check(c2.get("n600_2018_2019-12-12", False)["bench_size"] is None and c2.get("n600_2018_2019-12-12", False)["bench_source"] is None, "a text with no signature lines has no bench size")
n2 = c2.get("n200_2018_2019-04-10", False)
check(n2["dup_of"] == "b2019_5_569_578" and n2["bucket_path"] == "2019_5_569_578" and n2["maybe_dup_of"] is None, "a text the archive marks as in the bucket is a second copy of the bucket text it names (found by date and the cut-off title)")
check(c2.get("n101_2018_2019-03-04", False)["dup_of"] == "n100_2018_2019-03-04", "the same file under another diary number is a second copy of the first")
n4, n5, n6 = (c2.get(k, False) for k in ("n300_2018_2019-05-06", "n301_2018_2019-05-06", "n302_2018_2019-09-09"))
check(n5["dup_of"] is None and n4["dup_of"] == n5["doc_key"], "two texts with the same parties, the same decision date and nearly the same body are copies; the longer is read")
check(n6["dup_of"] is None, "the same parties and body on a different decision date are not copies")
n7 = c2.get("n400_2018_2019-04-10", False)
check(n7["dup_of"] is None and n7["maybe_dup_of"] == "b2019_5_569_578", "a text marked 'no' that has a bucket text of the same date and parties stays a judgment but is flagged")
n9 = c2.get("n600_2018_2019-12-12", False)
check(n9["dup_of"] is None and n9["maybe_dup_of"] is None, "a 'yes' that fits no bucket text is stored plainly")
check([d["doc_key"] for d in c2.search("zebraquartz")] == ["n100_2018_2019-03-04"] and sorted(d["doc_key"] for d in c2.search("zebraquartz", canonical_only=False)) == ["n100_2018_2019-03-04", "n101_2018_2019-03-04"],
      "full-text search finds a newer-archive text, and the archive's second copies only when asked")
check([d["doc_key"] for d in c2.by_cite("insc:2019:77")] == ["n100_2018_2019-03-04"] and [d["doc_key"] for d in c2.find_title("new case goa")] == ["n100_2018_2019-03-04"], "a newer text is found by its neutral citation and by its title")
check(len(list(c2.iter_docs("source='court' AND dup_of IS NULL"))) == 5 and len(list(c2.iter_docs())) == 9 + 5, "five newer-archive judgments are counted, on top of the nine already there")
c2.con.close()

# two more cases that need more fixtures: a bucket day with two titles that share a start, and a crawl text dated inside the days both archives cover
write_gz(os.path.join(crawl_dir, "shards", "000250-000499.ok1.gap0.err0.jsonl.gz"),
         json.dumps({"id": 300, "status": "ok", "pages": 2, "text": judis("OVERLAP PET", "OVERLAP RESP", "03/05/2017", ["A, J."], "2017 AIR 9", "2017 SCR 9", "A body. " + LONG)}) + "\n")
extra = [dict(path="2019_9_1_9", title="TWIN ALPHA versus STATE", petitioner="TWIN ALPHA", respondent="STATE", decision_date="11-11-2019", citation="[2019] 9 S.C.R. 1", case_id="2019 INSC 901",
              nc_display="", judge="", scope="after", text="[A AND B, JJ.]\nTwin alpha text. " + LONG),
         dict(path="2019_9_10_19", title="TWIN BETA versus STATE", petitioner="TWIN BETA", respondent="STATE", decision_date="11-11-2019", citation="[2019] 9 S.C.R. 10", case_id="2019 INSC 902",
              nc_display="", judge="", scope="after", text="[A AND B, JJ.]\nTwin beta text. " + LONG2)]
write_gz(os.path.join(bucket_dir, "shards", "after-0001.ok2.miss0.err0.jsonl.gz"), "".join(json.dumps(dict(r, status="ok", key="k", bytes=1, sha256="x", pages=2, scan_pages=0)) + "\n" for r in extra))
N8 = newer("500/2018", "2019-11-11", "TWIN GAMMA", "STATE", "The archive says the bucket holds it but two bucket texts fit. " + SOLO + " twin", in_bucket="yes", bucket_title="TWIN")
N10 = newer("500/2017", "2017-05-03", "OVERLAP PET", "OVERLAP RESP", "A text of the days both archives cover. " + BETA + " overlap")
N11 = newer("700/1978", "1978-01-25", "MANEKA GANDHI", "UNION OF INDIA", "The archive says the bucket holds it, but the store keeps the crawl's text. " + GAMMA + " maneka", in_bucket="yes", bucket_title="MANEKA GANDHI")
SAME_BYTES = "One file the court served under two diary numbers, and with two different dates. " + SOLO + " bytes"
N12 = newer("800/2018", "2019-06-01", "FILE ONE", "STATE", SAME_BYTES, sha="same-bytes")
N13 = newer("801/2018", "2019-06-02", "FILE TWO", "STATE", SAME_BYTES, sha="same-bytes")
N14 = newer("200/2019", "2019-04-10", "STATE OF RAJASTHAN", "KANHAIYA LAL", "The court's copy of a bucket judgment. " + BETA + " b", in_bucket="yes", bucket_title="STATE OF RAJASTHAN v", sha="bytes-b")
N15 = newer("100/2019", "2019-04-11", "OTHER NAME", "OTHER", "The court's copy of a bucket judgment. " + BETA + " b", sha="bytes-b")
st3 = build_with([N8, N10, N11, N12, N13, N14, N15], "corpus3.sqlite")
c3 = K.Corpus(os.path.join(base, "corpus3.sqlite"))
n8, n10 = c3.get("n500_2018_2019-11-11", False), c3.get("n500_2017_2017-05-03", False)
check(n8["dup_of"] is None and n8["maybe_dup_of"] == "b2019_9_10_19" and n8["bucket_path"] is None, "a 'yes' that fits two bucket texts is flagged against the first by path and not claimed as a copy")
check(n10["dup_of"] is None and n10["maybe_dup_of"] == "c300", "a text dated inside the days the crawl also covers is flagged against the crawl text with the same date and parties")
n11 = c3.get("n700_1978_1978-01-25", False)
check(n11["dup_of"] is None and n11["bucket_path"] is None and n11["maybe_dup_of"] == "c2", "a link to a bucket text the store does not hold is not made; the crawl text with the same date and parties is flagged instead")
c12, c13, c14, c15 = (c3.get(k, False) for k in ("n800_2018_2019-06-01", "n801_2018_2019-06-02", "n200_2019_2019-04-10", "n100_2019_2019-04-11"))
check(c12["dup_of"] is None and c13["dup_of"] == c12["doc_key"], "a file served under two diary numbers is one judgment even when the parties and dates differ")
check(c14["dup_of"] == "b2019_5_569_578" and c15["dup_of"] == "b2019_5_569_578", "and when one of them is a copy of a bucket text, the other is a copy of that bucket text too")
check(st3["court"] == 7 and st3["court_copies_of_bucket"] == 2 and st3["court_second_copies_inside"] == 1 and st3["court_judgments"] == 4 and st3["court_uncertain"] == 3 and st3["crawl"] == 8 and st3["bucket"] == 5, "the counts for this build say so")
c3.con.close()

# copies the archive's own marker missed: a day's difference, another spelling, a text that shares only part of its words
WORDS = lambda lo, hi: " ".join(f"word{i}" for i in range(lo, hi))        # the words LONG is made of (the bucket text of 2019_5_569_578 contains them all)
C1 = newer("900/2019", "2019-04-11", "STATE OF RAJASTHAN", "KANHAIYALAL", "NAGESWARA RAO, J. Leave granted. " + LONG)
C2 = newer("901/2019", "2019-04-12", "UNRELATED NAME", "OTHER SIDE", "Completely other heading. " + LONG)
C3 = newer("902/2019", "2019-04-11", "STATE OF RAJASTHAN", "KANHAIYA LAL", "Another heading. " + WORDS(0, 170) + " " + SOLO)
C4 = newer("903/2019", "2019-04-11", "STATE OF RAJASTHAN", "KANHAIYA LAL", "Another heading. " + WORDS(0, 120) + " " + SOLO.replace("solo", "sola"))
C5 = newer("904/2019", "2019-04-14", "STATE OF RAJASTHAN", "KANHAIYA LAL", "A heading. " + LONG)
C6 = newer("905/2019", "2019-04-11", "STATE OF RAJASTHAN", "KANHAIYA LAL", "A heading. " + SOLO.replace("solo", "solu"))
C7 = newer("906/2019", "2019-04-11", "UNRELATED NAME", "OTHER SIDE", "Another heading. " + WORDS(0, 120) + " " + SOLO.replace("solo", "solb"))
C8 = newer("907/2019", "2019-04-10", "STATE OF RAJASTHAN", "KANHAIYA LAL", "NAGESWARA RAO, J. Leave granted. " + LONG)
st4 = build_with([C1, C2, C3, C4, C5, C6, C7, C8], "corpus4.sqlite")
c4 = K.Corpus(os.path.join(base, "corpus4.sqlite"))
t1, t2, t3, t4, t5, t6 = (c4.get(k, False) for k in ("n900_2019_2019-04-11", "n901_2019_2019-04-12", "n902_2019_2019-04-11", "n903_2019_2019-04-11", "n904_2019_2019-04-14", "n905_2019_2019-04-11"))
check(t1["dup_of"] == "b2019_5_569_578" and t1["bucket_path"] == "2019_5_569_578", "a text the archive calls new, with another spelling of the names and a bucket date a day earlier, is a copy when it shares its words with the bucket text")
check(t2["dup_of"] == "b2019_5_569_578", "the names do not matter when the text shares at least half its 8-word runs")
check(t3["dup_of"] == "b2019_5_569_578", "a text that shares a third of its runs is a copy when the title agrees")
check(t4["dup_of"] is None and t4["maybe_dup_of"] == "b2019_5_569_578", "a text that shares a quarter of its runs and has an agreeing title is flagged and stays a judgment")
check(t5["dup_of"] is None and t5["maybe_dup_of"] is None, "the same words four days away are not matched")
check(t6["dup_of"] is None and t6["maybe_dup_of"] is None, "the same parties a day away with different words are not matched")
t7, t8 = c4.get("n906_2019_2019-04-11", False), c4.get("n907_2019_2019-04-10", False)
check(t7["dup_of"] is None and t7["maybe_dup_of"] is None, "a quarter of the runs with a title that does not agree is not enough to flag")
check(t8["dup_of"] == "b2019_5_569_578" and t8["maybe_dup_of"] is None, "a text first flagged by its names and then found to be a copy by its words is a copy, with the flag cleared")
check(st4["court"] == 8 and st4["court_copies_found_by_text"] == 4 and st4["court_copies_of_bucket"] == 4 and st4["court_judgments"] == 4 and st4["court_uncertain"] == 1, "the counts for this build say so")
c4.con.close()

# refusals
check(raises_(build_with, None, "x.sqlite", os.path.join(base, "no_such_dir")) == "FileNotFoundError", "a newer-archive folder that does not exist is refused")
write_newer([dict(N1, in_bucket="maybe")])
check(raises_(K.read_newer, newer_dir) == "ValueError", "an in_bucket value the archive does not define is refused")
write_newer([N1, dict(N1, pdf_url="https://court.example/other.pdf", sha256="other", text="x " + ALPHA)])
check(raises_(build_with, None, "y.sqlite") == "ValueError", "two records with one diary number and decision date are refused")

cp.con.close()
shutil.rmtree(base, ignore_errors=True)
print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
