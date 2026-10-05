"""Tests for goodlaw/library.py: the library's cases and which judgment in the collection each one is. Run: python test_goodlaw_library.py"""
import re

from goodlaw import library as L

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


class FakeCorpus:
    """Just the three lookups the matcher uses."""
    def __init__(self, docs):
        self.docs = {d["doc_key"]: d for d in docs}

    def get(self, doc_key, with_text=True):
        return self.docs.get(doc_key)

    def by_cite(self, key):
        return [d for d in self.docs.values() if key in d.get("cites", [])]

    def find_title(self, query, limit=20):
        words = re.findall(r"[A-Za-z0-9]+", query.lower())
        return [d for d in self.docs.values() if all(w in d["title"].lower() for w in words)][:limit]


def doc(key, title, year, cites=(), **kw):
    d = {"doc_key": key, "title": title, "year": year, "date": f"{year}-06-01", "cites": list(cites), "bench_size": 3, "maybe_dup_of": None}
    d.update(kw)
    return d


CORPUS = FakeCorpus([
    doc("c1", "RANGAPPA versus SRI MOHAN", 2010, ["scr:2010:6:507"]),
    doc("c2", "STATE OF PUNJAB versus BALDEV SINGH", 1999, ["scr:1999:3:977"]),
    doc("c3", "STATE OF PUNJAB versus BALDEV SINGH", 2006),                      # same names, another year
    doc("b4", "MOHANLAL versus THE STATE OF PUNJAB", 2018, ["scr:2018:9:1006", "insc:2018:578"]),
    doc("b5", "UNION OF INDIA versus MOHANLAL", 2016),
    doc("c6", "SIDDHARAM SATLINGAPPA MHETRE versus STATE OF MAHARASHTRA & ORS", 2010, ["scr:2010:15:1"]),
    doc("c7", "ARNESH KUMAR versus STATE OF BIHAR & ANR", 2014, ["scr:2014:7:1"]),
    doc("c8", "GAMMA TRADERS versus DELTA BANK", 2012),
    doc("c9", "GAMMA TRADERS versus DELTA BANK", 2012),                          # two judgments with the same parties in the same year
    doc("c10", "ALPHA STEELS versus BETA FINANCE", 2011, ["scr:2011:1:77"]),
    doc("b11", "ALPHA STEELS versus BETA FINANCE", 2011, [], maybe_dup_of="c10"),    # a bucket text that may be a second copy of c10
    doc("c12", "ZETA MILLS versus ETA UNION", 2000, ["scr:2000:2:55"]),         # carries the citation, but the names differ from what the library says
    doc("b13", "KAVERI PLASTICS versus MAHDOOM BAWA BAHRUDEEN NOORUL", 2025, ["insc:2025:1133"]),
    # the D.K. Basu trap: the right judgment is dated a year before the citation's year, and other judgments with a 'Basu' party sit in the citation's year
    doc("c14", "SHRI D.K. BASU,ASHOK K. JOHRI v. STATE OF WEST BENGAL,STATE OF U.P", 1996, [], pet="SHRI D.K. BASU,ASHOK K. JOHRI", resp="STATE OF WEST BENGAL,STATE OF U.P"),
    doc("c15", "THE STATE OF WEST BENGAL & ANR v. ARUN KUMAR BASU & ANR", 1997),
    doc("c16", "SHRI DILIP K. BASU ETC. v. STATE OF WEST BENGAL & ORS", 1997),
    # abbreviations in the corpus title
    doc("c17", "Lata Singh v. State of U.P. & Another", 2006),
    doc("c18", "Lalita Kumari v. Govt. of U.P. & Ors", 2013),
    # the same parties decided again a year later (a neutral citation names the year exactly)
    doc("b19", "SATENDER KUMAR ANTIL versus CENTRAL BUREAU OF INVESTIGATION", 2025),
    # a judgment the library names by the court's own file
    doc("c29675", "All Cargo Movers (I) Pvt. Ltd. & Ors v. Dhanesh Badarmal Jain & Anr", 2007),
    doc("c777", "COMPLETELY DIFFERENT PARTIES v. SOMEONE ELSE", 1990),
])


def case(name, citation, court=None, **kw):
    c = {"case_name": name, "citation": citation, "court": court, "source_url": ""}
    c.update(kw)
    c["court_class"] = L.court_class(c)
    c["year"] = L.year_of(citation)
    return c


# ---- classification and parsing
check(L.court_class({"court": "Supreme Court of India"}) == "SC" and L.court_class({"court": "Supreme Court of India (Constitution Bench)"}) == "SC", "a court named 'Supreme Court' is SC")
check(L.court_class({"court": "High Court of Delhi"}) == "HC" and L.court_class({"court": "Kerala High Court"}) == "HC" and L.court_class({"court": "Ministry of Home Affairs"}) == "OTHER", "a High Court is HC; a gazette is neither")
check(L.court_class({"citation": "2026 SCC OnLine Del 297"}) == "HC" and L.court_class({"citation": "2025 SCC OnLine Mad (MD) 12"}) == "HC" and L.court_class({"citation": "2023 SCC OnLine SC 90"}) == "SC", "the citation shows a High Court when the court is not stated")
check(L.court_class({"citation": "(2010) 11 SCC 441"}) == "SC" and L.court_class({"citation": "[1992] 1 S.C.R. 638"}) == "SC" and L.court_class({"citation": "AIRONLINE 2020 SC 784"}) == "SC" and L.court_class({"citation": "2025 INSC 844"}) == "SC", "Supreme Court citation forms are recognised")
check(L.court_class({"citation": "Criminal Appeal No. 511 of 2022", "source_url": "https://indiankanoon.org/doc/1/"}) == "UNKNOWN" and L.court_class({"citation": "x", "source_url": "https://api.sci.gov.in/jonew/judis/1.pdf"}) == "SC", "an entry that says nothing is UNKNOWN unless the source is the court's own site")
check(L.year_of("(2010) 11 SCC 441") == 2010 and L.year_of("Criminal Appeal No. 511 of 2022 (SC)") == 2022 and L.year_of("no year") is None, "the year is read from the citation")
check(L.split_name("Rangappa v Sri Mohan") == ("Rangappa", "Sri Mohan") and L.split_name("A vs. B")[1] == "B" and L.split_name("Only one")[1] == "", "a name is split into its two parties")
check(L.name_score("Mohan Lal v State of Punjab", CORPUS.docs["b4"]) == 1.0, "'Mohan Lal' finds 'MOHANLAL' (spacing does not matter)")
check(L.name_score("Rangappa v Sri Mohan", CORPUS.docs["b4"]) < 0.5, "different parties score low")

# ---- matching
m = L.match_case(CORPUS, case("Rangappa v Sri Mohan", "(2010) 6 S.C.R. 507"))
check(m["status"] == "MATCHED" and m["doc_key"] == "c1" and m["method"] == "citation" and m["confidence"] == "high", "a citation the judgment is known by, with agreeing names, is a high-confidence match")
m = L.match_case(CORPUS, case("State of Punjab v Baldev Singh", "(1999) 6 SCC 172"))
check(m["status"] == "MATCHED" and m["doc_key"] == "c2" and m["method"] == "name_year" and m["confidence"] == "high", "the same names in another year are told apart by the year")
m = L.match_case(CORPUS, case("Mohan Lal v State of Punjab", "(2018) 17 SCC 627"))
check(m["status"] == "MATCHED" and m["doc_key"] == "b4", "a name with different spacing still matches by name and year")
m = L.match_case(CORPUS, case("Union of India v Mohanlal", "(2016) 3 SCC 379"))
check(m["status"] == "MATCHED" and m["doc_key"] == "b5", "two cases with 'Mohanlal' are not confused")
m = L.match_case(CORPUS, case("Kaveri Plastics v Mahdoom Bawa Bahrudeen Noorul", "2025 INSC 1133"))
check(m["status"] == "MATCHED" and m["doc_key"] == "b13" and m["method"] == "citation", "a neutral citation matches")
m = L.match_case(CORPUS, case("Gamma Traders v Delta Bank", "(2012) 4 SCC 1"))
check(m["status"] == "AMBIGUOUS_MATCH" and len(m["candidates"]) == 2, "two judgments with the same parties and year are reported as ambiguous, not guessed")
m = L.match_case(CORPUS, case("Alpha Steels v Beta Finance", "(2011) 1 SCC 77"))
check(m["status"] == "MATCHED" and m["doc_key"] == "c10", "a bucket text that may be a second copy is not a second candidate")
m = L.match_case(CORPUS, case("Theta Corporation v Iota Board", "[2000] 2 S.C.R. 55"))
check(m["status"] == "AMBIGUOUS_MATCH" and m["candidates"] and m["doc_key"] is None, "a citation that fits a judgment with different names is not accepted")
m = L.match_case(CORPUS, case("Eta Union v Zeta Mills", "[2000] 2 S.C.R. 55"))
check(m["status"] == "MATCHED" and m["doc_key"] == "c12", "the same two parties named in the other order, with the citation, is the same case")
m = L.match_case(CORPUS, case("Nobody v Nowhere", "(2005) 1 SCC 1"))
check(m["status"] == "NOT_IN_COLLECTION" and m["doc_key"] is None, "a case with no such judgment is not in the collection")
m = L.match_case(CORPUS, case("Rangappa v Sri Mohan", "(2019) 1 SCC 1"))
check(m["status"] != "MATCHED", "the right names in a year more than one away from the citation's are not accepted")
m = L.match_case(CORPUS, case("Johnson V.U. v State of Kerala", "2024:KER:60051", court="Kerala High Court"))
check(m["status"] == "NOT_CHECKABLE_HIGH_COURT", "a High Court case is not looked for")

# ---- the traps found on the real library
m = L.match_case(CORPUS, case("D.K. Basu v State of West Bengal", "(1997) 1 SCC 416"))
check(m["status"] == "MATCHED" and m["doc_key"] == "c14" and m["confidence"] == "medium", "initials count: 'D.K. Basu' is not any other Basu, and a year one off the citation's is accepted (medium)")
check(L.name_score("D.K. Basu v State of West Bengal", CORPUS.docs["c15"]) < 0.8 and L.name_score("D.K. Basu v State of West Bengal", CORPUS.docs["c16"]) < 0.8, "a surname alone does not make a match")
check(L.name_score("Lata Singh v State of Uttar Pradesh", CORPUS.docs["c17"]) == 1.0 and L.name_score("Lalita Kumari v Government of Uttar Pradesh", CORPUS.docs["c18"]) == 1.0, "'U.P.' and 'Govt.' in the corpus title are read as Uttar Pradesh and Government")
m = L.match_case(CORPUS, case("Lata Singh v State of Uttar Pradesh", "(2006) 5 SCC 475"))
check(m["status"] == "MATCHED" and m["doc_key"] == "c17", "so a case whose title says 'U.P.' is found")
m = L.match_case(CORPUS, case("Lalita Kumari v Government of Uttar Pradesh", "(2014) 2 SCC 1"))
check(m["status"] == "MATCHED" and m["doc_key"] == "c18", "and one reported a year after it was decided is found")
m = L.match_case(CORPUS, case("Satender Kumar Antil v Central Bureau of Investigation (2026)", "2026 INSC 115"))
check(m["status"] == "NOT_IN_COLLECTION", f"a neutral citation names the exact year: the 2025 judgment with the same parties is not the 2026 one (got {m['status']})")
m = L.match_case(CORPUS, case("Satender Kumar Antil v Central Bureau of Investigation", "(2025) 7 SCC 1"))
check(m["status"] == "MATCHED" and m["doc_key"] == "b19", "with a report citation of the same year it is found")
m = L.match_case(CORPUS, case("All Cargo Movers (I) Pvt. Ltd. and Ors. v Dhanesh Badarmal Jain and Anr.", "(2007) 14 SCC 776", source_url="https://api.sci.gov.in/jonew/judis/29675.pdf"))
check(m["status"] == "MATCHED" and m["doc_key"] == "c29675" and m["method"] == "source_url", "the court's own file in the library entry gives the judgment exactly")
m = L.match_case(CORPUS, case("Nobody v Nowhere", "(2005) 1 SCC 1", source_url="https://api.sci.gov.in/jonew/judis/99999.pdf"))
check(m["status"] == "NOT_IN_COLLECTION", "a court-site id that is not in the collection falls through to the other tiers")
m = L.match_case(CORPUS, case("Nobody v Nowhere", "(2005) 1 SCC 1", source_url="https://api.sci.gov.in/jonew/judis/29675.pdf"))
check(m["status"] == "AMBIGUOUS_MATCH" and m["method"] == "source_url", "a court-site file that is a judgment with other names is reported, not accepted")

# ---- a person's decision wins
ov = {"Gamma Traders v Delta Bank": {"doc_key": "c9", "note": "checked by hand"}, "Nobody v Nowhere": {"not_in_collection": "we looked"}}
m = L.match_case(CORPUS, case("Gamma Traders v Delta Bank", "(2012) 4 SCC 1"), ov)
check(m["status"] == "MATCHED" and m["doc_key"] == "c9" and m["confidence"] == "person", "an override settles an ambiguous case")
m = L.match_case(CORPUS, case("Nobody v Nowhere", "(2005) 1 SCC 1"), ov)
check(m["status"] == "NOT_IN_COLLECTION" and m["note"] == "we looked", "an override can record that a case is not held")
m = L.match_case(CORPUS, {"case_name": "X v Y", "citation": "(2001) 1 SCC 1", "court_class": "SC", "year": 2001}, {"X v Y": {"doc_key": "nope"}})
check(m["status"] == "AMBIGUOUS_MATCH", "an override naming a judgment we do not have is not silently accepted")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
