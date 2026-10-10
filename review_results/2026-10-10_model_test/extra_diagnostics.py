"""EXPLORATORY, after the verdict (not part of the pre-registered rule; no network, no spend): for every tuning question and arm, where the key judgment's passages sit in the arm's own nearest-passage list over the pool
(passage level; the pool is thin for A1, see PREREGISTRATION.md section 3), and, for A0, over the whole index.
    python3 -P extra_diagnostics.py --work DIR --out FILE
Needs the cached voyage-4-large vectors (stage 1) and the question vectors (stage 0)."""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_test as T       # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    metas, M, qtext, qids, key_docs, by_doc = T.load_common()
    qv = {arm: {q: np.asarray(v, dtype=np.float32) for q, v in d.items()} for arm, d in json.load(open(a.work + "/queries.json")).items()}
    pools = json.load(open(a.work + "/pools.json"))["pools"]
    emb = T.load_emb(a.work)
    out = {}
    for q in qids:
        rows = pools[q]["pool"]
        PV = np.stack([emb[metas[r]["h"]] for r in rows]).astype(np.float32)
        isk = np.array([metas[r]["doc"] in key_docs[q] for r in rows])
        entry = {"pool_passages": len(rows), "key_passages_in_pool": int(isk.sum())}
        S0 = M[rows].astype(np.float32) @ qv["A0"][q]
        sims_all = np.concatenate([M[i:i + 50000].astype(np.float32) @ qv["A0"][q] for i in range(0, len(M), 50000)])
        kr = [i for d in key_docs[q] for i in by_doc[d]]
        rank_all = (np.argsort(np.argsort(-sims_all)) + 1)
        entry["A0_whole_index_best_key_passage_rank"] = int(rank_all[kr].min())
        for arm in ("A0", "A1", "A2", "A2b"):
            S = S0 if arm == "A0" else PV @ qv[arm][q]
            order = np.argsort(-S, kind="stable")
            rk = np.empty(len(S), dtype=int)
            rk[order] = np.arange(1, len(S) + 1)
            kranks = sorted(int(x) for x in rk[isk])
            entry[arm] = {"best_key_passage_rank_in_pool": kranks[0], "key_passages_in_top40": sum(1 for x in kranks if x <= 40), "key_passages_in_top100": sum(1 for x in kranks if x <= 100),
                          "score_of_best_key_passage": round(float(S[isk].max()), 4), "score_at_place_40": round(float(S[order[39]]), 4), "score_at_place_100": round(float(S[order[99]]), 4),
                          "five_best_key_ranks": kranks[:5]}
        out[q] = entry
        print(q, "pool", entry["pool_passages"], "key passages", entry["key_passages_in_pool"], "| A0 whole-index best key passage", entry["A0_whole_index_best_key_passage_rank"], "|",
              " | ".join(f"{arm}: best {entry[arm]['best_key_passage_rank_in_pool']}, top40 {entry[arm]['key_passages_in_top40']}, top100 {entry[arm]['key_passages_in_top100']}" for arm in ("A0", "A1", "A2", "A2b")))
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
