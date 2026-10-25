"""Tests for ghc/reparse_court_lists.py on a list drawn here, with the layout of the court's monthly lists (no network, costs nothing). Run: python test_reparse_court_lists.py"""
import importlib.util
import os
import tempfile

import pymupdf

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("reparse_court_lists", os.path.join(here, "ghc", "reparse_court_lists.py"))
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)

# columns as in the April 2011 list: serial 50, date 84, case 117, parties about 300 to 450, subject 458, judges 597
doc = pymupdf.open()
page = doc.new_page(width=842, height=595)
put = lambda x, y, t: page.insert_text((x, y), t, fontsize=8)
put(285, 30, "JUDGMENTS FOR THE MONTH OF APRIL, 2011")
put(49, 70, "Sl"); put(71, 70, "Date of"); put(117, 72, "CASE NO."); put(305, 72, "PARTIES' NAME"); put(458, 72, "SUBJECT"); put(597, 72, "JUDGMENT DELIVERED BY")
# row 1: the judges' names wrap onto lines of their own (the fault that put MADAN B. LOKUR and GOSWAMI after the respondent)
put(51, 120, "1"); put(84, 120, "5th"); put(117, 120, "CRL.A(J) 6/2005"); put(311, 108, "SHRI SUMAN RAJOWAR"); put(348, 117, "VS"); put(313, 126, "THE STATE OF ASSAM")
put(597, 94, "THE HON'BLE THE CHIEF JUSTICE MR"); put(597, 108, "MADAN B. LOKUR"); put(597, 122, "THE HON'BLE MR JUSTICE A K"); put(597, 135, "GOSWAMI")
# row 2: a bench in brackets in the case number (the fault that swallowed the parties into the case number), a subject, one judge
put(51, 200, "2"); put(84, 200, "6th"); put(117, 200, "WP(C) 77(AT)/2010"); put(324, 195, "SRI KRISHNA BHATTA"); put(348, 205, "VS"); put(313, 215, "THE STATE OF TRIPURA & ORS.")
put(458, 205, "Selection and appointment."); put(597, 205, "THE HON'BLE MR. JUSTICE B.K. SHARMA")
# row 3: the respondent in capitals, the judge's name set in the subject column, a petitioner called Justice
put(51, 280, "3"); put(84, 280, "7th"); put(117, 280, "Crl.Pet. 9/2009"); put(311, 270, "JUSTICE HARESWAR BARUAH (RETD.)"); put(348, 280, "VS"); put(313, 290, "MD. ALI & ORS.")
put(458, 285, "THE HON'BLE MR. JUSTICE T VAIPHEI")
page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(115, 112, 190, 124), "uri": "http://ghconline.gov.in/Judgment/CRLAJ62005.pdf"})
page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(115, 192, 200, 204), "uri": "http://ghconline.gov.in/Judgment/WPC772010.pdf"})
path = os.path.join(tempfile.mkdtemp(), "JDMTApr11.pdf")
doc.save(path)

year, month, rows, nlinks = rp.parse(path)
check((year, month, len(rows), nlinks) == (2011, 4, 3, 2), "the month, the three rows and the two links are found")
a, b, c = rows
check(a["case_number"] == "CRL.A(J) 6/2005" and a["petitioner"] == "SHRI SUMAN RAJOWAR" and a["respondent"] == "THE STATE OF ASSAM", "row 1: a judge's wrapped name is not part of the respondent")
check(a["judges"] == "THE HON'BLE THE CHIEF JUSTICE MR MADAN B. LOKUR | THE HON'BLE MR JUSTICE A K GOSWAMI", "row 1: each judge is whole, the wrapped names back with their honorific")
check(b["case_number"] == "WP(C) 77(AT)/2010" and b["petitioner"] == "SRI KRISHNA BHATTA" and b["respondent"] == "THE STATE OF TRIPURA & ORS.", "row 2: a bench in brackets does not swallow the parties")
check(b["subject"] == "Selection and appointment." and b["judges"] == "THE HON'BLE MR. JUSTICE B.K. SHARMA", "row 2: subject and judge are in their own columns")
check(c["petitioner"] == "JUSTICE HARESWAR BARUAH (RETD.)" and c["respondent"] == "MD. ALI & ORS." and c["judges"] == "THE HON'BLE MR. JUSTICE T VAIPHEI" and c["subject"] == "",
      "row 3: a petitioner called Justice stays a party; a judge's name set in the subject column goes to the judges")
check([r["date"] for r in rows] == ["2011-04-05", "2011-04-06", "2011-04-07"] and [r["serial"] for r in rows] == [1, 2, 3], "dates and serial numbers")
check(a["judgment_url"].endswith("CRLAJ62005.pdf") and b["judgment_url"].endswith("WPC772010.pdf") and c["judgment_url"] == "", "each link goes to the row whose case number it stands on")
check(rp.CASEPAT.search("77(AT)/2010") and rp.CASEPAT.search("6/2005") and not rp.CASEPAT.search("(AT)/2010"), "a case number may carry a bench in brackets")
check(rp.judges_of(["THE HON'BLE MR. JUSTICE I. A. ANSARI THE HON'BLE MR. JUSTICE P. K. MUSAHARY"]) == ["THE HON'BLE MR. JUSTICE I. A. ANSARI", "THE HON'BLE MR. JUSTICE P. K. MUSAHARY"],
      "two judges on one line are told apart, with 'THE' kept to its 'HON'BLE'")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED:")
    for f in FAILURES:
        print("  -", f)
    raise SystemExit(1)
print("ALL PASSED")
