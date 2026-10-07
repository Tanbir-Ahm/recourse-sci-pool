"""Tests for the Overruled Register: goodlaw/register.py, register_guard.py, register_build.py, register_review.py, register_sweep.py.
Run: python test_goodlaw_register.py

Part 1 uses a small register written here. Part 2 are the gates on the real register file (goodlaw/data/register/register.json): every row can be recognised, nothing that is not on the
register is hit by the 76 library cases except the two the checker also flags, and a bare name is never worded.
"""
import copy
import csv
import json
import os
import tempfile

from goodlaw import register as R
from goodlaw import register_build as RB
from goodlaw import register_guard as G
from goodlaw import register_review as RV
from goodlaw import register_sweep as SW
from goodlaw import register_exam as EX

FAILURES = []
HERE = os.path.dirname(os.path.abspath(__file__))


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def row(rid, a, ayear, b, byear, trust="verified", treatment="overruled", cites=(), scope=None, source="t", alt=(), years=None, flags=(), bcites=()):
    return {"id": rid, "source": source, "trust": trust,
            "overruled": {"name": a, "alt_names": list(alt), "court": "SC", "cites": list(cites), "keys": R.key_set(" : ".join(cites)), "year": ayear, "years": years or [ayear]},
            "overruling": {"name": b, "court": "SC", "cites": list(bcites), "keys": R.key_set(" : ".join(bcites)), "year": byear, "date": None, "bench": None},
            "treatment": treatment, "scope": scope, "court_words": None, "same_parties": False, "flags": list(flags), "evidence": {"basis": "B"}, "verification": None, "history": []}


ROWS = [
    row("A1", "Kharak Singh v. State of U.P.", 1963, "K.S. Puttaswamy v. Union of India", 2017, trust="candidate", treatment="overruled_in_part", cites=["AIR 1963 SC 1295", "(1964) 1 SCR 332"],
        scope="only the second part", years=[1962, 1963]),
    row("A2", "Mohan Lal v. State of Punjab", 2018, "Mukesh Singh v. State (Narcotic Branch of Delhi)", 2020, trust="candidate", cites=["(2018) 17 SCC 627"]),
    row("A3", "Commissioner of Income Tax Bombay v. Chugandas and Co.", 1965, "State of Mysore v. Syed Mahmood", 1968, cites=["(1965) 55 ITR 17", "(1964) 8 SCR 332"]),
    row("A4", "K.L. Verma v. State", 1998, "Adri Dharan Das v. State of West Bengal", 2005, cites=["(1998) 9 SCC 348"], bcites=["(2005) 4 SCC 303"]),
    row("A5", "Adri Dharan Das v. State of West Bengal", 2005, "Sushila Aggarwal v. State (NCT of Delhi)", 2020, trust="candidate", cites=["(2005) 4 SCC 303"]),
    row("A6", "K.L. Verma v. State", 1998, "Sushila Aggarwal v. State (NCT of Delhi)", 2020, trust="candidate", cites=["(1998) 9 SCC 348"]),
    row("A7", "A.D.M. Jabalpur v. Shivkant Shukla", 1976, "K.S. Puttaswamy v. Union of India", 2017, alt=["ADM Jabalpur v. Shivakant Shukla"], trust="reviewer_confirmed"),
    row("A8", "Foo v. Bar", 2001, "Baz v. Qux", 2010, trust="unchecked"),
    row("A9", "Sekar v. State", 1999, "Anand v. State of Tamil Nadu", 2005),                       # too generic to match by name
    row("A10", "Shafhi Mohammad v. State of H.P.", 2018, "Arjun Panditrao Khotkar v. Kailash Gorantyal", 2020, trust="rejected", cites=["(2018) 5 SCC 311"]),
    row("A11", "Gamma v. Delta", 1990, "Epsilon v. Zeta", 1995, treatment="disputed_listing", flags=["list_mutual_pair"]),
]
REG = R.Register(ROWS)


def hits(text, strength=None):
    return [(h["row"]["id"], h["how"], h["strength"]) for h in REG.scan(text) if strength in (None, h["strength"])]


# ---- names and citations -------------------------------------------------------------------------------------------------------------------------------------------------
check([t for t, _, _ in R.tokenize("A.D.M. Jabalpur v. K.L. Verma")] == ["adm", "jabalpur", "v", "kl", "verma"], "dotted initials are one token (A.D.M., K.L.)")
check([t for t, _, _ in R.tokenize("State of U.P. and State of Uttar Pradesh")].count("uttar_pradesh") == 2, "U.P. and Uttar Pradesh are the same token")
check(R.split_parties("Kharak Singh v. State of U.P.") == ("Kharak Singh", "State of U.P."), "parties are split at 'v.'")
check(R.key_set("AIR 1965 All 586 : (2010) 11 SCC 441") == ["airx:1965:all:586", "scc:2010:11:441"], "High Court AIR and Supreme Court keys")
check(R.keys_agree("scr:1964:1:332", "scr:1964:8:332") is False, "page 332 of two different SCR volumes is not one citation")
check(R.keys_agree("scr:1954::1077", "scr:1954:1:1077") is True, "a volume-less old SCR citation matches the same page")

# ---- matching -------------------------------------------------------------------------------------------------------------------------------------------------------------------
check(hits("see Kharak Singh v. State of Uttar Pradesh (1963)") == [("A1", "name_year", "strong")], "both names and the year: strong")
check(hits("Kharak Singh v. State of U.P., AIR 1963 SC 1295") == [("A1", "citation", "strong")], "a citation on the row: strong, and one finding for the row")
check(hits("Kharak Singh v. State of U.P. was discussed") == [("A1", "name_only", "weak")], "both names without a year: weak")
check(hits("Kharak Singh v. State of U.P. (1990)") == [("A1", "name_only", "weak")], "a year more than one away is not a match")
check(hits("Kharak Singh was a Lucknow resident and Mohan Lal a clerk") == [], "a bare party name is never a match")
check(hits("Mohan Lal v. State of Haryana (2018)") == [], "the same first party against a different respondent is not a match")
check(hits("Mohan Lal v. State of Punjab (1994) 3 SCC 1") == [("A2", "name_only", "weak")], "the right names with a different year are weak")
check(hits("(1964) 8 SCR 332") == [("A3", "citation", "strong")], "volume 8 page 332 finds Chugandas, not Kharak Singh (volume 1 page 332)")
check(hits("[1964] 1 SCR 332") == [("A1", "citation", "strong")], "and volume 1 finds Kharak Singh")
check(hits("ADM Jabalpur v. Shivakant Shukla (1976) 2 SCC 521") == [("A7", "name_year", "strong")], "an alternative spelling of the names is found")
check(hits("A.D.M. Jabalpur v. Shivkant Shukla, 1976") == [("A7", "name_year", "strong")], "dotted initials in the text")
check(hits("Sekar v. State (1999)") == [], "a name pair of common words only (Sekar v. State) is not matched by name")
check(hits("Sekar v. State, (1999) 1 SCC 1") == [], "and a citation that is not on the row is not a match")
check(hits("Mohan Lal v. State of Punjab (2018) and also Kharak Singh v. State of Uttar Pradesh (1963)") == [("A2", "name_year", "strong"), ("A1", "name_year", "strong")], "two cases in one text, in order")
check(len(REG.lookup_case("Mohan Lal v State of Punjab", 2018, "(2018) 17 SCC 627")) == 1, "lookup_case on a structured case (name, year, citation) gives one finding")
check(REG.lookup_case("Mohan Lal v State of Punjab", 1994, None)[0]["strength"] == "weak", "lookup_case with a wrong year is weak")

# ---- wording --------------------------------------------------------------------------------------------------------------------------------------------------------------------
c1 = REG.clause(ROWS[0])
check("is reported as overruled in part by K.S. Puttaswamy v. Union of India (2017)" in c1 and "not yet confirmed by our reviewer" in c1 and "only the second part" in c1, "a candidate row is worded as reported, not confirmed")
check(REG.clause(ROWS[2]).startswith("Commissioner of Income Tax Bombay v. Chugandas and Co. (1965) was overruled by State of Mysore v. Syed Mahmood (1968)."), "a verified row is worded firmly")
check("not yet confirmed" not in REG.clause(ROWS[6]), "a reviewer-confirmed row is worded firmly")
check(REG.clause(ROWS[7]) is None and REG.clause(ROWS[9]) is None, "unchecked and rejected rows have no wording")
check("listed in our reference list as overruled by Epsilon v. Zeta (1995), but the list is inconsistent" in REG.clause(ROWS[10]), "a disputed listing says the list is inconsistent")
check([r["id"] for r in REG.chain(ROWS[3])] == ["A5"], "chain: Adri Dharan Das (the overruling case of A4) is itself overruled by A5")
check("itself later overruled by Sushila Aggarwal" in REG.clause(ROWS[3]), "the chain is put in the wording")
check(sorted(r["id"] for r in REG.same_decision_rows(ROWS[3])) == ["A6"], "A4 and A6 are the same overruled decision (K.L. Verma) overruled by two cases")
grp = REG.clause_group([ROWS[3], ROWS[5]])
check(grp.startswith("K.L. Verma v. State (1998) was overruled by Adri Dharan Das") and "It is also reported as overruled by Sushila Aggarwal" in grp, "rows about the same decision give one sentence, the firmest first")

# ---- the three locks -----------------------------------------------------------------------------------------------------------------------------------------------------
ans = ("Mohan Lal v. State of Punjab (2018) 17 SCC 627 held that an informant cannot investigate. Kharak Singh v. State of U.P. (1963) was overruled in part by Puttaswamy. "
       "K.L. Verma v. State (1998) 9 SCC 348 limited bail. Sekar v. State (1999) was a different case. Mohan Lal v. State of Haryana was cited too.")
res = G.guard_answer(REG, ans)
check(len(res["notes"]) == 2 and res["badge"], "the guard adds a note for Mohan Lal and K.L. Verma, not for Kharak Singh (already said to be overruled)")
check(any("Mohan Lal" in n for n in res["notes"]) and any("K.L. Verma" in n and "Adri Dharan Das" in n for n in res["notes"]), "the notes are the register's sentences")
check(all(f["acknowledged"] for f in res["findings"] if f["row_id"] == "A1"), "'was overruled in part' next to the mention counts as saying it")
check(res["review"] == [], "no weak match here")
res2 = G.guard_answer(REG, "Mohan Lal v. State of Punjab was a leading case.")
check(res2["notes"] == [] and len(res2["review"]) == 1, "a weak match is listed for a person and never worded")
res3 = G.guard_answer(REG, "K.L. Verma v. State (1998) 9 SCC 348 was overruled by Adri Dharan Das v. State of West Bengal (2005).")
check(len(res3["notes"]) == 1 and res3["notes"][0].startswith("Adri Dharan Das v. State of West Bengal (2005) is reported as overruled by Sushila Aggarwal"), "an overruled case cited as the overruling case is itself noted ('overruled by' acknowledges K.L. Verma, not Adri Dharan Das)")
res4 = G.guard_answer(REG, "Mohan Lal v. State of Punjab (2018) 17 SCC 627 was the leading case. It was later overruled in a five-judge decision. Kharak Singh v. State of U.P. (1963) is cited. Another case was overruled.")
check([f["acknowledged"] for f in res4["findings"] if f["row_id"] == "A2"] == [True] and [f["acknowledged"] for f in res4["findings"] if f["row_id"] == "A1"] == [False], "an overruling in the next sentence counts only when it refers back ('It was later overruled'); a neighbouring case's does not")
check(G.apply_notes("Answer.", res).startswith("Answer.\n\nCurrency notes") and G.apply_notes("Answer.", {"notes": []}) == "Answer.", "apply_notes appends a block only when there are notes")
facts = G.prompt_facts(REG, ["Is Mohan Lal v. State of Punjab (2018) still good law?", "A.D.M. Jabalpur v. Shivkant Shukla (1976)"])
check(len(facts) == 2 and facts[0].startswith("REGISTER NOTE (not yet confirmed)") and facts[1].startswith("REGISTER FACT"), "prompt facts: a note for a candidate, a fact for a confirmed row")
fl = G.retrieval_flags(REG, [{"case_name": "Mohan Lal v State of Punjab", "year": 2018, "citation": "(2018) 17 SCC 627"}, {"case_name": "Arnesh Kumar v. State of Bihar", "year": 2014, "text": "see A.D.M. Jabalpur v. Shivkant Shukla (1976)"},
                          {"case_name": "ADM Jabalpur v. Shivakant Shukla", "year": 1976}, {"case_name": "Unrelated v. Case", "year": 2000}])
check([f["action"] for f in fl] == ["badge", "note", "demote_and_badge", None], "retrieval flags: badge a candidate, note a mention, demote a confirmed own case, leave the rest")

# ---- the weekly review ---------------------------------------------------------------------------------------------------------------------------------------------------
cards = {"cards": [{"status": "ADVERSE_SIGNAL", "case": {"name": "Mohan Lal v State of Punjab", "citation": "(2018) 17 SCC 627", "year": 2018}, "user_facing_note": "check it",
                    "corpus": {"doc_key": "b1"}, "evidence": [{"group": "strong", "title": "MUKESH SINGH", "date": "2020-08-31", "bench_size": 5, "cue": "overruled", "label": "OVERRULES", "quote": "Mohan Lal ... overruled."}]},
                   {"status": "NO_ADVERSE_FOUND", "case": {"name": "Quiet v. Case"}}]}
flags = {"schema": "goodlaw-flags-1", "flags": []}
new, quiet = RV.flags_from_cards(cards, flags, "2026-10-07")
check(new == ["F-mohan-lal-v-state-of-punjab"] and quiet == [] and len(flags["flags"]) == 1, "an ADVERSE_SIGNAL card becomes an open flag; a quiet card does not")
new2, quiet2 = RV.flags_from_cards({"cards": []}, flags, "2026-10-14")
check(new2 == [] and quiet2 == ["F-mohan-lal-v-state-of-punjab"] and flags["flags"][0]["state"] == "open", "a flag the checker stops raising stays open")
props = {"schema": "goodlaw-proposals-1", "proposals": [{"id": "P-0001", "state": "open", "kind": "tag", "doc_key": "b9", "date": "2021-01-01", "bench": 3, "title": "ALPHA versus BETA", "overruled_name": "Old v. Case",
                                                      "overruled_cites": "(1990) 1 SCC 1", "evidence": "overruled", "already_in_register": False, "history": []}]}
rows_w = copy.deepcopy(ROWS)
regw = R.Register(rows_w)
q = RV.build_queue(regw, flags, props, "2026-10-14")
kinds = {}
for it in q:
    kinds.setdefault(it["kind"], []).append(it["item_id"])
check(kinds.get("flag") == ["F-mohan-lal-v-state-of-punjab"], "the queue has the open flag")
check(set(kinds.get("candidate", [])) == {"A1", "A2", "A5", "A6"}, "every candidate row is in the queue (a candidate whose overruling case was itself overruled still shows as a candidate, with that noted)")
check("A4" in kinds.get("chain", []), "a row whose overruling decision was later overruled is a chain item")
check(kinds.get("unchecked") == ["A8"] and kinds.get("proposal") == ["P-0001"] and "A10" not in sum(kinds.values(), []), "unchecked rows and proposals are in, rejected rows are not")
check([i["kind"] for i in q][:1] == ["flag"] and all(i["next_review_if_kept"] == "2026-10-21" for i in q), "flags come first; a kept item returns seven days later")
limited = RV.build_queue(regw, flags, props, "2026-10-14", limit=3)
check(len(limited) == 3 and limited[0]["kind"] == "flag", "the limit cuts the sheet but never the flags")

with tempfile.TemporaryDirectory() as td:
    sheet = os.path.join(td, "q.csv")
    RV.write_queue(q, sheet)
    recs = list(csv.DictReader(open(sheet, encoding="utf-8")))
    check(recs[0]["item_id"] == "F-mohan-lal-v-state-of-punjab" and set(recs[0]) == set(RV.COLUMNS), "the sheet has the agreed columns")
    for r_ in recs:
        r_["reviewer"], r_["review_date"] = "Mr. Advocate", "2026-10-14"
        if r_["item_id"] == "F-mohan-lal-v-state-of-punjab":
            r_["decision"] = "confirm_overruled"
        elif r_["item_id"] == "A1":
            r_["decision"] = "confirm"
        elif r_["item_id"] == "A2":
            r_["decision"] = "keep"
        elif r_["item_id"] == "A5":
            r_["decision"] = "reject"
        elif r_["item_id"] == "A8":
            r_["decision"], r_["new_treatment"] = "confirm", "overruled"
        elif r_["item_id"] == "A4":
            r_["decision"] = "confirm"
        elif r_["item_id"] == "P-0001":
            r_["decision"], r_["overruled_year"] = "add_row", "1990"
        elif r_["item_id"] == "A6":
            r_["decision"], r_["new_treatment"] = "change", "not_good_law"
    with open(sheet, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RV.COLUMNS)
        w.writeheader()
        w.writerows(recs)
    out = RV.apply_decisions(rows_w, flags, props, sheet, "Mr. Advocate", "2026-10-14")
    check(out["errors"] == [] and len(out["applied"]) == len(recs), f"every decision was applied ({out['errors']})")
    by = {r_["id"]: r_ for r_ in rows_w}
    check(by["A1"]["trust"] == "reviewer_confirmed" and by["A1"]["verification"]["by"] == "Mr. Advocate" and by["A1"]["history"][-1]["event"].startswith("confirmed by the reviewer"), "confirm: a candidate becomes reviewer_confirmed, with the reviewer and the history")
    check(by["A2"]["trust"] == "reviewer_confirmed" and by["A2"]["treatment"] == "overruled", "the confirmed flag confirms the register row it matches (Mohan Lal)")
    check(flags["flags"][0]["state"] == "confirmed" and flags["flags"][0]["register_rows"] == ["A2"], "and the flag is recorded as confirmed with that row")
    check(by["A5"]["trust"] == "rejected" and len(by["A5"]["history"]) == 1 and REG.clause(by["A5"]) is None, "reject: the row stays, marked rejected, never worded")
    check(by["A8"]["trust"] == "reviewer_confirmed", "an unchecked row can be confirmed")
    check(by["A4"]["review"].get("chain_ok") == "2026-10-14" and by["A4"]["trust"] == "verified", "a verified chain row stays verified; the re-read is recorded and it leaves the queue")
    check(by["A6"]["treatment"] == "not_good_law" and by["A6"]["trust"] == "reviewer_confirmed", "change: a new treatment is recorded and confirmed")
    check(props["proposals"][0]["state"] == "added" and any(r_["id"].startswith("RS-") and r_["trust"] == "reviewer_confirmed" for r_ in rows_w), "a proposal added by the reviewer becomes a confirmed row")
    q2 = RV.build_queue(R.Register(rows_w), flags, props, "2026-10-14")
    check(not [i for i in q2 if i["item_id"] in ("A1", "A4", "A5", "A8", "P-0001", "F-mohan-lal-v-state-of-punjab")], "decided items are not in the next queue")
    rows_k = copy.deepcopy(ROWS)
    RV.apply_decisions(rows_k, {"flags": []}, {"proposals": []}, sheet, "Mr. Advocate", "2026-10-14")                # row-only decisions on a fresh copy: A2 is 'keep'
    kept = {r_["id"]: r_ for r_ in rows_k}["A2"]
    check(kept["review"]["next_due"] == "2026-10-21" and not RV.build_queue(R.Register([kept]), {"flags": []}, {"proposals": []}, "2026-10-15"), "keep: the item does not return until its due date")
    check(bool(RV.build_queue(R.Register([kept]), {"flags": []}, {"proposals": []}, "2026-10-21")), "and returns on it")
    bad = list(recs)
    bad[0] = {**bad[0], "decision": "bogus"}
    with open(sheet, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RV.COLUMNS)
        w.writeheader()
        w.writerows(bad[:1])
    out2 = RV.apply_decisions(copy.deepcopy(ROWS), copy.deepcopy(flags), copy.deepcopy(props), sheet, "x", "2026-10-14")
    check(len(out2["errors"]) == 1 and out2["applied"] == [], "an unknown decision is reported, not applied")

# ---- the sweep ------------------------------------------------------------------------------------------------------------------------------------------------------------------
head = ("Case Law Cited Raj Kumar Karwal v. Union of India (1990) 2 SCC 409: [1990] 2 SCR 63; Kanhaiyalal v. Union of India (2008) 4 SCC 668: [2008] 1 SCR 350 – overruled. "
        "State of Punjab v. Barkat Ram [1962] 3 SCR 338 – relied on. Old v. Case (1970) 1 SCC 1 – per incuriam.")
tags = SW.parse_tags(head)
check([t[0] for t in tags] == ["Raj Kumar Karwal v. Union of India", "Kanhaiyalal v. Union of India", "Old v. Case"], "the sweep reads the report's adverse tags and not the 'relied on' ones")
check(SW.operative_sentences("The decision in Foo v. Bar (supra) is hereby overruled. The learned counsel urged that Foo v. Bar (supra) is overruled.") == ["The decision in Foo v. Bar (supra) is hereby overruled."],
      "the sweep keeps the court's operative sentence and drops a party's argument")

# ---- the build ------------------------------------------------------------------------------------------------------------------------------------------------------------------
check(RB.split_cell("G.P. Ceramics Pvt. Ltd. Vs. Commissioner, Trade Tax, U.P., (2009) 1 JT 224 : (2008) 15 SCALE 538") == ("G.P. Ceramics Pvt. Ltd. Vs. Commissioner, Trade Tax, U.P.", "(2009) 1 JT 224 : (2008) 15 SCALE 538"),
      "a cell is split into the name and the citations")
check(RB.decision_record("Mahadeo Vs. The State of Bombay, AIR 1959 SC 735 : (1959) 2 SCR 339 Supp")["court"] == "SC" and RB.decision_record("K.G. Jagannath Vs. State of Mysore, AIR 1971 Kar 342")["court"] == "HC",
      "Supreme Court and High Court AIR citations are told apart")
check(RB.cite_years("(2008) CriLJ 1947 : (2007) 3 KCCR 165") == [2007, 2008], "a page number (CriLJ 1947) is not read as a year")
check(RB.display_name("A Vs. B, etc.") == "A v. B", "'Vs.' and a trailing 'etc.' are tidied")

# ---- the exam and the site bundle ----------------------------------------------------------------------------------------------------------------------------------------
check(EX._clean("Sabhajit Tewary v. Union of India (UOI) and Others") == "Sabhajit Tewary v. Union of India", "exam questions use tidy case names")

# ---- gates on the real register -----------------------------------------------------------------------------------------------------------------------------------------
REAL = R.Register.load()
rows_real = REAL.rows
check(len(rows_real) == 1765 and sum(1 for r_ in rows_real if r_["source"] == "list1") == 1688, "the register holds the 1,688 rows of list 1 and the rows of list 2 and its siblings")
check(all(r_["trust"] == "verified" and r_["verification"]["by"] == "Mr. Advocate" and r_["verification"]["on"] == "2026-10-07" for r_ in rows_real if r_["source"] == "list1"), "list 1 rows are verified, by Mr. Advocate, 2026-10-07 (as recorded from the owner)")
check(all(r_["trust"] in ("candidate", "unchecked") and r_["verification"] is None for r_ in rows_real if r_["source"] != "list1"), "no row of the post-2015 list is marked verified")
check(len({r_["id"] for r_ in rows_real}) == len(rows_real), "row ids are unique")
check(all(r_["treatment"] in R.TREATMENTS and r_["trust"] in R.TRUSTS for r_ in rows_real), "every treatment and trust level is a known one")
by_match = {}
for r_ in rows_real:
    by_match[r_["match_by"]] = by_match.get(r_["match_by"], 0) + 1
check(by_match.get("name_year", 0) + by_match.get("citation", 0) >= 1650, f"at least 1,650 rows are recognised strongly by their own name and year or citation ({by_match})")
miss = [r_["id"] for r_ in rows_real if r_["trust"] != "unchecked" and REAL.match_class(r_) != r_["match_by"]]
check(miss == [], "the stored match class of every row is what the matcher gives now")
check(all("needs_citation_or_year" in r_["flags"] for r_ in rows_real if r_["match_by"] in ("weak", "none") and r_["trust"] != "unchecked"), "rows that cannot be recognised strongly are flagged for the reviewer")
# round trip on every row that has a citation or a year
bad = []
for r_ in rows_real:
    if r_["trust"] == "unchecked" or r_["match_by"] not in ("name_year", "citation"):
        continue
    o = r_["overruled"]
    txt = " ; ".join(o["cites"]) if r_["match_by"] == "citation" else f"{o['name']} ({o['year']})"
    if not any(h["row"]["id"] == r_["id"] and h["strength"] == "strong" for h in REAL.scan(txt)):
        bad.append(r_["id"])
check(bad == [], f"every recognisable row is found when its own name and year (or citation) is scanned ({bad[:5]})")
lib = json.load(open(os.path.join(HERE, "goodlaw", "targets", "library.json"), encoding="utf-8"))["cases"]
lib_hits = {c["case_name"]: [h["row"]["id"] for h in REAL.lookup_case(c["case_name"], c.get("year"), c.get("citation")) if h["strength"] == "strong"] for c in lib}
lib_hits = {k: v for k, v in lib_hits.items() if v}
check(sorted(lib_hits) == ["Mohan Lal v State of Punjab", "Siddharam Satlingappa Mhetre v State of Maharashtra"], f"of the 76 library cases only the two the checker also flags are on the register ({sorted(lib_hits)})")
check(all(v[0].startswith("L2-") for v in lib_hits.values()), "and both are candidate rows (the post-2015 list), not verified rows")
check(REAL.lookup_case("Mohan Lal", None, None) == [] and REAL.lookup_case("Mohan Lal v. State of Punjab", 2005, None)[0]["strength"] == "weak", "on the real register a bare name is nothing and a wrong year is weak")
check("Mukesh Singh" in G.guard_answer(REAL, "Mohan Lal v. State of Punjab (2018) 17 SCC 627 held X.")["notes"][0], "the guard on the real register words Mohan Lal as overruled by Mukesh Singh")
chain_ids = [r_["id"] for r_ in rows_real if REAL.chain(r_)]
check({"L1-0256", "L1-0374", "L1-0407", "L1-0598", "L1-1405"} <= set(chain_ids) and "L2-057" in chain_ids, "the chains found by hand are found by the register (K.L. Verma, Synthetics, Ram Lal Narang, H.R.S. Murthy, Naz Foundation, N.N. Global)")
check(any("itself later" in (REAL.clause(REAL.by_id["L1-0256"]) or "") for _ in [0]), "and they appear in the wording")
flags_real = RV.load_flags()
check(sorted(f["id"] for f in flags_real["flags"]) == ["F-mohan-lal-v-state-of-punjab", "F-siddharam-satlingappa-mhetre-v-state-of-maharashtra"] and all(f["state"] == "open" for f in flags_real["flags"]), "the two checker flags are open in the ledger")
qs, key = EX.build_exam(REAL)
check(len(qs) == 50 and len({q["id"] for q in qs}) == 50 and {k["kind"] for k in key.values()} == {"list1", "list2", "chain"}, "the trap exam has 50 questions from list 1, the post-2015 list and chain rows")
check(qs == EX.build_exam(REAL)[0], "and it is the same exam every time (fixed seed)")
kid = next(iter(key))
krow = REAL.by_id[key[kid]["row_id"]]
nm = krow["overruled"]["name"].replace(" Vs. ", " v. ")
ok_ans = {k_: "Nothing relevant here." for k_ in key}
ok_ans[kid] = f"{nm} ({krow['overruled']['year']}) held X. It was later overruled."
t1, r1 = EX.score(REAL, ok_ans, key)
check(r1[kid] == "acknowledged" and t1["not_cited"] == 49 and t1["passes"], "exam scorer: an answer that says 'overruled' next to the case is acknowledged; an answer that does not cite the case is fine")
bad_ans = dict(ok_ans)
bad_ans[kid] = f"{nm} ({krow['overruled']['year']}) held X and is the leading authority."
t2, r2 = EX.score(REAL, bad_ans, key)
check(r2[kid] == "guard_note" and t2["passes"], "an answer that cites it as authority is caught by the guard (guard_note), not missed")
miss_ans = dict(ok_ans)
first = R.party_sigs(krow["overruled"]["name"])[0][0]
second = (R.party_sigs(krow["overruled"]["name"])[1] or ("",))[0]
miss_ans[kid] = f"The {first} case against {second} is the leading authority."
t3, r3 = EX.score(REAL, miss_ans, key)
check(r3[kid] == "unmatched" and not t3["passes"], "an answer that names the case in a form the register cannot recognise is 'unmatched' and fails the run")
import importlib.util
import subprocess
import sys
with tempfile.TemporaryDirectory() as td:
    out_dir = os.path.join(td, "overruled_register")
    proc = subprocess.run([sys.executable, os.path.join(HERE, "sci_goodlaw.py"), "register-export-site", "--out", out_dir], capture_output=True, text=True)
    check(proc.returncode == 0 and os.path.exists(os.path.join(out_dir, "register_slim.json")), "the site bundle is written")
    code = ("import sys; sys.path.insert(0, %r); import overruled_register as OR; reg = OR.load(); "
            "res = OR.register_guard.guard_answer(reg, 'Mohan Lal v. State of Punjab (2018) 17 SCC 627 held X.'); print(len(reg.rows), len(res['notes']), 'Mukesh Singh' in res['notes'][0])" % td)
    p2 = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, cwd=td)
    check(p2.stdout.split() == ["1765", "1", "True"], f"the bundle works on its own, without the rest of this repository ({p2.stdout.strip()} {p2.stderr.strip()[-120:]})")
    slim_doc = json.load(open(os.path.join(out_dir, "register_slim.json"), encoding="utf-8"))
    check(all("history" not in r_ and "evidence" not in r_ for r_ in slim_doc["rows"]) and os.path.getsize(os.path.join(out_dir, "register_slim.json")) < 1_200_000, "and it carries no history or evidence text and is under 1.2 MB")
meta = REAL.meta
check(meta["sources"]["list1"]["verified_by"] == "Mr. Advocate" and meta["sources"]["list2"]["trust"] == "candidate" and meta["review"]["interval_days"] == 7, "the register records the reviewer, the trust of each list and the 7-day interval")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
