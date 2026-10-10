import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, ROOT)
import pool_runner as PR, sci_index as si
pool = {q["qid"]: q for q in json.load(open(os.path.join(ROOT, "review_results/2026-10-10_sealed_run/pool.json")))["questions"]}
key = json.load(open(os.path.join(ROOT, "review_data/ruler/real30_key_v1.json")))["questions"]["R23"]; kd = set(key["key_docs"])
head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, _, _ = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
eng = PR.Engine(metas, M, si.make_client(), PR.Spend(5_000_000), PR.build_fts(metas), None)
q = pool["R23"]["question"]
a = eng.retrieve(q, pool=1000); ranked = a["cand"]; nums = a["nums"]
kidx = [(p + 1, r) for p, r in enumerate(ranked) if metas[r]["doc"] in kd]
print("fused length", len(ranked), "| key passages in the fused order (position):", [p for p, _ in kidx][:10])
c = ranked[:100]
s = eng.rerank(q, c, model="rerank-3-lite")
fin = {r: s[r] * eng.weight(r, nums) for r in c}
o = eng.order_by(fin)
print("positions after re-rank of key passages inside fused top 100:", [(o.index(r) + 1, round(s[r], 3), metas[r]['section']) for _, r in kidx if r in fin])
print("score of the 1st, 5th, 10th:", [round(fin[o[i]], 3) for i in (0, 4, 9)])

import numpy as np
qv = eng.embed(q)
sims = np.concatenate([M[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(M), 50000)])
order = np.argsort(-sims); pos = np.empty(len(order), dtype=np.int64); pos[order] = np.arange(len(order))
kall = sorted([i for i, m in enumerate(metas) if m["doc"] in kd], key=lambda i: pos[i])
extra = [i for i in kall if i not in set(c)][:6]
s2 = eng.rerank(q, c + extra, model="rerank-3-lite")
fin2 = {r: s2[r] * eng.weight(r, nums) for r in c + extra}
o2 = eng.order_by(fin2)
print("every passage of the key judgment, by meaning rank -> final position if it were in a 100+ pool:")
for i in kall[:8]:
    print("   meaning rank", int(pos[i]) + 1, "| in the fused top 100:", i in set(c), "| final position:", (o2.index(i) + 1) if i in fin2 else "(not scored)", "| type", metas[i]["section"], "|", re.sub(r"\s+", " ", metas[i]["text"][:150]))
