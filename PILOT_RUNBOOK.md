# Running the private pilot (a runbook for the owner)

Written 2026-10-22. **Nothing here is running.** The pieces that run offline are built; the sender (a chat service and its accounts), the real search and the list of people do not exist yet, and each needs the owner's say-so. Anything marked *suggested* is the assistant's suggestion, not a decision.

## What the pilot is for

To get real lawyers' marks on the passages the search shows (Relevant, Not relevant, Misleading). The project has only AI-reviewer marks so far (19 questions, no lawyer), and its measured "8% of shown passages misleading" rests on those. It is not a product launch and not a promise to anyone.

## What is already decided, and what is not

`python -m goodlaw.pilot_admin settings` prints every setting, who decided it and which are placeholders. Today:

| Setting | State |
|---|---|
| How a quiet card is shown in chat (`quiet_policy`) | **decided 2026-10-22: a grey "No warning found in what we hold. This is not a finding that the case is good law."** (the owner told the assistant to go with its recommendation; reasons and the review trigger are in `goodlaw/data/pilot_settings.json`) |
| Searches per user per day, and for the whole test | **decided 2026-10-22: 10 and 100** |
| Passages shown per question | placeholder (3) |
| Longest question accepted | **decided 2026-10-22: 1,000 characters** (a longer one is refused before anything is searched) |
| Re-ranker | **decided 2026-10-22: `rerank-3-lite`** |
| Keep the text of questions | default off, undecided (turning it on needs an Indian counsel's view on consent) |
| Who is on the list, who reads the marks | **open** |

## Suggested shape (the assistant's suggestion, not decided)

- **Who:** 3 to 5 lawyers in criminal practice (bail and arrest matters), in small chambers, people who will say bluntly when a passage is wrong. Not your own clients' matters; test questions only. Mr. Advocate reads the marks only if he agrees to: he has not been asked.
- **How long:** 4 weeks.
- **What would make you stop or rethink** (suggested thresholds, to be replaced by yours): the Voyage credit falls to your reserve; a lawyer reports a case shown as "no warning found" or "not checked" that was in fact overruled (investigate before anything else); after at least 50 marks, more than 1 in 4 are "Misleading"; any lawyer says they read the grey line as comfort (switch `quiet_policy` to `silent` in the settings file).

## Steps, when you decide to go ahead

1. **Choose the people** and tell each what the test is (the three rules the bot shows first: test questions only, no client names or facts; the chat is not end-to-end encrypted; nothing is independently verified).
2. **Approve a sender** (not built). Telegram needs no business approval. WhatsApp needs a business account and approved templates, and Meta restricts general-purpose AI assistants on its business platform. A chat id is known only once a person writes to the bot.
3. **Add each person:** `python -m goodlaw.pilot_admin add-user --store pilot_store --id <chat id> --label "Adv. A" --by "<your name>"`. Use a label that is not a real name. They cannot get an answer until they reply "I understand".
4. **Approve the real search** (not wired; it costs an embedding and a re-rank per question: about $0.0004 to $0.001 for a short question, see `review_results/2026-10-22_pilot_cost/COST_IN_PLAIN_TERMS.md`, which also lists what that figure leaves out, hosting above all) and set the limits in `goodlaw/data/pilot_settings.json`. The re-ranker is decided (`rerank-3-lite`). Hosting is the larger cost: the index needs about 2 GB of memory (2.05 GB steady since the newer archive and the Gauhati High Court were added), so a month on Railway is about $21 to $23 of memory, against under $1 of searches: `review_results/2026-10-22_index_memory/HOSTING_IN_PLAIN_TERMS.md`.
5. **Each week:** `python -m goodlaw.pilot_admin summary --store pilot_store`, then `export-marks --out marks.csv`, and have someone you trust read the "Misleading" passages and what they say.
6. **Pause at any time:** `python -m goodlaw.pilot_admin pause --store pilot_store` (everyone, even a stranger, gets "The test is paused"); `resume` undoes it. Switch one person off with `switch --off`.
7. **At the end:** read the marks; decide whether `quiet_policy` stays, whether the passages are good enough to show anywhere else, and whether the case-tracking product is worth pursuing.

## Keeping it private

The store (`pilot_store/` or a folder outside the repository) holds chat ids and lawyers' marks. The tools refuse any other place inside the repository, show ids only as their last three characters, and write labels, never ids, in every sheet. Question text is not kept unless you turn that on.

## What this does not do

It does not send anything, search anything, or make any claim about a case beyond what the register and the cards already say. The checker catches about 3 in 10 verified overrulings, and 98% of the passages from the 29 test questions were from judgments with no card, so most messages will read "Not checked by us". That is honest, and it is the main thing the pilot will show.
