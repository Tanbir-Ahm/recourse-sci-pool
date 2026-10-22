# What one pilot question costs, in plain terms (2026-10-22)

**The search bill is not the obstacle; the uncomfortable part is what this number leaves out.** A search costs a fraction of a cent. But the hosting of the index, the chat service and any person's time reading marks are not in it, and none of them has been measured. A pilot that looks nearly free on the Voyage dashboard can still cost real money elsewhere.

Confidence tags: **[Certain]** = computed from a file in this repository; **[Likely]** = strong inference; **[Guessing]** = filling a gap.

## The number

- **[Certain]** The stage F run (29 questions, one embedding and one re-rank call each, `rerank-3-lite`) used 20,703 re-rank tokens and 72.6 embedding tokens per question on average.
- **[Likely]** The prices are the listed ones in this repository's notes (voyage-law-2 $0.12 per million tokens; re-ranking $0.02 per million for `rerank-3-lite`, $0.05 for `rerank-2`). They come from third-party price lists, not Voyage's own pages. The dashboard is the check.
- **[Likely]** So one question costs about **$0.0004** with `rerank-3-lite`, or about **$0.0010** with `rerank-2`. About 2,400 questions cost $1 on the cheaper re-ranker.

| Scenario (28 days) | Questions | `rerank-3-lite` | `rerank-2` |
|---|---|---|---|
| 5 lawyers, 2 questions a day each | 280 | $0.12 | $0.29 |
| 5 lawyers, 5 questions a day each | 700 | $0.30 | $0.73 |
| Every placeholder cap hit every day (100 a day) | 2,800 | $1.18 | $2.92 |

The balance noted on 2026-10-10 was about $9.39 with a $5 reserve you set, so about $4.39 is spendable. **[Certain]** that this figure is 12 days old; **[Likely]** that the larger risk to the reserve is the live site's own use of the same credit, not the pilot. Read the dashboard before any real run.

## Why I added a question-length limit

**[Likely]** The re-ranker bills the question once for every candidate passage it scores (60 here). The repository's own estimate in `review_tools/pool_runner.py` assumes this too. A 1,000-character question is about 285 tokens, so it adds about 17,000 tokens: **it roughly doubles the cost**, and a pasted page would cost far more. So `goodlaw/bot_core.py` now refuses a question over 1,000 characters (a placeholder in `goodlaw/data/pilot_settings.json`, `max_question_chars`) before anything is searched or recorded, and a refused question does not use up the user's daily limit. The 29 test questions were short, so the figures above are for short questions.

## What is not in the number

- **Hosting the index. [Likely]** `FOLLOW_UPS.md` puts the index at about 0.5 GB of vectors plus 257 MB of text, and notes it has never been run inside the site's container and that the pilot search loops over every passage in Python. Something has to keep that in memory all day, and nobody has measured the speed or the monthly price of that. A small always-on server may cost more per month than all the searches above.
- **The chat service.** Telegram charges nothing for a bot [Likely]. WhatsApp charges per conversation or message, needs a business account, and Meta restricts general-purpose AI assistants on its business platform. Nothing is priced or chosen.
- **An answer-writing model.** None: the bot shows passages word for word and does not write an answer. No cost, and it is deliberate.
- **People.** Someone has to read the "Misleading" marks. Mr. Advocate has not been asked.
- **Embedding the corpus again,** if the index is ever rebuilt. Not part of a question.

## What this does not change

**[Certain]** The checker still covers 76 cards, and about 98% of the passages from the 29 test questions were from judgments with no card, so most messages will say "Not checked by us". Making the search cheaper does not make that better. Cards for the 183 judgments were declined, so that bottleneck stays.

## What I need from you, if you want to go on

Nothing in this folder spends money or starts anything. Before a real run, these are yours to decide: the daily limits (10 per person and 100 for the test are my placeholders), the question-length limit (1,000 characters, also a placeholder), which re-ranker the pilot uses, and where the index would be hosted.

On the re-ranker I have not settled which one is current. Every re-rank token in stage F's spend record is `rerank-3-lite`, which is why the table leads with it; but `FOLLOW_UPS.md` (2026-10-10) records "rerank-2 stays" until a proper trial of `rerank-3-lite`, and I did not find a later entry that switches it. The two differ by 2.5 times in price, so the choice matters more than the daily limits do. This is a question for you, not something I assumed.

Reproduce: `python review_tools/experiments/pilot_cost_2026-10-22.py --out review_results/2026-10-22_pilot_cost` (reads `review_results/2026-10-12_fix_test_f/spend.json`; no network).
