# Quote provenance at index time (prototype, 2026-10-26)

Owner's go, 2026-10-26: "Yes, build a and b and prototype of quote provenance at index time that would also fix the 'paragraph 8' display, which a prompt can't." This file is about the third part. (a) and (b) are in `../2026-10-26_followup_merge_dedupe/RESULTS.md`.

Nothing here was tried with the answer model (the sandbox has no Anthropic key). Every figure below is a count of words and numbers in the index, or a reading by Claude, who is not a lawyer.

## 1. What was wrong

The index cuts a judgment into passages at every line that starts "N. " and calls N the passage's paragraph. Read in the real index (document 38684, Sadhwi Pragyna Singh Thakur v. State of Maharashtra, 2011) the judgment's own paragraphs run 24, 25, 26, and between 25 and 26 sit passages numbered **3, 6, 8, 830**. Paragraph 25 of the judgment says "In Saptawna vs. The State of Assam AIR (1971) SC 813, this Court has observed as under in paras 2 and 3 of the reported decision : " and then quotes that decision (which quotes V.L. Rohlua (1970) in turn). The quoted text keeps the quoted decisions' own numbers; "830" is "(1966) 3 SCR / 830." wrapped onto a new line; a "4." in paragraph 21 is "SCC 718 para / 4." wrapped. The owner's staging answer credited Sadhwi with "paragraph 8": a paragraph of an older decision, quoted inside Sadhwi's paragraph 25. [Certain: shown by the index rows in `sadhwi_passages.json`.]

A prompt cannot fix that: the number printed beside the passage is wrong, and nothing in the passage tells the model whose words they are.

## 2. What was built (all behind switches that are off until the owner sets them)

| Piece | Where | Switch | Default |
|---|---|---|---|
| `sci_quotes.py`: finds passages whose number is not the judgment's own, from the numbering and the words that end the paragraph before; no model, no network, no re-embedding | research repo | none (a library) | |
| The service adds `"quote": {within, kind, intro?, block, ends_at?}` to such results | `sci_search_service.py` | **`SCI_QUOTES=on`** on the sci-search service | **off** |
| Head of the passage says "inside paragraph 25", a Note by code under it, one instruction sentence; the sources box, table, export and search page show "paragraph 25" and a reading note | Recourse `quote_notes.py`, `sci_search_tier.py`, `passage_notes.py` (kind "quoted"), `search_service.py` | none: a result without `quote` is worded byte for byte as before | |
| Search page shows the reading note | recourse-web `SearchResults.tsx`, `types.ts` | none (field optional) | |

So production, and staging, change only when the owner sets `SCI_QUOTES=on` on a sci-search service. Way back: delete the variable and redeploy that service.

How the detector decides (`sci_quotes.py`):
1. In each judgment with 6 to 2,500 numbered passages, the numbers that form the longest strictly increasing run in file order are the judgment's own (pieces "7/1", "7/2" share a number). Ties: smaller total steps; then the later passage (a quotation comes before the own paragraph that follows it).
2. A block of passages off that run, with the own run picking up again within 3 numbers right after it, sits inside the own paragraph before it. Blocks at the start or end of a judgment (a caption list, a second opinion that restarts the numbering, an annexure) are not touched.
3. "introduced" if the own paragraph before the block ends with a colon or an opening mark, or a quotation mark opened in it is closed in the block, or the block's first passage opens with a quotation mark. The judgment's own words that end there are copied (up to 320 characters) as `intro`. Otherwise "off_sequence".
4. **When in doubt, not flagged:** an uncued passage whose number fits the slot between the own paragraph before and the own paragraph after (a judgment that numbers two paragraphs "46") is left alone.
5. "ends_at": a joined passage ("8-24") that starts off the run and ends on it.

Honest wording: code can say that the number is not the judgment's own and where the passage sits. It cannot say the words are a quotation. "introduced" means "probably", because a colon also introduces a list; the Note by code says so, and for "off_sequence" it lists what the passage can be (a quotation, a statute section, a footnote, a wrapped citation, a list) and does not tell the model it is a quotation.

## 3. Measured

**On the whole newer index, as the service loads it** (19,255 judgments, 420,893 passages; `demo_end_to_end_output.txt`): 12,659 judgments have enough numbered passages to be read; **4,550 of them (36%) have at least one flagged block**; **21,524 passages flagged (5.1% of all passages)** in 8,792 blocks; 14,784 "introduced", 6,740 "off_sequence", 1,140 joined with an own paragraph. Reading all of it takes about 5.5 seconds at start-up. [Certain: counts.]

**In what the real recipe returns** (the saved 2026-10-26 comparison: 12 landmark questions and 9 spot questions, top 10 each; `in_results.json`): of 169 returned passages that carry a number, 14 (8%) are flagged for certain and 25 (15%) if a passage sharing its label with a flagged one is counted. So roughly one returned passage in eight to one in seven carries a number that is not the judgment's own. [Certain for the counts; the match is by document and label because the saved rows hold no passage id.]

**Precision, read by Claude on a fresh random sample of 40 flagged blocks drawn from the final code** (`sample_reading.json`, one passage per block, each read once from the end of the paragraph before, the passage and the next own passage): in **38 of 40 (95%)** the number belongs to something set out inside the judgment and is not a paragraph of it: 33 a quoted decision, a lower court's order or findings, a statute section or rule, a report, a letter, testimony or an agreement; 5 a list item or a number wrapped onto a new line. **1 of 40 looks like a false flag** (a judgment's own paragraph 17 that sits after 18 in the file) and **1 could not be told** (numbers repeated in a messy judgment). Of the 29 "introduced" blocks in the sample, 27 were a quoted decision or document, 1 a list, 1 the false flag; of the 11 "off_sequence", 6 were quotations without an introduction, 4 lists or wrapped numbers, 1 undecidable. [Likely: the reader is the person who wrote the rules, 40 is few, the interval for 38 of 40 is about 83% to 99%, and a lawyer has not read any of it.] An earlier sample of 80 read against earlier versions of the rules found the same kind of false flag (a judgment that repeats a number), which is what rule 4 above removes; those 80 are not counted here because the rules changed afterwards.

**The case that started this** (`demo_end_to_end_output.txt`; the real index, the real recipe with Voyage, no answer model): for "Armed Forces Special Powers Act and the arrest of a civilian" the first result is Sadhwi's passage numbered 8. With `SCI_QUOTES=on` the service marks it `within 25, introduced`, with the intro "In Saptawna vs. The State of Assam AIR (1971) SC 813, this Court has observed as under in paras 2 and 3 of the reported decision :". Through Recourse's `feed_block` the prompt head reads "...Sadhwi Pragyna Singh Thakur v. State of Maharashtra (2011-09-23), Supreme Court of India, **inside paragraph 25**", the Note by code under the passage names the number it starts with ("8.") and the paragraph it sits inside and gives the judgment's own words; the case the page lists has `paragraph "25"` and a reading note. The sources box, the table and the export read these fields (tests). The other 9 results in that list are untouched (none is flagged).

## 4. What it does not do

- **Quoted text with no paragraph numbers in it** is not numbered off at all, so nothing is flagged. Its passage carries the host paragraph's right number, but the words are still the quoted decision's. That is probably the larger share of quoting, and only the existing prompt rule (FOLLOW_UPS 2cj) and the model's care deal with it. [Likely]
- A quoted number that falls inside the judgment's own run (a quoted "8" between own 7 and own 8) is resolved by taking the later passage as the own, so the quote is missed or, rarely, an own paragraph is flagged (the 1 of 40).
- It does not name the quoted decision: the judgment's own words are given and the model reads the name from them. A decision named in those words becomes a case the answer names that was not fed as a wider-search case; the existing citation check sees the name in the material.
- The upstream cause is not repaired: the chunker still cuts at "N. " and the 420,893 vectors were not touched. A real repair (keep a quoted block inside its host paragraph, re-embed those passages) is a re-index; this prototype is the cheap, reversible step.
- Nothing was tried with the answer model. Whether the note changes what the model writes is unknown until the owner's staging test (`DEPLOY_STAGING.md` Part 4aa).
- Not a lawyer's reading, and no hallucination rate has been measured.

## 5. Files

`sci_quotes.py`, `test_sci_quotes.py` (45 checks, including the real Sadhwi rows in `sadhwi_passages.json`), `measure_in_results.py` / `in_results.json`, `demo_end_to_end.py` / `demo_end_to_end_output.txt` / `demo_end_to_end.json`, `sample_reading.json`. Recourse: `quote_notes.py`, `test_quote_notes.py` (55 checks). recourse-web: `tests/quote_note.test.tsx`.

Reproduce: `python3 sci_quotes.py report INDEX_DIR --samples 20` (counts and samples); `python3 review_results/2026-10-26_quote_provenance/measure_in_results.py INDEX_DIR`.
