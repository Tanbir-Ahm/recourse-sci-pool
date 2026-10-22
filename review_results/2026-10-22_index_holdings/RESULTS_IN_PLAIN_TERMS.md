# What the big search index holds, and is everything embedded? (2026-10-22)

**Short answer: no. The index looked at 55,140 judgments but embedded only 12,717, on purpose: it embeds only criminal-law judgments of adequate length, and not copies.** An earlier answer of mine called the index "48,595 judgments"; that counted judgments *looked at*, not judgments embedded. This note replaces it.

**The index is changing as this is written.** The figures are a snapshot of branch `claude/sci-index` at commit `5d8837e` (15:35 UTC); another session is embedding the Guwahati open-bucket text right now. Tags: **[Certain]** = counted from the index's own files (`numbers.json` here; `review_tools/experiments/index_holdings_2026-10-22.py`).

## How many [Certain]
| | Looked at | **Embedded** (searchable) | Passages |
|---|---|---|---|
| **Supreme Court** | 52,843 | **11,817** | 266,183 |
| the crawl (to 4 May 2017) | 36,928 | 8,101 | 153,383 |
| the open bucket | 12,168 | 2,404 | 82,772 |
| the court's newer archive | 3,747 | 1,312 | 30,028 |
| **Gauhati High Court** (so far) | 2,297 | **900** | 18,226 |
| the court's own files | 776 | 759 | 15,241 |
| the open-bucket text (7 of 34 blocks done) | 1,521 | 141 | 2,985 |
| **Both courts** | 55,140 | **12,717** | 284,409 |

- **When the Guwahati run finishes** (the other session's own no-spend preparation, `new_archive/SET_C_REJOIN_REPORT.md` on branch `claude/happy-feynman-3q8xq2`): that set (8,271 documents in 34 blocks) should end with about 980 judgments and 24,511 passages embedded (141 and 2,985 so far), so **about 1,739 Guwahati judgments and 39,752 passages in all**, and about 305,900 passages in the whole index. **[Likely]**: an estimate from that preparation, not a measurement.
- **Copies:** about 125 to 130 of the 11,817 Supreme Court judgments are second copies of another embedded judgment (the text store counts 11,659 distinct plus 29 it cannot place; the unapplied dedupe plan lists 131 groups).

## Why not everything is embedded [Certain]
- **Supreme Court, 41,026 looked at and not embedded:** 35,713 are not criminal law; 3,084 are bucket judgments the crawl already holds; 1,426 are too short; 803 are copies (664 exact, 139 near).
- **Guwahati so far:** 1,397 of the 2,297 looked at are not criminal law. A further 3,081 Guwahati documents we hold (orders, unreasoned documents, excluded types) are not sent to the index at all.
- **Never sent:** 6,662 of the newer archive's 10,409 texts: the archive says the open bucket holds them, and the bucket's copy had already been through the index.
- **Held but not embedded in total:** of the 12,128 Guwahati documents we hold, 9,047 are being put through the tests (776 + 8,271) and about 1,739 will be embedded.

## Is what is embedded complete? [Certain]
Yes. Every embedded judgment's passages are there: **284,409 passages = 284,409 vectors = the ledger's count = the document records' count**, in every block, none unreadable (no non-finite number). 8,300 fragments of embedded judgments (page headers and similar) were deliberately left out as noise.

## What nobody should read into this
Embedded does not mean the right judgments are searchable for a lawyer's question. Civil and service judgments (about 2 in 3 of what we hold) are not searchable by design, which is a decision the owner may want to revisit. Quality has not been measured on this index (`FOLLOW_UPS.md` item 1x).
