# Why the system missed *Sarda*, and what I changed, in plain words (2026-10-29)

**The uncomfortable part first.** This problem cannot be fixed "for good". What I built finds the important case for about **three questions in four** on test questions I wrote (it was about **one in two** before), and it has a side effect you should know about: it makes it **more likely that an old case that has since been overruled turns up** (5 of 104 test questions before, 13 of 104 now). Nothing has been tried with the answer-writing model yet; that is your staging test.

## What went wrong
Think of the search as two people working together.
1. **A quick clerk** runs to the shelves and pulls out 60 passages (out of about 420,000) whose words look most like the question.
2. **A careful judge** reads only those 60 and puts them in order. The answer is written from the top few.

*Sarda* is in the index (197 passages). But the quick clerk **never brought any of them to the judge**: by wording, the closest Sarda passage came 488th. Why? Sarda's passages are long and mix a quotation, some history and several points. A later judgment that repeats the rule in one tidy sentence "looks" much more like a short question. There are hundreds of those short repeats, so they crowd the 60 places.

Even if Sarda had reached the judge, the judge's scores for places 1 to 30 were almost the same (0.92 down to 0.84), so who ends up in the top 8 is close to luck.

And the system ignored the most obvious clue a lawyer would use: **22 of the 59 judgments it pulled up for this very question themselves cite Sarda, and 446 judgments in the whole collection do.** "Everybody is citing this one" means "go and read it". The system never looked at who cites whom.

This is not rare. On 104 test questions with a known landmark, the plain search had the landmark among the first 8 judgments only about half the time.

## What I changed
1. **A "who cites whom" table, built in advance** from the text of all judgments (a program reads every passage and notes which other judgments it names). It is a file (146 KB) for each index.
2. **At question time:** after the clerk brings the 60 passages, the program asks "which judgments do these 60 keep citing?" Any judgment that a good share of them cite (at least 3, and at least 8 percent) is added: its best three passages are handed to the judge too, and its score gets a small boost (never more than 1.7 times, so a passage that is clearly off-topic stays off-topic).
3. **The facts are shown:** under the answer, such a case carries one grey sentence ("Named by other judgments: 22 of the 59 judgments this search retrieved, about 446 in the whole collection ... this does not say that the case is still good law"). The answer model is told to read that passage first, never to repeat the numbers and never to call the case "settled".

It is a **switch** on the search service, **off by default**. Off, everything works exactly as today.

## What it achieved (test questions written by me, not by a lawyer)
| | Before | After |
|---|---|---|
| The 52 held-back questions, staging's index | 23 of 52 (44%) | **39 of 52 (75%)** |
| The 52 held-back questions, production's index | 27 of 52 (52%) | **41 of 52 (79%)** |
On your question the list now starts with **Sarda, then Hanumant**; before, neither was there. "Held-back" means I settled all the settings on the other 52 questions and ran these once at the end, without changing anything afterwards. The true figure for real users could be lower: I wrote the questions, I picked the "right" cases, and a lawyer might pick differently. Differences of two or three questions are just noise (the same plain search, run twice, moved 7 of 104 outcomes).

## What it does not do
- **It still misses about one question in four.** I looked at the 13 misses: in 6 the table could not recognise how later judgments spell the case's name ("Tukaram" for "Tuka Ram", "Mohd." for "Md.", "U.T." for "Union Territory"), in 7 the other judgments did not point to it strongly enough. Both are fixable, but any change must be measured again on **new** questions (the 104 are now used up).
- **More overruled cases surface.** A case that is cited a lot is often cited because a later judgment overruled it. Our register of overruled cases still attaches its warning to the ones it lists, and the code never says "read this first" for a listed case. But an overruled case that is not on the register gets no warning. Please look for this in your test answers.
- **"Cited a lot" is not "good law".** It is a count of mentions of a name. The page and the prompt say so.
- **The passage the model sees for Sarda is the one the judge liked best** (it discusses Hanumant's rule and "no person can be convicted on pure moral conviction"), not necessarily the passage that lists the five conditions. For that one topic the exact-words route (`LANDMARKS=on`) is still the way.
- It makes the judge read about a fifth to a third more text (+18% on your question); the judge is the cheap part of a search. The answer model's cost hardly changes.

## What you need to do (details: `DEPLOY_STAGING.md` Part 4ae)
1. On the **staging** search service add `SCI_AUTHORITY` = `on` and redeploy. Do not touch production.
2. Turn `LANDMARKS` **off** on the staging services for this test (otherwise the hand-made excerpts hide what the new step does).
3. Ask your circumstantial-evidence question again, then five or six where you know the landmark. Send me the answers and the `SCI_FEED` lines from the log.
4. Look at every case with an "Overruled Register" line and check the answer says so.
Only after a lawyer has read staging answers should this go anywhere near production. Then, if you want, I do version 2 (spelling variants and the threshold) on a fresh set of questions.
