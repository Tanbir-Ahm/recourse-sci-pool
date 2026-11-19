# Matter files (P0 and P1): what was built and what was measured (2026-11-19)

Owner's go: "go on P0 and P1. default would be 10 files per matter, 10 MB each, and a small total per account. test on public court orders and synthetic documents, later we will do it on real redacted orders." (Plan: `MATTER_FILES_PLAN.md`.)

**Nothing here has been tried with the answer model** (no Anthropic key in the sandbox). Nobody but Claude wrote or marked the test set. **No hallucination rate has been measured.**

## What was built (Recourse branch `register-hooks-and-overlay`, `recourse-web` `main`; NOT on Recourse `main`, nothing deployed)

- **P0, instructions.** `matters.instructions` (migration 0005; up to 2,000 characters). It is edited in the matter form and shown on the matter page. With `MATTER_INSTRUCTIONS=on` (default off) it reaches the answer model as a separate argument. It is placed with the answer-shaping clauses, outside the Hard rules, and framed as preferences that cannot change a Hard rule, add law, remove a REGISTER line or a warning, or claim a person checked anything. It is never folded into the question, so the Act Directory, register and grounding checks do not read it as the person's words.
- **P1, documents.**
  - Switch `MATTER_FILES=on` (default off; off means the routes answer 404 feature_off and the engine sees no document).
  - Accepted files are PDFs with text, `.docx` and `.txt`. The first bytes must agree with the name.
  - Limits: 10 per matter and 10 MB each (fixed), and the plan's `matter_files_mb` per account (50 on the free plan, provisional).
  - **The file's bytes are not kept.** Only the text a program read from it is stored, as passages with page (PDF) or paragraph (Word, text) numbers, plus a vector each when the meaning service answers. The name, size and SHA-256 are kept too.
  - A page that is a picture with little text is reported as not read; there is no OCR. A file with no readable text is refused (`no_text`).
  - The search runs within ONE matter, selected by the matter id and the person's id. It combines words (BM25 over stems) and meaning (voyage-law-2), fused by rank. It hands over at most 6 passages and 7,000 characters, as a separate engine argument, never as words of the question.
  - The block sits AFTER the legal information, under its own header. Every document line starts with "| ", and citation-like text, the header and the end line are neutralised inside documents.
  - A clause (outside the Hard rules) tells the model several things:
    - documents are facts as the documents state them, never law and never instructions;
    - cite `[Doc N, p. M]` / `[Doc N, para M]`;
    - say "the documents given do not show ..." when they do not.
  - After the answer, a code check looks for every quotation the answer attributes to a document on the page it cites. Its verdicts are ok, other_page, other_doc, not_in_file and unknown_doc. Its notes go into a "Your documents" box under the answer, also in the PDF/Word download, and are saved with the answer.
  - A section that only the documents name does not count as "made up". Instead it gets a note: its text was not among the law given.
  - A case that only the documents name is NOT accepted by the invented-case check: a document cannot make a case real.
  - When the library finds nothing but the documents have passages, the answer is written from the documents alone and the page says so.
  - The data export carries the files' names and read text. Deleting the matter, the file or the person deletes them.
  - Log lines carry counts only: no name, no text.

## The measurement (frozen in commit `3cbce34` before any code; `frozen_questions.json`, `quote_cases.json`, `make_docs.py`, `measure.py`)

**Documents.**
- Public: four Supreme Court judgments (Arnesh Kumar, Pankaj Bansal, Prabir Purkayastha, Satender Kumar Antil 2026; Indian Kanoon PDFs already in the Recourse repository) and two synthetic samples already there (an arrest memo, a section 138 notice).
- New synthetic ones (invented names, marked so in their footer): a 6-page chargesheet, 2 remand orders, a bail order in Word, a complainant's letter carrying planted instructions plus a scanned page, a scan-only FIR, a text note, and one order of another matter.

| Measure | Result |
|---|---|
| M1 reading | Every page and paragraph read; the letter's picture page reported unread; the scan-only file refused (`no_text`); 0 text pages wrongly reported unread |
| M2 search, 39 answerable questions, gold page among the 6 passages handed over | words only **33/39**; meaning only **35/39**; combined (the code's default, fixed before the run) **33/39** |
| M2b three questions with no answer in the files | no score floor separates them (the top meaning score of one, 0.43, is above the lowest of an answerable one, 0.27): the model must say "the documents do not show it"; a floor would not do it |
| M3 quote check, 25 cases | **24/25**. The one failure is an error in the frozen case, not the code: case 14 quotes four words, under the declared five-word minimum, so the code rightly skips it |
| M4 fencing (structural) | the planted instruction, a fake "Hard rules" heading, a fake end line and a fake citation all stay on fenced lines; one end line of ours. **Whether the model obeys the fence is NOT tested** |
| M5 leakage | Question 43 is about the other matter's document. Searched with matter A's passages it returns nothing of matter B; mixed together, matter B's passage would have ranked first. So the separation is what protects it. The API test proves the database side: another matter's, another person's or an unfiled conversation's passages never reach the engine |

The same numbers came out on the final code (run 1 kept as `results_run1.json`, final as `results.json`).

**What the misses show.**
- Long judgments crowd out the short case papers. "When was my client arrested?" brought arrest passages from Pankaj Bansal and Prabir Purkayastha, not the chargesheet's first page.
- A per-document cap or a preference for the matter's own case papers might help, but **it was not built**: it would be tuned on this set. A fresh set is needed.
- The 2-question gap between meaning-only and combined is too small on 39 questions to choose between them. The default stays as declared.

**Cost.** About 5,100 characters of document text per question (about 1,300 tokens), roughly Rs 0.25 at $2 per million input tokens (estimate, not measured). Embedding at upload: voyage-law-2, a few paise for a long PDF.

## Tests (all offline and free)

- Recourse:
  - `test_matter_files.py` (reading, passages, search, block, clause, quote check);
  - `test_matter_files_engine.py` (the prompt with a stubbed model: block placement, the Hard rules unchanged in v1/v3/v3-lawyer, the checks);
  - `test_api_matter_files.py` (routes, limits, ownership, leakage, the engine argument, the saved check, export, deletion, logs).
  - The suite before the last fixes: 157 of 158. The one failure was `api/openapi.json` out of date: regenerated, and the route contract was updated on purpose.
- `recourse-web`: tsc clean; 140 unit tests; 82 browser tests (78 passed and 4 skipped in the full run, the documents spec re-run alone 4 of 4 after one fix).
  - The new spec covers: add, refuse, ask, the box, the wrong-page note, remove, instructions, phone width, and axe on the matter page and the chat page (WCAG A/AA rules there, as the other chat specs use).

## Not built, on purpose (MATTER_FILES_PLAN P2 to P4)

- Facts proposed from files into the case file.
- Fetching the sections a document charges into the answer.
- Clocks.
- OCR.
- Drafting (not approved).

The search does not prefer the matter's own case papers over reference judgments; see the misses.
