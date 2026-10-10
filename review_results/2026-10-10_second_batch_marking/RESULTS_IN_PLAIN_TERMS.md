# J and S's second batch, in plain terms (2026-10-10; AI marks only, no lawyer has checked any of it)

**1. The re-ranker we already use is worth having.** Against the plain merged order, its top 5 has 8 to 17 points more direct answers and 10 to 15 points more useful passages (four ways of counting; the useful gain is clear in all four). Cost: a few more misleading passages (1 to 5 points, inside the noise), mostly because it also lifts old law. It is worse than no re-ranker on 4 of 19 questions (R08, R09, R17, R20). This replaces my earlier guess ("not proven").

**2. rerank-3-lite passes the rule I wrote before the marks, but the evidence is thin.** Of 19 passages it brings into the top 5 against 19 it pushes out, it brings in more direct answers (8 against 3 to 7), at least as many useful ones, and fewer misleading ones (1 or 2 against 2 to 4). I would call that "not worse, probably a little better", not "better".
- My rule had a blind spot: all 19 passages pushed out were marked in the first round, but 14 of the 19 brought in were marked only in the second, and the second round is a little more generous on the same text (the repeated passages show about +0.13 of a grade). Taking that off still leaves the same direction, but the margin shrinks.
- At question level the difference is small, and the intervals mostly include zero.
- It is better on R11, R14, R17, R24 and R22, level on four, worse on R12 and R20, and on R09 it swaps one old-law passage for another.
- The key paragraphs of R20, the case it "rescued", were never shown to a reviewer: it sits 8th, outside the top 5.

**3. The danger that remains is old law, not ranking.** About half of everything the reviewers called misleading is old or replaced law. One passage rerank-3-lite brings into R09 (Times Business Solution v. Databyte) rests on the Dashrath rule that a later statute replaced; both tools flagged it. It is not on our known-stale list, so my "none enters" check was a floor, not a clearance. No re-ranker removes this; the register and the checker are the tools for it.

**4. The safety net is cheap insurance, not a fix.** Its 52 passages are 18 to 20% direct answers and only 2 to 3% misleading. Nine were marked Yes by every run (R09: 3, R17: 2, one each in R04, R21, R24 and R28). R09's three were scored high by the re-ranker, then pushed from about 15th to about 30th by the 0.75 weight on statute-text passages. Places 6 to 10 of the normal list carry about half the direct-answer rate of the top 5.

**5. The reviewers.** ChatGPT and Gemini give the same mark on 75% of passages (a little steadier than in round one); ChatGPT is the more generous; 5% of their quotes are not word for word in the passage. R06 is the biggest split (ChatGPT 7 Partly, Gemini 8 No).

**Mistakes of mine, corrected:** I said 19 passages needed marking; 4 did. My rule did not allow for the two-round difference. My stale check cannot see replaced law that the key's list lacks.

**What I suggest:** keep rerank-2 live. Put rerank-2 and rerank-3-lite side by side as arms in the sealed run, with every top-5 passage of both marked in one shuffled round (that removes the two-round problem), pass and fail rules written first. The sealed half can be used once, so the full recipe (re-ranker, weights, safety net, register) must be settled before it. That is your decision. Tell me and I will draft the rules.
