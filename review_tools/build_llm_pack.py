#!/usr/bin/env python3
"""Builds LLM_Review_Pack.zip: one self-contained prompt file per question, in two presentation orders (A = passage-number order, B = reversed).
Passage numbers are the pool's numbers, the same as in the human review sheet. Nothing about which search found a passage is included.

  python review_tools/build_llm_pack.py --out DIR [--pool review_data/pool_all.json]
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import review_common as rc

HEADER = """You are helping to test a legal search tool for Indian Supreme Court criminal-law judgments. Below is ONE question that a person typed into the tool, followed by {n} passages the tool showed. Judge each passage as an answer to that question.

RULES
1. Judge only the text of each passage. Do NOT use outside knowledge about whether the case is famous, important or still good law. If the passage text itself says a view was later overruled, doubted or rejected, say so in "caveats".
2. Judge each passage on its own, as if the other passages did not exist. The order of the passages carries no meaning.
3. Use ONE mark per passage, exactly one of: Yes, Partly, No, Misleading.
{meanings}
4. For every passage give "evidence": a quote copied EXACTLY (character for character, no ellipses, no paraphrase) from that passage, at most 30 words, that best supports your mark. For "No", quote the words that show it is off-topic.
5. For every passage give "reason": one plain sentence, at most 30 words.
6. For every passage give "confidence": "high", "medium" or "low".
7. Do not search the web and do not use tools. If you cannot tell, choose the safer lower mark and set confidence to "low".
8. Reply with ONE JSON object only. No text before or after it and no markdown code fences.

REQUIRED JSON SHAPE (a template: use your own values)
{{
  "question_id": "{qid}",
  "marks": [
    {{"no": 1, "mark": "Yes", "evidence": "exact quote from passage 1", "reason": "one sentence", "confidence": "high"}},
    {{"no": 2, "mark": "No", "evidence": "exact quote from passage 2", "reason": "one sentence", "confidence": "medium"}}
  ],
  "good_answer_present": "Yes",
  "best_passage_no": 1,
  "caveats": ""
}}
Notes: "marks" must have exactly {n} entries, one for each passage number listed below. "good_answer_present" is "Yes" if at least one passage answers the question well, otherwise "No". "best_passage_no" is the number of the single best passage, or null if none is good. "caveats" is an empty string unless a careful reader should know something.

Passage numbers to cover: {nums}
"""

README = """LLM REVIEW PACK: how to run it (about 10 minutes of set-up, then copy and paste)

WHAT THIS IS
A test of a legal search tool for Indian Supreme Court criminal-law judgments. There are 12 questions (Q01 to Q12). For each question there are 11 to 16 passages that the search showed. An AI model is asked to mark each passage Yes / Partly / No / Misleading. All the texts are public court judgments; there is no personal or confidential information in the files.

WHAT YOU NEED
- One or more AI chat tools (for example ChatGPT, Gemini, Claude, Grok, DeepSeek). Please use at least TWO different ones; three is better. Different models disagree in useful ways.
- Switch OFF web search / browsing / "deep research" / tools if the tool has them. We want the model to judge only the text it is given.
- Use a NEW chat for every file. Do not continue an earlier chat.

HOW TO RUN IT
1. Open the folder 'prompts'. There are 24 files: Q01_A.txt ... Q12_A.txt and Q01_B.txt ... Q12_B.txt.
   - The A and B files hold the SAME passages with the SAME numbers. In B the passages are listed in reverse order. This checks whether the model is swayed by position.
2. For each file: open it, select all, copy, paste into a NEW chat, send. Wait for the answer.
3. Copy the model's ENTIRE reply and save it as a plain text file named exactly like this:
      Q03_A_<model>.txt        for example   Q03_A_ChatGPT5.txt   or   Q03_B_Gemini.txt
   Use the same <model> name every time for the same tool, with no spaces. Put all the saved replies in the folder 'replies'.
4. If a reply is not JSON, or is cut off, send this to the same chat: "Reply again with only the JSON object, nothing else." and save the new reply instead.
5. Zip the 'replies' folder and send it back.

HOW MUCH TO DO
- Minimum useful: two different models, the A files only (24 chats).
- Better: two models, A and B files (48 chats).
- Best: three models, A and B files.
If your tool has a low message limit, do Q03, Q04, Q09, Q10 first: those four are the most useful for measuring how much models agree.

PLEASE DO NOT
- Edit the prompt text, or add your own opinion to the chat.
- Tell the model which search produced the passages (you do not know, and nor does it).
- Fix or tidy the model's JSON by hand. Save what it returned. Mistakes are useful to us.
- Ask the model about whether a case is still good law. That is checked separately (Authority_Check_List.xlsx).

WHAT HAPPENS TO THE REPLIES
They are read by a script and compared. Every result will be labelled 'LLM-judged'. They are not lawyer-checked, and will not be described as lawyer-validated.

The marks mean:
   Yes        - answers the question directly
   Partly     - on the topic, useful, but incomplete
   No         - not helpful
   Misleading - could give a wrong impression (for example a lawyer's argument that the court rejects)
"""


def render(q, order):
    """The prompt for one question. q["rows"] must hold only the passages of this batch. order 'A' = number order, 'B' = reversed."""
    rows = sorted(q["rows"], key=lambda r: r["n"], reverse=(order == "B"))
    nums = ", ".join(str(r["n"]) for r in sorted(q["rows"], key=lambda r: r["n"]))
    out = [f"QUESTION ID: {q['qid']}   (prompt version: order {order})", "", HEADER.format(n=len(rows), qid=q["qid"], nums=nums, meanings=rc.meaning_lines()),
           "=" * 78, f"QUESTION: {rc.clean(q['question'])}", "=" * 78, ""]
    out += rc.passage_blocks(rows)
    out += ["=" * 78, f"END OF PASSAGES. Now reply with the single JSON object for {q['qid']} (passages {nums})."]
    return "\n".join(out) + "\n"


def build(pool_path, out_dir):
    """Writes out_dir/LLM_Review_Pack/ and out_dir/LLM_Review_Pack.zip from the first-batch passages of the pool. Returns the zip path."""
    qs = [dict(q, rows=rc.rows_of(q, False)) for q in rc.load_pool(pool_path)]
    folder, zip_path = os.path.join(out_dir, "LLM_Review_Pack"), os.path.join(out_dir, "LLM_Review_Pack.zip")
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(os.path.join(folder, "prompts"))
    os.makedirs(os.path.join(folder, "replies"))
    for q in qs:
        for order in ("A", "B"):
            with open(os.path.join(folder, "prompts", f"{q['qid']}_{order}.txt"), "w", encoding="utf-8") as fh:
                fh.write(render(q, order))
    with open(os.path.join(folder, "README.txt"), "w", encoding="utf-8") as fh:
        fh.write(README)
    with open(os.path.join(folder, "replies", "PUT_SAVED_REPLIES_HERE.txt"), "w", encoding="utf-8") as fh:
        fh.write("Save each model reply here, named like Q03_A_ChatGPT5.txt\n")
    rc.write_zip(folder, zip_path, "LLM_Review_Pack")
    return zip_path, len(qs) * 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="folder to write into")
    ap.add_argument("--pool", default=rc.DEFAULT_POOL)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    zip_path, n = build(a.pool, a.out)
    print(f"built {zip_path} ({os.path.getsize(zip_path):,} bytes); {n} prompt files")


if __name__ == "__main__":
    main()
