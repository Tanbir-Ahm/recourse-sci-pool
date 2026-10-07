# What the 12-question review showed (read in full, 2026-10-07)

**Source label for everything here: LLM-judged. J and SK sent each passage and question to an AI tool (ChatGPT, Gemini) and passed its marks on. No lawyer has checked any of it.** Twelve questions can show big differences between search versions, not small ones.

## What was read

- J, ChatGPT: Q01 to Q06, both orders (12 files). J, Gemini: Q07, Q08, Q10, Q11, Q12, both orders (10 files). **J's Q09 (A and B) did not arrive.**
- SK, ChatGPT: the 24 top-up passages (10 replies; Q01 and Q06 have none) and the overlap replies Q03_A and Q09_A.
- 6 runs; all 199 passages in the pool marked by at least one run. One file (`A08_A.rtf`) had the code box's heading "JSON" copied in front of the reply; the converter now drops that one label (tested); nothing else was changed.

## Can the marks be trusted?

- **Partly.** Same tool, other order: ChatGPT agrees with itself on 77% of marks (kappa 0.61), Gemini on 90% (kappa 0.86). Two people using ChatGPT on Q03 agree on 81% of marks (kappa 0.65), but on "useful or not" only kappa 0.43.
- **No question was judged by both ChatGPT and Gemini**, so nothing shows whether one is stricter. Comparing versions inside a question is fair (one judge per question); comparing absolute levels between the halves is not.
- Quotes: 361 of 374 evidence quotes are word for word. Of the 13 that are not, 10 are two real fragments of the passage joined with "...", 1 is a hyphenation difference, and 2 do not match (Gemini, Q12 passage 8, in both orders): treat those two marks as unsupported.
- 23 passages ended "split" (the runs disagree). The shares below drop them unless it says otherwise.

## The scores

"Yes" means the passage directly answers the question. Figures are averages per question over what the version showed in its top 5 (the site's method and "mine top 6" are scored on everything they showed).

| Version | Questions | Yes share | Yes on plain / legal questions | Passages marked Misleading | Questions with a Misleading passage |
|---|---|---|---|---|---|
| **A today** (my pipeline) | 12 | 0.45 | 0.50 / 0.39 | 9% | 3 of 12 |
| B no repeats | 12 | 0.45 | same | 7% | 3 of 12 |
| E no passage-type weights | 12 | 0.41 | 0.44 / 0.38 | 7% | 4 of 12 |
| **C rewrite** (plain questions in legal wording) | 6 | **0.83** (A on the same six: 0.50) | 0.83 / n/a | 7% | 2 of 6 |
| F merged (A and C pooled) | 6 | **0.86** | 0.86 / n/a | 7% | 2 of 6 |
| **S the site's own method on the big index** | 12 | 0.36 | 0.53 / **0.19** | **2%** | **1 of 12** |
| M mine top 6 | 12 | 0.40 | 0.50 / 0.29 | 10% | 3 of 12 |
| L the 20 hand-verified key paragraphs | 12 | 0.54 (0.96 Yes or Partly) | 0.58 / 0.50 | 0% | 0 |

- In how many questions does a version show at least one directly answering passage? Today's pipeline 10 of 12 (the two with none: Q06, whose wording is flawed, and Q10, the Section 50 "substantial compliance" question); every version 6 of 6 on the plain questions; the rewrite versions 6 of 6.
- If disagreements are counted as "not Yes", today's Yes share is 0.37 (legal questions 0.23). The legal-wording result moves a lot with that choice: it is the least reliable part.
- Even the hand-verified key paragraphs get "Yes" only 54% of the time (96% Yes or Partly): the reviewers' bar is strict, so every "Yes" share is conservative.
- Worst plain example, Q11 ("They found drugs and say I must prove I am innocent. Do I have to prove it?"): today's top 5 are all from the right case family but 4 of the 5 are marked "No" (a discussion of the European Convention, an old Privy Council case, bail provisions). With the legal rewrite, 4 of 5 are "Yes".

## What the search does wrong (the 11 passages the runs agreed were Misleading)

- **5: an earlier view that was later overruled.** Three Q08 passages repeat the 2008 view that Section 139 does not presume a legally recoverable debt (Rangappa, 2010, rejected it); two Q09/Q10 passages are from Prabha Shankar Dubey (2004), whose "substantial compliance" view the Jadeja Constitution Bench (2010) rejected. The checker already flags Prabha Shankar Dubey.
- **1: counsel's argument** (Q05, the only passage both ChatGPT runs called Misleading).
- **3: narration** of the evidence, of the conviction, or of a notice quoted from another case (Q09, Q12, Q10).
- 1 passage that mostly quotes statute text (Q07) and 1 summary of a rule that the runs found misleading without my having looked into why (Q09).

## The site's method versus mine

- The site's method (no re-ranker) shows fewer Misleading passages (2% against 9%; 1 of 12 questions against 3 of 12) and found 24 passages that today's top 5 did not show: 10 "Yes", 13 "Partly", 1 "No". Outside today's top 5 it showed 11 direct answers. But it has the lowest Yes share (0.36) and is weakest on legal-wording questions (0.19). The counts of Misleading passages are small (1 against 4 passages), so this is a hint, not a result.
- Connecting the site's present method to the big index as it is would be worse than my pipeline on direct answers.

## Limits

- LLM-judged, 12 questions, two judges that were never compared on the same questions, one question's replies missing (Q09, from J).
- **The rewrites in C and F were written by me knowing the expected case.** They show what a good rewrite can do, not what an automatic one would. The true gain is smaller; how much is not measured.
- Q06's wording is flawed (it asks about a non-compoundable Section 325 offence, but its case concerns Sections 324 and 326), and Q05's rewrite calls voluntarily causing grievous hurt "not compoundable". Their marks should not be reused as they are.
- "Plain" and "legal" questions are 6 each and alternate through the list, so the judge (ChatGPT or Gemini) is not mixed up with the kind of question.
