# What the big search index holds, and is everything embedded? (2026-10-22)

**Short answer: no. The index looked at 61,890 judgments and embedded 13,556, on purpose: it embeds only judgments that pass a criminal-law wording test, of adequate length, and not copies.** An earlier answer of mine called the index "48,595 judgments"; that counted judgments *looked at*, not embedded. This note replaces it.

Final snapshot: branch `claude/sci-index` at commit `bfbfd05`, 15:49 UTC, **after** the Guwahati open-bucket run finished (its last block and shift log were committed at 15:48:33 UTC by another session; I did not run it). Tags: **[Certain]** = counted from the index's own files (`numbers.json`, `ghc_case_types.json` here; scripts `index_holdings_2026-10-22.py`, `ghc_case_types_2026-10-22.py` in `review_tools/experiments/`).

## How many [Certain]
| | Looked at | **Embedded** (searchable) | Passages |
|---|---|---|---|
| **Supreme Court** | 52,843 | **11,817** | 266,183 |
| the crawl (to 4 May 2017) | 36,928 | 8,101 | 153,383 |
| the open bucket | 12,168 | 2,404 | 82,772 |
| the court's newer archive | 3,747 | 1,312 | 30,028 |
| **Gauhati High Court** | 9,047 | **1,739** | 39,752 |
| the court's own files | 776 | 759 | 15,241 |
| the open-bucket text | 8,271 | 980 | 24,511 |
| **Both courts** | 61,890 | **13,556** | **305,935** |

- 82,871,528 tokens have been spent on the index in all, against the ceiling of 85,000,000: **2,128,472 tokens are left (about $0.26 at the listed price)**, so any further embedding needs the ceiling raised.
- **Copies:** about 125 to 130 of the 11,817 Supreme Court judgments are second copies of another embedded judgment (the text store counts 11,659 distinct plus 29 it cannot place; the unapplied dedupe plan lists 131 groups).

## Why not everything is embedded [Certain]
- **Supreme Court, 41,026 looked at and not embedded:** 35,713 are not criminal law; 3,084 are bucket judgments the crawl already holds; 1,426 are too short; 803 are copies (664 exact, 139 near).
- **Guwahati, 7,308 looked at and not embedded:** all failed the criminal-law test. A further 3,081 Guwahati documents we hold (orders, unreasoned documents, excluded types) were never sent.
- **Never sent:** 6,662 of the newer archive's 10,409 texts: the archive says the open bucket holds them, and the bucket's copy had already been through the index.

## Is what is embedded complete? [Certain]
Yes. **305,935 passages = 305,935 vectors = the ledger's count = the document records' count**, in every block, none unreadable (no non-finite number). About 8,300 fragments of embedded judgments (page headers and similar) were deliberately left out as noise.

## Were the embedded Guwahati judgments all criminal? [Certain for case numbers; the rest is not measured]
**Not all: 1,649 of 1,739 (94.8%) have a criminal case number; 90 (5.2%) do not.** The index's test is a wording test on the text, not the court's case type; this check uses the case type the court itself gave (the case number in the index record).
- **The court's own files: all 759 are criminal case types** (Crl.A(J), Crl.Rev.P., Crl.Pet., W.P.(Crl.) and similar). They were chosen from the court's list of criminal-subject files.
- **The open-bucket text: 890 of 980 are criminal case types; 90 are not:** 74 civil writ petitions WP(C), 9 writ appeals, 2 civil revision petitions, 2 PILs, 2 regular second appeals, 1 matrimonial appeal. They carry 1,564 of the 39,752 Guwahati passages (3.9%).
- **How they got in:** 87 of the 90 passed on the density test (at least 10 criminal-law terms per 10,000 characters; median 14.8, highest 50.5), so many are probably civil or writ cases about police, detention or prison matters, which do contain criminal law; I have not read them. 3 passed on a criminal-looking heading while having almost no criminal wording (density 0.8, 1.1 and 8.5): a matrimonial appeal, a civil revision and a civil writ. Those three are probably wrong.
- **The other way round:** 26 judgments with criminal case types were *not* embedded (15 of the court's own files, 11 of the open-bucket text), so the test caught 98.4% of the criminal-type judgments it saw.
- A case type is the court's label, not a reading of the judgment.

## What nobody should read into this
Embedded does not mean the right judgments are searchable for a lawyer's question. Civil and service judgments (about 2 in 3 of the Supreme Court ones we hold) are not searchable by design, which is a decision the owner may want to revisit. Quality has not been measured on this index (`FOLLOW_UPS.md` item 1x).
