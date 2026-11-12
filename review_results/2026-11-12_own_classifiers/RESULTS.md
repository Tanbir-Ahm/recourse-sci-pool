# Own-classifier fixes after the Dowry Prohibition Act staging test (2026-11-12)

Owner: "Build 1, 2 and 3". Recourse branch `register-hooks-and-overlay`, NOT on `main`. Nothing tried with the answer model. All questions are Claude's, not a lawyer's.

## What the staging answer showed (Q1 and Q2, `recourse-conversation-2026-11-12_1.docx`)
- Q1 built its first ground for bail on "Section 4 ... non-cognizable, bailable (Part II) ... release as of right under BNSS 478(1)". Section 8(2) of the Act says every offence under it is non-bailable and non-compoundable; section 8 never reached the model (the five sections handed over were 4, 3, 2, 8A, 6). Part II is the DEFAULT for another law's offence; the Act's own section governs.
- Section 8(1)(b)(ii) (Code applies as if cognizable except for arrest without warrant or Magistrate's order) was also never available: the best point for arrested parents was missed.

## Build 1: companion (shelf_companions.py)
When a section of an own-classifier Act that names a punishment is among the sections handed over (or any section of it when the question uses bail / arrest / cognizable / compound / custody / remand / release words), the classifying section is added as a companion (the cap may go to three for this rule). Marked `companion`, so the grey box under the answer shows its official text when the answer does not mention it. Governed by `SHELF_COMPANIONS` (default on; needs `ACT_SHELF`).

## Build 2: the Part II default is not offered for such an Act (offence_class.py)
`OWN_CLASSIFIERS`: Dowry Prohibition Act s.8, Juvenile Justice Act s.86, Muslim Women (Marriage) Act s.7, PMLA s.45, UAPA s.43D. Found by searching every shelf section for cognizable / bailable / compoundable; `test_own_classifiers.py` repeats the search and fails if a new section turns up that is neither registered nor on the read-and-not-needed list (IT Act 69, 69A, 77B; JJ 12; MV 19; NI 147; PC Act 9; UAPA 14). `other_law_block` writes ONE line for the Act: "this Act classifies its own offences in section N, whose text is in the material above. The Part II default does NOT apply ..." or, when the text is not in the material (companions off), "do not state whether ... say the material does not show it". The model is not told what s.8 says.

## Measured (runner `run_own_classifiers.py`, questions `questions.json` committed in `98f7ff1` before the runner existed; baseline = registry emptied = the behaviour of Recourse `6116d84`)
25 questions about the five Acts (14 with a bail / arrest / cognizable / compounding word), 10 controls.
- Act found by the Directory: 25 of 25 (unchanged).
- Classifying section in the material: 11 of 25 before, 25 of 25 after (by construction for questions that reach a punishment section; for the 14 bail-word questions 9 -> 14).
- A Part II default line offered for the Act: 21 of 25 before, 0 after.
- Controls (Acts with no own classifier): 9 of 9 unchanged, sections and block identical. Question C10 was labelled a control by mistake (it is a Dowry Act question); it changed as designed, and its section 8 is not needed for a question about the definition of dowry: the cost of the rule is up to about 3.5k characters (UAPA 43D), 2.4k (PMLA 45), under 1k for the others, added to a prompt that reaches a punishment section of those Acts.
Limits: the questions are mine; the check is about what reaches the prompt, not what the model writes with it.

## Build 3: section-gloss check (section_checks.py)
- A sentence that describes the Schedule's classification ("Part II", "First Schedule", "classified") is not checked as a description of the section; the words of the code-built classification blocks count as given (like the person's own words); the clause after ';', a dash or ", the Supreme Court / High Court" is not attributed to the section.
- Result on the 12 saved answers (development material): the Dowry Q1 notices (both false) are gone; the other 6 flags of the old check, all on BNSS 483/480/47 sentences, are gone except one on BNSS 483(3), which is a false alarm of the eval (the saved page shows a windowed box, the engine's text holds "arrested and commit him to custody"). Recall of the new check was not re-measured on real answers; only hand-written cases test that a true positive still fires.
- **Correction of my reply of 2026-11-12:** I called the quote check's flag on "not less than five years" a false alarm caused by the amendment bracket. It was a real small misquote: the section reads "shall not be **be** less than [five years", the answer dropped "be". The quote check was right and needs no change; nothing was built for it.

Suite 152 of 152.
