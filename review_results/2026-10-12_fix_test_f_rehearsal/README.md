# Rehearsal of the fix test's stage F path (2026-10-12) — NOT A RESULT, NOT FOR J AND S

Purpose: run the whole stage F machinery once on real passages **without touching the new questions**: the 30 questions that are already used up (`real30_v1.json`, re-labelled N01 to N30 in domain order, see `make_rehearsal_set.py`)
go through the guarded search (`pool_runner.py --fix-test F`, hand-out log in a temporary file, never the real one), the pack builder (`--fix-test`), **invented** replies (`make_fake_replies.py`: random marks from a fixed seed),
both scoring stages and the reading sheet. Look-alike and soft-overlap flags are invented. Cost: 581,955 re-rank tokens (about $0.03).

What it showed: the path works end to end on real data (30 questions, 304 pooled passages, 60 chats). It also found one bug that the invented-data tests had not: court text contains control characters (form feeds) that an Excel cell
cannot hold; `fix_reading_sheet.py` now replaces them (and has a test). Nothing in `scores/` says anything about the search: the marks are random.

Do not send `pack/` to J and S. The real pack is made from the real search after sealing.
