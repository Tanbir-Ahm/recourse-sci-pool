# Accuracy rating of version A (the search with the re-ranker), 2026-10-09

PRIVATE. Every figure is an AI mark (ChatGPT and Gemini, run by J and S) on the 19 tuning questions of the owner's 30; no lawyer has marked anything; the 11 sealed questions are untouched. All numbers come from `analysis.json` (`python analyse_marks.py`), after the two missing ChatGPT replies (R02, R06) were added. Tags: [Certain] = counted from the marks, [Likely] = strong inference, [Guessing] = filling a gap.

## 0. What is being rated, and what is not

- **Rated:** the search step, version A: meaning search + keyword search + "section N" search, merged to 60 candidates, re-read by the Voyage re-ranker, passage-type weights, top 10 (scored here on the top 5). This is what would hand passages to the model that writes the answer.
- **Not rated:** the answer-writing model. Nobody has measured what it does with these passages. A is not "the model"; it is the search that feeds it, so an accuracy figure for A is **not** an accuracy figure for the tool's answers. [Certain]
- **"Accuracy" here** = the share of the five passages shown that the reviewers marked as directly answering the question (Yes), as useful (Yes or Partly) or as misleading. Each question counts once.

## 1. The rating

| Top 5 of version A, 19 questions | ChatGPT's marks | Gemini's marks | both tools, agreed only | both, cautious (ties to the lower mark) | both, generous (ties to the higher mark) |
|---|---|---|---|---|---|
| **directly answer** (Yes) | **45%** | **39%** | **40%** | 33% | 51% |
| **useful** (Yes or Partly) | **84%** | **76%** | **80%** | 75% | 87% |
| misleading | 10% | 10% | 8% | 13% | 6% |
| first result directly answers (of 19 questions) | 12 | 11 | – | 10 | 13 |
| first result useful | 16 | 16 | – | 15 | 17 |
| at least one direct answer in the top 5 | 16 | 14 | – | 13 | 16 |
| no useful passage at all | 0 | 0 | – | 0 | 0 |
| **"clean" question** (a direct answer, no misleading passage in the first three, no replaced law in the five) | 12 (63%) | 11 (58%) | – | 11 (58%) | 13 (68%) |
| replaced law somewhere in the top 5 | 4 (21%) | 4 (21%) | – | 4 (21%) | 4 (21%) |

**Headline, in one line:** about **80% of what A shows is useful** (75–87% depending on how the two tools' disagreements are settled), about **40% answers the question directly** (33–51%), about **8% could mislead** (6–13%). About **6 questions in 10 come back clean** (58–68%); the other 4 in 10 have no direct answer, a misleading passage near the top, or old law in the list. [Certain as counts]

"Replaced law" = a passage of a ruling on our stale list, or a passage that some reviewer called Misleading for replaced law (my reading of the reasons), whichever tool marked it. "Clean" uses the marks of the column it sits in.

If you want one number: **80% for "useful passages", 60% for "clean questions"**. I would not call either "the accuracy of the tool".

Variants of the same number:
- **Top 1 / top 3 / top 5, direct answers (cautious–generous):** 53–68% / 42–61% / 33–51%; **useful:** 79–90% / 75–90% / 75–87%. The first two places carry most of the value (Yes by place: 53%, 53%, 21%, 26%, 11%). If the answer-writing step reads only the first three, use the top-3 line. [Certain]
- **When the library holds the answer** (the 14 questions that are answerable: without the three index gaps R06, R15, R21 and the two controls R28, R29; agreed only): direct 45% (39–54), useful 87% (79–90), misleading 8% (7–14); 9–10 of 14 questions clean. [Certain]
- **By how the question is written** (cautious): everyday-language questions (6) 23% direct, 57% useful; long stories (6) 47% and 83%; legal-wording questions (7) 29% and 83% (legal-wording questions carry the most misleading passages, 17%). [Likely: six questions per group]

## 2. Compared with ChatGPT and Gemini

**(a) As the two markers of A (measured).** ChatGPT rates A's top 5 at 45% direct, 84% useful, 10% misleading; Gemini at 39%, 76%, 10%. ChatGPT is the more generous: it marks higher than Gemini on 42 of the 217 passages and lower on 22, and it gives A about 6 points more direct answers and 8 points more useful passages. The two give the same mark on 71% of passages (the same useful-or-not verdict on 84%). So **the measurement itself carries roughly ±4 points** (half the gap between the two tools) before any question-sampling error. [Certain]

**(b) As rivals that answer the same questions (not measured).** ChatGPT and Gemini were used only as markers. Nobody asked them to answer the 30 questions, and nobody scored their answers against the tool's. **I cannot give a percentage for ChatGPT or Gemini as answerers, and any figure I gave would be a guess presented as a result.** [Certain that no such measurement exists]

What the marks do hint at [Likely]:
- Both tools, shown the passages, often **noticed that a ruling had been overruled** and said so (the Kanhaiyalal line, Shafhi Mohammad, Dashrath): both flagged 12 passages of replaced law. Mostly this happened because the later ruling was in the same file (ChatGPT flagged three passages of the Rajesh Sharma line because a passage of the later ruling in the file declares the committee directions impermissible). That is the luck of the pool, not a currency check, and these marks cannot tell how often the two tools would know the later law unaided.
- My expectation, **not shown by these marks** [Likely]: on famous overrulings (Tofan Singh and the like) general chatbots probably match or beat an unaided search, which knows nothing of later law; on lesser-known rulings they are more likely to be wrong or to invent a citation.
- The tool's possible edge is that it **quotes the court's own paragraph from a library you can check**. That edge is real only if the answer-writing step stays close to the passages. Not measured.

**The test that would settle it** (no cost, one afternoon of Mr. Advocate's time): put the same sealed questions to ChatGPT, Gemini and the tool (A plus the answer-writing step), blind, and have a lawyer score each answer on three things: correct, still current, and every cited authority real and read correctly.

## 3. Why this rating (reasons, with evidence)

**What pulls it down**
1. **Old law.** In 4 of the 19 questions (R09 cheque jurisdiction, R11 NCB statements, R15 498A relatives, R21 CCTV certificate) the top 5 holds replaced law: 9 of the 95 slots (7 called Misleading by a reviewer, 2 known only from our list). Of the 34 passages any reviewer called Misleading, 19 were flagged for replaced law (my reading of their reasons). The count is a floor: only what the reviewers noticed or our short list knows. [Certain as counts; Likely that the true figure is higher]
2. **Direct answers thin out after place 2.** Yes by place: 53%, 53%, 21%, 26%, 11%. [Certain]
3. **Six questions have no direct answer** (cautious setting), for four different reasons: a library gap (R06, now fixed by a side index); old law (R09, R11); wording that does not match the case (R14); new or unsettled law (R15, R20). [Certain]
4. **Everyday-language questions** are the weakest group (23–27% direct in every setting). If your users write like that, expect that row, not the headline. [Likely]
5. **No "nothing found" signal.** The two controls (divorce waiting period, section 38 BNSS) were answered confidently with mostly useful-looking, partly pre-2018 material. [Certain]
6. **The re-ranker is not a currency check.** It raises the chance of finding the named authority (in the top 5 for 8 of 14 answerable questions before it, 10 after), but the passages it pulled in from beyond the merged top 5 were weaker (28% direct against 47% for those already there). It reads relevance, not whether the ruling still stands. [Certain on counts; Likely on reading]

**What keeps it from being lower**
1. **Never empty:** no question without a useful passage (0 of 19, every setting). [Certain]
2. **The first result is usually good:** useful on 79–89%, direct on 53–68% of questions. [Certain]
3. **The named key authority is in the top 5 for 10 of the 14 answerable questions**, and the 4 misses have understandable causes. [Certain]
4. **It is the best recipe tested:** the site's own search shows about 9–11 points fewer useful passages (and 15 points fewer direct answers when ties go the generous way); the no-weights variant about 6 points fewer direct answers and 5 more misleading ones. [Likely]

**Why you should not lean hard on the number**
1. **19 questions.** Sampling alone puts the headline's direct share anywhere from about 25% to 55%, and the useful share from about 67% to 90% (95% interval over questions, agreed only). A fresh set of 11 questions (the sealed half) could average anywhere from about 14% to 65% direct and 58% to 100% useful. [Certain as arithmetic]
2. **AI marks only.** The tools agree exactly on 71% of passages; the lawyer's standard is unknown. I expect a lawyer to be **stricter** than both on "Yes" (ChatGPT gave R06 a Yes for a general principle that its own caveat says is not a complete section 479 holding). Direction [Likely], size [Guessing].
3. **Best-case questions.** The 30 were re-told from reported cases and government sources, not taken from users. [Certain]
4. **"Misleading" is partly a reading rule:** 8 of the 34 flags are passages that merely record a lawyer's or a party's submission; a well-built answer step would not treat those as holdings. The replaced-law flags (19 of 34, and 12 of the 16 both tools share) are the ones that can produce a wrong answer. [Likely]
5. **Passages never shown were never marked** (35 of the 90 passages of the pre-re-ranker top 5), so what the re-ranker adds or removes is not fully visible. [Certain]

## 4. What I expect in real use [Likely for the direction, Guessing for the size]
- Lower than the headline if users write in everyday language: between the everyday row (about 25% direct, 60% useful) and the headline (40%, 80%).
- Better after three fixes already identified: the register and "relies on an overruled ruling" warnings for old law (the biggest lever), the side indexes for library gaps, and a rewrite used only as a rescue where A finds nothing.
- The 14-question figure (45% direct, 87% useful) is what to expect where the library holds the answer.

## 5. Recommended wording until the sealed run and a lawyer's check
Do not publish "X% accurate". If a figure is needed inside the team: "In a test of 19 questions, two AI reviewers rated about 4 in 10 of the five passages shown as directly answering and about 8 in 10 as useful; about 1 in 12 could mislead; in 4 of 19 questions the list contained law that had been replaced. Not checked by a lawyer."

## Appendix: question by question (A's top 5 in rank order; Y = directly answers, p = partly, n = no, M = misleading)

"Cautious" and "generous" are the two ways of settling a disagreement between the tools. "Clean" = at least one Y, no M among the first three, no replaced law in the five. R22 fails "clean" on one passage that rejects the asker's family circumstances (both tools called it Misleading; the flag is arguable). R06, R15 and R21 are the index-gap questions; R28 and R29 are the controls.

| Q | kind | ChatGPT | Gemini | cautious | generous | replaced law | clean (cautious / generous) |
|---|---|---|---|---|---|---|---|
| R01 | narrative | YYYYp | YpYYp | YpYYp | YYYYp | - | yes / yes |
| R02 | everyday | YYYYM | YYYYM | YYYYM | YYYYM | - | yes / yes |
| R04 | legal | YYYYY | YYYYp | YYYYp | YYYYp | - | yes / yes |
| R06 | everyday | YpMnp | pnpnn | pnMnn | Yppnp | - | no / yes |
| R08 | everyday | pYnpp | nYnnp | nYnnp | pYnpp | - | yes / yes |
| R09 | legal | MYppM | YMppM | MMppM | YYppM | yes | no / no |
| R11 | everyday | pppMM | pppMM | pppMM | pppMM | yes | no / no |
| R12 | narrative | pYpYY | pYpYp | pYpYp | pYpYY | - | yes / yes |
| R14 | everyday | pMpMp | pnnMp | pnnMp | pnppp | - | no / no |
| R15 | narrative | npnpn | nnnpn | nnnpn | npnpn | yes | no / no |
| R17 | legal | YYppY | YYpYY | YYppY | YYYYY | - | yes / yes |
| R19 | narrative | YYppp | YYppp | YYppp | YYppp | - | yes / yes |
| R20 | legal | YYYYp | pMpMp | pMpMp | YYYYp | - | no / yes |
| R21 | legal | MYppp | MYYYp | MYppp | MYYYp | yes | no / no |
| R22 | narrative | YYMYY | YYMYY | YYMYY | YYMYY | - | no / no |
| R24 | narrative | YYYpp | YYYpY | YYYpp | YYYpY | - | yes / yes |
| R26 | legal | Ypppp | Ypppp | Ypppp | Ypppp | - | yes / yes |
| R28 | everyday | YYppp | YYnYp | YYppp | YYppp | - | yes / yes |
| R29 | legal | YYYYp | Ypppp | Ypppp | YYYYp | - | yes / yes |
