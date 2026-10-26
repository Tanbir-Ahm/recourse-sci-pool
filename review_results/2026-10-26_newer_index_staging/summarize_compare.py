"""Reads compare_pinned_3c80a26.json and compare_newer_d8811a9.json (written by compare_old_new.py) and prints the Markdown tables of RESULTS.md. Usage: python summarize_compare.py <folder>"""
import json
import os
import sys

folder = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
old = json.load(open(os.path.join(folder, "compare_pinned_3c80a26.json"), encoding="utf-8"))
new = json.load(open(os.path.join(folder, "compare_newer_d8811a9.json"), encoding="utf-8"))
fmt = lambda r: "-" if r is None else str(r)

print("| Landmark judgment | words | rank in pinned index (10,522) | rank in newer index (19,255) | other-court passages in the newer top 10 |")
print("|---|---|---|---|---|")
for a, b in zip(old["landmarks"], new["landmarks"]):
    assert a["doc"] == b["doc"] and a["kind"] == b["kind"]
    print(f"| {a['landmark']} | {a['kind']} | {fmt(a['doc_rank_in_top10'])} | {fmt(b['doc_rank_in_top10'])} | {b['n_other_court_in_top10']} |")


def counts(d):
    r = [x["doc_rank_in_top10"] for x in d["landmarks"]]
    return (sum(1 for x in r if x), sum(1 for x in r if x and x <= 5), sum(1 for x in r if x and x <= 3), len(r))


for lab, d in (("pinned (3c80a26)", old), ("newer (d8811a9)", new)):
    t10, t5, t3, n = counts(d)
    print(f"\n{lab}: landmark judgment in the top 10: {t10} of {n}; in the top 5: {t5}; in the top 3: {t3}. Load {d['load_seconds']} s. Search spend for the {len(d['landmarks']) + len(d['spot'])} searches: {d['usage_today'].get('dollars_estimate')} dollars.")

print("\nSpot-check questions (nobody has marked them): passages of another court in the newer index's top 10, and its top three cases")
print("| Question | other-court passages (of 10) | newer index: first three results (court, case) |")
print("|---|---|---|")
for s in new["spot"]:
    top = "; ".join(f"{(r['court'] or '?').replace(' of India', '').replace('Supreme Court', 'SC').replace('Gauhati High Court', 'GHC')}: {(r['case'] or '')[:42]}" for r in s["results"][:3])
    print(f"| {s['q'][:90]} | {s['n_other_court']} | {top} |")
print("\nSame spot-check questions on the pinned index (first three results)")
print("| Question | first three results |")
print("|---|---|")
for s in old["spot"]:
    print(f"| {s['q'][:90]} | " + "; ".join((r['case'] or '')[:42] for r in s["results"][:3]) + " |")
