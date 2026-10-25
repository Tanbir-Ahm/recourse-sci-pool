"""Tests for tier_select.py (no network, costs nothing). Run: python test_tier_select.py"""
import tier_select as ts

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def row(doc, cos, text, court="Gauhati High Court"):
    return {"doc": doc, "cos": cos, "text": text, "src": {"court": court}}


# real passages from the 2026-10-25 tier test (public Gauhati High Court judgments): two transfer petitions decided together, and a third judgment on the same section
TWIN = ("6. As per sub-clause [a] of sub-section [2] of Section 142 of the Negotiable Instruments Act, 1881, as amended, the offence under Section 138 shall be inquired into and tried "
        "only by a court within whose local jurisdiction, [a] if the cheque is delivered for collection through an account, the branch of the bank where the payee or holder in due course, "
        "as the case may be, maintains the account, is situated; or [b] if the cheque is presented for payment by the payee or holder in due course, otherwise through an account, the branch "
        "of the drawee bank where the drawer maintains the account, is situated. Having regard to the afore-stated statutory provision, the Hon’ble Supreme Court in Bridgestone India "
        "Private Limited vs. Inderpal Sing, [2016] 2 SCC 75, has held that Section 142[2][a] has vested jurisdiction in the court where the cheque is delivered for collection.")
OTHER = ("7. I have perused the materials pleadings and the submissions from both the sides. Before proceeding further reference may be made to section 142 (2)(a), which says that :- "
         "“(2) The offence under section 138 shall be inquired into and tried only by a court within whose local jurisdiction,- (a) if the cheque is delivered for collection through an account, "
         "the branch of the bank where the payee or holder in due course, as the case may be, maintains the account, is situated.”")
THIRD = ("18. The presumption under Section 139 of the Negotiable Instruments Act is a rebuttable presumption, and for the accused to rebut it the petitioner has to lead evidence or produce "
         "material documents, something which should be more than mere denial and mere suggestions, as the Supreme Court has held in several decisions.")

r = ts.pick([row(1, 0.61, TWIN), row(2, 0.61, TWIN), row(3, 0.58, OTHER), row(4, 0.55, THIRD)])
check(sorted(x["doc"] for x in r) == [1, 3, 4], "two petitions with the same text show once, and the next candidate takes the freed place")
check([x["doc"] for x in r] == [1, 3, 4], "THIRD does not jump the queue: it carries the Supreme Court's words, but a High Court judgment quoting the Supreme Court stays at High Court rank (owner's decision)")
by_doc = {x["doc"]: x for x in r}
check(by_doc[1]["also_in"] == [2] and by_doc[3]["also_in"] == [] and by_doc[4]["also_in"] == [], "the kept result names the judgment it stands for")
check("_sh" not in r[0] and set(r[0]) == {"doc", "cos", "text", "src", "also_in", "authority", "voice_line"}, "no working data leaks into the result, and the verdict comes back with it")

rows = [row(1, 0.61, TWIN), row(2, 0.61, TWIN)]
before = [dict(x) for x in rows]
ts.pick(rows)
check(rows == before, "the input rows are not changed")

r = ts.pick([row(1, 0.61, TWIN), row(2, 0.60, TWIN.replace("6. As per", "7. As per"))])
check([x["doc"] for x in r] == [1] and r[0]["also_in"] == [2], "a different paragraph number does not make a passage new")

r = ts.pick([row(1, 0.61, TWIN), row(2, 0.60, OTHER)])
check([x["doc"] for x in r] == [1, 2], "two passages on the same section in different words are both shown")

r = ts.pick([row(1, 0.61, TWIN), row(1, 0.60, THIRD), row(2, 0.59, OTHER)])
check([x["doc"] for x in r] == [1, 2], "one passage per judgment: the second passage of a judgment is skipped")

r = ts.pick([row(1, 0.49, TWIN), row(2, 0.50, OTHER), row(3, 0.51, THIRD)])
check(sorted(x["doc"] for x in r) == [2, 3], "a cosine under the bar is dropped; exactly on the bar is kept")

# ---------------------------------------------------------------- the owner's order, enforced here (authority.py decides whose words they are)
SC_QUOTE = "In Vijaysinh the Supreme Court has held that the requirements of Section 50 of the NDPS Act are mandatory and must be strictly complied with."
TRIAL_QUOTE = "The learned Chief Judicial Magistrate held that the offence under Section 389 of the Indian Penal Code is a non-compoundable offence and rejected the prayer."
ARGUMENT = "Mr. M.K. Borah, learned counsel for the petitioner submits that the allegations levelled in the FIR are fabricated and frivolous."
r = ts.pick([row(1, 0.99, ARGUMENT), row(2, 0.90, TRIAL_QUOTE), row(3, 0.55, SC_QUOTE)])
check([x["doc"] for x in r] == [3, 2], "the High Court's own-rank words come before the trial court's, although the trial court scored higher")
r_sc = ts.pick([row(2, 0.90, "The High Court held that the complaint is not maintainable and the petition must fail.", "Supreme Court of India"),
                row(3, 0.55, "We are unable to agree with that view and we hold that the complaint is maintainable.", "Supreme Court of India")])
check([x["doc"] for x in r_sc] == [3, 2], "in a Supreme Court judgment the strict order puts the Court's own words above its recital of the High Court's view, whatever the scores")
r_hc = ts.pick([row(5, 0.95, SC_QUOTE), row(6, 0.60, TWIN)])
check([x["authority"]["tier"] for x in r_hc] == [1, 2] and [x["doc"] for x in r_hc] == [5, 6] and r_hc[0]["voice_line"].startswith("the Supreme Court, as quoted by Gauhati High Court"),
      "a High Court judgment quoting the Supreme Court keeps High Court rank (score decides against the court's own words) and says whose words it shows")
r_p = ts.pick([row(5, 0.55, SC_QUOTE), row(6, 0.60, TWIN)], promote=True)
check([x["doc"] for x in r_p] == [5, 6], "promote=True, the plain reading, would lift the quoted Supreme Court above the court's own words: measured, not chosen")
check(all(x["doc"] != 1 for x in r), "the lawyer's argument is not shown at all, although it scored highest")
check(r[0]["authority"]["tier"] == 1 and r[1]["authority"]["tier"] == 3, "each result says whose words it carries")
r2 = ts.pick([row(1, 0.99, ARGUMENT), row(2, 0.90, TRIAL_QUOTE), row(3, 0.55, SC_QUOTE)], by_authority=False)
check([x["doc"] for x in r2] == [2, 3], "with the order switched off the argument is still dropped, but the trial court stays on top (which is what the order fixes)")
try:
    ts.verify([{"voice_line": "x", "authority": {"tier": 3, "states_law": True, "blocked": False}}, {"voice_line": "x", "authority": {"tier": 1, "states_law": True, "blocked": False}}])
    check(False, "verify refuses a list that puts a lower court above a higher one")
except AssertionError:
    check(True, "verify refuses a list that puts a lower court above a higher one")
try:
    ts.verify([{"doc": 1, "authority": {"tier": 2, "states_law": True, "blocked": False}}])
    check(False, "verify refuses a result that has no line saying whose words it shows")
except AssertionError:
    check(True, "verify refuses a result that has no line saying whose words it shows")
try:
    ts.verify([{"authority": {"tier": None, "states_law": False, "blocked": True, "reason": "x"}}])
    check(False, "verify refuses a list with a blocked passage in it")
except AssertionError:
    check(True, "verify refuses a list with a blocked passage in it")

many = [row(i, 0.9 - i / 100, f"distinct passage number {i} " + " ".join(f"word{i}x{j}" for j in range(20))) for i in range(1, 6)]
check([x["doc"] for x in ts.pick(many)] == [1, 2, 3] and len(ts.pick(many, max_results=2)) == 2, "at most the maximum are kept, best first")

r = ts.pick(many[:3] + [row(9, 0.52, many[0]["text"])])
check([x["doc"] for x in r] == [1, 2, 3] and r[0]["also_in"] == [9], "a twin that comes after the list is full is still recorded under the result it repeats")

check(ts.pick([]) == [], "no candidates, no results")
check(ts.pick([row(1, 0.4, TWIN)]) == [], "nothing over the bar, nothing shown")
check(ts.same_passage({"a", "b"}, {"c"}) is False and ts.same_passage(set(), {"a"}) is False, "no shared shingle is never the same passage")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED:")
    for f in FAILURES:
        print("  -", f)
    raise SystemExit(1)
print("ALL PASSED")
