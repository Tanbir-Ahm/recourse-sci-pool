"""measure.py -- runs the planner (Recourse matter_depth.plan) over the frozen set planner_set.json.
Harness rule, declared before the first run (the set is frozen in 8278a36): the test matter's documents carry a labelled 'Sections:' line, so for the router-derived items (kind not starting with 'new_') the planner is told
that the charged sections can be named by code (pins_available=True); for the 'new_*' items the item's own 'pins' flag is used (False tests the no-pins fallback).
Dangerous errors: an item that needs law or a draft (standard, research, draft) sent to file, explain or smalltalk. Reported: standard or research sent to a lower size than it needs but still with law (explain<-research),
money (a lower-size item sent to standard or research), draft errors.
Usage: python3 measure.py A | B | C   (C is the fresh set written after the held-out run of B, for the two rule changes it showed were needed)"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "recourse"))
import matter_depth as D
half = (sys.argv[1] if len(sys.argv) > 1 else "A").upper()
S = json.load(open(os.path.join(HERE, "planner_set_C.json" if half == "C" else "planner_set.json")))[half]
NOLAW = {"file", "explain", "smalltalk"}
rows, wrong, danger, money, thin = [], [], [], [], []
for x in S:
    pins = True if not str(x.get("kind") or "").startswith("new_") else bool(x["pins"])
    got = D.plan(x["q"], pins_available=pins)["size"]
    ok = got == x["expect"] or got in x["also"]
    if not ok:
        wrong.append((x["id"], x["expect"], got, x["q"]))
        if x["expect"] in ("standard", "research", "draft") and got in NOLAW:
            danger.append(wrong[-1])
        elif x["expect"] in ("file", "explain", "smalltalk") and got in ("standard", "research"):
            money.append(wrong[-1])
        elif x["expect"] == "research" and got == "standard":
            thin.append(wrong[-1])
        elif x["expect"] == "standard" and got == "research":
            money.append(wrong[-1])
n = len(S)
print(f"half {half}: {n - len(wrong)} of {n} as frozen; dangerous (law or draft sent to a no-law size): {len(danger)}; money (small sent up): {len(money)}; thin (research sent to standard): {len(thin)}")
for w in wrong:
    print("  ", w)
