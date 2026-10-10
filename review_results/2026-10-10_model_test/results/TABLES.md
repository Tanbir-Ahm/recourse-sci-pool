Verdict by the pre-registered rule: **NOT-PASS**  (valid: True)

### Validity checks

- V1_merge_replica_equals_engine: True
- V2_candidates_equal_saved: True
- V3_pool_A0_first_stage_equals_whole_index: True
- V4_A0_reproduces_recorded_ranks: True
- V4_detail_off: {'R12': [6, 5]}
- V5_vector_sizes_checked_at_embedding: True
- all_ok: True

### Final top 10 (the search as it would run): place of the first passage of a key judgment, and whether a key passage is among the 60 candidates

| Question | A0 law-2 | A1 4-large | A2 4-lite q. | A2b 4 q. | key passage among the 60 candidates: A0 / A1 / A2 / A2b | recorded in AUTHORITY_HITS (version A) |
|---|---|---|---|---|---|---|
| R01 | 1 | 1 | 1 | 1 | yes / yes / yes / yes | 1 |
| R02 | 1 | 1 | 1 | 1 | yes / yes / yes / yes | 1 |
| R04 | 2 | 2 | 2 | 2 | yes / yes / yes / yes | 2 |
| R08 | 2 | 2 | 2 | 2 | yes / yes / yes / yes | 2 |
| R09 | - | - | - | - | yes / yes / yes / yes | - |
| R11 | 3 | 2 | 9 | 4 | yes / yes / yes / yes | 3 |
| R12 | 6 | - | - | - | yes / yes / yes / yes | 5 |
| R14 | - | - | - | - | no / no / no / no | - |
| R17 | 1 | 1 | 1 | 1 | yes / yes / yes / yes | 1 |
| R19 | 1 | 1 | 1 | 1 | yes / yes / yes / yes | 1 |
| R20 | - | - | - | - | yes / yes / yes / yes | - |
| R22 | - | - | - | - | no / no / no / no | - |
| R24 | 1 | 1 | 1 | 1 | yes / yes / yes / yes | 1 |
| R26 | 4 | 2 | 2 | 2 | yes / yes / yes / yes | 4 |

| Arm | key in top 1 | in top 5 | in top 10 | key among the 60 candidates | dense-only, in the pool, judgment level: top 1 / 3 / 5 / 10 | mean reciprocal rank |
|---|---|---|---|---|---|---|
| A0 | 5 | 9 | 10 | 12 of 14 | 5 / 5 / 8 / 9 | 0.4302 |
| A1 | 5 | 9 | 9 | 12 of 14 | 5 / 7 / 9 / 11 | 0.4846 |
| A2 | 5 | 8 | 9 | 12 of 14 | 3 / 7 / 8 / 11 | 0.3965 |
| A2b | 5 | 9 | 9 | 12 of 14 | 5 / 8 / 9 / 11 | 0.4797 |

### Dense-only place of the key judgment among the pool's judgments (the discrimination view; the re-ranker is not involved)

| Question | A0 | A1 | A2 | A2b | pool: passages / judgments |
|---|---|---|---|---|---|
| R01 | 1 | 2 | 2 | 2 | 1036 / 120 |
| R02 | 1 | 1 | 2 | 1 | 1605 / 174 |
| R04 | 5 | 1 | 1 | 1 | 890 / 61 |
| R08 | 4 | 4 | 4 | 3 | 506 / 132 |
| R09 | 12 | 8 | 10 | 10 | 535 / 108 |
| R11 | 1 | 1 | 2 | 1 | 1726 / 133 |
| R12 | 17 | 46 | 15 | 22 | 548 / 189 |
| R14 | 183 | 116 | 90 | 70 | 614 / 186 |
| R17 | 1 | 6 | 9 | 8 | 657 / 134 |
| R19 | 1 | 1 | 1 | 1 | 636 / 130 |
| R20 | 11 | 2 | 3 | 4 | 531 / 71 |
| R22 | 42 | 80 | 81 | 68 | 985 / 201 |
| R24 | 5 | 1 | 1 | 1 | 878 / 159 |
| R26 | 9 | 5 | 6 | 3 | 916 / 185 |

### Key passages in each arm's first-stage list (100 nearest) and among the 60 candidates

| Question | first stage A0 / A1 / A2 / A2b | candidates A0 / A1 / A2 / A2b |
|---|---|---|
| R01 | 8 / 21 / 23 / 23 | 4 / 11 / 11 / 11 |
| R02 | 39 / 40 / 36 / 39 | 25 / 25 / 22 / 25 |
| R04 | 32 / 43 / 43 / 42 | 21 / 24 / 25 / 23 |
| R08 | 11 / 13 / 10 / 10 | 8 / 8 / 8 / 7 |
| R09 | 3 / 6 / 6 / 5 | 2 / 2 / 2 / 1 |
| R11 | 12 / 6 / 10 / 14 | 4 / 3 / 2 / 3 |
| R12 | 2 / 1 / 1 / 1 | 2 / 1 / 2 / 2 |
| R14 | 0 / 0 / 0 / 1 | 0 / 0 / 0 / 0 |
| R17 | 4 / 7 / 6 / 6 | 2 / 4 / 2 / 3 |
| R19 | 10 / 14 / 13 / 11 | 6 / 10 / 8 / 8 |
| R20 | 8 / 7 / 7 / 7 | 3 / 3 / 3 / 3 |
| R22 | 2 / 0 / 0 / 1 | 0 / 0 / 0 / 0 |
| R24 | 11 / 21 / 14 / 19 | 8 / 13 / 10 / 15 |
| R26 | 7 / 11 / 10 / 11 | 6 / 6 / 6 / 7 |

### The rule

- rule_A1: rescues []; gain at 5 = +0; gain at 10 = -1; losses ['R12']; candidate-mix effects ['R11', 'R26']; conditions {'rescues>=1': False, 'gain10>=1': False, 'losses==0': False, 'gain5>=0': True}; **passed: False**
- rule_A2_same_test: rescues []; gain at 5 = -1; gain at 10 = -1; losses ['R12']; candidate-mix effects ['R26']; conditions {'rescues>=1': False, 'gain10>=1': False, 'losses==0': False, 'gain5>=0': False}; **passed: False**

Spend (listed, unchecked prices): {'embed': {'voyage-law-2': 878, 'voyage-4-large': 2660941, 'voyage-4-lite': 751, 'voyage-4': 751}, 'rerank': 382726, 'calls': {'voyage-law-2': 14, 'voyage-4-large': 65, 'voyage-4-lite': 14, 'voyage-4': 14}}  | about $0.3386
