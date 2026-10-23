"""
run_search_gold.py -- runs the frozen questions of search_gold_questions.json through the search page's engine (Recourse's search_service.search) twice: words only (meaning off) and words plus meaning (the real Voyage query vector;
a few paise in all). Prints and writes search_gold_results.json. Needs the Recourse checkout (RECOURSE_REPO, default ../recourse relative to this repository's parent) and VOYAGE_API_KEY for the meaning arm.
    python review_results/2026-10-23_export_and_search/run_search_gold.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("RECOURSE_REPO") or os.path.join(HERE, "..", "..", "..", "recourse")
sys.path.insert(0, os.path.abspath(REPO))
os.environ["ACT_SHELF"] = "on"

import search_service as S

qs = json.load(open(os.path.join(HERE, "search_gold_questions.json"), encoding="utf-8"))["questions"]
out = {}
for arm, meaning in (("words", False), ("words+meaning", True)):
    rows, hit5, hit10 = [], 0, 0
    for q in qs:
        r = S.search(q["q"], meaning=meaning)
        got = [(p["act"], p["section"]) for p in r["provisions"]]
        want = {(e["act"], e["section"]) for e in q["expect"]}
        rank = next((i + 1 for i, g in enumerate(got) if g in want), None)
        hit5 += bool(rank and rank <= 5)
        hit10 += bool(rank and rank <= 10)
        rows.append({"id": q["id"], "q": q["q"], "expect": sorted(want), "rank": rank, "meaning_used": r["meaning_used"], "top5": got[:5], "n_provisions": len(got)})
    out[arm] = {"hit_at_5": hit5, "hit_at_10": hit10, "n": len(qs), "rows": rows}
    print(f"{arm:14} hit@5 {hit5}/{len(qs)} ({100 * hit5 / len(qs):.0f}%)   hit@10 {hit10}/{len(qs)} ({100 * hit10 / len(qs):.0f}%)   meaning really used in {sum(1 for x in rows if x['meaning_used'])} of {len(rows)}")
    for x in rows:
        if not x["rank"] or x["rank"] > 5:
            print(f"   {'MISS' if not x['rank'] else 'rank ' + str(x['rank']):8} #{x['id']:<3} {x['q'][:62]:62} expect {x['expect']}  top3 {x['top5'][:3]}")
json.dump(out, open(os.path.join(HERE, "search_gold_results.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
