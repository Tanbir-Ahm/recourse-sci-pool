"""Model effect on IDENTICAL text: for each tuning question, a pool = the 40 chunks closest to the question under Vaquill's own vectors (voyage-4-large) plus every chunk of the key judgment(s);
the same chunk texts are embedded with voyage-law-2 and the key judgment's rank among the pool's judgments is compared under the two models. Tuning half only. Hard token cap."""
import sys, json, gzip, os
import numpy as np
sys.path.insert(0, "/home/user/recourse-sci-pool"); sys.path.insert(0, "/home/user/recourse-sci-pool/review_tools")
import sci_index as si
D = sys.argv[1] + "/"; shards = sys.argv[2].split(","); OUT = sys.argv[3]; CAP = int(sys.argv[4])
mp = json.load(open(D + "ab_mapping.json")); mapping = {int(k): v for k, v in mp["mapping"].items()}
dev, key = mp["dev"], mp["key"]
real = json.load(open("/home/user/recourse-sci-pool/review_data/ruler/real30_v1.json"))
qtext = {q["id"]: q["text"] for q in real["questions"] if q["half"] == "dev"}
wanted = set(mapping.values())
meta, vecs = [], []
for pre in shards:
    rows = []
    with gzip.open(D + pre + "_payload.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            p = json.loads(line); rows.append((p["case_id"], p["chunk_id"], p["language_code"]))
    V = np.load(D + pre + "_vecs.npy", mmap_mode="r")
    sel = [i for i, (c, ch, lg) in enumerate(rows) if c in wanted and lg == "EN"]
    meta += [rows[i] for i in sel]; vecs.append(np.array(V[sel]))
VQ = np.concatenate(vecs); VQ /= np.linalg.norm(VQ, axis=1, keepdims=True)
client = si.make_client(); tok = {"voyage-law-2": 0, "voyage-4-large": 0}
def embed(texts, model, itype):
    out = []
    for i in range(0, len(texts), 64):
        r = client.embed(texts[i:i + 64], model=model, input_type=itype); tok[model] += r.total_tokens
        if sum(tok.values()) > CAP: raise SystemExit("token cap exceeded")
        out += r.embeddings
    a = np.array(out, dtype=np.float32); return a / np.linalg.norm(a, axis=1, keepdims=True)
pools, qvec4, qvec2 = {}, {}, {}
for q in dev:
    k = key[q]
    if not k["reachable"] or not k["in_vaquill"]: continue
    qvec4[q] = embed([qtext[q]], "voyage-4-large", "query")[0]; qvec2[q] = embed([qtext[q]], "voyage-law-2", "query")[0]
    s4 = VQ @ qvec4[q]; top = list(np.argsort(-s4)[:40])
    keycases = set(k["in_vaquill"])
    keychunks = [i for i, m in enumerate(meta) if m[0] in keycases]
    pools[q] = sorted(set(top) | set(keychunks))
need = {meta[i][1] for pool in pools.values() for i in pool}
texts = {}
for pre in shards:
    with gzip.open(D + pre + "_payload.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            p = json.loads(line)
            if p["chunk_id"] in need: texts[p["chunk_id"]] = p["text"]
print("pool chunks to embed with voyage-law-2:", len(texts), flush=True)
ids = sorted(texts); E2 = dict(zip(ids, embed([texts[i] for i in ids], "voyage-law-2", "document")))
def jrank(order_cases, wanted_cases):
    seen = []
    for c in order_cases:
        if c not in seen:
            seen.append(c)
            if c in wanted_cases: return len(seen)
    return None
res = {}
for q, pool in pools.items():
    keycases = set(key[q]["in_vaquill"])
    s4 = np.array([VQ[i] @ qvec4[q] for i in pool]); s2 = np.array([E2[meta[i][1]] @ qvec2[q] for i in pool])
    o4 = [meta[pool[j]][0] for j in np.argsort(-s4)]; o2 = [meta[pool[j]][0] for j in np.argsort(-s2)]
    res[q] = {"pool_chunks": len(pool), "pool_judgments": len({meta[i][0] for i in pool}), "rank_voyage4large": jrank(o4, keycases), "rank_voyagelaw2": jrank(o2, keycases)}
    print(q, res[q], flush=True)
def hits(field, ks=(1, 3, 5, 10)):
    return {f"top{k}": sum(1 for v in res.values() if v[field] is not None and v[field] <= k) for k in ks}
out = {"questions": res, "n": len(res), "voyage_4_large_stored_vectors": hits("rank_voyage4large"), "voyage_law_2_same_chunk_text": hits("rank_voyagelaw2"), "tokens": tok}
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "questions"}, indent=1))
