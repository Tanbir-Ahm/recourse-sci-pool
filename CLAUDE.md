# Standing instructions for Claude sessions in this repository

This repository has no other persistent memory. Read `FOLLOW_UPS.md` first (item 0 is the standing item), then `LIVE_SITE_PLAN.md`, `REGISTER.md` and `GOODLAW.md`.

## Standing item (owner, 2026-10-07): bring this back when the site is connected

When the owner says the big index, the checker, the search phases and the Overruled Register patch are connected to the main Recourse site, or when the Recourse checkout contains `overruled_register/` or `register_hooks.py`, **raise this at the start of the session without being asked**: Claude is to export the checker's cards as a small overlay for the site, extended to every case the site can cite, plus a fixed "not checked by us" wording for a case with neither a register row nor a card. The owner applies `REGISTER_SITE_PATCH.md` himself; the Recourse repository is read-only for this project. Spec, prerequisites and limits: `FOLLOW_UPS.md` item 0.

## Rules that hold throughout

- Nothing here says a case is "good law". The register and the checker only subtract trust or warn; a row that is not confirmed by a person is worded as "reported ... not yet confirmed by our reviewer".
- Nothing is merged to `main`, no pull request is opened, and no scheduled routine is created without the owner's say-so. Development is on `claude/sharp-euler-unyfv0`.
- **Owner's say-so, 2026-10-12:** the branch was merged into `main` ("commit and push everything to the main"). That covers this one merge only; later merges, pull requests and routines still need his say-so. Stage F is finished: B stays, the Act-boost (N1/N2) is shelved (`review_results/2026-10-12_fix_test_f/RESULTS_IN_PLAIN_TERMS.md`). The Recourse site is still not connected and not touched by this repository.
- **Owner's say-so, 2026-10-12 (later the same day):** Claude may push to a **branch (not `main`)** of `Tanbir-Ahm/recourse`; never `main`, no pull request or merge there without a further say-so. The register/overlay patch is on branch `register-hooks-and-overlay` (head `4e4e25b`, based on `721e063`). The 28-question criminal trap exam is **deferred until the patch is deployed to the main website**. Product: one site with two modules, laypeople and lawyers' research tool. The WhatsApp bot is the same engine. Railway payment is coming. The register sheet is being sent to Mr. Advocate.
- One routine exists with the owner's say-so (2026-10-08): the **weekly register review sheet** (`REGISTER_ROUTINE_RUNBOOK.md`). It is read-only on the register and pushes only `register_review/` to `claude/sharp-euler-unyfv0`. Do not create other routines without asking.
- The register's reviewer is Mr. Advocate (the owner's statement of 2026-10-07; list 1 only is recorded as verified). Flags are reviewed once every 7 days.
- Indian Kanoon spending: keep at least Rs 200 in reserve; see `IK_PLAN.md`.
