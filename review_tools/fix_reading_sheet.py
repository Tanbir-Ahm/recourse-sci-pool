#!/usr/bin/env python3
"""The reading sheet for Mr. Advocate after the fix test's stage F (FIX_TEST_RULES_v1.md section 5, last line of the first page: "Mr. Advocate reads every passage anyone marked Misleading plus a random 20 before anything
leaves the project"): one row per passage that ANY run marked Misleading, plus 20 passages drawn at random (fixed seed) from the others. The sheet shows the question, the case, the passage and both tools' marks and quoted
evidence; it does NOT say which search version showed the passage (so that the reading is blind to the arms). Columns for his answer are empty. PRIVATE: the sheet names no arm and no key, but it is part of the project's
private material. No network, no spend.

  python review_tools/fix_reading_sheet.py --pool POOL.json --replies DIR --out OUTDIR [--seed fix-test-reading-v1] [--random 20]
"""
import argparse
import json
import os
import random
import sys

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ingest_llm_reviews as ing


def collect(pool_path, replies):
    pool, passages = ing.load_pool(pool_path)
    runs, problems, _ = ing.load_replies(replies, passages, pool)
    marks = {}
    for (tool, order), per in runs.items():
        for p, m in per.items():
            marks.setdefault(p, {})[tool] = m
    return pool, passages, marks


def pick(passages, marks, n_random, seed):
    """(misleading, random_others): passage keys. Misleading = any run marked it so. The random draw is from the passages that no run marked Misleading."""
    mis = sorted(p for p in passages if any(m == "Misleading" for m in marks.get(p, {}).values()))
    others = sorted(p for p in passages if p not in set(mis) and marks.get(p))
    rnd = sorted(random.Random(seed).sample(others, min(n_random, len(others))))
    return mis, rnd


def build(pool_path, replies, out_dir, seed="fix-test-reading-v1", n_random=20):
    pool, passages, marks = collect(pool_path, replies)
    q_text = {q["qid"]: q["question"] for q in pool}
    mis, rnd = pick(passages, marks, n_random, seed)
    os.makedirs(out_dir, exist_ok=True)
    wb = openpyxl.Workbook()
    ws0 = wb.active
    ws0.title = "Read me"
    for i, t in enumerate(["Reading sheet for Mr. Advocate: stage F of the fix test", "PRIVATE. LLM-judged marks (ChatGPT and Gemini); nothing here is lawyer-checked until you answer.",
                           f"{len(mis)} passages were marked Misleading by at least one run (all of them are listed) and {len(rnd)} more were drawn at random from the rest (seed '{seed}') as a check on the other direction.",
                           "For each row please say: is the passage Misleading for this question (Y / N / partly)? If so, what kind of problem: neighbouring regime (the wrong Act or code), overruled or replaced view, a lower court's view later reversed, special facts that do not carry over, or other. Add a comment if you wish.",
                           "The sheet does not say which search version showed a passage, on purpose."], 1):
        ws0.cell(i, 1, t).alignment = Alignment(wrap_text=True, vertical="top")
        ws0.cell(i, 1).font = Font(bold=(i == 1))
    ws0.column_dimensions["A"].width = 130
    ws = wb.create_sheet("Passages")
    head = ["Group", "Question id", "Question", "Passage no.", "Case", "Passage", "ChatGPT mark", "Gemini mark", "MR. ADVOCATE: misleading? (Y / N / partly)", "MR. ADVOCATE: kind of problem", "MR. ADVOCATE: comment"]
    ws.append(head)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="E2F0D9" if c.value.startswith("MR.") else "DDE6F0")
        c.alignment = Alignment(wrap_text=True, vertical="top")
    n = 0
    for group, keys in (("marked Misleading by at least one run", mis), ("random check", rnd)):
        for p in keys:
            r = passages[p]
            ws.append([group, p[0], q_text[p[0]], p[1], r.get("title"), r["text"], marks[p].get("ChatGPT"), marks[p].get("Gemini"), None, None, None])
            for c in ws[ws.max_row]:
                c.alignment = Alignment(wrap_text=True, vertical="top")
            for col in (9, 10, 11):
                ws.cell(ws.max_row, col).fill = PatternFill("solid", fgColor="E2F0D9")
            n += 1
    for i, w in enumerate([22, 8, 40, 8, 30, 90, 12, 12, 20, 28, 40], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "E2"
    path = os.path.join(out_dir, "Reading_Sheet_for_Mr_Advocate.xlsx")
    wb.save(path)
    info = {"misleading": len(mis), "random": len(rnd), "rows": n, "seed": seed}
    json.dump(info, open(os.path.join(out_dir, "reading_sheet_info.json"), "w"), indent=1)
    return info


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--replies", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", default="fix-test-reading-v1")
    ap.add_argument("--random", type=int, default=20)
    a = ap.parse_args(argv)
    info = build(a.pool, a.replies, a.out, a.seed, a.random)
    print(f"reading sheet written: {info['misleading']} Misleading passages + {info['random']} random = {info['rows']} rows")


if __name__ == "__main__":
    main()
