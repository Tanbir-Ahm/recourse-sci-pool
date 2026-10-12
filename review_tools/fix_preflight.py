#!/usr/bin/env python3
"""Checks, without handing out a single question and without spending anything, that the fix test's stage F search may start (FIX_TEST_RULES_v2.md section 5), and prints the exact commands.

  python review_tools/fix_preflight.py [--no-tests] [--owner-confirms writer-declaration,advocate-key,balance,refresh-postponed] [--date YYYY-MM-DD] [--out FILE]

Automatic checks: the frozen rules and the pinned Machine Spec files equal their hashes (v1 and v2); the checkout is clean and its commit is pushed; the index head is the one recorded in the sealed question file; the
sealed question file and its key still have their freeze hashes and no key field is in the public file; no hand-out is logged; the finalists of the frozen stage D2 gate exist and the D2 run was made under the same
rules; the three side indexes are present and made for this index; the Voyage key is set; the machinery's test suites pass. Checks only a person can make are OWNER items and count as open until named in --owner-confirms:
  writer-declaration  the writer's corrected declaration is in (who wrote the wording and the key; the AI tool named and its use stated; the confirmed freeze hash) and the replacements were re-checked
  advocate-key        Mr. Advocate has reviewed the key and his corrections are in the sealed key
  balance             the owner has read the Voyage dashboard: the balance stays above the $5 live-site reserve after about $0.05
  refresh-postponed   the bucket refresh is postponed until the stage F scoring is over (the index stays at its recorded commit)
Exit code 0 only if everything passes and every OWNER item is confirmed. It never calls select(), so it cannot hand a question out.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import fix_test_set as FT
import pool_runner as PR

OWNER_ITEMS = {"writer-declaration": "the writer's corrected declaration is in (who wrote the wording and the key; AI tool named, its use stated; the confirmed freeze hash) and the replacements were re-checked",
               "advocate-key": "Mr. Advocate has reviewed the key and his corrections are in the sealed key",
               "balance": "the Voyage balance, read on the dashboard, stays above the $5 reserve after about $0.05",
               "refresh-postponed": "the bucket refresh is postponed until the stage F scoring is over"}
TEST_SUITES = ["test_pool_runner.py", "test_fix_arms.py", "test_fix_test_set.py", "test_fix_test_f.py", "test_score_fix_test.py", "test_build_sealed_pack.py", "test_check_new_questions.py", "test_ingest_llm_reviews.py",
               "test_normalise_replies.py", "test_machine_spec_v2.py", "test_score_fix_stage_d.py", "test_fix_reading_sheet.py", "test_fix_preflight.py"]


def sh(*cmd):
    return subprocess.run(list(cmd), capture_output=True, text=True, cwd=ROOT)


def checks(a):
    out = []

    def add(name, ok, detail=""):
        out.append({"check": name, "ok": bool(ok), "detail": detail})
    for rel, (now, frozen) in PR.fix_frozen_files(*PR.fix_paths("F")).items():
        add(f"frozen file equals its hash: {rel}", frozen is not None and now == frozen, f"file {now[:10]}, freeze {str(frozen)[:10]}")
    commit, dirty = PR.code_state()
    add("checkout clean (tracked files)", not dirty, f"commit {commit[:10]}; changed: {dirty[:5]}")
    branch = sh("git", "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    ahead = sh("git", "rev-list", "--count", f"origin/{branch}..HEAD").stdout.strip()
    add("this commit is pushed", ahead == "0", f"{ahead or '?'} commit(s) ahead of origin/{branch}")
    head = PR.index_head(PR.DEFAULT_INDEX)
    try:
        public = FT.load(FT.DEFAULT_SET)
        key = json.load(open(FT.DEFAULT_KEY, encoding="utf-8"))
    except (OSError, ValueError) as e:
        public = key = None
        add("the sealed question file and its key can be read", False, str(e))
    if public is not None:
        bad = FT.check(public, key)
        n_s = sum(1 for q in public["questions"] if q["domain"] != "K")
        dropped = (public.get("provenance") or {}).get("dropped") or []
        add(f"the sealed question file and its key have their freeze hashes, {n_s} scored + {len(public['questions']) - n_s} control questions" + (f" ({len(dropped)} dropped before sealing: {', '.join(dropped)})" if dropped else "") + ", no key field in the public file",
            not bad and n_s >= FT.CNQ.USABLE_FLOOR - 3, "; ".join(bad) if bad else f"questions {public['freeze']['sha256'][:12]}, key {public['freeze']['key_sha256'][:12]}")
        add("index head is the recorded commit", head == (public.get("index_snapshot") or {}).get("commit"), f"head {head[:10]}, recorded {str((public.get('index_snapshot') or {}).get('commit'))[:10]}")
        prov = public.get("provenance") or {}
        add("the writer's own freeze hash matches the question texts (declared in the workbook, or confirmed by a named person)", bool(prov.get("writer_hash_matches")),
            f"declared {str(prov.get('writer_declared_sha256'))[:12]}, confirmed {str(prov.get('writer_confirmed_sha256'))[:12]} by {prov.get('writer_confirmed_by') or '-'}, computed {str(prov.get('writer_text_sha256'))[:12]}")
    runs = FT.read_runs()
    add("no hand-out is logged for the final questions", not runs, f"{len(runs)} entries")
    fin = PR.read_finalists()
    add("the frozen stage D2 gate names at least one finalist (rules v2 section 3)", bool(fin), str([f.split(' ')[0] for f in fin]))
    if os.path.exists(PR.STAGE_D2_POOL):
        recorded = json.load(open(PR.STAGE_D2_POOL, encoding="utf-8"))["run"].get("fix_test", {}).get("rules_sha256")
        have = PR.fix_frozen_files(*PR.fix_paths("F"))[os.path.relpath(PR.FIX2_RULES_PATH, ROOT)][0]
        add("stage D2 was run under the rules that are frozen now", recorded == have, f"D2 {str(recorded)[:10]}, rules {have[:10]}")
    else:
        add("stage D2 pool exists", False, PR.STAGE_D2_POOL)
    for rel in PR.FINAL_SIDE_INDEXES:
        mp = os.path.join(ROOT, rel, "SUPPLEMENT.json")
        ok = os.path.exists(mp) and json.load(open(mp)).get("main_index_commit") == head
        add(f"side index present and made for this index: {os.path.basename(rel)}", ok)
    add("VOYAGE_API_KEY is set", bool(os.environ.get("VOYAGE_API_KEY")))
    if not a.no_tests:
        for t in TEST_SUITES:
            r = subprocess.run([sys.executable, os.path.join(HERE, t)], capture_output=True, text=True, cwd=ROOT)
            add(f"tests pass: {t}", r.returncode == 0, (r.stdout.strip().splitlines() or [""])[-1][:100])
    confirmed = {c.strip() for c in (a.owner_confirms or "").split(",") if c.strip()}
    for k, text in OWNER_ITEMS.items():
        add(f"OWNER: {text}", k in confirmed, "confirmed" if k in confirmed else "open")
    return out


def commands(date, n_questions=None):
    chats = f"{2 * n_questions} chats" if n_questions else "2 chats per question"
    sides = " ".join(f"--supplement {d}" for d in PR.FINAL_SIDE_INDEXES)
    d = f"review_results/{date}_fix_test_f"
    return [("1. the search (hands the questions out ONCE and logs it; the label gets the rules hash and the code commit; about 30 re-rank calls, a few cents; the labels take about 8 minutes to compute)",
             f'python3 -P review_tools/pool_runner.py --fix-test F --label "stage F, single search" --max-rerank-tokens {PR.FIX_RERANK_CAP} {sides} --out {d}'),
            (f"2. the marking pack for J and S (send only the zip: {chats})", f"python3 -P review_tools/build_sealed_pack.py --fix-test --pool {d}/pool.json --out {d}/pack"),
            ("3. when the replies come back: keep them as received, then", f"python3 -P review_tools/normalise_replies.py --src {d}/replies_as_received --out {d}/replies_for_the_reader"),
            ("4. stage 1, marks only (the key is not opened)", f"python3 -P review_tools/score_fix_test.py marks --pool {d}/pool.json --replies {d}/replies_for_the_reader --out {d}/scores"),
            ("5. stage 2, the key (refuses unless stage 1 is complete and unchanged)", f"python3 -P review_tools/score_fix_test.py key --pool {d}/pool.json --replies {d}/replies_for_the_reader --out {d}/scores"),
            ("6. the reading sheet for Mr. Advocate: every passage marked Misleading by any run, and a random 20 of the others", f"python3 -P review_tools/fix_reading_sheet.py --pool {d}/pool.json --replies {d}/replies_for_the_reader --out {d}/scores")]


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
    print("\nREADY: every check passed and every owner item is confirmed." if ready else "\nNOT READY: " + "; ".join(r["check"] for r in res if not r["ok"])[:700])
    print("\nThe commands, once ready:")
    try:
        n_q = len(FT.load(FT.DEFAULT_SET)["questions"])
    except (OSError, ValueError, KeyError):
        n_q = None
    for title, cmd in commands(a.date, n_q):
        print(" ", title, "\n    ", cmd)
    if a.out:
        json.dump({"ready": ready, "checks": res}, open(a.out, "w"), indent=1)
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
