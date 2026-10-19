# The owner's section-17 staging test (2026-10-19) and the four fixes

What is here, in plain terms.

| File | What it is |
|---|---|
| `answers_q1_q4_as_pasted.txt` | The four answers exactly as the owner pasted them from the staging page (Ans 1 to Ans 4), each followed by the "Read the source" list and the wider-search passages that came with it. |
| `staging_deploy_logs.log` | The staging deploy log of the same session (Railway). Question hashes, cost lines and the `ACT_SHELF`, `SCI_FEED` and `CHAT_TURN` lines; no question text, no keys. |
| `replay_fix1.py` | Replays the four questions through the engine's section handling, as the website's follow-up mode would build them, and prints what each turn hands to the answer model. It uses Voyage once per turn (a fraction of a cent) and never the answer model. Run it from a Recourse checkout: `python -X utf8 replay_fix1.py <checkout>`. |
| `replay_fix1_before_SECTION_RULE_off.txt` | Its output with `SECTION_RULE=off`, which behaves as before the fix. |
| `replay_fix1_after.txt` | Its output with the rule on. |
| `stress_statute_filter_library.py` and `..._output.txt` | The wider-search statute filter run over the library's own 1,045 judgment chunks: the 168 that cite one of fifteen shelf sections, each marked keep or drop with the reason. |

## What the replay shows (Certain: it is the real engine code, run on the owner's four questions)

Before (rule off): in turn 2 ("I am asking about section 17, NOT section 17 A") section 17 of the Prevention of Corruption Act was not handed to the model at all; in turns 3 and 4 it came third, by meaning, behind two other sections (17A and 18; 18 and 18A); and BNS section 17, which has nothing to do with the question, was read from the bare number and put into the material in turns 2, 3 and 4.

After (rule on): section 17 comes first in all four turns (`named` in turn 1, `implied` in turns 2 to 4), BNS section 17 is dropped, and the prompt carries the clause "The section the person asked about".

## What this does not show

The answer model has not been run on any of this (the sandbox has no model key), so nothing here says how the model behaves under the new prompt lines. That is the owner's staging test: `DEPLOY_STAGING.md` Part 4q. The replay uses a stand-in text for the follow-up rewrite in turn 4.

## The four fixes (details in FOLLOW_UPS item 2ay)

1. **Named section** (`SECTION_RULE`): the section the person names is handed over first and the model is told to stay on it and set out every proviso; a grey note gives the official words when the answer does not; the page shows shelf sections whole.
2. **Wider-search filter** (`FEED_STATUTE_FILTER`): a passage that cites the same section NUMBER of another law is left out (Radhy Shyam, section 17 of the land-acquisition law).
3. **Label** (bug fix): "(from a wider search, not independently verified)" can no longer land inside a case name.
4. **Whose voice** (`PASSAGE_NOTES`, off until the owner's test): a note when a wider-search passage is a lower court's view, one judge's opinion or a party's submission.
