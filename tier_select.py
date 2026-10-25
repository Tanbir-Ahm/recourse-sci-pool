#!/usr/bin/env python3
"""Chooses what a labelled tier list shows (the High Court list beside the Supreme Court list). No network, no cost.

Two things are decided here, and both are decisions in code rather than wording in a prompt:

* **Whose words.** Every candidate goes through `authority.safe_classify`. A passage whose every word is a lawyer's or a party's is dropped, and the rest are put
  in the owner's order (2026-10-25): Supreme Court, then High Court, then trial court, and only inside one of those does the search score decide. A passage that
  states no law sorts below one that does, in the same tier. `verify` re-checks both on the way out and raises, so a caller cannot get a list that breaks them.
* **No repeats.** `review_results/2026-10-25_tier_test/tier_test.py` took the first MAX_RESULTS judgments over the bar, one passage each, so it showed the same
  words twice when the court had decided two petitions together (two case numbers, one text); `index_dedupe.py` leaves such twins in the index on purpose. Here a
  passage that reads the same as one already chosen (80% of the 8-word shingles in common, the measure `index_dedupe.py` uses) is not shown again: the next
  candidate takes its place, and the kept result lists the judgments it stands for in `also_in`, so a page can say "also decided in ...".
"""
import authority as A
import sci_index as si

BAR, MAX_RESULTS, SAME = 0.50, 3, 0.80      # the site's pilot tier: its own similarity bar (the core's is 0.40), three judgments at most


def same_passage(a, b, threshold=SAME):
    """a and b are shingle sets (si.shingles). True when each holds `threshold` of the other's shingles."""
    inter = len(a & b)
    return bool(inter) and inter / len(a) >= threshold and inter / len(b) >= threshold


def verify(kept, ordered=True, promote=False, own_tier=None):
    """Raises AssertionError if a list breaks either rule: nothing blocked may be in it (always), and the tiers must not go up again, which would put a lower
    court above a higher one (only when the list was ordered here; `pick(by_authority=False)` keeps the caller's order on purpose, to measure what the order
    changes). Called at the end of `pick`; cheap, and if it ever trips it is a fault in this code, not in the data."""
    for r in kept:
        assert not r["authority"]["blocked"], f"a blocked passage reached the list: {r.get('doc')} ({r['authority']['reason']})"
        assert r.get("voice_line"), f"a result without its line saying whose words it shows: {r.get('doc')}"
    if ordered:
        tiers = [A.sort_key(r["authority"], 0, own_tier, promote)[:2] for r in kept]
        assert tiers == sorted(tiers), f"the list is out of the owner's order: {[r['authority']['tier'] for r in kept]}"
    return kept


def pick(rows, bar=BAR, max_results=MAX_RESULTS, threshold=SAME, by_authority=True, promote=False, own_tier=None):
    """rows: candidates, each {"doc", "cos", "text", ...} and optionally "src" (the stored fields of its judgment) and "final" (the search score). Returns the
    rows to show: cosine at or over the bar, nobody's argument, the owner's order, one passage per judgment, and no two passages that read the same. Each kept
    row carries "authority" (the verdict, including `voice`, `tier` and the `quote` a page should show), "voice_line" (the line a page MUST print above the
    quote, saying whose words it is) and "also_in" (the judgments whose passage reads the same). Order, owner's decisions of 2026-10-25: the strict tier order,
    and a passage never ranks above the court that wrote its judgment (a High Court quoting the Supreme Court stays at High Court rank).
    `by_authority=False` keeps the caller's own order and only drops blocked passages, for measuring what the order itself changes; `promote=True` is the plain
    reading of the order, in which a quoted Supreme Court outranks the High Court quoting it (measured, not chosen; see `authority.effective_tier`)."""
    scored = []
    for r in rows:
        if r["cos"] < bar:
            continue
        v = A.safe_classify(r["text"], src=r.get("src"), doc=r.get("doc"))
        if v["blocked"]:
            continue
        scored.append({**r, "authority": v, "voice_line": A.voice_line(v)})
    if by_authority:
        scored.sort(key=lambda r: A.sort_key(r["authority"], r.get("final", r["cos"]), own_tier, promote))
    kept, seen = [], set()
    for r in scored:
        if r["doc"] in seen:
            continue
        seen.add(r["doc"])
        sh = si.shingles(r["text"])
        twin = next((k for k in kept if same_passage(sh, k["_sh"], threshold)), None)
        if twin:
            twin["also_in"].append(r["doc"])
        elif len(kept) < max_results:
            kept.append({**r, "also_in": [], "_sh": sh})
    return verify([{k: v for k, v in r.items() if k != "_sh"} for r in kept], ordered=by_authority, promote=promote, own_tier=own_tier)
