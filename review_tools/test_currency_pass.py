"""Tests for the currency pass (review_tools/currency_pass.py): the register's retrieval lock over saved search results, the stale-exposure counts, the demotion arm,
and a gate on the real first pool. Run: python review_tools/test_currency_pass.py
The real-pool gate needs the sibling index checkout and the corpus store (set RECOURSE_CORPUS=/path/corpus.sqlite); it says SKIP otherwise."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import currency_pass as CP
from goodlaw import register as R
from goodlaw import register_guard as G

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


reg = R.Register.load()

# ---- small helpers ----------------------------------------------------------------------------------------------------------------------------------

check("name_year splits a label", CP.name_year("Prabha Shankar Dubey v. State of M.P. (2003)") == ("Prabha Shankar Dubey v. State of M.P.", 2003))
check("name_year keeps a label with no year whole", CP.name_year("Some case") == ("Some case", None))


def split(name):
    pet, _, resp = name.partition(" v. ")
    return pet, resp


def find_row(trust, action):
    """A register row of the given trust whose own case the retrieval lock flags with `action` when named by its own title and year."""
    for row in reg.rows:
        if row["trust"] != trust or not row["overruled"].get("name") or " v. " not in row["overruled"]["name"]:
            continue
        pet, resp = split(row["overruled"]["name"])
        info = {"pet": pet, "resp": resp, "year": row["overruled"].get("year"), "insc": None}
        if G.retrieval_flags(reg, [CP.chunk(info, "")])[0]["action"] == action:
            return info
    return None


firm, cand = find_row("verified", "demote_and_badge"), find_row("candidate", "badge")
check("the register has a firm row the lock demotes, found by title and year", firm is not None)
check("the register has a candidate row the lock only badges", cand is not None)

CLEAN = {"doc_key": "c2", "pet": "Zzzz Qqqqq", "resp": "Wwwww Eeeee", "year": 2000, "insc": None}
STALE = {"doc_key": "c3", "pet": "Alpha Betaaa", "resp": "Gamma Deltaa", "year": 2000, "insc": None}
table = {1: dict(firm, doc_key="c1"), 2: CLEAN, 3: STALE}
cases = [{"name": "Alpha Betaaa v. Gamma Deltaa (2000)", "doc_key": "c3", "expect": "adverse"},
         {"name": "Zzzz Qqqqq v. Wwwww Eeeee (2000)", "doc_key": "c2", "expect": "not_adverse"}]


def row(n, doc, **variants):
    return {"n": n, "doc": doc, "text": "x", "variants": variants}


pool = [{"qid": "Q1", "rows": [row(1, 1, **{"A today": 1, "S site shown": 1}), row(2, 2, **{"A today": 2, "S site shown": 2}), row(3, 3, **{"A today": 3, "S site shown": 3})]}]
res = CP.analyse(pool, reg, table, cases, k=2)
a, s = res["versions"]["A today"], res["versions"]["S site shown"]
check("a version is counted over its top k only", a["slots"] == 2 and a["own_firm"] == 1, a)
check("a version starting with S is counted over everything it showed", s["slots"] == 3, s)
check("a stale passage outside the top k is not counted for that version", a.get("stale_slots", 0) == 0 and s["stale_slots"] == 1, (a, s))
check("a stale passage the register does not hold goes through unflagged", s.get("stale_slots_flagged", 0) == 0)
check("demotion moves the firm-row case out of the top k", a["after_slots_changed"] == 1, a)
check("and can pull a stale passage into the top k, which the report must show", a["after_stale_slots"] == 1, a)
check("the stale passage is listed with its question, number and version", res["stale_slots"] == [{"qid": "Q1", "n": 3, "version": "S site shown", "doc": 3, "case": cases[0]["name"], "register_action": None}], res["stale_slots"])
check("the pool is not changed by the pass", pool[0]["rows"][0]["variants"] == {"A today": 1, "S site shown": 1})

pool2 = copy.deepcopy(pool)
pool2[0]["rows"][0]["doc"] = 99
res2 = CP.analyse(pool2, reg, table, cases, k=2)
check("a passage whose judgment has no case information is counted as such and never flagged", res2["passages_without_case_info"] == 1 and res2["versions"]["A today"]["own_firm"] == 0)

rv = CP.register_view(reg, [{"name": f"{firm['pet']} v. {firm['resp']} ({firm['year']})", "expect": "not_adverse"}, {"name": "Alpha Betaaa v. Gamma Deltaa (2000)", "expect": "adverse"}])
check("register_view reports a settled case the register holds as a false alarm", rv[0]["in_register"] and rv[0]["false_alarm"], rv[0])
check("register_view reports an unheld stale case as not in the register", not rv[1]["in_register"] and not rv[1]["false_alarm"], rv[1])

pool3 = [{"qid": "Q1", "rows": [dict(row(1, 1, **{"A today": 1}), text="")]}]
cand_table = {1: dict(cand, doc_key="c1")}
r3 = CP.analyse(pool3, reg, cand_table, [], k=5)
check("a candidate-row case is badged, not demoted", r3["versions"]["A today"]["own_candidate"] == 1 and r3["versions"]["A today"]["own_firm"] == 0 and r3["versions"]["A today"]["after_slots_changed"] == 0, r3["versions"]["A today"])

text = CP.report(res)
check("the report says it is private and not for reviewers", "Never send to reviewers" in text and "PRIVATE" in text)
check("the report never calls a case good law", "good law" in text and "never says a case is good law" in text)

# ---- the known lists ----------------------------------------------------------------------------------------------------------------------------------

kc = CP.known_cases()
exp = {}
for c in kc:
    exp[c["expect"]] = exp.get(c["expect"], 0) + 1
check("the known lists hold the checker's 7 adverse and 13 settled cases plus 3 added", exp.get("adverse") == 8 and exp.get("not_adverse") == 13 and exp.get("adverse_in_part") == 2, exp)
check("every added stale case says what the later court said", all(c.get("basis") and c.get("source") for c in kc if c["name"].startswith(("Krishna", "Mohan", "Siddharam"))))

# ---- the real first pool --------------------------------------------------------------------------------------------------------------------------------

corpus = os.environ.get("RECOURSE_CORPUS") or os.path.join(CP.ROOT, "corpus.sqlite")
if os.path.exists(corpus) and os.path.isdir(os.path.join(CP.DEFAULT_INDEX, "index")):
    real_pool = json.load(open(CP.DEFAULT_POOL, encoding="utf-8"))
    tab = CP.case_table(CP.DEFAULT_INDEX, corpus)
    out = CP.analyse(real_pool, reg, tab, kc, 5)
    check("all 199 passages of the first pool are described by the corpus store", out["passages"] == 199 and out["passages_without_case_info"] == 0, (out["passages"], out["passages_without_case_info"]))
    names = ("PRABHA SHANKAR DUBEY", "KRISHNA JANARDHAN BHAT")
    stale_docs = {d for d, i in tab.items() if (i["pet"] or "").upper() in names}
    ok = True
    for v, st in out["versions"].items():
        direct = sum(1 for q in real_pool for r in CP.top_rows(q["rows"], v, 5) if r["doc"] in stale_docs)
        ok = ok and direct == st.get("stale_slots", 0)
    check("stale slots per version agree with a direct recount from the pool", ok)
    check("the register wrongly flags none of the 13 known-settled cases", not [x for x in out["register"] if x["false_alarm"]], [x["name"] for x in out["register"] if x["false_alarm"]])
else:
    print("SKIP real-pool gate: no corpus store (set RECOURSE_CORPUS) or no index checkout")

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
