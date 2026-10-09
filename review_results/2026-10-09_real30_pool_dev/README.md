# Tuning-half pool of the 30 questions, 2026-10-09 (PRIVATE)

Never send this folder to reviewers: `pool.json` names which search version found each passage, and `AUTHORITY_HITS.md` uses the private key.

## What is here

| File | What it is |
|---|---|
| `pool.json` | The pool: for the 19 tuning-half questions, the passages to be marked (217 in all, collapsed by identical text, shuffled with a fixed seed, numbered) with the version(s) and rank that found each, and each version's ordered top results (for the scorer). Titles of bucket judgments were filled afterwards from the index's document records (`run.titles_filled_afterwards`). |
| `questions.jsonl` | The raw run record, one line per question, as written while the run went. `pool.json` is compiled from it. |
| `spend.json` | What was billed, per question and in all. |
| `authority_hits.json`, `AUTHORITY_HITS.md` | The authority-hit test: is the named key authority in a version's top 1, 5, 10, and which older rulings reached the top 5. No reviewer mark. |

## How it was run

`python review_tools/pool_runner.py --half dev --max-rerank-tokens 15000000 --out review_results/2026-10-09_real30_pool_dev`, on index `claude/sci-index` `3c80a26` (the head recorded in the question file; the runner refuses any other), with the blind rewrites of 2026-10-09 for the 12 everyday and narrative questions (versions C and F). Versions: A today, B no repeats, E no multiplier, S site shown (the Recourse site's own search code run over this index, no pins, no routing) and, for the 12 rewritten questions, C rewrite and F merged. Only Voyage was called: 74 re-rank calls with `rerank-2` and 50 query embeddings with `voyage-law-2`.

**Spent:** 1,812,788 re-rank tokens and 3,258 embedding tokens, about **$0.09** at the listed prices ($0.05 and $0.12 per million tokens; the first is from third-party price lists, so the owner's dashboard balance, $9.88 before the run, is the check). The site arm's own query embeddings are not in the count (a few hundred tokens).

## First look (authority-hit test; 14 answerable questions; LLM-free and mark-free)

| Version | Key authority in top 1 | top 5 | top 10 |
|---|---|---|---|
| A today | 5 | 10 | 10 |
| B no repeats | 5 | 10 | 10 |
| E no multiplier | 4 | 9 | 10 |
| S site shown (3 to 6 passages shown) | 5 | 6 | 7 |

On the 9 answerable questions that have a blind rewrite (like with like), top 5: A 7, B 7, E 6, C 6, F 6, S 5. **The blind rewrite gives no gain on this measure.** Four answerable questions have no key authority in any top 10 of A (R09, R14, R20, R22); the file names one authority per question and other authorities can be right, so only the marks can say whether those are failures. Fourteen questions: differences of one or two questions are noise.

Where the index lacks the ruling that corrects an old one (R15, R21: the index-gap questions), every version puts the old ruling at the top: R15 Rajesh Sharma (modified by Social Action Forum) at rank 1 in A, B and E (and at rank 2 in A and B, rank 3 in E); R21 Shafhi Mohammad (overruled by Arjun Panditrao) at rank 1 in A and B, at ranks 1 to 3 in E and at rank 3 in S. On the answerable questions the old rulings in the top 5 are R09 Dashrath Rupsingh Rathod (replaced by statute) at rank 5 in A, B, E and rank 4 in S, and R11 Kanhaiyalal (overruled by Tofan Singh) at ranks 2 and 3 in the rewrite arms C and F only.

## Next

The marking pack (`../2026-10-09_real30_marking/`) goes to J and S: every file in ChatGPT and in Gemini. Replies go through `ingest_llm_reviews.py` (read, validate, agreement, per-version scores) and `real30_lights.py` (relevance and currency lights per domain, under every treatment of disagreements). Everything from AI replies is LLM-judged until a lawyer's sheet is added. The sealed half is not run until the owner decides.
