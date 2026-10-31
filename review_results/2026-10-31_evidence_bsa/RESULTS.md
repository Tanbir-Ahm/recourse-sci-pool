# Evidence Act 1872 and Bharatiya Sakshya Adhiniyam 2023 on the Act shelf, section map, companions (2026-10-31)

Owner's decision (answer-quality list, item 5): "load the Evidence Act and the BSA which are not in the library or on the Act shelf, both from India Code with the machine checks, plus a section map (s.106 to s.109, s.27 to the proviso of s.23(2), and so on)". Companion searches for circumstantial-evidence questions were part of the approved plan. Recourse branch `register-hooks-and-overlay`, NOT on `main`; nothing deployed; switch `ACT_SHELF` (already on on production by the owner's decision of 2026-10-20) decides whether the two Acts reach an answer, `EVIDENCE_COMPANIONS` (default off) the companions.

## 1. The BSA: machine_checked (same pipeline as the other nine Acts)
170 sections from India Code's database, equal to the PDF's arrangement of sections; strict two-way word-by-word comparison against the PDF (26,041 words) found **five faults of India Code's database, all repaired from the PDF with the reason recorded in the manifest**:
* s.2: "Bs death" for "B's death" (lost apostrophe);
* s.45 and s.121: the single illustration headed "Illustrations" (PDF: "Illustration");
* **s.94: illustration (c) is MISSING** from the database (it goes from (b) to (d)); restored exactly as the PDF prints it;
* **s.119: illustration (a) printed twice**; one removed.
Ten group headings that the PDF prints between sections ("Admissions", "Public documents" ...) are accepted as not part of any section.
Status `machine_checked`: a program compared the text with the PDF; no person has read it.

## 2. The Evidence Act: machine_extracted (ONE source only)
India Code keeps the repealed Act as an archive stub: one record, one PDF (`A1872-1.pdf`, 61 pages), **no section records**, and the Chhattisgarh, Rajasthan and Daman and Diu copies are stubs too. So the two-source check used for every other Act is impossible. What was done instead (`build_act_from_pdf.py`):
* the 185 sections are cut from the PDF's running text; their numbers and order equal the PDF's own arrangement of sections (seven headings whose wording differs from the arrangement, e.g. s.95 "unmeaning reference to", are accepted one by one with the reason);
* a second reader (Poppler `pdftotext`) must agree: every word of every section occurs in its reading, and every stretch where the two readings differ (35 of them) is explained by footnote text, a page mark or a footnote number that Poppler puts into the sentence (a stretch that is not explained stops the load);
* State amendments (Arunachal Pradesh 53A and 146, Chhattisgarh 114A) are set aside, not loaded; the footnotes and page numbers are not in the text; the Schedule (a list of repealed enactments) and the Preamble are not loaded.
Status `machine_extracted` (new value, accepted by `act_shelf.GOOD_STATUS`): **weaker than `machine_checked`**. It shows the cutting is complete and in order, not that the PDF's own text is free of misprints. A vocabulary check (words of the Act that no other loaded text has) found two suspected misprints, kept as printed: s.27 "inconsequence" (the BSA reads "in consequence") and s.6 illustration (a) "goals" (usually "gaols"). Mr. Advocate's sheet asks.

## 3. The section map (`section_map.py`, `act_shelf/section_map_ea_bsa.json`)
Built by program from shared wording (share of three-word runs of each Evidence Act paragraph found in one Adhiniyam paragraph, after the Act's new names are put in). Results: 122 same wording, 44 reworded, 14 partly carried, 1 split or merged, 3 with no counterpart found (113 cession of territory, 82, 166), 1 repealed in the Act (s.2).
The owner's two examples come out as he said: **EA 106 -> BSA 109 (99% of the words)** and **EA 27 -> the proviso to BSA 23(2) (88%)**; also EA 25 -> BSA 23(1), EA 24 -> BSA 22, EA 115 -> BSA 121, EA 145 -> BSA 148, EA 65B -> BSA 63 (69%, reworded: the Adhiniyam rewrote the certificate rules). EA 26 -> BSA 23(2) is only 32% (the wording changed) and is listed as "partly carried": **this is the kind of pair a lawyer must check**.
It is a count of shared words. It is not a statement that two sections mean the same, and it does not say which Act governs a given case. Status `machine_built_not_reviewed`; the sheet `acts/EVIDENCE_BSA_SHEET.docx` asks Mr. Advocate about the pairs the owner named, every pair the program is unsure of, and the rest on request.

## 4. How it reaches an answer
* The Act Directory already knew both Acts by name; the shelf now holds their text. "Section 106 of the Evidence Act" -> `named` section 106, plus the sections found by meaning; "Section 63 BSA" -> `named` BSA 63 (tried with the real embeddings: yes).
* Every matched section of these two Acts carries a fixed note (`ea_bsa_map.py`, through `context_note`): the repeal date (India Code), the corresponding section "reportedly", "our reviewer has not read it", never "means the same", never which Act governs. A section with no counterpart is not said to be dropped or carried over.
* `EVIDENCE_COMPANIONS=on` (default off; `evidence_companions.py`): for a circumstantial-evidence question (the same question test as `LANDMARKS`), EA 106, 27 and 8 and BSA 109, 23 and 6 are handed over from the shelf (needs `ACT_SHELF=on`), and, in feed mode, three more questions go to the wider search (last seen together; false explanation as a link; recovery on a disclosure statement), the best new result of each placed after the third result. All or none for the shelf pair; fail-open.

## 5. What this does NOT show
* No Anthropic key in the sandbox: **nothing was tried with the answer model**, and the companion searches were tried only with stand-ins (the sandbox has no index). Whether the wider-search companions bring useful cases is for the owner's staging test (`DEPLOY_STAGING.md` Part 4ag).
* The Evidence Act text rests on one PDF whose date is not printed; the Act as amended up to 30 June 2024 is not proved.
* Nobody has read either Act's text or the map. "Pre-July 2024 trial, which Act applies" is a legal question the notes deliberately do not answer.
* **Production effect once merged:** with `ACT_SHELF` already on, a question that names the Evidence Act or the BSA will now be answered from the shelf text (before, the Directory said the text is not held). That is the point of the change, but it changes production's behaviour on merge.
* No hallucination rate has been measured.

## 6. Tests
`test_evidence_bsa.py` (loader pieces, map, note, data files, shelf), `test_evidence_companions.py`; the nine older tests that counted "nine Acts" were updated; two older tests (`test_api_ask.py`, `test_refusal_text.py`) had been broken by the 2026-10-31 build stamp (a log line on stdout and a footer on the page) and were made to allow for it. Full free suite: 121 of 122 files pass; the one failure is a timing check (`test_grounding_checks.py` speed: 4.1 s against a limit of 4 s) that fails the same way on the untouched code.
