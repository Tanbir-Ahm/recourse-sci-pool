"""Tests for review_tools/fix_preflight.py (no network, no spend, no question handed out). Run: python review_tools/test_fix_preflight.py"""
import json
import os
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_preflight as F
import fix_test_set as FT

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


cmds = dict((t.split(" ")[0], c) for t, c in F.commands("2026-11-01"))
check("the search command names stage F, the cap, a label and all three side indexes", all(x in cmds["1."] for x in ("--fix-test F", "--max-rerank-tokens 3000000", "--label")) and all(s in cmds["1."] for s in F.PR.FINAL_SIDE_INDEXES), cmds["1."])
check("the pack, the normaliser, the two scoring stages and the reading sheet follow in order", "build_sealed_pack.py --fix-test" in cmds["2."] and "normalise_replies.py" in cmds["3."] and " marks " in cmds["4."] and " key " in cmds["5."] and "fix_reading_sheet.py" in cmds["6."])
check("every test suite the preflight runs exists", all(os.path.exists(os.path.join(F.HERE, t)) for t in F.TEST_SUITES), [t for t in F.TEST_SUITES if not os.path.exists(os.path.join(F.HERE, t))])
# stub the repository facts so that the logic can be tested without a real sealed set
d = tempfile.mkdtemp()
WB = os.path.join(F.ROOT, "review_data", "ruler", "inputs", "2026-10-12_Fix_Test_New_Questions_N01-N30_as_received.xlsx")
AUTH = os.path.join(F.ROOT, "review_results", "2026-10-12_new_questions_intake", "authorities_as_received.json")
HEAD = "3c80a26e42bea75e5858be6ed44a2649ec701355"
public, key = FT.build(WB, json.load(open(AUTH, encoding="utf-8")), [], HEAD, today="2026-10-12")
sp, kp = os.path.join(d, "set.json"), os.path.join(d, "key.json")
json.dump(public, open(sp, "w")); json.dump(key, open(kp, "w"))
FT.DEFAULT_SET, FT.DEFAULT_KEY = sp, kp
FT.read_runs = lambda p=None: []
F.PR.code_state = lambda: ("c" * 40, [])
F.PR.index_head = lambda x: HEAD
F.sh = lambda *c: SimpleNamespace(stdout="0\n" if "rev-list" in c else "claude/test\n")
res = F.checks(SimpleNamespace(no_tests=True, owner_confirms=""))
fails = [r["check"] for r in res if not r["ok"] and not r["check"].startswith("OWNER")]
check("with a sealed set, a clean pushed checkout and the recorded index head, nothing fails except what depends on this machine (the Voyage key, the side indexes)", all(("VOYAGE" in f or "side index" in f) for f in fails), fails)
owner = [r for r in res if r["check"].startswith("OWNER")]
check("the four owner items are open when nothing is confirmed", len(owner) == 4 and not any(r["ok"] for r in owner))
res2 = F.checks(SimpleNamespace(no_tests=True, owner_confirms="writer-declaration,advocate-key,balance,refresh-postponed"))
check("naming them closes them", all(r["ok"] for r in res2 if r["check"].startswith("OWNER")))
F.FT.read_runs = lambda p=None: [{"ts": "x"}]
res3 = F.checks(SimpleNamespace(no_tests=True, owner_confirms=""))
check("a logged hand-out makes the preflight fail", any("no hand-out is logged" in r["check"] and not r["ok"] for r in res3))
F.FT.read_runs = lambda p=None: []
F.PR.code_state = lambda: ("c" * 40, ["review_tools/pool_runner.py"])
res4 = F.checks(SimpleNamespace(no_tests=True, owner_confirms=""))
check("a dirty checkout makes the preflight fail", any("checkout clean" in r["check"] and not r["ok"] for r in res4))
F.PR.code_state = lambda: ("c" * 40, [])
F.PR.index_head = lambda x: "deadbeef" * 5
res5 = F.checks(SimpleNamespace(no_tests=True, owner_confirms=""))
check("another index head makes the preflight fail", any("index head" in r["check"] and not r["ok"] for r in res5))
F.PR.index_head = lambda x: HEAD
bad = json.load(open(sp)); bad["questions"][0]["text"] += " x"; json.dump(bad, open(sp, "w"))
res6 = F.checks(SimpleNamespace(no_tests=True, owner_confirms=""))
check("a changed question file makes the preflight fail", any("freeze hashes" in r["check"] and not r["ok"] for r in res6))
src = open(os.path.join(F.HERE, "fix_preflight.py"), encoding="utf-8").read()
check("the preflight never calls select(), so it cannot hand a question out", ".select(" not in src)
print("\nall passed" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
