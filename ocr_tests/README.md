# OCR bake-off scripts (no case data in this folder)

Support for `OCR_TRANSLATION_TEST_PLAN.md`. Scripts here take the document and the reference terms on the command
line. **Never commit a real case document, a case number, a name or a reference file to this public repository.**

## Sarvam run (first candidate, started 2026-10-25)
Needs, in a fresh session: `SARVAM_API_KEY` set as an environment variable of the cloud environment, `api.sarvam.ai`
in the environment's allowed domains, the PDF uploaded again, and a private `refs.json` (page -> terms read by eye).
The SDK confirms `as-IN` (Assamese), `kn-IN` and `en-IN` as document-digitise language codes; one language per job,
at most 10 pages per PDF. Price (docs pricing page, read 2026-10-25): Rs 0.50 per page for digitisation, Rs 2 per 1,000 characters for translation,
Rs 100 free credit for each verified user, so the 14-page file in three jobs (28 pages) is about Rs 14. Document AI is limited
to 10 requests per minute, so the script polls every 10 seconds and retries on HTTP 429. Keys are made at
indus.sarvam.ai/key-management. Digitise results return page text in md or html;
no per-block confidence is documented for digitise (only for extract), so check the saved JSON for one.
`python sarvam_run.py --selftest` checks the wiring without calling Sarvam.

`sarvam_translate_check.py` tests translation alone on invented clean Assamese and Kannada sentences with known English
(`sarvam-translate:v1`, source and target `as-IN`/`kn-IN` to `en-IN` are listed as allowed; 2,000 characters per request).
The Sarvam Vision model page makes no claim about handwriting; test it before assuming it.

## What the first Sarvam runs taught the script (2026-10-25)
The default output is HTML and the API refuses `md` for such a job, so the script reads the JSON results
(documents -> pages -> blocks with text, layout_tag, reading_order; no confidence field). A job takes at most
10 documents, so the all-pages pass is sent in chunks of 10. `--reuse` re-reads saved job results instead of paying again.
Summary of the first results is in section 10 of `OCR_TRANSLATION_TEST_PLAN.md`.

## Paid-tier Gemini test (prepared and run 2026-10-26; results in section 10c of the test plan)
The free tier cannot call the largest Gemini models (`gemini-3.1-pro-preview` and `gemini-4-argon` returned a quota error on the
free key; `gemini-3.8-flash` was overloaded). `gemini_read_check.py` first checks which models answer, then reads one handwritten page
several times per model and scores each reading against a private facts file (label -> regex; labels starting `[digit] ` are critical
numbers such as dates, ages and amounts). Run it from a session whose environment has `GEMINI_API_KEY` for a billing-enabled project,
with the approved image and facts file supplied outside the repo. `python gemini_read_check.py --selftest` checks the wiring only.
The first real reference (15 facts for one handwritten complaint page) and the free-tier results are in section 10b of the test plan.

After the first run the script was changed: matching now normalises text and patterns to NFD (Bengali y-with-dot stored composed or decomposed no longer causes false misses), and a reading whose Gemini finish reason is not `STOP` is reported as cut off. Keep the facts file, the image and the readings outside the repository.

## Step 3 harness (2026-10-27): run pages through the readers, compare, and mark

Three small scripts replace the ad hoc ones used for sections 10c to 10j. All three have a `--selftest` that uses **invented text only**.

| Script | What it does |
|---|---|
| `harness.py` | Sends each page image to each reader model, runs times, saves every output as `RUN/<page>/<model>/run<N>.txt`, and appends **every call, including failed ones**, to `RUN/ledger.jsonl` with time to first token, total time, input, output and thinking tokens, why it ended (`ok`, `INCOMPLETE (MAX_TOKENS)`, `EMPTY`, `failed`), and an **estimated** cost in rupees. `--budget-inr` stops it before a call that would pass the budget. Calls already paid for are skipped on a rerun; only failed calls are retried. Incomplete readings are saved as `run<N>.INCOMPLETE.txt` so they cannot be mistaken for good ones. `--report RUN/ledger.jsonl` prints a per-model summary. **PDFs:** the pages folder may also hold PDFs. Each PDF page goes through `pdf_triage.py` first: a page with a clean text layer is not sent to a model (its exact text is saved to `RUN/_text` and logged as model `text-layer`, cost 0); every other page is rendered to `RUN/_pages` and read like an image. Options `--pdf-reader tesseract|vision` (vision sends each PDF page to Google), `--pdf-lang`, `--pdf-dpi`, `--pdf-undecided image|skip`, `--pdf-no-match`. The triage result is kept in `RUN/triage/`, so a resumed run does not repeat it. Run end to end on two real PDFs on 2026-10-27 (one text layer used with no model call, one image-only file read by argon for Rs 2.86 logged). A text-layer page has no English draft yet: translating it is a separate step that is not built. |
| `pdf_triage.py` | Step 2 of the pipeline. For each page of a PDF says `use_text_layer`, `treat_as_image` or `person_decides`, from the text layer, its fonts, signs of a broken font encoding, and a base-letters-only comparison with the rendered page (read by Tesseract). Can save the text of good pages and a PNG of the others. Output is counts and verdicts only. **Built 2026-10-27 and run on two real files only** (one good layer under a garbled picture: use the text, 83.3% match, close to the 80% cut-off; one image-only file: treat as an image); the cut-offs are a first guess. `--reader vision` reads the page with Cloud Vision instead of Tesseract (97.7% match on the good file against 83.3%) but sends every page to Google, so use it only where cloud processing is allowed; it needs `GOOGLE_CLOUD_API_KEY` in the environment. |
| `checker.py` | Compares readings of one page. Every disagreement (a number, date, amount, name, land unit, or a whole line) comes first; every value the readings **agree** on is listed too, marked "still confirm", because agreement is not correctness. It never marks anything correct. `--page typed\|handwritten` runs the whole page check of plan section 11 on two blind readings of the same page (view 1 the image as given, view 2 a padded copy): letter agreement, dropped or cut-off readings, English sentences that changed between the views, `[unclear]` marks, the checks in `redundancy.py`, an optional third view that only shows which side of a disagreement it sides with, and a green / amber / red light with the reasons. `check_text_page` does the same for a PDF page whose own text is used (two English drafts compared). Cloud Vision is no longer part of it. Cut-offs are a first guess from Assamese pages only. |
| `marksheet.py` | Prints one self-contained HTML marking sheet per page: the page image beside the check list, the differing lines, both English drafts, and the plan's section 8 error table (type, severity, warned?) with Copy-as-CSV. Nothing is loaded from the internet, and reader text is escaped. Since 2026-10-28 a value you type in "Value on the page" is compared at once with both readings and flagged if it differs from both, the page summary says which reading it refers to, and the downloaded CSV includes the check-list answers. |
| `redundancy.py` | Checks that need no model: impossible dates (read with the Assamese danda too), numbered lists that skip or go back, English amounts whose digits and words disagree, the same name spelled two ways across pages, and names close to a confirmed name ("did you mean"; never auto-corrects). **Not built:** amounts in words against digits in the original script (no checked Assamese number-word parser), weekday against date. |
| `report.py`, `print_pdf.js` | One self-contained HTML report per page (the light and why, the page image, the English from each reading side by side, the page checks, the must-check list, the original-script readings in an appendix), printed to PDF with Chromium through Playwright. |
| `score_reference.py` | Scores English drafts against an official English text of the same document: closeness per sentence, numbers and names that differ. A true reference, used twice so far (sections 10r and 10t); it also counts clause, rule, article, section and order references including one-digit ones, which the plain number check ignores. The inputs are case data; keep them outside the repository. |
| `pipeline.py` | **Runs a whole test**: PDFs and images in, a report and a marking sheet per page out. PDF pages are triaged first (a good text layer is translated twice with a text-only call and no reading model); every other page is read as view 1 (image as given) and view 2 (padded copy), plus view 3 (ultra-high detail) only where the checker flags the page. Red pages are listed first. See the next section. |

`models.json` holds the model list, the key each one uses (read from an environment variable; keys are never printed or pasted into chat), and the prices. **The prices are third-party and unverified, and the estimates have run below the real bill (see 10k in the plan).** Reconcile the ledger against the billing page.

Quick start, from a session whose environment has the key set:
```
python harness.py --pages PAGES --out RUN --models gemini-4-argon,gemini-3.7-flash --runs 2 --language Assamese --budget-inr 150
python marksheet.py --page-id A01 --group A --image PAGES/A01.png --a RUN/A01/gemini-4-argon/run1.txt --a-name argon \
                    --b RUN/A01/gemini-3.7-flash/run1.txt --b-name flash37 --out A01_marksheet.html
```
Pages are named by ID only (`A01.png` = group A, page 1). `.gitignore` in this folder blocks images, PDFs, run folders, ledgers, marking sheets and marks files, but **check `git status` before every commit**: a marking sheet contains the page and its text.

Smoke test on 2026-10-27, on a public Hindi clipping with the free key: one real call (time, tokens and cost recorded), a second invocation skipped it, the checker and marking sheet ran on the result, and the sheet loaded in a real browser with no script errors.

## Running a new test (ready from 2026-10-28)

Put the pages in a folder OUTSIDE the repository (page images, PDFs, outputs and reports are case data). Then:

```
export GEMINI_API_KEY=...             # already in the environment's secrets; never paste it in chat
python ocr_tests/pipeline.py --input /path/to/pages --out /path/to/run --language Assamese --page-type typed --budget-inr 40 --pdf
```

- Files are recognised by their **content**, not their name: a PDF saved as `.php` (a download link that serves a PDF) is read as a PDF; anything that is not a PDF or a PNG, JPEG or WebP image is skipped with a message (before 2026-10-28 such a file was silently ignored).
- `--page-type typed` or `handwritten` is required (a handwritten page is never green). For a mix, give `--types types.json` with `{"page id": "handwritten"}`; PDF pages are named `<file>_p<N>`.
- Before spending anything: `python ocr_tests/pipeline.py --selftest` (fake callers, no cost), and `python ocr_tests/checker.py --selftest`, `redundancy.py --selftest`, `report.py --selftest`, `pdf_triage.py --selftest`, `harness.py --selftest`.
- Cost: about Rs 1 to 1.5 per read logged (2 reads per page, 3 where flagged; a text-layer PDF page costs two small text calls, under Rs 1). The real bill has run 1.5 to 2 times the logged figure; keep `--budget-inr` and check the AI Studio balance first. A stopped run is resumed by repeating the command.
- `--pdf-reader vision` uses Cloud Vision for the PDF text-layer match (about 98% against about 83% with the default Tesseract on the one good file) but sends each PDF page to Google; it needs `GOOGLE_CLOUD_API_KEY`.
- `--pdf` needs Node and Playwright; without them the HTML reports are still written.
- Outputs in the run folder: `report/<page>.html` (and `.pdf`), `marksheets/<page>_marksheet.html`, `checks/<page>.json`, `summary.json` (red first), `ledger.jsonl`.
- Marking: open each marking sheet, type what the page really says for every check-list row, log every error, press Download CSV, send the CSVs back. Nothing saves by itself.
- Names a reviewer has confirmed can be fed back with `--known known_names.json` (a JSON list; `redundancy.known_names_from_csv` builds it from downloaded CSVs). The list is case data.
- Rehearsed end to end on 2026-10-28 on one image page and one text-layer PDF (about Rs 4.4 logged).
