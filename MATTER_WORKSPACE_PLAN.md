# Matter Workspace: a "Projects"-style matter with the law on hand (PLAN, drafted 2026-11-20)

**Status (2026-11-20, later): W1 and W2 BUILT on the owner's "Go ahead with W1 and W2 together" (FOLLOW_UPS 2ex; `review_results/2026-11-20_matter_depth/RESULTS.md`; Recourse branch and `recourse-web` `main`, nothing deployed, switches `LAW_ON_HAND` and `MATTER_DEPTH` default off). W3 to W8 are NOT built and NOT approved; decisions D2 to D10 are still open (D1 taken as recommended on his go; D3 the quota unit, D5 the section cards and D7 IPC/CrPC matter next).** The rest of this file is the plan as drafted before the build, kept unchanged: Status: a PLAN. NOT approved, NOTHING built.** Drafted on the owner's message of 2026-11-20, after his staging test of a follow-up ("explain the sections in a clear manner") inside a matter: *"This is not right. What I need is a Projects for Claude type simulator, based on real grounding of laws and sections. This costing too much, and unnecessary details even for small questions. Be innovative and strategic. Think from all perspectives, and draft the plan."*
Everything here is Claude's reasoning from ONE logged turn (staging-api, 14:41 to 14:45 UTC, 20 Nov 2026), the downloaded answer, the repository and the code. Nothing was tried with the answer model (no Anthropic key in the sandbox); the question sets it proposes are Claude's, not a lawyer's; its cost figures are arithmetic on the owner's own log and on the price table in `cost_log.py`, not measurements of the new design. **No hallucination rate has been measured.**
It folds in R2 to R5 of `MATTER_ROUTING_PLAN.md` and P2 to P4 of `MATTER_FILES_PLAN.md`. It leaves `DRAFTING_PLAN.md` (not approved), `WHATSAPP_PLAN.md` (held), `SUPPORT_AND_FIT_PLAN.md` (held) and the deferred BNS/BNSS repair alone, and says where they touch it.

## In plain terms
1. **What failed.** You asked Recourse to explain the sections charged. It never fetched them. The answer says so itself: "the text of Sections 309(4), 115(2) and 3(5) is not in the material reviewed". It then wrote about bail law, listed eight unrelated cases, ran twice, and cost **Rs 22.16** (5,348 words in the download, of which 839 were the answer).
2. **Why.** The follow-up was sent down the full research path; the sections your first answer had named were lost between the two turns; and that path does everything for every question: scope checks, wider case search, long thinking, and a complete second answer when one section number could not be traced.
3. **What you want**, as I read it: a matter you set up once (documents, instructions), then chat freely; the answer is as long as the question deserves; it remembers the conversation; and every statement of law stands on text we hold and can show. Claude Projects has the first three. Nothing has the fourth for Indian criminal law; that is where Recourse can be better.
4. **The idea.** Three shelves in every matter: **Your file** (read once into a short, checkable sheet), **Law on hand** (the sections your file charges or cites, word for word, with punishment, cognizable, bailable and court from our Schedule table, fetched by code, not recalled by a model), and **Research** (judgments; only on a tap, costed). Every question gets one of three sizes: **Quick** (a fact from the file, or an explanation of named sections), **Standard** (apply the law on hand to the facts), **Research** (today's full note).
5. **What it would have cost.** The explain turn becomes about Rs 0.5 to 1.1 [Likely: arithmetic from a measured Rs 0.88 file answer, not a measurement of this design], about twenty times less, with the sections shown word for word.
6. **The strategic piece.** "Section cards": the common sections compiled once, shared by every user, checked by code and read by a lawyer once. After that, explaining a section is a lookup. This is the one thing a general assistant cannot match.
7. **The uncomfortable parts** (section 9): "legal path when unsure" was my build of your instruction and it is the wrong default once a cheaper safe path exists; the library has **no IPC or CrPC text**, so any matter under the old codes has no law on hand; and the section cards would quote BNS/BNSS text whose known losses are not yet repaired.
8. **Order.** W1 (law on hand and the explain turn) fixes your turn: the right sections, a short answer, about Rs 1; W2 (sizes) gives every other question the right size, because "can he get bail now?" still runs the full note until then; W3 to W6 are the Projects feel; W7 (IPC/CrPC) and W8 (a lawyer reads 20 answers) decide whether it is ready to charge for. Each step needs your go and ends in your staging test.

---

## 1. What happened (the evidence)

**The turn.** Inside a matter with one document (the synthetic chargesheet, 6 pages), the first question "what are the sections charged here?" was routed to the documents-only path: one Sonnet call, **Rs 0.88**, 3,338 tokens in, 248 out, its quotation found on the page, "Explain" offered for three sections. Then he typed "explain the sections in a clear manner".

**Where the Rs 22.16 went** (from `COST_CALL` / `COST_QUESTION` lines; USD 1 = Rs 96.5; Sonnet 5 at $2 in / $10 out per million):

| Item | Rs | Note |
|---|---|---|
| Answer call | 11.33 | 19,593 tokens in, 7,821 out |
| Second answer call ("recheck") | 9.50 | 19,723 in, 5,901 out; started because ONE section number (103) was not in the material; the first draft is not logged |
| Scope check, twice (Haiku) | 0.90 | the second run because the first invented "BNS 103, the successor to IPC 302 (murder)" as the charged section |
| AI Act detection (Haiku) | 0.27 | found no Act |
| Rewrite of the follow-up (Haiku) | 0.08 | its result was thrown away by the number guard |
| Embeddings and re-ranking | 0.08 | the wider search of 48 judgments |
| **Total** | **22.16** | |

By kind of token: output **Rs 13.24** (60%), input **Rs 7.59** (34%), side calls Rs 1.33. The visible answer was 839 words, about 1,200 tokens, so of the 13,722 output tokens across the two calls about 11,400 were the model thinking, about **Rs 11** [Likely: the log does not split thinking from text]. A research note that costs Rs 8 to 13 on its own (the owner's earlier lawyer runs) became Rs 22 through the second call.

**Why the sections never arrived** (each link read from the code; the first two also visible in the log):
1. The typed question was classed **law**: "explain" is on the law-signal list (`MATTER_ROUTE ... law_signals: ["explain"]`). So was the button: `ROUTE_INTENTS["explain_sections"] = "law"`. **Even the "Explain BNS 309(4), BNS 115(2)" button runs a full research note**; I said "a full research answer" in my last message and did not say what that costs. I should have.
2. The earlier answer stored **no sections**: a documents-only answer has `matches: []`, and `carry_forward.refs_from_turns` reads only `matches`. The log says `carry: []`.
3. The follow-up rewrite (which, I infer, held 309(4) and 115(2) taken from our own answer) was **dropped by the number guard** (`dropped_guard:number_not_in_person_messages`), which exists so our words never pass as the person's. So the engine's question held no section number. [Likely: the rewrite itself is not logged.]
4. With nothing to find, retrieval returned bail sections (BNSS 478, 234, 483, 480, 2). [Likely: the matter's own fields said "bail application before a Court of Session", which the answer repeats as "Facts assumed"; I have not read the matter's stored fields.]
5. Then everything a research question gets: two scope checks, AI Act detection, a wider search whose eight "fed" cases (Moti Ram, Kartar Singh, Ram Govind Upadhyay on quashing...) have nothing to do with explaining three sections, the full lawyer-note template, thinking at "medium" effort, and the retry.
6. The page itself noticed: "The answer names section 63 which appears in your documents but whose text was not among the law given to it". The system knew the law was missing and answered anyway.

**What worked** (keep it): the first turn (Rs 0.88, right route, quote found on the page); the Explain list was correct (309(4), 115(2), 3(5), not the 193 the report is filed under); the answer was honest about the gap rather than inventing the text.

**What I got wrong in my own work.** I measured the router on whether it picked the path, never on what the person then received or paid. I put "explain" on the law list because "explain a section" is a legal question, which is true and was exactly the problem: a legal question about three named sections is a small question. I listed R3 (fetch the charged sections as law) as "not built" and framed it as a risk on the legal path; it was the whole failure.

**Not seen** (so some links are inference): the discarded first draft and where "103" came from; the rewrite's text; the breakdown of the 19.6k input tokens by block (the log has no such line); the matter's stored fields.

## 2. What "a Projects simulator with real law" means here

| | Claude Projects | Recourse matter today | Target |
|---|---|---|---|
| Instructions kept per project | yes | yes (P0) | yes |
| Files kept per project | yes | yes (P1; 10 files, 10 MB) | yes, **read once into a checkable sheet** |
| Chats share the knowledge | yes | yes | yes, plus a **shared sheet** all chats read |
| Answer sized to the question | yes (the model decides) | **no** (a fixed research note for every legal question) | **yes, by code and by a visible size** |
| Remembers the conversation | yes | **no** (our earlier answers are kept out of the question on purpose) | **yes, without letting our words steer the law search** |
| Statements of law stand on shown text | no | partly (boxes, checks) | **yes: the section's own words on hand, checked by code** |
| Cost visible to the user | no | no | **a size label, and a tap to go deeper** |

## 3. Principles (what every step must keep true)
1. **A model never supplies a section number or a statute's words.** Code supplies the sections (from the file, the person's own words, or the matter's pins) and the text (from our library). A model explains and applies; it does not recall.
2. **Size follows the question.** A one-line ask gets a short answer with no template. The research note is for research asks and for a tap on "Go deeper".
3. **Cases are opt-in inside a matter.** No wider search, no fed judgments, unless the person asks for cases or taps for research. The expensive step is the person's choice.
4. **Unsure means the middle path, not the top one** (a change from the owner's instruction of 2026-11-20, decision D1): Standard, which has the law on hand, with a visible way up.
5. **Read once, answer many.** The file is turned into a short sheet with a page cite on every line; questions about the file start from the sheet.
6. **Memory without leakage.** The model may see the conversation; the search never sees our earlier words (see 4.7).
7. **Say what the answer stood on, in one line**; the long dump on request. Honest gaps stay, as one line.
8. **Cost is a design input.** Each size has a declared budget, logged on every turn, reviewed weekly.
9. **Every new behaviour is behind a switch, default off, staging first**, with its question set frozen before its code, as for the router. The Hard rules block is never edited.

## 4. The design

### 4.1 Three shelves
- **Your file** (exists: P1 documents; new: the sheet, 4.6). Facts, never law.
- **Law on hand** (new). For the matter: every section the documents charge or cite (code: the Explain-list machinery plus `sections_only_in_documents`), plus any the lawyer pins. For each: the section's text word for word (sliced to the cited sub-section for long sections: checked by hand on BNS 309(4), 115(2), 3(5) on 2026-11-20, the cut works), the BNSS Schedule I row (punishment, cognizable, bailable, court; exists as `offence_class`, `machine_extracted`, unread by a person), the provisos and cross-references (exists: `SECTION_RULE`, `SECTION_XREF`). Shown to the lawyer as a "Law" tab with a tick for "text on hand" and a cross for "not in our library" (IPC today, see W7).
- **Research** (exists: wider search, register, cards). Only on a tap or an explicit ask for cases.

### 4.2 Turn kinds and sizes
The planner is rules first (as the router was), logs its reason, and always lets the person move a turn up or down.

| Kind | Example | What the model is given | Model call | Shape | Declared budget (estimate) |
|---|---|---|---|---|---|
| **Edit the last answer** | "shorter", "simpler", "as a table", "in Hindi" | the last answer only | Haiku or Sonnet, no thinking | the same content reshaped; every section number and figure must already be in it (code check) | Rs 0.2 to 0.6 |
| **File fact** | "when was he arrested?", "who is the IO?" | the sheet line, else the file passages | none if the sheet holds it (code builds the answer with its page), else one small call (today's file path, measured Rs 0.88) | one or two sentences with the page | Rs 0 to 1 |
| **Explain provisions** | "explain the sections", "what is 309(4)?", "is it bailable?" | Law on hand for those sections, the sheet lines that concern them | one small call, or none for a section card (4.5) | the section's words, the code-built table, a plain-words gloss, what the file alleges (no verdict) | Rs 0.5 to 1.5 |
| **Apply to my facts** | "does 309(4) fit these facts?", "can he get bail now?" | Law on hand, the sheet, retrieved statute sections by meaning (library and shelf) | one Sonnet call, low or medium thinking | the answer first, the reasons, the one gap that matters; no cases | Rs 3 to 6 |
| **Research** | "what do courts say on...", "judgments on...", "go deeper", an explicit "detailed note" | today's full pipeline | as today | today's research note | Rs 8 to 22 (measured: Rs 8.01 on staging, Rs 13.2 on production, Rs 22.16 on 2026-11-20 with the second answer) |
| **Draft** | "draft a bail petition" | none | none | the existing notice (drafting not approved) | 0 |

Unsure between two: the lower of Standard and the larger of the two. A request the planner cannot place goes to **Standard**, whose answer ends with "Go deeper (research with cases)".

### 4.3 The three sizes and what each skips
| | Quick | Standard | Research |
|---|---|---|---|
| Scope check (2 Haiku calls, Rs 0.9 here) | skipped | skipped (a matter with documents is in scope) | as today |
| AI Act detection (Rs 0.27) | skipped | only if no pinned law | as today |
| Rewrite of the follow-up (Rs 0.08) | skipped | skipped | as today |
| Wider search and fed judgments | none | none unless a case is named by the person | as today |
| Thinking | none | low | medium (as today) |
| Template | none | short | research note |
| Second answer when something is untraceable | never: a code fix | never: a code fix | as today, for wrong statements only |
| "Sources and checks" | one line (4.8) | one line + a panel | as today |

### 4.4 Your turn, replayed (what W1 would do)
"explain the sections in a clear manner" in the chargesheet matter:
1. Planner: the message points at the last answer's sections (rule: "explain/what is/elements/punishment/bailable + the/these/those sections", or a named section). Kind: **Explain provisions**. Sections: BNS 309(4), BNS 115(2), BNS 3(5), taken **by code** from the last answer's code-checked list (the list the button uses), never from model text.
2. Law on hand by code: BNS 309 (2,956 characters; 309(1) to (4) are the definition and the punishment), BNS 115 (515), BNS 3(5) (about 330 characters, cut out); Schedule I rows for 309(4) and 115(2); no row for 3(5), said as "a general provision".
3. One call, about 3,000 tokens in (law about 1,000, rows about 150, the sheet or the three file passages about 300 to 600, instructions about 700), about 500 out, no thinking: the model explains each section in plain words, each point quoting the words it comes from, and says what the chargesheet alleges with pages, **without a verdict on fit**.
4. Code checks: every quoted phrase is in the text on hand; no section number outside the three; every figure (years, rupees) is in the text or the rows; a failed sentence is removed and noted, not regenerated.
5. Display: answer, the code-built table, the Law tab opened at those sections, the one-line strip, a "Go deeper" chip.
Arithmetic: 3,000 in and 500 out is Rs 1.06 on Sonnet 5 and Rs 0.53 on Haiku 4.5 at the table's prices. Against Rs 22.16: about 20 to 40 times less. A section card (4.5) makes the call optional.

### 4.5 Section cards: compile once, share, review once (the strategic piece)
A card per section (library BNS/BNSS/BSA and the shelf Acts): the text word for word (code); the Schedule row (code); the cross-referenced sections (code); and, **drafted by a program once and clearly labelled**, the ingredients in plain words, each quoting the phrase of the section it comes from (code checks every quoted phrase is verbatim in the section; a card whose phrase fails is not published). Status labels as everywhere in this project: `drafted by a program, not read by a person` until a lawyer reads it.
- **Why it is the right bet.** The sections lawyers ask about are few and constant. A card costs Rs 1 or so once; every later "explain 309(4)" is free and identical for everyone. Review is a bounded job: **the top 60 criminal sections** for Mr. Advocate on a one-page-each sheet (as `ACT_SHELF_SHEET.docx` works), not a case-by-case reading of answers.
- **What it is not.** Not an opinion on how a court reads the section; no case law; no "good law". The card says what the section says.
- **Release in two stages (decision D5).** First: text, Schedule row and cross-references only (no program-drafted ingredients). Second: ingredients after the first lawyer review.
- Bulk cost: about 900 BNS/BNSS sections at about Rs 1 is about Rs 900 once [Guessing: not measured]; the top 150 first costs about Rs 150.

### 4.6 The matter sheet (read once)
At upload, code reads what a rule can read and checks it:
- **By rules (no model):** the sections charged (exists), the FIR number, court, police station, dates written in a fixed pattern, "judicial custody since", "absconding".
- **By one small call (Haiku, about Rs 0.3 to 1 per document, [Guessing]):** the narrative facts as short lines, **each with a quotation that code finds on the page it cites**; a line whose quotation is not found is dropped, not shown.
- **The lawyer confirms or edits** in the existing editable panel (`CASE_FILE`), which becomes the sheet: lines read from documents carry "read from Doc 1 p. 5, not confirmed" until ticked.
- **Use.** Lookups answer from the sheet by code, with the page. Standard answers get the sheet's lines (a few hundred tokens) instead of six raw passages (5,000 characters today), so dates and custody status arrive as structured facts, not as text the model may skim.
- Staging only until the privacy and consent text exists (gate G1). A document's bytes are still not kept.

### 4.7 Conversation memory without the leak
The engine treats the whole question as the person's words (grounding, register, Act detection), which is why our earlier answers were kept out of it. Keep that for **search**. Add a second, labelled argument for **the model's reading**: the last few turns as "earlier in this conversation (not a source)". A rule: nothing in it is law; law comes only from Law on hand. Reshaping turns (shorter, simpler, a table, Hindi) use only the last answer and may not add a number or a section; the verbatim section text is never translated, only the gloss. Pronouns resolve by code against the last list ("the second one" is the second of the last list).

### 4.8 What the person sees
- **The answer, sized.** Quick and Standard answers have no template headings unless asked; no "Points the accused can rely on" table for a fact; "Gaps" only when there is a gap that changes the answer.
- **A one-line strip** in place of the 4,447-word dump: `Law on hand: BNS 309, 115, 3(5) word for word ✓ · File: Doc 1 pp. 1, 2, 5, quotations found ✓ · Cases: none used`. A "Details" fold opens today's boxes. The PDF/Word download of a Quick answer is one page.
- **A size label and two taps:** "Quick", with `Shorter` and `Go deeper (research with cases, uses 1 research answer)`; a Research answer offers `Shorter`.
- **Matter home:** left, documents; centre, chat; right, tabs **File** (the sheet) · **Law** (law on hand, ticked or crossed) · **Notes** (instructions). A **Charges** card at the top (each charged section with punishment, cognizable, bailable, court) at no model cost: the base the unapproved "clocks" would need.

### 4.9 Mock-up of the target answer to your question
*Written by Claude as a design mock-up, NOT model output; the statements of law are copied from the text on hand; the Schedule rows are machine-extracted and no person has read them; a lawyer has not read this.*

> **The sections charged in FIR 214/2026** [Doc 1, p. 1]
> **BNS 309(4), robbery.** Theft is robbery if, to commit it or carry away what was stolen, the offender voluntarily causes or attempts to cause death, hurt, wrongful restraint, or fear of instant death, hurt or restraint (309(2)); extortion is robbery in the cases in 309(3). Sub-section (4): rigorous imprisonment up to ten years and fine; up to fourteen years if the robbery is on the highway between sunset and sunrise.
> **BNS 115(2), voluntarily causing hurt.** Imprisonment up to one year, or fine up to ten thousand rupees, or both.
> **BNS 3(5), common intention.** When a criminal act is done by several persons in furtherance of the common intention of all, each is liable as if he had done it alone.
>
> | Section | Punishment | Cognizable | Bailable | Triable by |
> |---|---|---|---|---|
> | 309(4) | Rigorous imprisonment for 10 years and fine; for 14 years if on the highway between sunset and sunrise | Cognizable | Non-bailable | Magistrate of the first class |
> | 115(2) | Imprisonment for 1 year or fine of 10,000 rupees, or both | Non-cognizable | Bailable | Any Magistrate |
>
> **What the chargesheet alleges:** the pillion rider snatched a gold chain of about 18 grams and pushed the complainant, who fell [p. 2]; the doctor recorded an abrasion and a bruise, both "simple in nature" [p. 5]. Two accused; one in judicial custody since 18-03-2026, one absconding [pp. 1, 5].
>
> *Law on hand: BNS 309, 115, 3(5) word for word ✓ · File: Doc 1 pp. 1, 2, 5 ✓ · Cases: none used.* [Shorter] [Go deeper: bail and cases for these charges]

About 190 words, against 5,348.

### 4.10 Cost levers, with what each is worth on the logged turn
| Lever | At stake on this turn | Note |
|---|---|---|
| No second answer for an untraceable number (delete the sentence, or add the missing section by code, as `RETRY_BY_CODE` does for companions) | **Rs 9.50** | `RETRY_BY_CODE` was ON in this run and did not apply: an ungrounded section is a "wrong statement" and still gets a second answer |
| Thinking by size (none, low, medium) | about **Rs 11** across the two calls [Likely] | the largest single item |
| Skip the scope check inside a matter | Rs 0.90, and the invented "BNS 103" | the gate is already open on production |
| Skip AI Act detection when law is pinned | Rs 0.27 | |
| No wider search or fed cases below Research | Rs 0.08 plus a share of the 19.6k input tokens | **not itemised in the log**: W2 starts by adding a log line that counts input tokens by block, so the next trim is chosen from numbers |
| Stable prefix and prompt caching (`PROMPT_CACHE`, exists, off) | not measurable here | pays when a matter's law and sheet (a few thousand tokens) are re-sent across a session; Guessing until measured on staging |
| One-line strip instead of the dump | no model cost; 4,447 words of the 5,348 | |

**Average cost, as arithmetic on declared assumptions (not a forecast):** today a lawyer's turn in a matter is Rs 0.9 (a file fact) to Rs 22 (this); say a legal-heavy mix averages Rs 12. With 55% Quick at Rs 1, 30% Standard at Rs 4.5 and 15% Research at Rs 13 the average is **Rs 3.85**; at 20 turns a day and 22 days that is about Rs 1,700 a month against about Rs 5,300 [Guessing: the mix is invented; the staging `COST_QUESTION` lines per size will replace it]. It is the number the price of a subscription has to be built on.

## 5. The grounding contract (what code proves, and what it does not)
| Statement in an answer | Where it must come from | Checked by | What the check does NOT prove |
|---|---|---|---|
| A section number | Law on hand or the person's own words | code: every number in the answer is on hand, else the sentence is removed and a note says so | that the section is the right one for the facts |
| A statute's words | the text on hand | code: the quotation is found word for word (the meaning-flipping words included, `grounding_checks._FLIP`) | that the text is the current text: it is our copy (see 9, the BNS/BNSS losses) |
| Punishment, cognizable, bailable, court | the Schedule I row, printed by code | code: the row is looked up, not written by a model | that the row is right: `machine_extracted`, one source, unread by a person |
| A fact from the file | the sheet or a passage, with its page | code: the quotation is on that page | that the document says the truth, or that the reading is fair |
| "This fits / does not fit" | nothing: Quick and Standard answers give no verdict on fit unless the person asks, and then say what the text requires and what the file alleges | none | everything: this is judgment, and it is a lawyer's |
| A case | Research only | as today (register, checker, list) | good law |

## 6. How it will be judged (declared before any code)
- **Conversation scripts, frozen first.** At least 40 scripts of 3 to 6 turns on the synthetic documents of 2026-11-19 (and 10 on public court orders): each turn labelled with its kind, the sections that must be on hand, the sections that must NOT appear, the largest allowed size and cost. Written by Claude and committed before the planner; half held out and run once. A lawyer labels a sample of 20 turns.
- **Metrics.** (1) For Explain turns, the share where every named or charged section's text is on hand: the target is 100 percent by construction, and the test fails if it is not. (2) A Quick or Standard turn sent to Research (money) and a Research turn sent below (a thin answer; every such answer carries the Go-deeper tap): both reported, never traded against a safe answer. (3) Answer length against the ask. (4) Cost per turn by size from the staging `COST_QUESTION` lines. (5) The share of sentences removed by the number and quote checks. (6) **A lawyer reads 20 answers**: right level of detail; any wrong statement of law; whether a section's words were on view. That is the first lawyer-measured data in this line of work.
- **Offline vs staging.** The planner, the pinning, the slicing, the table, the checks and the display can be tested offline with a stubbed model. How the model behaves, and the real cost, only staging shows.
- **Do not tune on the held-out half.** A rule change needs a new frozen set.

## 7. The steps (each needs the owner's go; each ends in his staging test; nothing is set on production)
| Step | What | Fixes | Size |
|---|---|---|---|
| **W1** Law on hand and the explain turn | `law_on_hand` (pins from the last file answer, from sections the documents cite, from the person's pins; text by code with sub-section slicing; Schedule rows; code-built table), the explain answer shape, "typed = tapped" by rules, the file answer stores its sections, the number guard cannot drop them (they are not the person's words and not model text: code-checked pins), cost label; switch `LAW_ON_HAND` | your turn: the right sections, word for word | medium |
| **W2** Sizes | planner (kinds, Quick/Standard/Research), the table in 4.3, unsure means Standard, size label with Shorter / Go deeper, a log line counting input tokens by block, code fix instead of a second answer, thinking by size; switch `MATTER_DEPTH` | the cost; "unnecessary details" | medium |
| **W3** Memory | reshaping turns, the labelled conversation argument for the model, pronouns by code | "make it shorter", "the second one" | small |
| **W4** The sheet | reading at upload, quotations checked, the panel as the sheet, lookups by code; switch `MATTER_SHEET` | read once, answer many; the Charges card | medium |
| **W5** Matter home | File / Law / Notes tabs, the strip, the one-page download | the Projects feel | medium (web) |
| **W6** Section cards | stage 1 (text, rows, cross-references) for the top 150; Mr. Advocate's sheet for the top 60; stage 2 ingredients; prompt caching measured | free, identical explanations; the review that scales | medium, then ongoing |
| **W7** IPC and CrPC on the shelf | load both from India Code (the certificate expired on 2026-11-02: check first; never disable TLS verification), machine-check as the others | matters under the old codes | medium; needs its own go |
| **W8** The lawyer test | 20 answers read by a lawyer; then the quota units and the price per size | whether it can be charged for | the owner's |

W1 fixes this turn and the Explain button: the right sections, a short answer, about Rs 1. It does nothing for a question like "can he get bail now?", which keeps running the full research note until W2 gives it a size.

## 8. Decisions for the owner (with my recommendation)
- **D1.** Replace "legal path when unsure" (your instruction of 2026-11-20, built as asked) with **"unsure means Standard, with a visible Go deeper"**. *Recommend yes:* the old rule protected against an answer with no law; Law on hand removes that danger, and the old rule now costs Rs 8 to 22 for every unclear turn.
- **D2.** Show the size label ("Quick / Standard / Research") to the user. *Recommend yes;* the cost in rupees only to you, in the log.
- **D3.** Quota units by size (Quick very cheap or unmetered, Standard 1, Research 3?). The plan limits in `api/db/plans.json` are provisional (D7 of the website design). *Recommend by size, numbers after W8.*
- **D4.** The sheet: rules only first (charges, dates, custody) and the small model for narrative facts second. *Recommend that order.*
- **D5.** Section cards: release stage 1 (no program-drafted ingredients) first. *Recommend yes.*
- **D6.** Who reads the top 60 sections: Mr. Advocate. *Needed before stage 2 only.*
- **D7.** IPC and CrPC on the shelf: go or no-go, and whether old-code matters are in the first release. *Recommend go: see 9.*
- **D8.** The model may see earlier turns inside a matter (4.7). *Recommend yes, with the labelled argument.*
- **D9.** Whether naming a case ("what did Arnesh Kumar say?") is Standard (one named library case, no wider search) or Research. *Recommend Standard for a library case, Research for the rest.*
- **D10.** Declared answer lengths: Quick up to about 150 words, Standard up to about 400, Research as today. *Recommend these as starting points, to be moved by what lawyers say.*

## 9. Risks, said plainly
1. **The library has no IPC and no CrPC** [Certain: both are named in the Act Directory but there is no text in `chunks/` or `act_shelf/`]. Offences before 1 July 2024 are still tried under them; [Likely] they will be a large share of a lawyer's live matters for years. For such a matter Law on hand is empty and the answer will say so. Your synthetic documents use the BNS, which hides this. W7.
2. **Our BNS and BNSS copy has known losses** (checked against India Code on 2026-10-17: 99% identical; BNSS s.183, s.401, s.480, the s.359 table, s.531 and about 82 chunks ending in the next chapter's heading). The section cards and Law on hand would quote that text word for word. The sections in this plan's first use (BNS 309, 115, 3) were not among the listed defects, but I have not run the cross-check on them. This is a dependency of W1 and W6, mentioned here once as you asked not to be asked again; the repair stays deferred until you say.
3. **The Schedule I rows** (punishment, cognizable, bailable, court) are `machine_extracted` from one source and no person has read them. They would be printed by code as fact. Mr. Advocate's check of the rows for the common sections should come before the table is shown without the "not yet read" line.
4. **A program-drafted ingredient may misread a section** (stage 2 of the cards): hence stage 1 first, the verbatim quotation of each ingredient, and the label.
5. **The planner will misroute some turns.** Rules miss phrasings; the cost of a miss is now an answer that is too thin (a Quick where Research was wanted) as well as too dear. The tap to go deeper, the shadow log and the frozen set are the controls; no promise of zero.
6. **A short answer looks more certain than a long one.** Every Quick and Standard answer keeps the one-line caveat and the strip; none gives a verdict on fit unless asked.
7. **Memory can carry an error forward.** Earlier answers are labelled "not a source", law comes only from Law on hand, and the number and quote checks run on every turn.
8. **More moving parts.** Four switches, each default off; a way back for each; a test that with all of them off the answers are byte-identical to today's.
9. **Confidentiality.** The sheet is read by a model; documents stay staging-only until the lawyer-written privacy and consent text exists (gate G1).
10. **The cost figures are estimates**: one measured turn, the price table, and my token arithmetic. The measured numbers will come from staging.

## 10. Considered and not chosen
- **A tool-using agent** (the model calls `get_section`, `search_file`): flexible and closest to how Projects feels, but its cost and path are not bounded and not testable offline, and it lets the model pick the law. Revisit for Standard only after W2 has its numbers.
- **A bigger or different model to fix retrieval:** the failure was not a weak model; no section number reached it.
- **More after-the-fact checks that regenerate:** each one is another Rs 9. Checks should remove or fix by code.
- **Fine-tuning:** no data, and nothing here needs it.
- **Cloning the Claude Projects interface:** the experience (set up once, chat, sized answers, memory) is the aim; the look is not.

## 11. Relation to the other plans
`MATTER_ROUTING_PLAN.md`: R0 and R1 stay (the router, the file answer, the draft notice); R2 to R5 are replaced by W1 to W4; the router becomes the first stage of the planner. `MATTER_FILES_PLAN.md`: P2 (facts into the case file) is W4; P3 (fetch the charged sections) is W1; clocks and OCR stay unapproved. `DRAFTING_PLAN.md`: drafting would read the sheet and the Law on hand, which is why they come first; still not approved. `LAWYER_RETENTION_PLAN.md`: the Charges card is the base for the clocks, which stay unapproved. `SUPPORT_AND_FIT_PLAN.md` (held): its S1 checks (quotes tied to their own source) are in effect what section 5 does for statutes. `LEGAL_AI_ADOPTION_CHECKLIST.md` (held): the sheet and the cards are two of its four requirements in smaller form.
