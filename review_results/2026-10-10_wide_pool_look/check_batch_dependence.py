"""Does a re-ranker score for the same passage depend on what else is in the call, or on when the call is made? Uses 5 sealed questions (4 where the look's baseline differed from the saved list, 1 where it matched).
Same 60 candidates twice; the fused top 100 once; compares scores of the common 60, and the top 5 against the sealed run's saved list. PRIVATE, diagnosis only."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, ROOT)
import numpy as np
import pool_runner as PR, sci_index as si
pool = {q["qid"]: q for q in json.load(open(os.path.join(ROOT, "review_results/2026-10-10_sealed_run/pool.json")))["questions"]}
head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, _, _ = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
eng = PR.Engine(metas, M, si.make_client(), PR.Spend(5_000_000), PR.build_fts(metas), None)
H = lambda r: metas[r]["h"]
for qid in ["R13", "R16", "R23", "R27", "R03"]:
    q = pool[qid]["question"]
    a = eng.retrieve(q, pool=100); c100 = a["cand"]; c60 = c100[:60]; nums = a["nums"]
    s1 = eng.rerank(q, c60, model="rerank-3-lite"); s2 = eng.rerank(q, c60, model="rerank-3-lite"); s100 = eng.rerank(q, c100, model="rerank-3-lite")
    d12 = max(abs(s1[r] - s2[r]) for r in c60); d1_100 = max(abs(s1[r] - s100[r]) for r in c60)
    top5 = lambda s, cs: [H(r) for r in eng.order_by({r: s[r] * eng.weight(r, nums) for r in cs})[:5]]
    saved = [it["h"] for it in pool[qid]["lists"]["R challenger re-ranker"][:5]]
    print(f"{qid}: same 60 twice: max score difference {d12:.4f}, top5 identical {top5(s1,c60)==top5(s2,c60)} | 60 vs inside 100: max difference {d1_100:.4f}, top5 of the common 60 identical {top5(s1,c60)==top5({r:s100[r] for r in c60},c60)} | today's 60 equals the sealed run's saved top 5: {top5(s1,c60)==saved} | candidates equal sealed? n/a")
