# review_data: PRIVATE answer key

`pool_all.json` is the pool of passages behind the review packs. For each of the 12 test questions it holds every passage that was shown to reviewers, with the number reviewers see, the judgment it came from, and **which search version showed it** (`variants`: version name to rank). It also holds the expected case per question (`landmark_doc`) and, for the question-rewrite version, the rewritten question I wrote (`rewrite`).

That last part is what makes it an answer key: a reviewer who saw it could be swayed by which search "should" win. **Never send this file, or anything built from its `variants`, to reviewers.** The packs and sheets that go to reviewers are built from it by `review_tools/` and contain none of it (a test checks this).

This repository is private. If it is ever made public, move this folder first.

Version notes:
- Rows without `topup` are the first batch (175 passages, numbers 1 to 12-16 per question), built 2026-10-02 from the top 10 passages of six search versions per question, de-duplicated by identical text, capped at 16, then shuffled with a fixed seed.
- Rows with `topup: true` are the top-up batch (24 passages) that only the site's own search method showed when run on the wide index; their numbers continue after the first batch's.
- Tags `S site shown` and `M mine top 6` say whether the site's method (run unmodified on the wide index, statute lookups off) or my pipeline's top 6 showed a passage. They are tags on what was shown, not rankings.
