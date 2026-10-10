"""Dense-only retrieval comparison on the 19 tuning questions, over the SAME judgments:
   ours    = our passages (voyage-law-2 vectors, as in the index)       Vaquill = their English chunks (voyage-4-large vectors from the Qdrant snapshot, header included)
Metric: rank of the first passage/chunk that comes from a key authority of the question (tuning half only; the sealed half's key is never read), and hits at k.
Query vectors: one embedding call per question per model (a few thousand tokens in all). Writes ab_result.json."""
import sys, json, gzip, glob, os, time
import numpy as np
sys.path.insert(0, "/home/user/recourse-sci-pool"); sys.path.insert(0, "/home/user/recourse-sci-pool/review_tools")
import sci_index as si
D = sys.argv[1] + "/"
shards = sys.argv[2].split(",")
OUT = sys.argv[3]
mp = json.load(open(D + "ab_mapping.json"))
mapping = {int(k): v for k, v in mp["mapping"].items()}
dev = mp["dev"]; key = mp["key"]
real = json.load(open("/home/user/recourse-sci-pool/review_data/ruler/real30_v1.json"))
qtext = {q["id"]: q["text"] for q in real["questions"] if q["half"] == "dev"}
wanted_cases = set(mapping.values())
# ---- Vaquill side
rows, vecs = [], []
for pre in shards:
    meta = []
    with gzip.open(D + pre + "_payload.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            p = json.loads(line)
            meta.append((p["case_id"], p["chunk_index"], p.get("language_code")))
    V = np.load(D + pre + "_vecs.npy", mmap_mode="r")
    assert len(meta) == V.shape[0], (pre, len(meta), V.shape)
    sel = [i for i, (c, ci, lg) in enumerate(meta) if c in wanted_cases and lg == "EN"]
    rows += [meta[i] for i in sel]; vecs.append(np.array(V[sel]))
    print(f"{pre}: SC points {len(meta):,}; kept {len(sel):,} (judgments shared with our index)", flush=True)
VQ = np.concatenate(vecs); VQ /= np.linalg.norm(VQ, axis=1, keepdims=True)
print("Vaquill chunks searched:", VQ.shape[0], "from", len({r[0] for r in rows}), "judgments (of", len(wanted_cases), "shared)")
# ---- our side (same judgments only, and the whole index as a second reading)
metas, M, _ = si._load_index("/home/user/recourse-sci-index")
same = np.array([m["doc"] in mapping for m in metas])
M32 = M.astype(np.float32)
print("our passages searched (same judgments):", int(same.sum()), "| whole index:", len(metas))
client = si.make_client()
tok = {"voyage-law-2": 0, "voyage-4-large": 0}
def embed(q, model):
    r = client.embed([q], model=model, input_type="query"); tok[model] += r.total_tokens
    v = np.array(r.embeddings[0], dtype=np.float32); return v / np.linalg.norm(v)
def first_rank(order_docs, wanted):
    for r, d in enumerate(order_docs, 1):
        if d in wanted: return r
    return None
def doc_rank(order_docs, wanted):
    """rank among DISTINCT judgments (a judgment is ranked by its best passage/chunk)"""
    seen = []
    for d in order_docs:
        if d not in seen:
            seen.append(d)
            if d in wanted: return len(seen)
    return None
res = {}
for q in dev:
    k = key[q]
    if not k["reachable"]: continue
    kd_ours = set(k["key_docs"]); kd_vq = set(k["in_vaquill"])
    qo, qv = embed(qtext[q], "voyage-law-2"), embed(qtext[q], "voyage-4-large")
    so_all = M32 @ qo
    order_all = np.argsort(-so_all)[:2000]
    r_all = first_rank([metas[i]["doc"] for i in order_all], kd_ours)
    so = np.where(same, so_all, -9)
    order = np.argsort(-so)[:2000]
    # key docs that exist on both sides only
    kd_both = {d for d in kd_ours if d in mapping}
    r_ours_same = first_rank([metas[i]["doc"] for i in order], kd_both) if kd_both else None
    sv = VQ @ qv
    ordv = np.argsort(-sv)[:2000]
    cases_both = {mapping[d] for d in kd_both}
    r_vq = first_rank([rows[i][0] for i in ordv], cases_both) if cases_both else None
    r_ours_doc = doc_rank([metas[i]["doc"] for i in order], kd_both) if kd_both else None
    r_vq_doc = doc_rank([rows[i][0] for i in ordv], cases_both) if cases_both else None
    res[q] = {"ours_same_judgments_doc_rank": r_ours_doc, "vaquill_doc_rank": r_vq_doc, "key_docs": len(kd_ours), "key_docs_in_vaquill": len(kd_both), "ours_whole_index_first_rank": r_all, "ours_same_judgments_first_rank": r_ours_same, "vaquill_first_rank": r_vq}
    print(q, res[q], flush=True)
def hits(field, ks=(1, 5, 10, 20, 50, 100), only=None):
    qs = [q for q, v in res.items() if v["key_docs_in_vaquill"] > 0 and (only is None or q in only)]
    return {"questions": len(qs), **{f"top{k}": sum(1 for q in qs if res[q][field] is not None and res[q][field] <= k) for k in ks}}
out = {"questions": res, "ours_same_judgments": hits("ours_same_judgments_first_rank"), "vaquill": hits("vaquill_first_rank"), "ours_whole_index": hits("ours_whole_index_first_rank"),
       "ours_same_judgments_by_judgment": hits("ours_same_judgments_doc_rank", ks=(1, 3, 5, 10, 20)), "vaquill_by_judgment": hits("vaquill_doc_rank", ks=(1, 3, 5, 10, 20)),
       "tokens": tok, "vaquill_chunks": int(VQ.shape[0]), "our_passages_same_judgments": int(same.sum()), "judgments_shared": len(wanted_cases)}
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "questions"}, indent=1))
