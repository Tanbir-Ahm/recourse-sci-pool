"""Tests for hc_labels.py (no network, costs nothing). Run: python test_hc_labels.py"""
import csv
import os
import re

import hc_labels as hl

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


# ---------------------------------------------------------------- real stored fields (public Gauhati High Court judgments), as they stand in the index
KOJANI = {"scope": "ghc_court", "court": "Gauhati High Court", "date": "2011-04-27", "path": "https://ghconline.gov.in/Judgment/CRLREVNSH332009.pdf",
          "url": "https://ghconline.gov.in/Judgment/CRLREVNSH332009.pdf", "title": "M/S KOJANI’S DHANKHETI THE HON’BLE MR JUSTICE T VAIPHEI Vs ",
          "citation": "CRL.REVN 33(SH)/2009 SHRI JOSE PULLAN @ JOSEPH P VS SMTI UMA JASRASARIA @ AGARWAL PROPRIETOR OF"}
RAJIB = {"scope": "ghc_court", "court": "Gauhati High Court", "date": "2017-08-04", "path": "https://ghconline.gov.in/Judgment/CrlRevP1542006.pdf",
         "url": "https://ghconline.gov.in/Judgment/CrlRevP1542006.pdf", "title": "RAJIB ALI Vs THE STATE OF ASSAM RANJAN PATHAK", "citation": "Crl.Rev.P. 154/2006"}
SARADA = {"scope": "ghc_post2017", "court": "Gauhati High Court", "date": "2023-08-29", "path": "data/pdf/year=2023/court=18_6/bench=asghccis/GAHC010172512018_1_2023-08-29.pdf",
          "url": "https://ghcservices.assam.gov.in/casestatus/pdfWatermark.php?file=2018/220900007702018_12.pdf", "title": "SARADA BAISHYA ANDF 2 ORS. Vs THE STATE OF ASSAM  AND ANR.", "citation": "Crl.Pet./770/2018"}
KOHIMA = {"scope": "ghc_post2017", "court": "Gauhati High Court", "date": "2026-07-23", "path": "data/pdf/year=2026/court=18_6/bench=nlghccis/GAHC01.pdf",
          "url": "https://ghcservices.assam.gov.in/casestatus/pdfWatermark.php?file=2025/x.pdf", "title": "SHRI MILAN A SHAH Vs STATE OF NAGALAND AND ANR", "citation": "Crl. Pet./43/2025"}

# ---------------------------------------------------------------- small helpers
check(hl.squash("  A   B \n C ") == "A B C" and hl.squash(None) == "", "squash collapses every run of white space and takes None")
check(hl.leaf("https://ghconline.gov.in/Judgment/Crl%20Rev%20P1542006.PDF") == "crlrevp1542006.pdf", "leaf is the file name of the address, lower case, without spaces")
check(hl.case_numbers("CRL.REVN 33(SH)/2009 SHRI JOSE PULLAN @ JOSEPH P VS SMTI UMA JASRASARIA") == "CRL.REVN 33(SH)/2009", "party names swallowed with a case number are cut off it")
check(hl.case_numbers("Crl.Pet. 79/2011 ; Crl.Pet. 154/2011 ; Crl.Pet. 79/2011") == "Crl.Pet. 79/2011 ; Crl.Pet. 154/2011", "several case numbers are kept once each, in order")
check(hl.case_numbers("Crl.Pet./770/2018") == "Crl.Pet./770/2018" and hl.case_numbers("W.P.(Crl.)/5/2019") == "W.P.(Crl.)/5/2019" and hl.case_numbers("CRL.A(J) 132/2005") == "CRL.A(J) 132/2005", "clean case numbers of every style pass through")
check(hl.case_numbers("Misc 12") == "Misc 12" and hl.case_numbers("") == "" and hl.case_numbers(None) == "", "a citation with no year, an empty one and None are left alone")

# ---------------------------------------------------------------- the bench
check([hl.court_file_bench(c, "A Vs B") for c in ("WP(C) 77(AT)/2010", "CRL.REVN 4(SH)/2009", "Crl.Pet. 21(AP)/2017", "W.P.(Crl.) 49(IM)/2011", "Crl.Rev.P. 6(K)/2016", "MACApp. 11(AZ)/2011")]
      == [("Agartala", "Tripura"), ("Shillong", "Meghalaya"), ("Itanagar", "Arunachal Pradesh"), ("Imphal", "Manipur"), ("Kohima", "Nagaland"), ("Aizawl", "Mizoram")],
      "each bracketed code names its bench")
check(hl.court_file_bench("CRL.A(J) 132/2005", "A Vs THE STATE OF ASSAM") == ("Guwahati", "Assam") and hl.court_file_bench("WP(C) 5/2014", "A Vs B") == ("Guwahati", "Assam"),
      "a case number without a bench code (the (J) and (C) are case types) is the principal seat")
check(hl.court_file_bench("Crl.Rev.P. 665/2004", "SUSHANTA SARKAR Vs THE STATE OF NAGALAND") is None, "no code and another state named: the bench is not guessed")
check(hl.court_file_bench("WP(C) 9(XY)/2010", "A Vs B") is None, "a bracketed code that is not a known bench is not guessed either")
check([hl.bench_of({"path": f"data/pdf/year=2019/court=18_6/bench={c}/x.pdf"}) for c in ("asghccis", "arghccis", "nlghccis", "azghccis", "zzghccis")]
      == [("Guwahati", "Assam"), ("Itanagar", "Arunachal Pradesh"), ("Kohima", "Nagaland"), ("Aizawl", "Mizoram"), None], "the bucket's file path names the bench; an unknown code does not")
check(hl.bench_of({"scope": "sci_newer", "path": "x"}) is None and hl.bench_of({"scope": "ghc_court", "citation": "Crl.A. 40(AT)/2003 SHRI X VS Y", "title": "T", "path": "https://x/y.pdf"}) == ("Agartala", "Tripura"),
      "a Supreme Court judgment has no bench here; a court file is read from its case number even when parties are stuck to it")
check(hl.bench_label("Guwahati", "Assam") == "principal seat, Guwahati" and hl.bench_label("Kohima", "Nagaland") == "Kohima bench (Nagaland)"
      and hl.bench_label("Shillong", "Meghalaya") == "Shillong bench (Meghalaya), until March 2013", "bench wording; the three benches that ended in 2013 say so")

# ---------------------------------------------------------------- clean_label
table = {"crlrevnsh332009.pdf": {"url": KOJANI["url"], "title": "SHRI JOSE PULLAN @ JOSEPH P Vs SMTI UMA JASRASARIA @ AGARWAL PROPRIETOR OF M/S KOJANI’S DHANKHETI", "case_number": "CRL.REVN 33(SH)/2009",
                                 "bench": "Shillong", "state": "Meghalaya"},
         "crlrevp1542006.pdf": {"url": RAJIB["url"], "title": "RAJIB ALI Vs THE STATE OF ASSAM", "case_number": "Crl.Rev.P. 154/2006", "bench": "Guwahati", "state": "Assam"}}
k = hl.clean_label(KOJANI, table)
check(k["title"].startswith("SHRI JOSE PULLAN") and "HON" not in k["title"] and k["case_no"] == "CRL.REVN 33(SH)/2009" and k["bench"] == "Shillong" and k["fixed"] is True
      and k["bench_label"] == "Shillong bench (Meghalaya), until March 2013" and k["court"] == "Gauhati High Court" and k["url"] == KOJANI["url"] and k["date"] == "2011-04-27", "a court file takes title, case number and bench from the table")
r = hl.clean_label(RAJIB, table)
check(r["title"] == "RAJIB ALI Vs THE STATE OF ASSAM" and r["fixed"] is True, "the judge's name that trailed the respondent is gone")
k2 = hl.clean_label(KOJANI, {})
check(k2["case_no"] == "CRL.REVN 33(SH)/2009" and k2["bench"] == "Shillong" and k2["title"] == hl.squash(KOJANI["title"]), "without a table row the title stays as stored, but the case number and bench are still mended")
s = hl.clean_label(SARADA, table)
check(s["title"] == "SARADA BAISHYA ANDF 2 ORS. Vs THE STATE OF ASSAM AND ANR." and s["case_no"] == "Crl.Pet./770/2018" and s["bench"] == "Guwahati" and s["fixed"] is False,
      "a judgment of 2018 on keeps its stored words (a typo in the source stays); only the double space is mended; the bench comes from the path")
check(hl.clean_label(KOHIMA, table)["bench_label"] == "Kohima bench (Nagaland)", "a Kohima bench judgment says so")
check(hl.clean_label({"scope": "ghc_court", "title": "A Vs B", "citation": "Crl.A. 1/2001", "date": "2012-01-01", "court": "Gauhati High Court"}, table)["url"] is None, "a record with no address does not break the lookup")

# ---------------------------------------------------------------- the table in the repository
real = hl.load_table()
rows = list(csv.DictReader(open(hl.TABLE, encoding="utf-8", newline="")))
check(len(rows) == 758 and len(real) == 758, "the table holds the 758 court files of 2010-2017")
check(not [x for x in rows if re.search(r"HON.?BLE|\bMR\.?\s*JUSTICE|CHIEF JUSTICE", x["title"], re.I)], "no title in the table carries a judge's honorific")
check(not [x for x in rows if not x["title"].strip() or x["title"].strip().startswith("Vs") or x["title"].strip().endswith("Vs")], "no title has an empty side")
check(not [x for x in rows if x["case_number"] != hl.case_numbers(x["case_number"])], "every case number in the table is only a case number")
check(sorted({x["how"] for x in rows}) == ["judge or subject words removed", "rebuilt from the case number text", "unchanged"], "every row says what was done to it")
check({x["bench"] for x in rows} == {"Guwahati", "Kohima", "Shillong", "Imphal", "Agartala", "Itanagar", ""}, "the benches named are the ones the court's case numbers carry")
real_k = hl.clean_label(KOJANI)
check(real_k["title"] == table["crlrevnsh332009.pdf"]["title"] and real_k["bench"] == "Shillong", "clean_label reads the repository's table when no table is passed")

# ---------------------------------------------------------------- card: what a page prints for one result
import tier_select as ts
PASSAGE = ("We have considered the submissions. We hold that a revision petition against an order framing charge does not lie where the order is interlocutory in nature, "
           "and the petitioner must raise the objection at the trial.")
res = ts.pick([{"doc": 7, "cos": 0.7, "text": PASSAGE, "src": KOJANI}])
check(len(res) == 1, "the sample passage survives the filter, so the card has a result to wrap")
c = hl.card(KOJANI, res[0])
check(c["heading"] == " · ".join((c["title"], "CRL.REVN 33(SH)/2009", "2011-04-27")) and c["bench_label"] == "Shillong bench (Meghalaya), until March 2013"
      and c["voice_line"] == res[0]["voice_line"] and c["quote"] == res[0]["authority"]["quote"] and c["url"] == KOJANI["url"] and c["also_decided_in"] == [],
      "card carries the heading, the bench, the link, the voice line and the quote of the result")
check(set(c) == {"heading", "court", "title", "case_no", "date", "bench_label", "url", "voice_line", "quote", "also_decided_in"}, "card has exactly the fields the patch notes list")
c2 = hl.card(SARADA, {"voice_line": "x", "authority": {"quote": "q"}, "also_in": [3, 4]})
check(c2["also_decided_in"] == [3, 4] and c2["bench_label"].startswith("principal seat"), "twins folded under a result are listed on its card")

# ---------------------------------------------------------------- the exported bundle works on its own, from an empty directory
import subprocess, sys, tempfile
import export_voice_bundle as ev
with tempfile.TemporaryDirectory() as out, tempfile.TemporaryDirectory() as work:
    files = ev.main(os.path.join(out, "passage_authority"))
    check(files == ["__init__.py", "authority.py", "court_file_labels.csv", "hc_labels.py", "textutil.py"], "the bundle holds five files")
    code = ("from passage_authority import hc_labels\n"
            "k = hc_labels.clean_label({'scope':'ghc_court','court':'Gauhati High Court','date':'2011-04-27','url':'https://ghconline.gov.in/Judgment/CRLREVNSH332009.pdf',"
            "'path':'https://ghconline.gov.in/Judgment/CRLREVNSH332009.pdf','title':'M/S KOJANI’S DHANKHETI THE HON’BLE MR JUSTICE T VAIPHEI Vs ','citation':'x'})\n"
            "print(k['bench'], '|', k['title'])")
    run = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, %r)\n" % out + code], cwd=work, capture_output=True, text=True)
    check(run.returncode == 0 and run.stdout.startswith("Shillong | SHRI JOSE PULLAN") and "HON" not in run.stdout, "the bundle, imported from an empty directory, gives the Shillong bench and the clean title: " + (run.stderr[-200:] or run.stdout[:80]))

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED:")
    for f in FAILURES:
        print("  -", f)
    raise SystemExit(1)
print("ALL PASSED")
