"""Tests for review_tools/build_real30_pack.py and for reading replies to its prompts (ingest_llm_reviews.py with R-numbered questions), on an invented pool.
Run: python review_tools/test_build_real30_pack.py"""
import json
import os
import shutil
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_real30_pack as B
import ingest_llm_reviews as ing

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


def question(i, nrows):
    qid = f"R{i:02d}"
    rows = [{"n": n, "h": f"h{i}-{n}", "doc": 1000 + n, "pn": str(n), "page": n, "title": f"Case {n} v. State (2020)", "text": f"{n}. Passage {n} of {qid} says something about bail and arrest in plain words.",
             "also": [], "variants": {"A today": n, "S site shown": 1} if n <= 5 else {"B no repeats": n}} for n in range(1, nrows + 1)]
    return {"qid": qid, "domain": "B", "kind": ["everyday", "legal", "narrative"][i % 3], "question": f"Question text for {qid}: can the police arrest without a notice?", "rewrite": f"SECRET REWRITE {qid}", "half": "dev",
            "rows": rows, "lists": {"A today": []}}


tmp = tempfile.mkdtemp()
try:
    qs = [question(i, 6 + i % 5) for i in range(1, 31)]
    pool_path = os.path.join(tmp, "pool.json")
    json.dump({"run": {"when": "x"}, "questions": qs}, open(pool_path, "w"))
    zip_path, nfiles, nchats = B.build(pool_path, tmp)
    folder = os.path.join(tmp, "Real30_Review_Pack")
    names = sorted(os.listdir(os.path.join(folder, "prompts")))
    rev = [q["qid"] for q in qs if q["qid"] in B.reversed_set([x["qid"] for x in qs])]
    check("every question has an A file and only the hash-chosen ones have a B file", [n for n in names if n.endswith("_A.txt")] == [f"{q['qid']}_A.txt" for q in qs] and [n[:3] for n in names if n.endswith("_B.txt")] == rev, names)
    ids = [q["qid"] for q in qs]
    check("exactly a third are also reversed, and the choice is fixed by a hash, not by anyone", len(rev) == 10 and B.reversed_set(ids) == B.reversed_set(list(reversed(ids))) and len(B.reversed_set(ids[:19])) == 6 and len(B.reversed_set(ids[:12])) == 4, (len(rev), len(B.reversed_set(ids[:19]))))
    a = open(os.path.join(folder, "prompts", "R03_A.txt"), encoding="utf-8").read()
    check("a prompt holds the question, the passages and the marking rules", "Question text for R03" in a and "--- PASSAGE 1 ---" in a and "Yes, Partly, No, Misleading" in a)
    bad = ["A today", "B no repeats", "S site shown", "SECRET REWRITE", "variants", "half", "domain", "dev", "sealed", "lists", "rewrite"]
    allp = "\n".join(open(os.path.join(folder, "prompts", n), encoding="utf-8").read() for n in names)
    check("no prompt names a search version, a rewrite, a half or a domain", not [w for w in bad if w in allp.replace("Judge only the text", "")], [w for w in bad if w in allp])
    if rev:
        b = open(os.path.join(folder, "prompts", f"{rev[0]}_B.txt"), encoding="utf-8").read()
        a2 = open(os.path.join(folder, "prompts", f"{rev[0]}_A.txt"), encoding="utf-8").read()
        pa = [int(x.split()[2]) for x in a2.split("\n") if x.startswith("--- PASSAGE")]
        pb = [int(x.split()[2]) for x in b.split("\n") if x.startswith("--- PASSAGE")]
        check("B lists the same passages with the same numbers in reverse order", pa == sorted(pa) and pb == pa[::-1] and len(pa) > 1, (pa, pb))
    readme = open(os.path.join(folder, "README.txt"), encoding="utf-8").read()
    check("the README names both tools and the file and chat counts", "ChatGPT AND Gemini" in readme and f"{nfiles} files" in readme and f"{nchats} chats" in readme and "R01_A_Gemini.txt" in readme and "R03_A" not in readme)
    check("the README does not mention the search versions, the key or the halves", not any(w in readme for w in ("search version", "sealed", "tuning", "rewrite", "register")))
    rows = open(os.path.join(folder, "manifest.csv"), encoding="utf-8").read().strip().split("\n")
    check("the manifest has a line per file per tool", len(rows) - 1 == nchats == nfiles * 2, (len(rows), nchats, nfiles))
    with zipfile.ZipFile(zip_path) as z:
        zn = z.namelist()
    check("the zip holds the prompts, the README, the manifest and the replies folder", f"Real30_Review_Pack/prompts/R01_A.txt" in zn and "Real30_Review_Pack/README.txt" in zn and "Real30_Review_Pack/manifest.csv" in zn and any(n.startswith("Real30_Review_Pack/replies/") for n in zn))

    # replies to these prompts are read by the ingestion tool
    pool, passages = ing.load_pool(pool_path)
    check("the ingestion tool reads the pool runner's file (a dict with 'questions')", len(pool) == 30 and ("R01", 1) in passages)
    rep = os.path.join(tmp, "replies")
    os.makedirs(rep)
    q1 = qs[2]                                          # R03, an everyday question
    for tool in ("ChatGPT", "Gemini"):
        reply = {"question_id": "R03", "marks": [{"no": r["n"], "mark": "Yes" if r["n"] <= 3 else "No", "evidence": r["text"].split(".")[1].strip()[:20], "reason": "x", "confidence": "high"} for r in q1["rows"]], "good_answer_present": "Yes", "best_passage_no": 1, "caveats": ""}
        open(os.path.join(rep, f"R03_A_{tool}.txt"), "w").write(json.dumps(reply))
    runs, problems, ev = ing.load_replies(rep, passages, pool)
    check("replies named R03_A_ChatGPT.txt and R03_A_Gemini.txt are read as two runs", sorted(runs) == [("ChatGPT", "A"), ("Gemini", "A")] and runs[("ChatGPT", "A")][("R03", 1)] == "Yes" and runs[("Gemini", "A")][("R03", 5)] == "No", (sorted(runs), problems[:3]))
    cons, pair, var_rows = ing.analyse(runs, passages, pool)
    v = {r["variant"]: r for r in var_rows}
    check("the version scores come out of the pool's variants, and everyday/narrative questions count as the plain-language group", "A today" in v and v["A today"]["questions"] == 1 and v["A today"]["yes_lay"] is not None and v["A today"]["yes_legal"] is None, v.get("A today"))
    check("a file that matches neither Qnn nor Rnn is reported", any("does not match" in m for _, m in ing.load_replies((lambda d: (open(os.path.join(d, "bogus.txt"), "w").write("x"), d)[1])(tempfile.mkdtemp()), passages, pool)[1]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
