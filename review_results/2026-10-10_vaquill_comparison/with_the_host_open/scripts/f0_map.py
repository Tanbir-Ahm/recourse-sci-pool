"""Maps our index documents (and the tuning half's key documents) to Vaquill case ids. Tuning half only: the key entries of the sealed half are never read."""
import sys, re, json, sqlite3, collections
import pandas as pd
sys.path.insert(0, "/home/user/recourse-sci-pool"); sys.path.insert(0, "/home/user/recourse-sci-pool/review_tools")
import sci_index as si
meta_p, corpus_p, out_p = sys.argv[1:4]
real = json.load(open("/home/user/recourse-sci-pool/review_data/ruler/real30_v1.json"))
dev = [q["id"] for q in real["questions"] if q["half"] == "dev"]
key_all = json.load(open("/home/user/recourse-sci-pool/review_data/ruler/real30_key_v1.json"))["questions"]
key = {q: key_all[q] for q in dev}                         # the sealed half is dropped here, unread
del key_all
metas, M, _ = si._load_index("/home/user/recourse-sci-index")
docs_in_index = sorted({m["doc"] for m in metas}, key=int)
c = sqlite3.connect(f"file:{corpus_p}?mode=ro", uri=True)
import glob, gzip
crawl = {int(r[0]): (r[1], r[2]) for r in c.execute("select src_id, insc, date from docs where source='crawl'")}            # crawl id (= index doc number) -> (insc, iso date)
bucket = {}
for f in glob.glob("/home/user/recourse-sci-index/index/*.docs.jsonl.gz"):
    with gzip.open(f, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                src = r.get("src")
                if isinstance(src, dict) and src.get("case_id"):
                    d_, m_, y_ = (src.get("date") or "").split("-") if (src.get("date") or "").count("-") == 2 else (None, None, None)
                    bucket[r["doc"]] = (src["case_id"], f"{y_}-{m_}-{d_}" if y_ else None)
vq = pd.read_parquet(meta_p, columns=["case_id", "language_code", "chunk_index", "decision_date"])
vq = vq[(vq.language_code == "en") & (vq.chunk_index == 0)].set_index("case_id").decision_date.to_dict()
vq_by_key = {re.sub(r"[^0-9A-Za-z]", "", k).upper(): (k, d) for k, d in vq.items()}
mapping, miss = {}, collections.Counter()
for d in docs_in_index:
    insc, date = bucket.get(d, (None, None)) if d >= 1_000_000_000 else crawl.get(d, (None, None))
    src = None
    if not insc: miss["no INSC id in our corpus"] += 1; continue
    k = re.sub(r"[^0-9A-Za-z]", "", insc).upper()
    if k not in vq_by_key: miss["INSC id not in Vaquill English set"] += 1; continue
    cid, dd = vq_by_key[k]
    if (date or "")[:10] != dd[:10]: miss["same INSC id, different date"] += 1; continue
    mapping[d] = cid
print("our index documents:", len(docs_in_index), "| mapped to a Vaquill English case:", len(mapping), f"({len(mapping)/len(docs_in_index):.1%})", "| unmapped:", dict(miss))
kd = {}
for q, k in key.items():
    docs = [int(x) for x in k["key_docs"]]
    kd[q] = {"reachable": bool(k.get("reachable")), "key_docs": docs, "in_vaquill": [mapping[d] for d in docs if d in mapping], "not_in_vaquill": [d for d in docs if d not in mapping]}
print("tuning-half key documents mapped to Vaquill:")
for q, v in kd.items():
    if v["reachable"]: print("  ", q, "key docs", len(v["key_docs"]), "| in Vaquill", len(v["in_vaquill"]), "| not", len(v["not_in_vaquill"]))
json.dump({"mapping": mapping, "key": kd, "dev": dev}, open(out_p, "w"))
