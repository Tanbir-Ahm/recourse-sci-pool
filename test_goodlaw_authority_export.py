"""Tests for goodlaw/authority_export.py: a list of cases written as a CSV file with each case's status, evidence date and a note on every row.
Run: python test_goodlaw_authority_export.py

Part 1 uses a small register and cards written here, one for each kind of row. Part 2 exports the 76 real library cases.
"""
import csv
import io
import json
import os
import tempfile

from goodlaw import authority_export as AE
from goodlaw import cardreader as CR
from goodlaw import chat_format as CF
from goodlaw import register as R
from goodlaw import watchlist as W

FAILURES = []
HERE = os.path.dirname(os.path.abspath(__file__))
ADV = "A later five-judge bench of the Supreme Court (2020) appears to overrule or reject this case, in whole or in part, so check it before relying on this case."
CAU = "Later judgments doubt or limit this case, so check them before relying on it."
STATUTE = "This judgment discusses a section whose number changed under the 2023 codes."


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc:
        return True
    except BaseException:
        return False
    return False


def row(rid, a, ayear, b, byear, trust="verified", treatment="overruled", cites=()):
    return {"id": rid, "source": "t", "trust": trust,
            "overruled": {"name": a, "alt_names": [], "court": "SC", "cites": list(cites), "keys": R.key_set(" : ".join(cites)), "year": ayear, "years": [ayear]},
            "overruling": {"name": b, "court": "SC", "cites": [], "keys": [], "year": byear, "date": None, "bench": None},
            "treatment": treatment, "scope": None, "court_words": None, "same_parties": False, "flags": [], "evidence": {"basis": "B"}, "verification": None, "history": []}


def card(name, status, note=None, generated="2026-10-06", statute_note=None, review=None):
    return {"case": {"name": name, "citation_keys": []}, "status": status, "user_facing_note": note, "statute_note": statute_note, "internal_note": "", "review": review, "provenance": {"generated": generated}}


REG = R.Register([row("V1", "Ratanlal Industries v. Sethi Traders", 1965, "State of Mysore v. Syed Mahmood", 1968),
                  row("C1", "Mohan Lal v. State of Punjab", 2018, "Mukesh Singh v. State", 2020, trust="candidate"),
                  row("N1", "Gamma Industries v. Delta Traders", 1990, "Epsilon Bank v. Zeta Mills", 1995, treatment="not_good_law")], {"built_on": "2026-10-07"})
CARDS = CR.load({"cards": [
    card("Alpha v Beta", "ADVERSE_SIGNAL", ADV),
    card("Human v Review", "ADVERSE_SIGNAL", ADV, review={"current": True, "verdict": "CONFIRMED_ADVERSE", "reviewer": "Mr. Advocate", "date": "2026-10-10"}),
    card("Gamma Corp v Delta Ltd", "QUESTIONED", CAU),
    card("Quiet v Case", "NO_ADVERSE_FOUND", generated="2026-10-05"),
    card("Statute v Case", "NO_ADVERSE_FOUND", statute_note=STATUTE),
    card("Few v Cites", "INSUFFICIENT"),
    card("Mohan Lal v State of Punjab", "ADVERSE_SIGNAL", ADV),
]})
F = CF.Formatter(REG, CARDS, quiet_policy="coverage_note", today="2026-10-22")
FS = CF.Formatter(REG, CARDS, quiet_policy="silent", today="2026-10-22")


def one(name, year=None, citation=None, fmt=F, **kw):
    return AE.build_rows(fmt, [{"name": name, "year": year, "citation": citation}], **kw)[0]


# ---- one cell ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("cells")
check([AE.safe_cell(x) for x in ("=1+1", "+5", "-5", "@x", "\t=1+1", "\r@x")] == ["'=1+1", "'+5", "'-5", "'@x", "'=1+1", "'@x"], "a cell that starts like a formula gets an apostrophe in front, even after leading whitespace")
check(AE.safe_cell("\tx") == "x" and AE.safe_cell("  a\n\n b\tc ") == "a b c" and AE.safe_cell(None) == "" and AE.safe_cell(2018) == "2018" and AE.safe_cell("a=b") == "a=b", "whitespace and line breaks become single spaces; a formula character in the middle is left alone")

# ---- one row per kind --------------------------------------------------------------------------------------------------------------------------------------------------------------
print("rows")
r = one("Ratanlal Industries v. Sethi Traders", 1965)
check(r["status"] == "On the Overruled Register" and "was overruled by State of Mysore v. Syed Mahmood (1968)" in r["what_we_know"] and r["checked_by"] == "Overruled Register (reviewed list)" and r["evidence_as_of"] == "2026-10-07"
      and r["note"].startswith("From the Overruled Register: a row a lawyer reviewed"), "a confirmed register row: status, the register's own sentence, who checked, the date, and its note")
r = one("Mohan Lal v State of Punjab", 2018, "(2018) 17 SCC 627")
check(r["status"] == "Reported on the Overruled Register" and "not yet confirmed by our reviewer" in r["what_we_know"] and r["checked_by"].startswith("Overruled Register (candidate") and "not yet confirmed" in r["note"], "a candidate row says so in three places")
check(r["also"].startswith("Reported adverse: ") and ADV in r["also"], "and the checker's card, which also warns, is in the 'also' column")
r = one("Alpha v Beta")
check(r["status"] == "Reported adverse" and r["what_we_know"] == ADV and r["checked_by"] == "Checker (pattern-rule reading)" and r["evidence_as_of"] == "2026-10-06" and "not lawyer-validated" in r["note"] and r["also"] == "", "a checker flag: the card's sentence, the date, and 'not lawyer-validated'")
r = one("Human v Review")
check(r["status"] == "Adverse, confirmed by our reviewer" and r["checked_by"] == "Checker, confirmed by our reviewer", "a flag a person confirmed says who confirmed it")
r = one("Gamma Corp v Delta Ltd")
check(r["status"] == "Questioned" and r["what_we_know"] == CAU and "not lawyer-validated" in r["note"], "a caution")
r = one("Quiet v Case")
check(r["status"] == "No warning found in what we hold" and r["what_we_know"].startswith("Nothing adverse found in the later Supreme Court judgments we hold.") and "not a finding" in r["what_we_know"] and r["evidence_as_of"] == "2026-10-05" and "not a finding that the case is good law" in r["note"] and "not lawyer-validated" in r["note"], "a quiet case is spelled out, with the reason it is not reassurance")
check(one("Quiet v Case", fmt=FS)["status"] == "No warning found in what we hold", "even when the chat formatter is set to silence quiet cards, the file is not silent")
r = one("Nobody v Nowhere")
check(r["status"] == "Not checked by us" and r["checked_by"] == "" and r["evidence_as_of"] == "" and r["note"] == AE.NOTES[6] and "Verify" in r["what_we_know"], "a case nobody checked says so, with no invented source or date")
check(one("Few v Cites")["status"] == "Not checked by us" and "Too few later judgments" in one("Few v Cites")["what_we_know"], "too few citing judgments is not checked, with the reason")
r = one("Statute v Case")
check(r["section_numbers"] == STATUTE and r["status"] == "No warning found in what we hold", "a statute note goes in its own column")
r = one("Gamma Industries v. Delta Traders", 1990)
check("held not to be good law in Epsilon Bank v. Zeta Mills" in r["what_we_know"], "a court's holding is worded as the register words it, and the wording guard allows it")

# ---- the whole list ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("a list")
CASES = [{"name": "Quiet v Case"}, {"name": "Nobody v Nowhere"}, {"name": "Gamma Corp v Delta Ltd"}, {"name": "Alpha v Beta"}, {"name": "Human v Review"},
         {"name": "Mohan Lal v State of Punjab", "year": 2018, "citation": "(2018) 17 SCC 627"}, {"name": "Ratanlal Industries v. Sethi Traders", "year": 1965}, {"name": "Statute v Case"}]
rows = AE.build_rows(F, CASES)
check([r["case"] for r in rows] == ["Ratanlal Industries v. Sethi Traders", "Human v Review", "Alpha v Beta", "Mohan Lal v State of Punjab", "Gamma Corp v Delta Ltd", "Nobody v Nowhere", "Quiet v Case", "Statute v Case"],
      "most pressing first: a confirmed register row, a warning a person confirmed, other warnings, cautions, not checked, no warning found; the input order inside a group")
check([r["case"] for r in AE.build_rows(F, CASES, order="input")] == [c["name"] for c in CASES] and raises(ValueError, AE.build_rows, F, CASES, order="whatever"), "or the input order, when asked; any other ordering is refused")
check(all(r["status"] and r["note"] and r["exported_on"] == "2026-10-22" and r["what_we_know"] for r in rows), "no row is without a status, a note, an export date or something we know")
dup = AE.build_rows(F, [{"name": "Alpha v Beta", "year": 2018}, {"name": "ALPHA VERSUS BETA", "year": 2018}, {"name": "Alpha v Beta", "year": 2019}])
check(len(dup) == 2, "the same case under another spelling is one row; another year is another case")
check(raises(ValueError, AE.build_rows, F, [{"name": " "}]) and AE.build_rows(F, []) == [], "a case without a name is refused; an empty list gives no rows")
saved = AE.NOTES[5]
AE.NOTES[5] = "This case is good law."
try:
    guarded = raises(CF.WordingError, AE.build_rows, F, [{"name": "Quiet v Case"}])
finally:
    AE.NOTES[5] = saved
check(guarded, "a row whose own wording claims good law is not written")
check(AE.build_rows(F, [{"name": "Alpha v Beta", "label": "My client's lead authority"}])[0]["case"] == "My client's lead authority", "the lawyer's own label, if given, is the case column")
check("internal_refs" not in rows[0] and AE.build_rows(F, CASES[:1], include_internal=True)[0]["internal_refs"] == "quiet", "internal keys appear only when asked for")
check(AE.build_rows(F, [{"name": "Alpha v Beta"}], exported_on="2027-01-02")[0]["exported_on"] == "2027-01-02", "the export date can be given")

# ---- the file ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("the file")
tricky = [{"name": "=HYPERLINK(\"http://x.invalid\",\"click\")", "year": 2018}, {"name": "रमेश v. State of “X”, Ltd.", "year": 2015, "citation": "(2015) 3 SCC 1"}, {"name": "Line\nbreak v. Co", "year": 2012}]
rows = AE.build_rows(F, tricky)
with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "authorities.csv")
    n = AE.write_csv(rows, path)
    raw = open(path, "rb").read()
    check(n == 3 and raw.startswith(b"\xef\xbb\xbf") and b"\r\n" in raw, "the file is UTF-8 with a byte-order mark, one record per line")
    got = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
    check(got[0] == AE.COLUMNS and len(got) == 4 and all(len(g) == len(AE.COLUMNS) for g in got), "the header is the fixed columns and every row has all of them")
    cells = {g[0] for g in got[1:]}
    check("'=HYPERLINK(\"http://x.invalid\",\"click\")" in cells and "रमेश v. State of “X”, Ltd." in cells and "Line break v. Co" in cells, "a formula is defused, Indian-language text and curly quotes survive, a line break becomes a space")
    check(not any(c.startswith(AE._FORMULA) for g in got[1:] for c in g), "no cell starts with a formula character")
    check(AE.to_csv_text([]).strip() == ",".join(AE.COLUMNS), "an empty list gives a header only")

# ---- a saved watchlist -----------------------------------------------------------------------------------------------------------------------------------------------------------------
print("a saved watchlist")
wl = W.Watchlist(F, owner="a test chamber")
wl.add("Quiet v Case", 2012, label="Quiet one")
wl.add("Alpha v Beta", 2018)
wl.add("Nobody v Nowhere", 2001)
with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "w.csv")
    n = AE.export_watchlist(wl, path)
    got = list(csv.DictReader(io.StringIO(open(path, encoding="utf-8-sig", newline="").read(), newline="")))
    check(n == 3 and [g["case"] for g in got] == ["Alpha v Beta", "Nobody v Nowhere", "Quiet one"] and got[2]["year"] == "2012", "a watchlist exports its cases with the lawyer's labels, most pressing first")

# ---- the real register and cards ---------------------------------------------------------------------------------------------------------------------------------------------
print("the real register and cards")
cfile = json.load(open(os.path.join(HERE, "cards", "currency_cards.json"), encoding="utf-8"))
RF = CF.Formatter(R.Register.load(), CR.load(cfile), quiet_policy="silent", today="2026-10-22")
cases = [{"name": c["case"]["name"], "year": c["case"].get("year"), "citation": c["case"].get("citation")} for c in cfile["cards"]]
rows = AE.build_rows(RF, cases)
keys = {W.watch_key(c["name"], c["year"], c["citation"]) for c in cases}
check(len(rows) == len(keys) and len(rows) >= 70, f"the library's cases export as one row each ({len(rows)} rows)")
statuses = {r["status"] for r in rows}
check(statuses <= {"On the Overruled Register", "Reported on the Overruled Register", "Reported adverse", "Adverse, confirmed by our reviewer", "Questioned", "Not checked by us", "No warning found in what we hold"}, f"every status is one of the fixed words ({sorted(statuses)})")
check(all(r["status"] and r["note"] and r["what_we_know"] for r in rows) and all(r["checked_by"] or r["status"] == "Not checked by us" for r in rows), "no row is silent, and every checked row says who checked it")
check([r["case"] for r in rows[:2]] == ["Mohan Lal v State of Punjab", "Siddharam Satlingappa Mhetre v State of Maharashtra"] or {r["case"] for r in rows[:2]} <= {"Mohan Lal v State of Punjab", "Siddharam Satlingappa Mhetre v State of Maharashtra"},
      "the two known warnings (Mohan Lal and Mhetre) come first")
text = AE.to_csv_text(rows)
check("L1-" not in text and "L2-" not in text and "register:" not in text and "card:" not in text, "no internal register ids or keys appear in the default file")
check(sum(1 for r in rows if r["status"] == "Not checked by us") >= 20 and sum(1 for r in rows if r["status"] == "No warning found in what we hold") >= 30, "most library cases are either not checked or quiet, as the cards say")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
