# Cost per answer, 2026-11-16 (owner: "Measure the cost per answer")

**What this is NOT:** a measurement of today's real cost. The sandbox has no Anthropic key, and the repository holds no cost log line later than 2026-10-20 and none for a lawyer's answer. Two things were done: (1) every stored real `COST_QUESTION` line was parsed (`parse_cost_lines.py`); (2) today's real prompt for 10 questions was captured with the answer model stubbed (`prompt_size.py`, output `prompt_size.json`), and input tokens were estimated at 3.6 to 4.2 characters a token (the tokenizer was not available; this ratio is a guess, not calibrated).

## 1. Real, stored (17 layman lines, October, v3, effort medium, Rs 94.98 to 96.5 a dollar)
- Rs 2.25 to 4.58 per answer for 16 of 17 (median 3.60, mean 3.83 over all 17); one at Rs 8.70 where the answer was asked for twice (about 32,000 input tokens).
- Answer call: 5,000 to 17,000 input tokens, 800 to 1,070 output tokens (the output includes the model's thinking). Everything else (scope check, embeddings, wider-search re-rank) about Rs 0.45 to 0.5.
- Lawyer answers: no stored line. The only figures are in FOLLOW_UPS 2x: Rs 8.01 (one call) and Rs 13.36 (answer Rs 6.41 + `answer_recheck` Rs 6.52). From Rs 8.01 at 15,230 input tokens the output works out to about 5,000 tokens: one data point.

## 2. Today's prompt, offline (production switches on; wider search NOT run, so add about 2,000 to 4,000 input tokens where it is on)
Answer-call prompt, 20 runs (10 questions x 2 audiences): median about 24,000 characters (about 6,000 tokens), range 13,000 to 72,000 (3,100 to 20,000 tokens). The layman and the lawyer prompt differ by about 700 characters: the audience difference is in the OUTPUT length, not the input.
Three of ten questions (job cheating, arrest legality, bail after arrest) hand over 57,000 to 72,000 characters (14,000 to 20,000 tokens): whole BNSS sections and the companions.
Rupees at Sonnet-5 prices (2 and 10 dollars a million tokens, Rs 96.5): input-only part Rs 0.7 to 4.7; each 1,000 output tokens add Rs 0.97.

## 3. Estimate, not measurement
| | no retry | one retry (second full answer) |
|---|---|---|
| Layman, typical (6k to 10k in, about 900 out, + Rs 0.5 other) | about Rs 2.5 to 4.5 | about Rs 5 to 9 |
| Layman, heavy (17k to 20k in) | about Rs 4.5 to 5.5 | about Rs 9 to 11 |
| Lawyer, typical (about 5,000 out; single data point) | about Rs 6 to 10 | about Rs 12 to 20 |
Per 250 answers a month: layman about Rs 900 to 1,100; lawyer about Rs 1,500 to 2,500 before retries. The retry rate is unknown for lawyers (1 of 17 stored layman lines retried).

## 4. What would make it a measurement
The `COST_QUESTION` lines of `staging-api` (or the production website service) for the last week, exported from Railway's log search; run `parse_cost_lines.py` on them (it reads any `.log` under `review_results/`). Needs: at least 20 layman and 20 lawyer lines, with the build commit field.
Say "no hallucination rate has been measured". Prices as coded in `cost_log.py` (list of 2026-10-06; Voyage re-ranker price not checked with Voyage).
