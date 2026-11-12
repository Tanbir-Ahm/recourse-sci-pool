#!/usr/bin/env python3
"""For each multi-sentence question: which sections does the shelf hand over (named + pointed + meaning)? Counts: all expected present, any expected present, and (also_ok counted) any. Needs VOYAGE_API_KEY.
Usage: python acts/shelf_multisentence_eval.py <questions.json> [--recourse /home/user/recourse] [--show]"""
import json, os, sys
rec = sys.argv[sys.argv.index("--recourse") + 1] if "--recourse" in sys.argv else os.environ.get("RECOURSE", "/home/user/recourse")
sys.path.insert(0, rec)
os.environ["ACT_SHELF"] = "on"
import act_shelf as S
d = json.load(open(sys.argv[1]))
full = anyx = anyl = 0
for q in d["questions"]:
    r = S.search(q["q"], [{"id": q["act_key"]}], current_message=q["q"])
    got = [str(m.get("section_number")) for m in r["matches"]]
    a = all(e in got for e in q["expected"]); b = any(e in got for e in q["expected"]); c = any(e in got for e in q["expected"] + q["also_ok"])
    full += a; anyx += b; anyl += c
    if "--show" in sys.argv or not a:
        print("%-5s %-5s expected=%s handed=%s" % (q["id"], "OK" if a else "MISS", q["expected"], got))
n = len(d["questions"])
print("all expected handed over: %d of %d; any expected: %d of %d; any expected or also_ok: %d of %d" % (full, n, anyx, n, anyl, n))
