# Production switch-over: put the patch on the MAIN site, step by step (written 2026-10-15)

Plain steps for the owner. **YOU** = needs your Railway or GitHub account. Railway's screens change; where I describe a screen from memory it is marked [Likely].
Nothing here has been done. **Claude does not merge into `Tanbir-Ahm/recourse` `main`, open a pull request, or change production until the owner says so in so many words** (CLAUDE.md, "Rules that hold throughout").

## What is being put live

The branch `register-hooks-and-overlay` (head `0327c48` on 2026-10-15) is 25 commits ahead of Recourse `main` (`721e063`), which has not moved, so a clean fast-forward is possible.
It changes 29 files outside the register bundle (about +4,650 / -160 lines) and adds the `overruled_register/` bundle (7 files).

## What day one changes even with everything switched off (read this first)

"Switched off" is not "unchanged". These parts have **no switch** and run in production the moment the merge deploys:

1. **The Act-name checks.** A section number with no Act name gets "of the BNS/BNSS" added by code (instead of a second paid model call); the wrong one of BNS/BNSS after a number is corrected by code; "of the former Code" / "(now Section ...)" mentions are left alone.
2. **The invented-phone-number check is gone** (owner's instruction, 2026-10-15). Nothing in code now stops a made-up helpline; the prompt's hard rules do not mention contact numbers.
3. **Cost logging**: `COST_CALL` / `COST_QUESTION` lines in the Deploy Logs. No effect on users. The question itself is never logged, only a short hash.
4. **Grounding checks in `log` mode** (default): lines in the log only, nothing shown to users.
5. **Cut-off answers**: a reply that runs out of tokens is asked for once more with a bigger budget, and if still cut it is closed at the last full sentence with a note (v1 keeps its 4,000-token budget).
6. **Small code changes** in `semantic_retrieval.py` (cost logging of the embedding call), `whatsapp_bot.py` and `whatsapp_formatter.py` (a "Daily limit reached" message and the v3 hand-over; both inert unless the switches are on).

Everything else is behind a variable and **off by default**, EXCEPT one: **`REGISTER_HOOKS` defaults to ON when unset** (`register_hooks.py`). That is why step 1 below comes first.

## The variables (names exactly as written)

| Variable | Default when unset | Meaning |
|---|---|---|
| `REGISTER_HOOKS` | **on** | Overruled Register notes, labels, the "not checked by us" sentence, and the lawyers' case-check box |
| `RESPONSE_STYLE` | `v1` (today's style) | `v1` today's, `v2`, `v3` = the Adviser / Research Note |
| `SCI_SEARCH_MODE` | `off` | `shadow` (search runs, logged, not shown), `show`, `feed` (staging only) |
| `ANSWER_EFFORT` | unset (model default) | `medium` saves about 37% on lawyer answers |
| `GROUNDING_CHECKS` | `log` | `warn` adds a notice under the answer; never `enforce` |
| `ANCHORS` | `off` | verbatim excerpts for trial-delay questions |
| `DAILY_BUDGET_INR`, `COST_STATE_FILE` | unset | daily spending limit; the file needs a Railway volume |
| `SCOPE_MODEL`, `PROMPT_CACHE` | unset | leave unset for now |
| `SCOPE_GATE` (added 2026-10-16) | `on` = the topic bar stays as today | `open` lifts the bar: special-law and civil questions are answered instead of turned away. Test it on staging first (DEPLOY_STAGING Part 4g). Needs `SCI_SEARCH_MODE=feed` to be useful for a topic the library does not cover. The code has been on Recourse `main` since the owner merged PR #2 (`74d13ce`, 2026-10-16); the variable is unset on production until the owner sets it |
| `ACT_DIRECTORY` (added 2026-10-16, branch only until the owner merges) | unset = on: one fixed notice when a question names, or clearly describes, an Act whose text Recourse does not hold | `off` = no notice, no prompt line; `names` = name matches only. Test on staging first (DEPLOY_STAGING Part 4h). Status and appeal lines stay hidden until Mr. Advocate confirms them |

## Before you start (about 10 minutes)

**A. Find the production services. YOU.** In Railway, open the production project. Note every service: the website, and the WhatsApp bot if it is a separate service. For each, open Settings and read **Source**: which branch does it deploy from? Those that say `main` will redeploy at the merge. [Likely]

**B. Write down the way back. YOU.** For each of those services, open Deployments and note the time of the current Active deployment. If anything goes wrong, you can open that older deployment's menu and choose Redeploy or Rollback [Likely]. This is the way back even if the variables do not help.

**C. Check the keys exist.** The production website needs the same `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` it has today. Do not add any WhatsApp or Gupshup variable for this work.

## Step 1: set the first safety valve BEFORE the merge. YOU.

On every production service that will redeploy from `main` (the website, and the WhatsApp bot if it deploys from `main`):

1. Variables, add `REGISTER_HOOKS` = `off`.
2. Apply the change if Railway asks, and wait until the deployment is Active.
3. Ask one question on the live site. It should answer as it always did.

You do **not** need to add `RESPONSE_STYLE=v1` (that is already the default) or any `SCI_SEARCH_MODE` (default `off`; `shadow` needs the search service, which production does not have yet). You may add `RESPONSE_STYLE=v1` as visible insurance; it changes nothing.

## Step 2: the merge. YOU TELL CLAUDE, in so many words, e.g. "merge register-hooks-and-overlay into main".

Claude will fast-forward `main` to the branch (or you do it yourself in GitHub). Say if you want a pull request instead. **No merge happens before you say it.**

## Step 3: confirm nothing visible changed. YOU.

When the deployment is Active:
1. Website: ask one question. Same style as before; no "Checked by code" box, no "(from a wider search...)" labels, no "For lawyers: check whether one case has been overruled" box in the footer.
2. WhatsApp: send one message to the bot. Same style as before.
3. Deploy Logs: you should now see `COST_CALL` and `COST_QUESTION` lines, with `"style": "v1"`. That is the new cost log.
4. If anything looks different or broken: do not touch other settings. Send Claude the log; the way back is in "Before you start, B".

## Step 4: turn the register on (one day later is wise). YOU.

1. Delete `REGISTER_HOOKS` (or set it to `on`). Apply, wait for Active.
2. Ask the same two checks. Now expected: register notes and the "not checked by us" sentence under answers, and the lawyers' case-check box in the footer.
3. Watch it for a day. The instant switch back is `REGISTER_HOOKS=off`.

## Step 5: the cost and quality settings, ONE AT A TIME (a day apart is better)

After each one: ask a question, read the `COST_QUESTION` line, and look at the answer.

1. `ANSWER_EFFORT` = `medium`.
2. `GROUNDING_CHECKS` = `warn`.
3. The daily budget: add a Railway Volume to the production website service mounted at `/data`, then `COST_STATE_FILE` = `/data/cost_state.json` and `DAILY_BUDGET_INR` = a number you choose (two to three times the expected daily spend; the real maximum is that number plus one answer).
4. `RESPONSE_STYLE` = `v3` (this adds the Layman / Lawyer switch on the page).
5. `ANCHORS` = `on` (its text is still "verbatim excerpt, not yet confirmed by our reviewer" until Mr. Advocate answers the sheet).

## Step 6: the search service in production. LATER, not now.

Only after a lawyer has read shadow logs (runbook Part 5). Add the search service to the production project the same way as on staging (volume, index, tokens), then `SCI_SEARCH_MODE` = `shadow` first. `feed` stays staging-only.

## Instant switches

`REGISTER_HOOKS=off` · `RESPONSE_STYLE=v1` · `ANSWER_EFFORT` deleted · `GROUNDING_CHECKS=log` · `ANCHORS=off` · `SCOPE_GATE=on` (or deleted) · `SCI_SEARCH_MODE=off` (and on the search service `SCI_SEARCH_ENABLED=0`).
Each is a variable change; Railway redeploys in about a minute. They do not undo the "no switch" parts above; for those the way back is the older deployment.

## What is still not true

No hallucination rate has been measured for the answer-writing step. The tool is not "accurate" or "safe" because tests passed. The criminal trap exam (28 questions) is deferred until the patch is on the main site; run it after Step 4.
