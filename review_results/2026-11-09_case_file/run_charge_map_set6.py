import os, sys
sys.path.insert(0, "/home/user/recourse"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charge_map as C
import questions_charge_map_set6 as S
none = lambda x: []
def has316(t): return "BNS 316" in {f"{c['act']} {c['section']}" for c in C.candidates(t, search=none)}
print("POS_CBT: 316 offered %d of %d" % (sum(has316(t) for t in S.POS_CBT), len(S.POS_CBT)))
for t in S.POS_CBT:
    if not has316(t): print("  MISS", t[:70])
print("NEG_CBT: 316 wrongly offered %d of %d" % (sum(has316(t) for t in S.NEG_CBT), len(S.NEG_CBT)))
for t in S.NEG_CBT:
    if has316(t): print("  FIRE", t[:70])
f = getattr(C, "asks_offences", None)
if f is None:
    print("ASK detector: does not exist yet (0 of %d positives, 0 of %d negatives wrongly)" % (len(S.ASK_POS), len(S.ASK_NEG)))
else:
    print("ASK_POS: detected %d of %d" % (sum(bool(f(t)) for t in S.ASK_POS), len(S.ASK_POS)))
    for t in S.ASK_POS:
        if not f(t): print("  MISS", t)
    print("ASK_NEG: wrongly detected %d of %d" % (sum(bool(f(t)) for t in S.ASK_NEG), len(S.ASK_NEG)))
    for t in S.ASK_NEG:
        if f(t): print("  FIRE", t)
