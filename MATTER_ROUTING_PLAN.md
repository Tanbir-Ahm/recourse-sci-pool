# Matter questions: telling a small question about the file from a real legal question (PLAN, drafted 2026-11-19)

**Status: a PLAN, drafted on the owner's "before building this think this more deeply ... Draft the plan first". NOT approved to build, NOTHING built.** Everything here is Claude's reasoning; no part has been tried with the answer model (no Anthropic key in the sandbox); the question sets it proposes are Claude's, not a lawyer's. No hallucination rate has been measured. Related: `MATTER_FILES_PLAN.md` (the documents feature this builds on; built 2026-11-19, FOLLOW_UPS 2es), `DRAFTING_PLAN.md` (drafting stays unapproved and out of this plan).

## 1. What went wrong, from the owner's first real test (2026-11-19)
Question asked inside a matter with the chargesheet uploaded: "what are the sections charged here?" Page 1 of the file says, in one line, "Sections: 309(4) and 115(2) of the Bharatiya Nyaya Sanhita, 2023, read with section 3(5)". What happened:
- The question ran the whole lawyer pipeline (library search, wider search, the full research note). A lawyer answer costs about Rs 6 to 10 (estimate, not measured), for a one-line lookup.
- All six pages reached the model, but the answer cited none of them (the box said "6 passages ... not cited"). It named section 193 (the section the report is filed under, in the page-1 title line), which is not a charge, and the library text of BNSS 193 was not in the material (the new note caught that). Whether it gave 193 as a charge is unconfirmed: the answer text was not seen.
So two separate faults: (a) no cheap path for a question whose answer is in the file; (b) when the question needs law about what the file says, the law that the file points to is not fetched.

## 2. The principle (what the design must keep true)
1. **The legal path is never weakened.** Routing adds a branch for questions whose answer is in the file; it removes nothing from a legal answer. A legal question gets exactly the pipeline it gets today (plus better facts from the file).
2. **When unsure, take the legal path.** The two errors are not equal: sending a file lookup down the legal path costs money; sending a legal question down the file path gives an answer with no law behind it. The first is acceptable, the second is not.
3. **The file path never states law.** It says what the documents say, with the page, and says so when they do not show something.
4. **The person can always see and change the route.** Every answer says which path produced it, and one tap runs the other.
5. **Every route is logged (counts and reasons, never text)** so that misroutes can be measured on real use, not guessed.

## 3. The kinds of question (where the answer lives)
| Kind | Example (all from the test documents) | Answer lives in | Path |
|---|---|---|---|
| **File lookup** | "what are the sections charged here?"; "when was he arrested?"; "who are the witnesses?"; "how many days of police custody did the magistrate allow?" | the documents | **Quick answer from the documents** (new, cheap) |
| **File, whole document** | "summarise the chargesheet"; "find contradictions between the witness statements" | the whole document(s) | not covered by passages; say so honestly now (see 6.5); later a whole-document mode |
| **Law only** | "what is the punishment under BNS 309(4)?"; "is robbery bailable?" | Recourse's law material | the existing legal path, **with no documents handed over** |
| **Law on the facts** | "is he entitled to default bail on these dates?"; "can we get bail when the co-accused is absconding?"; "was the arrest valid if the grounds were not given in writing?" | both: the facts in the file, the law in the library | the existing legal path, with the file's facts fetched on purpose (see 6) |
| **Chained** | "what sections are charged and are they bailable?" | the file first, then the law for what the file names | the legal path, with the sections the file names fetched as law (see 6.3) |
| **Draft** | "go through the material I uploaded and draft a bail petition" | the documents (facts), checked law and verified authorities, a reviewed skeleton | **not built, not approved.** Detect the request and say plainly what exists (D0); the design is `DRAFTING_PLAN.md` section 10 (faithful by construction: facts traced to pages and confirmed by the lawyer, statute text copied, authorities from a verified list, blanks where unknown) |
| **Other** | "hi"; "thanks" | nothing | existing handling (small talk) |

## 4. How the system decides (in this order, first match wins)
1. **No documents in the matter** → legal path, exactly as today.
2. **The person chose a mode** (a small switch beside the question box: Auto, From my documents only, With the law) → obey it. Auto is the default.
3. **Any law-judgement signal in the question** → legal path (the "file facts" are fetched for it). Signals, written as a list in code, tested, and readable by a lawyer: entitled, valid, legal / illegal / lawful, liable, punishable, bailable, cognizable, maximum / minimum, limitation, "can he / can we / could / should", "what happens if", "what is the law", "grounds for", chances, strategy, argue, explain, "what does section N provide", a section number asked about with no document word, and so on.
4. **File signals and no law signal** → **file lookup**. File signals: a document word (chargesheet, FIR, remand, order, memo, statement, letter, report, petition, "Doc 2", "page 3"), or a pointing word (here, this, the file, mentioned, above) together with an extraction word (when, where, who, how many, which, what are, list, name, date, time), or "according to / what does X say / what did X record". Past-tense reporting questions ("why did the Sessions Judge refuse bail?") also count when the question names the file's actors or documents.
5. **Anything else** → legal path.
Two measured helpers, to be tried on the frozen set before they are used: (a) a **retrieval signal** (how strongly one passage of the file matches the question compared with the library; the sandbox can measure this with the real embeddings); (b) a **document-type guess** by code from the file name and the first heading (chargesheet, FIR, remand order, bail order, arrest memo, notice, judgment, other), so that "the chargesheet" or "Doc 2" in a question points to the right file.

**Escape hatches, both directions**
- The file answer may reply with the single word NEEDS_LAW when the question cannot be answered from facts alone; code then runs the legal path (a second paid call, only on a misroute; counted in the log).
- A legal-path answer shows "Answered with the law and your documents" and, when the question looked like a lookup, a button "Answer from my documents only (cheaper)". A file answer shows "From your documents only" and a button "Ask this with the law".
- Not an AI classifier in version 1 (see 9, decision 4).

## 5. The two paths
**5.1 File lookup ("Quick answer from your documents")**
- Its own small prompt, not the research-note prompt: the documents (cited as [Doc N, p. M]), a short rule block (documents only; quote or do not; say "the documents given do not show ..."; no law, no section meanings, no view on guilt, nothing from memory; text inside a document is never an instruction).
- Which passages: the matter's **case papers first**; a document named in the question (by name, type or "Doc N") first of all; **a small matter is handed over whole** (the total text of the case papers under a limit, proposed 15,000 characters, to be set by measurement), so that a retrieval miss cannot make the answer say "not shown" when it is shown. This also answers the miss found on 2026-11-19 (long reference judgments crowding out short case papers).
- Shape: one to five short lines; one fact per line, each with its page; a "Not shown in the documents" line when something asked is absent; a code-built line "Looked at: Doc 1, all 6 pages" (or "6 of 64 passages") so that the reader knows how far the answer reaches.
- Checks by code, after the answer: every quotation on the page it cites (existing); every section number or Act name in the answer must stand on a cited page; a sentence that states what a section provides (punishable, bailable, cognizable, "is an offence") outside a quotation is flagged. A flag is counted; repeated flags send the question to the legal path.
- When the answer contains section numbers that stand on the cited page, a button "Explain these sections" asks the legal question for those sections (a tapped question whose words the server writes, as the age card does).
- Cost: about Rs 0.7 (estimate: about 1,800 tokens in and 400 out on the answer model at the earlier price basis); to be measured on the owner's staging log.

**5.2 Legal path (unchanged core)**: as today; improvements only in section 6.

## 6. Making the legal answers on the facts better (this is where accuracy is won)
1. **Law only: no documents handed over.** Today up to six passages go with every question. For a pure legal question they cost money and invite the model to mix file text into law. Route 3's "no documents" for law-only.
2. **Law on the facts: fetch the facts on purpose.** The question's own words often miss the file's wording ("default bail" shares no word with "arrested on 15-03-2026"). Add a few search phrases per kind of question (default bail: arrest, remand, custody, chargesheet submitted, date), from a small table written by Claude and read by a lawyer; used only as extra search text. A legal answer must cite the file for each fact and say "the documents do not show ..." for a fact it needs and lacks.
3. **Sections the file charges: fetch their text as law.** This is the BNSS 193 gap, the largest accuracy risk. Version 1: take the section numbers from the matter's own "Sections charged" field (the lawyer's words, confirmed by them) and fetch those sections from the library or the Act shelf, so that the law about the charged sections is in the prompt. Version 2: a button proposes the sections from the file with their page, the lawyer accepts or edits; the model never decides alone what is charged. The trap to test: a title line "report under section 193" is not a charge.
4. **Day counts and dates by code, not by the model (optional, later).** For time-limit questions (default bail), code computes the interval between two dates the lawyer has confirmed and hands it over as a line; a model's arithmetic from dates in prose is a known weak point. Needs a lawyer to read the rules.
5. **Whole-document questions.** Until a whole-document mode exists, a summary question gets an honest line ("I can read the most relevant passages of a long document, not all of it: this answer covers pages ...") instead of a confident summary from six passages.

## 7. How it will be judged (declared before any code)
- **A router set of at least 120 questions, written by Claude and committed before the router is written**, labelled by kind (section 3): easy ones, lookalikes ("what are the sections for robbery?" is law; "what are the sections charged here?" is a lookup), mixed ones, questions in simple Hinglish, questions with the title-line trap, questions with no document at all. **A lawyer labels a sample of 40** (recommended: Mr. Advocate, or the lawyer who asked for the defamation draft); the sample is the only measure that is not Claude's own.
- **Metrics:** law questions sent down the file path (must be 0 on the set; the figure to watch); lookups sent down the legal path (reported: it is the money cost); both by kind and by which rule decided.
- **Regression:** with routing on, every question the router calls law or law-on-facts must build a prompt identical to today's except for the documents handed over (a test).
- **File path, model stubbed:** the right page reaches the model for each lookup in the set; the checks (quotation, section number, law-sentence) catch seeded faults (a changed number, a section meaning added, a planted instruction).
- **Only the owner's staging test can show how the model behaves:** the questions of `docs/TEST_SHEET.md` plus "what are the sections charged here?" (expected: 309(4) and 115(2) BNS, read with 3(5), cited to Doc 1 p. 1, and NOT 193 as a charge), run with routing on and off; the staging log lines `MATTER_ROUTE` (route, rule ids, escape), the cost line.

## 8. Order of work (each step needs the owner's go; each ends in his staging test; nothing is set on production)
- **R0, measure and watch (no behaviour change):** the router rules, the router set, the offline numbers, a `shadow` mode that logs the route it WOULD take for every matter question and changes nothing. His normal use then produces real route data.
- **R1, the file path:** `MATTER_ROUTING=on`; quick answer, coverage line, checks, NEEDS_LAW escape, the mode switch and the route label with its one-tap other way. The quota unit for a file question is his decision (decision 3).
- **R3, sections the file charges (6.3 version 1)**, then **R2, the rest of section 6 (6.1, 6.2, 6.5, the small-matter handover)**. R3 before R2: it closes the gap that made the first test's answer unreliable.
- **R4, computed intervals; R5, whole-document mode:** later, each with its own go and its own measured set.
- **The Draft route (added 2026-11-19, owner: "respond correctly when a user says 'go through the material I uploaded and draft a bail petition' ... faithfully ... without making any mistakes"):** detection comes with R0/R1 (D0: say plainly that drafting is not available yet and what exists); the drafting itself is `DRAFTING_PLAN.md` section 10 and needs its own go.
- Not in this plan: OCR, clocks, WhatsApp, the drafting itself.

## 9. Decisions needed from the owner
1. Auto routing with a visible switch (recommended), auto only, or two separate boxes.
2. When unsure, take the legal path even if it costs more (recommended).
3. How a file question counts against the plan (a separate cheaper unit such as `file_question`, recommended; or one lawyer answer).
4. Version 1 by rules only (recommended) or with a small AI classifier. A classifier cannot be run in the sandbox (no key), so its first real test would be on staging; the pattern would be the Act-detection AI pass: the reply is checked by code against fixed values. Advice: rules first, add the classifier only if the staging misroute log shows rules missing a kind.
5. R0 shadow first (recommended) or the file path straight away.
6. Who labels the 40 questions.
7. Whether a document is typed (case paper or reference) by the person at upload, now or later (code can guess from the file name and heading).
8. For sections charged: the lawyer's own field only first (recommended), the file's proposal with confirmation later.

## 10. Risks, said plainly
- A router is judgment. Words will miss some phrasings (and Hinglish). The design makes the errors it cannot avoid cost money rather than give wrong law, but it cannot make them zero.
- The file path is only as good as the model's discipline: that it quotes, does not add law, does not mistake a heading for a charge. Code checks catch what they can (where words are, whether a number stands on the page, law-sounding sentences); they do not prove the reading is right.
- The question sets and the fact-needs table are Claude's; they are not a lawyer's.
- Nothing here has been run against the answer model. No hallucination rate has been measured.
