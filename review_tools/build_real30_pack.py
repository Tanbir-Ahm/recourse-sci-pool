#!/usr/bin/env python3
"""Builds the marking pack for J and S from a pool of the 30 questions: one self-contained prompt file per question, presentation order A (passage numbers ascending) for every question and
order B (reversed) for about a third of them, to be run in BOTH ChatGPT and Gemini. Nothing about which search found a passage, no rewrite, no key and no half goes into a prompt.

  python review_tools/build_real30_pack.py --pool review_results/DATE_real30_pool_dev/pool.json --out DIR

Replies are saved as R03_A_ChatGPT.txt, R03_A_Gemini.txt (R03_B_... for the reversed files) and read by `ingest_llm_reviews.py --replies ... --pool <the same pool.json>`.
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_llm_pack as blp
import review_common as rc

TOOLS = ("ChatGPT", "Gemini")
SALT = "real30-order"


def reversed_set(qids):
    """A third of the questions (rounded to the nearest whole question) are also run in reversed order, a check on position bias. They are the first third when the questions are
    ordered by a fixed hash, so that nobody picks them and the share does not depend on luck."""
    ordered = sorted(qids, key=lambda q: hashlib.sha256(f"{SALT}|{q}".encode("utf-8")).hexdigest())
    return set(ordered[:round(len(ordered) / 3)])


README = """MARKING PACK FOR THE 30 REAL QUESTIONS: how to run it (copy and paste; every file is run twice, once in each tool)

WHAT THIS IS
A test of a legal search tool for Indian Supreme Court criminal-law judgments. This pack holds {nq} questions ({ids}). For each question there are {lo} to {hi} passages that the search showed. An AI model is asked to mark each passage Yes / Partly / No / Misleading. All the texts are public court judgments; there is no personal or confidential information in the files.

WHAT YOU NEED
- ChatGPT AND Gemini. Every file is run in both tools (one new chat per file per tool). If one of you has only one of them, split the work so that each file still gets both tools.
- Switch OFF web search, browsing, "deep research" and any tools. We want the model to judge only the text it is given.
- Use a NEW chat for every file. Do not continue an earlier chat.

HOW TO RUN IT
1. Open the folder 'prompts'. There are {nfiles} files. File names look like R03_A.txt or R03_B.txt.
   - A and B hold the SAME passages with the SAME numbers. In B the passages are listed in reverse order. Only {nb} questions have a B file; it checks whether the model is swayed by position.
2. For each file: open it, select all, copy, paste into a NEW chat, send, wait for the answer.
3. Copy the model's ENTIRE reply and save it as a plain text file named exactly like this:
      R03_A_ChatGPT.txt     R03_A_Gemini.txt     R03_B_ChatGPT.txt     R03_B_Gemini.txt
   Put all the saved replies in the folder 'replies'.
4. If a reply is not JSON, or is cut off, send this to the same chat: "Reply again with only the JSON object, nothing else." and save the new reply instead.
5. Tick the file off in manifest.csv, zip the 'replies' folder and send it back.

HOW MUCH TO DO
{nchats} chats in all ({nfiles} files x 2 tools). If time is short, do every A file in both tools first; the B files come last.

PLEASE DO NOT
- Edit the prompt text, or add your own opinion to the chat.
- Tell the model which search produced the passages (you do not know, and nor does it).
- Fix or tidy the model's JSON by hand. Save what it returned. Mistakes are useful to us.
- Ask the model whether a case is still good law. That is checked separately.

WHAT HAPPENS TO THE REPLIES
They are read by a script and compared. Every result will be labelled 'LLM-judged'. They are not lawyer-checked, and will not be described as lawyer-validated.

The marks mean:
   Yes        - answers the question directly
   Partly     - on the topic, useful, but incomplete
   No         - not helpful
   Misleading - could give a wrong impression (for example a lawyer's argument that the court rejects)
"""


def questions_of(pool_path):
    with open(pool_path, encoding="utf-8") as fh:
        doc = json.load(fh)
    return doc["questions"] if isinstance(doc, dict) else doc


def build(pool_path, out_dir):
    """Writes out_dir/Real30_Review_Pack/ and out_dir/Real30_Review_Pack.zip. Returns (zip path, number of files, number of chats)."""
    qs = [{"qid": q["qid"], "question": q["question"], "rows": sorted(q["rows"], key=lambda r: r["n"])} for q in questions_of(pool_path)]
    folder, zip_path = os.path.join(out_dir, "Real30_Review_Pack"), os.path.join(out_dir, "Real30_Review_Pack.zip")
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(os.path.join(folder, "prompts"))
    os.makedirs(os.path.join(folder, "replies"))
    manifest = []
    rev = reversed_set([q["qid"] for q in qs])
    for q in qs:
        for order in ("A", "B") if q["qid"] in rev else ("A",):
            name = f"{q['qid']}_{order}.txt"
            with open(os.path.join(folder, "prompts", name), "w", encoding="utf-8") as fh:
                fh.write(blp.render(q, order))
            for tool in TOOLS:
                manifest.append([name, q["qid"], order, len(q["rows"]), tool, f"{q['qid']}_{order}_{tool}.txt", ""])
    nfiles = len({m[0] for m in manifest})
    sizes = [len(q["rows"]) for q in qs]
    with open(os.path.join(folder, "README.txt"), "w", encoding="utf-8") as fh:
        fh.write(README.format(nq=len(qs), ids=f"{qs[0]['qid']} to {qs[-1]['qid']}", lo=min(sizes), hi=max(sizes), nfiles=nfiles, nb=len(rev), nchats=len(manifest)))
    with open(os.path.join(folder, "manifest.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["prompt file", "question", "order", "passages", "tool", "save the reply as", "done (tick)"])
        w.writerows(manifest)
    with open(os.path.join(folder, "replies", "PUT_SAVED_REPLIES_HERE.txt"), "w", encoding="utf-8") as fh:
        fh.write("Save each model reply here, named like R03_A_ChatGPT.txt or R03_A_Gemini.txt\n")
    rc.write_zip(folder, zip_path, "Real30_Review_Pack")
    return zip_path, nfiles, len(manifest)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    zip_path, nfiles, nchats = build(a.pool, a.out)
    print(f"built {zip_path} ({os.path.getsize(zip_path):,} bytes); {nfiles} prompt files, {nchats} chats")


if __name__ == "__main__":
    main()
