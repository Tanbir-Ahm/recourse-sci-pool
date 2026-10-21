# The catalogue of judgments fetched from the court's newer archive (built 2026-10-21)

`catalogue.csv` has **one row per English judgment** fetched so far (733: January 2019, January to June 2026, and 7 sample judgments of 2018 to 2024). `build_catalogue.py` builds it from `*/results.csv`, the link lists and the PDFs; run it again after each new month. The owner's purpose: later, when a user types a case name on the Recourse site, the site can show these judgments with a link to the court's own PDF.

## Columns
| Column | Meaning |
|---|---|
| `case_name` | "Petitioner versus Respondent" as printed on page 1 of the judgment (the bucket's title where page 1 could not be read: 2 rows) |
| `petitioner`, `respondent` | the two sides, role words ("Appellant", "Respondent(s)") removed |
| `name_key` | lower-case, letters and digits only, "versus" as "v", "M/s" as "ms": the string to match a user's typed name against |
| `case_number` | the first case number printed (for example "CIVIL APPEAL NO.8430 OF 2018"; 2026 judgments may print "CIVIL APPEAL NO. OF 2026" with the number blank) |
| `diary_no` | diary number and year, as in the court's link |
| `decision_date` | YYYY-MM-DD, from the link |
| `neutral_citation` | "2026 INSC 14" where page 1 prints one (108 of 229; found on 2023 and later judgments here, none on 2019) |
| `reportable` | REPORTABLE, NON-REPORTABLE or unmarked, as printed on page 1 |
| `criminal_heading` | yes if page 1 carries a criminal heading (a rough test) |
| `pdf_url` | the court's own PDF link (api.sci.gov.in) |
| `translations` | the court's translation links for the same judgment, as `LANGUAGE=url` pairs (27 rows; the 2026 lists contained no translations) |
| `in_bucket`, `bucket_title` | whether the open bucket holds the same judgment, and its title there |
| `pages`, `sha256`, `fetched_on`, `source` | page count, checksum of the PDF, date fetched, where it came from |

## Limits [Certain unless marked]
- **Suo motu "In Re" matters** have one name and no second side (5 rows); 1 row has no name (a suo motu matter whose title the rules could not read).
- **One name per judgment.** A judgment that decides several appeals together shows only the first matter's parties (for example *Leena Vivek Masal*, three appeals). A user typing the second matter's name will not match. Fix when needed: read every "X versus Y" block on page 1 into `other_matters`.
- Names are read by rules from the page; a 22-row sample read by eye looked right, and no row has a leftover role word. Rows where only the bucket's title could be used: 2; one name has unbalanced brackets. Case numbers are the first one printed, not checked.
- Typed names will differ from printed ones (initials, "M/s", "State of U.P." against "State of Uttar Pradesh"). `name_key` removes punctuation only; real matching (aliases, initials, a fuzzy match) is for the site and needs a test set.
- The catalogue lists what the owner's searches returned. For January 2019 the court page lacked 6 judgments the bucket holds, and for January 2026 1 (see the monthly READMEs): a judgment missing here is not proof that the court has none.
- It holds nothing of the text. The links open the court's PDF; whether they stay valid, and whether a user's browser is allowed to open them, has not been tested from outside this environment.

## How the site should use it (the owner applies this; the Recourse repository is read-only for this project)
- Show the judgment as **"from the Supreme Court of India's website; not checked by us for later treatment"** unless the Overruled Register or a card says otherwise, using the register's own wording. Nothing in the catalogue says a judgment is good law.
- Keep the court's source link with every display (the pool's source acknowledgement).
- Check the court's terms on linking to and reusing these documents before showing them.
