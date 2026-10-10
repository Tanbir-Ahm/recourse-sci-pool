"""Model test: voyage-4-large against voyage-law-2 on OUR passages, through a simulation of the real search (design and decision rule: PREREGISTRATION.md, committed before this file).

    python3 model_test.py stage0 --work DIR --vq DIR     # embeds the 14 questions with 4 models (a few thousand tokens), builds the pools, checks V1/V2, estimates tokens; embeds no passage
    python3 model_test.py stage1 --work DIR              # embeds the pool passages with voyage-4-large (token caps), cached on disk by passage hash
    python3 model_test.py stage2 --work DIR --out DIR    # simulation of the search for every arm, re-ranker, measures, validity checks V3-V5, the rule
    python3 model_test.py stage3 --work DIR --out DIR --vq DIR   # confirmation step (only after a PASS): wider competitor field for the rescued questions
    python3 model_test.py selftest                       # no network: the rule and the merge on made-up numbers

Tuning half only. The key file holds all 30 questions; the tuning ones are kept on the line that loads it and the rest is dropped unread (as with_the_host_open/scripts/f0_map.py does).
Costs: questions ~5,000 tokens; passages ~2.7M tokens expected (hard stop 3.6M); re-ranker ~0.5M tokens (cap 1.0M). PRIVATE (the pools name the key judgments)."""
import argparse
import collections
import gzip
import json
import os
import re
import sys
import time

import numpy as np

ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT)
sys.path.insert(0, ROOT + "/review_tools")
import pool_runner as P      # noqa: E402
import sci_index as si       # noqa: E402

INDEX = P.DEFAULT_INDEX
REAL = ROOT + "/review_data/ruler/real30_v1.json"
KEYF = ROOT + "/review_data/ruler/real30_key_v1.json"
FUSED = ROOT + "/review_results/2026-10-09_real30_pool_dev/rerank_effect/fused_lists.json"
ABMAP = ROOT + "/review_results/2026-10-10_vaquill_comparison/with_the_host_open/results/ab_mapping.json"
SHARDS = ["sc_shard0", "sc_shard1", "sc_shard2", "sc_shard3", "sc_shard3b"]

ARMS = {"A0": ("voyage-law-2", None), "A1": ("voyage-4-large", 1024), "A2": ("voyage-4-lite", 1024), "A2b": ("voyage-4", 1024)}
DOC_MODEL = "voyage-4-large"
CFG = dict(law2_near=300, v4_docs=12, law2_near_confirm=1000, v4_docs_confirm=30, est_cap=3_400_000, embed_cap=3_600_000, confirm_extra=800_000,
           rerank_cap=1_000_000, dim=1024, cands=60, dense=100)
PRICE = {"voyage-4-large": 0.12, "voyage-4": 0.06, "voyage-4-lite": 0.02, "voyage-law-2": 0.12, "rerank-2": 0.05}      # per million tokens; third-party lists, NOT checked with Voyage
EXPECTED_A0 = {"R01": 1, "R02": 1, "R04": 2, "R08": 2, "R09": None, "R11": 3, "R12": 5, "R14": None, "R17": 1, "R19": 1, "R20": None, "R22": None, "R24": 1, "R26": 4}   # AUTHORITY_HITS.md, version A


# ------------------------------------------------------------------ spend ledger (persisted, so caps hold across restarts)
class Ledger:
    def __init__(self, path):
        self.path = path
        self.d = json.load(open(path)) if os.path.exists(path) else {"embed": {}, "rerank": 0, "calls": {}}

    def embed(self, model, tokens):
        self.d["embed"][model] = self.d["embed"].get(model, 0) + int(tokens or 0)
        self.d["calls"][model] = self.d["calls"].get(model, 0) + 1
        self.save()

    def rerank(self, tokens):
        self.d["rerank"] += int(tokens or 0)
        self.d["calls"]["rerank-2"] = self.d["calls"].get("rerank-2", 0) + 1
        self.save()

    def doc_tokens(self):
        return self.d["embed"].get(DOC_MODEL, 0)

    def dollars(self):
        return sum(t * PRICE[m] / 1e6 for m, t in self.d["embed"].items()) + self.d["rerank"] * PRICE["rerank-2"] / 1e6

    def save(self):
        json.dump(self.d, open(self.path, "w"), indent=1)

    def line(self):
        return f"billed so far: embed {self.d['embed']} | rerank {self.d['rerank']:,} | about ${self.dollars():.4f} at the listed (unchecked) prices"


# ------------------------------------------------------------------ pure pieces (tested by selftest)
def merge(sem, kw, sc, pool=60):
    """The reciprocal-rank merge of pool_runner.Engine.retrieve, with the first-stage list given."""
    rr = {}
    for lst in (sem, kw, sc):
        for rank, rid in enumerate(lst):
            rr[rid] = rr.get(rid, 0.0) + 1.0 / (60 + rank)
    return [r for r, _ in sorted(rr.items(), key=lambda x: -x[1])][:pool]


def first_key_rank(rows, metas, key_docs):
    for pos, r in enumerate(rows, 1):
        if metas[r]["doc"] in key_docs:
            return pos
    return None


def judgment_rank(rows, scores, metas, key_docs):
    best = {}
    for r, s in zip(rows, scores):
        d = metas[r]["doc"]
        if d not in best or s > best[d]:
            best[d] = s
    for rank, d in enumerate(sorted(best, key=lambda d: -best[d]), 1):
        if d in key_docs:
            return rank
    return None


def hits(res, arm, k, qs):
    return sum(1 for q in qs if res[q][arm]["rank"] is not None and res[q][arm]["rank"] <= k)


def apply_rule(res, qs, arm="A1", base="A0"):
    """PREREGISTRATION.md section 7. res[q][arm] = {rank (first key place in the final top 10 or None), cand_has_key (bool)}."""
    rescues = [q for q in qs if not res[q][base]["cand_has_key"] and res[q][arm]["cand_has_key"]]
    gain5, gain10 = hits(res, arm, 5, qs) - hits(res, base, 5, qs), hits(res, arm, 10, qs) - hits(res, base, 10, qs)
    losses = [q for q in qs if (res[q][base]["rank"] is not None and res[q][arm]["rank"] is None) or (res[q][base]["cand_has_key"] and not res[q][arm]["cand_has_key"])]
    cond = {"rescues>=1": len(rescues) >= 1, "gain10>=1": gain10 >= 1, "losses==0": not losses, "gain5>=0": gain5 >= 0}
    return {"arm": arm, "rescues": rescues, "gain5": gain5, "gain10": gain10, "losses": losses, "conditions": cond, "passed": all(cond.values()),
            "candidate_mix_effects": [q for q in qs if q not in rescues and res[q][base]["cand_has_key"] and res[q][arm]["cand_has_key"] and
                                      (res[q][arm]["rank"] or 99) < (res[q][base]["rank"] or 99) and (res[q][arm]["rank"] or 99) <= 10]}


# ------------------------------------------------------------------ loading
def load_common():
    metas, M, _ = si._load_index(INDEX)
    real = json.load(open(REAL))
    dev = [q["id"] for q in real["questions"] if q["half"] == "dev"]
    qtext = {q["id"]: q["text"] for q in real["questions"] if q["half"] == "dev"}
    key_all = json.load(open(KEYF))["questions"]
    key = {q: key_all[q] for q in dev}                      # the sealed half is dropped here, unread
    del key_all
    qids = [q for q in dev if key[q].get("reachable")]
    key_docs = {q: {int(d) for d in key[q]["key_docs"]} for q in qids}
    by_doc = collections.defaultdict(list)
    for i, m in enumerate(metas):
        by_doc[m["doc"]].append(i)
    return metas, M, qtext, qids, key_docs, by_doc


def kw_sc(fts, q):
    toks = list(dict.fromkeys(t for t in re.findall(r"[A-Za-z0-9]{4,}", q.lower()) if t not in si.STOP))[:12]
    kw = [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (" OR ".join(f'"{t}"' for t in toks),))] if toks else []
    nums = si.section_numbers(q)
    sc = []
    for n in nums:
        sc += [r[0] for r in fts.execute("select rowid from f where f match ? order by bm25(f) limit 30", (f'"section {n}"',))]
    return kw, sc, nums


def embed_queries(client, qids, qtext, work, led):
    path = work + "/queries.json"
    cache = json.load(open(path)) if os.path.exists(path) else {}
    for arm, (model, dim) in ARMS.items():
        cache.setdefault(arm, {})
        for q in qids:
            if q in cache[arm]:
                continue
            extra = {"output_dimension": dim} if dim else {}
            resp = P.call(client.embed, [qtext[q]], model=model, input_type="query", tries=6, pause=3.0, **extra)
            led.embed(model, resp.total_tokens)
            v = np.asarray(resp.embeddings[0], dtype=np.float32)
            if v.shape != (CFG["dim"],):
                raise SystemExit(f"{model} returned {v.shape}, expected ({CFG['dim']},): stopped")
            cache[arm][q] = (v / np.linalg.norm(v)).tolist()
            json.dump(cache, open(path, "w"))
    return {arm: {q: np.asarray(v, dtype=np.float32) for q, v in d.items()} for arm, d in cache.items()}


def load_vaquill(vqdir, wanted_cases, work):
    cm, cv = work + "/vq_sub_meta.json", work + "/vq_sub_vecs.npy"
    if os.path.exists(cm) and os.path.exists(cv):
        return json.load(open(cm)), np.load(cv)
    rows, vecs = [], []
    for pre in SHARDS:
        meta = []
        with gzip.open(f"{vqdir}/{pre}_payload.jsonl.gz", "rt", encoding="utf-8") as fh:
            for line in fh:
                p = json.loads(line)
                meta.append((p["case_id"], p["chunk_index"], p.get("language_code")))
        V = np.load(f"{vqdir}/{pre}_vecs.npy", mmap_mode="r")
        assert len(meta) == V.shape[0], (pre, len(meta), V.shape)
        sel = [i for i, (c, ci, lg) in enumerate(meta) if c in wanted_cases and lg == "EN"]
        rows += [list(meta[i][:2]) for i in sel]
        vecs.append(np.array(V[sel]))
        print(f"  Vaquill {pre}: {len(meta):,} points, kept {len(sel):,}", flush=True)
    VQ = np.concatenate(vecs).astype(np.float32)
    VQ /= np.linalg.norm(VQ, axis=1, keepdims=True)
    json.dump(rows, open(cm, "w"))
    np.save(cv, VQ)
    return rows, VQ


class World:
    """Everything the stages share. `prep` holds, per question, the law-2 whole-index sims and order, the keyword and section lists, and the engine's own 60 candidates."""

    def __init__(self, work, vq=None, need_vq=True):
        self.work = work
        os.makedirs(work, exist_ok=True)
        self.metas, self.M, self.qtext, self.qids, self.key_docs, self.by_doc = load_common()
        self.led = Ledger(work + "/spend.json")
        self.client = si.make_client()
        self.qvec = embed_queries(self.client, self.qids, self.qtext, work, self.led)
        print(self.led.line(), flush=True)
        print("building the keyword table over", len(self.metas), "passages ...", flush=True)
        self.fts = P.build_fts(self.metas)
        self.spend = P.Spend(max(0, CFG["rerank_cap"] - self.led.d["rerank"]))
        self.eng = P.Engine(self.metas, self.M, self.client, self.spend, self.fts)
        by_text = {self.qtext[q]: self.qvec["A0"][q] for q in self.qids}
        self.eng.embed = lambda text: by_text[text]          # the cached law-2 question vector: no second paid call
        self.prep = {}
        for q in self.qids:
            qv0 = self.qvec["A0"][q]
            sims = np.concatenate([self.M[i:i + 50000].astype(np.float32) @ qv0 for i in range(0, len(self.M), 50000)])
            order = np.argsort(-sims)
            kw, sc, nums = kw_sc(self.fts, self.qtext[q])
            self.prep[q] = {"sims": sims, "order": order, "sem": [int(i) for i in order[:CFG["dense"]]], "kw": kw, "sc": sc, "nums": nums}
        self.vq_rows = self.VQ = self.case_to_docs = None
        if need_vq:
            mp = json.load(open(ABMAP))
            mapping = {int(k): v for k, v in mp["mapping"].items()}
            self.case_to_docs = collections.defaultdict(list)
            for d, c in mapping.items():
                self.case_to_docs[c].append(d)
            self.vq_rows, self.VQ = load_vaquill(vq, set(mapping.values()), work)
            print("Vaquill English chunks of shared judgments:", len(self.vq_rows), flush=True)

    def v4_docs(self, q, n):
        sv = self.VQ @ self.qvec["A1"][q]
        cases, seen = [], set()
        for j in np.argsort(-sv):
            c = self.vq_rows[j][0]
            if c in seen:
                continue
            seen.add(c)
            cases.append(c)
            if len(cases) == max(n, 100):
                break
        nearest_cases = cases[:100]
        docs = [d for c in cases[:n] for d in self.case_to_docs.get(c, [])]
        nearest_docs = {d for c in nearest_cases for d in self.case_to_docs.get(c, [])}
        return docs, nearest_docs

    def pool_for(self, q, n_law2, n_v4):
        pr = self.prep[q]
        key_rows = [i for d in self.key_docs[q] for i in self.by_doc.get(d, [])]
        cand_rows = merge(pr["sem"], pr["kw"], pr["sc"], CFG["cands"])
        law2_rows = [int(i) for i in pr["order"][:n_law2]]
        v4_docs, nearest_docs = self.v4_docs(q, n_v4)
        v4_rows = [i for d in v4_docs for i in self.by_doc.get(d, [])]
        pool = sorted(set(key_rows) | set(cand_rows) | set(law2_rows) | set(v4_rows))
        pool_set = set(pool)
        partly = sum(1 for d in nearest_docs if any(r in pool_set for r in self.by_doc.get(d, [])))
        fully = sum(1 for d in nearest_docs if self.by_doc.get(d) and all(r in pool_set for r in self.by_doc[d]))
        return {"pool": pool, "KEY": len(key_rows), "CAND": len(cand_rows), "LAW2_NEAR": len(law2_rows), "V4_NEAR_docs": len(v4_docs), "V4_NEAR_rows": len(v4_rows),
                "pool_passages": len(pool), "pool_docs": len({self.metas[r]["doc"] for r in pool}),
                "vaquill_nearest100_judgments_mapped_to_ours": len(nearest_docs), "of_these_with_some_passage_in_pool": partly, "of_these_with_every_passage_in_pool": fully}

    def estimate(self, pools):
        uniq = {}
        for q in pools:
            for r in pools[q]["pool"]:
                uniq.setdefault(self.metas[r]["h"], r)
        chars = sum(len(self.metas[r]["text"]) for r in uniq.values())
        return uniq, len(uniq), chars, chars / si.CHARS_PER_TOKEN * si.TOKEN_CALIBRATION


def load_emb(work):
    d = work + "/emb4"
    out = {}
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            z = np.load(os.path.join(d, f))
            for h, v in zip(z["h"], z["v"]):
                out[str(h)] = v
    return out


# ------------------------------------------------------------------ stages
def stage0(a):
    W = World(a.work, a.vq)
    # V1: the replica of the merge, fed with law-2's whole-index 100 nearest, gives the engine's own candidates
    saved = json.load(open(FUSED))["questions"]
    v1, v2 = {}, {}
    for q in W.qids:
        pr = W.prep[q]
        eng_cand = W.eng.retrieve(W.qtext[q])["cand"]
        mine = merge(pr["sem"], pr["kw"], pr["sc"], CFG["cands"])
        v1[q] = (mine == eng_cand)
        v2[q] = ([W.metas[r]["h"] for r in mine] == [it["h"] for it in saved[q]["fused"]]) if q in saved else None
    print("V1 (merge replica == engine):", all(v1.values()), v1)
    print("V2 (recomputed candidates == saved):", sum(1 for v in v2.values() if v), "of", len(v2), {q: v for q, v in v2.items() if not v})
    cfg_used = {"law2_near": CFG["law2_near"], "v4_docs": CFG["v4_docs"], "shrunk": []}
    while True:
        pools = {q: W.pool_for(q, cfg_used["law2_near"], cfg_used["v4_docs"]) for q in W.qids}
        uniq, n_uniq, chars, tokens = W.estimate(pools)
        print(f"pool {cfg_used}: {sum(p['pool_passages'] for p in pools.values()):,} passages, {n_uniq:,} unique texts, estimate {tokens:,.0f} tokens (about ${tokens * PRICE[DOC_MODEL] / 1e6:.3f})", flush=True)
        if tokens <= CFG["est_cap"]:
            break
        if cfg_used["law2_near"] > 200:
            cfg_used["law2_near"] = 200
            cfg_used["shrunk"].append("law2_near 300 -> 200")
        elif cfg_used["v4_docs"] > 8:
            cfg_used["v4_docs"] = 8
            cfg_used["shrunk"].append("v4_docs 12 -> 8")
        else:
            raise SystemExit(f"estimate {tokens:,.0f} tokens is above the {CFG['est_cap']:,} cap even after the shrink steps: stopped, nothing embedded")
    out = {"config": cfg_used, "V1": v1, "V2": v2, "estimate": {"unique_texts": n_uniq, "chars": chars, "tokens": tokens, "dollars_at_listed_price": tokens * PRICE[DOC_MODEL] / 1e6},
           "pools": {q: pools[q] for q in W.qids}}
    json.dump(out, open(a.work + "/pools.json", "w"))
    for q in W.qids:
        p = pools[q]
        print(q, {k: v for k, v in p.items() if k != "pool"})
    print(W.led.line())


def stage1(a):
    W = World(a.work, need_vq=False)
    pj = json.load(open(a.work + "/pools.json"))
    uniq, n_uniq, chars, tokens = W.estimate(pj["pools"])
    have = load_emb(a.work)
    todo = [h for h in uniq if h not in have]
    texts = [W.metas[uniq[h]]["text"] for h in todo]
    print(f"unique texts {n_uniq:,}; cached {len(have):,}; to embed {len(todo):,}; estimate {tokens:,.0f} tokens", flush=True)
    cap = CFG["embed_cap"]
    os.makedirs(a.work + "/emb4", exist_ok=True)
    n0 = len(os.listdir(a.work + "/emb4"))
    for bi, b in enumerate(si.batch_texts(texts, 60_000, 500)):
        est = sum(len(texts[i]) for i in b) / si.CHARS_PER_TOKEN * si.TOKEN_CALIBRATION
        if W.led.doc_tokens() + est > cap:
            raise SystemExit(f"stopped before the next batch: billed {W.led.doc_tokens():,} + about {est:,.0f} would pass the {cap:,} cap. Cached batches are kept.")
        resp = P.call(W.client.embed, [texts[i] for i in b], model=DOC_MODEL, input_type="document", output_dimension=CFG["dim"], tries=6, pause=4.0)
        W.led.embed(DOC_MODEL, resp.total_tokens)
        v = np.asarray(resp.embeddings, dtype=np.float32)
        if v.shape != (len(b), CFG["dim"]):
            raise SystemExit(f"unexpected vector shape {v.shape}")
        np.savez(f"{a.work}/emb4/b{n0 + bi:05d}.npz", h=np.array([todo[i] for i in b]), v=v.astype(np.float16))
        print(f"  batch {bi + 1}: {len(b)} texts, {resp.total_tokens:,} tokens (estimate {est:,.0f}); {W.led.line()}", flush=True)
    print("done.", W.led.line())


def simulate(W, q, pool_rows, emb, arms=("A0", "A1", "A2", "A2b")):
    """One question, every arm. Returns per-arm candidates, final top 10, first key rank, dense-only judgment rank in the pool."""
    pr = W.prep[q]
    kd = W.key_docs[q]
    metas = W.metas
    P_rows = list(pool_rows)
    PV = np.stack([emb[metas[r]["h"]] for r in P_rows]).astype(np.float32)
    S0 = W.M[P_rows].astype(np.float32) @ W.qvec["A0"][q]
    out, cands = {}, {}
    for arm in arms:
        if arm == "A0":
            sem, scores = pr["sem"], S0                     # the engine's own first stage (whole index); the pool copy is checked in V3
        else:
            scores = PV @ W.qvec[arm][q]
            sem = [P_rows[i] for i in np.argsort(-scores, kind="stable")[:CFG["dense"]]]
        cands[arm] = merge(sem, pr["kw"], pr["sc"], CFG["cands"])
        out[arm] = {"sem_top100": sem, "dense_judgment_rank_in_pool": judgment_rank(P_rows, scores, metas, kd)}
    # V3: A0's 100 nearest inside the pool == the whole-index 100 nearest
    pool_sem = [P_rows[i] for i in np.argsort(-S0, kind="stable")[:CFG["dense"]]]
    whole = set(pr["sem"])
    diff = whole ^ set(pool_sem)
    v3 = (not diff) or all(abs(float(pr["sims"][r]) - float(pr["sims"][pr["sem"][-1]])) < 1e-5 for r in diff)
    union = list(dict.fromkeys(r for arm in arms for r in cands[arm]))
    scores_rr = W.eng.rerank(W.qtext[q], union)
    for arm in arms:
        final = {r: scores_rr[r] * W.eng.weight(r, pr["nums"]) for r in cands[arm]}
        top10 = [r for r, _ in sorted(final.items(), key=lambda x: -x[1])][:10]
        out[arm].update({"cands": cands[arm], "cand_has_key": any(metas[r]["doc"] in kd for r in cands[arm]), "top10": top10,
                         "rank": first_key_rank(top10, metas, kd), "top10_h": [metas[r]["h"] for r in top10]})
    return out, v3, len(union)


def summarise(res, qs, arms):
    return {arm: {"hit@1": hits(res, arm, 1, qs), "hit@5": hits(res, arm, 5, qs), "hit@10": hits(res, arm, 10, qs), "candidates_with_key": sum(1 for q in qs if res[q][arm]["cand_has_key"]),
                  "dense_pool_judgment_hits": {f"top{k}": sum(1 for q in qs if res[q][arm]["dense_rank"] is not None and res[q][arm]["dense_rank"] <= k) for k in (1, 3, 5, 10)},
                  "dense_pool_mrr": round(sum(1.0 / res[q][arm]["dense_rank"] for q in qs if res[q][arm]["dense_rank"]) / len(qs), 4)} for arm in arms}


def run_sim(W, qs, pools, emb, label):
    arms = ("A0", "A1", "A2", "A2b")
    res, v3, union_sizes, rr_before = {}, {}, {}, W.spend.rerank
    saved = json.load(open(FUSED))["questions"]
    for q in qs:
        sim, ok, usz = simulate(W, q, pools[q]["pool"], emb, arms)
        v3[q], union_sizes[q] = ok, usz
        res[q] = {arm: {"rank": sim[arm]["rank"], "cand_has_key": sim[arm]["cand_has_key"], "dense_rank": sim[arm]["dense_judgment_rank_in_pool"], "top10_docs": [W.metas[r]["doc"] for r in sim[arm]["top10"]],
                        "cands_overlap_with_A0": len(set(sim[arm]["cands"]) & set(sim["A0"]["cands"]))} for arm in arms}
        res[q]["A0_top10_h_equals_recorded"] = (sim["A0"]["top10_h"] == saved[q]["A_top10_h"]) if q in saved else None
        # where the key passages sit in the first-stage list of each arm (for the rescue questions)
        kd = W.key_docs[q]
        res[q]["key_passages_in_first_stage_top100"] = {arm: sum(1 for r in sim[arm]["sem_top100"] if W.metas[r]["doc"] in kd) for arm in arms}
        res[q]["key_passages_in_candidates"] = {arm: sum(1 for r in sim[arm]["cands"] if W.metas[r]["doc"] in kd) for arm in arms}
        print(q, {arm: (res[q][arm]["rank"], res[q][arm]["cand_has_key"]) for arm in arms}, "V3", ok, flush=True)
    W.led.d["rerank"] += W.spend.rerank - rr_before
    W.led.save()
    return res, v3, union_sizes


def stage2(a):
    W = World(a.work, need_vq=False)
    pj = json.load(open(a.work + "/pools.json"))
    emb = load_emb(a.work)
    missing = [h for h in {W.metas[r]["h"] for q in pj["pools"] for r in pj["pools"][q]["pool"]} if h not in emb]
    if missing:
        raise SystemExit(f"{len(missing)} pool passages have no voyage-4-large vector yet: run stage1")
    qs = list(W.qids)
    res, v3, usz = run_sim(W, qs, pj["pools"], emb, "main")
    arms = ("A0", "A1", "A2", "A2b")
    # validity
    v4 = {q: (res[q]["A0"]["rank"], EXPECTED_A0.get(q)) for q in qs}
    off = {q: (got, want) for q, (got, want) in v4.items() if got != want}
    big = {q: gw for q, gw in off.items() if gw[0] is None or gw[1] is None or abs(gw[0] - gw[1]) > 1}
    valid = {"V1_merge_replica_equals_engine": all(pj["V1"].values()), "V2_candidates_equal_saved": sum(1 for v in pj["V2"].values() if v) >= 13,
             "V3_pool_A0_first_stage_equals_whole_index": all(v3.values()),
             "V4_A0_reproduces_recorded_ranks": (len(off) <= 2 and not big), "V4_detail_off": off,
             "V5_vector_sizes_checked_at_embedding": True}
    valid["all_ok"] = all(v for k, v in valid.items() if k.startswith("V") and not k.endswith("detail_off"))
    rule = apply_rule(res, qs, "A1")
    rule_a2 = apply_rule(res, qs, "A2")
    out = {"when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "config": pj["config"], "questions": qs, "validity": valid, "summary": summarise(res, qs, arms),
           "rule_A1": rule, "rule_A2_same_test": rule_a2, "verdict": ("INVALID" if not valid["all_ok"] else ("PASS (confirmation step still to run)" if rule["passed"] else "NOT-PASS")),
           "per_question": res, "pool_sizes": {q: {k: v for k, v in pj["pools"][q].items() if k != "pool"} for q in qs}, "rerank_union_sizes": usz, "spend": W.led.d, "dollars_at_listed_prices": round(W.led.dollars(), 4)}
    os.makedirs(a.out, exist_ok=True)
    json.dump(out, open(a.out + "/results.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ("per_question", "pool_sizes")}, indent=1))


def stage3(a):
    """Confirmation after a PASS: the rescued questions only, wider competitor field."""
    first = json.load(open(a.out + "/results.json"))
    if first["verdict"].startswith("INVALID") or not first["rule_A1"]["passed"]:
        raise SystemExit("no confirmation step: the main test did not pass (or was invalid)")
    qs = first["rule_A1"]["rescues"]
    W = World(a.work, a.vq)
    pools = {q: W.pool_for(q, CFG["law2_near_confirm"], CFG["v4_docs_confirm"]) for q in qs}
    uniq, n_uniq, chars, tokens = W.estimate(pools)
    emb = load_emb(a.work)
    new_tokens = sum(len(W.metas[r]["text"]) for h, r in uniq.items() if h not in emb) / si.CHARS_PER_TOKEN * si.TOKEN_CALIBRATION
    print(f"confirmation pools for {qs}: {n_uniq:,} unique texts, of which new about {new_tokens:,.0f} tokens", flush=True)
    json.dump({"config": {"law2_near": CFG["law2_near_confirm"], "v4_docs": CFG["v4_docs_confirm"]}, "pools": pools, "V1": {}, "V2": {}}, open(a.work + "/pools.json.confirm", "w"))
    if new_tokens > CFG["confirm_extra"]:
        raise SystemExit(f"confirmation would need about {new_tokens:,.0f} new tokens, above its {CFG['confirm_extra']:,} cap: stopped")
    # embed the missing passages (same code path as stage1, with the extra allowance)
    texts_h = [h for h in uniq if h not in emb]
    texts = [W.metas[uniq[h]]["text"] for h in texts_h]
    os.makedirs(a.work + "/emb4", exist_ok=True)
    n0 = len(os.listdir(a.work + "/emb4"))
    for bi, b in enumerate(si.batch_texts(texts, 60_000, 500)):
        est = sum(len(texts[i]) for i in b) / si.CHARS_PER_TOKEN * si.TOKEN_CALIBRATION
        if W.led.doc_tokens() + est > CFG["embed_cap"] + CFG["confirm_extra"]:
            raise SystemExit("stopped: the confirmation allowance would be passed")
        resp = P.call(W.client.embed, [texts[i] for i in b], model=DOC_MODEL, input_type="document", output_dimension=CFG["dim"], tries=6, pause=4.0)
        W.led.embed(DOC_MODEL, resp.total_tokens)
        v = np.asarray(resp.embeddings, dtype=np.float32)
        np.savez(f"{a.work}/emb4/b{n0 + bi:05d}.npz", h=np.array([texts_h[i] for i in b]), v=v.astype(np.float16))
        print(f"  batch {bi + 1}: {len(b)} texts, {resp.total_tokens:,} tokens; {W.led.line()}", flush=True)
    emb = load_emb(a.work)
    res, v3, usz = run_sim(W, qs, pools, emb, "confirm")
    rule = apply_rule(res, qs, "A1")
    stands = bool(rule["rescues"]) and rule["gain10"] >= 1
    out = {"questions": qs, "pool_sizes": {q: {k: v for k, v in pools[q].items() if k != "pool"} for q in qs}, "per_question": res, "rule_A1_on_rescued": rule, "V3": v3,
           "confirmation_stands": stands, "spend": W.led.d, "dollars_at_listed_prices": round(W.led.dollars(), 4)}
    json.dump(out, open(a.out + "/results_confirm.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "per_question"}, indent=1))


def selftest():
    # merge: a passage in two lists beats one in a single list at the same rank
    assert merge([1, 2, 3], [3, 4], [], 4) == [3, 1, 2, 4]          # 3 is in two lists; 2 and 4 tie and keep the order they entered
    # rule: made-up results
    def mk(base, arm):
        return {"A0": {"rank": base[0], "cand_has_key": base[1]}, "A1": {"rank": arm[0], "cand_has_key": arm[1]}}
    res = {"Q1": mk((1, True), (1, True)), "Q2": mk((None, False), (3, True)), "Q3": mk((4, True), (6, True))}
    r = apply_rule(res, ["Q1", "Q2", "Q3"])
    assert r["rescues"] == ["Q2"] and r["gain10"] == 1 and r["gain5"] == 0 and not r["losses"] and r["passed"], r          # Q3 slid 4 -> 6: movement, not a loss; gain5 stays 0
    res["Q3"] = mk((4, True), (None, True))                                                                                 # key falls out of the top 10: a loss
    r = apply_rule(res, ["Q1", "Q2", "Q3"])
    assert r["losses"] == ["Q3"] and not r["passed"], r
    res["Q3"] = mk((4, True), (11, False))
    assert apply_rule(res, ["Q1", "Q2", "Q3"])["losses"] == ["Q3"]
    res["Q3"] = mk((4, True), (4, True)); res["Q2"] = mk((None, False), (None, False))                                    # no rescue
    r = apply_rule(res, ["Q1", "Q2", "Q3"])
    assert not r["passed"] and r["rescues"] == [], r
    res["Q2"] = mk((None, True), (7, True))                                                                                 # candidate-mix effect: counted, not a rescue
    r = apply_rule(res, ["Q1", "Q2", "Q3"])
    assert r["rescues"] == [] and r["candidate_mix_effects"] == ["Q2"] and not r["passed"], r
    # first_key_rank / judgment_rank
    metas = [{"doc": 1}, {"doc": 2}, {"doc": 2}, {"doc": 3}]
    assert first_key_rank([0, 1, 3], metas, {2}) == 2 and first_key_rank([0, 3], metas, {2}) is None
    assert judgment_rank([0, 1, 2, 3], [0.9, 0.5, 0.8, 0.7], metas, {2}) == 2         # doc 2's best passage (0.8) is second after doc 1 (0.9)
    print("selftest ok")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["stage0", "stage1", "stage2", "stage3", "selftest"])
    ap.add_argument("--work")
    ap.add_argument("--vq")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    {"stage0": stage0, "stage1": stage1, "stage2": stage2, "stage3": stage3, "selftest": lambda _a: selftest()}[a.stage](a)


if __name__ == "__main__":
    main()
