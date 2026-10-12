# Fix test, stage D: the mechanical gate (PRIVATE)

Run 2026-10-12T07:31:45Z; index `3c80a26`; rules `0190876e3258`; code `1740db78fe`; 22 questions (19 tuning + R16, R23, R03 as a check, not a test).
Source label: the named key authority found in the index by name; no reviewer mark; nothing here says a passage answers a question. Not lawyer-checked.

## The four conditions (rules section 3)

| Arm | answerable tuning questions | named authority top 5 | top 10 | stale slots top 5 (questions) | R16 key judgment in top 5 (rank) | R23 rank | R03 rank | tokens vs B |
|---|---|---|---|---|---|---|---|---|
| B baseline (rerank-3-lite) | 14 | 9 | 11 | 1 (1) | no (#None) | #None | #None | 1.00 |
| C cap 2 per judgment | 14 | 9 | 11 | 1 (1) | no (#None) | #None | #None | 1.00 |
| N1 named-Act boost (precise) | 14 | 9 | 11 | 1 (1) | no (#7) | #None | #None | 1.00 |
| N2 named-Act boost (broad) | 14 | 9 | 11 | 1 (1) | no (#7) | #None | #None | 1.00 |

## Verdict (all four must hold; an arm that fails is dropped, not retuned)

| Arm | 1 authority top 10 >= B | 2 stale <= B | 3 R16 | 4 tokens | goes to stage F |
|---|---|---|---|---|---|
| C cap 2 per judgment | yes | yes | NO | yes | **NO** |
| N1 named-Act boost (precise) | yes | yes | NO | yes | **NO** |
| N2 named-Act boost (broad) | yes | yes | NO | yes | **NO** |

## How much each arm changed (not gated)

| Arm | questions | top 5 differs from B | top 10 differs from B |
|---|---|---|---|
| C cap 2 per judgment | 22 | 5 | 5 |
| N1 named-Act boost (precise) | 22 | 3 | 3 |
| N2 named-Act boost (broad) | 22 | 5 | 7 |

## Which Acts fired (question side)

| Question | N1 | N2 |
|---|---|---|
| R08 | NI Act | NI Act |
| R09 | NI Act | NI Act |
| R11 | - | NDPS |
| R15 | - | DPA |
| R19 | - | POCSO |
| R24 | - | PMLA |
| R16 | PWDVA | PWDVA |
