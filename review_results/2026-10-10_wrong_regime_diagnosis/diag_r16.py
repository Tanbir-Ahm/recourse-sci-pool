"""Second look at R16 only (used-up question): what does the re-ranker put above the right passage, and which of the 60 candidates actually discuss the Domestic Violence Act? Diagnosis only. PRIVATE."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, ROOT)
import numpy as np
import pool_runner as PR, sci_index as si
pool = {q["qid"]: q for q in json.load(open(os.path.join(ROOT, "review_results/2026-10-10_sealed_run/pool.json")))["questions"]}
q = pool["R16"]["question"]
key = json.load(open(os.path.join(ROOT, "review_data/ruler/real30_key_v1.json")))["questions"]["R16"]
kdocs = set(key["key_docs"])
head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, _, _ = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
eng = PR.Engine(metas, M, si.make_client(), PR.Spend(500000), PR.build_fts(metas), None)
a = eng.retrieve(q); cand = a["cand"]
base = eng.rerank(q, cand)
raw = eng.order_by(base)
title = lambda r: re.sub(r"\s+", " ", str(metas[r].get("title") or metas[r]["doc"]))[:55]
dv = re.compile(r"domestic violence|protection of women", re.I); lim = re.compile(r"498-?A|468|473|limitation", re.I)
print("key passages (in the 60):")
for r in cand:
    if metas[r]["doc"] in kdocs:
        t = metas[r]["text"]
        print("  raw position", raw.index(r) + 1, "| mentions DV Act:", bool(dv.search(t)), "| mentions limitation:", bool(lim.search(t)), "| type", metas[r]["section"], "|", re.sub(r"\s+", " ", t[:260]))
print("\nrerank-2 order, first 14 of the 60 (DV = mentions the Domestic Violence Act; LIM = mentions limitation or 498A):")
for p, r in enumerate(raw[:14]):
    t = metas[r]["text"]
    print(f"  {p+1:2} {'KEY' if metas[r]['doc'] in kdocs else '   '} DV={int(bool(dv.search(t)))} LIM={int(bool(lim.search(t)))} type={metas[r]['section']:10} {title(r)}")
dvpos = [p + 1 for p, r in enumerate(raw) if dv.search(metas[r]['text'])]
print("\npositions of the passages that mention the DV Act (of 60):", dvpos[:20], "... total", len(dvpos))
dvlim = [p + 1 for p, r in enumerate(raw) if dv.search(metas[r]['text']) and lim.search(metas[r]['text'])]
print("positions of passages that mention BOTH the DV Act and limitation:", dvlim)
