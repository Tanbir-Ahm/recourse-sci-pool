"""
run_search_gold.py -- runs the frozen questions of search_gold_questions.json through the search page's engine (Recourse's search_service.search) twice: words only (meaning off) and words plus meaning (the real Voyage query vector;
a few paise in all). Prints and writes search_gold_results.json. Needs the Recourse checkout (RECOURSE_REPO, default ../recourse relative to this repository's parent) and VOYAGE_API_KEY for the meaning arm.
    python review_results/2026-10-23_export_and_search/run_search_gold.py [questions|heldout]
The held-out set is run ONCE (it was frozen before round 2 of the engine): the script refuses to overwrite an existing held-out result file. Every result file records which engine it ran (Recourse commit, whether the checkout
was clean, and the SHA-256 of search_service.py and search_stem.py) and when.
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("RECOURSE_REPO") or os.path.join(HERE, "..", "..", "..", "recourse")
sys.path.insert(0, os.path.abspath(REPO))
os.chdir(os.path.abspath(REPO))          # the engine's data files (chunks/, embeddings/, case_lookup_index.db, act_shelf/) are found relative to the repository root, as when the service runs from it
os.environ["ACT_SHELF"] = "on"

import search_service as S

SET = (sys.argv[1] if len(sys.argv) > 1 else "questions")            # "questions" (the tuning set) or "heldout"
LABEL = os.environ.get("GOLD_LABEL")                     # e.g. BEFORE_round2: the same questions through an OLDER engine (RECOURSE_REPO pointing at a worktree of that commit), for comparison only
OUT = os.path.join(HERE, f"search_gold_results_{SET}{'_' + LABEL if LABEL else ''}.json")
if SET == "heldout" and os.path.exists(OUT):
    sys.exit(f"{OUT} exists: the held-out set is run once; it was already run. Delete the file only if the run was invalid, and say why in RESULTS.md.")
qs = json.load(open(os.path.join(HERE, f"search_gold_{SET}.json"), encoding="utf-8"))["questions"]


def _git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=os.getcwd()).stdout.strip()


def _sha(name):
    return hashlib.sha256(open(name, "rb").read()).hexdigest() if os.path.exists(name) else None        # search_stem.py does not exist in the engine of round 1


out = {"engine": {"recourse_commit": _git("rev-parse", "HEAD"), "recourse_checkout_clean": _git("status", "--porcelain", "--", "search_service.py", "search_stem.py") == "",
                  "search_service_sha256": _sha("search_service.py"), "search_stem_sha256": _sha("search_stem.py"), "run_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "set": SET, "n": len(qs)}}
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
json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
