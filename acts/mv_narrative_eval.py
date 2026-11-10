#!/usr/bin/env python3
"""For each long narrative question: which sections of the Motor Vehicles Act would the shelf hand over (named + pointed + the first 5 by meaning)? Needs VOYAGE_API_KEY (a few hundred tokens).
Usage: python acts/mv_narrative_eval.py acts/mv_narrative_questions.json [--recourse /home/user/recourse]"""
import json, os, sys
rec = os.environ.get("RECOURSE", "/home/user/recourse")
if "--recourse" in sys.argv:
    rec = sys.argv[sys.argv.index("--recourse") + 1]
sys.path.insert(0, rec)
os.environ["ACT_SHELF"] = "on"
import act_shelf as S
d = json.load(open(sys.argv[1]))
import shelf_companions as SC
def handed(q):
    r = S.search(q, [{"id": "mv_act_1988"}], current_message=q)
    ms = list(r["matches"])
    if "--companions" in sys.argv:                                    # the companion rule of shelf_companions.py on top of what the shelf handed over
        ms += SC.add(q, [dict(m, source="act_shelf") for m in ms])
    return [str(m.get("section_number")) for m in ms]
ok = 0
for q in d["fled"]:
    h = handed(q); got = [s for s in d["want"] if s in h]
    ok += len(got) == len(d["want"])
    print("FLED  all of 132/134/187: %-5s handed=%s | %s" % (len(got) == len(d["want"]), h, q[:50]))
bad = 0
for q in d["others"]:
    h = handed(q); fired = [s for s in d["want"] if s in h]
    bad += bool(fired)
    print("OTHER pointer sections present: %-5s handed=%s | %s" % (bool(fired), h, q[:50]))
print("fled questions with 132, 134 and 187 handed over: %d of %d; other questions with any of them: %d of %d" % (ok, len(d["fled"]), bad, len(d["others"])))
