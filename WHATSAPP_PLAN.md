# WhatsApp bot: state and plan (stored 2026-10-20 at the owner's instruction; ON HOLD until the owner says it is fixed)

**Status: HELD by the owner ("Store the whatsapp plan into memory for now. I will let you know once its fixed.").** Do not start any of it, and do not re-ask every session. Raise it once, briefly, when the owner says WhatsApp is fixed, or when he asks what is open. Never store the bot's raw logs in this repository (they hold the webhook secret, phone numbers and the text of people's messages).

## 1. State at the time of storing (facts)
- Railway project `perceptive-enthusiasm`, environment `production`, service `whatsapp-bot` (volume `whatsapp-bot-volume` at `/data`; URL `whatsapp-bot-production-969a.up.railway.app`). NOT connected to GitHub (CLI deploys). Start command in the dashboard: `uvicorn whatsapp_bot:app --host 0.0.0.0 --port $PORT` (the leftover variable `NIXPACKS_START_CMD` holds the same). Healthcheck Path set to `/whatsapp/health` (2026-10-20).
- Code: the owner redeployed it on 2026-10-20 (about 11:44 UTC) from a clean clone of Recourse `main` `0d880bf` with `railway.json` and `Procfile` removed from the copy. Before that it ran the 29 September code (`721e063`).
- It first ran with `REGISTER_HOOKS=off`, `ACT_DIRECTORY=off`, style v1, the topic bar closed, no shelf, no wider search, no budget. The log then showed: healthcheck 200, `COST_QUESTION` lines, one BNS question answered (Rs 1.44, sent as one acknowledgement and seven messages), one tehsildar-bribe question turned away by the closed topic bar.
- The owner later set these variables on the bot (his paste; the key values were dummies): `ANSWER_CACHE_DB_PATH`, `CASE_LOOKUP_STATE_PATH`, `WHATSAPP_DB_PATH` (all under `/data`), `GUPSHUP_*`, `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `WHATSAPP_PUBLIC_BASE_URL`, `WHATSAPP_WEBHOOK_SECRET`, `REGISTER_HOOKS=off`, `COST_STATE_FILE=/data/cost_state.json`, `DAILY_BUDGET_INR=100`, `RESPONSE_STYLE=v3`, `ANSWER_EFFORT=medium`, `SCOPE_GATE=open`, `ACT_SHELF=on`, `ACT_DETECT=on`. Whether `ACT_DIRECTORY=off` was removed was not confirmed.
- Railway then had an incident ("new builds are temporarily paused", from 17:03 UTC on 2026-10-20; running services unaffected). Whether the variable changes took effect on the bot was not confirmed: check the bot's Deployments tab and Variables once Railway resumes.

## 2. Problems found, in the order to settle them
0. **After Railway resumes:** confirm the bot's latest deployment is Active and the variables are applied.
1. **Variable fixes:** `ACT_DETECT` must be `wide` (`on` is not a valid value: the code reads only `wide` or `ai` and treats anything else as off); `ACT_DIRECTORY` must be absent or `on` (the shelf needs the Directory on); `REGISTER_HOOKS` must read plainly `off` (that switch does not strip quote marks); add `GROUNDING_CHECKS=warn` and `SECTION_XREF=on` to match the website. Not needed on the bot: `SCI_SEARCH_*`, `PASSAGE_NOTES`; `ANCHORS` optional.
2. **Rotate the webhook secret:** it is printed in the access log (the URL path) and was pasted into a session. New random value in `WHATSAPP_WEBHOOK_SECRET`, same value in Gupshup's callback URL, at a quiet moment; confirm by one message. (PowerShell for a value: `-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 40 | %{[char]$_})`.)
3. **The earlier-answers leak (code, the owner's own pull request, then a CLI redeploy):** `whatsapp_bot.py` builds the engine's question with `whatsapp_store.build_question_with_context(history, message_text)` from `get_recent_history`, which includes Recourse's own earlier replies; the engine treats the whole text as the person's words, so the Act Directory, the shelf and the register read our own answers (an answer that says "Prevention of Corruption Act" would pull that Act into the next, unrelated message). Fix: fold only the person's own earlier messages (as `web_chat.py` does for the website), with a test. It must be fixed BEFORE `ACT_SHELF` and `ACT_DETECT` are relied on for real users; the owner has them switched on for his own testing.
4. **Raw-payload logging:** the bot logs every incoming webhook payload (phone number, WhatsApp name, full message text) at INFO level. Reduce it before real users (code change, owner's own pull request).
5. **Tests after the fixes (about five messages):** the PC Act question, then a follow-up; a topic switch right after (a BNS bail question: no PC Act material or notice may leak in); a POCSO section 19 question in a fresh chat; the tehsildar question (should now be answered); count the WhatsApp messages a v3 answer arrives as (v1 already split one answer into seven). Use questions not asked before (the answer cache could hide an update); send the answers and logs with phone numbers removed.
6. **Budget:** `DAILY_BUDGET_INR=100` is about 25 to 30 answers a day: enough for testing, too low for users.
7. **Bring it level with the website, one variable at a time, a day apart:** register on (delete `REGISTER_HOOKS`; test with Mohan Lal 2018, Raj Deo Sharma 1999, Bilal Ahmed Kaloo 1997); `GROUNDING_CHECKS=warn`; `SECTION_XREF`; the Act notice. Wider search (`SCI_SEARCH_*`) stays off on the bot unless the owner decides otherwise.
8. **Open questions the owner has not answered:** who uses the bot today; how it has been tested (Gupshup has one number, so there is no safe test number).

## 3. How to deploy and how to go back (command line, on the owner's Windows PC, in a NEW folder)
Never run `railway up` for this service from a folder that still has `railway.json` or `Procfile` (both start Streamlit, the website).
```
cd ~\Documents
git clone https://github.com/Tanbir-Ahm/recourse.git recourse-bot
cd recourse-bot
git checkout <the commit to deploy>      # 0d880bf was the first
Remove-Item railway.json, Procfile
railway link        # perceptive-enthusiasm > production > whatsapp-bot
railway status      # must show exactly that, or stop
railway up --service whatsapp-bot
```
Then open `/whatsapp/health` (should show `{"status": "ok"}`), send the test messages, read the logs. **Way back:** the same steps with `git checkout 721e063`. Old CLI deployments show REMOVED and cannot be redeployed from the dashboard, and a deploy needs a build (it does not work while Railway builds are paused).

## 4. Deployment path, decided for now
Keep the CLI deploys. Connecting the service to GitHub is optional and risky today: the repo's `railway.json` and `Procfile` belong to the website and would override the bot's start command and healthcheck, and Railway says services that never used Config as Code cannot opt in. If ever wanted: a dedicated release branch (for example `whatsapp-release`, `main` minus those two files) that the bot follows, updated by the owner's own pull requests; creating it needs the owner's say-so.

## 5. What is not changed by this plan
Nothing in the website. The bot's answer cache holds only human-approved answers (30 days); if any were approved, repeat questions can return old-style answers until they expire.
