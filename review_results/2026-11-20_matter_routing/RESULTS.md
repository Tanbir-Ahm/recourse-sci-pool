# Matter question routing, R0 + R1: results (2026-11-20)

**Owner's go (2026-11-20):** "go ahead with auto routing, legal path when unsure." Plan: `MATTER_ROUTING_PLAN.md` (FOLLOW_UPS 2et). Built: the router (R0, with a `shadow` mode that only logs) and the quick answer from the documents (R1), with the drafting notice (D0). Recourse branch `register-hooks-and-overlay` and `recourse-web` `main`; NOT on Recourse `main`; nothing deployed. **Nothing here has been tried with the answer model** (no Anthropic key in the sandbox). No lawyer has labelled a routing question or read an answer. No hallucination rate has been measured.

## What changes for the person (only inside a matter that has documents, and only with `MATTER_FILES=on` and `MATTER_ROUTING=on`)
- **A question about what the file says** ("what are the sections charged here?", "when was he arrested?", "chargesheet mein kaun se sections lage hain?") gets a short answer from the documents only: one model call, the documents as the only source, every statement cited `[Doc N, p. M]`, "The documents given do not show ..." when they do not, and no law. A line above the answer says **"From your documents only. This answer states no law."** and the documents box says which pages were read ("Looked at: Doc 1 chargesheet.pdf (all 6 pages)").
- Under that answer, one tap runs it the other way: **"Ask this with the law"** (the full research answer) and, when the answer names charged sections that code finds in the documents, **"Explain BNS 309(4), BNS 115(2)"** (a legal question the server writes: "Explain sections 309(4) and 115(2) of the Bharatiya Nyaya Sanhita, 2023, and how they apply to the facts of this matter.").
- **A legal question** ("is he entitled to default bail on these dates?") takes the legal path exactly as today; the line says "Answered with the law and your documents." When the model on the file path finds the question needs law, it replies `NEEDS_LAW` and the legal path answers instead ("This question needed the law, so it was answered with the law and your documents.").
- **A request to draft** ("go through the material I uploaded and draft a bail petition for me", "bail application draft kar do") gets a plain notice, "Recourse can't draft this yet", with what can be asked instead, and **"No answer was used up by this message."** No model is called. A question ABOUT drafting ("how is a quashing petition drafted?") is a legal question, not a request.
- **Anything unsure goes to the legal path.** A matter with no documents always takes the legal path.

## The router (rules only; `matter_routing.py`)
Order: a request to draft first; then any law signal (legal judgement words, a named Act, a section asked about, a case name, "can he / should we", bail, punishment, limitation, ...) → law; then a file signal (a document word, a pointing word with an extraction word, a past-tense report, the file's actors, simple Hinglish) → file; otherwise law.

**Measured on the frozen set** (`router_set.json`, 140 questions written by Claude and committed in `4c5b51c` BEFORE any router code; two halves of 70, each 36 legal, 28 file, 6 draft, with 9 traps such as the title line "report under section 193" and 3 questions about drafting):

| Half | Legal → legal | File → file | Draft → draft | Legal sent to the file path | File sent to the legal path |
|---|---|---|---|---|---|
| A (tuning; not a measure) | 36 / 36 | 28 / 28 | 6 / 6 | 0 | 0 |
| **B (held out, run once)** | **36 / 36** | **24 / 28** | **6 / 6** | **0** | 4 |

The four held-out misses are all in the safe direction (they cost a full answer; they do not give an answer without law): "For how many days was he sent to judicial custody?", "Did the police seize the motorcycle, and where from?", "What is the registration number of the motorcycle?", "what are the charges". No question about drafting was taken for a request (0 of 6). The rules were NOT changed after the held-out run (`heldout_run1.txt`).

What the set cannot show: the questions and their labels are Claude's; the plan's lawyer-labelled sample of 40 has not been done; real use will bring phrasings the set lacks. The `shadow` mode exists for that: it logs the route it would take (counts and rule ids, never text) and changes nothing.

## The quick answer from the documents (model stubbed)
- **What reaches the model:** the whole matter when its read text is 15,000 characters or less (the five readable test documents of 2026-11-19 together come to about 10,200; a real chargesheet with witness statements may well be longer), else the 8 best passages up to 10,000 characters. The documents stay fenced (every line starts with "| "). The prompt's rules: documents only; cite every statement; quote numbers and sections word for word; a title, heading or "report under section ..." is not a charge; no law, no case, no advice; "The documents given do not show ..."; `NEEDS_LAW` alone when the question needs law.
- **Code checks after the answer** (into the documents box; never edits the answer): every quotation looked for on the cited page (as before); a section number the answer names that is not in the passages; a case name not in the passages; a sentence that reads as a statement of law. Seeded faults in the test are caught (a section 411 not in the file, "Arnesh Kumar v. State of Bihar", "robbery is punishable with ten years").
- **"Explain these sections"** is offered only for section numbers that code finds in the passages handed over, only from sentences about charges, never the section a report is "filed under", never from a sentence that names two Acts, at most 8.
- Tests: `test_matter_routing.py` (switch, frozen set, hand cases, prompt, checks, the engine: one call and no research-note dressing; `NEEDS_LAW` → the legal path; no route → exactly today's path), `test_api_matter_routing.py` (off / shadow / on, whole matter handed over, label and offers in the view, the three intents and a refused one, the draft notice uses no quota, no routing without documents, without a matter, or with `MATTER_FILES` off). Browser: `recourse-web` `e2e/matter_routing.spec.ts` (the label, the coverage line, the two buttons, the Explain tap, a legal question, the drafting notice and its last line, the count of answers left), unit tests in `tests/matter_files.test.tsx`.

## Cost (ESTIMATED, not measured)
A file answer is one Sonnet call with about 3,000 to 5,000 input tokens and a short reply; at the price table in `cost_log.py` (Sonnet $2 / $10 per million) and `ANSWER_EFFORT=medium` (thinking is paid as output) that is **about Rs 1 to 3.5**, against about Rs 6 to 10 estimated for a lawyer research note (FOLLOW_UPS 2em). The `COST_QUESTION` line on staging gives the real figure. **It still counts as one lawyer answer against the plan** (decision 3 of the plan is open: a cheaper unit such as `file_question`).

## Not built (needs its own go)
- The visible mode switch beside the question box (plan decision 1): instead every routed answer carries its label and a one-tap other way.
- R3, the sections the file charges fetched as law for the legal path (the BNSS 193 trap on the LEGAL path is still open: the first real test's answer could still mis-read the title line when the question goes to the legal path); R2 (no documents for law-only questions, facts fetched on purpose, the summary line); R4, R5; a lower effort for the file call.
- The drafting itself (`DRAFTING_PLAN.md` section 10; NOT approved).
