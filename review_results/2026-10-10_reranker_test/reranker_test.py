"""Re-ranker test: Voyage's newer re-rankers on the 14 saved candidate lists. Design and rule: PREREGISTRATION.md (committed before this file).

    python3 -P reranker_test.py run --out DIR      # C1, C2 (rerank-2 twice), N1 rerank-3, N2 rerank-3-lite, X rerank-2.5; a confirming second run for any new model that passes
    python3 -P reranker_test.py selftest           # no network: the rule on made-up places

Reads the 60 saved candidates of each tuning question (rerank_effect/fused_lists.json), finds each passage in the index by (judgment, hash), re-ranks the 60 with each model, applies the passage-type weight and
section boost of version A, and compares the place of the first key passage. Tuning half only (the key file is parsed whole and the sealed entries dropped on the same line, unread). No embedding is bought.
Hard stop: 2.0M re-rank tokens. PRIVATE (names the key judgments)."""
import argparse
import collections
import json
import os
import sys
import time

ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT)
sys.path.insert(0, ROOT + "/review_tools")
import pool_runner as P      # noqa: E402
import sci_index as si       # noqa: E402

INDEX = P.DEFAULT_INDEX
REAL = ROOT + "/review_data/ruler/real30_v1.json"
KEYF = ROOT + "/review_data/ruler/real30_key_v1.json"
FUSED = ROOT + "/review_results/2026-10-09_real30_pool_dev/rerank_effect/fused_lists.json"
MODELS = {"C1": "rerank-2", "C2": "rerank-2", "N1": "rerank-3", "N2": "rerank-3-lite", "X": "rerank-2.5"}
CAP_TOKENS = 2_000_000
PRICE_UPPER = 0.05          # dollars per million tokens: the dearest listed rate, used as an upper bound for every model (rerank-3's own price was not read)
RECORDED = {"R01": 1, "R02": 1, "R04": 2, "R08": 2, "R09": None, "R11": 3, "R12": 5, "R14": None, "R17": 1, "R19": 1, "R20": None, "R22": None, "R24": 1, "R26": 4}   # AUTHORITY_HITS.md, version A


def top(p, k=10):
    return p is not None and p <= k


def hits(places, k, qs):
    return sum(1 for q in qs if top(places[q], k))


def judge(M, C1, C2, qs):
    """PREREGISTRATION.md section 6 for one run of a new model M against the two control runs. Each argument: {question: place of the first key passage in the final ordering or None}."""
    gain = [q for q in qs if top(M[q]) and not top(C1[q]) and not top(C2[q])]
    loss = [q for q in qs if top(C1[q]) and top(C2[q]) and not top(M[q])]
    guard = hits(M, 5, qs) >= min(hits(C1, 5, qs), hits(C2, 5, qs))
    return {"gain": gain, "loss": loss, "top5_guard_ok": guard, "hits5": hits(M, 5, qs), "control_hits5": [hits(C1, 5, qs), hits(C2, 5, qs)], "passed": bool(gain) and not loss and guard}


class Ledger:
    def __init__(self, path):
        self.path = path
        self.d = json.load(open(path)) if os.path.exists(path) else {"tokens": {}, "calls": {}}

    def add(self, model, tokens):
        self.d["tokens"][model] = self.d["tokens"].get(model, 0) + int(tokens or 0)
        self.d["calls"][model] = self.d["calls"].get(model, 0) + 1
        json.dump(self.d, open(self.path, "w"), indent=1)

    def total(self):
        return sum(self.d["tokens"].values())


def load_world():
    metas, _M, _ = si._load_index(INDEX)
    real = json.load(open(REAL))
    dev = [q["id"] for q in real["questions"] if q["half"] == "dev"]
    qtext = {q["id"]: q["text"] for q in real["questions"] if q["half"] == "dev"}
    key_all = json.load(open(KEYF))["questions"]
    key = {q: key_all[q] for q in dev}                      # the sealed half is dropped here, unread
    del key_all
    qids = [q for q in dev if key[q].get("reachable")]
    key_docs = {q: {int(d) for d in key[q]["key_docs"]} for q in qids}
    rowof = {}
    for i, m in enumerate(metas):
        rowof.setdefault((m["doc"], m["h"]), i)
    saved = json.load(open(FUSED))["questions"]
    cands = {}
    for q in qids:
        rows = [rowof[(int(it["doc"]), it["h"])] for it in saved[q]["fused"]]
        assert len(rows) == 60 and len(set(rows)) == len(rows), (q, len(rows))
        cands[q] = rows
    return metas, qtext, qids, key_docs, cands, saved


def weight(metas, r, nums):
    return si.W.get(metas[r]["section"], 1.0) * (1.10 if nums and si.has_section(metas[r]["text"], nums) else 1.0)


def ordering(metas, rows, scores, nums, weighted=True):
    fin = {r: scores[r] * (weight(metas, r, nums) if weighted else 1.0) for r in rows}
    return [r for r, _ in sorted(fin.items(), key=lambda x: -x[1])]


def place(metas, order, kd):
    for pos, r in enumerate(order, 1):
        if metas[r]["doc"] in kd:
            return pos
    return None


def cmd_run(a):
    os.makedirs(a.out, exist_ok=True)
    metas, qtext, qids, key_docs, cands, saved = load_world()
    led = Ledger(a.out + "/spend.json")
    raw_path = a.out + "/raw_scores.json"
    raw = json.load(open(raw_path)) if os.path.exists(raw_path) else {}
    client = si.make_client()
    nums = {q: si.section_numbers(qtext[q]) for q in qids}

    def run_arm(arm, model):
        for q in qids:
            k = f"{arm}|{q}"
            if k in raw:
                continue
            texts = [metas[r]["text"][:3500] for r in cands[q]]
            est = sum(len(t) for t in texts) / 3.5 * 1.1 + len(texts) * len(qtext[q]) / 3.5
            if led.total() + est > CAP_TOKENS:
                raise SystemExit(f"stopped before {k}: billed {led.total():,} + about {est:,.0f} would pass the {CAP_TOKENS:,}-token cap")
            resp = P.call(client.rerank, qtext[q], texts, model=model, top_k=len(texts), tries=6, pause=4.0)
            led.add(model, resp.total_tokens)
            raw[k] = {str(cands[q][x.index]): float(x.relevance_score) for x in resp.results}
            assert len(raw[k]) == 60, (k, len(raw[k]))
            json.dump(raw, open(raw_path, "w"))
        print(f"  {arm} ({model}) done; billed so far {led.total():,} tokens", flush=True)

    def scores_of(arm, q):
        return {int(r): s for r, s in raw[f"{arm}|{q}"].items()}

    def places(arm, weighted=True):
        return {q: place(metas, ordering(metas, cands[q], scores_of(arm, q), nums[q], weighted), key_docs[q]) for q in qids}

    for arm in ("C1", "C2", "N1", "N2", "X"):
        run_arm(arm, MODELS[arm])
    verdicts, confirmations = {}, {}
    pl = {arm: places(arm) for arm in raw_arms(raw)}
    for arm in ("N1", "N2"):
        v = judge(pl[arm], pl["C1"], pl["C2"], qids)
        verdicts[arm] = v
        if v["passed"]:                                     # pre-registered confirmation: a second, independent run of the same model must pass again
            run_arm(arm + "b", MODELS[arm])
            pl[arm + "b"] = places(arm + "b")
            confirmations[arm] = judge(pl[arm + "b"], pl["C1"], pl["C2"], qids)
    for arm in ("N1", "N2"):
        verdicts[arm]["confirmation"] = confirmations.get(arm)
        verdicts[arm]["PASS"] = bool(verdicts[arm]["passed"] and confirmations.get(arm) and confirmations[arm]["passed"])

    arms = list(pl)
    unweighted = {arm: places(arm, False) for arm in arms}
    top5 = lambda arm, q: set(ordering(metas, cands[q], scores_of(arm, q), nums[q])[:5])
    new_in_top5 = {arm: sum(len(top5(arm, q) - top5("C1", q)) for q in qids) for arm in arms}
    top10_same = lambda a1, a2: sum(1 for q in qids if ordering(metas, cands[q], scores_of(a1, q), nums[q])[:10] == ordering(metas, cands[q], scores_of(a2, q), nums[q])[:10])
    recorded_same = sum(1 for q in qids if [metas[r]["h"] for r in ordering(metas, cands[q], scores_of("C1", q), nums[q])[:10]] == saved[q]["A_top10_h"])
    med_top = {arm: round(sorted(max(scores_of(arm, q).values()) for q in qids)[len(qids) // 2], 3) for arm in arms}
    summary = {arm: {"hit@1": hits(pl[arm], 1, qids), "hit@5": hits(pl[arm], 5, qids), "hit@10": hits(pl[arm], 10, qids), "unweighted_hit@5": hits(unweighted[arm], 5, qids),
                     "unweighted_hit@10": hits(unweighted[arm], 10, qids), "new_passages_in_top5_vs_C1": new_in_top5[arm], "median_top_score": med_top[arm]} for arm in arms}
    out = {"when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "questions": qids, "models": MODELS, "places_weighted": pl, "places_unweighted": unweighted, "summary": summary,
           "verdicts": verdicts, "control_wobble": {"C1_vs_C2_identical_top10": top10_same("C1", "C2"), "C1_top10_equals_recorded_version_A": recorded_same, "questions": len(qids),
                                                     "key_place_differs_between_C1_and_C2": [q for q in qids if pl["C1"][q] != pl["C2"][q]]},
           "spend": led.d, "tokens_total": led.total(), "dollars_upper_bound": round(led.total() * PRICE_UPPER / 1e6, 4)}
    json.dump(out, open(a.out + "/results.json", "w"), indent=1)
    print_tables(out)


def raw_arms(raw):
    seen = []
    for k in raw:
        arm = k.split("|")[0]
        if arm not in seen:
            seen.append(arm)
    return seen


def print_tables(out):
    qs, pl, arms = out["questions"], out["places_weighted"], list(out["places_weighted"])
    cell = lambda p: "-" if p is None else str(p)
    print("\nPlace of the first key passage among the 60 (weighted, as version A; top 10 is what is shown; '-' = no key passage among the candidates)")
    print("| Q | recorded A | " + " | ".join(f"{a} {out['models'].get(a.rstrip('b'), '')}" for a in arms) + " |")
    for q in qs:
        print(f"| {q} | {cell(RECORDED.get(q))} | " + " | ".join(cell(pl[a][q]) for a in arms) + " |")
    print("\nSummary:", json.dumps(out["summary"], indent=1))
    print("\nControl wobble:", out["control_wobble"])
    print("\nVerdicts:", json.dumps(out["verdicts"], indent=1))
    print("\nTokens", out["tokens_total"], "| upper-bound dollars", out["dollars_upper_bound"], "| per model", out["spend"])


def selftest():
    qs = ["a", "b", "c", "d"]
    C1 = {"a": 1, "b": 6, "c": 12, "d": None}
    C2 = {"a": 2, "b": 5, "c": 9, "d": None}          # c is in C2's top 10 only: borderline
    M = {"a": 1, "b": 3, "c": 8, "d": None}
    v = judge(M, C1, C2, qs)
    assert v["gain"] == [] and not v["loss"] and v["top5_guard_ok"] and not v["passed"], v          # c is borderline: not a clear gain
    C2["c"] = 14
    v = judge(M, C1, C2, qs)
    assert v["gain"] == ["c"] and v["passed"], v
    M2 = dict(M, b=11)                                                                              # b was in both controls' top 10 and drops out: a loss
    v = judge(M2, C1, C2, qs)
    assert v["loss"] == ["b"] and not v["passed"], v
    M3 = {"a": 7, "b": 7, "c": 8, "d": None}                                                        # all in the top 10 but the top-5 count falls from 2 and 1 to 0
    C2["c"] = 14
    v = judge(M3, C1, C2, qs)
    assert not v["top5_guard_ok"] and not v["passed"], v
    print("selftest ok")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run", "selftest"])
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    selftest() if a.cmd == "selftest" else cmd_run(a)


if __name__ == "__main__":
    main()
