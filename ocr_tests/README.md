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
| `checker.py` | Compares two readings of one page. Every disagreement (a number, date, amount, name, land unit, or a whole line) comes first. Every date, amount, number, unit, section number and name the readers **agree** on is listed too, marked "still confirm", because agreement is not correctness. It never marks anything correct. With `--page typed|scan|handwritten` it runs the whole page check of plan section 11: letter agreement between the two argon runs and against Cloud Vision, dropped or cut-off readings, English sentences that changed between runs, and a green / amber / red light with the reasons. **Written 2026-10-27 and not yet run on any page** (not even its selftest); the cut-offs are a first guess from Assamese pages only. |
| `marksheet.py` | Prints one self-contained HTML marking sheet per page: the page image beside the check list, the differing lines, both English drafts, and the plan's section 8 error table (type, severity, warned?) with Copy-as-CSV. Nothing is loaded from the internet, and reader text is escaped. |

`models.json` holds the model list, the key each one uses (read from an environment variable; keys are never printed or pasted into chat), and the prices. **The prices are third-party and unverified, and the estimates have run below the real bill (see 10k in the plan).** Reconcile the ledger against the billing page.

Quick start, from a session whose environment has the key set:
```
python harness.py --pages PAGES --out RUN --models gemini-4-argon,gemini-3.7-flash --runs 2 --language Assamese --budget-inr 150
python marksheet.py --page-id A01 --group A --image PAGES/A01.png --a RUN/A01/gemini-4-argon/run1.txt --a-name argon \
                    --b RUN/A01/gemini-3.7-flash/run1.txt --b-name flash37 --out A01_marksheet.html
```
Pages are named by ID only (`A01.png` = group A, page 1). `.gitignore` in this folder blocks images, PDFs, run folders, ledgers, marking sheets and marks files, but **check `git status` before every commit**: a marking sheet contains the page and its text.

Smoke test on 2026-10-27, on a public Hindi clipping with the free key: one real call (time, tokens and cost recorded), a second invocation skipped it, the checker and marking sheet ran on the result, and the sheet loaded in a real browser with no script errors.
