# land_case_check: pilot for linking land parcels to court cases

A separate project from the case-law register and checker in the rest of this repository. It is kept here only so the tool survives between sessions. It does not touch the Recourse site.

## What it does
`parcel_case_check.py` checks land parcels against eCourtsIndia case data. The eCourtsIndia case search has no father's-name field and no dag field, so the tool runs a cascade instead of one three-field search:
1. search each holder's name (several English spellings, fuzzy) in the chosen state or district;
2. score every hit locally: name, then father's name (when the party string carries "S/O ...");
3. pay for case detail only for the best candidates;
4. scan the order and judgment text for the parcel's dag and patta numbers and its village names.

Results are graded: level 3 (text cites the dag and the village), level 2 (name plus father or village), level 1 (name only, or a dag number alone). A report must say "nothing found in these sources on this date", never "no case". Searched: eCourtsIndia case data only. Not searched: revenue courts, debt recovery tribunals unless supplied, pleadings, the registry.

## Run it
Offline self-test (no network, no token):
    python3 land_case_check/parcel_case_check.py --selftest

Live pilot (spends money; the budget is a hard cap):
    ECI_TOKEN=... python3 land_case_check/parcel_case_check.py parcels.json --budget 150 --plan payg --state-code <code>

`parcels.json` is a list of parcels; see `SAMPLE` in the script (label, dags, patta, places_en, holders with Assamese name and father).

## Rules
- Put the token in the environment (`ECI_TOKEN`), never in a file, a message or a commit.
- Never commit raw replies (`eci_raw/`), reports, or any file with real holders' names. The `.gitignore` here blocks the usual names.
- The pilot has not yet been run against the live API. The response layout in the public docs is incomplete, so the first run saves raw replies for inspection.
- Storing or reselling eCourtsIndia results needs their written permission; their pricing page is silent on it.
- A result is a lead to confirm, not a finding. Holders' data is personal data; the main duties of the Digital Personal Data Protection Act start about 13 May 2027.
