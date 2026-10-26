"""For the 12 landmark questions on the newer index: what stood above the landmark judgment (or filled the top 10 when it is missing)? Reads compare_newer_d8811a9_rows.json and compare_pinned_3c80a26.json.
A document number of 2,000,000,000 or more is a document added after the first index (a Gauhati High Court judgment or a newer Supreme Court one: the court field says which); a lower number is a judgment that was in the first index."""
import json
import os
import sys

folder = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
new = json.load(open(os.path.join(folder, "compare_newer_d8811a9_rows.json"), encoding="utf-8"))
old = json.load(open(os.path.join(folder, "compare_pinned_3c80a26.json"), encoding="utf-8"))
SC = "Supreme Court of India"
print("| Landmark | words | pinned rank | newer rank | in the newer top 10: other-court / newer Supreme Court / first-index Supreme Court passages | rank among Supreme Court passages only |")
print("|---|---|---|---|---|---|")
tot = {"hc": 0, "sc_new": 0, "sc_old": 0}
for a, b in zip(old["landmarks"], new["landmarks"]):
    rows = b["rows"]
    hc = sum(1 for r in rows if r["court"] != SC)
    sc_new = sum(1 for r in rows if r["court"] == SC and r["doc"] >= 2_000_000_000)
    sc_old = sum(1 for r in rows if r["court"] == SC and r["doc"] < 2_000_000_000)
    for k, v in (("hc", hc), ("sc_new", sc_new), ("sc_old", sc_old)):
        tot[k] += v
    sc_only = [r for r in rows if r["court"] == SC]
    r_sc = next((i + 1 for i, r in enumerate(sc_only) if r["doc"] == b["doc"]), None)
    print(f"| {b['landmark'][:30]} | {b['kind']} | {a['doc_rank_in_top10'] or '-'} | {b['doc_rank_in_top10'] or '-'} | {hc} / {sc_new} / {sc_old} | {r_sc or '-'} |")
n = sum(tot.values())
print(f"\nAll {n} passages of the 12 newer top 10s: other court {tot['hc']} ({tot['hc'] / n:.0%}), newer Supreme Court {tot['sc_new']} ({tot['sc_new'] / n:.0%}), first-index Supreme Court {tot['sc_old']} ({tot['sc_old'] / n:.0%}).")
