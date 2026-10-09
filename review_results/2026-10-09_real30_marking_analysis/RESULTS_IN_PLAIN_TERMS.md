# What J and S's marks tell us, in plain terms (2026-10-09; AI marks only, no lawyer; the 19 tuning questions only)

**Short version.** The search finds something useful for every question, and something that answers directly for most. Its real weakness is not finding passages but **old law**: when a later ruling or statute has replaced the law, the search still puts the old rulings in the top five. The recipe we use today (version A) is the best of the six we tried; the live site's own search is clearly worse on everyday questions; rewriting the question helps one question a lot and the rest not at all.

## First, a problem with the files (fixed, two chats still owed)
- 23 of 25 ChatGPT files had hidden backslashes added by copying out of the chat window, so they could not be read. I removed exactly those backslashes and nothing else (a tested tool; originals kept).
- One ChatGPT file (R02) was the **prompt**, not a reply. Another (R06) was an exact copy of Gemini's reply. Both are left out. **Please ask for two chats again: ChatGPT on R02 (order A) and on R06 (order A).** Until then Q6 rests on Gemini alone.

## How far to trust the marks
- The two AI tools gave the same mark on about 3 passages in 4 (and the same useful-or-not verdict on 9 in 10). Each tool is steady when the passages are shown in reverse order, and there is no sign that being first in the list earns a better mark.
- ChatGPT is more generous, Gemini stricter. Gemini's quotations from the passages are exact 86% of the time, ChatGPT's 95%.
- They did not judge each passage alone, as told. They noticed when another passage in the same file said a case had been overruled, and marked the old one "Misleading". Useful for us, but it means the marks partly check currency by accident.
- All of it is AI judgment. A gap of less than about ten points between two versions is not worth acting on.

## How good is today's search (version A)?
Out of the five passages shown, on average: **about 2 answer the question directly, about 2 more are useful background, and about 1 in 10 is misleading** (the exact shares depend on how a disagreement between the two tools is settled: direct answers 33 to 50%, useful 76 to 85%, misleading 6 to 12%).
- The first result answers directly on 10 to 12 of the 19 questions and is useful on 15 to 17. No question was left without a useful passage.
- The order matters: about half of the passages in places 1 and 2 answer directly; only about 1 in 10 of those in place 5 does. The search puts the better ones first.
- **Everyday questions are the weakest** (about a quarter of the passages answer directly), long stories and legal-wording questions are better.
- Six questions got no direct answer in the top five. Four different reasons:
  1. **Missing from the library** (Q6): once we added the missing order, every version found it first or second.
  2. **Old law fills the list** (Q9 cheque jurisdiction, Q11 NCB statements).
  3. **The story's words do not match** (Q14): the rewritten question found 5 direct answers where today's search found none.
  4. **New or unsettled law** (Q15, Q20): nothing directly answers.

## Which search recipe is best?
| Version | Verdict |
|---|---|
| A today | the best all-round; keep as the baseline |
| B (no repeats) | same as A in practice |
| E (no passage-type weights) | worse than A on every way of counting (about 6 points fewer direct answers, 5 points more misleading): keep the weights, which push down passages that merely record a lawyer's argument |
| S (the live site's own search) | **clearly weaker**: about 10 points fewer useful passages, and on everyday questions only 1 in 10 passages answers directly (A: about 1 in 4). Equal on questions already worded in legal terms |
| C, F (rewritten question) | looks like +5 to +12 points of direct answers, but **almost all of it is Q14**; without it the gain is about zero, and the rewrite also pulls in more old law (Q11, Q15). Not a general improvement |

## The biggest finding: old law
- Of the 30 passages that anyone marked "Misleading", **about two thirds were marked so because a later ruling or statute had replaced what the passage says.** A fifth were passages that only record a lawyer's argument.
- In **4 of 19 questions** (cheque jurisdiction, NCB statements, 498A relatives, CCTV certificate) today's top five contains replaced law.
- **Our list of known stale rulings misses most of it.** For the NCB question the reviewers flagged not just Kanhaiyalal but the cases that followed it (Ram Singh 1992, Surinder Kumar Khanna 2018, a 2023 passage of Balwinder Singh). A warning on the overruled case alone does not protect the user from them. The next step is a warning on cases that **rely on** an overruled ruling, which the checker can find. Mr. Advocate's list of modified and replaced-by-statute rulings (Rajesh Sharma, Dashrath) is the other half.

## Readiness lights, today's search, tuning half (a first reading: one to three questions per domain)
- **Relevance:** green and stable in Arrest, Bail, Marriage-related, Special-statute arrest and bail, After conviction; mixed in Cheque bounce, FIR quashing and Sexual offences; amber in NDPS; red in Violent crime, but that red comes from one question whose top five has four direct answers and one misleading passage, so treat it as amber.
- **Currency:** red in Cheque bounce, Marriage-related and Violent crime/evidence (an overruled or modified ruling is in the top five); green in Bail; NDPS is green on our list but, as above, not really.
- The two "controls" (divorce waiting period, section 38 BNSS) were not clean: the search showed confident, mostly useful-looking but pre-2018 or partial material, and gives no "nothing found" signal. Cleaner controls are asked of Mr. Advocate.

## What I think
1. Today's search is a decent **finder** and an unsafe **adviser on current law**. Fixing currency (library gaps, the lists, "relies on an overruled ruling") will do more for users than any change to the search recipe.
2. If the big index is connected to the site, use A's pipeline, not the site's own search.
3. Do not adopt the rewrite as a default on this evidence.
4. These are tuning-half and AI-only results. The sealed half and a lawyer's check still decide anything final.
5. Optional and cheap: have the 35 never-marked passages of the pre-re-ranker top five marked (36 short chats) to show, with marks, whether the re-ranker helps.
