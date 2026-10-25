# OCR bake-off scripts (no case data in this folder)

Support for `OCR_TRANSLATION_TEST_PLAN.md`. Scripts here take the document and the reference terms on the command
line. **Never commit a real case document, a case number, a name or a reference file to this public repository.**

## Sarvam run (first candidate, started 2026-10-25)
Needs, in a fresh session: `SARVAM_API_KEY` set as an environment variable of the cloud environment, `api.sarvam.ai`
in the environment's allowed domains, the PDF uploaded again, and a private `refs.json` (page -> terms read by eye).
The SDK confirms `as-IN` (Assamese), `kn-IN` and `en-IN` as document-digitise language codes; one language per job,
at most 10 pages per PDF. Listed price: Rs 0.5 per page for digitisation (docs page; a marketing page says Rs 1.5), so
the 14-page file in three jobs (28 pages) is a few tens of rupees. Digitise results return page text in md or html;
no per-block confidence is documented for digitise (only for extract), so check the saved JSON for one.
`python sarvam_run.py --selftest` checks the wiring without calling Sarvam.
