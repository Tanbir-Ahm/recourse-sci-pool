# acts/ : the Act Directory's review sheet

The Act Directory (Recourse `act_directory.py` and `acts_directory.json`, a copy in `../site_patch/`) is step 1 of `../STATUTE_COVERAGE_PLAN.md`: signposts for the Acts whose text Recourse does not hold.

- `ACT_DIRECTORY_SHEET.docx` is for Mr. Advocate: 30 rows (Claude's drafted status line, where appeals go, a link to click), then a table of the names and short forms that make the site say "names the X Act" and the phrases that make it say "looks like it is about the X Act" (28 Acts; IPC and CrPC are not detected). He is asked to strike any name or phrase that could mean something else.
  The confidence column means "I saw no reason to doubt it", not "checked against the Act": no India Code page was opened (corrected 2026-10-17; the first version said "read on India Code").
  Rebuild it from the data with `python acts/build_directory_sheet.py [directory.json] [out.docx]` after the data change.
- Nothing in a drafted column is shown to a user until a person confirms it. In the Recourse checkout: `python act_directory.py confirm ID status|appeal|link --by "Mr. Advocate" [--on DATE]`.
  Claude records only what he answers; it never runs `confirm` on anyone's behalf. An empty draft cannot be confirmed.
- Links: `python act_directory.py check-links [--write]` opens each link (then its alternative) where India Code is reachable and records the ones that open; a redirect to another page counts as a failure.
  Until a link is recorded as checked, the notice points to the India Code home page.
- Limits: every status and appeal line is Claude's draft (from general knowledge and India Code search results); no link has been opened from the build sandbox; the detector finds an Act only when the question names it
  or uses one of the listed phrases. The measurements are in `../STATUTE_COVERAGE_PLAN.md` ("Status of step 1") and `../test_act_directory_controls.py`.
