# The search versions behind the review packs, in plain words

**Do not send this file to reviewers.** It names the search versions, and the pool is a private answer key (see `../../review_data/README.md`).

Numbers are from `review_data/pool_all.json` as of 2026-10-04 (after the four-passage correction). The technical record is in `README.md` beside this file, and the scripts are saved there as they were run.

## What every first-pack version does the same way

1. The question is turned into a meaning fingerprint, and the 100 closest passages are taken.
2. A keyword search takes the top 50. If the text being searched names a section, such as "section 138", a section search adds up to 30 more.
3. These are merged into 60 candidates.
4. A second model (the re-ranker, Voyage `rerank-2`) reads the question with each candidate and re-scores it.
5. The top 10 go into the pool. The pack then shows up to 16 passages per question, in shuffled order.

L is the exception. It is not a search.

## The six versions in the first pack

| Version | Plain description | What is different | Questions | Top-10 slots in the pack |
|---|---|---|---|---|
| **A "today"** | The pipeline as it works now | After re-ranking, scores are weighted by passage type (reasoning counts fully, facts 0.8, arguments 0.85, orders 0.6, headers 0.3). A passage that names the section asked about gets a 10% boost. | All 12 | 115 of 120 |
| **B "no repeats"** | A, without copies | Identical-text passages are removed before the 60 candidates are chosen, so copies cannot fill the list. | All 12 | 119 of 120 |
| **E "no multiplier"** | A, without the weights | Uses the re-ranker's raw scores. Shows whether the weights help. | All 12 | 108 of 120 |
| **C "rewrite"** | A, with a rewritten question | The plain-language question is rewritten in legal wording and that is searched. | 6 plain-language | 50 of 60 |
| **F "merged"** | A and C together | Candidates from both are pooled, and each is scored by the better of its two scores. | 6 plain-language | 52 of 60 |
| **L "landmark key passages"** | Not a search | The 1 or 2 verified paragraphs of the expected case, added by hand so they are judged even if no search returns them. | All 12 | 20 passages, always kept |

How to read "115 of 120": A, B and E each list 10 passages per question, so 12 × 10 = 120 slots. C and F run only on the 6 plain-language questions, so 6 × 10 = 60. The top number is how many of those passages reached the pack. The rest were trimmed because the pack is capped at 16 per question. Six questions hit the cap (Q01, Q03, Q07, Q09, Q10, Q11), and every shortfall is in one of them.

Missing slots by question: A: Q09 3, Q10 1, Q11 1. B: Q11 1. E: Q01 2, Q03 1, Q07 3, Q09 3, Q10 2, Q11 1. C: Q01 1, Q03 2, Q07 1, Q09 2, Q11 4. F: Q01 1, Q03 1, Q09 2, Q11 4.

The trimming rule: passages in A's top 5 and the landmark passages are kept first. The rest are kept by how many versions found them.

Which questions run the section search: only those whose searched text names a section. Among the 12 original questions these are Q01, Q02, Q06, Q08, Q10 and Q12. The plain-language rewrites for Q01, Q05, Q07, Q09 and Q11 name sections, so versions C and F run it for those. Q03 and Q04 have no section search in any version.

## The two sources behind the top-up pack

| Source | Plain description | How it picks passages | Count |
|---|---|---|---|
| **S "site shown"** | The Recourse site's own search code, on the same index | Top 50 by meaning, keep those within 0.08 of the best score, then at most 4. Up to 2 keyword extras are allowed, but only if the passage is also in the meaning top 50. No second-model re-ranking. | 64 passages: 40 already in the first pack, **24 new** (the top-up) |
| **M "mine top 6"** | My own top 6 per question, built like A | Same as A | 72 passages, all already in the first pack |

The site run leaves out the site's own topic routing and hand-pinned paragraphs, so it measures the site's search step alone, not the live site.

## How the results are scored

- A, B, C, E and F are scored on their top 5 passages.
- S and M are scored on everything they showed, because they show about 4 to 6 passages each.
- A passage found by several versions appears once in the pack. The 175 passages are not the sum of the lists.
- Every figure from AI reviewers is LLM-judged. It becomes expert-checked only if a lawyer's sheet is read with `--expert`.

## Snapshot note

The first pack was built on 2026-10-02 at 14:58, before the duplicate fix of the same day (8,236 judgments, 156,235 passages). The top-up was built afterwards on the fixed index (8,101 judgments, 153,981 passages). The effect is probably small.
