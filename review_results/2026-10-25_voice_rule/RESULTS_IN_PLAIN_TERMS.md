# Whose words a passage puts forward: results in plain terms (2026-10-25)

What the owner asked for (2026-10-25): test the rule for problem 1 of the tier test; check whether it had been attempted before; fix it permanently "the same way as we did it citation checker and verbatim quote checker, DO not just use Guardrails"; and hold this order — 1 Supreme Court, 2 High Court, 3 trial court, 4 a lawyer's arguments, which are never a binding principle and **must never be shown**.

Rules and pass marks were written first (`PLAN_AND_RULES.md`, committed as `a7b1daf` before the sample was labelled). Cost of the whole thing: **$0.034**, one re-run of 26 questions. Nothing was written to the index; nothing is connected to the site.

## Two of my own five pass marks are missed [Certain]

| | What I asked for beforehand | What it does | |
|---|---|---|---|
| V1 block precision | 90% of what it blocks really is nothing but a lawyer's or a party's words | **76%** (25 of 33) | **FAIL** |
| V2 block recall | it blocks 70% of the passages that are nothing but that | **93%** (25 of 27) | PASS |
| V3 tier | agrees with my reading 85% of the time, and **never** puts a trial court's words at tier 1 or 2 | **84%** (43 of 51), and 1 of 140 wrongly promoted | **FAIL** |
| V4 no loss | blocks none of the 47 tier-test passages I had read as on point, bar real arguments | blocks 1, and it is a lawyer's submission | PASS |
| V5 order | no lower tier above a higher one, no blocked passage, checked by an assertion | held in all 104 lists built | PASS |

**By the rule I set, that is a FAIL, and I am not moving the goalposts.** What it means in practice: the ban works (it catches about 9 in 10 of the passages that are purely argument), the ordering is right about 5 times in 6, and the price is that about 1 in 4 of the passages it blocks did have something of a court's in them. Whether that price is acceptable is the owner's call, and the detail is below so he can make it.

## The earlier attempts: it was tried twice and measured once, and never fixed [Certain]

The owner asked me to check this, and thought it might be "the Fatima judgement case".

- **Not Fatima.** Gulfisha Fatima v State (NCT of Delhi) is in `FOLLOW_UPS.md` item 1 for a different fault: in October 2026 all ten top passages came from that one judgment. That led to the "cap 2 passages per judgment" arm of the fix test, not to anything about whose words a passage is.
- **Attempt 1, `sci_index.tag_doc` with the weights `sci_index.W`.** It already tags a whole passage facts / argument / reasoning / order and weights an argument at 0.85 against reasoning's 1.0 — above facts at 0.8. Its own comment says "tags are soft signals, never filters", and a high similarity score simply overrides them. Run over the 65 passages the tier test showed, it called 60 of them "reasoning", 51 of those with basis "default", which means no evidence at all; it tagged the trial court's quoted reasoning (entry 21) as the High Court's reasoning.
- **Attempt 2, `goodlaw.mentions.speaker`.** This one does decide court / counsel / lower court / headnote, and the good-law checker already drops counsel and lower-court sentences (`goodlaw/report.py`). But it reads **one sentence**, it was built for a different job, and **the search never calls it**. Applied to whole passages it called 11 of those 65 "counsel", and 7 of the 11 wrongly, because a court's own paragraph usually reports the argument it is about to reject.
- **It was measured.** The sealed run of 10 October recorded the kinds of misleading passage in its top fives: "neighbouring regime 13, overruled view 4, **lower-court view later reversed 3**, special-facts murder 2" (`FOLLOW_UPS.md` item 1m). The fix test that followed tried a wider pool, a per-judgment cap and an Act boost — none of them about voice. So: seen, counted, never fixed.

## What is new

`authority.py`: sentence by sentence, who is speaking — the deciding court (the default, because a court is the author of everything it does not hand to someone else), a higher court quoted, a trial court or the court below quoted, a lawyer, a party, or the words of a section; then whether the sentence states law; then for the passage a tier (1, 2, 3) and a block. `tier_select.pick` runs every candidate through it, drops the blocked, and sorts by **tier, then whether it states law, then the search score** — so no similarity score can lift a trial court above a High Court. `tier_select.verify` raises if either rule is broken, so a caller cannot get a bad list. 0.9 ms per passage, no network, no model, nothing to spend. `authority_audit.py --assert-baseline` fails if a later edit moves the shares.

## The measurement: 140 passages, labelled before any verdict was read [Certain for the counts]

100 drawn at random from the whole index (50 Supreme Court, 50 Gauhati) and 40 drawn at random from what the rule blocks, shuffled together and written out **without** the rule's answers (`sample_to_label.json`, `draw_sample.py`). I labelled each one on two questions — is every word of it a lawyer's or a party's, and whose words carry the law in it — and only then compared (`my_labels.json`, `score_sample.py`, `sample_scored.json`). **My labels, not a lawyer's**, and on about a tenth of them the honest answer was "arguable".

- I marked 27 of the 140 as nothing but a lawyer's or a party's words. The rule blocks 25 of those 27 and 8 others.
- **Of the 8 it blocks wrongly, 4 carry no law at all** by my reading (two preambles of appearances, a cause title, and a procedural note). Of the other 4, **3 are passages where the only law is inside a lawyer's framing of it** — counsel citing or quoting a judgment. Under the owner's own instruction those should not be shown, so whether they are even mistakes depends on how his rule is read; by my labels they count against the rule and I have left them counting against it. The fourth is a quoted order of a court below that the rule read as a lawyer's, because the quoted order itself begins "the petitioner submits".
- The 2 arguments it misses are ones where the court adds a sentence of its own.
- Tier: 43 of 51 agree. Of the 8 that do not, **5 are in the safe direction** — a Gauhati judgment quoting the Supreme Court read as the Gauhati court's own, so the passage sits lower than it deserves. 2 put a High Court's words one step out. **1 is in the dangerous direction**, and it is the hole below.

**The hole, measured and not fixed:** where a judgment quotes a lower court with no quotation mark or phrase that shows it is doing so, the words are read as the deciding court's own. That happened once in 140 (a trial court's reasoning inside a Supreme Court judgment, where the quotation mark had been lost from the text). This is why `VOICE_SITE_PATCH.md` requires the page to print whose words it is showing: a reader who is told "the trial court's view, as recorded in this judgment" can catch what the rule cannot.

## What it does to the 26 questions of the tier test [Certain]

Re-run so that a freed place is refilled from the real candidates (`voice_rule_test.py`, `26_questions.json`, and every shown passage in `26_questions_shown.json`).

**The Gauhati list.** 65 results before, 64 now. 33 of the old results are gone: **3 blocked** (a lawyer's submission, a party's allegations, and an off-subject argument) and **30 pushed down the list** by the order. Of the 64 results now shown, **every single one states law** — the background-narrative results that problem 1 complained of are gone. Whose words they are: 44 a quoted higher court, 19 the Gauhati court's own, 1 a trial court (last, as it should be). The six passages the tier test flagged are all dealt with: the trial court's reasoning is tier 3, the lawyers' arguments and the party's allegations are blocked or displaced, and the background facts are displaced.

**The Supreme Court list — the cost.** This is the part to weigh:

| On the 14 tuning questions | key case 1st | in top 5 | in top 10 |
|---|---|---|---|
| today, no rule | 5 | 8 | 9 |
| **with the block only** | **5** | **8** | **9** |
| with the block and the tier order | 5 | 7 | 7 |

**The block costs nothing. The tier order costs one question at top 5 and two at top 10** (R11 moved from 3rd to 22nd, R26 from 7th to 12th, R12 from 28th to 38th). The reason is exactly what the owner asked for: in each of those three, the retrieved passage of the key Supreme Court judgment is the part where the Court *recites the High Court's view*, so the rule ranks it below the Court's own words. The judgment is still in the list, lower down. [Certain for the numbers; the cause read off the three passages]

**A design question only he can answer.** Ordering by tier makes the Gauhati list mostly the Supreme Court's words as quoted by Gauhati (44 of 64). The alternative, "demote only" (`authority.effective_tier(promote=False)`), never lifts a quotation above the court that wrote the judgment, so the High Court list stays about the High Court and only pushes trial-court recitals down; it changes 17 of the 26 lists. In the Supreme Court list the two are identical. I have **not** measured which a reader prefers — these 26 questions cannot tell me that.

## The whole index, as a baseline for later [Certain]

All 418,286 passages, 513 seconds (`index_counts_20261025.json`, `authority_audit.py`): blocked **28,253 (6.8%)** — 15,451 Gauhati, 12,802 Supreme Court; tier 1 **233,502 (55.8%)**, tier 2 **130,193 (31.1%)**, tier 3 **18,845 (4.5%)**, not known 7,493 (1.8%); voices: the deciding court 82.0%, a court below 6.9%, a higher court quoted 2.2%, a section 2.2%. A third of all passages (33.8%) state no law and so sort below those that do. A later run that moves these shares by more than 2 points fails `--assert-baseline`, which is how a broken cue gets caught — one did break during this work, when an alternative spliced into the middle of a pattern made a bare court word match on its own.

## What I recommend [Likely]

1. **Turn the block on everywhere, now.** It costs nothing measurable on the Supreme Court list, it is what the owner banned, and it is already enforced in `tier_select.pick`.
2. **Use the tier order in the High Court list, as "demote only".** It keeps that list about the High Court and pushes trial-court recitals to the bottom.
3. **In the Supreme Court list, decide with the cost in front of you:** the strict order honours the instruction exactly and moves one key authority out of the top five of 14 questions; leaving it off keeps today's ranking but lets a recited High Court view sit above the Court's own words. My own preference is the strict order, because the thing he is protecting against is precisely a recital outranking the Court.
4. **Print the voice on every result** (`VOICE_SITE_PATCH.md`, point 2c). This is the part that covers the measured hole, and it is the difference between a filter the reader has to trust and one he can check.
5. **Do not treat this as the end of problem 1.** A passage can be the court's own words, correctly tier 1, and still go against the person asking (entry 45 of the tier test). Nothing here touches that, and nothing here says a case is good law.

## Files

`PLAN_AND_RULES.md` (written first) · `draw_sample.py`, `sample_to_label.json` (the blind sample) · `my_labels.json` (my labels) · `score_sample.py`, `sample_rule_verdicts.json`, `sample_scored.json` (the scoring) · `voice_rule_test.py`, `26_questions.json`, `26_questions_shown.json` (the re-run) · `index_counts_20261025.json` (the baseline). Code: `authority.py`, `tier_select.py`, `authority_audit.py`, `export_voice_bundle.py`, `VOICE_SITE_PATCH.md`; tests `test_authority.py` (49 checks), `test_tier_select.py`.


## The owner's three decisions, 2026-10-25 (after this note was first written), and what was done

1. **Supreme Court list: the strict order is taken**, at the measured cost (one question out of the top 5, two out of the top 10 of the 14).
2. **A High Court judgment quoting the Supreme Court stays at High Court rank.** Done: `authority.effective_tier` no longer promotes (`promote=False` is the default), the verdict carries the tier of the court that wrote the judgment (`own_tier`), and `sort_key` uses it, so no caller can forget. In a Supreme Court judgment this is the strict order. On the 26 questions this is the "demote only" arm already measured: 64 results, 17 of 26 lists differ from the plain reading.
3. **The page prints whose words each result shows.** Done: `authority.voice_line` makes the line, `tier_select.pick` attaches it to every result as `voice_line`, and `tier_select.verify` raises if a result has none, so it cannot be left out by accident. Rendered on all 64 results of the 26-question run without a gap (28 "Gauhati High Court's own words", 28 "the Supreme Court, as quoted by Gauhati High Court", and 8 of those marked as background because the saved text was cut at 600 characters). `VOICE_SITE_PATCH.md` point 2(c) now makes it mandatory for the site.

No new spending: both orderings had already been measured in the run above. Tests: `test_authority.py` and `test_tier_select.py` extended (the old expectation that a quoted Supreme Court passage jumps the queue is replaced by its opposite).
