"""Tests for review_tools/fix_arms.py and the --fix-test wiring of pool_runner.py (invented data, fake service, no network, no spend). Run: python review_tools/test_fix_arms.py"""
import json
import os
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_arms as FA
import pool_runner as P

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


# ---- C: cap of 2 per judgment in the top 5 ---------------------------------------------------------------------------------------------------------
doc = {r: ("X" if r in "abcd" else "Y" if r in "efg" else r.upper()) for r in "abcdefghijklmnop"}
order = list("abcdefghijklmnop")
got = FA.cap_per_judgment(order, doc.get)
check("C: a third passage of the same judgment is skipped in the top 5", got[:5] == list("abefg") or got[:5] == ["a", "b", "e", "f", "h"], got)
check("C: exact top 5 for judgments X (a to d) and Y (e to g)", got[:5] == ["a", "b", "e", "f", "h"], got[:5])
check("C: places 6 to 10 are the best of everything not placed, in score order (skipped passages come back)", got[5:] == ["c", "d", "g", "i", "j"], got[5:])
check("C: no passage twice, ten shown", len(got) == 10 and len(set(got)) == 10)
check("C: with no judgment over the cap the list is the plain score order", FA.cap_per_judgment(list("abcdefghijkl"), {r: r for r in "abcdefghijkl"}.get) == list("abcdefghij"))
check("C: if the cap cannot fill the top 5 (every candidate from one judgment) the skipped passages follow in score order, so nothing is lost", FA.cap_per_judgment(list("abcdefghijkl"), lambda r: "Z") == list("abcdefghij"))
check("C: fewer candidates than ten is fine", FA.cap_per_judgment(list("abc"), lambda r: "Z") == list("abc"))

# ---- N1 and N2: the boost ---------------------------------------------------------------------------------------------------------------------------
Q_NI = "My cheque bounced and the bank sent a memo; can the payee file a complaint under section 138 of the Negotiable Instruments Act?"
Q_PLAIN = "My husband beat me and threw me out of the house; what can I do?"
Q_NONE = "Is anticipatory bail available for a theft case?"
labels = {a: set() for a in FA.S.ACTS}
labels["NI Act"] = {7}
labels["PWDVA"] = {8}
final = {1: 1.00, 2: 0.95, 3: 0.92, 4: 0.80}
docof = {1: 5, 2: 7, 3: 7, 4: 8}.get
b = FA.apply_boost(final, docof, {7})
check("the boost multiplies every passage of a labelled judgment by 1.10, once, and nothing else", b == {1: 1.00, 2: 0.95 * 1.10, 3: 0.92 * 1.10, 4: 0.80}, b)
check("no judgment labelled: scores unchanged", FA.apply_boost(final, docof, set()) == final)
out, fired = FA.arms(Q_NI, final, docof, labels)
check("B is the score order", out[FA.B_VERSION] == [1, 2, 3, 4], out[FA.B_VERSION])
check("N1 fires on a precise question and lifts the labelled judgment over the unlabelled passage", fired["N1"] == ["NI Act"] and out[FA.N1_VERSION] == [2, 3, 1, 4] or out[FA.N1_VERSION][:2] == [2, 1], (fired, out[FA.N1_VERSION]))
check("N1 order: passage 2 (0.95 x 1.10 = 1.045) first, then 1 (1.00)", out[FA.N1_VERSION][:2] == [2, 1] or out[FA.N1_VERSION][0] == 2, out[FA.N1_VERSION])
out, fired = FA.arms(Q_PLAIN, final, docof, labels)
check("a plain-language question fires N2 but not N1; N1 then equals B and N2 lifts the PWDVA judgment", fired["N1"] == [] and fired["N2"] == ["PWDVA"] and out[FA.N1_VERSION] == out[FA.B_VERSION], fired)
check("N2 boosted passage 4 (0.80 x 1.10 = 0.88) but it stays last: a boost is 10 percent, not a jump", out[FA.N2_VERSION] == [1, 2, 3, 4], out[FA.N2_VERSION])
out, fired = FA.arms(Q_NONE, final, docof, labels)
check("no Act fires: all four arms but C are the plain order", fired == {"N1": [], "N2": []} and out[FA.N1_VERSION] == out[FA.N2_VERSION] == out[FA.B_VERSION], (fired, out))
check("a general-code question never boosts (a question about BNSS/CrPC fires no Act)", FA.boosted_docs("What does section 438 of the CrPC say about anticipatory bail?", "N2", labels) == ([], set()))

# ---- the engine: one retrieval, one re-rank call, four arms from the same scores ------------------------------------------------------------------
import fake_pool_fixture as T
e = T.engine()
lists, fired = e.lists_for_fix(T.Q, "rerank-3-lite", {a: set() for a in FA.S.ACTS})
check("four arms, ten each, from ONE re-rank call and ONE embedding", sorted(lists) == sorted(FA.FIX_VERSIONS) and all(len(v) == 10 for v in lists.values()) and e.client.rerank_calls == 1 and e.client.embed_calls == 1, (sorted(lists), e.client.rerank_calls, e.client.embed_calls))
check("B equals the final recipe's challenger arm on the same question (the baseline is unchanged)", lists[FA.B_VERSION] == T.engine().lists_for_final(T.Q, "rerank-3-lite")[P.R_VERSION])
check("the model passed is the challenger", e.spend.rerank_by_model.get("rerank-3-lite", 0) > 0 and not e.spend.rerank_by_model.get("rerank-2", 0), dict(e.spend.rerank_by_model))

# ---- rules v2: four candidates (N1, N2 at 1.25 and 1.50) from the same scores ----------------------------------------------------------------------
check("v2 versions: B plus four named candidates, sizes 1.25 and 1.50 only", len(FA.V2_VERSIONS) == 5 and FA.SIZES_V2 == (1.25, 1.50) and len(set(FA.V2_VERSIONS)) == 5, FA.V2_VERSIONS)
fin2 = {1: 1.00, 2: 0.80, 3: 0.60}
doc2 = {1: 5, 2: 7, 3: 7}.get
lab2 = {a: set() for a in FA.S.ACTS}
lab2["NI Act"] = {7}
o2, f2 = FA.arms_v2(Q_NI, fin2, doc2, lab2)
check("v2: 0.80 x 1.25 = 1.00 ties and 0.80 x 1.50 = 1.20 passes the 1.00 passage (sorted order is stable for the tie)", o2[FA.v2_name("N1", 1.50)][0] == 2 and o2[FA.v2_name("N1", 1.25)][:2] in ([1, 2], [2, 1]), o2)
check("v2: B is unchanged and a question that fires nothing leaves every candidate equal to B", FA.arms_v2(Q_NONE, fin2, doc2, lab2)[0][FA.v2_name("N2", 1.50)] == [1, 2, 3])
check("v2: a plain-language question moves only the N2 candidates", FA.arms_v2(Q_PLAIN, fin2, doc2, {**lab2, "PWDVA": {7}})[0][FA.v2_name("N1", 1.50)] == [1, 2, 3] and FA.arms_v2(Q_PLAIN, fin2, doc2, {**lab2, "PWDVA": {7}})[0][FA.v2_name("N2", 1.50)][0] == 2)

# ---- the guard ----------------------------------------------------------------------------------------------------------------------------------------
def args(**kw):
    base = dict(fix_test="D", challenger_model="rerank-3-lite", max_rerank_tokens=3_000_000, allow_other_index=False, source="real30", supplement=[os.path.join(P.ROOT, d) for d in P.FINAL_SIDE_INDEXES])
    base.update(kw)
    return SimpleNamespace(**base)
ok_files, ok_code = {"r.md": ("a" * 64, "a" * 64)}, ("c" * 40, [])
check("the guard lets a frozen, clean stage D request through", P.fix_guard(args(), ok_code, ok_files) == [], P.fix_guard(args(), ok_code, ok_files))
for label, kw, frag in [("another challenger", dict(challenger_model="rerank-3"), "arms use"), ("a cap over 3 million", dict(max_rerank_tokens=4_000_000), "cap"), ("another index", dict(allow_other_index=True), "allow-other-index"),
                        ("the ruler as source", dict(source="ruler"), "real30"), ("a missing side index", dict(supplement=[]), "side index"), ("an unknown stage", dict(fix_test="X"), "only stage D")]:
    got = P.fix_guard(args(**kw), ok_code, ok_files)
    check(f"the guard refuses {label}", bool(got) and any(frag in g for g in got), got)
check("stage D2 is accepted by the guard", P.fix_guard(args(fix_test="D2"), ok_code, ok_files) == [])
check("D2 reads the v2 freeze file and rules", P.fix_paths("D2") == (P.FIX2_FREEZE_PATH, P.FIX2_RULES_PATH) and P.fix_paths("D") == (P.FIX_FREEZE_PATH, P.FIX_RULES_PATH))
f2files = P.fix_frozen_files(*P.fix_paths("D2"))
check("the real v2 freeze pins v1 rules, v2 rules, the spec code, its JSON and its tests, all matching now", len(f2files) == 5 and all(n == f for n, f in f2files.values()) and any(k.endswith("FIX_TEST_RULES_v2.md") for k in f2files) and any(k.endswith("FIX_TEST_RULES_v1.md") for k in f2files), f2files)
check("the guard refuses a changed file", any("frozen hash" in g for g in P.fix_guard(args(), ok_code, {"r.md": ("b" * 64, "a" * 64)})))
check("the guard refuses a file the freeze does not list", any("not listed" in g for g in P.fix_guard(args(), ok_code, {"r.md": ("b" * 64, None)})))
check("the guard refuses a dirty checkout", any("uncommitted" in g for g in P.fix_guard(args(), ("c" * 40, ["x.py"]), ok_files)))
frozen = P.fix_frozen_files()
check("the real freeze file lists the rules, the spec code, the spec JSON and the spec tests, all matching now", len(frozen) == 4 and all(n == f for n, f in frozen.values()), frozen)
with tempfile.TemporaryDirectory() as d:
    fz = os.path.join(d, "x.freeze")
    open(os.path.join(d, "f.txt"), "w").write("hello")
    import hashlib
    open(fz, "w").write(hashlib.sha256(b"hello").hexdigest() + "  f.txt\n")
    got = P.fix_frozen_files(fz, root=d)
    check("fix_frozen_files compares a listed file with its recorded hash", got["f.txt"][0] == got["f.txt"][1], got)
check("stage D question ids are exactly the 19 tuning questions plus R16, R23, R03", len(P.STAGE_D_IDS) == 22 and len(set(P.STAGE_D_IDS)) == 22 and {"R16", "R23", "R03"} <= set(P.STAGE_D_IDS))
sealed_rest = {"R05", "R07", "R10", "R13", "R18", "R25", "R27", "R30"}
check("no other sealed question is in stage D", not (sealed_rest & set(P.STAGE_D_IDS)))
real = json.load(open(P.DEFAULT_REAL, encoding="utf-8"))
tuning = {q["id"] for q in real["questions"] if q["half"] == "dev"}
check("all but the three known failures are tuning questions, and all exist in the question file", set(P.STAGE_D_IDS) - {"R16", "R23", "R03"} == tuning and set(P.STAGE_D_IDS) <= {q["id"] for q in real["questions"]}, sorted(set(P.STAGE_D_IDS) - tuning))

print("\nall passed" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
