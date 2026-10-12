"""Tests for review_tools/score_fix_stage_d.py on an invented pool and key. Run: python review_tools/test_score_fix_stage_d.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_arms as FA
import score_fix_stage_d as SD

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


def item(doc, h=None):
    return {"doc": doc, "h": h or f"h{doc}", "also": []}


def lists(b, c, n1, n2):
    return {FA.B_VERSION: [item(d) for d in b], FA.C_VERSION: [item(d) for d in c], FA.N1_VERSION: [item(d) for d in n1], FA.N2_VERSION: [item(d) for d in n2]}


filler = list(range(500, 520))
key = {"questions": {
    "T1": {"reachable": True, "key_docs": [1], "stale_docs": [{"doc": 9, "label": "Old", "kind": "overruled", "counts_as_stale": True}], "authorities": []},
    "T2": {"reachable": True, "key_docs": [2], "stale_docs": [], "authorities": []},
    "R16": {"reachable": True, "key_docs": [16], "stale_docs": [], "authorities": []},
    "R23": {"reachable": True, "key_docs": [23], "stale_docs": [], "authorities": []},
    "R03": {"reachable": True, "key_docs": [3], "stale_docs": [], "authorities": []}}}
pool = [
    {"qid": "T1", "lists": lists([9] + filler[:9], filler[:10], [1] + filler[:9], filler[:10])},                  # B has the stale ruling at 1 and no key; N1 has the key
    {"qid": "T2", "lists": lists(filler[:9] + [2], filler[:9] + [2], filler[:10], filler[:9] + [2])},             # key at 10 in B, C, N2; N1 loses it
    {"qid": "R16", "lists": lists(filler[:10], filler[:4] + [16] + filler[:5], filler[:10], filler[:10])},       # only C brings the key judgment into the top 5
    {"qid": "R23", "lists": lists(filler[:10], filler[:10], filler[:10], filler[:10])},
    {"qid": "R03", "lists": lists(filler[:10], filler[:10], filler[:10], filler[:10])},
]
table, scores = SD.gate(pool, key, ["T1", "T2"])
r = table["rows"]
check("B: one key authority in the top 10 (T2), one stale slot (T1)", r[FA.B_VERSION]["named_authority_top10"] == 1 and r[FA.B_VERSION]["stale_slots_top5"] == 1, r[FA.B_VERSION])
check("known failures are not counted in the tuning totals", r[FA.B_VERSION]["answerable_tuning_questions"] == 2)
v = table["verdict"]
check("C: authority 1 >= 1, stale 0 <= 1, R16 key in top 5: goes to stage F", v[FA.C_VERSION]["goes to stage F"], v[FA.C_VERSION])
check("N1: authority 1 (gains T1, loses T2) >= 1, stale 0, but R16 not in top 5: fails condition 3 only", not v[FA.N1_VERSION]["goes to stage F"] and not v[FA.N1_VERSION]["3 R16 key judgment in top 5"] and v[FA.N1_VERSION]["1 named authority top 10 >= B"] and v[FA.N1_VERSION]["2 stale slots top 5 <= B"], v[FA.N1_VERSION])
check("N2: authority 1 >= 1 and stale ok, but R16 not in top 5: fails", not v[FA.N2_VERSION]["goes to stage F"])
table2, _ = SD.gate(pool, key, ["T1", "T2"], tokens_by_arm={FA.C_VERSION: 1.81})
check("tokens above 1.8 x B fail condition 4", not table2["verdict"][FA.C_VERSION]["4 tokens <= 1.8 x B"])
ch = SD.churn(pool)
check("churn counts questions whose top 5 / top 10 differ from B's", ch[FA.C_VERSION]["top5_changed"] == 2 and ch[FA.C_VERSION]["top10_changed"] == 2, ch)
check("churn: N1 changed T1 (top 5) and T2 (place 10 only), nothing else", ch[FA.N1_VERSION]["top10_changed"] == 2 and ch[FA.N1_VERSION]["top5_changed"] == 1, ch[FA.N1_VERSION])
# ---- rules v2 gate: per trigger the smaller passing size, condition 5 --------------------------------------------------------------------------
def lists2(**over):
    base = filler[:10]
    d = {v: [item(x) for x in base] for v in FA.V2_VERSIONS}
    d.update({k: [item(x) for x in v] for k, v in over.items()})
    return d
N1a, N1b, N2a, N2b = (FA.v2_name(t, z) for t in ("N1", "N2") for z in FA.SIZES_V2)
pool2 = [
    {"qid": "T1", "lists": lists2()},
    {"qid": "T2", "lists": lists2()},
    {"qid": "R16", "lists": lists2(**{N1b: filler[:4] + [16] + filler[:5], N2a: filler[:4] + [16] + filler[:5], N2b: filler[:4] + [16] + filler[:5]})},
    {"qid": "R23", "lists": lists2()},
    {"qid": "R03", "lists": lists2()},
]
t2, _ = SD.gate_v2(pool2, key, ["T1", "T2"])
check("v2: N1-125 fails (R16 not in top 5), N1-150 passes", not t2["verdict"][N1a]["passes"] and t2["verdict"][N1b]["passes"], t2["verdict"][N1a])
check("v2: N2 finalist is the SMALLER passing size (125) though 150 also passes", t2["finalists"] == {"N1": N1b, "N2": N2a}, t2["finalists"])
pool3 = [dict(q) for q in pool2]
pool3[0] = {"qid": "T1", "lists": lists2(**{N1b: [9] + filler[:9]})}              # N1-150 now puts a known-stale ruling in the top 5
t3, _ = SD.gate_v2(pool3, key, ["T1", "T2"])
check("v2: more stale slots than B fails condition 2 and, with no other size passing, N1 has no finalist", not t3["verdict"][N1b]["2 stale slots top 5 <= B"] and t3["finalists"]["N1"] is None, t3["finalists"])
many = [{"qid": f"T{i}", "lists": lists2(**{N2a: list(reversed(filler[:10]))})} for i in range(9)]
many += [q for q in pool2 if q["qid"] in ("R16", "R23", "R03")]
kk = {"questions": {**{f"T{i}": {"reachable": True, "key_docs": [1], "stale_docs": [], "authorities": []} for i in range(9)}, **{q: key["questions"][q] for q in ("R16", "R23", "R03")}}}
t4, _ = SD.gate_v2(many, kk, [f"T{i}" for i in range(9)])
check("v2: changing the top 5 on 10 questions (9 here and R16) fails condition 5 (limit 8)", t4["rows"][N2a]["top5_changed"] == 10 and not t4["verdict"][N2a]["5 top 5 changed on <= 8 of 22"], t4["rows"][N2a])
print("\nall passed" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
