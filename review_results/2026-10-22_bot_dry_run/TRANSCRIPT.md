# A dry run of the pilot bot's core, 2026-10-22

Offline: no chat service, no network, no spend. **Real:** the Overruled Register, the currency cards, the rules and the wording. **Invented:** the users, the judgments' names, the passages and the search (a stub that returns four fixed hits). Read it as a picture of what a lawyer would see, not as evidence about the search. The bot is built from the recorded settings (`goodlaw/data/pilot_settings.json`), so the quiet-card choice shown is the one decided on 2026-10-22.

### A stranger writes

```
What is the rule on bail?
```

**The bot replies:**

```
This is a private test. Ask the person who invited you to add you.
```

### Adv. A (first message) writes

```
Hello
```

**The bot replies:**

```
Welcome to the Recourse test.

Three rules before you start:
1. Test questions only. Do not type client names or facts.
2. This chat is not end-to-end encrypted. Treat it as a public place.
3. Nothing here is independently verified. Check every case yourself before you cite it.

Reply "I understand" to start.
```

### Adv. A writes

```
I understand
```

**The bot replies:**

```
Thank you. Ask your first test question. After each passage, tell us whether it was useful.
```

### Adv. A writes

```
Can bail be refused on a conspiracy allegation?
```

**The bot replies:**

```
Found 4 passages from Supreme Court judgments. Showing 3. What we know about a case's later treatment comes before its passage. Results are not independently verified. Check any case before you cite it.
```

**The bot replies:**

```
REPORTED ON THE OVERRULED REGISTER
Mohan Lal v. State of Punjab (2018) is reported as overruled by Mukesh Singh v. State (Narcotic Branch of Delhi) (2020) (not yet confirmed by our reviewer). As of 7 Oct 2026.

REPORTED ADVERSE
A later five-judge bench of the Supreme Court (2020) appears to overrule or reject this case, in whole or in part, so check it before relying on this case. As of 6 Oct 2026.

MOHAN LAL v. STATE OF PUNJAB
Supreme Court · 2018 · para 14 · page 9

“14. [Invented passage 1: a paragraph of the first judgment, word for word.]”

Was this passage useful?
```

Buttons: Relevant | Not relevant | Misleading

**The bot replies:**

```
NOT CHECKED BY US
No register entry and no check on file for this case. Verify it before you cite it.

SAMPLE ONE v. STATE
Supreme Court · 2015 · para 3 · page 2
Passage: Appears to record counsel's arguments, not the Court's view.

“3. [Invented passage 2: counsel for the appellant submitted that the order was bad.]”

Was this passage useful?
```

Buttons: Relevant | Not relevant | Misleading

**The bot replies:**

```
NOT CHECKED BY US
We could not identify which judgment this passage comes from, so we have not checked it against the register or for later treatment. Verify it before you cite it.

Judgment no. 777 (title not available)
Supreme Court · page 1

“[Invented passage 3: a paragraph from a judgment nobody can name.]”

Was this passage useful?
```

Buttons: Relevant | Not relevant | Misleading

### Adv. A writes

```
tap: m|q1|1111aaaa2222bbbb|m
```

**The bot replies:**

```
Thanks, noted.
```

### Adv. A writes

```
/watch Mohan Lal v State of Punjab (2018) ; (2018) 17 SCC 627
```

**The bot replies:**

```
Saved to your watchlist. This is what we know today:

Mohan Lal v State of Punjab

REPORTED ON THE OVERRULED REGISTER
Mohan Lal v. State of Punjab (2018) is reported as overruled by Mukesh Singh v. State (Narcotic Branch of Delhi) (2020) (not yet confirmed by our reviewer). As of 7 Oct 2026.

REPORTED ADVERSE
A later five-judge bench of the Supreme Court (2020) appears to overrule or reject this case, in whole or in part, so check it before relying on this case. As of 6 Oct 2026.

Silence is not an all-clear.
```

### Adv. A writes

```
/watch Sample One v State (2015)
```

**The bot replies:**

```
Saved to your watchlist. This is what we know today:

Sample One v State

NOT CHECKED BY US
No register entry and no check on file for this case. Verify it before you cite it.

Silence is not an all-clear.
```

### Adv. A writes

```
/watchlist
```

**The bot replies:**

```
Your saved cases:
- Mohan Lal v State of Punjab: Reported on the Overruled Register
- Sample One v State: Not checked by us

Silence is not an all-clear. Check every case before you cite it.
```

### Adv. A writes

```
/export
```

**The bot replies:**

```
Your 2 saved cases as a spreadsheet. Every row carries its own note about how it was checked.
```

Attachment: `authorities_adv-a_2026-11-05.csv`

The exported file (all its columns, one row each):

```
case,year,citation,status,what_we_know,evidence_as_of,checked_by,also,section_numbers,exported_on,note
Mohan Lal v State of Punjab,2018,(2018) 17 SCC 627,Reported on the Overruled Register,Mohan Lal v. State of Punjab (2018) is reported as overruled by Mukesh Singh v. State (Narcotic Branch of Delhi) (2020) (not yet confirmed by our reviewer).,2026-10-07,"Overruled Register (candidate row, not yet confirmed)","Reported adverse: A later five-judge bench of the Supreme Court (2020) appears to overrule or reject this case, in whole or in part, so check it before relying on this case.",,2026-11-05,"From the Overruled Register: a row not yet confirmed by our reviewer. Treat it as a pointer to check, not as a fact."
Sample One v State,2015,,Not checked by us,No register entry and no check on file for this case. Verify it before you cite it.,,,,,2026-11-05,Not checked. Verify the case yourself before you cite it.

```

## A month later: the watchlist check (not part of the bot's core; shown to complete the picture)

Run on 2026-12-02: 2 cases checked, 1 unchanged, 1 draft alert(s). A person reads the draft; nothing is sent until someone approves it, and no sender exists.

**Draft alert (NEW_WARNING, status: draft):**

```
WATCHLIST ALERT: New warning on a case you saved

Sample One v State

REPORTED ADVERSE
A later five-judge bench of the Supreme Court (2026) appears to overrule or reject this case, in whole or in part, so check it before relying on this case. As of 1 Dec 2026.

We only message you when something changes against a case you saved. Silence is not an all-clear.
```

## What the owner sees

```
users: 1, accepted the rules: 1, questions: 1, marks: 1
by mark: {'relevant': 0, 'not_relevant': 0, 'misleading': 1}
misleading passages to review: [('1111aaaa2222bbbb', 1000000001)]
```

