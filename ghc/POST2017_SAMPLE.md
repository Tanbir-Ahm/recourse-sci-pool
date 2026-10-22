# Guwahati High Court, open bucket, decided 2018 to 2026: how many judgments? (sample of 300, 2026-10-22)

The bucket holds **211,222 documents** for 2018 to 2026 (counted from its own listing; by year: 2018 22,842; 2019 24,683; 2020 15,840; 2021 19,707; 2022 26,000; 2023 27,799; 2024 27,102; 2025 26,470; 2026 20,779). It does not say which are judgments. A random sample of 300 (seed 20261022, drawn from all 211,222) was downloaded from the open bucket (no court site), read, and classified; per-document facts are in `post2017_sample_300.csv` (no text kept). Fetching was 2 at a time with a pause; nothing else was downloaded; the post-2017 batch is still NOT approved.

The post-2017 template puts a long cause title (addresses, advocates) before the order, so the document length overstates the content; "body" below is the text from the "BEFORE ... HON'BLE" line on.

| Definition | In sample | Estimate for all 211,222 | 95% range (sampling only) | of which wanted case types |
|---|---|---|---|---|
| The court's heading says JUDGMENT (or CAV) | 50 | about 35,200 | 26,300 to 44,100 | about 24,600 |
| Body of 5,000+ characters (any heading) | 62 | about 43,700 | 34,000 to 53,300 | about 35,200 |
| Heading says JUDGMENT, or body 5,000+ | 85 | about 59,800 | 49,100 to 70,600 | about 41,500 |

Wanted case types = not AB, BA, bail, IA or MC (143 of the 300). Everything else is orders: 216 of 300 documents carry an ORDER heading, 76 of 300 have a body under 1,000 characters.

Reading the result: the narrow figure (about 35,000) is what the court itself calls a judgment; the broad figure (about 60,000) adds long reasoned orders. Judgments in the court's wording are 17% of the documents; judgments in wanted case types roughly 12%. The sample is small: the ranges are wide and the criminal-law share (8 of the 35 labelled judgments in wanted types, about 5,600 judgments, range very wide) is only a guess. Labelled JUDGMENT documents have a median body of 6,480 characters; a few labelled ones are very short (minimum 326), so the label is not a perfect test.
