# Support-and-fit plan: countering "a real case that does not actually support the claim or fit the facts"

**STATUS: PARKED. Nothing in this file has been built. Do not start it.**
Owner's instruction, 2026-10-18: "Store this in memory for now. Keep it separately. Keep it as it is. We will do this, once the pending changes are fully done and the website is ready and functional."

**Trigger to bring it back:** the owner says the pending changes are done and the website is ready and functional. Raise it then, once and briefly, without being asked. Do not re-ask every session. It may also be mentioned once, briefly, if the owner raises accuracy, hallucination, citation support, `GROUNDING_CHECKS` or asks what is open.

**What the owner asked for (2026-10-18, verbatim):** "You said that the citation checker cannot say if the case really helps the situation even if the case cited is real. And that is a gap. Be innovative, strategic and after a proper research, tell me, how to counter that. Do not directly act on it. First tell me the plan that you have, and once approved we will proceed."
**Approval status:** the plan was presented; the owner did NOT approve it yet. He parked it. When the trigger fires, ask for approval (and the six decisions at the end of Part A) before building anything.

**Notes added when this was stored (not part of the plan text below):**
- Part A is the plan exactly as presented in chat on 2026-10-18. Part B is the plain-terms explanation given afterwards, also unchanged. Neither has been edited.
- Figures in the plan are as of 2026-10-18 and may be stale when the plan is revived: Anthropic prices (fetched live that day: Haiku 5.5 $0.10/$0.50 and Sonnet 5.5 $2/$10 per million tokens; Batch API 50% off), the Rs 8–13 cost per lawyer-module answer (measured 2026-10-16), the library card counts (cards generated 2026-10-06: 48 of 76 cases with 3 or more later citing judgments, 22 with none), and the role-tagger numbers (measured read-only on the 1,045 library case passages: 567 of 652 "reasoning" labels are defaults, 85 rest on a holding cue, 113 are tagged argument). Re-check them before relying on them.
- Related earlier deferral: the 50-question set and marking sheet (owner, 2026-10-17; FOLLOW_UPS 2ar). Step S0 below is a smaller, reshaped version of it.
- Not verified at the time: the Stanford paper's own wording of "misgrounded" (arXiv was blocked from the sandbox) and the July 2026 Supreme Court ruling's text (news coverage only). Both are marked [Likely] in the plan.
- The saved answers I re-read for the plan are in `review_results/2026-10-16_staging_scope_gate_test/answers_q1_q2_q3.txt` and `review_results/2026-10-16_production_after_merge/`; the reading was Claude's, not a lawyer's.

---

# PART A. The plan, as presented (unchanged)

No program can prove that a real case fits a user's facts, so "countering" this gap can only mean three things: make unsupported claims harder to write, catch most of the rest with an independent reader, and tell the user exactly what was and wasn't checked. The last step stays with a lawyer. [Certain]

Nothing below has a measured effect size yet; the costs are arithmetic on live prices with assumed token counts. I changed nothing in either repo.

**How big the gap is**
- Errors compound. With 3 case-uses in an answer, a 5% error per use puts a bad use in 14% of answers; with 8 uses (a Research Note), 34%. [Certain: arithmetic]
- We have never measured our rate. The only evidence is AI-marked search passages: of 34 marked misleading, 19 were replaced law (the register covers that), 8 were a party's submission passed off as the court's holding, 7 other. No lawyer has marked an answer for this.
- It's already visible. Re-reading the saved Q1–Q3 staging answers (about 8 case mentions; my reading, not a lawyer's):
  - Arnesh Kumar (about arrest) is stretched into "the backdrop for anticipatory bail pleas".
  - Bilal's facts are described though no fed passage contains them (FOLLOW_UPS 2ae).
  - An unrelated case sat in the sources box (since fixed).

  Three answers prove nothing about a rate. [Likely]
- Outside: Stanford found Lexis+ AI, Westlaw AI and Ask Practical Law AI wrong or unsupported in 17–33% of US-law queries despite "hallucination-free" marketing; the paper counts citing a source that doesn't support the claim as a hallucination (I couldn't open it from here; that definition is from memory). [Likely] A July 2026 Supreme Court ruling, reported as "zero tolerance", covered misattributed passages as well as invented judgments (news coverage; I haven't read the judgment). [Likely] So for lawyers, "real case, wrong content" is a professional-liability issue.

**What the research gives us**
1. Prompting alone doesn't close it: Anthropic's own guide says quote-first and retract-unsupported techniques reduce hallucinations but "don't eliminate them entirely". [Certain]
2. A writer's citation can be "correct" yet not what it relied on: up to 57% in an adversarial test (Wallat et al.). So the writer's own citations need an independent reader. [Likely]
3. Cheap independent checkers exist: a 770M model matched GPT-4 on a fact-checking benchmark at ~400× lower cost (MiniCheck), but the best public scores are ~75–80% (balanced accuracy / F1), lower on expert text. [Likely] A filter, not a judge, and it must be measured on Indian legal text with lawyer marks.
4. Legal research treats "on the topic" and "actually entails" as different problems (COLIEE's case-entailment task; CitaLaw's rule→facts→conclusion test). Court-filing trackers (Charlotin's database, via Stanford CIS) separate fabricated cases, false quotes or misrepresented real cases, and overturned cases; we cover the first and third, and the middle one is this gap. [Certain / Likely]
5. Claude's Citations feature returns the exact source span from the API, so a quote can't be misquoted and pointers are valid; it can point to a paragraph if we send each paragraph as its own block. It proves nothing about support, can't be combined with structured output (400 error) and is all-or-none per request. [Certain: read the docs today]

**Where we stand**

| A citation can claim… | Today |
|---|---|
| The case exists | Checked |
| These words are in the material | Checked (tightened 18 Oct) |
| …in that case's own passage | Not checked: the quote check can't tell which case the words came from |
| The sentence means what the passage says | Not checked (two narrow rules only) |
| The court held it, not a party | Weak: on the library, 567 of 652 "reasoning" labels are defaults; only 85 rest on a holding cue |
| Still good law | Register and cards, with their known limits |
| Fits this user's facts | Cannot be machine-checked |

**The plan** (each step behind a default-off switch with log → warn → enforce, like `GROUNDING_CHECKS`; pass/fail tests fixed before any run)

**S0 – A ruler.** Mr. Advocate marks ~150 case-uses (about 30 questions) as Supports / Overstated / Not in passage / Party's submission / Different issue / Doesn't fit facts. It gives the first real rate (±~5 points at n=150), the failure mix and the frozen test for everything below. AI markers can't stand in: the checker is an AI too, so their blind spots overlap (our two AI markers agree on only 71% of passages). This is a reshaped, smaller version of the 50-question set you deferred on 17 Oct; if it stays deferred, S2 runs blind.

**S1 – Free, no model (I can build and test it here).** Bind every quote to the case whose passage holds it, so words from another case are flagged; keep argument/header passages from being described as "the court held". Catches misattribution and the 8-in-34 "submission" class; won't catch stretches. [Likely feasible; I'd confirm in the code first]

**S2 – Independent support reader (the main new defence).** After the answer is written: one cheap call splits each case-claim into small statements (so "built around 498-A" and "backdrop for anticipatory bail" are judged apart); a second call, a different and cheaper model, sees only the statement and that case's passages — not the user's question, not the writer's reasoning — and says Supported / Overstated / Not in passage / Different issue. It must quote the words it relied on and **code re-checks those words in the passage; a verdict without a checkable quote counts as "unconfirmed"**. A third "attack" prompt hunts for the best reason it doesn't support; any disagreement means unconfirmed. Modes: log (users see nothing) → warn (a small "support not confirmed" tag) → enforce (the sentence is replaced by the verified quote; never withholds a whole answer). Running cost under Rs 1 per answer on Haiku-class, Rs 3–6 on Sonnet-class, against Rs 8–13 per lawyer-module answer today.

**S3 – Make fit visible, since it can't be proven.**
 (i) Reverse-question fingerprints: once per library passage, a model writes "this passage decides… / does not decide…" (cents for the library); the reader sees them and the lawyers' module prints them.
 (ii) "Not for" notes: Mr. Advocate writes one line for the ~25 most-used cases on what people wrongly cite them for (e.g., Arnesh Kumar: arrest procedure, not anticipatory bail); writer and reader both receive them.
 (iii) Later-court witness: what later Supreme Court benches cite the case for, quoted from our own corpus (mention finder, treatment labels). Independent of the writer. (The same citing-sentence → cited-passage pairing the CLERC dataset uses for US law.) Coverage: 48 of 76 library cases have ≥3 later citing judgments, 22 have none (cards of 6 Oct), so it's a second witness for about half.
 (iv) Conditions ledger, lawyers' module only: rule (verified quote) → conditions it depends on → facts from the user's own words that match → facts still unknown. "Fit" becomes a checklist the lawyer completes, not a hidden judgement.

**S4 – Honest labels.** Three states per authority: passage found and read as supporting this (machine-checked, not lawyer-checked) / case and quote found, support not confirmed / not found; paragraph link; one fixed line for laypeople that software checked what the case says, not whether it fits their facts. Never "good law", "accurate" or "safe".

**S5 – Keep measuring.** Fortnightly ~20 answers, ~30 min of Mr. Advocate; track the unsupported-use rate and reader-vs-lawyer agreement. Staging/test questions only; real users' answers need the DPDP consent work that isn't done. A routine needs your say-so.

**What I advise against**
- A "fit score" or confidence %: false precision.
- Letting the writer re-check itself in the same call (post-rationalisation).
- Using enforce before the false-alarm rate is known: a checker that strikes correct law makes the product worse and teaches users to ignore flags.
- Widening the public feed: unread wider-search passages each add case-uses the writer can mis-describe; the earlier rule stands (feed back to shadow before public launch).

**Limits that stay**: fit to the user's facts is a lawyer's call; the reader sees passages, not whole judgments, so a true passage can still be qualified elsewhere in the judgment; and checkers are ~75–80% right on hard sets. The end claim is "supported by the quoted words, as read by software and sampled by a lawyer at rate X", never "correct".

**Order, gates, cost**
S0 and S1 first; S2 in log mode on staging, scored on S0's frozen half. Proposed gate to warn, fixed before any run [Guessing, to agree with you]: at most 5% of reader-"supported" items are ones Mr. Advocate marks unsupported, it catches at least 70% of his "not supported", and at most 15% false alarms. S3 after S2's numbers; S4 with warn. Model spend for the whole build and tests ≈ $15–25 [Guessing]; generating the 30 answers ≈ Rs 240–390 on your staging bill.

**Decisions I need**
1. Order: S0 + S1 first?
2. Mr. Advocate: ~4 h for S0 (or ~2 h if he marks only flagged items plus a random slice), plus ~1.5 h for the "not for" notes?
3. An Anthropic key in the sandbox with a hard spend cap (as for Voyage) — without it I can't test any model step; alternative: you run my scripts on staging.
4. May I shape the deferred 50-question set into S0's 30?
5. Ledger (S3 iv) in the lawyers' module only (my recommendation)?
6. The Citations feature (exact spans, paragraph pointers): decide after S0, since it needs prompt restructuring.

Say "approved" (or name changes) and I start with S0's sheet and S1. If you want this as a page for Mr. Advocate, say so.

Sources:
- [Hallucination-Free? (Stanford, arXiv)](https://arxiv.org/html/2405.20362v1) · [Stanford HAI summary](https://hai.stanford.edu/news/ai-trial-legal-models-hallucinate-1-out-6-or-more-benchmarking-queries)
- [Anthropic: reduce hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations) · [Citations](https://platform.claude.com/docs/en/build-with-claude/citations) · [Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [Correctness is not Faithfulness in RAG Attributions](https://arxiv.org/pdf/2412.18004) · [MiniCheck](https://arxiv.org/abs/2404.10774v2) · [AttributionBench](https://arxiv.org/pdf/2402.15089) · [Bespoke-MiniCheck / LLM-AggreFact figures](https://docs.bespokelabs.ai/models)
- [COLIEE 2023](https://sites.ualberta.ca/~rabelo/COLIEE2023/) · [CitaLaw](https://preview.aclanthology.org/setup/2025.findings-acl.583) · [CLERC](https://arxiv.org/pdf/2406.17186) · [Stanford CIS on court-filing hallucinations](https://cyberlaw.stanford.edu/whos-submitting-ai-tainted-filings-in-court/)
- [Free Press Journal on the Supreme Court ruling](https://www.freepressjournal.in/mumbai/supreme-court-declares-zero-tolerance-for-ai-generated-fake-legal-precedents-directs-bar-council-to-act) · [MediaNama](https://www.medianama.com/2026/03/223-supreme-court-ai-fake-case-laws-misconduct/)

---

# PART B. The plain-terms explanation of Part A, as given afterwards (unchanged)

The gap is that our checks prove a case exists and that quoted words are really in it. They do not prove the case supports the sentence we wrote about it, or fits the user's situation. You can't remove that gap completely, only shrink it and make it visible. I changed nothing in either repo. The plan is a proposal waiting for your approval.

## The opening point

No computer program can prove that a real case fits a particular person's facts. So "countering" the gap means three things:
1. Make it harder for the AI to write claims the case doesn't support.
2. Use a second, independent reader to catch most of the claims that slip through.
3. Tell the user exactly what was checked and what wasn't.

The final step, deciding whether a case fits, stays with a lawyer. [Certain]

I also said that nothing in the plan has a measured effect yet. The costs are arithmetic on today's price list, using token counts (the units AI models charge by) that I assumed.

## How big the gap is

**1. Small errors add up across citations.** If an answer cites 3 cases and each has a 5% chance of being misused, then 14% of answers contain at least one bad use. With 8 citations, as in a lawyer-style Research Note, it is 34%. [Certain, because it's arithmetic.]

**2. We have never measured our own error rate.** The only evidence is from an earlier test where AI "markers" (ChatGPT and Gemini, not lawyers) judged search results. Of 34 passages they called misleading:
- 19 were rulings later replaced by newer law. The register and cards already cover this.
- 8 were a lawyer's or party's argument presented as if it were the court's decision.
- 7 were other problems.

No lawyer has ever marked a finished answer for this problem.

**3. The problem is already visible in our own saved answers.** I re-read the saved Q1–Q3 staging answers, about 8 case mentions. This is my reading, not a lawyer's.
- Arnesh Kumar is a case about police arrest. The answer stretched it into "the backdrop for anticipatory bail pleas".
- The answer described the facts of the Bilal case, but none of the passages we gave the AI contained those facts (FOLLOW_UPS item 2ae).
- An unrelated case (NALSA) appeared in the sources box. That has since been fixed.

Three answers say nothing about the overall rate. [Likely]

**4. Outside evidence.**
- A Stanford study tested Lexis+ AI, Westlaw AI and Ask Practical Law AI. These are expensive commercial legal tools. They gave wrong or unsupported answers in 17–33% of US-law questions, even though they were marketed as "hallucination-free".
- I couldn't open the paper from here. That it counts "cites a source that doesn't support the claim" as a hallucination is from my memory. [Likely]
- A July 2026 Supreme Court ruling was reported as showing "zero tolerance". It covered misattributed passages as well as invented judgments. This comes from news coverage, and I haven't read the judgment. [Likely]
- So for lawyers, citing a real case for something it doesn't say is a professional-liability issue, not just a quality issue.

## What the research says

1. **Prompting alone isn't enough.** Anthropic's own guide recommends asking for quotes first and withdrawing unsupported claims. It says these techniques reduce hallucinations but "don't eliminate them entirely". [Certain]
2. **The AI's own citations can't be trusted by themselves.** A citation can be correct but not be what the AI actually relied on. In one adversarial test, up to 57% of citations were like this (Wallat et al.). So an independent reader is needed. [Likely]
3. **Cheap independent checkers exist, but they are imperfect.**
   - A small 770-million-parameter model (MiniCheck) matched GPT-4 on a fact-checking benchmark at about 400 times lower cost.
   - The best public scores are only about 75–80%, and lower on expert text.
   - So they filter out bad claims but can't be the final judge.
   - They must be tested on Indian legal text, using lawyer marks. [Likely]
4. **"On the same topic" and "actually supports it" are different problems.**
   - COLIEE's case-entailment task and CitaLaw's rule→facts→conclusion test treat them that way.
   - Trackers of AI mistakes in court filings (Charlotin's database, as summarised by Stanford CIS) list three kinds: invented cases, false quotes or misrepresented real cases, and overturned cases.
   - We cover the first and third. The middle one is our gap. [Certain / Likely]
5. **Claude's Citations feature** returns the exact source passage from the API itself.
   - A quote can't be misquoted, and pointers are valid.
   - It can point to a paragraph if we send each paragraph as its own block.
   - It does not prove the passage supports the claim.
   - It can't be combined with "structured output" mode (that returns an error).
   - It is all-or-none per request: every document in a request must have it on, or none.
   - [Certain, because I read the docs today.]

## Where we stand today

| A citation can claim… | Today |
|---|---|
| The case exists | Checked |
| These words are in the material | Checked (tightened on 18 Oct) |
| …in that case's own passage | Not checked. The quote check can't tell which case the words came from. |
| The sentence means what the passage says | Not checked (only two narrow rules) |
| The court held it, not a party | Weak. On the library, 567 of 652 "reasoning" labels are just defaults, and only 85 rest on a real "we hold…" style cue. |
| Still good law | Register and cards, with their known limits |
| Fits this user's facts | Cannot be machine-checked |

## The plan

Each step would sit behind a switch that is off by default. It would go through three stages, as `GROUNDING_CHECKS` does:
- **log:** it runs silently and users see nothing.
- **warn:** users see a small tag.
- **enforce:** the system acts on it automatically.

Pass/fail tests are fixed before any run.

### S0 – A ruler: measure first
- Mr. Advocate marks about 150 case-uses, from roughly 30 questions.
- Each gets one label: Supports / Overstated / Not in passage / Party's submission / Different issue / Doesn't fit the facts.
- This gives the first real error rate, with a margin of about ±5 points. It also shows the mix of failure types and gives a fixed test for everything after it.
- AI markers can't replace him, because the checker is also an AI and they share blind spots. Our two AI markers agreed on only 71% of passages.
- This is a smaller, reshaped version of the 50-question set you deferred on 17 Oct. If it stays deferred, S2 runs blind, with no way to know how good it is.

### S1 – Free, no AI model (I can build and test it here)
- Tie every quote to the specific case whose passage contains it, so words taken from a different case get flagged.
- Stop argument passages and headers from being described as "the court held".
- This catches misattribution and the "party's argument" class (8 of 34 above). It will not catch stretches like the Arnesh Kumar one.
- I think this is feasible, but I'd confirm it in the code first. [Likely]

### S2 – An independent support reader (the main new defence)
After the answer is written:
1. A cheap AI call breaks each case-claim into small statements. That way "built around 498-A" and "backdrop for anticipatory bail" are judged separately.
2. A second AI call, to a different and cheaper model, sees only the statement and that case's passages. It does not see the user's question or the writer's reasoning. It answers Supported / Overstated / Not in passage / Different issue.
3. It must quote the words it relied on. **Our code then checks that those words are really in the passage.** A verdict without a checkable quote counts as "unconfirmed".
4. A third "attack" prompt looks for the best reason the case does not support the claim. Any disagreement means unconfirmed.
5. Modes: log (users see nothing), then warn (a small "support not confirmed" tag), then enforce (the sentence is replaced by the verified quote). A whole answer is never withheld.
6. Running cost is under Rs 1 per answer with a Haiku-class (small, cheap) model, or Rs 3–6 with a Sonnet-class model. A lawyer-module answer costs Rs 8–13 today.

### S3 – Make "fit" visible, since it can't be proven
- **(i) Reverse-question fingerprints.** Once per library passage, an AI writes "this passage decides… / does not decide…". It costs cents for the whole library. The reader sees these, and the lawyers' module prints them.
- **(ii) "Not for" notes.** Mr. Advocate writes one line for each of the ~25 most-used cases, saying what people wrongly cite it for. For example, Arnesh Kumar is about arrest procedure, not anticipatory bail. The writer and the reader both receive these notes.
- **(iii) A later-court "witness".**
  - It shows what later Supreme Court benches cite the case for, quoted from our own collection of judgments (using the mention finder and treatment labels).
  - It's independent of the writer. CLERC, a US dataset, pairs citing sentences with the cited passages in the same way.
  - Coverage is partial. Of 76 library cases, 48 have at least 3 later citing judgments and 22 have none (cards of 6 Oct). So it's a second witness for about half the library.
- **(iv) A conditions ledger, in the lawyers' module only.** It lists the rule (a verified quote), the conditions it depends on, the facts from the user's own words that match, and the facts still unknown. "Fit" becomes a checklist the lawyer completes instead of a hidden judgement.

### S4 – Honest labels on screen
Each authority shows one of three states:
- Passage found and read as supporting this (machine-checked, not lawyer-checked).
- Case and quote found, but support not confirmed.
- Not found.

Each also gets a link to the paragraph. Laypeople see one fixed sentence: software checked what the case says, not whether it fits their facts. The site never says "good law", "accurate" or "safe".

### S5 – Keep measuring
- Sample about 20 answers a fortnight, about 30 minutes of Mr. Advocate's time.
- Track the rate of unsupported case-uses, and how often the reader agrees with the lawyer.
- Use staging and test questions only. Real users' answers would need the privacy-consent (DPDP) work, which isn't done.
- A recurring routine for this needs your say-so.

## What I advise against
- **A "fit score" or confidence percentage.** It would look precise but have no real basis.
- **Letting the writing AI re-check itself in the same call.** It tends to justify what it already wrote.
- **Turning on enforce before we know the false-alarm rate.** A checker that strikes out correct law makes the product worse and teaches users to ignore warnings.
- **Widening the public feed.** Passages from the wider search that nobody has read give the writer more cases to describe wrongly. The earlier rule still stands: switch the feed back to shadow mode before public launch.

## Limits that remain
- Fit to the user's facts is a lawyer's call.
- The reader sees passages, not whole judgments. A true passage can still be qualified elsewhere in the same judgment.
- Checkers are only about 75–80% right on hard test sets.

So the most we could honestly say is: "supported by the quoted words, as read by software and sampled by a lawyer at rate X". We could never say "correct".

## Order, gates and cost
- S0 and S1 come first.
- Then S2 in log mode on staging, scored against S0's reserved test half.
- S3 follows S2's results, and S4 ships when S2 moves to warn.
- My proposed gate to move S2 to warn is below. I fixed it before any run, and it's a guess for us to agree on. [Guessing]
  - At most 5% of the reader's "supported" items are ones Mr. Advocate marks unsupported.
  - It catches at least 70% of his "not supported" items.
  - No more than 15% false alarms.
- Model spend for the whole build and tests is about $15–25. [Guessing]
- Generating the 30 S0 answers on your staging site costs about Rs 240–390 on your bill.

## Decisions I need from you
1. Do S0 and S1 go first?
2. How much of Mr. Advocate's time can we have?
   - About 4 hours for S0, or about 2 hours if he marks only flagged items plus a random slice.
   - About 1.5 hours for the "not for" notes.
3. Can I have an Anthropic API key in the sandbox with a hard spending cap, as with Voyage? Without it I can't test any AI step. The alternative is that you run my scripts on staging.
4. May I shape the deferred 50-question set into S0's 30 questions?
5. Should the conditions ledger (S3 iv) go in the lawyers' module only? That's my recommendation.
6. The Citations feature needs prompt restructuring, so I'd decide on it after S0.

If you say "approved", or name changes, I start with S0's sheet and S1. I can also turn the plan into a page to send to Mr. Advocate.

## Sources I used
- Stanford study: [Hallucination-Free? (arXiv)](https://arxiv.org/html/2405.20362v1) and the [Stanford HAI summary](https://hai.stanford.edu/news/ai-trial-legal-models-hallucinate-1-out-6-or-more-benchmarking-queries)
- Anthropic docs: [reduce hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations), [Citations](https://platform.claude.com/docs/en/build-with-claude/citations) and [Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- Papers: [Correctness is not Faithfulness](https://arxiv.org/pdf/2412.18004), [MiniCheck](https://arxiv.org/abs/2404.10774v2) and [AttributionBench](https://arxiv.org/pdf/2402.15089)
- Benchmark figures: [Bespoke-MiniCheck / LLM-AggreFact](https://docs.bespokelabs.ai/models)
- Legal research: [COLIEE 2023](https://sites.ualberta.ca/~rabelo/COLIEE2023/), [CitaLaw](https://preview.aclanthology.org/setup/2025.findings-acl.583) and [CLERC](https://arxiv.org/pdf/2406.17186)
- Court filings and India: [Stanford CIS on court-filing hallucinations](https://cyberlaw.stanford.edu/whos-submitting-ai-tainted-filings-in-court/), [Free Press Journal on the Supreme Court ruling](https://www.freepressjournal.in/mumbai/supreme-court-declares-zero-tolerance-for-ai-generated-fake-legal-precedents-directs-bar-council-to-act) and [MediaNama](https://www.medianama.com/2026/03/223-supreme-court-ai-fake-case-laws-misconduct/)
