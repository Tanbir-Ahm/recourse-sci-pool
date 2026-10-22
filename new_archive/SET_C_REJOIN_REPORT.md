# Set C (Guwahati, open-bucket text): word rejoin and trial block (2026-10-22)

## The problem
The bucket's Guwahati PDFs are typed on an 80-column grid. A line break falls inside a word ("popular|ly") or at a word end where the space was lost ("months|of June"). About 3 in 4 breaks are inside a word. The earlier `unwrap_fixed` glued every full-width line to the next without a space, so it merged words at the other breaks.

## The rule (`rejoin_guwahati.py`)
Each break between two letter pieces L and R is decided from a lexicon built from CLEAN text only (the 3,747 Supreme Court newer-archive judgments and the 776 Guwahati court files; the bucket text itself is not used): a capital after a lowercase letter means a new word; if only L+R is a word, join; if only L and R are words, put a space; if both readings are words, compare how often L+R occurs as one word against "L R" as two; if neither is a word, join. Lines that end a sentence, or are more than 12 characters short of the page width, are never joined.

## Measurement (n and method stated; no lawyer or human labels involved)
- **Synthetic test with known answers (20,000 cut points taken inside real bucket lines, 82% mid-word, 18% at a word end):** right 99.6% of the time. Glued two words: 1.8% of the word-end cuts. Split a word: 0.1% of the mid-word cuts. The old rule ("always join") is right 81.9%. Errors are mostly names and damaged words that neither the lexicon nor the text can settle. The test assumes the grid model above; it was not checked against a court copy of the same judgment (the 20-document comparison set of 2026-10-21 is not stored in the repository).
- **Real documents (300 random reasoned documents, 1.07M words):** share of words found in the clean lexicon: raw 89.9%, old rule 94.5%, new rule 96.0%. Single and double letter fragments: 5.9%, 3.2%, 2.8%. The remaining unknown words are mostly initials, abbreviations (Mr, WP, PW, Rs) and Assam names.
- Reproduce: `rejoin_eval_synthetic.py` and `rejoin_eval_real.py` (paths are relative to the layout used in the session: data worktrees one level above the code).

## Blocks
`build_index_blocks_c.py` writes `index_blocks/ghc_bucket-NNNN.*.jsonl.gz` (scope `ghc_bucket`, already known to `sci_index.py`): 8,271 reasoned documents in 34 blocks (ids 2,000,500,000 to 2,000,508,270), written on the local `claude/ghc-bucket` worktree and NOT committed or pushed (see below). No-spend preparation with the indexer's own code: 980 judgments kept as criminal law (the earlier plan said 974), 24,511 passages (plan 25,489, fewer because fewer fragments), 5,592,428 estimated tokens before the usual calibration.

## Trial block (real spend)
Block 2000508000 (the last full block, 2016-17 judgments): 250 documents, 31 kept (219 civil skipped), 729 passages, 178,530 tokens charged against 186,719 estimated (4.4% lower), nothing wasted, pushed to `claude/sci-index` (head f982dae). Vectors: 729 rows of 1,024 numbers, finite, unit length, ids in range, every judgment records court, date and link, 97% of passages carry a paragraph number. Total spent 77,642,302 of 85,000,000. The other 33 blocks are not embedded.
