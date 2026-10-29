# Verbatim excerpts ("anchors"): what they are and how a topic is added

An **anchor** is a short passage of a Supreme Court judgment, copied word for word, that the Recourse site hands the answer-writing model when a question is of a kind it covers (a **topic**). The words are checked by code against the Supreme Court's own archive PDF. A program cannot decide that the passage is the right authority or that the law has not moved, so every anchor stays `machine_checked` and the site words it "verbatim excerpt, not yet confirmed by our reviewer" until a person answers the sheet for it.

| Topic | Cases | Recourse switch (default off) | Reviewer sheet |
|---|---|---|---|
| `trial_delay` (delay in a criminal trial, Article 21) | P. Ramachandra Rao (2002), Hussainara Khatoon (I) (1979) | `ANCHORS` | `ANCHOR_SHEET_trial_delay.docx` |
| `circumstantial_evidence` (conviction on circumstantial evidence alone) | Sharad Birdhichand Sarda (1984), Hanumant (1952) | `LANDMARKS` | `ANCHOR_SHEET_circumstantial_evidence.docx` |

Files: `anchors/anchors.json` (the data and the check records), `sci_anchors.py` (verify, export, sheet, confirm), `test_sci_anchors.py`. The Recourse module `excerpt_anchors.py` reads the exported copy `excerpt_anchors.json` (`python3 sci_anchors.py export --out <Recourse checkout>`).

## Rules that do not bend

- **Never mark an anchor `reviewer_confirmed` on anyone's behalf.** Only `python3 sci_anchors.py confirm ID --by NAME` after the reviewer has answered the sheet.
- **Never add an excerpt that `verify` has not passed.** `export` refuses it.
- **Never say a case is good law.** The anchors, the register and the checker only subtract trust or warn.
- **A new topic gets a switch of its own.** `ANCHORS` has been on in production since 2026-10-16; a topic added under it would go live on the owner's next merge. A new switch stays off until the owner sets it.

## Adding a topic

1. **Choose the cases and read them.** Read the judgment in the court's PDF (`https://api.sci.gov.in/jonew/judis/<doc>.pdf`). Choose passages that state the rule in the court's own words. Shorter is better: a segment is one unbroken stretch; several segments of one excerpt are joined by "..." on the page.
2. **Write the record in `anchors.json`.** Fields: `id`, `topic`, `case_name`, `aliases` (optional: a short form of the name that the answer may use, such as "Sharad Sarda"; it lets the label be found, nothing else), `year`, `date`, `court`, `bench_note` and `bench_source` (say where the bench comes from; leave it out if the archive's header is wrong), `citation` and `citation_source`, `link`, `also_in` (later judgments in the index that quote the passages with their paragraph numbers or citation: `doc`, `name`, `must_contain` phrases that `verify` looks for), `excerpts` (`label`, `segments`, optionally `paragraph`, `report` when it is not the SCC report, `paragraph_source`, `note`), `status` = `machine_checked`, `note_for_reviewer`.
   - **Paragraph numbers** are shown only if something other than a guess supplies them: the archive PDF of an old judgment carries the printed report's page numbers, not the SCC paragraphs, so take each number from later judgments that quote the passage with it (`also_in`), and say so in `paragraph_source`.
3. **Old printed reports.** If the PDF has page numbers, footnote marks or hyphenated line ends inside a sentence, name only what the check may look past, in `verify_options`: `ignore_page_numbers`, `ignore_footnote_marks`, `join_hyphens`, `ignore_lines` (exact footnote lines). A word that differs is still a failure; what was looked past is written into the check record and onto the reviewer's sheet. The default is nothing.
4. **Verify.** `python3 sci_anchors.py verify --write --index <index worktree folder>`. It must say `OK` for every anchor and `True` for every `also_in` line. `test_sci_anchors.py` has negative controls (a changed, added or dropped word fails).
5. **Sheet wording.** Add the topic to `TOPIC_INFO` in `sci_anchors.py`, then `python3 sci_anchors.py sheet --out anchors --topic <topic>`.
6. **Recourse side** (`excerpt_anchors.py`): add the topic to `TOPICS` with its own switch and a question test; add its wording to `TOPIC_WORDING`; add a guidance function that fires only when the words it relies on are among the excerpts. Write the **test questions first** (a file of questions that should and should not hand the excerpts over, committed before any pattern exists), then the patterns, then a second set that tuning may use, then a third set run once; and run the independent pool of unrelated questions for false fires. Record all of it, including the misses (`review_results/2026-10-29_landmark_circumstantial/` is the model).
7. **Export and test.** Export into the Recourse checkout, run its tests (`run_tests.py`), and give the owner the staging steps (`DEPLOY_STAGING.md`).

## What is still true after all this

Nothing here has been read by a lawyer, and nothing has been tried with the answer model in the sandbox (it has no model key). The owner's staging test is the first time the model sees the excerpts. No hallucination rate has been measured.
