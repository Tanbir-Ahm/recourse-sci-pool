import os, sys
sys.path.insert(0, "/home/user/recourse"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charge_map as C
import importlib
S = importlib.import_module(os.path.basename(__file__).replace("run_charge_map_", "questions_charge_map_").replace(".py", ""))
none = lambda x: []
def keys(t): return {f"{c['act']} {c['section']}" for c in C.candidates(t, search=none)}
def grp(name, qs, need):
    miss = 0
    for t in qs:
        lost = sorted(need - keys(t))
        if lost: miss += 1; print("  MISS", t[:70], "missing:", ", ".join(lost))
    print("%s: complete %d of %d" % (name, len(qs) - miss, len(qs)))
grp("POS_DEATH", S.POS_DEATH, {"BNS 106", "BNS 281"})
grp("POS_HURT", S.POS_HURT, {"BNS 281", "BNS 125"})
bad = 0
for t in S.NEG:
    k = keys(t) & {"BNS 106", "BNS 281", "BNS 125"}
    if k: bad += 1; print("  FIRE", t[:70], sorted(k))
print("NEG: wrongly offered %d of %d" % (bad, len(S.NEG)))
