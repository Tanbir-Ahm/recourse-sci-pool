"""Tests for goodlaw/cites.py: reporter citations become comparable keys. Run: python test_goodlaw_cites.py"""
from goodlaw import cites as C

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


CASES = {
    "(2010) 11 SCC 441": ["scc:2010:11:441"],
    "1996 (2) SCC 1": ["scc:1996:2:1"],
    "AIR 1990 SC 1403": ["air:1990:1403"],
    "AIR 1962 SC 955": ["air:1962:955"],
    "1990 AIR 1403": ["air:1990:1403"],
    "1967 AIR  243": ["air:1967:243"],
    "1980 SC 898": ["air:1980:898"],
    "1980 SC898": ["air:1980:898"],
    "[2019] 5 S.C.R. 569": ["scr:2019:5:569"],
    "1966 SCR  209": ["scr:1966::209"],
    "1964 (5) SCR 89": ["scr:1964:5:89"],
    "2001 Supp(1) SCR 598": ["scr:2001:s1:598"],
    "2008 (8 )  SCR 1201": ["scr:2008:8:1201"],
    "1978 SCR (2) 621": ["scr:1978:2:621"],
    "[1976] Suppl. SCR 172": ["scr:1976:s:172"],
    "(1976) 2 SCC 521 : [1976] Suppl. SCR 172": ["scc:1976:2:521", "scr:1976:s:172"],
    "1978 SCR  (2)  621": ["scr:1978:2:621"],
    "2017 INSC 447": ["insc:2017:447"],
    "2017INSC447": ["insc:2017:447"],
    "(2015) 3 SCALE 28": ["scale:2015:3:28"],
    "JT 1999 (6) SC 89": ["jt:1999:6:89"],
    "(1994) 3 SCC (Cri) 569": ["scccri:1994:3:569"],
    "[2024] 12 S.C.R. 1436 : 2024 INSC 1039": ["scr:2024:12:1436", "insc:2024:1039"],
    "Rangappa v. Sri Mohan, (2010) 11 SCC 441 and Bhajan Lal, 1992 Supp (1) SCC 335": ["scc:2010:11:441", "scc:1992:s1:335"],
    "1992 Supp(1) SCC 335": ["scc:1992:s1:335"],
    "(1955) 1 SCR 1083": ["scr:1955:1:1083"],
    "[1992] 1 Suppl. SCR 764": ["scr:1992:s1:764"],
    "(1995) Supp. 1 SCC 80": ["scc:1995:s1:80"],
    "(1993) 4 Suppl. SCC 693: [1992] 1 Suppl. SCR 764": ["scc:1993:s4:693", "scr:1992:s1:764"],
    "1987 (Supp.) SCC 295": ["scc:1987:s:295"],
    "1995 SCC Supl. (3) 541": ["scc:1995:s3:541"],
    "1995 SCC (2) 560": ["scc:1995:2:560"],
    "2023 SCC OnLine SC 1308": ["sconline:2023:1308"],
    "(2022) SCC OnLine SC 883": ["sconline:2022:883"],
    "2009 SCC OnLine Delhi 2806": [],
    "2012 (4) SCALE 272": ["scale:2012:4:272"],
    "1996 SCALE (5) 267": ["scale:1996:5:267"],
    "[2008 (13) SCALE 372]": ["scale:2008:13:372"],
    "JT 2003 (Supp.1) SC 557": ["jt:2003:1:557"],
    "2021(10) JT 58": ["jt:2021:10:58"],
    "JT (2010) 12 SC 287": ["jt:2010:12:287"],
    "JT 1995 (6) 299": ["jt:1995:6:299"],
    "AIR (1968) SC 1012": ["air:1968:1012"],
    "(AIR (1959) SC 1012)": ["air:1959:1012"],
    "A.I.R. 1962 SC 955": ["air:1962:955"],
    "AIR 1958 Mad 398": [],
    "2006(XI) SCALE 440": ["scale:2006:11:440"],
    "(2021) SCC ONLINE SC 325": ["sconline:2021:325"],
    "JT 2000 (Suppl.3) SC 528": ["jt:2000:3:528"],
    "1995 AIR 2486 1995 SCC Supl. (3) 541 JT 1995 (6) 299 1995 SCALE (4)824": ["air:1995:2486", "scc:1995:s3:541", "jt:1995:6:299", "scale:1995:4:824"],
    "(1992) Supp (1) SCC 335": ["scc:1992:s1:335"],
    "(1999) 2 SCC 10 and AIR 1999 SC 1234": ["scc:1999:2:10", "air:1999:1234"],
}
for text, want in CASES.items():
    got = C.cite_keys(text)
    check(got == want, f"{text!r} -> {want}" + ("" if got == want else f" (got {got})"))

check(C.cite_keys("AIR 1990 Bom 123") == [] and C.cite_keys("1995 Cri LJ 100") == [] and C.cite_keys("AIR 1945 Privy Council 118") == [], "High Court reports and other series are not read")
check(C.cite_keys("SC No. 136/89 and SC 24") == [], "'SC' without a year before it is not a citation")
check(C.cite_keys("")== [] and C.norm_cite("no cite") is None, "empty or citation-free text gives nothing")
check(C.norm_cite("(2010) 11 SCC 441") == "scc:2010:11:441", "norm_cite gives the single key")
check(C.parse_key("scc:2010:11:441") == ("scc", 2010, "11", 441) and C.parse_key("air:1980:898") == ("air", 1980, "", 898) and C.parse_key("insc:2017:447") == ("insc", 2017, "", 447), "keys parse back")
check([x[0] for x in C.find_cites("see (2010) 11 SCC 441, para 5; AIR 1980 SC 898")] == ["scc:2010:11:441", "air:1980:898"], "find_cites keeps order and positions")
t = "see AIR 1980 SC 898 here"
k, s, e = C.find_cites(t)[0]
check(t[s:e] == "AIR 1980 SC 898", "find_cites gives the exact span of the citation")

check(C.key_variants("scr:1978:2:621") == {"scr:1978:2:621", "scr:1978::621", "scr:1978:s:621"} and C.key_variants("air:1980:898") == {"air:1980:898"}, "an SCR key with a volume also denotes the volume-less form")
check(C.keys_match("scr:1978::621", "scr:1978:2:621") and C.keys_match("scr:1976:s:172", "scr:1976:s1:172") and C.keys_match("scr:1976:s:172", "scr:1976::172") and not C.keys_match("scr:1976:s2:172", "scr:1976:s1:172") and not C.keys_match("scr:1978:3:621", "scr:1978:2:621") and not C.keys_match("scr:1978::621", "scr:1979:2:621") and C.keys_match("air:1980:898", "air:1980:898"),
      "keys_match treats a missing SCR volume as a wildcard, nothing else")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
