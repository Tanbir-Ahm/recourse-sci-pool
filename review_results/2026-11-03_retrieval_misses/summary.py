"""Prints the table of RESULTS.md from the stored e2e_*.json files and the false-positive check of the evidence word pass. Output saved as summary_output.txt."""
import json, os, sys
sys.path.insert(0, "/home/user/recourse"); sys.path.insert(0, "."); sys.path.insert(0, "../2026-10-31_relevance_gate"); sys.path.insert(0, "../2026-11-03_relevance_neighbours")
from analyze_e2e import analyse
SETS = [("dev 1 (29 q)", "questions"), ("dev 2 (36 q)", "questions_fresh"), ("frozen (48 q)", "questions_frozen"), ("evidence 2 (16 q)", "questions_evidence2"), ("set 3 (35 q)", "questions_set3")]
print("Expected sections that reach the answer model (stubbed model, real search, shelf and overrides). 'today' = ACT_SHELF=on ACT_DETECT=wide; 'fixes' = + STATUTE_WIDEN=on STATUTE_ALIASES=on EVIDENCE_DETECT=on")
print(f"{'set':20s} {'today':>14s} {'fixes':>14s}")
for label, s in SETS:
    a = analyse(f"e2e_shelf_{s}.json", quiet=True); b = analyse(f"e2e_fixes_{s}.json", quiet=True)
    print(f"{label:20s} {a[0]:>5d}/{a[1]:<3d} {100*a[0]/a[1]:3.0f}%   {b[0]:>5d}/{b[1]:<3d} {100*b[0]/b[1]:3.0f}%")
print()
os.environ["ACT_DETECT"] = "wide"; os.environ["EVIDENCE_DETECT"] = "on"
import act_detect as A
from questions_frozen import POS as F
from questions_evidence2 import NEG2, POS as E2
from questions_negative import NEG
from questions import POS as P0
from questions_fresh import POS as P1
from questions_set3 import POS as P3
neg = [("dev 1", [q for q, _ in P0]), ("dev 2", [q for q, _ in P1]), ("frozen offence+procedure", [q for q, e, k in F if k in ("offence", "procedure")]), ("set 3", [q for q, e, k in P3]), ("NEG", NEG), ("NEG2", NEG2)]
tot = fp = 0
for name, qs in neg:
    hits = [q for q in qs if any(h["id"] == "bsa_2023" for h in A.wide(q))]
    tot += len(qs); fp += len(hits)
    print(f"evidence word pass on non-evidence questions, {name:26s}: {len(hits)} of {len(qs)} name the Bharatiya Sakshya Adhiniyam" + ("" if not hits else "  <- " + "; ".join(h[:70] for h in hits)))
print(f"total: {fp} of {tot}")
for name, qs in (("frozen evidence (12)", [q for q, e, k in F if k == "evidence"]), ("frozen evidence-named (4)", [q for q, e, k in F if k == "evidence-named"]), ("evidence 2 (16)", [q for q, e, k in E2])):
    n = sum(1 for q in qs if any(h["id"] == "bsa_2023" for h in A.wide(q)))
    print(f"word pass alone, {name}: names the Act for {n} of {len(qs)}")
