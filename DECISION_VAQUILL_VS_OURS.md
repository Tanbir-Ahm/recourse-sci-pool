# Decision record: our way or the Vaquill way (owner asked 2026-10-10; read this before any future test or ingestion work on court data)

Evidence: `review_results/2026-10-10_vaquill_comparison/` (README section 10, `with_the_host_open/`), commit `bc6f8c5`. Tags: [Certain] counted, [Likely] inferred, [Guessing].

## Verdict (blunt)
**Our way is better. Keep building on the court's own documents (old crawl + the open AWS bucket), cleaned and cut into passages by us. Do not use Vaquill's data, chunks or vectors as a foundation.** Its dataset is a convenience product with real quality problems, and a legal tool lives or dies on accurate, current, quotable text. **The one exception: its embedding model (voyage-4-large) did better than ours (voyage-law-2) in a small test, so test that model on OUR clean passages.** That is the only thing worth taking from Vaquill.

## What the results mean, in plain terms
1. **It is a copy of a copy.** Court -> AWS bucket -> Vaquill. Every Supreme Court judgment it has is already in the bucket we hold; it adds nothing and loses things (2009 almost absent, half of 2025, nothing in 2026). [Certain]
2. **Its text is dirtier than ours.** Two thirds of the file is Hindi/Punjabi translations we do not need. In the English part, 3.9% of words are not real words (ours 1.6%). For judgments from 2018 on, 46 of 69 have words stuck together ("highcourt", "writpetition") and margin letters fused into words ("SectionD35"); ours have none. That breaks keyword search and exact quoting. [Certain]
3. **Its chunks are the wrong shape for us.** About 3,700 characters each (ours about 1,100), a header and tags on every chunk, margin-letter lines in 77.5% of them, 47% end mid-sentence, no paragraph numbers, section labels that say nothing (97% "body/paragraph/section"). We cite by paragraph; they cannot. [Certain]
4. **Its vectors are good but unusable for us.** Made with voyage-4-large from the dirty text (cosine 0.9995 on a re-check). Our voyage-law-2 scores 0.03 against them, so they cannot be mixed with our index. The set is also inconsistent: 4,871 duplicate vectors, 734 judgments in the file have no vectors. Its citation fields (cases cited, acts, cited-by) are empty and its "treatment" tags are word-spotting, not verdicts. [Certain]
5. **It is stale where it matters.** Newest decision 6 Nov 2025; it has 9% of the last twelve months' judgments (35 of 378). The bucket has 249 newer ones and refreshes about every two weeks. Vaquill's own README says its release "goes stale". [Certain]
6. **The model result, honestly.** Meaning-search only, 13 answerable tuning questions, same judgments: named authority in the top 3 for 9 (Vaquill chunks + voyage-4-large) against 5 (ours). Same text, two models: 9 against 7. Six or seven questions better, three worse, rest tied: suggestive, NOT proven. Our full search (keywords, sections, re-ranker) already gets 10 of 14 into the top 5, so this tests one ingredient only. [Likely]

## What is wrong with our way (do not forget)
- Our crawl ends 4 May 2017; newer judgments depend on a third party's bucket (Dattam Labs). If it stops, we need a direct fetch from the court, which is untested (`digiscr.sci.gov.in` is blocked in the sandbox; the court site's terms are unchecked).
- Both we and the bucket hold only about 60% of what Indian Kanoon lists for 1968-1999.
- Our embedding model is older than the one Vaquill used.

## For future cases / testing
- Do not re-test "use Vaquill's data" unless the evidence changes (a new snapshot with fresh 2026 judgments, clean text, no duplicates). If it does, rerun `with_the_host_open/RUN.md`.
- Next test if the owner agrees (about $0.30): our clean passages for the same pools embedded with voyage-4-large, against voyage-law-2. If it holds, re-embed the index (about $8 if the listed $0.12 per million tokens is right; third-party prices, not checked with Voyage). voyage-4-lite ($0.02) can embed queries because the series shares one vector space.
- Keep: monthly bucket refresh as the main route for new judgments; a direct court fetch only as a backup, after the site's terms are checked and the host is allowed.
- Spend so far on this: about $0.13 of Voyage credit (balance should read about $9.39 by estimate). Keep at least $8 for the live site.
- Corrections to earlier statements are in README section 10.1 (source_url 83.3% was legislation; the yearly table counts vectors by law-report year; `text_original` equals `text`; tags/headers are in the English text; Vaquill's text is noisier, not equal; the model is voyage-4-large).
