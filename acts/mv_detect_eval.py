#!/usr/bin/env python3
"""Runs the word pass (Recourse act_detect.wide) on a Motor Vehicles Act question file and counts: positives that reach mv_act_1988, negatives and traps that wrongly do. Free, no model, no network.
Usage: python acts/mv_detect_eval.py acts/mv_detect_questions.json [--recourse /home/user/recourse]"""
import json, os, sys
rec = os.environ.get("RECOURSE", "/home/user/recourse")
if "--recourse" in sys.argv:
    rec = sys.argv[sys.argv.index("--recourse") + 1]
sys.path.insert(0, rec)
import act_detect
d = json.load(open(sys.argv[1]))
hit = lambda q: any(h["id"] == d["want"] for h in act_detect.wide(q))
miss = [q for q in d["positives"] if not hit(q)]
fire = [q for q in d["negatives"] if hit(q)]
trap = [q for q in d.get("traps", []) if hit(q)]
for q in miss: print("MISS ", q[:100])
for q in fire: print("FIRE ", q[:100])
for q in trap: print("TRAP ", q[:100])
print("positives reached: %d of %d" % (len(d["positives"]) - len(miss), len(d["positives"])))
print("negatives wrongly reached: %d of %d" % (len(fire), len(d["negatives"])))
print("declared traps wrongly reached: %d of %d" % (len(trap), len(d.get("traps", []))))
