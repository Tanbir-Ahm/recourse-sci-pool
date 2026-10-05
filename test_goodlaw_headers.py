"""Tests for goodlaw/headers.py: parties, dates, bench, citations, the reporter's citator, body start. Run: python test_goodlaw_headers.py"""
from goodlaw import headers as H

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


# a real JUDIS header from the crawl (P.L. Lakhanpal v. Union of India, 1966), trimmed
LAKHANPAL = """http://JUDIS.NIC.IN
SUPREME COURT OF INDIA
Page 1 of 6
PETITIONER:
P.   L. LAKHANPAL
        Vs.
RESPONDENT:
UNION OF INDIA
DATE OF JUDGMENT:
19/04/1966
BENCH:
SARKAR, A.K. (CJ)
BENCH:
SARKAR, A.K. (CJ)
HIDAYATULLAH, M.
BACHAWAT, R.S.
SHELAT, J.M.
DAYAL, RAGHUBAR
CITATION:
 1967 AIR  243            1966 SCR  209
 CITATOR INFO :
 F          1967 SC 908  (1,5)
 OPN        1967 SC1507  (5)
 RF         1980 SC1789  (107)
 O          1980 SC 898  (15)
ACT:
Defence of India Rules, 1962 r. 30(1) (b)-If ultra vires.
HEADNOTE:
The petitioner, the editor of a newspaper, was detained.
HELD: Rule 30 (1) (b) cannot be said to be ultra vires.
JUDGMENT:
The Judgment of the Court was delivered by SARKAR, C.J.  This is a petition under Art. 32.
"""
pet, resp, lay = H.parse_parties(LAKHANPAL)
check((pet, resp, lay) == ("P. L. LAKHANPAL", "UNION OF INDIA", "judis"), "JUDIS header: parties are read and the trailing 'Vs.' is dropped")
check(H.parse_date(LAKHANPAL) == ("1966-04-19", "header"), "JUDIS header: DATE OF JUDGMENT on its own line is read")
check(H.bench_from_header(LAKHANPAL) == (5, ["SARKAR, A.K.", "HIDAYATULLAH, M.", "BACHAWAT, R.S.", "SHELAT, J.M.", "DAYAL, RAGHUBAR"]) or H.bench_from_header(LAKHANPAL)[0] == 5,
      "JUDIS header: the last BENCH: section gives five judges, the repeated presiding judge counted once")
check(H.parse_header_citations(LAKHANPAL)["air"] == ["1967 AIR 243"] and H.parse_header_citations(LAKHANPAL)["scr"] == ["1966 SCR 209"], "JUDIS header: AIR and SCR citations of the judgment itself")
cit = H.parse_citator(LAKHANPAL)
check([(c["code"], c["cite"], c["paras"]) for c in cit] == [("F", "1967 SC 908", "1,5"), ("OPN", "1967 SC 1507", "5"), ("RF", "1980 SC 1789", "107"), ("O", "1980 SC 898", "15")],
      "citator: codes, normalised cites (1967 SC1507 becomes 1967 SC 1507) and paragraph numbers")
check(cit[3]["meaning"] == "overruled" and cit[0]["meaning"] == "followed", "citator codes carry their meaning")
check(H.judis_body_start(LAKHANPAL) is not None and LAKHANPAL[H.judis_body_start(LAKHANPAL):].strip().startswith("The Judgment of the Court"), "the court's own judgment starts after the JUDGMENT: heading, past the reporter's headnote")
whole = H.parse_crawl(LAKHANPAL)
check(whole["bench_size"] == 5 and whole["bench_source"] == "header" and whole["layout"] == "judis", "parse_crawl: five judges from the header in the JUDIS layout")

check(H.parse_header_citations("CITATION:\n 1978 AIR  597            1978 SCR (2) 621\nACT:\n")["scr"] == ["1978 SCR (2) 621"], "a volume printed in the header is kept")

# 1995 to 2007 layout (Jasbir Singh v. Vipin Kumar Jaggi, 2001)
JASBIR = """http://JUDIS.NIC.IN
SUPREME COURT OF INDIA
Page 1 of 9
CASE NO.:
Appeal (crl.)  826-827 of 2001
PETITIONER:
JASBIR SINGH
RESPONDENT:
VIPIN KUMAR JAGGI AND ORS.
DATE OF JUDGMENT: 16/08/2001
BENCH:
G.B. PATTANA1K & RUMA PAL
JUDGMENT:
JUDGMENT
2001 Supp(1) SCR 598
The Judgment of the Court was delivered by RUMA PAL, J. Leave granted.
"""
check(H.parse_parties(JASBIR)[:2] == ("JASBIR SINGH", "VIPIN KUMAR JAGGI AND ORS"), "1995-2007 layout: parties after CASE NO.")
check(H.parse_date(JASBIR) == ("2001-08-16", "header"), "1995-2007 layout: date on the same line as DATE OF JUDGMENT")
check(H.bench_from_header(JASBIR)[0] == 2, "1995-2007 layout: two judges on one BENCH line split at '&'")
check(H.parse_header_citations(JASBIR)["scr"] == ["2001 Supp(1) SCR 598"], "1995-2007 layout: the single SCR line after JUDGMENT is read")

# captions of the later layouts
CAPTIONS = [
    ("IN THE SUPREME COURT OF INDIA\nCIVIL APPELLATE JURISDICTION\nCIVIL APPEAL NOS.1147-1151 OF 2009\n(arising out of SLP (C) Nos. 19361-19365 of 2005)\nState of Kerala & Anr.\n …Appellants\nVersus\nMahesh Kumar & Ors.\n …Respondents\nJUDGMENT\n",
     ("State of Kerala & Anr", "Mahesh Kumar & Ors")),
    ("Page 1\nJUDGMENT\n1\nNON-REPORTABLE\nIN THE SUPREME COURT OF INDIA\nCIVIL APPELLATE JURISDICTION\n CIVIL\n  APPEAL\n  NO(s).\n  4110\n  OF\n   2006\nUMA SASHI DEVI (DEAD) THROUGH LRS.               Appellant (s)\n                 VERSUS\nDIBAKAR BANERJEE AND OTHERS                       Respondent(s)\n     JUDGMENT\n",
     ("UMA SASHI DEVI (DEAD) THROUGH LRS", "DIBAKAR BANERJEE AND OTHERS")),
    ("Reportable\nIN THE SUPREME COURT OF INDIA\nCIVIL APPELLATE JURISDICTION\nCIVIL APPEAL NO.4561 OF 2008\nITC LTD.\n… Appellant\nVs.\nState of Uttar Pradesh & Ors.\n… Respondents\nWith Civil Appeal Nos.4562/2008\nJ U D G M E N T\n",
     ("ITC LTD", "State of Uttar Pradesh & Ors")),
    ("REPORTABLE\nIN THE SUPREME COURT OF INDIA\nCIVIL APPEAL NOs.  5321-5322                     OF 2013\n(ARISING OUT OF SLP(C) 13619-13620 OF 2012)\nSTATE OF GUJARAT & ORS.\n    … APPELLANTS\nVERUS\nPWD EMPLOYEES UNION & ORS. ETC.\n  … RESPONDENTS\nJ U D G M E N T\n",
     ("STATE OF GUJARAT & ORS", "PWD EMPLOYEES UNION & ORS. ETC")),
    ("IN THE SUPREME COURT OF INDIA\n CIVIL  APPELLATE JURISDICTION \nCIVIL APPEAL NO. 44  OF 2007\n   KHAJA SHARIFF & ORS.                           Appellant(s)\n                         :VERSUS:\n   B.H.E.L., HYDERABAD                            Respondent(s)\nO R D E R\n",
     ("KHAJA SHARIFF & ORS", "B.H.E.L., HYDERABAD")),
    ("2008 (8 )  SCR 1201\nA.P.S.R.T.C.& ANR.\nv.\nK. HEMALATHA & ORS.\n(Civil Appeal Nos.3623-3626 of 2008)\nMAY 16, 2008\n", ("A.P.S.R.T.C.& ANR", "K. HEMALATHA & ORS")),
]
for text, want in CAPTIONS:
    got = H.parse_parties(text)[:2]
    check(got == want, f"caption layout: {want[0]} v. {want[1]}" + ("" if got == want else f" (got {got})"))
check(H.parse_parties("#### garbage ####bjbjqPqP####")[0] is None, "an unreadable text gives no parties instead of a guess")

# dates at the end of later layouts
check(H.parse_date("... Appeal dismissed.\n\n......................J.\n(ARUN MISHRA)\nNew Delhi;\nMay 04, 2017.")[0] == "2017-05-04", "tail: date on the line after 'New Delhi;' is read")
check(H.parse_date("... dismissed.\nNew Delhi; January 10, 2007.\n")[0] == "2007-01-10" and H.parse_date("... dismissed.\nNew Delhi; January 10, 2007.\n")[1] == "tail_place", "tail: place line and date in one line")
check(H.parse_date("done.\nNEW DELHI\n10.01.2007\n")[0] == "2007-01-10", "tail: numeric date after the place")
check(H.parse_date("the order dated 3.6.2005 was set aside. Appeal allowed.\nDated: 12 March 2010")[0] == "2010-03-12", "tail: with no place line the last date in the tail is used")
check(H.parse_date("no date here at all")[0] is None, "no date gives None, not a guess")
check(H.to_iso("31", "02", "2010") is None, "an impossible date is rejected")

# bench from the law report line and signatures
PUTT = "[JAGDISH SINGH KHEHAR, CJI, J. CHELAMESWAR,\nS. A. BOBDE, R. K. AGRAWAL, R. F .. NARIMAN,\nABHAY MANOHAR SAPRE, DR. D. Y. CHANDRACHUD,\nSANJAY KISHAN KAUL AND S. ABDUL NAZEER, JJ.]\nThe Judgment of the Court was delivered by"
check(H.bench_from_report_line(PUTT)[0] == 9, "report line: nine judges of the privacy bench, 'AND' in capitals handled")
check(H.bench_from_report_line("[A. M. KHANWILKAR AND AJAY RASTOGI, JJ.]")[0] == 2, "report line: two judges")
check(H.bench_from_report_line("[Vikram Nath and Prasanna B. Varale,* JJ.]")[0] == 2, "report line: the author's asterisk is ignored")
check(H.bench_from_report_line("no bench line")[0] is None, "no report line gives None")
NAVTEJ = "379\nNAVTEJ SINGH JOHAR v. UOI THR. SECY. MINISTRY OF LAW & JUSTICE\n[DIPAK MISRA, CJI ]\n379\n[2018] 7 S.C.R. 379\nNAVTEJ SINGH JOHAR & ORS.\nv.\nUNION OF INDIA\nSEPTEMBER 06, 2018\n[DIPAK MISRA, CJI, R. F. NARIMAN,\nA. M. KHANWILKAR, DR. D.Y. CHANDRACHUD AND\nINDU MALHOTRA, JJ.]\nPenal Code, 1860"
check(H.bench_from_report_line(NAVTEJ)[0] == 5, "report line: a running header naming only the author does not hide the real bench line (five judges)")
check(H.bench_from_report_line("[JAGDISH SINGH KHEHAR, CJI, KURIAN JOSEPH,\nR. F. NARIMAN, UDAY .UMESH LALIT\nAND S. ABDUL NAZEER, JJ,j\nMAJORITY OPINION")[0] == 5, "report line: OCR damage to the closing bracket (JJ,j) is tolerated")
check(H.bench_from_report_line("[A. K. SIKRI, J.]")[0] == 1, "report line: a one-judge bench")
check(H.bench_from_report_line("DECEMBER 18, 1992\n(S. RATNAVEL PANDIAN AND K. JAYACHANDRA REDDY, JJ.]\nB")[0] == 2, "report line: an OCR-damaged opening bracket is tolerated")
SIGS = "...\n.......................J.\n(ARUN MISHRA)\n.......................J.\n(S. ABDUL NAZEER)\n.......................J.\n(M.R. SHAH)\nNew Delhi;\nMay 04, 2017."
check(H.bench_from_signatures(SIGS) == 3, "signatures: three signature lines make three judges")
check(H.bench_from_signatures("no signatures") is None, "no signatures give None")
check(H.bench_size(PUTT, "caption") == (9, "report_line"), "bench_size prefers the report line")

# the 'unknown code' path and non-citator text
check(H.parse_citator("PETITIONER:\nA\nRESPONDENT:\nB\nJUDGMENT:\nxxx") == [], "no citator block gives an empty list")
check(H.ADVERSE_CODES == {"O", "HO", "NF"}, "adverse citator codes are overruled, held overruled and not followed")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
