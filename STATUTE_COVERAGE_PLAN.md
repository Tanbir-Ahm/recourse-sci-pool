# Acts and statutes that are not in the library: the plan (PROPOSED 2026-10-16, awaiting the owner's choice)

Asked by the owner on 2026-10-16, after the first production answer to an opened question (TADA appeal, FOLLOW_UPS 2ae): "What to do with the legal statutes and the acts like the PC act which are not in our arsenal today? ... suggest the best way forward." Nothing below is built yet except what is marked DONE. Nothing here has been measured with a live model; no rate of wrong answers exists for the answer-writing step.

## 1. The problem in one paragraph
The library holds full text only for the BNS and the BNSS, plus 19 sections of the Negotiable Instruments Act and 10 of the IT Act (statute chunks, counted 2026-10-16). Cheque bounce, domestic violence (PWDVA, 11 of 30-plus sections) and NDPS were added as small, hand-built packs (curated sections and judgments, every line read by a person; `ndps_doctrine_map.py` is the template). The Prevention of Corruption Act, TADA, POCSO, UAPA, PMLA and every civil, tax, family, service and company law have no text on the shelf. With the topic bar closed such a question was refused; with `SCOPE_GATE=open` the model answers from the nearest library material and from court passages of the wider search. The first production answer showed the risk: the nearest material was a BNSS section (420) that does not fit a TADA conviction, and the answer's account of the first case's facts was not in the passages it had been given. A prompt cannot supply text that is not there; the fix is text, tiers and honest labels.

## 2. What exists that the plan reuses (checked 2026-10-16)
- The loader pattern: `build_ni_act_statute_chunks.py` (Recourse) pulls sections from India Code's public discovery API (`indiacode.gov.in/server/api/discover/search/objects`), one record per section with the current in-force text and inline amendment brackets, into the chunk shape the embedder already reads. Its docstring records two traps: a PDF of the Act was outdated (missing section 143A), and India Code's own database carried typos in section 118 that had to be caught by cross-checking Indian Kanoon. So official text is the best source, and still needs a machine check and a person's sample.
- The verbatim-excerpt method of the anchors (`sci_anchors.py verify`, status `machine_checked` until Mr. Advocate confirms).
- The wider Supreme Court search (feed mode): it already returns court passages on TADA and corruption-law questions.
- The register (overruled judgments) and its notes, which work for any case named in an answer.
- The exam machinery (`register_exam/situation`, the trap exam runner) for a before-and-after measurement.
- Limits: this sandbox cannot reach India Code (HTTP 403 on both `indiacode.nic.in` and `indiacode.gov.in`, a network-policy denial, 2026-10-16) and has no model or embedding key; so the fetch needs the host allowed in the environment's network settings (or the owner's PC) and the embedding step needs the owner's key.

## 3. The plan, in order (each step useful on its own; none is a rebuild of the site)
**Step 0, DONE 2026-10-16 (Recourse `087b730`, branch only):** the "not checked" box no longer calls the overruling case unchecked; the scope note for opened topics tells the model not to present a BNS or BNSS section as the governing provision, the offence, the procedure or the route of appeal for a matter under another Act unless the material shows it applies. Not measured live.

**Step 1: a signpost for every Act we lack (no model risk, one session, one page for Mr. Advocate).** An Act Directory of about 30 Acts: full name and year, aliases ("PC Act", "TADA"), status (in force, repealed, lapsed, with the date), where appeals go in one line, the official link, and "pack status" (none, partial, full). Code, not the model, spots the Act in the question (word-boundary alias match) and the page shows a fixed box: "This question is governed by the X Act. Recourse does not hold its text. Official text: [link]." The prompt gets the same fact. `SCOPE_OPEN` gains an `act` field, so demand is counted by Act. Acceptance: right Act found for 20 plain-words questions per Act listed; no false detection on the 24 situation-exam questions and a control set of BNS/BNSS questions. Mr. Advocate checks the table once (statuses and forums are legal statements; Claude must not invent them).

**Step 2: real text for the few Acts asked about most.** A manifest-driven loader (generalising the NI builder) loads the full text of short Acts from India Code; first batch proposed: Prevention of Corruption Act 1988 (as amended 2018), POCSO 2012, UAPA 1967, PMLA 2002, SC/ST (Prevention of Atrocities) Act 1989; TADA only as a Directory entry (lapsed; legacy appeals). Checks by machine: section list complete against the Act's table of contents, no empty or cut-off section, amendment brackets kept. Label on every use: "official text loaded <date>, not yet read by our reviewer"; Mr. Advocate ticks about ten sections per Act (chosen by how often retrieval returns them) and those become `verified`. The search looks only on the governing Act's shelf (plus BNS/BNSS where the Act itself points to them), so a PC Act question cannot be answered from a loosely related BNSS section. The classifier paragraph, the Act-name and section checks (built for BNS/BNSS and untested for other Acts) and the tests are extended per Act. Needs: the host allowed or the owner's PC for the fetch; the owner's key for the embedding (a few rupees).

**Step 3: word-for-word court passages for the questions asked most.** Same method as the speedy-trial anchors: verbatim from the court's own PDF, machine-verified, confirmed by Mr. Advocate before the "not yet confirmed" wording goes. Chosen by evidence (how often a doctrine is the point of real questions; how often the Supreme Court cites a section), not by taste.

**Step 4: let real questions set the order.** After the site is shared, the `SCOPE_OPEN` log shows what people ask; load the next Acts in that order. Monthly: refresh statute text (amendments) and re-run the checks. Measure with an "uncovered-Acts exam": about 10 questions per Act and 10 civil/tax; automatic fails (a BNS/BNSS section cited as governing for another Act; a section number of an Act not in the material; a case named that is not in the material) plus Mr. Advocate's reading; compare gate closed, gate open as today, gate open with Step 0, with Step 1, with Step 2.

## 4. What not to do
- Do not load all 800-plus central Acts now: no demand evidence, and more text means more nearest-neighbour mistakes (the NALSA link and BNSS 420 are the same kind of slip) unless the search is scoped by Act.
- Do not let the model name sections of an Act we lack from memory; do not rely on "be careful" prompts as the main control.
- Do not word anything about an Act's status or appeal route that a lawyer has not read (the Directory is the place for it, and Mr. Advocate checks it).
- Do not call any of this accurate or safe: no rate of wrong answers has been measured for opened topics.

## 5. Decisions needed from the owner
1. Start Step 1 (the Directory and detection)? Claude's recommendation: yes, first.
2. The first five Acts for Step 2 (default: PC Act, POCSO, UAPA, PMLA, SC/ST Act).
3. Network: allow `indiacode.gov.in` (and nothing else) in the environment's Network access settings so the loader can run here, or run it on the owner's PC.
4. Mr. Advocate: one page for the Directory (30 rows), then ten sections per Act.

## 6. Related gap (not part of the plan, noted so it is not lost)
The old codes (IPC 1860 and CrPC 1973) are not in the library as text; the concordance maps their numbers to the BNS and BNSS. Proceedings for offences before 1 July 2024 still run under the old codes, so an appeal from an old conviction is a place where a BNSS answer can be anachronistic (the TADA answer was one).
