#!/usr/bin/env python3
"""Builds the ONE marking round of the sealed run (SEALED_RUN_RULES_v1.md section 2) from the sealed pool: one self-contained prompt file per question, order A only, every passage of every arm in one
shuffled list, to be run in BOTH ChatGPT and Gemini. Nothing about which search or re-ranker found a passage, no arm, no key and no half goes into a prompt (checked here, and again by the tests).

  python review_tools/build_sealed_pack.py --pool review_results/DATE_sealed_run/pool.json --out DIR
  python review_tools/build_sealed_pack.py --pool .../pool.json --out DIR --rehearsal        # a tuning-half pool, for a trial of the machinery; the output is named Rehearsal_Pack and never goes to J and S

Refuses a pool that is not the final recipe of a sealed run (unless --rehearsal), a question with no passages, numbering with gaps, or an empty passage text. Replies are saved as R03_A_ChatGPT.txt and R03_A_Gemini.txt,
passed through `normalise_replies.py`, and read by `score_sealed_run.py --pool <the same pool.json>`. The pool is PRIVATE (it names the arms); the pack is not. No network, no spend.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_llm_pack as blp
import review_common as rc

TOOLS = ("ChatGPT", "Gemini")
PACK_NAME, REHEARSAL_NAME = "Third_Batch_Pack", "Rehearsal_Pack"          # what the reviewers see: nothing in the pack says what it is for
LEAKS = ["merged", "re-rank", "rerank", "safety", "variant", "challenger", "baseline", "arm ", "sealed", "tuning", "fused", "half:", "recipe", "search version", "versions", "A today", "site shown", "key authority"]

README = """MARKING PACK, THIRD BATCH: how to run it (copy and paste; every file is run twice, once in each tool)

WHAT THIS IS
A test of a legal search tool for Indian Supreme Court criminal-law judgments. This pack holds {nq} questions ({ids}). For each question there are {lo} to {hi} passages that the search showed. An AI model is asked to mark each passage Yes / Partly / No / Misleading. All the texts are public court judgments; there is no personal or confidential information in the files. All the files are new questions; nothing here repeats an earlier pack.

WHAT YOU NEED
- ChatGPT AND Gemini. Every file is run in both tools (one new chat per file per tool). If one of you has only one of them, split the work so that each file still gets both tools.
- Switch OFF web search, browsing, "deep research" and any tools. We want the model to judge only the text it is given.
- Use a NEW chat for every file. Do not continue an earlier chat.

HOW TO RUN IT
1. Open the folder 'prompts'. There are {nfiles} files, named like {ex}_A.txt. (One file per question; no reversed files.)
2. For each file: open it, select all, copy, paste into a NEW chat, send, wait for the answer.
3. Copy the model's ENTIRE reply and save it as a plain text file named exactly like this:
      {ex}_A_ChatGPT.txt        {ex}_A_Gemini.txt
   Put all the saved replies in the folder 'replies'.
4. If a reply is not JSON, or is cut off, send this to the same chat: "Reply again with only the JSON object, nothing else." and save the new reply instead.
5. BEFORE you zip, open each saved file and check two things (two files in an earlier round were wrong this way):
   a. it is the model's REPLY (it starts with {{ and has a "marks" list), not the prompt you pasted;
   b. the ChatGPT file and the Gemini file for the same question are different replies: each tool's own answer, not one saved twice.
6. Tick the file off in manifest.csv, zip the 'replies' folder and send it back.

HOW MUCH TO DO
{nchats} chats in all ({nfiles} files x 2 tools). Each file lists the passage numbers to cover; use exactly the numbers shown.

PLEASE DO NOT
- Edit the prompt text, or add your own opinion to the chat.
- Fix or tidy the model's JSON by hand. Save what it returned. If a ChatGPT reply has backslashes before underscores or square brackets, leave them: a script removes them.
- Ask the model whether a case is still good law. That is checked separately.

WHAT HAPPENS TO THE REPLIES
They are read by a script and compared. Every result will be labelled 'LLM-judged'. They are not lawyer-checked, and will not be described as lawyer-validated.

The marks mean:
   Yes        - answers the question directly
   Partly     - on the topic, useful, but incomplete
   No         - not helpful
   Misleading - could give a wrong impression (for example a lawyer's argument that the court rejects)
"""


def framing_leaks(text):
    """Leak words in the parts of a prompt or README that WE write (the passages are court text and may contain any word)."""
    return [w for w in LEAKS if re.search(r"\b" + re.escape(w.strip()) + (r"\b" if w.endswith(" ") else ""), text, re.I)]


def build(pool_path, out_dir, rehearsal=False):
    """Writes out_dir/Third_Batch_Pack/ (+ .zip) and out_dir/build_info.json. Returns the info dict."""
    with open(pool_path, encoding="utf-8") as fh:
        doc = json.load(fh)
    questions = doc["questions"] if isinstance(doc, dict) else doc
    run = doc.get("run", {}) if isinstance(doc, dict) else {}
    if not rehearsal:
        if run.get("half") != "sealed" or not run.get("final_recipe"):
            raise SystemExit("refused: this pool is not the final recipe of a sealed run (use --rehearsal for a trial on the tuning half)")
        if run.get("final_recipe", {}).get("code_uncommitted"):
            raise SystemExit("refused: the pool was made from uncommitted code")
    if not questions:
        raise SystemExit("refused: the pool holds no questions")
    qs = []
    for q in questions:
        rows = sorted(q["rows"], key=lambda r: r["n"])
        if not rows:
            raise SystemExit(f"refused: {q['qid']} has no passages")
        if [r["n"] for r in rows] != list(range(1, len(rows) + 1)):
            raise SystemExit(f"refused: the passage numbers of {q['qid']} are not 1 to {len(rows)}")
        if any(not (r.get("text") or "").strip() for r in rows):
            raise SystemExit(f"refused: {q['qid']} has an empty passage text")
        qs.append({"qid": q["qid"], "question": q["question"], "rows": rows})
    name = REHEARSAL_NAME if rehearsal else PACK_NAME
    folder, zip_path = os.path.join(out_dir, name), os.path.join(out_dir, name + ".zip")
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(os.path.join(folder, "prompts"))
    os.makedirs(os.path.join(folder, "replies"))
    manifest = []
    for q in qs:
        prompt = blp.render(q, "A")
        frame = blp.render(dict(q, rows=[], question=""), "A")                 # our own wording only: the question and the passages are not ours to check
        bad = framing_leaks(frame)
        if bad:
            raise SystemExit(f"refused: the prompt framing for {q['qid']} contains {bad}")
        for r in q["rows"]:
            if f"--- PASSAGE {r['n']} ---" not in prompt:
                raise SystemExit(f"refused: passage {r['n']} of {q['qid']} is missing from its prompt")
        fname = f"{q['qid']}_A.txt"
        with open(os.path.join(folder, "prompts", fname), "w", encoding="utf-8") as fh:
            fh.write(prompt)
        for tool in TOOLS:
            manifest.append([fname, q["qid"], "A", len(q["rows"]), tool, f"{q['qid']}_A_{tool}.txt", ""])
    sizes = [len(q["rows"]) for q in qs]
    readme = README.format(nq=len(qs), ids=f"{qs[0]['qid']} to {qs[-1]['qid']}", lo=min(sizes), hi=max(sizes), nfiles=len(qs), nchats=len(manifest), ex=qs[0]["qid"])
    bad = framing_leaks(readme)
    if bad:
        raise SystemExit(f"refused: the README contains {bad}")
    with open(os.path.join(folder, "README.txt"), "w", encoding="utf-8") as fh:
        fh.write(readme)
    with open(os.path.join(folder, "manifest.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["prompt file", "question", "order", "passages", "tool", "save the reply as", "done (tick)"])
        w.writerows(manifest)
    with open(os.path.join(folder, "replies", "PUT_SAVED_REPLIES_HERE.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"Save each model reply here, named like {qs[0]['qid']}_A_ChatGPT.txt or {qs[0]['qid']}_A_Gemini.txt\n")
    rc.write_zip(folder, zip_path, name)
    info = {"rehearsal": bool(rehearsal), "questions": len(qs), "prompt_files": len(qs), "chats": len(manifest), "passages": sum(sizes), "per_question": {q["qid"]: len(q["rows"]) for q in qs},
            "pool_sha256": hashlib.sha256(open(pool_path, "rb").read()).hexdigest(), "zip_sha256": hashlib.sha256(open(zip_path, "rb").read()).hexdigest(), "zip_bytes": os.path.getsize(zip_path),
            "run_label": run.get("final_recipe", {}).get("label")}
    with open(os.path.join(out_dir, "build_info.json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=1)
        fh.write("\n")
    return info


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rehearsal", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    info = build(a.pool, a.out, a.rehearsal)
    print(f"built {a.out} ({info['zip_bytes']:,} bytes): {info['prompt_files']} prompt files, {info['chats']} chats, {info['passages']} passages" + (" [REHEARSAL: not for J and S]" if info["rehearsal"] else ""))


if __name__ == "__main__":
    main()
