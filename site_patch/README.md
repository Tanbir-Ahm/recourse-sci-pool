# site_patch: what the Recourse owner applies (Phase 1 step 8, 2026-10-12)

- `recourse_721e063.patch`: `git apply` it to Recourse at `721e063` (head on 2026-10-12). Touches `chat_assistant.py`, `recourse_app.py`; adds `register_hooks.py` and `test_register_hooks.py`.
- `register_hooks.py`, `test_register_hooks.py`: the same two new files, for reading.
- The bundle (`overruled_register/`, about 830 KB with the overlay) is NOT in the patch; export it with `python sci_goodlaw.py register-export-site --out <recourse>/overruled_register` and re-export after each weekly review.
- Notes and the list of what was and was not tested: `REGISTER_SITE_PATCH.md`.
- If Recourse has moved on, `git apply --3way` or apply by hand using the insertion points in `REGISTER_SITE_PATCH.md`; the patch is small (about 100 added lines outside the new files).
