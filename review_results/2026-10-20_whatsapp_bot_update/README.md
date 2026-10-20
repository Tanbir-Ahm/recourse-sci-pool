# WhatsApp bot updated by the owner (2026-10-20, about 11:44 UTC = 17:14 IST)

The owner redeployed the `whatsapp-bot` service himself from a clean clone of Recourse `main` at `0d880bf` with `railway.json` and `Procfile` removed from the copy (`railway link` to perceptive-enthusiasm / production / whatsapp-bot, then `railway up --service whatsapp-bot`). Before that he set the bot's Healthcheck Path to `/whatsapp/health` (Settings > Deploy) and redeployed once. Start command (dashboard and a leftover `NIXPACKS_START_CMD` variable, same value): `uvicorn whatsapp_bot:app --host 0.0.0.0 --port $PORT`. Bot variables seen before the update (names only): ANSWER_CACHE_DB_PATH, ANTHROPIC_API_KEY, CASE_LOOKUP_STATE_PATH, GUPSHUP_API_KEY, GUPSHUP_APP_NAME, GUPSHUP_SOURCE_NUMBER, NIXPACKS_START_CMD, VOYAGE_API_KEY, WHATSAPP_DB_PATH, WHATSAPP_PUBLIC_BASE_URL, WHATSAPP_WEBHOOK_SECRET. Whether the owner added REGISTER_HOOKS=off and ACT_DIRECTORY=off was not confirmed to Claude.

The deploy log is NOT stored here: it contains the webhook secret (in the URL path), phone numbers, a WhatsApp profile name and the text of a user's message. Only the findings are recorded.

## What the log showed (Certain)
- Clean start at 11:44:55 UTC; Railway's healthcheck `GET /whatsapp/health` answered 200 at once; the owner's own check 40 seconds later also 200.
- The new code is running: `COST_CALL` and `COST_QUESTION` lines appear (the old code printed none), `"style": "v1"`, `"grounding": "log"`, `budget: ok`, `SCI_TIER mode=off`.
- Message 1 ("What is section 18 of BNS"): answered, Rs 1.44; one acknowledgement message and seven answer messages were sent through Gupshup.
- Message 2 (a tehsildar demanding Rs 10,000 to sign land papers): only the scope check ran (Rs 0.51), no answer call: it was turned away (the topic bar is closed on the bot: SCOPE_GATE unset). The website answers that kind of question.
- Every Gupshup delivery receipt produces `WARNING Could not parse an incoming message out of this payload shape` (status callbacks, not messages; the bot returns 200): noise, [Likely] not new.

## Findings to act on
1. The webhook secret is printed in the access log (uvicorn logs the URL path `/whatsapp/webhook/<secret>`). It has now been pasted into this session as well. Recommendation: rotate WHATSAPP_WEBHOOK_SECRET and update the callback URL in Gupshup.
2. The bot logs every incoming webhook payload raw (`RAW incoming webhook payload`): phone number, profile name and the full text of the person's message, at INFO level. The website logs only a hash of the question. For real users this is personal data (DPDP) in Railway logs; reduce it before public use (a small code change, needs the owner's go and his own pull request).
3. No spending cap on the bot (no DAILY_BUDGET_INR / COST_STATE_FILE).
4. Parity gap: WhatsApp has no register (if REGISTER_HOOKS=off), v1 style, topic bar closed, no Act shelf, no wider search; the website has them. Bringing the bot level needs variables (SCOPE_GATE, ACT_SHELF, ACT_DETECT, SCI_SEARCH_*, RESPONSE_STYLE, budget) and, before ACT_SHELF or ACT_DETECT, the fix for the bot folding Recourse's own earlier answers into the next question.
