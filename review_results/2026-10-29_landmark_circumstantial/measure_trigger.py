"""Measures the circumstantial-evidence trigger (Recourse excerpt_anchors._circumstantial) on the three question sets and on the independent pool, with the code as it is now.

    python3 measure_trigger.py [--recourse /path/to/recourse-checkout]   # writes trigger_measurement_final_code.json next to this file

Sets (all written by Claude, none by a lawyer):
  frozen_questions_set1.json      written and committed (135976c) BEFORE any trigger pattern existed
  tuning_questions_set2.json      written after the first run on set 1, adversarial (paraphrases); the patterns were tuned on it
  final_check_questions_set3.json written after the tuning, run once, not tuned on
  independent_pool.json           284 questions from ten question files of earlier work (register exam, ruler, Act shelf and JJ/dowry evals); none was written for this topic
A 'pos' question should hand the excerpts over, a 'neg' one should not; 'ambiguous' questions are only counted.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--recourse", default="/home/user/recourse")
a = ap.parse_args()
sys.path.insert(0, a.recourse)
os.environ["LANDMARKS"] = "on"
import excerpt_anchors as E  # noqa: E402

match = E.TOPICS["circumstantial_evidence"]["match"]


def qs(items):
    return [x["q"] if isinstance(x, dict) else x for x in items]


out = {"sets": {}, "pool": {}}
for name, f in (("set1_frozen", "frozen_questions_set1.json"), ("set2_tuning", "tuning_questions_set2.json"), ("set3_final_check", "final_check_questions_set3.json")):
    d = json.load(open(os.path.join(HERE, f), encoding="utf-8"))
    pos, neg, amb = qs(d["pos"]), qs(d["neg"]), qs(d.get("ambiguous") or [])
    misses = [q for q in pos if not match(q)]
    false_fires = [q for q in neg if match(q)]
    amb_fires = [q for q in amb if match(q)]
    out["sets"][name] = {"pos": len(pos), "pos_hit": len(pos) - len(misses), "neg": len(neg), "neg_fired": len(false_fires), "ambiguous": len(amb), "ambiguous_fired": len(amb_fires),
                         "misses": misses, "false_fires": false_fires, "ambiguous_that_fired": amb_fires}
pool = json.load(open(os.path.join(HERE, "independent_pool.json"), encoding="utf-8"))
fires = {k: [q for q in v if match(q)] for k, v in pool.items()}
out["pool"] = {"questions": sum(len(v) for v in pool.values()), "fired": sum(len(v) for v in fires.values()), "by_file": {k: {"questions": len(pool[k]), "fired": len(fires[k]), "which": fires[k]} for k in pool}}
json.dump(out, open(os.path.join(HERE, "trigger_measurement_final_code.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in out["sets"].items():
    print(f"{k}: handed over for {v['pos_hit']} of {v['pos']} wanted; fired for {v['neg_fired']} of {v['neg']} unwanted; ambiguous fired {v['ambiguous_fired']} of {v['ambiguous']}")
    for q in v["misses"]:
        print("    MISS:", q)
    for q in v["false_fires"]:
        print("    FALSE FIRE:", q)
    for q in v["ambiguous_that_fired"]:
        print("    ambiguous fired:", q)
print(f"independent pool: fired for {out['pool']['fired']} of {out['pool']['questions']}")
for k, v in out["pool"]["by_file"].items():
    for q in v["which"]:
        print("    POOL FIRE:", k, "|", q)
