import os, sys
sys.path.insert(0, "/home/user/recourse"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charge_map as C
from questions_charge_map import POS, NEG
miss = []
for t, exp in POS:
    got = {f"{c['act']} {c['section']}" for c in C.candidates(t, search=lambda x: [])}
    lost = sorted(exp - got)
    print(("OK   " if not lost else "MISS ") + t[:70], "" if not lost else "missing: " + ", ".join(lost))
    if lost: miss.append((t, lost))
fire = []
for t in NEG:
    got = [f"{c['act']} {c['section']}" for c in C.candidates(t, search=lambda x: [])]
    if got:
        fire.append((t, got)); print("FIRE ", t[:70], got)
print("positives with every expected section: %d of %d" % (len(POS) - len(miss), len(POS)))
print("negatives that wrongly produced candidates: %d of %d" % (len(fire), len(NEG)))
