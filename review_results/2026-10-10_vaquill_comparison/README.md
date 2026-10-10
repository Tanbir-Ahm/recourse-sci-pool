# Vaquill's open-india-law against our sources (2026-10-10; PRIVATE; read-only on the Recourse checkout; no search, no embedding, no spend)

Question (owner, 2026-10-10): the Recourse repository carries a Vaquill database that "claims to have every judgment from all courts"; compare it critically with what we scraped from api.sci.gov.in and Indian Kanoon, and say whether to use it for embedding the judgments.

Tags: [Certain] = counted or quoted from a file in this folder or in the Recourse checkout; [Likely] = strong inference; [Guessing] = filling a gap. Recourse checkout read: `tanbir-ahm/recourse` at `721e0631` (29 Sep 2026). Upstream documents: `vaquill-AI/open-india-law`, `main`, fetched 2026-10-10 02:46 to 02:47 UTC from raw.githubusercontent.com, saved in `upstream_snapshot/` (sha256 in `upstream_snapshot/SHA256SUMS`; the commit was not recorded).

## Verdict

**Do not use Vaquill's dataset to embed (or to extend) the Supreme Court judgments.** It adds no judgment we do not already hold, it is missing 2,522 that the open bucket lists, and its vectors cannot be mixed with ours. The only thing it could add is the High Courts, which this project does not hold; that is a separate decision (section 9), and a direct count against the AWS High Court tables it cites (section 3b) shows it holds 65% of their rows, with the shortfall concentrated in recent years and a few large courts.

1. **No unique Supreme Court judgments** [Certain]: all 35,596 Supreme Court case ids in the list Recourse built from Vaquill's parquet are in the open AWS bucket we already hold (0 Vaquill-only); the bucket lists 2,522 that Vaquill lacks. For the shared ids, title, party, date and law-report citation are identical to the bucket's in 99.7 to 99.9% of cases: Vaquill's Supreme Court layer is the bucket, processed.
2. **Holes in the processed copy** [Certain]: 2,414 of the 2,522 missing ids sit in five years: 2009 (1,309 of the bucket's 1,324), 2025 (455), 2008 (383), 2026 (214), 2006 (53).
3. **Not drop-in** [Certain]: voyage-4 vectors (we use voyage-law-2; both are 1,024 numbers, so a mix would not raise an error, it would give nonsense); 4,096-character chunks against our paragraph passages; the Supreme Court's vectors share a 179.6 GB collection with High Court chunks.
4. **Unaudited** [Certain]: in Vaquill's own release file 29 entries say `coverage_verified: false` and none says `true` (the case-law tier carries no such flag and is marked HELD); its README says the judgments are published while the same repository's `coverage.yml` says case law is "HELD. Not released"; its yearly table disagrees with its own parquet by up to 297 judgments in one year.
5. **No accuracy gain in text** [Likely]: its English text agrees with ours at about the level our own two sources agree with each other (a word-level difference of about 3%), and carries the same scan debris (Recourse measured 189 stray margin letters and 49 repeated paragraphs in one judgment).

## 1. Two premises to correct

| Premise | What is true |
|---|---|
| "a Vaquill database with all the judgments in the repository" | The Recourse checkout holds **103 judgments' full text** (`vaquill_search.db`, a domestic-violence topic pool, keyword search only) and a **38,026-row case list** (`case_lookup_index.db`: title, parties, date, citation; 35,596 rows from Vaquill, 2,430 added later from the bucket; its `doc_bundle` text table is empty). The 12.8 million judgments are not in the repository; the code reads Vaquill's remote parquet on demand (`build_index`, `fetch_case_text`). [Certain] |
| "claims every judgment from all courts" | README line 4: "Every judgment of the Supreme Court of India and all 25 High Courts". Line 15: "District and trial court decisions are **not** included." Tribunals are "indexed by case, not yet by full text" (line 100). The claim is Supreme Court plus 25 High Courts, and no entry in its release file has passed its own completeness audit (29 entries say `coverage_verified: false`, none says `true`). Measured against the AWS tables it says it was built from: Supreme Court 93% of the bucket's ids (section 3), High Courts 65% of the bucket's rows (section 3b). [Certain] |

## 2. The four sources side by side

| | Our crawl (api.sci.gov.in) | Open AWS bucket (Dattam Labs, CC-BY-4.0) | Indian Kanoon (IK) | Vaquill open-india-law |
|---|---|---|---|---|
| What it is | The court's own `judis` PDFs, text extracted by us | The court's PDFs plus a metadata table per year | Commercial aggregator; pay-per-call API | Text, chunks and vectors made **from the bucket's PDFs** (README lines 35 to 37 and 424 to 428: "we do not re-host them ... publishes the layer they lack: extracted text, chunking, provenance and metadata") |
| Supreme Court judgments | 36,928 | 38,152 distinct for 1950 to 2025, plus 214 for 2026 | 54,349 listed for 1968 to 2025 (55,332 to 2026) | 34,954 in its own table; 35,596 ids in its parquet as read |
| Reaches to | 4 May 2017 | 12 Aug 2026 | now | 2025 (none for 2026) |
| What we hold of it | all of it as text | metadata for all; text for the 9,084 judgments the crawl lacks (our unified store holds 46,012 documents) | counts only (typed from a screenshot) and Rs 8.49 of API calls; spending stopped by the owner on 2026-10-06 | 103 judgments' text and the case list |
| Licence / terms | court's own site; government work | CC-BY-4.0 | API terms: attribution ("powered by IKanoon") required for RAG; storage silent | code Apache-2.0; compilation CC BY 4.0 (attribution); underlying text a government work (their reliance: Copyright Act s.17(d), s.52(1)(q)) |

Vaquill's own policy file excludes IK entirely ("Indian Kanoon in particular: none of its data, none of its scrapers, no derived material", `coverage.yml` lines 41 to 45), so it is independent of IK but not of the bucket. [Certain]

## 3. Coverage: judgments per period (every source counted by decision year)

Produced by `vaquill_vs_ours.py` from `coverage/year_counts.csv`, `upstream_snapshot/vaquill_sc_by_year.json` and `vaquill_id_overlap.json`.

| Period | IK | our crawl (est.) | open bucket | Vaquill (own table) | Vaquill rows as read | rows as share of bucket |
|---|---|---|---|---|---|---|
| 1950-67 | - | 3,473 | 3,483 | 3,304 | 3,455 | 99% |
| 1968-79 | 5,919 | 3,623 | 3,619 | 3,607 | 3,617 | 100% |
| 1980-89 | 4,473 | 2,786 | 2,700 | 2,865 | 2,689 | 100% |
| 1990-99 | 11,983 | 6,910 | 6,497 | 6,469 | 6,454 | 99% |
| 2000-04 | 6,688 | 4,561 | 3,276 | 3,276 | 3,267 | 100% |
| **2005-09** | 8,843 | 7,934 | 5,815 | 4,057 | 4,063 | **70%** |
| 2010-14 | 5,460 | 5,148 | 4,007 | 3,974 | 3,954 | 99% |
| 2015-17 | 2,337 | 2,437 | 2,080 | 2,019 | 2,012 | 97% |
| 2018-23 | 6,201 | 3 | 4,996 | 4,200 | 4,910 | 98% |
| **2024-25** | 2,445 | 0 | 1,679 | 1,183 | 1,175 | **70%** |
| **2026** | 983 | 0 | 214 | - | 0 | **0%** |
| 1968-2025 | 54,349 | 33,402 | 34,669 | 31,650 | 32,141 | 93% |

The years that matter:

| Year | IK | our crawl (est.) | bucket | Vaquill rows | Vaquill table | bucket ids Vaquill lacks |
|---|---|---|---|---|---|---|
| 2006 | 1,250 | 1,155 | 1,029 | 976 | 976 | 53 |
| 2008 | 2,835 | 2,447 | 1,508 | 1,124 | 1,123 | 383 |
| **2009** | 2,218 | 2,069 | 1,324 | **13** | **6** | **1,309** |
| 2025 | 1,421 | 0 | 897 | 437 | 439 | 455 |
| 2026 | 983 | 0 | 214 | 0 | - | 214 |

Reading [Certain unless marked]:
- In every year outside the five below Vaquill holds 86 to 100% of what the bucket holds (median 99.7%; lowest 1958 at 86%, 2024 at 94%, 2018 at 95%): a processed copy, not a second source. The five holes are its own; 2009 is almost absent, and for 2005 to 2009 our crawl holds nearly twice as many as Vaquill (7,934 against 4,063).
- Recourse found the 2025 hole independently on 2026-09-20 (`extend_index_from_bucket.py` docstring: 437 against 897; *Gayatri Balasamy v ISG Novasoft* "not found" although its PDF exists) and patched its case list with 2,430 bucket rows (2009: 1,309; 2025: 456; 2008: 384; 2006: 52). It still lacks the bucket's 214 rows for 2026 and 4 older ones.
- Against IK's list for 1968 to 2025 the three open sources hold about the same 59 to 64% (Vaquill 32,141; crawl 33,402; bucket 34,669 of 54,349). Vaquill does not close any part of that gap. IK may count orders or duplicates (`coverage/COVERAGE_NOTE.md` section 2), so "IK has more" does not prove every extra is a distinct judgment. [Likely]
- **Vaquill's yearly table does not match its own parquet**: the rows Recourse read exceed the table by up to 297 in a year (2021: +297; 2019: +231; 2020: +102) and fall short by up to 153 (1964: -153; 1988: -152; 1985: -123); summed, +1,662 and -1,020, and 35,596 ids against the README's 34,954. Cause unknown (the table says "measured July 2026"; the parquet is the later snapshot) [Likely].

## 3b. High Courts: the same test against the AWS High Court tables (`hc_aws_vs_vaquill.py`, `hc_aws_vs_vaquill.json`)

Vaquill says its High Court text comes from the public AWS bucket "Indian High Court Judgments" (README lines 35 to 37, 424 to 428; "~17.8M judgments, ~1.25 TiB"). I counted the rows of that bucket's 1,494 metadata tables from their parquet footers (one small range request each; nothing downloaded; no Vaquill host used) and set them against Vaquill's own per-court, per-year table and its own "held vs embedded" table.

| | Rows / documents |
|---|---|
| AWS tables, all years / through 2025 / 2026 | 20,673,084 / 19,691,923 / 981,161 (25 courts) |
| Vaquill, High Court total (its table; "embedded") | 12,813,690 = **65%** of the bucket's rows through 2025; 72% of the 17.8M its own README quotes for the same bucket |
| Vaquill, "extracted texts held" (its `COVERAGE.md`, measured 2026-08-14) | 14,600,558 = 74% |

| Court | AWS rows to 2025 | Vaquill published | share | Vaquill texts held | share |
|---|---|---|---|---|---|
| Gujarat | 416,562 | 411,638 | 99% | 414,751 | 100% |
| Patna | 1,648,679 | 1,615,041 | 98% | 1,627,284 | 99% |
| Telangana | 1,033,581 | 1,004,138 | 97% | 1,009,749 | 98% |
| Madras | 1,588,012 | 1,494,952 | 94% | 1,518,793 | 96% |
| Allahabad | 3,342,568 | 1,498,250 | **45%** | 1,567,283 | 47% |
| Bombay | 2,307,560 | 1,595,948 | 69% | 1,382,734 | 60% |
| Punjab and Haryana | 1,779,511 | 483,253 | **27%** | 797,830 | 45% |
| Rajasthan | 1,077,087 | 324,567 | **30%** | 1,057,775 | **98%** |
| Orissa | 752,783 | 283,063 | 38% | 0 | 0% |
| Jammu and Kashmir | 107,422 | 40,289 | 38% | 103,044 | 96% |
| Sikkim | 2,358 | 453 | 19% | 2,317 | 98% |

(The other 14 courts are in the JSON.) Reading [Certain as counts; the causes are Likely or Guessing]:
- **Where the gap is**: 794 of the court-years fall short; only two (Gauhati 2022 and 2023) exceed the bucket, by 156 rows in all. 76% of the shortfall (6.9 million rows) is in 2018 to 2025 and 54% of it in the 25 largest court-years. Allahabad's bucket tables hold almost nothing before 2018 (2,324 rows) and 3.34 million for 2018 to 2025, of which Vaquill has 45%. Bombay 2024: 277,355 against 73,777; 2025: 386,281 against 44,981. Punjab and Haryana 2012: 85,301 against 0; 2023: 149,388 against 3,023; 2024: 154,801 against 8,594; 2025: 145,495 against 2.
- **Vaquill's own unresolved question has an answer**: its `COVERAGE.md` says that for Rajasthan 1,057,775 texts are held against 324,567 embedded, "Either the embedded figure is a severe undercount or roughly 70% of Rajasthan was never indexed. Unresolved." The bucket lists 1,077,087 Rajasthan documents, so the held texts are 98% of the bucket and the published figure 30%: the missing 70% is lost after extraction. The same shape holds for 10 more courts (Kerala, Madhya Pradesh, Jharkhand, Calcutta, Himachal Pradesh, Uttarakhand, Jammu and Kashmir, Tripura, Meghalaya, Sikkim: held 94 to 99% of the bucket, published 19 to 88%). [Likely]
- For Allahabad, Bombay and Punjab and Haryana even the held texts are only 45 to 60% of the bucket (Karnataka 76%, Andhra Pradesh 80%, Chhattisgarh 82%, Manipur 86%); Orissa has none.
- **Caution**: a row is one document of a case (its PDF is named `<CNR>_<order number>_<date>`), so it can be an interim order. The metadata cannot separate final judgments from orders (`is_final` and `order_type` exist in recent files only and are almost empty), and `pdf_exists` reads False on every sampled row. Vaquill may have left out interim orders on purpose, so this shows missing documents, not missing final judgments. That Vaquill's held texts match the bucket's row count in so many courts suggests its "judgments" are documents of this kind. [Likely]

## 4. Metadata: copied from the bucket, with one gap

For the 35,596 shared ids (`vaquill_id_overlap.json`): same title 99.8%, same petitioner 99.9%, same decision date 99.8%, same law-report citation 99.7%. The few differences are mostly two judgments sharing one neutral id. Fill rates as read by Recourse: law-report citation 35,596 of 35,596; **`source_url` 0 of 35,596**, although the README (line 278) says the publisher's own page is given "on 83.3% of rows" in v2026.08.1. Recourse recorded the same on 2026-09-14 for its 103 judgments ("`source_url` is empty for every one of the 103 ... candidates"). Which snapshot Recourse read is not recorded, so the 83.3% may hold for other courts or a later file [Likely].

## 5. Text: what the evidence supports (`vaquill_text_compare.py`, 101 of the 103 pool judgments matched to our text by neutral citation and date)

| Measure | Result |
|---|---|
| Median length, Vaquill stored text / our text / Vaquill English-only | 109,133 / 39,950 / 52,959 characters |
| Judgments over 30% non-Latin script | 89 of 101 (median 61%) |
| Judgments with `[SECTION]` tags; with `Case:` header lines | 101 of 101 (median 50 tags); 101 of 101 (median 30 lines) |
| Share of our 8-word runs found in Vaquill's English text (median) | 78% (implies a word-level difference of about 3%) |
| Same measure, our crawl against our bucket, scanned years (`COVERAGE_NOTE.md` section 3) | 76% |

**How to read it.** The language mix, tags and headers are **not a defect of the dataset's English text**: Recourse's first builder (`vaquill_search.py`, 2026-09-14) joined every parquet row of a case id in every language and used the `text` column, which carries a contextual header for keyword search (`UNIFIED_CHUNKING_SCHEMA.md` lines 47 to 49, 138 to 139). Recourse's later builder says so itself: "Every case is stored ONCE PER LANGUAGE (en, hin, mar, ori, pun, tam ... -- the Supreme Court's vernacular translations, some badly OCR'd) ... mixing them produced interleaved garbage plus chunk counts inflated ~4x" (`case_lookup.py` lines 162 to 165). The README's own recipe ("group by `case_id` and order by `chunk_index`", line 266) does not mention a language filter, so a reader who follows it gets that result. The figures that bear on the dataset are the last two: its English text matches ours at the level our own two sources match each other, so **no gain**, and Recourse measured the same scan debris in it (`case_lookup.py` lines 394 to 399: on one judgment "49 repeated paragraphs, 189 stray letters, 525 paragraphs where ~375 are real") and had to write about 180 lines of cleaning code (`case_lookup.py` lines 379 to 557). No ground truth was checked, so this does not show whose text is more accurate. [Likely]

## 6. Chunks and vectors: why they cannot be reused

| | Ours | Vaquill |
|---|---|---|
| Unit | 236,155 passages of 10,503 criminal-law judgments; mean 1,089 characters (median 1,315, max 3,000) | chunks of 4,096 characters with 512 overlap (`UNIFIED_CHUNKING_SCHEMA.md` lines 22 to 23), about 5 language objects per Supreme Court judgment (`COVERAGE.md` lines 177 to 179) |
| Paragraph numbers | on 69.2% of passages (method `para`); the rest built from sentences | none; "section" labels come from regex detection ("15+ regex patterns", `UNIFIED_CHUNKING_SCHEMA.md` line 104; values `ratio_decidendi`, `obiter_dicta`, `conclusion`, `section`, `body`, `paragraph`, as mapped in `vaquill_search.py`) |
| Labels used by the search | passage type (reasoning, argument, facts, statute_text, order, header) with weights tuned on the marks of J and S | not comparable; a regex label for "ratio" is a guess [Likely] |
| Vector model | voyage-law-2, 1,024 numbers, float16 matrix (0.48 GB) | voyage-4 series, 1,024 numbers, Qdrant snapshots; Supreme Court only in `legal_corpus_v2` (11,823,753 points, 179.6 GB, Supreme Court and High Court together) (`README.md` lines 293 to 308) |

A question must be embedded by the same model as the passages, so adopting Vaquill's vectors means replacing voyage-law-2 everywhere, then redoing the pool, the re-ranker settings, the passage-type weights and the J and S marking on a different chunk shape. The saving is bounded by what embedding costs us: the current index took 67.3 million tokens (the block file names in `recourse-sci-index/index/`), about $8 at the listed $0.12 per million tokens; everything we hold (46,012 documents, 1.33 billion characters, about 348 million tokens at 3.82 characters per token) would be about $42 at list price [Likely; price from third-party lists]. If the attraction is the newer model, test voyage-4 on our own passages with the same marking protocol; that does not need Vaquill's data. [Guessing about any benefit]

## 7. Licence, provenance, internal contradictions

- **Licence** [Certain]: not a differentiator. Their compilation is CC BY 4.0 (attribution, say if changed); the text is a government work reproduced under s.52(1)(q), which their own `LICENSE.md` calls "defeasible" where a court has barred publication. Our sources are equally open.
- **Release status contradicts itself** [Certain]: README says 26 judgment files are published (`v2026.08`, 32,572,660 chunks); `coverage.yml` line 206 says "TIER C - case law. HELD. Not released, and no scraper is published", with `required_before_any_release` still listing a provenance audit, an exclusion filter, a redaction pass and a pending Supreme Court reference on the right to be forgotten; the same file's `snapshot.legal_review` says "Release cleared by counsel, August 2026". Probably one is stale; we cannot tell which.
- **Own admissions about High Court data** [Certain]: Orissa High Court has 283,063 judgments embedded and "not one of them has a text file on record"; Bombay has 213,214 fewer texts than embedded judgments; for Rajasthan 1,057,775 are held against 324,567 embedded ("Either the embedded figure is a severe undercount or roughly 70% of Rajasthan was never indexed. Unresolved.") (`COVERAGE.md` lines 165 to 171). The per-court breakdown is "not yet measured" (`coverage.yml`).
- **Redaction changes the court's words** [Certain that it is done; Likely that it is minor]: phone numbers, e-mails, some IDs and some names are masked by rule (README lines 437 to 446), and their exposure measure of 2026-08-13 (taken before the redaction pass) counted "~95k chunks" with live phone numbers, so we cannot tell what remains. Anything we quote would need checking against the original PDF.
- **Commercial interest** [Certain]: the README advertises paid pipeline work ("If a law firm, publisher or legal-research product needs data at this scale ... email contact@vaquill.ai"), so the headline "every judgment" is marketing copy until audited.
- **Recourse's own verdict on it** [Certain]: "THIS IS NOT A TRUSTED-TIER SOURCE. Nobody has hand-verified this dataset" (`case_lookup.py` lines 17 to 19). Fetching one case live from the remote parquet takes "~30-50s (sometimes far more)" (line 597).

## 8. What Vaquill does better, and what I could not verify

Better, for fairness [Certain]: 25 High Courts (12.8 million documents published, 14.6 million texts held) where we hold none; a clear data licence and attribution line; published checksums and superseding snapshots; a redaction path; chunk-level vectors anyone can restore; candid caveats (`Important caveats`, `coverage.yml`).

Not verified, and why:
1. **The parquet itself.** `oss-data-in.vaquill.ai` and huggingface.co answer HTTP 403 from this environment's gateway, so I could not read the Supreme Court file's schema, the real fill rates (`source_url`, `citation`, `case_number`), the per-language rows, or any High Court file. Everything about the Supreme Court layer rests on Vaquill's own tables, Recourse's catalogue and 103-judgment pool (built from it), and our bucket metadata. [Certain that it is blocked]
2. **Why 2009 (and 2008, 2025) are missing.** Unknown; a processing gap is the simplest guess [Guessing].
3. **Whether its English text is better after a proper language filter and `text_original`.** Not testable without the parquet; the 103-judgment pool is also one topic (domestic violence), so it may not represent other topics.
4. **High Court text quality** (counts are now checked against the AWS tables, section 3b; text is not), and whether the OCR fallback (a script in the legislation folder) is used for judgments.

## 9. Recommendation

1. **Supreme Court: keep the crawl and the bucket; do not add Vaquill.** Nothing in it is new; the 2005 to 2009 hole in the bucket is better filled from our crawl (7,934 against 5,815), and the thin spots against IK (about 40% of 1968 to 1999) are not helped by Vaquill at all.
2. **Do not import its vectors or chunks** (section 6).
3. **High Courts, only if you want to widen beyond the Supreme Court:** run a small pilot rather than adopt the dataset. One High Court, one topic: (a) take that court's PDFs from the AWS High Court bucket (CC-BY-4.0), not Vaquill's chunks; (b) check coverage against a random sample from the court's own portal before trusting any count (Vaquill's published High Court counts are 65% of the AWS tables and unaudited by its own file; the AWS tables themselves count documents, orders included); (c) embed with voyage-law-2 using our chunker, so the existing pool, re-ranker and marking tools apply; (d) judge it on 10 to 15 questions marked by J and S before it joins the index. Nothing is spent until you say so.
4. **If you want me to look at the parquet itself** (Supreme Court schema, fill rates, the 2008 and 2009 hole, High Court samples): add `oss-data-in.vaquill.ai` to the cloud environment's allowed domains. Reading a few columns costs no Voyage money.
5. **Side finding for the Recourse owner** (the Recourse repository is read-only for this project): the case list lacks the bucket's 214 rows for 2026; `extend_index_from_bucket.py 2026` is the person-run fix.

## Files

| File | What it is |
|---|---|
| `vaquill_id_overlap.py` / `.json` | id overlap, field-by-field metadata comparison, fill rates, missing ids by year, Recourse's bucket additions |
| `vaquill_vs_ours.py` / `.json` | the period and year tables of section 3 |
| `vaquill_text_compare.py`, `vaquill_text_compare_summary.json`, `vaquill_text_compare_rows.json` | section 5 (counts and shares only; no judgment text is saved) |
| `hc_aws_vs_vaquill.py` / `.json` | section 3b: footer row counts of the AWS High Court tables against Vaquill's per-court and per-year tables (public S3, anonymous, no spend; about 3 minutes) |
| `upstream_snapshot/` | the nine upstream documents quoted above, unmodified, with `SOURCE.md` and `SHA256SUMS` |

Inputs that live outside the repository (so the scripts take paths): the Recourse checkout (`case_lookup_index.db`, `vaquill_search.db`), the Supreme Court bucket's per-year metadata tables (`meta_<year>.parquet`) and `corpus.sqlite` (the session's unified text store); `hc_aws_vs_vaquill.py` reads the public High Court bucket directly. Run the scripts with `python3 -P` from a directory without data files. Each script reproduced the figures of the scratch versions run earlier the same day (2026-10-10).
