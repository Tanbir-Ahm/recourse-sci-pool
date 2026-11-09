import os, sys
sys.path.insert(0, "/home/user/recourse"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charge_map as C
import questions_charge_map_set5 as S
none = lambda x: []
def keys(t): return {f"{c['act']} {c['section']}" for c in C.candidates(t, search=none)}
COMP = S.C
miss = 0
for t, exp in S.POS:
    lost = sorted(exp - keys(t))
    if lost: miss += 1; print("MISS ", t[:70], "missing:", ", ".join(lost))
print("POS: complete %d of %d" % (len(S.POS) - miss, len(S.POS)))
def leak(name, qs, comp_only=True):
    n = 0
    for t in qs:
        k = keys(t); bad = sorted(k & COMP) if comp_only else sorted(k)
        if bad: n += 1; print("FIRE ", name, t[:60], bad)
    print("%s: wrongly offered %d of %d" % (name, n, len(qs)))
leak("NEG_SINGLE", S.NEG_SINGLE); leak("NEG_AFTER", S.NEG_AFTER); leak("NEG_NONE", S.NEG_NONE, comp_only=False); leak("TRAP (declared)", S.TRAP)
