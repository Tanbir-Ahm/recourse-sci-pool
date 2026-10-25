"""Tier test (plan and rules: PLAN_AND_RULES.md, committed before this ran). Uses the experiments' own search code (review_tools/pool_runner.py, class Engine) on views of the index.
  python3 -I tier_test.py validate CODE_DIR OLD_INDEX_DIR OUT.json     # the mixed arm on the old index (3c80a26) must reproduce the recorded results for the 14 tuning questions
  python3 -I tier_test.py full CODE_DIR INDEX_DIR OUT.json             # all arms on the current index: 12 landmark questions + 14 tuning questions
Needs VOYAGE_API_KEY. Nothing is written to the index."""
import collections, gzip, hashlib, json, os, sys, time
import numpy as np
mode, code, idx, out_path = sys.argv[1:5]
sys.path[:0] = [code, os.path.join(code, "review_tools")]
import sci_index as si
import pool_runner as PR

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

client = CachingClient(si.make_client())
spend = PR.Spend(20_000_000)
t0 = time.time()
metas, M, _ = si._load_index(idx)
group, removed_to_kept = {}, {}
for s, v in si.ledger(idx).items():
    for l in gzip.open(os.path.join(idx, "index", v["base"] + ".docs.jsonl.gz"), "rt", encoding="utf-8"):
        r = json.loads(l); d = r["doc"]; sc = (r.get("src") or {}).get("scope")
        group[d] = "HC" if sc in ("ghc_court", "ghc_bucket", "ghc_post2017") else "SC"
        if r.get("skip") == "near_duplicate" and r.get("dup_of"): removed_to_kept[d] = r["dup_of"]
by_h = collections.defaultdict(set)
for m in metas: by_h[m["h"]].add(m["doc"])
key = json.load(open(os.path.join(code, "review_data", "ruler", "real30_key_v1.json"), encoding="utf-8"))["questions"]
qs = {}
for l in open(os.path.join(code, "review_results", "2026-10-09_real30_pool_dev", "questions.jsonl"), encoding="utf-8"):
    r = json.loads(l); qs[r["qid"]] = r["question"]
TUNING = [q for q in ("R01", "R02", "R04", "R08", "R09", "R11", "R12", "R14", "R17", "R19", "R20", "R22", "R24", "R26") if key[q]["reachable"] and key[q]["key_docs"]]
assert len(TUNING) == 14, TUNING
def wanted_docs(qid):
    w = set(key[qid]["key_docs"]); w |= {removed_to_kept[d] for d in list(w) if d in removed_to_kept}; return w

class View:
    def __init__(self, name, keep):
        self.name = name; self.sel = [i for i, m in enumerate(metas) if keep(m["doc"])]
        self.metas = [metas[i] for i in self.sel]; self.M = M[self.sel]; self.fts = PR.build_fts(self.metas)
        self.eng = PR.Engine(self.metas, self.M, client, spend, self.fts, site=None)
    def run(self, q):
        a = self.eng.retrieve(q); rs = self.eng.rerank(q, a["cand"])
        final = {r: s * self.eng.weight(r, a["nums"]) for r, s in rs.items()}
        qv = self.eng.embed(q)
        return {"order": self.eng.order_by(final), "final": final, "cand": a["cand"], "nums": a["nums"], "qv": qv}

def passages(view, order):
    return [{"doc": view.metas[r]["doc"], "h": view.metas[r]["h"], "row": r, "text": view.metas[r]["text"]} for r in order]
def first_rank(items, wanted):
    for rank, it in enumerate(items, 1):
        if (by_h[it["h"]] | {it["doc"]}) & wanted: return rank
    return None
def hits(fr): return {"hit1": bool(fr and fr <= 1), "hit5": bool(fr and fr <= 5), "hit10": bool(fr and fr <= 10)}

full = View("whole index", lambda d: True)
results = {"mode": mode, "index_passages": len(metas)}
if mode == "validate":
    rec = json.load(open(os.path.join(code, "review_results", "2026-10-09_real30_pool_dev", "authority_hits.json")))["scores"]["A today"]
    rows = []
    for q in TUNING:
        r = full.run(qs[q]); items = passages(full, r["order"][:10]); fr = first_rank(items, wanted_docs(q))
        rows.append({"qid": q, "first_rank_now": fr, "first_rank_recorded": rec[q]["first_rank"], **hits(fr)})
        print(q, "now", fr, "recorded", rec[q]["first_rank"], flush=True)
    agg = {k: sum(r[k] for r in rows) for k in ("hit1", "hit5", "hit10")}; same = sum(1 for r in rows if r["first_rank_now"] == r["first_rank_recorded"])
    print("harness check: hit1/5/10 now", agg, "| recorded 5/10/10 | identical first rank in", same, "of 14"); results.update({"rows": rows, "agg": agg, "identical": same})
else:
    sc_view = View("Supreme Court only", lambda d: group[d] == "SC"); hc_view = View("Gauhati only", lambda d: group[d] == "HC")
    print("views built:", len(full.metas), len(sc_view.metas), len(hc_view.metas), f"{time.time()-t0:.0f}s", flush=True)
    HC_BAR, HC_MAX = 0.50, 3
    lm = json.load(open(os.path.join(code, "landmarks.json"), encoding="utf-8"))["landmarks"]
    def land_metrics(items, L, pins):
        seen, ranked = set(), []
        for it in items:
            if it["doc"] not in seen: seen.add(it["doc"]); ranked.append(it["doc"])
        rank = ranked.index(L["doc"]) + 1 if L["doc"] in ranked else None
        own = [it for it in items if it["doc"] == L["doc"]][:3]
        pinned = any(si.is_pinned(it["text"], pins) for it in own)
        return {"rank": rank, "pinned": pinned, "pass": bool(rank and rank <= 5 and pinned)}
    def hc_tier(view, r, q):
        sims = view.M.astype(np.float32) @ r["qv"] if False else None
        out, seen = [], set()
        for row in r["order"]:
            m = view.metas[row]
            cos = float(view.M[row].astype(np.float32) @ r["qv"])
            if cos < HC_BAR or m["doc"] in seen: continue
            seen.add(m["doc"]); out.append({"doc": m["doc"], "cos": round(cos, 3), "final": round(r["final"][row], 3), "text": m["text"]})
            if len(out) == HC_MAX: break
        return out
    land, tune, hc_read = [], [], []
    for L in lm:
        pins = [si.shingles(p["text"]) for p in L["pinned"]]
        for qd in L["questions"]:
            q = qd["q"]; rm = full.run(q); rs = sc_view.run(q); rh = hc_view.run(q)
            order_m = passages(full, rm["order"]); order_sc_t1 = [p for p in order_m if group[p["doc"]] == "SC"]
            w8 = sorted(rm["final"].items(), key=lambda x: -(x[1] * (0.8 if group[full.metas[x[0]]["doc"]] == "HC" else 1.0))); order_w = passages(full, [r for r, _ in w8])
            tier = hc_tier(hc_view, rh, q)
            row = {"landmark": L["name"], "kind": qd["kind"], "M": land_metrics(order_m, L, pins), "T1_SC": land_metrics(order_sc_t1, L, pins), "T2_SC": land_metrics(passages(sc_view, rs["order"]), L, pins),
                   "courtweight_0.8": land_metrics(order_w, L, pins), "hc_tier_n": len(tier), "hc_in_mixed_top5": sum(1 for p in order_m[:5] if group[p["doc"]] == "HC")}
            land.append(row); hc_read.append({"qid": L["name"] + " / " + qd["kind"], "q": q, "tier": tier})
            print("landmark", L["name"][:24], qd["kind"], {k: row[k]["rank"] for k in ("M", "T1_SC", "T2_SC", "courtweight_0.8")}, "hc tier:", len(tier), flush=True)
    for qid in TUNING:
        q = qs[qid]; wd = wanted_docs(qid); rm = full.run(q); rs = sc_view.run(q); rh = hc_view.run(q)
        order_m = passages(full, rm["order"]); order_sc_t1 = [p for p in order_m if group[p["doc"]] == "SC"]
        w8 = sorted(rm["final"].items(), key=lambda x: -(x[1] * (0.8 if group[full.metas[x[0]]["doc"]] == "HC" else 1.0))); order_w = passages(full, [r for r, _ in w8])
        arms = {"M": order_m, "T1_SC": order_sc_t1, "T2_SC": passages(sc_view, rs["order"]), "courtweight_0.8": order_w}
        row = {"qid": qid}
        for a, items in arms.items(): fr = first_rank(items, wd); row[a] = {"first_rank": fr, **hits(fr)}
        tier = hc_tier(hc_view, rh, q); row["hc_tier_n"] = len(tier); row["hc_in_mixed_top5"] = sum(1 for p in order_m[:5] if group[p["doc"]] == "HC")
        tune.append(row); hc_read.append({"qid": qid, "q": q, "tier": tier})
        print("tuning", qid, {a: row[a]["first_rank"] for a in arms}, "hc tier:", len(tier), flush=True)
    def agg_land(a): return {"pass": sum(r[a]["pass"] for r in land), "case_top5": sum(1 for r in land if r[a]["rank"] and r[a]["rank"] <= 5), "case_top10": sum(1 for r in land if r[a]["rank"] and r[a]["rank"] <= 10), "not_found": sum(1 for r in land if r[a]["rank"] is None)}
    def agg_tune(a): return {k: sum(r[a][k] for r in tune) for k in ("hit1", "hit5", "hit10")}
    arms_l = ("M", "T1_SC", "T2_SC", "courtweight_0.8")
    results.update({"landmarks": land, "tuning": tune, "agg_landmarks": {a: agg_land(a) for a in arms_l}, "agg_tuning": {a: agg_tune(a) for a in arms_l},
                    "hc_tier_questions_with_a_result": sum(1 for r in land + tune if r["hc_tier_n"] > 0), "questions": len(land) + len(tune), "hc_tier_judgments_shown": sum(r["hc_tier_n"] for r in land + tune)})
    json.dump(hc_read, open(out_path.replace(".json", "_hc_tier_readings.json"), "w"))
    print("LANDMARKS", results["agg_landmarks"]); print("TUNING", results["agg_tuning"]); print("HC tier shows something for", results["hc_tier_questions_with_a_result"], "of", results["questions"], "questions;", results["hc_tier_judgments_shown"], "judgments")
cost = client.billed["rerank"] / 1e6 * 0.05 + client.billed["embed"] / 1e6 * 0.12
results["billed"] = {"embed_calls": client.calls["embed"], "embed_tokens": client.billed["embed"], "rerank_calls": client.calls["rerank"], "rerank_tokens": client.billed["rerank"], "dollars": round(cost, 4), "seconds": round(time.time() - t0)}
print("billed:", results["billed"]); json.dump(results, open(out_path, "w"), indent=1)
