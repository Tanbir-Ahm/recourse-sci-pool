# site_patch: what the Recourse owner applies (Phase 1 step 8, 2026-10-12)

- `recourse_721e063.patch`: `git apply` it to Recourse at `721e063` (head on 2026-10-12). Touches `chat_assistant.py`, `recourse_app.py`; adds `register_hooks.py` and `test_register_hooks.py`.
- `register_hooks.py`, `test_register_hooks.py`: the same two new files, for reading.
- 2026-10-14: the patch now also carries answer style v3 (`answer_style.py`, `authorities_table.py`, tests `test_answer_style_v3*.py`, `test_response_style.py`); see `DEPLOY_STAGING.md` Part 4c.
- 2026-10-14 (Recourse `c1e85b0`): the patch also carries the cost log and switches, the grounding checks, the wider-search tier (`sci_search_tier.py`), and the owner's three changes of that day: the controlling case added when a fed passage names a register case (`register_hooks.text_mentions`), the "not checked" sentence leaving out wider-search cases, and **verbatim excerpts** (`excerpt_anchors.py`, its data `excerpt_anchors.json`, `test_excerpt_anchors.py`; switch `ANCHORS`, default off; see `DEPLOY_STAGING.md` Part 4f). `excerpt_anchors.json` is made by `python sci_anchors.py export --out <recourse>` in this repository (it exports only anchors that passed the check against the court's PDF); a copy is here for reading. The case-name finder in the bundle (`overruled_register/overlay.py`, from `goodlaw/overlay.py`) changed too: re-export the bundle.
- The bundle (`overruled_register/`, about 830 KB with the overlay) is NOT in the patch; export it with `python sci_goodlaw.py register-export-site --out <recourse>/overruled_register` and re-export after each weekly review.
- Notes and the list of what was and was not tested: `REGISTER_SITE_PATCH.md`.
- If Recourse has moved on, `git apply --3way` or apply by hand using the insertion points in `REGISTER_SITE_PATCH.md`; the patch is small (about 100 added lines outside the new files).

## The trap exam (Phase 1 step 9): how to run it, and what it can and cannot show

**Finding first:** 35 or more of the original 50 trap questions (`register_exam/`) are about tax, service, property or arbitration cases. The live site is a criminal-law tool and will probably refuse them, which would make the exam "pass" by saying nothing. Only 14 register rows (of 1,765) concern cases that are in the criminal-law index. So there are three exams (the first, 'situation', was added after the staging test of 13 October):

| Exam | Questions | Use |
|---|---|---|
| `register_exam/situation/` (`--exam situation`, the default since 2026-10-13) | 24 (12 register rows, each as a real fact pattern: once naming the overruled case, once not) | **The best test of the live site.** Staging showed that the site refuses bare "is X still good law?" questions (a scope filter that varies run to run), but answers situations and then adds the register note. Topics read from the judgments' own text or the overruling judgments; built by `build_situation_exam.py` |
| `register_exam/criminal/` (`--exam criminal`) | 28 (14 register rows, 2 phrasings each) | The one that can test the live site. Built by `build_criminal_exam.py` from the index titles (14 rows: 11 by party names and year, 3 added by hand after reading the titles). |
| `register_exam/` (`--exam original`) | 50 | Tests only the matching and the guard on cases from the whole register; expect most answers to be refusals. |

Run (on your own computer: it calls the real Anthropic model and Voyage with the Recourse keys, so it costs credit; [Guessing] a few dollars for 56 answers, try `--limit 3` first):

```
python site_patch/run_trap_exam.py --recourse <recourse checkout with the patch applied and overruled_register/ exported> --out-dir exam_run_1 --limit 3
python site_patch/run_trap_exam.py --recourse <same> --out-dir exam_run_1          # the full 28 x 2 arms
python sci_goodlaw.py register-exam score --out register_exam/criminal --answers exam_run_1/answers_off.jsonl   # by hand, against the criminal key
```

(`run_trap_exam.py` also scores all three files itself and prints the three tables, and writes `reading_sheet.md`: 20 answers for the reading lawyer, the ones the guard had to correct first.)

Three answer files are scored on purpose: **off** (the site today), **on_model** (locks a and b only: did the model itself say "overruled"?), **on_shown** (all three locks: what a user sees). Pass mark from the plan: no answer that states an overruled decision as authority without the page saying it was overruled; a lawyer reads 20.

What it cannot show: the exam only tests cases the register already knows, so it cannot show that an unlisted overruled case is caught (it is not; see "Limits" in `REGISTER.md`). A model that does not name the case passes trivially, so read the `states` line the runner prints: a column of `out_of_scope` or `no_match` means the question never reached an answer.

Tested here without the model: `test_trap_exam_runner.py` (a stand-in assistant: both arms, the switch, one failing question, the three files, the reading sheet; and that the guard catches a naive answer on all 28 questions and accepts an aware one). **The exam itself has not been run.**
