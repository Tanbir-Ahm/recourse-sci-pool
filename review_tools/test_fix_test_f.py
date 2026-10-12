"""Tests for the stage F search (pool_runner.py --fix-test F): pooling of B's top 10 and each finalist's top 5, the finalists-only lists, the guard that runs BEFORE the hand-out, and the one-time hand-out.
Invented index and fake service (fake_pool_fixture.py); the question set is built from the writer's workbook as received into a temporary folder; nothing is sealed or handed out for real.
Run: python review_tools/test_fix_test_f.py"""
import copy
import json
import os
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fake_pool_fixture as T
import fix_arms as FA
import fix_test_set as FT
import pool_runner as P

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


HEAD = "3c80a26e42bea75e5858be6ed44a2649ec701355"
WB = os.path.join(P.ROOT, "review_data", "ruler", "inputs", "2026-10-12_Fix_Test_New_Questions_N01-N30_as_received.xlsx")
AUTH = os.path.join(P.ROOT, "review_results", "2026-10-12_new_questions_intake", "authorities_as_received.json")
N1, N2 = FA.v2_name("N1", 1.25), FA.v2_name("N2", 1.25)

# ---- build_question: top 10 of B and top 5 of each finalist -------------------------------------------------------------------------------------------
metas, hdocs = T.metas, T.hdocs
lists = {FA.B_VERSION: list(range(0, 10)), N1: [3, 0, 1, 2, 4, 20, 21, 22, 23, 24], N2: list(range(30, 40))}
rec = P.build_question({"id": "N01", "domain": "A", "kind": "narrative", "text": "q", "half": "final"}, lists, metas, hdocs, lambda d: f"Case {d}", None, top_k={FA.B_VERSION: 10, N1: 5, N2: 5})
hs = lambda ids: {metas[r]["h"] for r in ids}
pooled = {r["h"] for r in rec["rows"]}
check("the pool is B's top 10 plus each finalist's top 5 (N1's places 6 to 10 stay out unless B or N2 shows them)", pooled == hs(range(0, 10)) | hs(range(30, 35)) | hs([3, 0, 1, 2, 4]), (len(pooled)))
check("N1's places 6 to 10 are not in the pool", not (hs([20, 21, 22, 23, 24]) & pooled))
check("every pooled passage records the rank each version gave it (when it is in a top 10)", all(isinstance(r["variants"], dict) and r["variants"] for r in rec["rows"]))
check("the ordered top 10 of every version is kept for the automatic measures (named authority, stale)", set(rec["lists"]) == {FA.B_VERSION, N1, N2} and all(len(v) == 10 for v in rec["lists"].values()))
rec_int = P.build_question({"id": "N01", "domain": "A", "kind": "narrative", "text": "q", "half": "final"}, lists, metas, hdocs, lambda d: "x", None, top_k=5)
check("an integer top_k still works as before (all versions alike)", {r["h"] for r in rec_int["rows"]} == hs(range(0, 5)) | hs([3, 0, 1, 2, 4]) | hs(range(30, 35)))

# ---- run(): the lists are B and the finalists only, from ONE re-rank call per question --------------------------------------------------------------
e = T.engine()
labels = {a: set() for a in FA.S.ACTS}
qs = [{"id": "N01", "domain": "A", "kind": "narrative", "text": T.Q, "half": "final", "look_alike": True, "soft_overlap": False, "control_type": None, "acts": ["NDPS"], "acts_named": False, "trap": False, "twin_of": None}]
with tempfile.TemporaryDirectory() as t:
    ordered, stopped = P.run(None, qs, {}, e, hdocs, lambda d: f"Case {d}", t, log=lambda *_: None, challenger="rerank-3-lite", top_k={FA.B_VERSION: 10, N1: 5, N2: 5}, fix_labels=labels, fix_v2=True, fix_arms=[N1, N2])
    r0 = ordered[0]
    check("stage F lists: exactly B and the two finalists", set(r0["lists"]) == {FA.B_VERSION, N1, N2}, set(r0["lists"]))
    check("one re-rank call and one embedding for the question", e.client.rerank_calls == 1 and e.client.embed_calls == 1, (e.client.rerank_calls, e.client.embed_calls))
    check("the record carries the tags the scorer needs (look-alike, soft overlap, control type, Acts) and the Acts that fired", r0["meta"]["look_alike"] is True and r0["meta"]["acts"] == ["NDPS"] and "acts_fired" in r0, r0.get("meta"))
    e2 = T.engine()
    ordered2, _ = P.run(None, qs, {}, e2, hdocs, lambda d: "x", t + "_2", log=lambda *_: None, challenger="rerank-3-lite", top_k=10, fix_labels=labels, fix_v2=True)
    check("without fix_arms all five versions are listed (stage D2 behaviour unchanged)", len(ordered2[0]["lists"]) == 5)

# ---- the guard that runs before the hand-out --------------------------------------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as t:
    public, key = FT.build(WB, json.load(open(AUTH, encoding="utf-8")), ["N04", "N06", "N07", "N13"], HEAD, today="2026-10-12")
    sp, kp, runs = os.path.join(t, "set.json"), os.path.join(t, "key.json"), os.path.join(t, "runs.jsonl")
    json.dump(public, open(sp, "w"), sort_keys=True); json.dump(key, open(kp, "w"), sort_keys=True)
    d2pool = os.path.join(t, "pool.json")
    have = P.fix_frozen_files(*P.fix_paths("F"))[os.path.relpath(P.FIX2_RULES_PATH, P.ROOT)][0]
    json.dump({"run": {"fix_test": {"rules_sha256": have}}}, open(d2pool, "w"))
    a = SimpleNamespace(fix_set=sp, fix_key=kp, fix_arms="", fix_repeat=False)
    ok, pub, ky, fin = P.fix_guard_f(a, HEAD, runs, d2pool, finalists=[N1, N2])
    check("a complete, sealed, unhanded-out request is let through", ok == [] and pub is not None and fin == [N1, N2], ok)
    check("no finalist: refused (rules v2 section 3)", any("no finalist" in b for b in P.fix_guard_f(a, HEAD, runs, d2pool, finalists=[]) [0]))
    check("arms that differ from the finalists are refused", any("differs from the finalists" in b for b in P.fix_guard_f(SimpleNamespace(**dict(vars(a), fix_arms=N1)), HEAD, runs, d2pool, finalists=[N1, N2])[0]))
    check("arms equal to the finalists (any order) are accepted", P.fix_guard_f(SimpleNamespace(**dict(vars(a), fix_arms=f"{N2}, {N1}")), HEAD, runs, d2pool, finalists=[N1, N2])[0] == [])
    check("another index head is refused", any("index head" in b for b in P.fix_guard_f(a, "deadbeef" * 5, runs, d2pool, finalists=[N1, N2])[0]))
    bad_set = copy.deepcopy(public); bad_set["questions"][0]["text"] += " x"
    json.dump(bad_set, open(sp, "w"), sort_keys=True)
    check("a question file changed since the freeze is refused", any("changed since the freeze" in b for b in P.fix_guard_f(a, HEAD, runs, d2pool, finalists=[N1, N2])[0]))
    json.dump(public, open(sp, "w"), sort_keys=True)
    bad_key = copy.deepcopy(key); bad_key["questions"]["N03"]["key_docs"] = [1]
    json.dump(bad_key, open(kp, "w"), sort_keys=True)
    check("a key changed since the freeze is refused", any("key has changed" in b for b in P.fix_guard_f(a, HEAD, runs, d2pool, finalists=[N1, N2])[0]))
    json.dump(key, open(kp, "w"), sort_keys=True)
    json.dump({"run": {"fix_test": {"rules_sha256": "0" * 64}}}, open(d2pool, "w"))
    check("a stage D2 run made under other rules is refused", any("stage D2 was run under rules" in b for b in P.fix_guard_f(a, HEAD, runs, d2pool, finalists=[N1, N2])[0]))
    json.dump({"run": {"fix_test": {"rules_sha256": have}}}, open(d2pool, "w"))
    check("a missing stage D2 pool is refused", any("stage D2 pool" in b for b in P.fix_guard_f(a, HEAD, runs, os.path.join(t, "nope.json"), finalists=[N1, N2])[0]))
    FT.select(public, final=True, label="stage F", runs_path=runs)
    check("after a hand-out the guard refuses a second search ...", any("already handed out" in b for b in P.fix_guard_f(a, HEAD, runs, d2pool, finalists=[N1, N2])[0]))
    check("... unless it is declared a repeat after a technical failure", P.fix_guard_f(SimpleNamespace(**dict(vars(a), fix_repeat=True)), HEAD, runs, d2pool, finalists=[N1, N2])[0] == [])

# ---- the real gate file gives the finalists the frozen rule chose ---------------------------------------------------------------------------------------
fin = P.read_finalists()
check("the finalists read from the frozen stage D2 gate are N1-125 and N2-125", fin == [FA.v2_name("N1", 1.25), FA.v2_name("N2", 1.25)], fin)
check("stage F uses the v2 freeze file", P.fix_paths("F") == (P.FIX2_FREEZE_PATH, P.FIX2_RULES_PATH))
print("\nall passed" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
