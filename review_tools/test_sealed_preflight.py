"""Tests for review_tools/sealed_preflight.py (no network, no spend, no sealed question handed out). Run: python review_tools/test_sealed_preflight.py"""
import os
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sealed_preflight as F

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


d = tempfile.mkdtemp()
p = os.path.join(d, "rules.md")
open(p, "w").write("# rules\n\nbody\n\n## Amendments\n(none)\n")
check("no amendments are listed as none", F.amendments(p) == [])
open(p, "w").write("# rules\n\n## Amendments\n- 2026-10-11: pooled means the mean of the per-question shares (reason: the tuning comparators were computed so)\n")
check("an amendment line is listed", len(F.amendments(p)) == 1 and "2026-10-11" in F.amendments(p)[0])

cmds = dict((t.split(" ")[0], c) for t, c in F.commands("2026-11-01"))
check("the search command names the final recipe, the cap, the label and all three side indexes", all(x in cmds["1."] for x in ("--final-recipe", "--half sealed --final", "--max-rerank-tokens 2000000", "--label")) and all(s in cmds["1."] for s in F.PR.FINAL_SIDE_INDEXES), cmds["1."])
check("the ruler's frozen half is run with the same recipe and its key-paragraph test", "--source ruler" in cmds["2."] and "--final-recipe" in cmds["2."] and "ruler_keytest.py" in cmds["2."])
check("the pack, the normaliser and the two scoring stages follow in order", "build_sealed_pack.py" in cmds["3."] and "normalise_replies.py" in cmds["4."] and " marks " in cmds["5."] and " key " in cmds["6."])

# the owner items stay open until named; everything else is stubbed so that the real repository is not needed
F.PR.rules_state = lambda *a, **k: ("a" * 64, "a" * 64)
F.PR.code_state = lambda: ("c" * 40, [])
F.PR.index_head = lambda d: "3c80a26e42bea75e5858be6ed44a2649ec701355"
F.sh = lambda *c: SimpleNamespace(stdout="0\n" if "rev-list" in c else "claude/test\n")
F.RQ.read_runs = lambda p: []
F.RU.read_runs = lambda p: []
res = F.checks(SimpleNamespace(no_tests=True, owner_confirms=""))
owner = [r for r in res if r["check"].startswith("OWNER")]
check("the four owner items are open when nothing is confirmed", len(owner) == 4 and not any(r["ok"] for r in owner))
res2 = F.checks(SimpleNamespace(no_tests=True, owner_confirms="register-patch,advocate-16,refresh-postponed,balance"))
check("naming them closes them", all(r["ok"] for r in res2 if r["check"].startswith("OWNER")))
check("a hand-out already logged would fail the check", True if not any("no sealed hand-out" in r["check"] and not r["ok"] for r in res2) else False)
F.RQ.read_runs = lambda p: [{"ts": "x"}]
res3 = F.checks(SimpleNamespace(no_tests=True, owner_confirms=""))
check("a logged sealed hand-out makes the preflight fail", any("no sealed hand-out" in r["check"] and not r["ok"] for r in res3))
F.PR.code_state = lambda: ("c" * 40, ["review_tools/pool_runner.py"])
res4 = F.checks(SimpleNamespace(no_tests=True, owner_confirms=""))
check("a dirty checkout makes the preflight fail", any("checkout clean" in r["check"] and not r["ok"] for r in res4))
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sealed_preflight.py"), encoding="utf-8").read()
check("the preflight never calls select(), so it cannot hand a question out", ".select(" not in src)
print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
