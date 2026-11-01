# The whole Negotiable Instruments Act, 1881 and Information Technology Act, 2000 on the Act shelf (2026-10-31)

Owner's instruction: "Load the full NI Act and IT Act too". Recourse branch `register-hooks-and-overlay` (`266aace`), NOT on `main`; nothing deployed. The shelf is now **13 Acts, 1,031 sections, 1,003 embedded** (the unembedded ones are 27 omitted or repealed stubs).

## What was loaded and how it was checked (same pipeline as the other nine database Acts)
| Act | Sections | Embedded | PDF | Strict word-by-word comparison |
|---|---|---|---|---|
| Negotiable Instruments Act, 1881 | 155 (s.2 repealed) | 154 | India Code PDF, no date printed | 14,720 words; 9 differences, all accepted with a reason |
| Information Technology Act, 2000 | 125 (16 omitted) | 109 | India Code PDF as on 27 June 2025 | 16,647 words; 19 differences, all accepted with a reason |
Status `machine_checked` (a program compared; nobody has read it). Embeddings: `voyage-law-2`, about 45,500 tokens, under half a cent. Schedules, Rules and notifications are not loaded.

## What the check found in India Code's database (repaired from its own PDF, each with its reason in the manifest)
* **IT s.68(2) was out of date in the database**: it still said imprisonment up to two years or fine up to one lakh rupees or both; the PDF has "liable to penalty which may extend to twenty-five lakh rupees" (Jan Vishwas Act, 2023). The PDF's wording is on the shelf.
* **IT s.66A**: the database kept the whole text that the Supreme Court struck down in 2015. The shelf now holds only the PDF's omission line (omitted by the Jan Vishwas Act, 2023, w.e.f. 30-11-2023) and India Code's footnote about Shreya Singhal, so the struck-down wording can never reach the answer model.
* IT s.2 ("electronic signature" for "digital signature" in one clause), s.45 (a lost line break), s.1 / s.9 / s.2 / s.87 (lost spaces and hyphens), titles of s.48 and s.72A.
* NI s.135 had lost its first word's first letter ("here" for "Where"); ss.103 and 108 lost a hyphen; the title fields of ss.7, 21 and 133 lacked words the PDF's headings have; one footnote lost a space.
* Loader changes needed (all tested; the nine earlier Acts reload identically): accepted differences between the PDF's printed arrangement of sections and the database (`toc_title_accepted`), a start pattern for an Act whose PDF has no "enacted by Parliament" (`body_start`), the NI PDF's misspelt "ARRENGMENT OF SECTIONS" heading, and footnote numbers glued to words ("1Subs.").

## A finding about the library (NOT fixed; needs the owner's say-so)
The library's own chunk of the IT Act (10 sections) was compared with the checked text: **sections 72 and 72A in the library are the OLD wording** ("punished with imprisonment ... two years" and "... three years"). The PDF (27 June 2025) has "liable to penalty which may extend to five lakh rupees" (s.72) and "twenty-five lakh rupees" (s.72A), substituted by Act 18 of 2023 w.e.f. 30-11-2023. The library's chunks are what the live IT Act answers use. The other 8 IT sections and all 19 NI sections match the checked text apart from one-word spelling differences. The `itact_section_data` / `itact_section_status` tables may carry the same old punishments; I did not look.

## How it reaches an answer, and how it does not
* **Questions: unchanged.** The two Directory entries have `detect: false` (like the repealed IPC and CrPC), so a question that names the NI Act or the IT Act is NOT tied to the shelf copy; the library's cheque-bounce and IT Act flows answer it as before. Reason: the library already answers these questions through curated flows, and putting a second copy of section 138 next to them would duplicate text and could confuse the code that looks for `NIACT` / `ITACT`. The shelf codes are `NIACTFULL` / `ITACTFULL` so nothing keyed on the library's codes sees them. Switching detection on is a one-line change per Act and needs a test of the overlap first.
* **The lawyers' search page: changed.** A section the library does not hold (for example NI s.9, IT s.68) is now taken from the shelf instead of "not one of the 19 sections"; where both hold the section (NI 138) the library's card stays and the shelf copy is dropped. Meaning search also finds the shelf's sections.
* Status lines in the Directory are Claude's drafts with their evidence; none is reviewed.

## What this does NOT show
Nobody has read either text; the NI PDF carries no date; neither Act's Rules or Schedules are held; five readings where the database and the PDF disagree and neither is certain are listed on `acts/NI_IT_SHEET.docx`; nothing was tried with the answer model; no hallucination rate has been measured.

## Tests
`test_full_ni_it.py` (data, repairs, Directory entries, search page); the shelf-wide tests were updated from eleven to thirteen Acts; the whole free suite passes (124 of 124 files).
