# The Judgments page label (2026-11-16)

Owner: "Fix the Judgments page label". Recourse branch `register-hooks-and-overlay`, NOT on `main`. Nothing deployed.

## The fault
The Judgments page card for a Supreme Court title-list judgment always said "Supreme Court index (title and citation only)". The title list holds only title and citation, but 8,093 of its 38,026 judgments are ALSO documents of the wide full-text search index, and so are all 3,025 court-linked "extras" and all 7,553 Gauhati judgments. A tester read the label as "no readable text" and a comparison article blamed a coverage gap for Gunmala, S.M.S. Pharmaceuticals, Bridgestone, HDFC Bank (2025 INSC 759) and Kamalkishor; all five are in both the pinned (production) and the newer index. The omission in that answer was a retrieval miss, not title-only coverage.

## The fix
- Data (`build_case_links.py`, new `wide_flags` and `annotate`, no download needed): `case_pdf_links.json.gz` now carries `wide_index` {both, newer, commits} for title rows and a `wide` field on every extras entry. A title row is "in an index" when it was tied to that index's court address, or its bucket PDF is the very file a bucket-linked row of that index's names table points at. A judgment only the archive list tied is never counted. Rebuild with `python build_case_links.py --annotate case_pdf_links.json.gz --names-table <newer names table> --names-table-pinned <pinned names table>` whenever either index changes.
- Code: `case_links.wide_status(case_id)` ('both' | 'newer' | None; None with `CASE_LINKS=off` or no flags); `search_service._index_tier` and three card builders.
- Wording: both indexes -> "Supreme Court index (title and citation here; the full text is in the wider search)"; only the newer index -> "... may be in the wider search" (the wider search may run on the older index); Gauhati High Court -> "Gauhati High Court list (title, case number and link here; the full text may be in the wider search)"; a judgment not known to be in the wide index keeps "Supreme Court index (title and citation only)". The web page shows the label as the API sends it: `recourse-web` needed no change.

## Numbers
Title list 38,026 rows: 8,091 in both indexes, 2 only in the newer, 29,933 not known to be in the wide index (mostly civil and other judgments the criminal-law index never embedded; they keep the old words, which is true for them). Extras 3,025: 1,900 in both, 1,125 only in the newer. Gauhati: all 7,553 get the "may be" wording. The five cases of the article and Arnesh Kumar: Gunmala, both S.M.S. judgments, Bridgestone, HDFC Bank 2025 and Kamalkishor say "the full text is in the wider search"; the Ayodhya judgment (M. Siddiq, 2019 INSC 1231; a civil title suit) keeps "title and citation only"; a library judgment is still "Reviewed library". Checked on the real title index through `search_service.search`.

## Limits
- The flags rest on the names table, which is one row per judgment of the search index; I did not fetch passages from the index here (it is not in this sandbox).
- The match of a title row to an index document uses the same guarded passes as the court-address links (hold-out estimate about 0.1% wrong for list-matched addresses); the bucket-file test is exact.
- The label says the text is in the wider search; it does not say the wider search will bring that judgment up for a question (the article's real fault was that it did not).
- The file is production data in the Recourse repository: it reaches production only through the owner's own pull request.

Tests: `test_wide_labels.py` (23 checks; the builder on made-up rows, the round trip, the loader, the labels on real searches); `test_hc_links.py` expectation updated; suite 154 of 154.
