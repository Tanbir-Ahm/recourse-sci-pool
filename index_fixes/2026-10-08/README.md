# Index fix applied 2026-10-08: Proposal A (four duplicate judgments, 659 passages)

`plan.json` is `../2026-10-07/plan_proposalA.json`, applied on the owner's acceptance of 2026-10-08 with `python index_dedupe.py apply --index-dir ../recourse-sci-index --plan index_fixes/2026-10-07/plan_proposalA.json --push` (commit `3c80a26` on `claude/sci-index`; to undo, revert that one commit).

Removed (the other copy of the same judgment stays): 1000000830 (Devarapalli Lakshminarayana Reddy, [1976], law-report scan; kept 5614), 1000000717 (Ishar Das v State of Punjab, [1972], scan; kept 6906), 1000250000 (Kumaran v State of Kerala, 2017; kept 44878), 44879 (Mukesh & Anr v State for NCT of Delhi, the Nirbhaya case; kept the more complete law-report copy 1000250002).

Result (counted afterwards from the index files): 10,505 embedded judgments (was 10,509), 236,155 passages (was 236,814), vector rows equal passage rows in every block, none of the four removed judgments still embedded. No tokens were spent. The EVAL step of the runbook (a few cents of Voyage use) was not run: it waits for the owner's re-ranking allowance, and the baseline run on the new questions exercises the index anyway. `review_tools/test_builders.py` reads `plan.json` files in `index_fixes/` to make sure no review-pool passage points at a removed judgment.
