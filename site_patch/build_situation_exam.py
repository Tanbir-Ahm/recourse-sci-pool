"""Writes register_exam/situation/ (questions.jsonl, key.json): the trap exam in situation form (goodlaw/register_exam.py, SITUATIONS). Needs only the register; no index, no network.
    python site_patch/build_situation_exam.py [--out DIR]"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from goodlaw import register as R, register_exam as EX

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(ROOT, "register_exam", "situation"))
a = ap.parse_args()
reg = R.Register.load()
qs, key = EX.build_exam_situations(reg)
os.makedirs(a.out, exist_ok=True)
with open(os.path.join(a.out, "questions.jsonl"), "w", encoding="utf-8") as f:
    for q in qs:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")
json.dump(key, open(os.path.join(a.out, "key.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(qs)} questions from {len({k['row_id'] for k in key.values()})} register rows -> {a.out}")
