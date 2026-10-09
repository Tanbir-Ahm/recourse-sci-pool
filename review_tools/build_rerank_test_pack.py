#!/usr/bin/env python3
"""Builds the marking pack that tests the re-ranker: the passages nobody has marked yet, for J and S to mark in ChatGPT and Gemini exactly as before.

What goes in (per question; the question's earlier passages keep their numbers and are not repeated):
  * core   - the passages of the MERGED top 5 (the order the three searches give before the re-ranker) that no version ever showed to the reviewers;
  * extra  - version A's places 6 to 10 that are not marked yet and are not in the merged top 5 (so that the whole list shown, A's ten plus the safety net, can be scored);
  * anchors - two passages that were marked in the first batch, chosen by a fixed hash and not by their marks, repeated under new numbers, to measure whether the same tool marks the same text differently
              in a second batch (a batch effect). They are not part of any search version.
New numbers continue after the question's first-batch numbers (the same top-up rule as build_topup_pack.py), in a fixed shuffle that shows nothing about where a passage came from.
Prompts: one file per question, R01_TA.txt (order A only), no reversed files. Replies are saved as R01_TA_ChatGPT.txt and R01_TA_Gemini.txt and read by ingest_llm_reviews.py with the EXTENDED POOL this
builder writes (pool_with_rerank_arms.json): the old rows plus the new ones, with two arms added for scoring, "N merged order (no re-ranker)" (top 10 of the merged order) and "M safety net" (the merged top 5
that version A's ten do not show). The extended pool names the arms and is PRIVATE; the prompts say nothing about the search, the versions, the arms, the key or the half.

  python review_tools/build_rerank_test_pack.py --pool review_results/DATE_real30_pool_dev/pool.json --fused review_results/DATE_real30_pool_dev/rerank_effect/fused_lists.json --out DIR [--index-dir ...]

Needs the index only to read the text of the new passages (read-only; it must be the commit the pool was made on). No network, no spend.
"""
import argparse
import collections
import copy
import csv
import hashlib
import json
import os
import random
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_topup_pack as TP
import pool_runner as P
import review_common as rc

SEED = "rerank-pack-v1"
ANCHOR_SALT = "rerank-anchor-v1"
TOOLS = ("ChatGPT", "Gemini")
PACK_NAME = "Second_Batch_Pack"                 # what the reviewers see: nothing in the pack says what it is for
N_ARM, M_ARM = P.SAFETY_VERSIONS


def pick_anchors(rows, qid, k=2):
    """k first-batch rows chosen by a fixed hash of (question, passage), not by how they were marked or which version showed them."""
    ordered = sorted(rows, key=lambda r: hashlib.sha256(f"{ANCHOR_SALT}|{qid}|{r['h']}".encode("utf-8")).hexdigest())
    return ordered[:k]


def plan_question(pool_q, fused_q, depth=P.SAFETY_NET_DEPTH, anchors=2):
    """What this question needs. Returns a dict of lists of (h, doc): core, extra, anchors (rows), and the arms' orders (hashes)."""
    have = {r["h"] for r in pool_q["rows"]}
    merged = [it["h"] for it in fused_q["fused"]]
    doc_of = {it["h"]: it["doc"] for it in fused_q["fused"]}
    for it in pool_q["lists"]["A today"]:
        doc_of.setdefault(it["h"], it["doc"])
    a10 = fused_q["A_top10_h"]
    core = list(dict.fromkeys(h for h in merged[:depth] if h not in have))
    extra = list(dict.fromkeys(h for h in a10[5:10] if h not in have and h not in core))
    net = P.safety_net(merged, a10, depth)
    return {"core": [(h, doc_of[h]) for h in core], "extra": [(h, doc_of[h]) for h in extra], "anchors": pick_anchors(pool_q["rows"], pool_q["qid"], anchors),
            "merged": merged, "a10": a10, "net": net}


def fetch_records(index_dir, wanted):
    """{(h, doc): row fields} for the wanted passages, read from the index (read-only)."""
    import sci_index as si
    metas, _M, _ = si._load_index(index_dir)
    hdocs = collections.defaultdict(set)
    for m in metas:
        hdocs[m["h"]].add(m["doc"])
    title = P.titles([index_dir], metas)
    by = {}
    for m in metas:
        if (m["h"], m["doc"]) in wanted and (m["h"], m["doc"]) not in by:
            by[(m["h"], m["doc"])] = {"h": m["h"], "doc": m["doc"], "pn": m["pn"], "page": m["page"], "title": title(m["doc"]), "text": m["text"], "also": sorted(hdocs[m["h"]] - {m["doc"]})}
    missing = sorted(wanted - set(by))
    if missing:
        raise SystemExit(f"{len(missing)} wanted passages are not in the index at {index_dir}, e.g. {missing[:3]}: is it the commit the pool was made on?")
    return by


def extend_question(pool_q, fused_q, records, depth=P.SAFETY_NET_DEPTH, anchors=2):
    """The question with its new rows (flagged topup, numbered on, shuffled with a fixed seed) and the two arms added to every row. Returns (extended question, list of the new rows, plan)."""
    plan = plan_question(pool_q, fused_q, depth, anchors)
    q = copy.deepcopy(pool_q)
    merged, a10, net = plan["merged"], plan["a10"], plan["net"]
    pos_merged = {h: i for i, h in enumerate(merged[:10], 1)}
    pos_net = {h: i for i, h in enumerate(net, 1)}
    pos_a = {h: i for i, h in enumerate(a10, 1)}

    def arms(h):
        v = {}
        if h in pos_merged:
            v[N_ARM] = pos_merged[h]
        if h in pos_net:
            v[M_ARM] = pos_net[h]
        return v
    for r in q["rows"]:
        r["variants"].update(arms(r["h"]))
    top = max(r["n"] for r in q["rows"])
    new = []
    for kind in ("core", "extra"):
        for h, doc in plan[kind]:
            row = dict(records[(h, doc)])
            row["variants"] = dict(arms(h), **({"A today": pos_a[h]} if h in pos_a else {}))
            row["kind"] = kind
            new.append(row)
    for old in plan["anchors"]:
        row = {k: old[k] for k in ("h", "doc", "pn", "page", "title", "text", "also")}
        row["variants"] = {}
        row["kind"] = "anchor"
        row["anchor_of"] = old["n"]
        new.append(row)
    random.Random(f"{SEED}|{pool_q['qid']}").shuffle(new)
    for i, row in enumerate(new, top + 1):
        row["n"] = i
        row["topup"] = True
    q["rows"] = q["rows"] + new
    q.setdefault("lists", {})
    by_h = {it["h"]: it for it in pool_q["lists"]["A today"]}
    for it in fused_q["fused"]:
        by_h.setdefault(it["h"], {"doc": it["doc"], "h": it["h"], "also": []})
    q["lists"][N_ARM] = [dict(by_h[h]) for h in merged[:10]]
    q["lists"][M_ARM] = [dict(by_h[h]) for h in net]
    return q, new, plan


README = """SECOND-BATCH MARKING PACK: how to run it (copy and paste; every file is run twice, once in each tool)

WHAT THIS IS
A second batch of passages for the same {nq} questions you marked before ({ids}). The passages are new, except that two per question are repeated on purpose from the first batch, as a check; you cannot tell which and you do not need to. So each file is short: {lo} to {hi} passages. The task and the rules are the same as before: an AI model marks each passage Yes / Partly / No / Misleading. All the texts are public court judgments; there is no personal or confidential information in the files.

WHAT YOU NEED
- ChatGPT AND Gemini. Every file is run in both tools (one new chat per file per tool). If one of you has only one of them, split the work so that each file still gets both tools.
- Switch OFF web search, browsing, "deep research" and any tools. We want the model to judge only the text it is given.
- Use a NEW chat for every file. Do not continue an earlier chat.

HOW TO RUN IT
1. Open the folder 'prompts'. There are {nfiles} files, named like {ex}_TA.txt. (No reversed files this time.)
2. For each file: open it, select all, copy, paste into a NEW chat, send, wait for the answer.
3. Copy the model's ENTIRE reply and save it as a plain text file named exactly like this:
      {ex}_TA_ChatGPT.txt        {ex}_TA_Gemini.txt
   Put all the saved replies in the folder 'replies'.
4. If a reply is not JSON, or is cut off, send this to the same chat: "Reply again with only the JSON object, nothing else." and save the new reply instead.
5. BEFORE you zip, open each saved file and check two things (two files in the last round were wrong this way):
   a. it is the model's REPLY (it starts with {{ and has a "marks" list), not the prompt you pasted;
   b. the ChatGPT file and the Gemini file for the same question are different replies: each tool's own answer, not one saved twice.
6. Tick the file off in manifest.csv, zip the 'replies' folder and send it back.

HOW MUCH TO DO
{nchats} chats in all ({nfiles} files x 2 tools). Each file lists the passage numbers to cover; they do not start at 1 because they continue from the first batch. Use exactly the numbers shown.

PLEASE DO NOT
- Edit the prompt text, or add your own opinion to the chat.
- Tell the model which search produced the passages (you do not know, and nor does it).
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


def build(pool_path, fused_path, out_dir, index_dir=P.DEFAULT_INDEX, records=None, anchors=2, depth=P.SAFETY_NET_DEPTH):
    """Writes out_dir/Second_Batch_Pack/ (+ .zip), out_dir/pool_with_rerank_arms.json and out_dir/build_info.json. Returns a summary dict."""
    with open(pool_path, encoding="utf-8") as fh:
        pool = json.load(fh)
    with open(fused_path, encoding="utf-8") as fh:
        fused = json.load(fh)
    if fused.get("index_commit") != pool["run"]["index_commit"]:
        raise SystemExit(f"the merged lists were made on index {str(fused.get('index_commit'))[:7]} but the pool on {pool['run']['index_commit'][:7]}")
    if fused.get("reproduction_problems"):
        raise SystemExit(f"the merged lists do not reproduce the pool for {fused['reproduction_problems']}")
    if records is None:
        head = P.index_head(index_dir)
        if head != pool["run"]["index_commit"]:
            raise SystemExit(f"the index at {index_dir} is at {head[:7]}, the pool was made on {pool['run']['index_commit'][:7]}")
        wanted = set()
        for q in pool["questions"]:
            p = plan_question(q, fused["questions"][q["qid"]], depth, anchors)
            wanted |= set(p["core"]) | set(p["extra"])
        records = fetch_records(index_dir, wanted)
    ext_questions, packs, plans = [], [], {}
    for q in pool["questions"]:
        eq, new, plan = extend_question(q, fused["questions"][q["qid"]], records, depth, anchors)
        ext_questions.append(eq)
        plans[q["qid"]] = {"core": len(plan["core"]), "extra": len(plan["extra"]), "anchors": len(plan["anchors"]), "net": len(plan["net"])}
        if new:
            packs.append({"qid": q["qid"], "question": q["question"], "rows": sorted(new, key=lambda r: r["n"])})
    os.makedirs(out_dir, exist_ok=True)
    folder, zip_path = os.path.join(out_dir, PACK_NAME), os.path.join(out_dir, PACK_NAME + ".zip")
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(os.path.join(folder, "prompts"))
    os.makedirs(os.path.join(folder, "replies"))
    manifest = []
    for p in packs:
        name = f"{p['qid']}_TA.txt"
        with open(os.path.join(folder, "prompts", name), "w", encoding="utf-8") as fh:
            fh.write(TP.render(p, "A"))
        for tool in TOOLS:
            manifest.append([name, p["qid"], "TA", len(p["rows"]), tool, f"{p['qid']}_TA_{tool}.txt", ""])
    sizes = [len(p["rows"]) for p in packs]
    with open(os.path.join(folder, "README.txt"), "w", encoding="utf-8") as fh:
        fh.write(README.format(nq=len(packs), ids=f"{packs[0]['qid']} to {packs[-1]['qid']}", lo=min(sizes), hi=max(sizes), nfiles=len(packs), nchats=len(manifest), ex=packs[0]["qid"]))
    with open(os.path.join(folder, "manifest.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["prompt file", "question", "batch", "passages", "tool", "save the reply as", "done (tick)"])
        w.writerows(manifest)
    with open(os.path.join(folder, "replies", "PUT_SAVED_REPLIES_HERE.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"Save each model reply here, named like {packs[0]['qid']}_TA_ChatGPT.txt or {packs[0]['qid']}_TA_Gemini.txt\n")
    rc.write_zip(folder, zip_path, PACK_NAME)
    ext = {"run": dict(pool["run"], extended_by={"builder": "review_tools/build_rerank_test_pack.py", "fused_lists_sha256": hashlib.sha256(open(fused_path, "rb").read()).hexdigest(),
                                                  "pool_sha256": hashlib.sha256(open(pool_path, "rb").read()).hexdigest(), "arms_added": list(P.SAFETY_VERSIONS), "safety_net_depth": depth,
                                                  "anchors_per_question": anchors, "note": "top-up rows (flagged topup) continue the first-batch numbers; anchors repeat first-batch passages (anchor_of) and belong to no version"}),
           "questions": ext_questions}
    ext["run"]["versions"] = list(pool["run"]["versions"]) + [v for v in P.SAFETY_VERSIONS if v not in pool["run"]["versions"]]
    with open(os.path.join(out_dir, "pool_with_rerank_arms.json"), "w", encoding="utf-8") as fh:
        json.dump(ext, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    info = {"questions_with_new_passages": len(packs), "prompt_files": len(packs), "chats": len(manifest), "new_passages": sum(sizes),
            "by_kind": dict(collections.Counter(r["kind"] for q in ext_questions for r in q["rows"] if r.get("topup"))), "per_question": plans,
            "zip_sha256": hashlib.sha256(open(zip_path, "rb").read()).hexdigest(), "zip_bytes": os.path.getsize(zip_path)}
    with open(os.path.join(out_dir, "build_info.json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=1)
        fh.write("\n")
    return info


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--fused", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--index-dir", default=P.DEFAULT_INDEX)
    ap.add_argument("--anchors", type=int, default=2)
    a = ap.parse_args(argv)
    info = build(a.pool, a.fused, a.out, a.index_dir, anchors=a.anchors)
    print(f"built {a.out}/{PACK_NAME}.zip ({info['zip_bytes']:,} bytes): {info['prompt_files']} prompt files, {info['chats']} chats, {info['new_passages']} passages {info['by_kind']}")


if __name__ == "__main__":
    main()
