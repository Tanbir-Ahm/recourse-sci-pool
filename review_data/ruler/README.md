# The ruler (PRIVATE, like `../pool_all.json`): the fixed test for the search versions

Built 2026-10-08 (plan item 1, "build the ruler", approved by the owner as Steps 0-1). Code: `review_tools/ruler.py`; tests: `review_tools/test_ruler.py`. **Never send this folder, or anything built from it, to reviewers.** It holds the answer key and the frozen half.

| File | What it is |
|---|---|
| `topics_v2.json` | Hand-written source: the ten new topics (questions, expected judgments, where Recourse holds the key paragraphs), the two corrections, notes on judgments the index cannot show. Written before any search was run on the new questions. |
| `ruler_v2.json` | Built from the source plus `../pool_all.json`, `../../landmarks.json`, the index and Recourse's `chunks/`. 16 topics, 33 question entries (32 active), 44 key paragraphs, the split and the freeze hash. |
| `frozen_runs.jsonl` | Appears when the frozen half is first handed out. Empty now. |

## What it holds, in plain terms

- **16 topics, each with one everyday ("lay") question and one legal-wording question.** Six are the original topics (Q01-Q12; all decided before 2017). Ten are new (Q13-Q32; judgments from 2017 to 2025).
- **For each topic: the acceptable judgments and the key paragraph(s)** where the Court itself states the rule. A search result can be compared with them with no human marking. This is the "landmark" test, which is a weak measure on its own (other passages can also be right); the marks from reviewers still do the real work.
- **Where the key paragraphs come from.** For the ten new topics, only from the Recourse repository (read-only, commit 721e063): verbatim excerpts it already lists as hand-verified in its doctrine maps, chosen by Recourse's curation and not by this project's search. For the six original topics, this project's own picks (`landmarks.json`) plus Recourse's excerpts where Recourse has them (they agree: the same passages). **Nothing here is lawyer-checked.**
- **All 44 key paragraphs were found in the index** (a long one can be cut across passages: the Section 50 paragraph of Jadeja is spread over three).

## The split: how many are frozen, and why it is not half

| Half | Topics | Active questions |
|---|---|---|
| dev (may be used to tune) | T01-T06 (the original six), T07, T09, T10, T11, T14, T15 | 24 |
| frozen (run once, at the end) | T08 default bail (Rakesh Kumar Paul 2017, Bikramjit Singh 2020, M. Ravindran 2020), T12 NDPS Section 37 bail (Nawaz Khan 2021), T13 informant-as-investigator (Mukesh Singh 2020), T16 domestic-violence complaint after leaving (Prabha Tyagi 2022) | 8 |

**The frozen half is 8 of 32 questions (25%), not half.** The 12 original questions were scored, rewritten by hand and discussed before this file existed, so they cannot be frozen. Three new topics (T10, T11, T15) are in a doctrine group with an original topic (civil dispute as crime; compounding; cheque presumption), so they stay on the tuning side: a case must not sit on both sides. The remaining 14 new questions were split by a fixed rule: inside each area (arrest and bail, matrimonial, NDPS) the groups are ordered by SHA-256 of `recourse-ruler-v2|group` and alternate frozen, dev, frozen. One seed, used once.

**Eight questions can only show a big difference.** To widen the frozen half, topics are needed. The Recourse repository holds hand-verified excerpts for roughly twenty more cases, all decided before 2017 and not each checked against the collection (for example Lata Singh 2006, Inder Mohan Goswami 2007, Karnail Singh 2009, Lalita Kumari 2013, Parmanand 2014). Nothing else from 2017 on is available without writing the ground truth ourselves or asking a lawyer.

The guard (`ruler.select`) hands out the frozen questions only for a final run with a label, only if the freeze hash still matches, and only once unless a repeat is asked for; every hand-out is logged in `frozen_runs.jsonl`. `python review_tools/ruler.py check` verifies the hash; `list --half dev` prints the questions to tune on.

## What was seen before the freeze (disclosure)

- No search was run on any new question, and no passage of a new topic has been marked.
- Before the split was computed, a matching probe printed the index's passage type for every key paragraph. It showed that Rakesh Kumar Paul para 40 (T08, frozen) is labelled "argument" although it is the Court's own holding, and that the key paragraphs of Nawaz Khan (T12, frozen) sit inside one merged passage (paras 19-20) and across two (para 24). **Rule for later work: no label rule, weight or rewrite may be motivated by what was seen on a frozen topic's key paragraphs or passages. The passage-label work uses the dev topics and the original pool.**
- The questions were written after reading Recourse's notes on each case. They describe the situation or the legal issue and do not quote the key paragraphs. The everyday questions were written by Claude, not by laypeople, and not pretested.

## The corrections

- **Q06 is superseded by Q06v2.** Q06 asked about Section 325; the landmark (Nanda Gopalan) is about Sections 324 and 326, and Section 325 is compoundable with the court's permission. Q06v2 says Section 326. The old passages were found with a section search on 325, so they are not a fair pool for Q06v2: **it needs a new pool and new marks.** Q06's marks stay on record, labelled as answering the old wording.
- **Q05's text is unchanged** (it only says "grievous hurt" and "non-compoundable"), so its marks stand. **Its hand-written rewrite** (used by versions C and F) now names Section 326; the old one is kept as `rewrite_v1`. C and F on Q05 were run on the old rewrite and need re-running and re-marking.

## What still needs a reviewer (nothing here can be done by the code alone)

1. **J: Q09 in Gemini, orders A and B** (asked for). Q09's 21 passages are marked by one reader only; three of them are "Misleading".
2. **A new pool for Q06v2 and for the 20 new questions**, then marks from the AI tools, then a lawyer's look at the borderline marks. The pool is built by running the search versions on these questions (this uses Voyage re-ranking; the allowance is still to be read from the owner's dashboard) and sending them out like the first pack. The frozen questions are pooled only at the end.
3. **A spot-check of about 20 labels** by the owner or a lawyer; the three "Misleading" Q09 passages and Rakesh Kumar Paul para 40 are good first picks.

## Judgments the ruler cannot test (the index or collection lacks them)

Listed in `ruler_v2.json` under `index_gaps`. Satender Kumar Antil v CBI (2026 INSC 115), which Recourse treats as the current-code restatement of Arnesh Kumar, is not in the collection (2026 coverage is partial: 214 judgments, INSC numbers up to 847). (Correction of 2026-10-08: Mohan Lal (2018), the decision Mukesh Singh overruled, IS in the collection and the index as 'MOHANLAL'; an earlier version of this paragraph said it was missing, because a search had split its name into two words.) Youth Bar Association (2016) and Usha Chakraborty (2023) have no title match. Shreya Singhal (2015), Hiral Harsora (2016), Satish Chander Ahuja (2020) and S. Vanitha (2020) are in the collection but left out of the index by its criminal-law filter, so no search can find them.

## Currency: the second pass (agreed with the owner, 2026-10-08)

The Overruled Register and the checker are **not** part of the search and are kept out of the relevance marks. Plan for every pool: (1) search and AI-tool marking with the register off, so relevance numbers stay clean; (2) `review_tools/currency_pass.py` over the saved results, which counts passages from register cases and from known-stale cases per search version and simulates the register's demotion; (3) trap questions from Mr. Advocate double as a test of whether the register holds the trap rulings (a gap goes to his weekly sheet as a proposal). On the first pool the register flagged none of the stale passages, because neither stale case is in it. The register sees only explicit Supreme Court overrulings: expect misses.
