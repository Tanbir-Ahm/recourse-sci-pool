# Drafting plan for the lawyers' module (written 2026-11-16)

**Status: a PLAN. Nothing is approved to build and nothing is built.** Drafting stays "ask before starting" (`LAWYER_RETENTION_PLAN.md`, CLAUDE.md). The owner asked on 2026-11-16 ("i have these templates now, be innovative and plan it now"); this is that plan. Everything here is Claude's reasoning; demand is unverified; no lawyer has read it. Say "no hallucination rate has been measured".

## 0. Why this exists
A lawyer asked the tool to "draft a document for a defamation case"; it showed Supreme Court and Gauhati High Court judgments and no draft. Cause: the engine has no draft intent (every message is a research question), the only drafting code (`draft_layer.py`, `petition_draft.py`, `scenario_draft.py`) is deterministic templates for arrest, freeze and bail situations, and there is no defamation template.

## 1. What the 21 templates are (read in full on 2026-11-16; the zip is the owner's, not stored here: provenance and licence unknown)
- 20 distinct Word files (`loan-agreement (1)` is byte-identical text to `loan-agreement`). Each is 2,000 to 5,000 characters, one placeholder style `[PLEASE PROVIDE: Label]` (212 distinct labels; 35 recur: Day, Month, Year, City, State, Full Address, Amount in Rupees, Advocate Name / Enrollment / Address / Phone, Witness 1 and 2, PAN, Aadhaar), plus about 92 free-text instructions in square brackets ("[describe the events ...]", "[bailable / triable by Magistrate ...]") that are the real drafting content. A page-number footer only.
- Relevant to Recourse (criminal and litigation): bail application, legal notice, affidavit, writ petition. Civil litigation: consumer complaint, divorce petition. **Fourteen are transactional** (rent, lease, sale, gift, will, POA, NDA, MoU, employment, partnership, franchise, consultancy, loan, service agreement): they need the Transfer of Property, Registration, Contract, Partnership and Succession Acts and state stamp duty, none of which is on the Act shelf, and they have nothing to do with the research moat.
- **Not in the set: defamation (notice, private complaint under BNSS 223, quashing petition under BNSS 528), and anything else criminal beyond bail.**
- **Defects seen in the templates (the lawyer should confirm):** the affidavit cites the Indian Evidence Act, 1872 s.3 (the Bharatiya Sakshya Adhiniyam replaced it); the legal notice is headed "Section 80 CPC / General" (s.80 is the notice to the Government), is built on the Contract Act s.73, and carries a stamp-duty line, an exclusive-jurisdiction clause and witness lines that a notice does not normally need; the bail application hard-codes three authorities (Sanjay Chandra, Arnesh Kumar, Satender Kumar Antil) with no paragraph and no register check (Arnesh Kumar is about arrest, not bail), says "court fees ... paid", and opens its grounds with a stock "innocent and falsely implicated"; the bail template does not say which of BNSS 480, 483 or 484 applies; the writ template is Article 226 only.
- Whether a lawyer wrote or reviewed any of them is unknown. **Never mark a template `reviewed` on anyone's behalf.**

## 2. The idea in one line
**The model never writes the law and never invents a fact. Code fills the lawyer's own Word template; the law comes word for word from the Act shelf; facts come only from the Matter's case file; the model, if used at all, only joins the lawyer's own facts into paragraphs, and every sentence it adds is traced or highlighted.** The product's edge over ChatGPT and CaseMine's drafting is the checking, not the writing.

## 3. Pieces that already exist
Matter and case file (the person's own typed sentences, word for word); the Act shelf (BNS, BNSS, 13 Acts, verbatim sections, official-text boxes); the invented-case check and tolerant name match; the quote check; the register and checker for authorities; PDF / Word export; the interview pattern (`interview_flow.py`); the cost log; the statute map EA to BSA. **New pieces:** the template specs, the fill engine, the draft linter, law-block insertion, a CrPC/IPC to BNSS/BNS reference map (not built; the library has only the EA to BSA map), the intent detector, the draft cover sheet.

## 4. The design (innovations)
1. **Templates become data.** A script reads each docx and writes a spec: sections in order, fields (type: name, date, amount, choice, address, free text from facts, LAW block, AUTHORITY slot), required or not, which statute each section rests on. The 212 labels fold into one registry, so "Client Full Name" is one field across every document.
2. **Type once, used everywhere.** An Advocate profile (name, enrolment, address, phone) saved once fills five templates' signature blocks; the Matter holds court, FIR, police station, parties and dates once. This is the stickiness the retention plan wanted, at zero model cost.
3. **Fill the lawyer's own Word file in place** (python-docx on the original, formatting and footer kept), not a re-typed copy.
4. **A highlight code the lawyer reads at a glance:** no mark = from the lawyer's own facts or verbatim law; yellow = a blank or a choice for the lawyer; red = a check failed. The checks live on a separate cover sheet that is NOT part of the filing.
5. **Law blocks.** `{{LAW:BNS:356}}` is replaced by the shelf's text word for word with its source and the shelf's `machine_checked` status; the template's hand-typed legal references are replaced by checked blocks.
6. **Elements first, for defamation.** The draft's paragraphs follow the elements of BNS 356 (an imputation, made or published, intending or knowing or having reason to believe it will harm reputation) and the exceptions are shown word for word so that the lawyer sees at once which exception the other side will run. The same case file also produces the defence side (a quashing petition, grounds to resist the complaint). BNSS 223 changes the complaint's path: the Magistrate examines the complainant on oath and must give the accused a hearing before cognizance (shelf text read 2026-11-16), so the complaint must be drafted for that.
7. **Draft check as a free product of its own (no model, no cost).** Upload any Word draft (ours, the lawyer's, the other side's): the linter flags stale law (IPC, CrPC, Evidence Act), a section number with no text, a citation that is not on the verified list or is on the register, blanks left, party names or dates that differ between paragraphs, a missing verification or annexure line. This reuses the same checks, helps the lawyer on day one, and shows whether the checks catch real faults before any generation is shipped.
8. **Filing-readiness list** per document type (annexures, affidavit, vakalatnama, court fee, limitation question): lawyer-written rule table, shown as questions, never as legal conclusions.
9. **Style library later:** the lawyer's own past drafts (anonymised, with permission) set the house format.

## 5. Order (each step needs the owner's go; each ends in his staging test; nothing is set on production without his say-so)
- **D0, small, no drafting:** when someone asks to draft something and no template exists, say so plainly and offer what exists (the section's elements, the statute text, the cases). Detect "draft / prepare / write a ..." asks.
- **D1, deterministic core, no model:** spec converter, field registry, Advocate profile, fill engine for the four criminal-litigation templates (bail, notice, affidavit, writ), highlight code, cover sheet, the linter. Measured on 20 fact sets written before the build.
- **D2, law blocks and authorities:** shelf-verbatim sections replace hand-typed references; authority slots accept only judgments the checker and register know; the CrPC/IPC to BNSS/BNS map (built from the shelf and checked by program, then a lawyer reads it).
- **D3, the defamation set:** notice, private complaint (BNSS 223), quashing petition (BNSS 528), the elements table. The lawyer supplies or corrects the skeletons; Claude may write a first skeleton from the statute text, marked `unreviewed`.
- **D4, model-written fact paragraphs**, switch `DRAFT_MODEL`, default off, staging: the model joins case-file facts into the template's free-text slots; every sentence is traced to a case-file line or highlighted; invented names, dates, amounts and sections are caught (measured by seeding invented facts into drafts and counting what the check finds). Cost per draft to be measured, not assumed.
- **D5, draft check for uploads, D6, style library.**
- Transactional templates (14): not in v1, not before D4 measures; they are a different market (property and corporate lawyers, clerks, the public), crowded (ChatGPT, document sites), state-specific (stamp duty, registration), and they do not use the research moat.

## 6. How it will be judged
Pre-registered, all committed before running: (a) the linter finds 100% of seeded stale-law and blank faults on 20 templates-times-fact-sets, with false alarms counted; (b) every statute passage in a draft is a character-for-character copy of the shelf (a diff check, not a sample); (c) the trace check finds seeded invented facts (report the rate, do not assume it); (d) a lawyer scores 10 drafts blind against a ChatGPT draft from the same facts: wrong law, wrong or invented authority, minutes to filing-ready. Claude's own scoring is not accepted as the result. No claim that drafts are accurate or safe until (d) exists.

## 7. Risks, said plainly
A draft is a court filing: a wrong section or an invented case harms the lawyer, not just the user. Hence: lawyers only at first; "draft for lawyer review", never "ready to file"; no limitation or jurisdiction conclusion (a question to the lawyer); a draft stored in a Matter holds client names (privacy policy and DPDP consent are still placeholders, gate G1). ChatGPT and CaseMine already draft: the edge is only the checks, unproven until D6's blind test. Licence of the templates: if bought or copied from a site, they may not be shipped.

## 8. Decisions needed from the owner
1. Go for D0 and D1 (or D0 only).
2. Where the templates came from, who reviewed them, whether Recourse may ship them.
3. Which lawyer reads and corrects the skeletons and marks a template `reviewed` (Mr. Advocate or the lawyer who asked for the defamation draft); whether he will supply the defamation, complaint and quashing skeletons.
4. Defamation first from the complainant's side, the accused's side, or both.
5. v1 scope: the four criminal templates plus the defamation set (advised), not the fourteen transactional ones.
6. Drafting for laypeople: never, or later (advised: lawyers first).
7. Price or monthly allowance for drafting (after D4 gives a measured cost).

## 9. Relationship to matters (recorded 2026-11-19, owner: "Record this in both plan files"; see `MATTER_FILES_PLAN.md`)
Drafts live INSIDE a matter: the matter is the container (instructions, facts, files, conversations, clocks) and a draft is a work product made from it, a different kind of object from a Q&A answer (a document to file, filled by code from the lawyer's template, facts only from the matter, law word for word from the shelf, versioned, with a cover sheet of checks that is not part of the filing). The matter is what makes drafting worth building: without it a bail application is a form with blanks; with it the court, FIR, police station, parties and dates are filled once (design point 2 above). Order of dependency: matter facts, then uploads (which propose facts so the lawyer does not retype them; staging only until the legal text exists), then drafting. **Exception: the draft check (design point 7, step D5) works on any uploaded Word file with no matter attached; a matter is not a precondition for it.** The rule of section 2 holds even with a matter full of uploaded documents: the model never writes the law and never invents a fact. Building the matter-files steps P0 and P1 does not start drafting; drafting still needs the owner's go on D0 onwards.


## 10. Drafting from the matter's documents: "go through the material I uploaded and draft a bail petition" (recorded 2026-11-19, owner's requirement: draft any petition faithfully, grounded in the resources, without mistakes)
**Status: still a PLAN. Drafting is NOT approved and nothing is built.** Written after `MATTER_ROUTING_PLAN.md` (which sorts a question into a file lookup, a legal question or a draft request) and `MATTER_FILES_PLAN.md` (the documents feature). Everything here is Claude's reasoning; no lawyer has read it; nothing has been run with the answer model.

### 10.1 What "without mistakes" can and cannot mean
No tool can promise that a court filing has no mistake, and Recourse must not say it does. What can be promised, and tested, is **faithfulness by construction**: every fact in the draft traces to a page of the lawyer's own documents and to a line the lawyer confirmed; every statute passage is a character-for-character copy of Recourse's checked text; every authority is on a verified list and nothing else; and **everything the tool does not know is a visible blank, never a guess**. What code cannot check, and the lawyer must: the choice of remedy and forum, whether a ground fits these facts, whether an authority supports the point it is used for, limitation, court fee, the court's own format, and whether a fact in the file is itself right. The draft says so on a cover sheet that is not part of the filing. "Draft for lawyer review", never "ready to file".

### 10.2 What happens today (so that the gap is clear)
The engine has no draft intent: every message is a research question (that is why the lawyer's "draft a document for a defamation case" got judgments and no draft). The only drafting code (`draft_layer.py`, `petition_draft.py`, `scenario_draft.py`) is deterministic assembly for arrest, freeze and bail situations from a finished assessment, with no model: the same principle as here. An improvised draft from the research prompt would be exactly the unfaithful kind, so detecting the request (D0, below) matters before any drafting is built.

### 10.3 The flow for one sentence from the lawyer
1. **Recognise the request** (the Draft route of the routing plan: a drafting verb with a petition, application, notice, complaint, affidavit or writ). Until drafting exists the answer says plainly that it is not available yet and offers what exists (a fact sheet from the documents, the law on bail, the grounds the file supports): D0.
2. **Find out which petition, without guessing.** "A bail petition" can be regular bail after a refusal or after the chargesheet, anticipatory bail, or default bail: a legal choice that depends on stage, custody, earlier orders and forum. The tool shows what the file shows ("in custody since 18-03-2026; bail refused by the Sessions Judge on 05-05-2026, Doc 3; chargesheet filed 10-06-2026, Doc 1 p. 6") and asks the lawyer to choose from a short list. It does not choose.
3. **Read the documents into a fact sheet.** The model reads (whole-document mode, a cost) and PROPOSES fields: court, case numbers, parties, FIR, police station, sections charged, arrest, remand and custody dates, chargesheet status, co-accused status, earlier bail applications and orders, and so on. Each proposal carries the page and the exact words. **Code rejects any proposal whose value is not on the cited page** (the same check as the quotation check), and shows conflicts between documents side by side. A title line ("report under section 193") is not a charge: a named test case.
4. **The lawyer confirms the fact sheet** in an editable panel (the case-file panel of 2026-11-09 is the model: every line theirs to edit, add or remove). Only confirmed lines flow into the draft; an unconfirmed line shows yellow.
5. **Ask only what is missing and material** (the interview pattern): antecedents, residence and surety, age, health, family, status of the co-accused, any other pending application. Unanswered stays a yellow blank.
6. **Assemble** a Word file in the lawyer's own template (design points 3 and 4 above: highlight code, cover sheet, linter).
7. **Review checklist** for the lawyer: every yellow item, every authority still unconfirmed, every fact the documents contradict.

### 10.4 Where each part of a bail petition comes from
| Part | Source | Checked by |
|---|---|---|
| Court, cause title, parties, FIR, police station, sections | the confirmed fact sheet (matter fields and the file's proposals) | trace to a confirmed line; blank when absent |
| Facts of the case and custody history | confirmed fact lines in order; sentences by fixed wording, or (optional, off by default) a model that only joins confirmed lines | every date, name, number and amount in a sentence must stand in a traced line; any other is red |
| Day counts (for example days from arrest to chargesheet) | computed by code from two confirmed dates | recomputed by the check |
| Statutory provisions (BNSS 480, 483, 482, 187 as chosen) | word for word from Recourse's checked text, with its source | diff against the source; **see the prerequisite on the BNSS text below** |
| Grounds | a **ground bank**: paragraph skeletons read by a lawyer, each with a trigger (the facts it needs). A ground is offered only when the file supports its trigger; the lawyer ticks it; the model writes no ground | trigger facts present and confirmed |
| Authorities | only a **verified list**: each entry is a verbatim excerpt that passed `verify` (the anchors machinery), tied to the one proposition it was verified for, with its register status. Unconfirmed entries show yellow. The model adds no case | on the list; not on the register; excerpt is a copy |
| Disclosure paragraphs (earlier applications, pending proceedings) | a lawyer-written rule table: if the file shows an earlier refusal, the draft must state it | the rule fires or the cover sheet says it is missing |
| Prayer and interim prayer | the template | none beyond the template |
| Annexure list | built by code from the uploaded documents (Annexure A is the chargesheet; its pages) | matches the files |
| Verification, affidavit, advocate's details | template and the saved advocate profile | blanks highlighted |
The only uses of the model: reading documents into proposed facts (checked as above) and, if the lawyer turns it on, joining confirmed lines into sentences (traced). **Never** the law, the grounds, the authorities or the prayer. The default draft is therefore reproducible: the same confirmed facts give the same draft.

### 10.5 "Any petition"
A free generator for any petition would be unfaithful. What scales is a **library of reviewed petition types**, each a lawyer-read skeleton, ground bank, authority list and disclosure-rule table: regular bail first, then anticipatory bail, default bail, quashing (BNSS 528), notices and complaints (the defamation set of section 4). For a type that has no reviewed skeleton the tool says so, and offers the fact sheet and the research instead. Adding a type is a lawyer's reading, not a code change.

### 10.6 What must exist first (none of it does yet)
- **The fact sheet extraction and its confirm panel** (P2 of `MATTER_FILES_PLAN.md`, not approved).
- **A lawyer's reading of the bail skeleton, the ground bank, the authority list and the disclosure rules.** The owner's supplied bail template has unknown provenance and licence and stale-law defects (section 1); Claude may write first skeletons from the statute text marked `unreviewed`, never `reviewed`.
- **Verified bail authorities** in the anchors machinery (verbatim, `verify` passed; Mr. Advocate's confirmation before a petition relies on one without a yellow mark).
- **Correct BNSS text.** Recourse's own BNSS copy has known losses (checked 2026-10-17): s.480 has a one-letter loss ("o" for "on"), and s.183 and s.401 have lines missing. **A petition quoting section 480 from that copy would carry the defect.** The deferred BNS/BNSS repair (CLAUDE.md, FOLLOW_UPS 2ah item 5) becomes a prerequisite of quoting those sections in a draft. It needs the owner's word and his own pull request (production data).
- The privacy policy and consent text (gate G1): a draft held in a matter holds client facts.
- The routing plan's Draft route and the matter-documents plan's sections-charged fetch.

### 10.7 How it will be judged (declared before any code)
(a) Extraction: on the synthetic and public documents with hand-marked fields, the share of proposed values that stand on the cited page (must be 100% by the code check) and the share of marked fields found; including the title-line trap. (b) Seeded faults: invented facts, wrong dates, altered statute text, a made-up case planted in drafts; report how many the checks catch (report the rate, do not assume it). (c) Every statute passage in a draft is a copy of the source (a diff, not a sample). (d) A deterministic draft for the test matter has the expected fields, blanks and annexures. (e) **A lawyer scores 10 drafts blind against a generic chatbot's draft from the same facts** (wrong law, wrong or invented authority, minutes to filing-ready): the only measure that is not Claude's own, and until it exists no claim that drafts are accurate or safe.

### 10.8 Order
D0 (detect a draft request and say plainly what exists; no drafting) with the routing plan's R0/R1; the fact sheet (P2) after the routing plan's R3; D1 (deterministic regular-bail petition from the confirmed fact sheet, a reviewed skeleton and ground bank); D2 (law blocks after the BNSS repair, and the verified authority list); D4 (optional traced model joining); further petition types one at a time. Each step needs the owner's go and ends in his staging test.

### 10.9 Decisions needed from the owner
1. Go for D0 alone (detect and say what exists) as the first, safe step.
2. Faithfulness by construction (deterministic assembly, the model only reads; advised) rather than freer model-written drafts.
3. Which bail petition first: regular bail after a refusal or after the chargesheet (the test matter's situation), anticipatory, or default bail.
4. Which lawyer reads the skeleton, the ground bank, the authorities and the disclosure rules, and the court format to follow (Gauhati High Court, Sessions, Magistrate).
5. Where the supplied templates came from and whether they may ship (section 8, decision 2).
6. The BNS/BNSS repair: go, as a prerequisite of quoting BNSS text in a draft (his own pull request).
7. Whether a draft counts as its own priced unit (section 8, decision 7).
