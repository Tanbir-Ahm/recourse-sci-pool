# Matter Workspace W1 + W2: law on hand and answer sizes (built 2026-11-20)

**Owner's go (2026-11-20):** "Go ahead with W1 and W2 together", after the plan `MATTER_WORKSPACE_PLAN.md` (drafted the same day from his staging test of "explain the sections in a clear manner", which never fetched BNS 309(4), 115(2) or 3(5) and cost Rs 22.16). Built on the Recourse branch `register-hooks-and-overlay` and in `recourse-web` `main`; NOT on Recourse `main`; nothing deployed; both switches default OFF. **Nothing here has been tried with the answer model** (no Anthropic key in the sandbox); the question sets are Claude's, not a lawyer's; no lawyer has read an answer. No hallucination rate has been measured.

## What was built
**Switches (default off; nothing in the site changes while they are unset; they act only in a matter that holds documents, with `MATTER_FILES` on):**
- `LAW_ON_HAND=on`: a question that asks to explain named or charged sections is answered by the new **explain** size.
- `MATTER_DEPTH=off|shadow|on`: chooses among all sizes (file, explain, standard, research, draft, smalltalk); unsure means Standard. `shadow` logs the size it would choose and changes nothing. `MATTER_ROUTING` still works alone as before (file path or the full path). A tapped button decides by itself.

**W1, law on hand** (`law_on_hand.py`, `matter_files.charged_refs`, `api/matter_docs.charged_pins`, `chat_assistant._answer_explain`):
- The sections to explain come **by code**: the ones the person's own message names (`refs_in_text`: an Act word next to the number, or a pinned section with the same number), else the matter's pins: the code-checked list the last answer gave (so the typed follow-up works like the button), else the sections the documents give as charged **on a labelled line** ("Sections: ...", "Offences charged: ..."; the section a report is filed under is never taken for a charge; read on the real chargesheet PDF: `['BNS 309(4)', 'BNS 115(2)', 'BNS 3(5)']`).
- The text of each section comes from our own library (BNS and BNSS) or the Act shelf (BSA, when `ACT_SHELF` is on), cut to the cited sub-section when the section is over 3,500 characters (BNS 3(5): 270 characters; BNS 309 and 115 whole, because the definition sits above the punishment); the BNSS First Schedule row is added for a BNS offence section (309(4), 115(2); none for 3(5) or a BNSS section). A section the library lacks is reported "its text is not in our library" and never described.
- One small call (Sonnet, thinking `low`, a 5,000-token cap) writes at most about 220 words, quoting the words each point comes from; **code then removes** any sentence that names a section not on hand, quotes words that are not in the text, or gives a figure found in no source (the text, the Schedule rows, the documents); it never regenerates. A section number the documents name may stand only in a sentence that cites the document.
- The page shows the sections word for word and the Schedule table (built by code; "no person has read it yet"), and the PDF/Word download carries them.

**W2, sizes** (`matter_depth.py`, `depth_ctx.py`, gates in `chat_assistant.py`, `sci_search_tier.py`, `act_detect.py`, `excerpt_anchors.py`, `api/chat_service.py`):
- A rules-only planner (below). **Standard** = the statute retrieval of the full path, but: no scope check, no AI Act guess (the free word pass stays), no wider search, no judgments of the library, no verbatim excerpts, no pilot list, thinking `low`, a 5,000-token cap, its own short template (the Hard rules block carried over word for word; a test asserts it), no research-note dressing (Bottom line, table of authorities, ask checklist). The pinned sections are handed over as `pinned`. **No second answer:** an untraceable section number is removed with its sentence, a missing Act name or companion section is added by code, a classification that differs from our table gets our table's words (`STANDARD_FIXED_BY_CODE` log line). Research is today's path, byte-for-byte (a test shows the same untraceable number still gets its second answer there).
- **Small talk** ("thanks", "hello", "ok") gets a fixed line and no model call; a **draft request** keeps its notice; neither uses an answer of the day.
- Every answer carries its size label; under a Quick or Standard answer a **Go deeper** tap re-asks the stored question as Research (the server writes the words; refused with 409 when not offered).
- **`PROMPT_SIZES` log line** (counts only): the prompt's characters by block (template, question, retrieved material, pilot and documents, conflict clause), so that the next trim is chosen from numbers (the log of 2026-11-20 could not say what the 19,600 input tokens were).

## The planner, measured (rules only; `measure.py`)
Question set frozen before any planner code (`planner_set.json`, commit `8278a36`: 92 questions per half, written by Claude, not a lawyer; the router set of 2026-11-20 relabelled by size plus 22 new explain and research questions per half). Harness rule declared before the first run: the test matter's documents carry a labelled "Sections:" line, so for the router-derived items the planner is told pins are available; for the new items the item's own flag is used.

| Run | As frozen | Law or draft sent to a no-law size | Notes |
|---|---|---|---|
| Half A (rules written on it) | 92 of 92 | 0 | not a measure |
| **Half B, held out, run once** (`heldout_run1.txt`) | **86 of 92** | **0** | 4 file lookups the router sends up (money, not danger); B08 "Which court is the chargesheet filed in?" went to explain; BN16 "Write a detailed legal research memo on default bail" was read as a request to draft |
| Set C, fresh, written after B and before the two changes (`C_before_fix.txt`) | 35 of 40 | 1 | the same two faults again, a lookup sent up, and C34 |
| After two declared changes: "which court" counts only as "which court tries / can try / is competent to try"; a research memo is research, not a draft | A 92 of 92; B 88 of 92 (no longer held out); **C 38 of 40** (`C_after_fix.txt`, `B_after_fix.txt`) | 0 on A and B; 1 on C | the remaining C misses: C02 a lookup sent up (the router); C34 "Is anything missing from the chargesheet?" went to the file path (the router; that path answers NEEDS_LAW when it needs law) |

What this does not show: the questions and labels are Claude's; real phrasings will differ; Hinglish is thin ("in sections ko samjhao" stays Standard); the rules were not changed after C.

## What the explain turn would have cost (arithmetic, not a measurement)
The real explain prompt for the real synthetic chargesheet is 12,604 characters, about 3,150 tokens (law on hand 4,879 characters, documents 6,114). At the price table in `cost_log.py` and USD 1 = Rs 96.5: **Rs 0.95 to 1.19 on Sonnet 5** (350 to 600 output tokens), Rs 0.47 to 0.59 on Haiku 4.5, against **Rs 22.16** for the turn that failed: about twenty times less. The only measured part is the neighbouring file answer of the same log (Rs 0.88, 3,338 tokens in, 248 out). Whether `low` effort really cuts the thinking, and what a Standard answer costs, only staging shows.

## What was NOT built (the plan's W1 and W2 rows; each needs its own go)
- **Shorter** (a reshaping turn: W3), the one-line strip and the matter home (W5), the matter sheet (W4), section cards (W6), IPC and CrPC on the shelf (W7).
- Skipping the follow-up **rewrite** (a Haiku call, Rs 0.08; it runs before the size is known), prompt caching, the answer-length ask ("in detail" lengthens a Standard answer through its template line only).
- A Standard answer hands over a whole long section (BNS 3, 4,744 characters) when it is pinned; only the explain size cuts to the sub-section.
- The quota unit: an explain, Standard or Research answer each count as one lawyer answer; thanks and drafts count none (D3 of the plan is open).

## Known limits
- The law on hand is **our copy** of BNS and BNSS (checked against India Code on 2026-10-17: 99% identical, with known losses in other sections); the Schedule rows are `machine_extracted` from one source and no person has read them. Matters under the IPC and CrPC have no law on hand (the library has neither): the answer says the text is not on hand.
- The code checks count words and numbers: they cannot tell that a quotation is used fairly or that an explanation is right. Pins come only from the last answer's list, labelled lines of the documents, or the person's own words.
- Staging only, like the documents themselves, until the privacy and consent text (gate G1) exists.

## Test totals (2026-11-20, after the last commit)
Recourse `run_tests.py`: **163 of 163 pass** (the three new files `test_law_on_hand.py`, `test_matter_depth.py`, `test_api_matter_depth.py` included; the routing, documents and answer-view tests that touch the changed code pass unchanged except the Explain button's words, updated on purpose). `recourse-web`: `tsc` clean, **148 unit tests pass**, **83 browser tests pass, 4 skipped** (the whole suite, desktop and phone, axe included). The browser tests run the real law on hand (the library's own text) with a stub for the model's words.
