# Fix test (rules v2), stage D2: the mechanical gate (PRIVATE)

Run 2026-10-12T07:59:06Z; index `3c80a26`; rules v2 `d2f2be58da05`; code `dcc69094d2`; 22 questions (19 tuning + R16, R23, R03 as a check, not a test).
Source label: the named key authority found in the index by name; no reviewer mark; nothing here says a passage answers a question. Not lawyer-checked. The R16 condition is NOT independent evidence (rules v2, section 2, condition 3).

| Arm | answerable tuning questions | named authority top 5 | top 10 | stale slots top 5 | R16 key judgment in top 5 (rank) | R23 rank | R03 rank | top 5 differs from B on |
|---|---|---|---|---|---|---|---|---|
| B baseline (rerank-3-lite) | 14 | 9 | 11 | 1 (1) | no (#None) | #None | #None | 0 of 22 |
| N1-125 named-Act boost x1.25 (precise) | 14 | 9 | 11 | 1 (1) | yes (#3) | #None | #None | 3 of 22 |
| N1-150 named-Act boost x1.50 (precise) | 14 | 9 | 11 | 1 (1) | yes (#3) | #None | #None | 3 of 22 |
| N2-125 named-Act boost x1.25 (broad) | 14 | 9 | 11 | 1 (1) | yes (#3) | #None | #None | 5 of 22 |
| N2-150 named-Act boost x1.50 (broad) | 14 | 9 | 11 | 1 (1) | yes (#3) | #None | #None | 6 of 22 |

## Verdict (all five must hold)

| Arm | 1 authority top 10 >= B | 2 stale <= B | 3 R16 | 4 tokens | 5 top 5 changed on <= 8 | passes |
|---|---|---|---|---|---|---|
| N1-125 named-Act boost x1.25 (precise) | yes | yes | yes | yes | yes | **yes** |
| N1-150 named-Act boost x1.50 (precise) | yes | yes | yes | yes | yes | **yes** |
| N2-125 named-Act boost x1.25 (broad) | yes | yes | yes | yes | yes | **yes** |
| N2-150 named-Act boost x1.50 (broad) | yes | yes | yes | yes | yes | **yes** |

## Finalists (rules v2, section 1.4: per trigger the smaller passing size)

- N1: N1-125 named-Act boost x1.25 (precise)
- N2: N2-125 named-Act boost x1.25 (broad)

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
