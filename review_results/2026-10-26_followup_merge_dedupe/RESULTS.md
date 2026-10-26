# (a) Follow-up retrieval merge and (b) library cases kept out of the wider search (2026-10-26)

Owner's go, 2026-10-26: "Yes, build a and b ..." (item (c), a section shown whole in the sources box, was NOT approved and is not built). Neither piece has a switch: (a) acts only on a message that carries a rewrite (so only with `CHAT_MODE` on) and (b) only in feed mode (`SCI_SEARCH_MODE=feed`). Nothing was tried with the answer model.

## (a) A follow-up is searched on the person's own words as well

**The defect** (FOLLOW_UPS 2cl, from the owner's staging PDF): the follow-up "is bail possible in this case?" reaches the engine as the person's words, a line break, then the rewrite "(Read with the earlier messages, this asks: ...)". The library search ran on that whole string, so the earlier matter (Armed Forces, delay) drowned the bail words, and the answer rested on BNSS 83 (a warrant executed outside the district) and never mentioned the bail sections BNSS 480, 482, 483, which the library holds.

**The change** (`chat_assistant._find_relevant_sections_for_turn`, `_add_own_words_search`, `_merge_follow_up_results`): when the message carries a rewrite, one more library search runs on the person's own words alone, and its sections and judgments are merged with the first search's, interleaved with the own words first, repeats dropped, at most 7 statutes and 5 judgments (the ordinary search keeps 5 and 4). Rules: the result's state stays "single_match" (the extra sections are context, not a finding that the law forks); a "conflicting_matches" result is left alone; if the first search found nothing and the own words find something, the own-words result is used; any failure leaves the first result as it was. One log line, `CHAT_MERGE`, holds counts only (never words or sections). A first message, a message with no rewrite, and WhatsApp are searched exactly once, as before.

**On the real library** (`demo_a_output.txt`; real Voyage embedding, a fraction of a cent): the rewrite the engine received in the owner's test is not logged, so three plausible rewrites were written by Claude and run before and after.

| rewrite (Claude's) | bail sections before | after |
|---|---|---|
| "Is bail possible for a person arrested by the army under the Armed Forces Special Powers Act, where the trial is delayed?" | **none** (BNSS 521, 42; Vihaan Kumar, Pankaj Bansal) | + BNSS 139, **480**, 488, **482** |
| "Can a person arrested under a special law in a disturbed area be granted bail when the trial has been delayed for years?" | already BNSS 479, 480 | + 139, 488, 482 |
| "...arrested by armed forces personnel and kept in custody for a long time without trial?" | already BNSS 478, 480 | + 139, 488, 482 |

So the merge repairs the case where the rewrite's words drown the bail words (1 of 3 here) and otherwise adds a few weaker sections (BNSS 139 and 488 score 0.35-0.36, just above the 0.34 threshold) at the price of up to two more sections in the prompt. [Certain: the table. Likely: that the owner's real rewrite behaved like the first; it cannot be checked.] Cost: one more embedding of a few words (about Rs 0.0001) and a local keyword search, a few tenths of a second.

Tests: `test_followup_merge.py` (39 checks: the own-words extractor; the merge rules and caps; the wrapper with its log line and fail-open; the entry point searched twice for a follow-up and once for anything else; the old fallback to the full question still runs first).

## (b) A library case is not handed over again as a "wider search" case

**The defect** (2cl): Pankaj Bansal (2023 INSC 866) was among the library matches and came again from the wider search, so the answer called it "(from a wider search, not independently verified)" and said its currency had not been checked, while the table beside it said "No adverse later judgment found by our automatic check".

**The change** (`sci_search_tier.feed_block(question, exclude_names)`, `library_keys`, `is_library_case`; the call in `generate_grounded_response`; a second guard in `attach`): the judgments among the answer's library matches are left out of the wider-search passages (a result is "the same case" by the register's own name rule and, where both sides give a year, the same year; a controlling case fetched by a second search is also skipped if the library has it), and `attach` removes any such case from the page's wider-search list and from the labelling, whatever reached the prompt. The cache of the block is now per question and per library list. One log line, `SCI_FEED_LIBRARY`, names what was left out.

**On real data** (`demo_b_output.txt`; the real newer index, the real recipe, the real library retrieval; no answer model): for "Must the police give the grounds of arrest in writing to a person arrested under the money laundering law?" the library supplies Pankaj Bansal, Prabir Purkayastha and Vihaan Kumar; the wider search returned 10 passages, 8 cases once repeats are dropped, among them Pankaj Bansal and Vihaan Kumar. Without the exclusion, 8 cases were fed; with it, 6, and the two library cases are gone from the prompt and from the page's list.

**A second defect found by that same run, fixed** [Certain, shown on real data]: the answer text still carried "(from a wider search...)" after "Pankaj Bansal v. Union of India (2023)", although Pankaj Bansal was no longer a wider-search case. Cause: the labeller finds a case's first mention "by its second party alone"; the wider-search case *Vijay Madanlal Choudhary & Ors v. Union of India & Ors* was therefore found at the words "Union of India" in another case's name, and its label landed there. `_second_party_span` now accepts a generic second party ("Union of India", "State of ...") only when the words before the "v." resemble the case's own first party (`_first_party_agrees`: a shared word of three letters or more, or a close spelling). A shortened or misspelt first party is still found (tests: "Nikesh Shah v. Union of India", "Vijai Madanlal Choudary v. Union of India", "Sadhwi Pragya v. State of Maharashtra"); a different case against the same respondent is not. Re-run on the same real data: the library case carries no label and the genuine wider-search case does. This bug could put the label on *any* case with a "Union of India" or "State of ..." respondent, so the owner's earlier sighting of a mislabelled case may have come from this and not only from the overlap [Guessing].

**Not done:** a library judgment that is NOT among this answer's library matches (the library holds 68 judgments; each answer retrieves a few) still arrives as a wider-search case and is labelled so; a pilot-tier case is not excluded (it already carries its own hedged label).

Tests: `test_library_dedupe.py` (34 checks; the label guard is in the last block).
