"""Measurement 3 of PLAN_AND_RULES.md: the 26 questions of the tier test, re-run so that a place freed by a block is refilled from the real candidates.
Reports, for the Gauhati list: what the old rule showed, what the rule shows now, and what the order alone changes; and for the Supreme Court list: whether the
gate costs any of the 14 key authorities. Uses the experiments' own search code (review_tools/pool_runner.py), unchanged. Needs VOYAGE_API_KEY.
  python3 -I voice_rule_test.py CODE_DIR INDEX_DIR OUT.json
"""
import collections, gzip, hashlib, json, os, sys, time
import numpy as np
code, idx, out_path = sys.argv[1:4]
sys.path[:0] = [code, os.path.join(code, "review_tools")]
import authority as A
import pool_runner as PR
import sci_index as si
import tier_select as ts


class CachingClient:
    def __init__(self, real): self.real, self.cache, self.billed, self.calls = real, {}, collections.Counter(), collections.Counter()
    def embed(self, texts, model=None, input_type=None):
        k = ("e", tuple(texts), model, input_type)
        if k not in self.cache:
            r = self.real.embed(texts, model=model, input_type=input_type); self.cache[k] = r; self.billed["embed"] += getattr(r, "total_tokens", 0) or 0; self.calls["embed"] += 1
        return self.cache[k]
    def rerank(self, query, documents, model=None, top_k=None):
        k = ("r", query, hashlib.sha1("\x00".join(documents).encode("utf-8", "replace")).hexdigest(), model, top_k)
        if k not in self.cache:
            r = self.real.rerank(query, documents, model=model, top_k=top_k); self.cache[k] = r; self.billed["rerank"] += getattr(r, "total_tokens", 0) or 0; self.calls["rerank"] += 1
        return self.cache[k]


client, spend, t0 = CachingClient(si.make_client()), PR.Spend(20_000_000), time.time()
metas, M, _ = si._load_index(idx)
group, src, removed_to_kept = {}, {}, {}
for s, v in si.ledger(idx).items():
    for line in gzip.open(os.path.join(idx, "index", v["base"] + ".docs.jsonl.gz"), "rt", encoding="utf-8"):
        r = json.loads(line); d = r["doc"]; sc = (r.get("src") or {}).get("scope")
        group[d] = "HC" if sc in ("ghc_court", "ghc_bucket", "ghc_post2017") else "SC"
        src[d] = r.get("src")
        if r.get("skip") == "near_duplicate" and r.get("dup_of"): removed_to_kept[d] = r["dup_of"]
by_h = collections.defaultdict(set)
for m in metas: by_h[m["h"]].add(m["doc"])
key = json.load(open(os.path.join(code, "review_data", "ruler", "real30_key_v1.json"), encoding="utf-8"))["questions"]
qs = {}
for line in open(os.path.join(code, "review_results", "2026-10-09_real30_pool_dev", "questions.jsonl"), encoding="utf-8"):
    r = json.loads(line); qs[r["qid"]] = r["question"]
TUNING = [q for q in ("R01", "R02", "R04", "R08", "R09", "R11", "R12", "R14", "R17", "R19", "R20", "R22", "R24", "R26") if key[q]["reachable"] and key[q]["key_docs"]]


class View:
    def __init__(self, keep):
        self.sel = [i for i, m in enumerate(metas) if keep(m["doc"])]
        self.metas = [metas[i] for i in self.sel]; self.M = M[self.sel]
        self.eng = PR.Engine(self.metas, self.M, client, spend, PR.build_fts(self.metas), site=None)
    def run(self, q):
        a = self.eng.retrieve(q); rs = self.eng.rerank(q, a["cand"])
        final = {r: s * self.eng.weight(r, a["nums"]) for r, s in rs.items()}
        return {"order": self.eng.order_by(final), "final": final, "qv": self.eng.embed(q)}


def rows_of(view, r):
    """Every re-ranked candidate as a row for tier_select.pick, best first, with its cosine and the search score."""
    out = []
    for row in r["order"]:
        m = view.metas[row]
        out.append({"doc": m["doc"], "cos": round(float(view.M[row].astype(np.float32) @ r["qv"]), 3), "final": round(r["final"][row], 3), "text": m["text"], "src": src.get(m["doc"])})
    return out


def old_rule(rows, bar=ts.BAR, max_results=ts.MAX_RESULTS):
    """What the tier test of 2026-10-25 showed: over the bar, one passage per judgment, the first three, nothing about whose words they are."""
    kept, seen = [], set()
    for r in rows:
        if r["cos"] < bar or r["doc"] in seen: continue
        seen.add(r["doc"]); kept.append(r)
        if len(kept) == max_results: break
    return kept


def wanted(qid):
    w = set(key[qid]["key_docs"]); return w | {removed_to_kept[d] for d in list(w) if d in removed_to_kept}


def first_rank(items, want):
    for rank, it in enumerate(items, 1):
        if ({it["doc"]} | by_h.get(si_h(it), set())) & want: return rank
    return None


def si_h(it):
    return hashlib.sha1(it["text"].encode("utf-8", "replace")).hexdigest()[:16]


sc_view, hc_view = View(lambda d: group[d] == "SC"), View(lambda d: group[d] == "HC")
print("views:", len(sc_view.metas), len(hc_view.metas), f"{time.time() - t0:.0f}s", flush=True)
lm = json.load(open(os.path.join(code, "landmarks.json"), encoding="utf-8"))["landmarks"]
questions = [(L["name"] + " / " + qd["kind"], qd["q"]) for L in lm for qd in L["questions"]] + [(q, qs[q]) for q in TUNING]

hc_results, sc_cost, rowsdump = [], [], []
for label, q in questions:
    rh = hc_view.run(q); rows = rows_of(hc_view, rh)
    old = old_rule(rows)
    new = ts.pick(rows)                                  # the gate and the owner's order
    gate_only = ts.pick(rows, by_authority=False)        # the gate alone, to separate the two effects
    kept_docs = {r["doc"] for r in new}
    hc_results.append({"question": label, "old": [{"doc": r["doc"], "cos": r["cos"]} for r in old],
                       "new": [{"doc": r["doc"], "cos": r["cos"], "tier": r["authority"]["tier"], "voice": r["authority"]["voice"], "states_law": r["authority"]["states_law"], "also_in": r["also_in"]} for r in new],
                       "gate_only": [r["doc"] for r in gate_only],
                       "dropped_from_old": [{"doc": r["doc"], "reason": A.safe_classify(r["text"], src=r.get("src"), doc=r["doc"])["reason"], "tier": A.safe_classify(r["text"], src=r.get("src"), doc=r["doc"])["tier"]} for r in old if r["doc"] not in kept_docs],
                       "new_in_new": [r["doc"] for r in new if r["doc"] not in {o["doc"] for o in old}]})
    rowsdump.append({"question": label, "shown": [{"doc": r["doc"], "cos": r["cos"], "tier": r["authority"]["tier"], "voice": r["authority"]["voice"], "cue": r["authority"]["cue"], "quote": r["authority"]["quote"][:600], "text": r["text"][:600]} for r in new]})
    print("HC", label[:34], "old", [r["doc"] for r in old], "->", [r["doc"] for r in new], flush=True)

for qid in TUNING:
    q = qs[qid]; rs = sc_view.run(q); rows = rows_of(sc_view, rs)
    want = wanted(qid)
    plain = [{"doc": r["doc"], "text": r["text"], "h": si_h(r)} for r in rows]
    gated = [r for r in rows if not A.safe_classify(r["text"], src=r.get("src"), doc=r["doc"])["blocked"]]
    ordered = sorted(gated, key=lambda r: A.sort_key(A.safe_classify(r["text"], src=r.get("src"), doc=r["doc"]), r["final"]))
    f_plain, f_gated, f_ord = (first_rank(plain, want), first_rank(gated, want), first_rank(ordered, want))
    sc_cost.append({"qid": qid, "plain": f_plain, "gated": f_gated, "ordered": f_ord,
                    "key_blocked": bool(f_plain and not f_gated)})
    print("SC", qid, "key at", f_plain, "-> gate", f_gated, "-> ordered", f_ord, flush=True)


def hits(rs, k): return sum(1 for r in rs if r and r <= k)


agg = {a: {f"hit{k}": hits([r[a] for r in sc_cost], k) for k in (1, 5, 10)} for a in ("plain", "gated", "ordered")}
cost = client.billed["rerank"] / 1e6 * 0.05 + client.billed["embed"] / 1e6 * 0.12
res = {"questions": len(questions), "hc": hc_results, "sc_key_authority": sc_cost, "sc_agg": agg,
       "hc_counts": {"old": sum(len(r["old"]) for r in hc_results), "new": sum(len(r["new"]) for r in hc_results),
                     "dropped": sum(len(r["dropped_from_old"]) for r in hc_results), "refilled": sum(len(r["new_in_new"]) for r in hc_results),
                     "questions_with_nothing": sum(1 for r in hc_results if not r["new"]),
                     "tiers": dict(collections.Counter(s["tier"] for r in hc_results for s in r["new"]))},
       "billed": {"embed_calls": client.calls["embed"], "embed_tokens": client.billed["embed"], "rerank_calls": client.calls["rerank"], "rerank_tokens": client.billed["rerank"], "dollars": round(cost, 4), "seconds": round(time.time() - t0)}}
print("\nHC:", res["hc_counts"]); print("SC key authority (hit at 1/5/10):", agg); print("billed:", res["billed"])
json.dump(res, open(out_path, "w"), indent=1)
json.dump(rowsdump, open(out_path.replace(".json", "_shown.json"), "w"), indent=1)
