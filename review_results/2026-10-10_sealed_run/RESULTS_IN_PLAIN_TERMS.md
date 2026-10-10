# The sealed run, in plain terms (PRIVATE; 2026-10-10; LLM-judged: ChatGPT and Gemini marks, run by J and S; no lawyer has checked any of it)

**Outcome fixed by the frozen rules: a floor is missed, so nothing is connected, and the sealed half is used up.** Any new final test needs new questions. The rules were written before the questions were searched and were applied mechanically (`scores/SEALED_RUN_REPORT.md`, `scores/stage1.json`, `scores/stage2.json`).

## What was tested
11 questions never used for tuning, one search recipe, two re-rankers (A = rerank-2, R = rerank-3-lite) and the Recourse site's own search (S) as a reference. 181 passages, every one marked Yes / Partly / No / Misleading by both ChatGPT and Gemini. The key was opened only after the marks were scored (`scores/key_opened.json`).

## The four floors (chosen arm: R, because it won the choice rules)

| Floor | Needed | R got | Result |
|---|---|---|---|
| F1 useful (Yes or Partly) in the top 5, where the two judges disagree take the lower mark | 70% or more | 69.1% | **missed by about one passage** |
| F2 Misleading in the top 5: lower mark / higher mark | 15% or less and 10% or less | 18.2% / 5.5% | **missed** (lower-mark side) |
| F3 the named authority is in the top 10 (10 answerable questions) | 60% or more | 60% (6 of 10) | met, exactly at the line |
| F4 direct answers (Yes) | 25% or more | 34.5% | met |

All four must hold; two do not. The tuning half had given 75% / 13% / 71% / 33% for the same search with rerank-2 (this run's rerank-2: 65.5% / 21.8% / 60% / 27.3%).

## Which re-ranker (decision D1): rerank-3-lite wins, by the rules
rerank-3-lite was at least as good in all four ways of settling the judges (top-5 grade 1.85 against 1.71 with the lower mark; 2.31 against 2.11 on ChatGPT alone), within the margins on Misleading and useful, better on 3 questions and worse on 1, as good on the named authority (6 and 6) and with fewer known-overruled passages in the top 5 (3 against 4), and the judges' agreement was not "weak". It was better on R03 (rerank-2 put passages about a different Act's search section in the top 5), R07 and R10, and worse on R05. The passages that only one re-ranker put in its top 5: rerank-3-lite's 19 held 6 Yes and 3 Misleading; rerank-2's 19 held 2 Yes and 5 Misleading. So the tuning-half reading ("not worse, probably better") now has support from questions it was not tuned on. It does not make the recipe fit to connect.

## The Recourse site's own search (reference arm)
Clearly behind both: 15% direct answers and 50% useful (lower mark) against 35% and 69% for rerank-3-lite.

## The safety net (D3): not kept
Its 33 extra passages: 14% Misleading (needed 5% or less), 42% useful (needed 55% or more). The lawyer list should be the ten alone.

## Domains and currency
No domain is eligible (the floors failed first). The currency light, without the register, is amber: 3 of 8 trap questions let a known-overruled or changed ruling into the top 5 (this counts the tuning half's trap questions too). The register arm was not run: it needs the corpus store, which is not in this environment, and it cannot change the outcome now.

## Where the failure comes from (descriptive, after the outcome was fixed; not a rescue and not a new rule)
- **One question explains the two missed floors.** R16 (a woman asks whether it is too late to file a domestic-violence case three years after she was thrown out): every top-5 passage of both re-rankers is about limitation for criminal cruelty or breach of trust (sections 498A / 406 IPC, 468 and 473 CrPC), not the Domestic Violence Act. Gemini marked all of them Misleading, ChatGPT Partly. The key case (Kamatchi v. Lakshmi Narayanan, 2022) is not in either top 10 (the site's own search puts it first). Without R16, R's numbers would be about 76% useful and 10% Misleading. That is a diagnosis of where the problem lies, **not** a ground to drop the question: the rules count it.
- **The Misleading marks fall into four kinds (22 top-5 slots of rerank-2 or rerank-3-lite flagged by either judge):** a neighbouring legal regime (R16, 10 slots; R03, 3 slots where rerank-2 showed passages on the NDPS Act's section 50 for a question on CrPC section 50A); an old view that was later overruled (R10, 4 slots: the Mohan Lal passages, which say so in their own text); a lower court's view later reversed (R18, 2; R05, 1); a murder conviction on special facts offered for an ordinary single-blow question (R23, 2).
- **The register and checker address one of the four kinds (overruled law).** They do nothing for the neighbouring-regime failures, which are a retrieval problem.
- **Named authority:** 6 of 10 answerable questions have the key case in the top 10 (R03, R13, R16, R23 do not). For R13 and R23 the top passages were still marked Yes or Partly by most marks, so other correct cases are probably standing in; the key names only one or two authorities per question (Mr. Advocate's sheet asks for the others).

## How much to trust it
- **The two judges agree exactly on 63.5% of passages** (kappa 0.48; they agree on useful or not for 76%). ChatGPT is the more generous (52% Partly; Gemini 38% Partly, 27% No). Of 38 passages that either judge called Misleading, both agreed on only **11**. So the Misleading figures rest on judges who often disagree, and the outcome depends on the way ties are settled: on ChatGPT alone rerank-3-lite gets 93% useful and 5% Misleading, on Gemini alone 69% and 18%.
- **Eleven questions** cannot show a difference of a few points. The rules said at the outset that even a tool as good as in the tuning half would miss at least one floor in roughly 35 to 45% of repeats [Guessing]. A miss of F1 by one passage is the kind of result noise can produce. The rules still say "missed".
- **Mr. Advocate agrees with the list of 16 older rulings** is the owner's relayed report; no filled-in sheet is in the repository, so everything that uses the list is "not lawyer-checked".
- **The rule on the replies:** the first copies of two ChatGPT replies (R07, R23) could not be read (a chat window's copy button had put a backslash before a backtick, and doubled a backslash before a quotation mark). J and S's re-asked replies carried the same faults; the cleaning tool was extended narrowly (marks checked to be unchanged) and the re-asked replies were used. This was decided before any mark was read.

## What this does not allow
No shadow mode, no panel, no connection of the big index. Do **not** tune the search on these 11 questions and then test on them: they are used up. Any fix (for example for the domestic-violence limitation failure) needs new questions written by someone who has not seen these. Mr. Advocate reads every passage that either judge marked Misleading (38 passages in the pool) and a random 20 of the others before anything leaves the project.
