#!/usr/bin/env python3
"""Checks, without handing out a single sealed question and without spending anything, that the sealed run may start (SEALED_RUN_RULES_v1.md section 8, steps 1 to 3), and prints the exact commands.

  python review_tools/sealed_preflight.py [--no-tests] [--owner-confirms register-patch,advocate-16,refresh-postponed,balance] [--out FILE]

Automatic checks: the rules file equals its frozen hash (and any amendment is listed); the checkout is clean and its commit is pushed; the index head is the recorded one; the sealed content still has its freeze hash;
no sealed hand-out is logged (the 30 questions' log and the ruler's); the three side indexes are present and made for this index; the Voyage key is set; the machinery's test suites pass; the scorer, rehearsed on the
tuning data, reproduced the tuning-half comparators (rehearsal folder). Checks only a person can make are listed as OWNER items and count as open until named in --owner-confirms:
  register-patch      the owner has applied REGISTER_SITE_PATCH.md (staging first) or has decided the run does not wait for it
  advocate-16         Mr. Advocate has reviewed the 16 older rulings (real30_stale_status_v1.json) or the owner has decided the run does not wait for him
  refresh-postponed   the 2026-10-12 bucket-refresh reminder was answered "after the sealed run"
  balance             the owner has read the Voyage dashboard: the balance stays above the $5 live-site reserve after about $0.05 for this run
Exit code 0 only if everything passes and every OWNER item is confirmed. Run it again on the day; it is cheap.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import pool_runner as PR
import real_questions as RQ
import ruler as RU

OWNER_ITEMS = {"register-patch": "the register patch is applied (staging first) or the run does not wait for it", "advocate-16": "Mr. Advocate has reviewed the 16 older rulings or the run does not wait for him",
               "refresh-postponed": "the 2026-10-12 bucket-refresh reminder is answered 'after the sealed run'", "balance": "the Voyage balance, read on the dashboard, stays above the $5 reserve after about $0.05"}
TEST_SUITES = ["test_pool_runner.py", "test_build_sealed_pack.py", "test_score_sealed_run.py", "test_real_questions.py", "test_ingest_llm_reviews.py", "test_normalise_replies.py", "test_score_rerank_arms.py", "test_sealed_preflight.py"]
TUNING_COMPARATORS = {"F1_useful_lower": 0.75, "F2_mis_lower": 0.13, "F2_mis_higher": 0.06, "F4_yes_lower": 0.33, "F3_named_authority_top10": 0.71}      # version A on the tuning half (README of the second-batch analysis)


def amendments(rules_path):
    text = open(rules_path, encoding="utf-8").read()
    tail = text.split("## Amendments", 1)[-1] if "## Amendments" in text else ""
    items = [l.strip() for l in tail.splitlines() if l.strip().startswith("- ") or re.match(r"^\d{4}-\d\d-\d\d", l.strip())]
    return items


def sh(*cmd):
    return subprocess.run(list(cmd), capture_output=True, text=True, cwd=ROOT)


def checks(a):
    out = []

    def add(name, ok, detail=""):
        out.append({"check": name, "ok": bool(ok), "detail": detail})
    have, recorded = PR.rules_state()
    add("rules equal their frozen hash", recorded is not None and have == recorded, f"file {have[:12]}, freeze {str(recorded)[:12]}")
    am = amendments(PR.RULES_PATH)
    add("amendments to the frozen rules (listed, none is an error)", True, f"{len(am)} amendment line(s): {am[:3]}")
    commit, dirty = PR.code_state()
    add("checkout clean (tracked files)", not dirty, f"commit {commit[:10]}; changed: {dirty[:5]}")
    branch = sh("git", "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    ahead = sh("git", "rev-list", "--count", f"origin/{branch}..HEAD").stdout.strip()
    add("this commit is pushed", ahead == "0", f"{ahead or '?'} commit(s) ahead of origin/{branch}")
    real = RQ.load(os.path.join(ROOT, "review_data", "ruler", "real30_v1.json"))
    head = PR.index_head(PR.DEFAULT_INDEX)
    add("index head is the recorded commit", head == real["index_snapshot"]["commit"], f"head {head[:10]}, recorded {real['index_snapshot']['commit'][:10]}")
    add("sealed content still has its freeze hash", RQ.freeze_digest(real) == real["freeze"]["sha256"], real["freeze"]["sha256"][:12])
    add("no sealed hand-out is logged for the 30 questions", not RQ.read_runs(RQ.DEFAULT_RUNS), f"{len(RQ.read_runs(RQ.DEFAULT_RUNS))} entries")
    try:
        ruler_runs = RU.read_runs(RU.DEFAULT_RUNS)
    except Exception:       # noqa: BLE001
        ruler_runs = []
    add("no hand-out is logged for the ruler's frozen half", not ruler_runs, f"{len(ruler_runs)} entries")
    for rel in PR.FINAL_SIDE_INDEXES:
        mp = os.path.join(ROOT, rel, "SUPPLEMENT.json")
        ok = os.path.exists(mp) and json.load(open(mp)).get("main_index_commit") == head
        add(f"side index present and made for this index: {os.path.basename(rel)}", ok)
    add("VOYAGE_API_KEY is set", bool(os.environ.get("VOYAGE_API_KEY")))
    reh = os.path.join(ROOT, "review_results", "2026-10-10_sealed_run_rehearsal", "scorer_on_tuning_data", "stage2.json")
    if os.path.exists(reh):
        d = json.load(open(reh))
        v = d["floors_chosen_arm"]
        got = {**v["values"], "F3_named_authority_top10": v["F3_named_authority_top10"]}
        bad = {k: (round(got[k], 3), want) for k, want in TUNING_COMPARATORS.items() if abs(got[k] - want) > 0.011}
        add("the scorer, rehearsed on the tuning data, reproduces the tuning-half comparators", not bad, f"off: {bad}" if bad else "F1 75%, F2 13% and 6%, F3 71%, F4 33%")
    else:
        add("the scorer rehearsal exists", False, reh)
    if not a.no_tests:
        for t in TEST_SUITES:
            r = subprocess.run([sys.executable, os.path.join(HERE, t)], capture_output=True, text=True, cwd=ROOT)
            add(f"tests pass: {t}", r.returncode == 0, (r.stdout.strip().splitlines() or [""])[-1][:100])
    confirmed = {c.strip() for c in (a.owner_confirms or "").split(",") if c.strip()}
    for k, text in OWNER_ITEMS.items():
        add(f"OWNER: {text}", k in confirmed, "confirmed" if k in confirmed else "open")
    return out


def commands(date):
    sides = " ".join(f"--supplement {d}" for d in PR.FINAL_SIDE_INDEXES)
    d = f"review_results/{date}_sealed_run"
    return [("1. the search (hands the questions out ONCE; the guard adds the rules hash and code commit to the label)",
             f'python3 -P review_tools/pool_runner.py --half sealed --final --final-recipe --label "sealed run, final recipe" --max-rerank-tokens {PR.FINAL_RERANK_CAP} {sides} --out {d}'),
            ("2. the ruler's frozen half (key-paragraph test only; its own guard)",
             f'python3 -P review_tools/pool_runner.py --source ruler --half sealed --final --final-recipe --label "sealed run, ruler frozen half" --max-rerank-tokens {PR.FINAL_RERANK_CAP} {sides} --out {d}_ruler  # then: python3 review_tools/ruler_keytest.py --pool {d}_ruler/pool.json --out {d}_ruler'),
            ("3. the marking pack for J and S (send only the zip)", f"python3 -P review_tools/build_sealed_pack.py --pool {d}/pool.json --out {d}/pack"),
            ("4. when the replies come back: keep them as received, then", f"python3 -P review_tools/normalise_replies.py --src {d}/replies_as_received --out {d}/replies_for_the_reader"),
            ("5. stage 1, marks only (the key is not opened)", f"python3 -P review_tools/score_sealed_run.py marks --pool {d}/pool.json --replies {d}/replies_for_the_reader --out {d}/scores"),
            ("6. stage 2, the key (refuses unless stage 1 is complete and unchanged); add --tuning-pool and --tuning-replies for the combined lights",
             f"python3 -P review_tools/score_sealed_run.py key --pool {d}/pool.json --replies {d}/replies_for_the_reader --out {d}/scores --half sealed --tuning-pool review_results/2026-10-10_real30_rerank_test_pack_v2/pool_with_rerank_arms.json --tuning-replies review_results/2026-10-10_second_batch_marking/replies_both_batches"),
            ("7. the register arm (offline; the register's commit is recorded)", "python3 review_tools/currency_pass.py ... (see its docstring) on the saved pool, then pass --register-flags to stage 2 and run it again")]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--owner-confirms", default="")
    ap.add_argument("--date", default="DATE")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = checks(a)
    for r in res:
        print(("OK    " if r["ok"] else "OPEN  " if r["check"].startswith("OWNER") else "FAIL  ") + r["check"] + (f"  [{r['detail']}]" if r["detail"] else ""))
    ready = all(r["ok"] for r in res)
    print("\nREADY: every check passed and every owner item is confirmed." if ready else "\nNOT READY: " + "; ".join(r["check"] for r in res if not r["ok"])[:600])
    print("\nThe commands, once ready:")
    for title, cmd in commands(a.date):
        print(" ", title, "\n    ", cmd)
    if a.out:
        json.dump({"ready": ready, "checks": res}, open(a.out, "w"), indent=1)
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
