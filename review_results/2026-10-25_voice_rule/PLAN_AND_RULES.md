# Whose words a passage puts forward: plan and pass/fail rules, written BEFORE the sample was labelled (2026-10-25)

Owner's instruction (2026-10-25): test the rule for problem 1 of the tier test; check whether it was attempted before; "Fix this problem permanently. Do it the same way as we did it citation checker and verbatim quote checker, DO not just use Guardrails, that does not work." And the order that must hold:

> 1. Supreme court  2. High court  3. Trial court  4. Lawyer's arguments (But never put forward as binding principles). But these arguments must never be shown in the responses.

## What is being tested

`authority.py`: for one passage, who is speaking sentence by sentence, whether the sentence states law, and from that the passage's tier (1 Supreme Court, 2 High Court, 3 trial court) and whether every word of it is a lawyer's or a party's (then it is blocked: never shown). Deterministic, text only, no model, no network, nothing to spend. Ordering: `sort_key` = (tier, does it state law, then the search score), so a score can never put a lower tier above a higher one.

## The three measurements

1. **A hand-labelled sample, labelled blind.** 100 passages drawn at random from the whole index (seed 20261025, 50 Supreme Court and 50 Gauhati, so both sides are covered) plus 40 drawn at random from the passages the rule blocks (seed 20261025, to measure the block decision, which is too rare in a random sample to measure on 100). The 140 are shuffled together and written **without the rule's verdict**; I label each one before looking at any verdict. Two labels per passage:
   - `block`: is every word of it a lawyer's or a party's (an argument, a submission, a pleading, an allegation), with nothing of any court's own?
   - `tier`: whose words carry the law in it - Supreme Court, High Court, trial court, or none (no law in it).
   My labels, not a lawyer's, and said so in the results.
2. **The 65 passages the tier test showed** (`review_results/2026-10-25_tier_test/hc_tier_ratings.csv`), where 6 are already recorded as the wrong voice: entry 21 a trial court's reasoning, 49 lawyers' arguments, 50 a party's allegations, 2, 3 and 35 background facts. The rule must put 21 at tier 3, block or demote 49 and 50, and must not block the on-point ones.
3. **The 26 questions of the tier test, re-run** so that a place freed by a block is refilled from the real candidates (the saved results hold only the first three). Measures what the list looks like after the rule, at a cost of a few cents.

## Pass/fail rules

- **V1 block precision:** of the passages the rule blocks, at least 90% are ones I labelled `block`. (A wrong block throws away a court's own words, so this is the expensive mistake.)
- **V2 block recall:** of the passages I labelled `block`, the rule blocks at least 70%.
- **V3 tier accuracy:** on the passages where I labelled a tier, the rule agrees on at least 85%, and **no passage I labelled trial court is given tier 1 or 2** (that is the mistake the owner's instruction is about: it would let a trial court outrank a High Court).
- **V4 no loss on the 65:** the rule blocks none of the 47 passages I had read as on point, except where the block is right because the passage is an argument (counted and listed one by one).
- **V5 order:** in the re-run, no result of a lower tier stands above a result of a higher tier in any list, and no blocked passage appears. Checked by an assertion in the code, not by eye.
- **Verdict:** PASS = V1 to V5 hold. PARTIAL = V1, V3 and V5 hold but V2 or V4 does not. FAIL = V1, V3 or V5 fails.
- 140 passages is a small sample: a percentage has roughly +/- 8 points of slack on it, and that is reported, not hidden. No significance test is claimed.

## Limits fixed in advance

- The rule says nothing about whether a passage is right, helpful, or still good law. A passage can be the court's own words, correctly tier 1, and still go against the person asking (entry 45 of the tier test). That is **not** fixed here and the results say so.
- Nothing is written to the index. Nothing is connected to the live site. The Recourse repository stays read-only: the delivery is a module, a bundle and patch notes the owner applies himself.
- The rule is not tuned after the labels are read, except for faults the labels show, and any such change is listed in the results with the numbers before and after.
