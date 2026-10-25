#!/usr/bin/env python3
"""Chooses what a labelled tier list shows (the High Court list beside the Supreme Court list). No network, no cost.

review_results/2026-10-25_tier_test/tier_test.py took the first MAX_RESULTS judgments over the bar, one passage each, so it showed the same words twice when the
court had decided two petitions together (two case numbers, one text); index_dedupe.py leaves such twins in the index on purpose. Here a passage that reads the same
as one already chosen (80% of the 8-word shingles in common, the measure index_dedupe.py uses) is not shown again: the next candidate takes its place, and the kept
result lists the judgments it stands for in `also_in`, so a page can say "also decided in ...".
"""
import sci_index as si

BAR, MAX_RESULTS, SAME = 0.50, 3, 0.80      # the site's pilot tier: its own similarity bar (the core's is 0.40), three judgments at most


def same_passage(a, b, threshold=SAME):
    """a and b are shingle sets (si.shingles). True when each holds `threshold` of the other's shingles."""
    inter = len(a & b)
    return bool(inter) and inter / len(a) >= threshold and inter / len(b) >= threshold


def pick(rows, bar=BAR, max_results=MAX_RESULTS, threshold=SAME):
    """rows: candidates, best first, each {"doc", "cos", "text", ...}. Returns the rows to show, best first: cosine at or over the bar, one passage per judgment,
    no two passages that read the same. A kept row gets "also_in": [doc, ...] for the judgments left out because their passage reads the same as its."""
    kept, seen = [], set()
    for r in rows:
        if r["cos"] < bar or r["doc"] in seen:
            continue
        seen.add(r["doc"])
        sh = si.shingles(r["text"])
        twin = next((k for k in kept if same_passage(sh, k["_sh"], threshold)), None)
        if twin:
            twin["also_in"].append(r["doc"])
        elif len(kept) < max_results:
            kept.append({**r, "also_in": [], "_sh": sh})
    return [{k: v for k, v in r.items() if k != "_sh"} for r in kept]
