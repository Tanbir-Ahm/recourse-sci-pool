"""test_goodlaw_register_hold.py -- a register row that is chronologically impossible is not worded (2026-10-16).

Staging, 2026-10-16: the page told a user that "Nalini (1999) was overruled by Bilal Ahmed Kaloo (1997)" and that Bilal Ahmed Kaloo "was itself later overruled by Nalini". The build had already flagged 11
list-1 rows `year_order_check` (the overruling decision's years are all earlier than the overruled decision's), but they were still worded as firm facts. Now such a row is HELD (register.held): no sentence,
no note, no chain step, no prompt line, until a person confirms the entry (`review.listing_ok`). It stays in the register and in the weekly review.
Part 1 uses a small register written here; part 2 uses the real register file. Fully offline. Run: python -X utf8 test_goodlaw_register_hold.py"""
import copy
import json
import sys

from goodlaw import register as R
from goodlaw import register_guard as G
from goodlaw import register_review as RV
from goodlaw import overlay as OV

FAILURES = []


def check(cond, msg):
    print(f"[{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        FAILURES.append(msg)


def row(rid, a, ayear, b, byear, trust="verified", treatment="overruled", flags=(), review=None):
    r = {"id": rid, "source": "list1", "trust": trust, "treatment": treatment, "scope": None, "flags": list(flags),
         "overruled": {"name": a, "alt_names": [], "keys": [], "year": ayear, "years": [ayear]},
         "overruling": {"name": b, "keys": [], "year": byear, "date": None, "alt_names": [], "years": [byear]}}
    if review:
        r["review"] = review
    return r


# ---------------- part 1: a small register ----------------
GOOD = row("A", "Bilal Ahmed Kaloo v. State of Andhra Pradesh", 1997, "State through Superintendent of Police, CBI/SIT v. Nalini and Others", 1999)
REVERSED = row("B", "State through Superintendent of Police, CBI/SIT v. Nalini and Others", 1999, "Bilal Ahmed Kaloo v. State of Andhra Pradesh", 1997, flags=["year_order_check"])
REG = R.Register([copy.deepcopy(GOOD), copy.deepcopy(REVERSED)], {})
a, b = REG.by_id["A"], REG.by_id["B"]

check(R.held(b) and not R.held(a) and R.unwordable(b) and not R.unwordable(a), "held(): only the flagged row is held")
check(REG.clause(b) is None, "a held row gives no sentence")
check(REG.clause(a) == "Bilal Ahmed Kaloo v. State of Andhra Pradesh (1997) was overruled by State through Superintendent of Police, CBI/SIT v. Nalini and Others (1999).", f"the good row's sentence has NO chain note any more ({REG.clause(a)!r})")
check(REG.chain(a) == [], "a held row is not a step in the good row's chain")
check(REG.clause_group([a, b]) == REG.clause(a) and REG.groups([a, b]) == [[a]], "groups and clause_group leave the held row out")

ans = "The Supreme Court in Bilal Ahmed Kaloo v. State of Andhra Pradesh (1997) held that a confession is limited, and in State through Superintendent of Police, CBI/SIT v. Nalini and Others (1999) it went further."
gd = G.guard_answer(REG, ans)
check(len(gd["notes"]) == 1 and gd["notes"][0].startswith("Bilal Ahmed Kaloo") and "Nalini and Others (1999) was overruled by Bilal" not in " ".join(gd["notes"]) and "itself later" not in " ".join(gd["notes"]),
      f"the answer guard adds the one true note and nothing about Nalini being overruled ({gd['notes']})")
lines = G.prompt_facts(REG, ["Nalini and Bilal Ahmed Kaloo v. State of Andhra Pradesh (1997) and State through Superintendent of Police, CBI/SIT v. Nalini and Others (1999)"])
check(len(lines) == 1 and "Bilal Ahmed Kaloo" in lines[0] and "REGISTER FACT" in lines[0] and "Nalini and Others (1999), is" not in lines[0].split("overruled by")[0], f"the prompt gets one REGISTER FACT line, for the real direction ({lines})")
x = G.extra_notes(REG, "My brother's lawyer cites State through Superintendent of Police, CBI/SIT v. Nalini and Others (1999) for his appeal. Is it still good?", "That is a debated question.")
check(x["notes"] == [] and x["possible"] == [], f"a question that names the held row's overruled case (the later, controlling decision) draws no warning ({x})")
check(G.question_prompt_lines(REG, "He cites State through Superintendent of Police, CBI/SIT v. Nalini and Others (1999).") == [], "...and no prompt line")

# the reviewer's confirmation lifts the hold
conf = copy.deepcopy(REVERSED)
conf["review"] = {"listing_ok": "2026-10-20"}
REG2 = R.Register([copy.deepcopy(GOOD), conf], {})
check(not R.held(REG2.by_id["B"]) and REG2.clause(REG2.by_id["B"]) is not None, "once a person has confirmed the entry (review.listing_ok) it is worded again")

# other flags do not hold
other = row("C", "Alpha Beta v. State of Kerala", 1990, "Gamma Delta v. State of Goa", 1995, flags=["list_mutual_pair"], treatment="disputed_listing")
check(not R.held(other), "a list_mutual_pair row is not held (it is already worded as 'listed ... inconsistent')")

# slim export: the flag and the confirmation travel
sl = {s["id"]: s for s in R.slim([copy.deepcopy(GOOD), copy.deepcopy(REVERSED)])}
check("flags" not in sl["A"] and sl["B"].get("flags") == ["year_order_check"] and "review" not in sl["B"], "slim(): the flag travels with the held row, nothing extra for the others")
sl_conf = [s for s in R.slim([conf]) if s["id"] == "B"][0]
check(sl_conf.get("review") == {"listing_ok": "2026-10-20"}, "slim(): the confirmation travels too")
site = R.Register([s for s in R.slim([copy.deepcopy(GOOD), copy.deepcopy(REVERSED)])], {})
check(site.clause(site.by_id["B"]) is None and "itself later" not in (site.clause(site.by_id["A"]) or ""), "a register loaded from the slim bundle behaves the same")

# the weekly review still asks about it, and says what the site does
q = RV.build_queue(REG, {"flags": []}, {"proposals": []}, "2026-10-20")
if True:
    item = [i for i in q if i["item_id"] == "B"]
    check(len(item) == 1 and item[0]["kind"] == "listing" and "does not word this row until you confirm" in item[0]["evidence"] and "already in the register as A" in item[0]["evidence"], f"the weekly review keeps the item and says the site is silent on it ({item[:1]})")

# ---------------- part 2: the real register ----------------
reg = R.Register.load()
flagged = [r for r in reg.rows if "year_order_check" in (r.get("flags") or [])]
check(len(flagged) == 11 and all(R.unwordable(r) for r in flagged if not (r.get("review") or {}).get("listing_ok")), f"the real register: the {len(flagged)} flagged rows are held")
bad = []
for r in reg.rows:
    if R.unwordable(r):
        continue
    lo_a = min(r["overruled"].get("years") or [r["overruled"].get("year") or 0])
    hi_b = max(r["overruling"].get("years") or [r["overruling"].get("year") or 9999])
    if r["overruled"].get("year") and r["overruling"].get("year") and hi_b < lo_a:
        bad.append(r["id"])
check(bad == [], f"no worded row in the real register has an overruling decision wholly before the overruled one ({bad})")
nal = [r for r in reg.rows if "nalini" in r["overruled"]["name"].lower() and "kaloo" in r["overruling"]["name"].lower()]
kal = [r for r in reg.rows if "kaloo" in r["overruled"]["name"].lower() and "nalini" in r["overruling"]["name"].lower()]
check(len(nal) == 1 and len(kal) == 1 and reg.clause(nal[0]) is None, "the real Nalini / Bilal pair: the reversed row is silent")
c = reg.clause(kal[0])
check(c is not None and c.startswith("Bilal Ahmed Kaloo v. State of Andhra Pradesh (1997) was overruled by State through Superintendent of Police, CBI/SIT v. Nalini and Others") and "itself later" not in c, f"...and the true row reads cleanly ({c})")
ans_real = "In Bilal Ahmed Kaloo v. State of Andhra Pradesh (1997) the Court limited the use of a confession; that was reconsidered in State through Superintendent of Police, CBI/SIT v. Nalini and Others (1999)."
notes = G.guard_answer(reg, ans_real)["notes"]
check(not any("Nalini and Others (1999) was overruled" in n or "itself later" in n for n in notes), f"the guard on the real register no longer says Nalini was overruled ({notes})")
for name, q_ in (("Laxman", "My lawyer cites Laxman v. State of Maharashtra (2002) on dying declarations. Is it good law?"), ("Nalini", "He cites State through Superintendent of Police, CBI/SIT v. Nalini and Others (1999).")):
    check(G.extra_notes(reg, q_, "That is a debated question.")["notes"] == [], f"{name}: a question naming the later, controlling decision draws no 'overruled' note")

print("\nALL PASSED" if not FAILURES else f"\n{len(FAILURES)} FAILED: {FAILURES}")
sys.exit(1 if FAILURES else 0)
