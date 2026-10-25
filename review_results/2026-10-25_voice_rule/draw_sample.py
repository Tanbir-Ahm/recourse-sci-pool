"""Draws the sample of PLAN_AND_RULES.md and writes it WITHOUT the rule's verdict, so it can be labelled blind; the verdicts go to a second file that the
labelling does not read. 100 passages at random from the whole index (50 Supreme Court, 50 Gauhati) and 40 at random from the passages the rule blocks, shuffled
together. No network, no cost.
Usage: python3 -I draw_sample.py CODE_DIR INDEX_DIR OUT_DIR"""
import glob, gzip, json, os, random, sys
sys.path[:0] = [sys.argv[1]]
import authority as A
import sci_index as si

SEED = 20261025
code, idx, out = sys.argv[1:4]
metas, M, _ = si._load_index(idx)
src = {}
for f in sorted(glob.glob(os.path.join(idx, "index", "*.docs.jsonl.gz"))):
    for line in gzip.open(f, "rt", encoding="utf-8"):
        r = json.loads(line)
        if r.get("src"):
            src[r["doc"]] = r["src"]


def side(m):
    court = (src.get(m["doc"]) or {}).get("court") or ""
    return "HC" if "High Court" in court else "SC"


rows = [dict(m, _side=side(m), _src=src.get(m["doc"])) for m in metas]
rnd = random.Random(SEED)
sc = [r for r in rows if r["_side"] == "SC"]
hc = [r for r in rows if r["_side"] == "HC"]
picked = rnd.sample(sc, 50) + rnd.sample(hc, 50)
chosen = {(r["doc"], r["text"][:60]) for r in picked}
blocked_pool = [r for r in rows if (r["doc"], r["text"][:60]) not in chosen and A.safe_classify(r["text"], src=r["_src"], doc=r["doc"])["blocked"]]
picked += random.Random(SEED).sample(blocked_pool, 40)
rnd.shuffle(picked)
os.makedirs(out, exist_ok=True)
blind = [{"id": i + 1, "court": (r["_src"] or {}).get("court") or "Supreme Court of India", "paragraph": r["pn"], "text": " ".join(r["text"].split())} for i, r in enumerate(picked)]
with open(os.path.join(out, "sample_to_label.json"), "w", encoding="utf-8") as fh:
    json.dump(blind, fh, ensure_ascii=False, indent=1)
keys = [{"id": i + 1, "doc": r["doc"], "side": r["_side"], "from": "blocked pool" if j >= 100 else "random",
         "rule": {k: v for k, v in A.safe_classify(r["text"], src=r["_src"], doc=r["doc"]).items() if k in ("tier", "voice", "blocked", "reason", "states_law")}}
        for i, r in enumerate(picked) for j in [picked.index(r)]]
with open(os.path.join(out, "sample_rule_verdicts.json"), "w", encoding="utf-8") as fh:
    json.dump(keys, fh, ensure_ascii=False, indent=1)
print(len(blind), "passages written to sample_to_label.json (no verdicts in it); verdicts in sample_rule_verdicts.json")
print("blocked in the pool the 40 were drawn from:", len(blocked_pool), "of", len(rows))
