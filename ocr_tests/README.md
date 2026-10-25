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
