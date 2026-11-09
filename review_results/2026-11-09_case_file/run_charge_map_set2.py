import os, sys
sys.path.insert(0, "/home/user/recourse"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charge_map as C
import questions_charge_map as S1, questions_charge_map_set2 as S2, questions_charge_map_set3 as S3
def run(name, POS, NEG):
    miss = []
    for t, exp in POS:
        got = {f"{c['act']} {c['section']}" for c in C.candidates(t, search=lambda x: [])}
        lost = sorted(exp - got)
        if lost: miss.append((t[:70], lost)); print("MISS ", t[:70], "missing:", ", ".join(lost))
    fire = []
    for t in NEG:
        got = [f"{c['act']} {c['section']}" for c in C.candidates(t, search=lambda x: [])]
        if got: fire.append(t); print("FIRE ", t[:70], got)
    print("%s: positives complete %d of %d; negatives wrongly firing %d of %d" % (name, len(POS) - len(miss), len(POS), len(fire), len(NEG)))
run("set 1", S1.POS, S1.NEG)
run("set 2", S2.POS, S2.NEG)
run("set 3 (new)", S3.POS, S3.NEG)
