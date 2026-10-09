# Review tools: marking passages and scoring the search

What this is for: asking reviewers (AI tools, people, one day a lawyer) to mark the passages a search shows, then counting how useful each search version's passages are. Nothing here changes the index or the search.

Needs `pip install openpyxl`. The reply reader needs nothing else.

## Files

| File | What it does |
|---|---|
| `../review_data/pool_all.json` | The pool: 12 test questions, 199 passages (175 in the first batch, 24 in the top-up batch) with their numbers, and which search version showed each one. **Private answer key. Never send it to reviewers.** |
| `build_llm_pack.py` | Builds `LLM_Review_Pack.zip`: 24 prompt files (A = number order, B = reversed) and a README for AI reviewers. |
| `build_topup_pack.py` | Builds `Top_Up_Pack.zip` (10 prompts, one `TA` file per question with new passages, plus a README) and `Top_Up_Review_Sheet.xlsx` for the 24 top-up passages. `--with-reverse` also writes `TB` files (the same passages reversed, 17 prompts in all); off by default because reversing 1 to 5 passages is a weak order test. |
| `build_review_sheet.py` | Builds the human review sheet `Search_Review_Sheet_Pooled_v2.xlsx` (the 175 first-batch passages, dropdown marks, per-question verdicts). |
| `build_authority_list.py` | Builds `Authority_Check_List.xlsx`: is each case still good law, and what does a research tool show for the 12 questions. |
| `ingest_llm_reviews.py` | Reads the replies, checks them, and scores each search version. |
| `rtf_to_txt.py` | Turns reply files saved as Rich Text (`.rtf`, for example from Mac TextEdit) into the plain-text files the reader accepts. |
| `normalise_replies.py` | Prepares saved reviewer replies for the reader **without touching a mark**: removes the backslashes a chat window's copy button puts before `_ [ ]` (they make the JSON unreadable), reports files that are the prompt itself or byte-identical to another file, drops only the files named with `--drop`, and writes a fingerprint manifest next to the output folder. Originals stay untouched. |
| `review_common.py` | Shared helpers and the wording both prompt packs use. |
| `real_questions.py`, `real30_build.py` | The owner's 30 real questions (2026-10-09): the intake form and checks, the link-first sealing, the freeze hashes and the once-only guard for the sealed half; the builder that reads the owner's workbook and writes `../review_data/ruler/real30_v1.json` (questions only) and `real30_key_v1.json` (the private key, never read by a search or a pack builder). |
| `real30_authority_coverage.py` | Which authorities named in the owner's file the index can reach at all (name and year lookup; no search, no spend). |
| `pool_runner.py` | Runs versions A, B, E, S (and C, F for questions with a blind rewrite) over the index for the 30 questions: index-head guard, re-rank token cap, resumable; `--supplement DIR` searches main + side index and labels the run; writes the pool (`pool.json`) the pack builder and the scorer read. |
| `real30_score.py` | The authority-hit test (is the key authority in a version's top 1, 5, 10) and the known-stale rulings in the top 5, from a pool and the key; no reviewer mark. `--overlay` gives a question the key documents that only a side index holds (the key file is never changed). |
| `build_supplement.py` | Builds a **side index**: passages and vectors for judgments the main index left out, in a separate folder (default is a plan only; `--embed --max-tokens N` spends). Checks each text against the main index's own record of it; the main index is not touched. A list entry marked `fetched` is a document from outside the collection (read from a local text file with a provenance record, id 6,000,000,000 and up, must be new to the main index). The first one: `../review_data/side_index/2026-10-09_correcting_judgments/` (17 judgments, 2,572 passages, $0.098). |
| `build_advocate_sheet.py` | Builds `Mr_Advocate_Sheet.xlsx` for the practising advocate: the 16 older rulings, the owner's 7 to-verify items, the 30 questions (other right authorities, older rulings to guard against), rulings replaced by statute, a clean control. **Private: holds the key; to him only.** |
| `real30_compare_arms.py` | Compares two pools of the same questions (main index vs main index + side index): key-authority rates, where ranks moved, which side-index judgments surfaced, which passages nobody has marked. No mark, no spend. |
| `build_real30_pack.py` | Builds `Real30_Review_Pack.zip`: a prompt per question (a third also reversed), to be run in both ChatGPT and Gemini, with a README and a tick-off manifest. Replies are named `R03_A_ChatGPT.txt` and read by `ingest_llm_reviews.py`. |
| `experiments/` | The one-off scripts that made the pool and ran the site-versus-mine comparison, saved as run. A record, not a tool. Never send to reviewers. |
| `test_ingest_llm_reviews.py`, `test_builders.py`, `test_rtf_to_txt.py`, `test_normalise_replies.py`, `test_real_questions.py`, `test_real30_build.py`, `test_real30_authority_coverage.py`, `test_real30_score.py`, `test_pool_runner.py`, `test_build_real30_pack.py`, `test_build_supplement.py`, `test_real30_compare_arms.py`, `test_build_advocate_sheet.py` | Tests (invented data and a fake search service; nothing real is sent anywhere; `test_real30_build.py` also checks the committed question file against the owner's workbook). |

The builders reproduce, byte for byte or cell for cell, the files that were first sent out on 2026-10-02 (checked when they were saved here). Rebuilding changes nothing a reviewer has already seen, because the passage numbers come from `pool_all.json`. One exception, from the pool correction of 2026-10-04 (see `../review_data/README.md`): four passages (Q03 no. 4; Q04 nos. 1, 7, 12) now show their right case name and judgment id, so `Q03_A/B` and `Q04_A/B` differ from the first send in those lines only; the human sheet differs in 8 cells (case name and hidden key); the authority workbook lists judgment 18070 at row 11 instead of 7 and has 85 'our results' rows instead of 87. The top-up pack is unchanged.

## The routine

1. Build and send (never send anything from `review_data/`):

        python review_tools/build_llm_pack.py --out OUTDIR
        python review_tools/build_topup_pack.py --out OUTDIR
        python review_tools/build_review_sheet.py --out OUTDIR      # for a human reviewer
        python review_tools/build_authority_list.py --out OUTDIR

2. Reviewers return replies. For AI reviewers each reply is a plain text file named `Q03_A_<model>.txt` (first pack) or `Q03_TA_<model>.txt` (top-up); `B` (and `TB`, if built with `--with-reverse`) are the reversed-order versions. The first pack's `B` files are the real order check, because its questions have 11 to 16 passages; for that, `Q03_B` and `Q09_B` in each tool are enough. Put them in one folder. The real reply files are kept in `../review_replies/` (`J_first_pack/`, `S_top_up/`); copy both into one folder before reading. If two people use the same tool, ask them to add their initials to the model name, or one set overwrites the other (the reader reports it).

3. Read them:

        python review_tools/ingest_llm_reviews.py --replies REPLIES_DIR --out RESULTS_DIR \
            [--human filled_sheet.xlsx ...]   # a person who is not a lawyer
            [--expert filled_sheet.xlsx ...]  # a lawyer's sheet only

   It writes `llm_summary.md`, `llm_marks.csv` and, when there is more than one run, `llm_sensitivity.csv`. The summary lists file problems (not JSON, passages not marked, a quote that is not in the passage, a wrong question number), agreement between runs (kappa; the same model in A and B order shows how much position matters), how many passages were marked Misleading, and a table scoring each search version on what it showed. With more than one run it adds a sensitivity table: the same scores recomputed with disagreements dropped, settled to the lower mark, settled to the higher mark, and for each run alone, with each version compared against version A on the same questions. Treat a difference as real only if it points the same way in every column.

4. The authority workbook has no reader script: open the returned file and read the Judgments, Questions and Summary sheets.

## Reading the results honestly

- Every figure from AI replies is **LLM-judged**. A person's sheet is **human-judged (not a lawyer)**. Only a lawyer's sheet passed with `--expert` is **expert-checked**. None of it is lawyer validation unless a lawyer's sheet is there.
- Agreement between AI tools shows the marks are consistent, not that they are right: the tools share training data and can share blind spots. They are weak on "is it still good law" and on "could this mislead"; the authority workbook covers currency.
- Twelve questions can show a big difference between search versions, not a small one.
- Versions named `S ...` and `M ...` in the scoring table (the site's own search method run on the wide index; my pipeline's top 6) are sets scored on everything they showed. The others are scored on their top 5.
- The pool's passage numbers are fixed, because reviewers' marks are matched to passages by (question, number). To add a new round of passages (for example after the search changes), add rows to the pool with numbers continuing after the existing ones for that question and the `topup` flag, so every old mark stays valid.

## The one-off experiment scripts

The scripts that first made the pool (running six search versions per question, then finding the passages the site's search showed that were not yet marked) and the site-versus-mine comparison run are saved in `experiments/`, exactly as they were run, with a README that says what each did. They are a record, not a tool: they have hard-coded paths and a re-run will not reproduce the pool. `pool_all.json` is the result.
