# Case page ("Judgment at a Glance") idea: STORED, NOT APPROVED, NOT STARTED (owner, 2026-10-21: "Keep this idea in memory for now. We will pick it up from here.")

Owner's trigger: a mockup of a one-screen judgment page (case details, key issue, relevant law, key arguments, court's decision, key takeaways, citations, related judgments, tags, "Verified Source"). Do not re-ask every session; raise it once, briefly, when the owner says to pick it up or asks what is open. Evidence and numbers: `review_results/2026-10-20_case_page_coverage/RESULTS.md`; FOLLOW_UPS 2bn and 2bo.

## Verdict given (2026-10-20/21)
Buildable only as "extract, don't compose". Never a free-form AI summary, never a "Verified Source" badge (texts are machine-checked, nobody has read them), never generated "Key takeaways" except on lawyer-reviewed cases. The mockup's own sample card is wrong against our data (Sibbia is a Constitution Bench anticipatory-bail case under CrPC 438, (1980) 2 SCC 565; the NDPS Act is a 1985 statute).

## Coverage (upper bounds; section tags are rule-made and unchecked by a lawyer)
10,503 criminal Supreme Court judgments in the index (to 2026-07-13) -> 9,727 with name+date+link -> 9,244 real judgments (3,000+ characters) -> 5,241 with paragraph numbers -> 3,012 also with an order-tagged passage -> 2,687 also with an argument-tagged passage. Not covered: 33,395 non-criminal judgments, all High Courts. Only 66 library cases have treatment labels (cards).

## Method options, ranked
A free AI summary (reject); B extract, don't compose: a model returns sentence pointers, CODE copies the exact words (good, unmeasured); C the library route: person plus model write claims and quotes, code checks quotes, Gemini reads BLIND and checks the claims, code re-checks Gemini's quotes, a person approves (`second_reader.py`, `add_pilot_case.py` in Recourse; highest trust, ~60 cases, cannot scale without a person); D = B plus the Gemini cross-check with no person (pilot later, behind a switch); E lawyer-written cards (only for takeaways); F data page only (header, statutes with CrPC to BNSS mapping, later treatment, full text, link).
Real example (Arnesh Kumar v. State of Bihar, index doc 41736): 14 passages, no paragraph numbers (page numbers only), no argument-tagged passage, and directions (1) to (5) sit in a passage tagged "reasoning" while only direction (6) onward is tagged "order": a decision panel built from the order tag alone would drop the most important directions. So the model must read the end of the whole judgment, not tags.

## Recommendation (the "best now")
1. Build first, no model, no Railway: a case-record builder (name, court, date, link, statutes, attribution) for the 9,727; run the later-treatment finder for these targets (free code) BEFORE any decision panel shows on them; the treatment line sits ABOVE the decision panel.
2. Library "gold" cards for the ~60 library cases with the existing pipeline (needs a Gemini key and a person to approve).
3. Mr. Advocate marks about 10 pages: the first real error rate for this method and the first slice of the agreed question set (D8).
4. Only then pilot D (B plus second reader) on cases actually cited in answers, built on demand and cached, behind a switch, shown only where the bench is small (rule: no generated decision panel for benches of five or more or where a dissent is detected; Constitution Bench opinions can be separate) and the treatment line is clean.
Unknowns, none measured: whether Claude/Gemini agreement predicts correctness; cost per page (guess Rs 1 to 5 for the Claude call); how many panels survive the checks. Open question to the owner: include a paid Gemini key now or only after step 3 (free tier throttles and may train on content).
