# Adding the court's newer archive to the text store, in plain terms (2026-10-22)

**The store now holds 48,647 distinct Supreme Court judgments, not the 48,933 I told you earlier, and the 3,461 newest ones are the only part that is genuinely new.** My first estimate counted copies as new judgments. Tags: **[Certain]** = measured from the files; **[Likely]** = strong inference.

## What was done
- The text store (`corpus.sqlite`, on this machine only, not in git) is built from three folders of data. The third is new: `../recourse-sci-newer-data`, the branch `claude/sci-court-newer` (the court's own newer archive, 10,409 texts, 1 May 2017 to 16 October 2026).
- All 10,409 texts are in the store. Each is marked as one of:

| What the build made of it | Texts |
|---|---|
| A new judgment the bucket does not hold | **3,461** (6 of them uncertain, flagged) |
| A second copy of a bucket text (kept, not counted) | 6,944 |
| A second copy of another text in the same archive (several diary numbers on one judgment) | 4 |

- Count by source, with copies left out: crawl 36,102 + bucket-only 9,084 + newer-archive-only 3,461 = **48,647**.
- New judgments by year: 2017 204, 2018 369, 2019 323, 2020 148, 2021 211, 2022 301, 2023 226, 2024 260, **2025 567, 2026 852**. [Certain]
- **Nothing that was already in the store changed.** The 46,012 old rows, their text lengths and their 276,803 citation entries are identical; the new texts were added after them. [Certain]
- The citation index (`corpus.sqlite.cites`) was rebuilt: 352,094 citation entries.

## Two things the checks found, and what I did about them
1. **The archive's own "not in the bucket" marker was wrong for hundreds of texts [Certain].** It compares the exact date and the exact title. The bucket often dates the same judgment a day earlier, or spells a name differently ("MOHANLAL", "KERELA"), so the marker said "not held" for judgments we already have. I compared the words: if a text shares at least half its 8-word runs with a bucket text dated within 3 days, it is a second copy (a third of its runs, if the title also agrees). That found 289 more copies, which is why 3,461 is lower than the 3,749 of the first build. Typeset bucket text has glued and misread words, so a few real copies sharing less than 20% may remain.
2. **Bench sizes were misread [Certain].** The pattern that reads a law-report's list of judges read phrases such as "one of us (Aftab Alam" in 12 newer texts as a complete bench. Newer texts now get only the count of signature lines, which is always treated as a lower bound; 47 texts have no bench size.

## What it did to the currency cards (a dry run, nothing saved)
I ran the 76 cards on the old store and on the new one, into scratch folders. **The committed cards are untouched.**
- **Before the second fix, two cards got worse:** "Mohan Lal v State of Punjab" went from a warning (ADVERSE_SIGNAL) to "ambiguous match", and "Vihaan Kumar v State of Haryana" to "ambiguous match". Both were duplicates the first build had missed (the bucket spells "MOHANLAL"; it dates Vihaan Kumar a day earlier). With the final store both are back to what they were.
- **Final result: 75 of 76 cards are identical to the committed ones, warnings included (2 ADVERSE_SIGNAL, unchanged).**
- **One status changed:** "S. Vanitha v Deputy Commissioner, Bengaluru Urban District" goes from INSUFFICIENT to NO_ADVERSE_FOUND, because at least three later judgments we now hold cite it. That is the quiet status, and it means "no warning found in what we hold", never "good law".
- **Four library cases are now found in our collection** (they were not before): Lokesh B.H v State of Karnataka (3 Aug 2026), Prakash Chimanlal Sheth v Jagruti Keyur Rajpopat (25 Jul 2025), Satender Kumar Antil v CBI (15 Jan 2026) and Usha Chakraborty v State of West Bengal (30 Jan 2023). Their statuses did not change.

## What is NOT done
- **The cards are not regenerated.** A person reviews cards, so I did not overwrite them. If you want them regenerated from the new store, say so; the dry run shows five changes to look at.
- **The search index (`claude/sci-index`) does not hold the newer archive.** The pilot's search, and the figures about it, are unchanged. Adding it would mean embedding about 3,500 judgments, which spends Voyage credit; I have not done that and will not without your say-so.
- **Six judgments are flagged uncertain** (`maybe_dup_of`): each has a bucket text of nearly the same date and title that shares only part of its words (for example *In re: Right to Privacy of Adolescents*, *Operation Asha v Shelly Batra*, *GMR Warora Energy v CERC*). They are counted as judgments; at most 6 of the 3,461 are copies. They are listed in `numbers.json`.
- **This is a text store, not a promise that the texts are right.** The newer archive's text is raw: it still carries the court's "digitally signed" blocks and page lines, and nobody has compared it with the PDFs.
- **Older years are still thin** (about 61 to 64% of Indian Kanoon's yearly counts for 1968 to 2004). Nothing here changes that.

## Where things are
- Code: `goodlaw/corpus.py` (`read_newer`, `link_newer`, `match_by_text`, `add_newer`); tests `test_goodlaw_corpus.py` (the newer-archive section, mutation-checked).
- Rebuild: `python sci_goodlaw.py build --crawl-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --newer-dir ../recourse-sci-newer-data --corpus corpus.sqlite` (about 15 minutes, 2.3 GB). A build deletes the file it writes to, so build to a new name and swap.
- Numbers: `numbers.json` here (made by `review_tools/experiments/newer_archive_store_2026-10-22.py --new <store> --old <old store> --out ...`).
- The previous store is kept on this machine as `corpus.sqlite.before_newer` (and `.cites`), git-ignored, so the change can be undone. It will be lost with this session's container.
