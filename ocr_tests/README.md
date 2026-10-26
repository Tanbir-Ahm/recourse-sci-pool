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
