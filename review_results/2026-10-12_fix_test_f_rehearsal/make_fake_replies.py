"""Writes INVENTED replies (random marks from a fixed seed) for the rehearsal pool, so that the pack, the reply reader, the scorer and the reading sheet can be exercised on real passages. The marks mean nothing;
nothing here is a result. Usage: make_fake_replies.py POOL.json OUTDIR"""
import hashlib, json, os, sys
pool = json.load(open(sys.argv[1], encoding="utf-8"))["questions"]
out = sys.argv[2]; os.makedirs(out, exist_ok=True)
def u(*parts):
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
LAD = ["Misleading", "No", "Partly", "Yes"]
for q in pool:
    for tool in ("ChatGPT", "Gemini"):
        marks = []
        for r in sorted(q["rows"], key=lambda r: r["n"]):
            x = u("base", q["qid"], r["n"])
            base = "Misleading" if x < .10 else "No" if x < .40 else "Partly" if x < .75 else "Yes"
            m = base
            if tool == "Gemini" and u("flip", q["qid"], r["n"]) < .3:
                i = LAD.index(base); m = LAD[max(0, min(3, i + (1 if u("dir", q["qid"], r["n"]) < .5 else -1)))]
            marks.append({"no": r["n"], "mark": m, "evidence": " ".join(r["text"].split())[:25], "reason": "invented", "confidence": "high"})
        open(os.path.join(out, f"{q['qid']}_A_{tool}.txt"), "w", encoding="utf-8").write(json.dumps({"question_id": q["qid"], "marks": marks, "good_answer_present": "Partly", "best_passage_no": None, "caveats": ""}))
print("wrote", len(pool) * 2, "invented reply files to", out)
