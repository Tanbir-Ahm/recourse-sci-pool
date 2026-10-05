# Currency cards: the checker's answer for every case Recourse can show

A **card** is the still-good-law checker's report on one case, computed ahead of time and saved, so that answering a question is a lookup, not a ten-second search. There is one card for each of the 76 cases the live site can show (the registry behind `_JUDGMENT_CHUNK_FILES`, 68 cases, plus the 8 extra cases in the pilot pool). Nothing here is connected to the live site yet.

Source label on everything: **pattern-rule reading of Supreme Court texts; not lawyer-validated.** A card is a proposal for a person to confirm, never a decision. Recourse's own human-verified records (`citation_currency.py`) come first.

## What is in this folder

| File | What it is |
|---|---|
| `currency_cards.json` | all 76 cards in one file; this is the file the answer step reads |
| `REVIEW_SHEET.csv` | the cases a person should look at, most pressing first, with the quoted evidence; a person fills in the last four columns |
| `MATCH_CHECK.csv` | every case with the judgment in our collection it was matched to, uncertain matches first |
| `CHANGES.md` | what changed since the previous run (a status that moved towards a warning is listed first) |
| `reports/*.md` | the full readable report for each checked case |
| `reviews.json` | the verdicts people have recorded (an empty list until someone records one) |

## What a card says

| `status` | Meaning | `user_facing_note` |
|---|---|---|
| `ADVERSE_SIGNAL` | a later judgment of this Court, in its own voice, appears to overrule or reject the case (a bench at least as large), or the reporter's citator marks it overruled | a warning |
| `QUESTIONED` | later judgments disagree with, doubt, limit or refer it, a smaller bench appears to overrule it, or the legislature responded | a caution |
| `NO_ADVERSE_FOUND` | at least three later judgments we hold cite it and nothing adverse turned up. **Silence in what we hold, not a finding about the law** | none |
| `INSUFFICIENT` | fewer than three later judgments we hold cite it | none |
| `NOT_IN_COLLECTION` | not among the Supreme Court judgments we hold | none |
| `NOT_CHECKABLE_HIGH_COURT` | a High Court decision; the collection is Supreme Court only | none |
| `AMBIGUOUS_MATCH` | we could not tell which judgment in our collection it is | none |

Each card also has: the case's own details and citations; the matched judgment and how it was matched; `evidence` (the quoted sentences, the judgment each comes from, its bench, the cue, the caveats, checked word for word against the text); `support` (how many later judgments cite it, the latest year, recent approving ones, what the reporters' case-law tables marked); `coverage` (what the collection can and cannot see); `statute_note` (when the judgment discusses an IPC or CrPC section the 2023 codes renumbered at least three times: a note about the number, not the doctrine); `provenance` (date, the checker's git commit, the corpus); `fingerprint`; and `review`.

### The wording rules

- Only a warning or a caution carries a note. A quiet or unchecked case carries none, as Recourse already does for its own `GOOD_LAW` records (it found that "hasn't been verified" notes read as hand-wringing).
- A note says "appears to" because a rule read it. It never says a case "is good law", "still valid" or "safe to rely on"; `cardreader.check_wording` is the guard, the tests check every note, and the reader withholds a note that contains such a phrase.
- The note is one or two plain sentences with no internal identifiers. The quotes stay in `evidence` for the reviewer.

## How an answer would use a card

`goodlaw/cardreader.py` (standard library only, plus `goodlaw/cites.py`) is the whole reader:

```python
import cardreader                                           # copied next to cites.py
CARDS = cardreader.load("currency_cards.json")              # once, at start-up
card = cardreader.find(CARDS, case_name=m["case_name"])     # the exact case_name the chunks carry
result = cardreader.for_answer(card)                        # level: warning / caution / none; user_facing_note; stale; decided_by
```

`for_answer` also applies a person's review (below) and flags a card older than 45 days as `stale`.

**How Recourse could wire it (a proposal only: Recourse's code was read, never changed).** In `chat_assistant.py`, in the currency block that calls `get_citation_currency_for_case_name`, keep everything as it is, and add, where Recourse has no curated record (every returned status is `NOT_YET_VERIFIED`), the card's warning in place of the generic "This case hasn't been checked for legal currency yet.":

```python
if all(r["status"] == "NOT_YET_VERIFIED" for r in currency_records):
    res = cardreader.for_answer(cardreader.find(CARDS, case_name=m["case_name"]))
    if res["user_facing_note"]:
        notes = [res["user_facing_note"]]
```

This logic was run against the real cards in isolation (Mohan Lal gets the warning; a quiet card and an unknown case keep the generic note; a curated `GOOD_LAW` case is untouched). It has not been run inside the app. Two things to know: (1) the pilot-pool path (`_fetch_pilot_related_judgments`) returns case names without any currency lookup, as far as I can see, so a warning about a pilot-only case such as Mhetre reaches an answer only if that path is connected too; (2) to deploy, copy `currency_cards.json`, `cardreader.py` and `cites.py` into the Recourse repository (or fetch the JSON at start-up).

## The review loop (a person confirms)

1. Open `REVIEW_SHEET.csv` (it opens in Excel). Each row is a case the checker flagged, or could not match, with the quoted evidence and, beside it, what Recourse's own record says. Rows where Recourse says `GOOD_LAW` but the checker flags the case come first.
2. In `your_verdict` write one of `CONFIRMED_ADVERSE` (the later judgment really does overrule or reject it), `FALSE_ALARM` (the quoted passage is not adverse to this case), `NEEDS_RESEARCH`. Add `reviewer`, `review_date` and a `note`.
3. Run `python sci_goodlaw.py cards-review` to record the verdicts in `reviews.json` and put them on the cards. (Running `cards` merges any unmerged verdicts first, so a filled sheet is never lost.)
4. A verdict applies only while the card's `fingerprint` (its status and its evidence) is unchanged. If a later run finds new evidence, the review is kept but marked no longer current, the reader ignores it, and `CHANGES.md` says so.

At read time: `CONFIRMED_ADVERSE` gives a warning; `FALSE_ALARM` silences it; `NEEDS_RESEARCH` keeps the checker's reading and marks it under review.

## Refreshing (after each monthly bucket refresh)

```
python sci_goodlaw.py build --corpus corpus.sqlite              # about 15 minutes
python sci_goodlaw.py library --recourse-dir <Recourse checkout> # only when Recourse's library changed
python sci_goodlaw.py cards --corpus corpus.sqlite              # about 2.5 minutes for 76 cases
```

Then read `CHANGES.md`: any case whose status moved towards a warning, or that gained evidence, needs a look. `python sci_goodlaw.py card "Rangappa v Sri Mohan"` shows exactly what the answer step would be told about one case.

`goodlaw/targets/library.json` is the snapshot of Recourse's library (names, citations, court, curated records, the Recourse commit read). `goodlaw/targets/library_overrides.json` is where a person settles a case the matcher reports as ambiguous or wrongly matched.

## What the first run found (2026-10-05, checker commit in each card)

76 cases: 45 `NO_ADVERSE_FOUND`, 14 `INSUFFICIENT`, 10 High Court decisions (not checkable), 5 not in the collection, **2 `ADVERSE_SIGNAL`**.

- **Mohan Lal v State of Punjab (2018) 17 SCC 627**: overruled by the five-judge bench in Mukesh Singh v State (Narcotic Branch of Delhi) (2020), whose headnote says "overruled". Recourse has no curated currency record for it.
- **Siddharam Satlingappa Mhetre v State of Maharashtra (2011) 1 SCC 694**: overruled "to that extent" by the five-judge Sushila Aggarwal bench (2020), on the point that no restrictive conditions can be imposed when granting anticipatory bail. It is in the pilot pool (150 chunks), and Sushila Aggarwal is in the pilot pool too. Recourse has no curated record for it.
- Not checked: 5 Supreme Court cases we do not hold (Lokesh B.H. 2026, Prakash Chimanlal Sheth 2025, Satender Kumar Antil 2026, Usha Chakraborty 2023, Youth Bar Association 2016) and 10 High Court decisions.
- Before the final run, eight cases were flagged. I read every flagged card: two were real (above), six were false alarms caused by rule errors, which I fixed generically (see `goodlaw/EVALUATION.md`): "undoubtedly" read as "undo", "its overruling in T" read as T overruled, a case that re-examined others read as re-examined, a refusal to refer read as a doubt, counsel's argument read as the Court's, and a later judgment's page header read as a mention. A seventh rule came from the Sushila Aggarwal card: a smaller bench's disagreement with a larger bench's ruling is now a weak signal.
- 5 cases were matched to a judgment on the names and year alone, within a year of the citation's (D. Velusamy, D.K. Basu, Lalita Kumari, M. Ravindran, Tofan Singh); I checked that the names and dates agree, but not the content, and `MATCH_CHECK.csv` lists them first for a glance.

## Limits (read before relying on any card)

- **A quiet card is weak evidence.** The checker found roughly a third to a half of the overrulings it could be tested on, and about half its clean flags were real (see `goodlaw/EVALUATION.md`). The 45 quiet cards are not 45 findings that the law is settled.
- The collection lacks roughly 40% of what Indian Kanoon lists for 1968 to 1999 and about a quarter of 2018 to 2025; High Court treatment is invisible.
- A card is a snapshot: rebuild it after each monthly refresh (`stale` flags a card older than 45 days).
- The two warnings above and the five unmatched cases are facts about this collection on this date.
