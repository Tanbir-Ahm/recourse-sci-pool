# Finding out what brings an ordinary lawyer back: ten interviews and a two-week manual test (written 2026-11-21)

**Status: documents written, nothing run.** Written on the owner's "Yes, write the interview script and the hearing-prep sheet" after Claude's answer to "what would make an everyday ordinary lawyer come back to Recourse". Demand is UNVERIFIED: no lawyer other than the reviewer has been asked anything. Everything here is Claude's reasoning; the thresholds are Claude's starting suggestions. No hallucination rate has been measured; nothing here says the tool is accurate or safe.

## Files (folder `lawyer_validation/`)
- `LAWYER_INTERVIEW_SCRIPT.docx`: who to talk to (ten criminal practitioners, mixed), rules for the person asking, the consent words, the questions in nine parts (A to I, 35 minutes: their practice; the last hearing; dates and counting; drafting; looking up the law; AI and trust; the sample sheet; the ask for a real matter; money last), the redaction rule, a note grid, what counts as a real signal, **the decision rules written before the first interview**, and a one-page pocket card.
- `HEARING_PREP_SHEET.docx`: pages 1 to 3 the sample sheet built from the SYNTHETIC chargesheet, remand orders, bail order and lawyer's note of 2026-11-19 (invented names; initials only); pages 4 and 5 the blank worksheet we fill for a real matter.
- `build_interview.py`, `build_sheet.py`, `docx_kit.py`: rebuild the two files. `build_sheet.py` reads the real test documents and **stops if any page cite or quotation in the sample is not on the page it cites** (all pass). It is for the sample only; a real sheet is made by hand from the template.

## What the sheet is (and is not)
One matter, prepared for a hearing: what is charged (the sections' own words from our library, the First Schedule row); dates with day numbers counted from arrest; what changed since the last bail order; what the papers say about the event; what the papers do not show; the lawyer's own note checked against the papers; authorities only on request. It states **no view on the merits** and **does not choose the detention period** of BNSS 187(3): it prints the text word for word and the arithmetic (day 60 and day 90 counted from arrest and from the first judicial custody order). Reason: our library's BNSS 187(3)(i) says "ten years or more" and BNS 309(4)'s punishment "may extend to ten years", so which bracket applies is a legal question for a lawyer; a day-count feature needs a lawyer-checked rule table first. It is NOT a draft and NOT drafting (drafting is not approved).

## The two stages and what we decide from them
1. **Ten interviews** (`LAWYER_INTERVIEW_SCRIPT.docx`), run by the owner. Decision rules are in section 8 of the script; change them before the first interview, never after.
2. **Two-week manual test, five lawyers**, only if the interviews say yes (4 or more would use the sheet and 3 or more offer a real matter). Each lawyer sends ONE redacted matter (initials; no addresses, phones, Aadhaar, bank or vehicle numbers) or a public order. Staging only; written consent first; papers deleted after the test; no real client paper in the live service until a lawyer writes the privacy and consent text (gate G1).

**Declared before the test (Claude's suggestions):** it works if 3 or more of 5 ask for a second sheet unprompted within 14 days; 3 or more return specific corrections; 2 or more say how many minutes it saved; at least 1 says it caught something they would have missed. It fails, and we do not build day counts or drafting, if fewer than 2 of 5 ask for a second sheet. **Any invented or wrong date, section or page that reaches a lawyer pauses the test and is logged with its cause.** The target is zero.

## How a real sheet is made
1. Upload the redacted papers to a staging matter (the documents panel); the system reads them by page.
2. The charged sections come from the "Sections:" line by code (`matter_files.charged_refs`), the words from the library, the table from the First Schedule rows (`law_on_hand`, `offence_class`).
3. Dates and facts are read from the text by a person or by Claude, each with its page.
4. Day numbers and the 187(3) dates are arithmetic only.
5. **A second person checks every date and page against the original before the sheet is sent** (the owner or Mr. Advocate). Never send a sheet that has not been checked.
6. Send it as Word. Log per sheet: minutes spent making it, errors the checker found, errors the lawyer found, whether they asked for another. If one sheet takes hours by hand, that is a finding too: the habit may be worth it, but not at that cost.

## Risks, said plainly
- The sample is built from invented documents; real papers are messier (scans without text are refused; no OCR).
- A wrong date or page destroys trust faster than anything else: hence the second-person check.
- Lawyers may like the sheet and still not pay for it. Money is asked last and only recorded.
- The ten lawyers are not a statistical sample. Ten stories decide what to build next; they do not prove demand.

Related: `LAWYER_RETENTION_PLAN.md` (clocks, drafting, pricing: still unapproved), `MATTER_WORKSPACE_PLAN.md`, `DRAFTING_PLAN.md`.
