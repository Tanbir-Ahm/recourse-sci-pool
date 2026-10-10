"""More looks at the second batch (EXPLORATORY; no network, no spend): marks per question, what 'Misleading' meant, the safety-net passages, and the questions the library cannot answer.
    python3 -P analyse_second_batch_extra.py --pool .../pool_with_rerank_arms.json --replies DIR_BOTH_BATCHES --out extra_analysis.json"""
import argparse
import collections
import json
import os
import re
import sys

ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT + "/review_tools")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ingest_llm_reviews as ing      # noqa: E402
import score_rerank_arms as S         # noqa: E402
import analyse_second_batch as A      # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--pool", required=True)
ap.add_argument("--replies", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
pool_list, passages = ing.load_pool(a.pool)
runs, problems, ev = ing.load_replies(a.replies, passages, pool_list)
det = A.reply_details(a.replies)
out = {}

# per question, second batch only, per tool: Yes / Partly / No / Misleading
perq = {}
for (tool, order, qid, no), v in det.items():
    if order == "TA":
        perq.setdefault(qid, {}).setdefault(tool, collections.Counter())[v["mark"]] += 1
out["second_batch_marks_per_question"] = {q: {t: dict(c) for t, c in d.items()} for q, d in sorted(perq.items())}

# what 'Misleading' meant (second batch and all batches), by the reviewer's own reason
def kind(reason):
    r = reason.lower()
    if re.search(r"supersed|replaced|overrul|later (rule|ruling|decision|judgment|statut|amend)|older|earlier (rule|view|position|approach|case|ruling)|pre-amendment|no longer|since (been )?(over|modif)|abrogat|new (law|code)|bns|bnss|bharatiya", r):
        return "old or replaced law"
    if re.search(r"argument|counsel|contention|submission|appellant argues|respondent|petitioner's", r):
        return "a party's argument, not the court's holding"
    if re.search(r"distinguish|reject|does not apply|not applicable|inapplicable|different (facts|context|issue)|unrelated|different", r):
        return "rejected, distinguished or a different issue"
    return "other"
mis = collections.defaultdict(collections.Counter)
mis_passages = collections.defaultdict(set)
for (tool, order, qid, no), v in det.items():
    if v["mark"] == "Misleading":
        k = kind(v["reason"])
        mis["second batch" if order == "TA" else "first batch"][k] += 1
        mis_passages["second batch" if order == "TA" else "first batch"].add((qid, no))
out["misleading_marks_by_kind"] = {b: dict(c) for b, c in mis.items()}
out["misleading_distinct_passages"] = {b: len(s) for b, s in mis_passages.items()}

# safety net: which questions' net passages are 'Yes' by every run that marked them
net_rows = [(q["qid"], r) for q in pool_list for r in q["rows"] if S.M_ARM in r["variants"] and not r.get("anchor_of")]
yes_net = collections.defaultdict(list)
for qid, r in net_rows:
    votes = [runs[k][(qid, r["n"])] for k in runs if (qid, r["n"]) in runs[k]]
    if votes and all(v == "Yes" for v in votes):
        yes_net[qid].append({"n": r["n"], "title": r["title"], "para": r["pn"], "merged_place": r["variants"].get(S.N_ARM), "a_place": r["variants"].get(S.A_ARM)})
out["safety_net_passages_that_every_run_marked_Yes"] = dict(yes_net)

# the index-gap questions and controls: every second-batch mark with a one-line reason
focus = {}
for q in ("R06", "R15", "R21", "R28", "R29"):
    rows = []
    for (tool, order, qid, no), v in sorted(det.items()):
        if qid == q and order == "TA" and tool == "ChatGPT":
            p = passages[(qid, no)]
            other = det.get(("Gemini", "TA", qid, no), {}).get("mark")
            rows.append({"n": no, "title": (p["title"] or "")[:50], "para": p["pn"], "ChatGPT": v["mark"], "Gemini": other, "chatgpt_reason": v["reason"][:200]})
    focus[q] = rows
out["gap_and_control_questions_second_batch"] = focus
json.dump(out, open(a.out, "w"), indent=1)
print("misleading marks by kind:", json.dumps(out["misleading_marks_by_kind"]), "| distinct passages:", out["misleading_distinct_passages"])
print("safety-net passages every run marked Yes:", {q: [(x["n"], x["title"][:30], x["merged_place"], x["a_place"]) for x in v] for q, v in yes_net.items()})
print("per question (second batch) ChatGPT/Gemini:")
for q, d in out["second_batch_marks_per_question"].items():
    ab = lambda c: "".join(f"{k[0]}{c.get(k, 0)}" for k in ("Yes", "Partly", "No", "Misleading"))
    print(" ", q, "ChatGPT", ab(collections.Counter(d.get("ChatGPT", {}))), "Gemini", ab(collections.Counter(d.get("Gemini", {}))))
