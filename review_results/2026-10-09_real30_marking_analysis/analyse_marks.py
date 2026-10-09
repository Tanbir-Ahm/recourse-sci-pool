"""Thorough analysis of the J and S marks on the tuning half of the 30 questions (all marks are LLM-judged: ChatGPT and Gemini, two presentation orders for a third of the questions).
Reads the normalised replies, the pool and the private key; writes analysis.json (every number the report quotes). PRIVATE. Run: python analyse_marks.py

Definitions used throughout (so that a number can be traced):
  * consensus mark of a passage: the plurality of the runs that marked it; a tie for the most votes is 'split' (and is dropped under 'agreed only', settled to the lower or the higher mark under the other two treatments).
  * a version's score on a question: the share of its top-5 passages (all of S's) with a given consensus mark, averaged over questions (every question counts once).
  * paired difference: version minus A today on the same questions; the interval is a bootstrap over questions (5,000 resamples, fixed seed), so it says how much the answer could move if other questions had been asked.
"""
import collections, itertools, json, os, random, re, sys
ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT + "/review_tools")
import ingest_llm_reviews as ing

HERE = os.path.dirname(os.path.abspath(__file__))
POOL = ROOT + "/review_results/2026-10-09_real30_pool_dev/pool.json"
REPLIES = HERE + "/replies_for_the_reader"
KEY = json.load(open(ROOT + "/review_data/ruler/real30_key_v1.json"))["questions"]
REAL = json.load(open(ROOT + "/review_data/ruler/real30_v1.json"))
DOMAINS = {d["code"] if isinstance(d, dict) and "code" in d else k: d for k, d in (REAL["domains"].items() if isinstance(REAL["domains"], dict) else enumerate(REAL["domains"]))}
RERANK = json.load(open(ROOT + "/review_results/2026-10-09_real30_pool_dev/rerank_effect/rerank_effect.json"))

pool, passages = ing.load_pool(POOL)
runs, problems, ev = ing.load_replies(REPLIES, passages, pool)
cons, pair, var_rows = ing.analyse(runs, passages, pool)
sens = ing.sensitivity(runs, passages, pool)
keys = sorted(runs)
qinfo = {q["qid"]: q for q in pool}
VERS = ["A today", "B no repeats", "E no multiplier", "C rewrite", "F merged", "S site shown"]
out = {}

# ------------------------------------------------------------------ replies as raw objects (reasons, caveats, good_answer_present)
raw = {}
for fn in sorted(os.listdir(REPLIES)):
    m = ing.NAME_RE.match(fn)
    if not m:
        continue
    qid, order, model = f"{m.group(1).upper()}{int(m.group(2)):02d}", m.group(3).upper(), re.sub(r"(?:\.(?:txt|json|md))+$", "", m.group(4), flags=re.I)
    obj, _ = ing.parse_reply(open(os.path.join(REPLIES, fn), encoding="utf-8").read())
    raw[(qid, model, order)] = obj

# ------------------------------------------------------------------ 1. reliability
rel = {"runs": {f"{m}/{o}": len(r) for (m, o), r in runs.items()}, "files_with_replies": len(raw)}
dist = {}
for (m, o), r in runs.items():
    c = collections.Counter(r.values())
    dist[f"{m}/{o}"] = {k: c.get(k, 0) for k in ing.MARKS} | {"n": len(r)}
rel["mark_distribution_by_run"] = dist
tool = collections.defaultdict(collections.Counter)
for (m, o), r in runs.items():
    tool[m].update(r.values())
rel["mark_distribution_by_tool"] = {m: {k: round(c[k] / sum(c.values()), 3) for k in ing.MARKS} | {"n": sum(c.values())} for m, c in tool.items()}
# same passages marked by both tools (A order)
both = sorted(set(runs[("ChatGPT", "A")]) & set(runs[("Gemini", "A")]))
conf = collections.Counter((runs[("ChatGPT", "A")][p], runs[("Gemini", "A")][p]) for p in both)
rel["chatgpt_vs_gemini_A_confusion"] = {f"ChatGPT {a} / Gemini {b}": n for (a, b), n in sorted(conf.items())}
rank = {"Misleading": 0, "No": 1, "Partly": 2, "Yes": 3}
rel["on_the_common_passages_chatgpt_marks_higher_than_gemini"] = sum(1 for (a, b), n in conf.items() if rank[a] > rank[b] for _ in range(n))
rel["on_the_common_passages_gemini_marks_higher_than_chatgpt"] = sum(1 for (a, b), n in conf.items() if rank[a] < rank[b] for _ in range(n))
rel["common_passages"] = len(both)
rel["agree_exactly"] = sum(n for (a, b), n in conf.items() if a == b)
# quotes
qs_ = collections.defaultdict(lambda: [0, 0])
for (qid, model, order), obj in raw.items():
    for e in obj["marks"]:
        try:
            no = int(e["no"])
        except Exception:
            continue
        quote = ing.norm(e.get("evidence"))
        if (qid, no) not in passages:
            continue
        qs_[model][1] += 1
        qs_[model][0] += bool(quote and quote in ing.norm(passages[(qid, no)]["text"]))
rel["quotes_found_verbatim"] = {m: {"found": a, "of": b, "share": round(a / b, 3)} for m, (a, b) in qs_.items()}
rel["agreement_pairs"] = pair
# position bias: for the questions run in both orders by the same tool, passages marked in A and in B
shift = {}
for model in ("ChatGPT", "Gemini"):
    ra, rb = runs.get((model, "A"), {}), runs.get((model, "B"), {})
    com = sorted(set(ra) & set(rb))
    changed = [p for p in com if ra[p] != rb[p]]
    up_when_earlier = down_when_earlier = 0
    for p in changed:
        n_q = max(r["n"] for r in qinfo[p[0]]["rows"])
        # position in A = passage number n (A lists numbers ascending); in B the order is reversed
        posA, posB = p[1], n_q - p[1] + 1
        earlier_in = "A" if posA < posB else "B" if posB < posA else None
        if earlier_in is None:
            continue
        mkA, mkB = rank[ra[p]], rank[rb[p]]
        higher_in = "A" if mkA > mkB else "B"
        if higher_in == earlier_in:
            up_when_earlier += 1
        else:
            down_when_earlier += 1
    shift[model] = {"passages_in_both_orders": len(com), "marked_differently": len(changed), "higher_mark_in_the_order_where_it_was_earlier": up_when_earlier, "higher_mark_in_the_order_where_it_was_later": down_when_earlier}
rel["order_effect"] = shift
out["reliability"] = rel

# ------------------------------------------------------------------ 2. marks per passage under three treatments
votes = {p: [runs[k][p] for k in keys if p in runs[k]] for p in passages}
def agreed(p):
    c = collections.Counter(votes[p]).most_common()
    return None if not c or (len(c) > 1 and c[0][1] == c[1][1]) else c[0][0]
def lower(p):
    return ing._resolve(votes[p], min)
def higher(p):
    return ing._resolve(votes[p], max)
TREAT = {"agreed only": agreed, "ties to the lower mark": lower, "ties to the higher mark": higher}

def version_rows(q, v):
    """passages of version v on question q: top 5 (all for S), with their rank in that version."""
    items = []
    for r in q["rows"]:
        rk = r["variants"].get(v)
        if rk is not None and (v.startswith("S") or rk <= 5):
            items.append((rk, r["n"]))
    return sorted(items)

def shares(q, v, f):
    ms = [f((q["qid"], n)) for _, n in version_rows(q, v)]
    j = [m for m in ms if m is not None]
    if not j:
        return None
    n = len(j)
    return {"yes": sum(m == "Yes" for m in j) / n, "useful": sum(m in ("Yes", "Partly") for m in j) / n, "mis": sum(m == "Misleading" for m in j) / n, "n": n, "shown": len(ms)}

per_q = {t: {v: {q["qid"]: shares(q, v, f) for q in pool if shares(q, v, f)} for v in VERS} for t, f in TREAT.items()}
def macro(d, qids, key):
    vals = [d[q][key] for q in qids if q in d]
    return sum(vals) / len(vals) if vals else None
table = {}
for t in TREAT:
    table[t] = {}
    for v in VERS:
        d = per_q[t][v]
        table[t][v] = {"questions": len(d), "yes": macro(d, d, "yes"), "useful": macro(d, d, "useful"), "mis": macro(d, d, "mis")}
out["version_scores_all_their_questions"] = table

# self-check: the 'agreed only' scores computed here must equal the ones the ingestion tool prints (same rule, written twice)
for r in var_rows:
    v = r["variant"]
    if v in table["agreed only"]:
        mine = table["agreed only"][v]
        assert r["questions"] == mine["questions"] and abs(r["yes"] - mine["yes"]) < 1e-9 and abs(r["useful"] - mine["useful"]) < 1e-9 and abs(r["misleading"] - mine["mis"]) < 1e-9, (v, r, mine)
out["self_check"] = "the agreed-only scores equal those of ingest_llm_reviews.py for every version"

# like with like: every version against A on the SAME questions, with a bootstrap over questions
rnd = random.Random(20261009)
def boot(diffs, n=5000):
    if not diffs:
        return None
    ms = []
    for _ in range(n):
        s = [diffs[rnd.randrange(len(diffs))] for _ in diffs]
        ms.append(sum(s) / len(s))
    ms.sort()
    return [ms[int(0.025 * n)], ms[int(0.975 * n)]]
paired = {}
for t in TREAT:
    paired[t] = {}
    for v in VERS[1:]:
        common = [q for q in per_q[t][v] if q in per_q[t]["A today"]]
        row = {"questions": len(common)}
        for key in ("yes", "useful", "mis"):
            diffs = [per_q[t][v][q][key] - per_q[t]["A today"][q][key] for q in common]
            row[key] = {"version": sum(per_q[t][v][q][key] for q in common) / len(common), "A": sum(per_q[t]["A today"][q][key] for q in common) / len(common),
                        "diff": sum(diffs) / len(diffs), "ci95": boot(diffs), "better": sum(d > 1e-9 for d in diffs), "same": sum(abs(d) <= 1e-9 for d in diffs), "worse": sum(d < -1e-9 for d in diffs)}
        paired[t][v] = row
out["paired_against_A_same_questions"] = paired

# question-level success measures (conservative: a Yes must be the consensus under 'lower'; lenient: under 'higher')
def question_hits(v, f):
    res = {}
    for q in pool:
        its = version_rows(q, v)
        if not its:
            continue
        ms = [f((q["qid"], n)) for _, n in its]
        top3 = [f((q["qid"], n)) for rk, n in its[:3]]
        top1 = f((q["qid"], its[0][1]))
        res[q["qid"]] = {"has_yes": any(m == "Yes" for m in ms), "no_useful": not any(m in ("Yes", "Partly") for m in ms), "mis_in_top3": any(m == "Misleading" for m in top3), "top1_yes": top1 == "Yes", "top1_useful": top1 in ("Yes", "Partly")}
    return res
hits = {}
for t in ("ties to the lower mark", "ties to the higher mark"):
    hits[t] = {}
    for v in VERS:
        r = question_hits(v, TREAT[t])
        hits[t][v] = {"questions": len(r)} | {k: sum(x[k] for x in r.values()) for k in ("has_yes", "no_useful", "mis_in_top3", "top1_yes", "top1_useful")}
out["question_level_measures"] = hits

# by kind
def kind_of(q):
    return qinfo[q]["kind"]
bykind = {}
for t in ("ties to the lower mark",):
    for v in VERS:
        d = per_q[t][v]
        for kd in ("everyday", "narrative", "legal"):
            qids = [q for q in d if kind_of(q) == kd]
            if qids:
                bykind.setdefault(v, {})[kd] = {"questions": len(qids), "yes": macro(d, qids, "yes"), "useful": macro(d, qids, "useful"), "mis": macro(d, qids, "mis")}
out["by_kind_ties_lower"] = bykind

# ------------------------------------------------------------------ 3. per question for A
perq = {}
for q in pool:
    ms = [(rk, n, lower((q["qid"], n))) for rk, n in version_rows(q, "A today")]
    c = collections.Counter(m for _, _, m in ms)
    perq[q["qid"]] = {"kind": q["kind"], "domain": q["domain"], "Yes": c.get("Yes", 0), "Partly": c.get("Partly", 0), "No": c.get("No", 0), "Misleading": c.get("Misleading", 0),
                      "marks_in_rank_order": [m for _, _, m in ms], "key_reachable": KEY[q["qid"]]["reachable"]}
out["per_question_A_ties_lower"] = perq
# good_answer_present by tool
gap = collections.defaultdict(dict)
for (qid, model, order), obj in raw.items():
    gap[qid][f"{model}/{order}"] = obj.get("good_answer_present")
out["good_answer_present"] = gap
# questions where no version has a Yes in its top 5 (conservative)
nov = [qid for qid in qinfo if not any(hits_q.get(qid, {}).get("has_yes") for hits_q in [question_hits(v, lower) for v in VERS])]
out["questions_with_no_Yes_in_any_version"] = nov

# ------------------------------------------------------------------ 4. misleading catalogue
mis = []
for p, vs in votes.items():
    if "Misleading" in vs:
        qid, n = p
        row = next(r for r in qinfo[qid]["rows"] if r["n"] == n)
        reasons = []
        for (q2, model, order), obj in raw.items():
            if q2 != qid:
                continue
            for e in obj["marks"]:
                if str(e.get("no")) == str(n) and ing.norm_mark(e.get("mark")) == "Misleading":
                    reasons.append(f"{model}/{order}: {e.get('reason', '')[:260]}")
        mis.append({"qid": qid, "no": n, "title": (row.get("title") or "")[:80], "doc": row["doc"], "pn": row["pn"], "votes": dict(collections.Counter(vs)), "versions": row["variants"], "reasons": reasons[:3]})
out["misleading_passages"] = sorted(mis, key=lambda x: (x["qid"], x["no"]))

# ------------------------------------------------------------------ 5. currency: stale rulings in the top 5 and what reviewers made of them
stale_rows = []
for q in pool:
    stale = {s["doc"]: s for s in KEY[q["qid"]]["stale_docs"]}
    if not stale:
        continue
    for r in q["rows"]:
        docs = {r["doc"], *r["also"]}
        hit = [stale[d] for d in docs if d in stale]
        if hit:
            for v, rk in r["variants"].items():
                if v.startswith("S") or rk <= 5:
                    stale_rows.append({"qid": q["qid"], "no": r["n"], "version": v, "rank": rk, "ruling": hit[0]["label"], "kind": hit[0]["kind"], "counts_as_stale": hit[0]["counts_as_stale"], "mark_ties_lower": lower((q["qid"], r["n"])), "mark_agreed": agreed((q["qid"], r["n"]))})
out["stale_passages_in_top5"] = stale_rows
st = [x for x in stale_rows if x["version"] == "A today" and x["counts_as_stale"]]
out["stale_in_A_top5_summary"] = {"passages": len(st), "marked_useful_by_reviewers": sum(1 for x in st if x["mark_ties_lower"] in ("Yes", "Partly")), "marked_yes": sum(1 for x in st if x["mark_ties_lower"] == "Yes"), "marked_misleading": sum(1 for x in st if x["mark_ties_lower"] == "Misleading")}
# how often did a reviewer say 'overruled / no longer good law / later' in caveats
cav = collections.Counter(); cav_tot = 0
for (qid, model, order), obj in raw.items():
    c = (obj.get("caveats") or "").strip()
    cav_tot += 1
    if c:
        cav["non_empty"] += 1
        if re.search(r"overrul|no longer|later (?:court|ruling|decision|held)|superseded|doubted|not good law|recalled|modified", c, re.I):
            cav["mentions_a_later_change"] += 1
out["caveats"] = {"replies": cav_tot, **cav}

# ------------------------------------------------------------------ 6. the re-ranker and the marks: A's top 5 passages that came from beyond the merged top 5
fused_pos = {r["qid"]: r["final_top5_fused_positions"] for r in RERANK["rows"] if r["qid"] not in {x for x, _ in RERANK["reproduction_problems"]}}
promoted, kept = [], []
for q in pool:
    if q["qid"] not in fused_pos:
        continue
    its = version_rows(q, "A today")
    for (rk, n), fp in zip(its, fused_pos[q["qid"]]):
        m = lower((q["qid"], n))
        if m is None:
            continue
        (kept if (fp is not None and fp <= 5) else promoted).append(m)
def share(ms, ks):
    return round(sum(m in ks for m in ms) / len(ms), 3) if ms else None
out["reranker_promoted_vs_kept"] = {"promoted_from_beyond_merged_top5": {"n": len(promoted), "yes": share(promoted, ("Yes",)), "useful": share(promoted, ("Yes", "Partly")), "misleading": share(promoted, ("Misleading",))},
                                    "already_in_merged_top5": {"n": len(kept), "yes": share(kept, ("Yes",)), "useful": share(kept, ("Yes", "Partly")), "misleading": share(kept, ("Misleading",))}}
# usefulness by final rank in A (rank 1..5)
byrank = collections.defaultdict(list)
for q in pool:
    for rk, n in version_rows(q, "A today"):
        m = lower((q["qid"], n))
        if m is not None:
            byrank[rk].append(m)
out["A_by_rank"] = {str(rk): {"n": len(ms), "yes": share(ms, ("Yes",)), "useful": share(ms, ("Yes", "Partly")), "misleading": share(ms, ("Misleading",))} for rk, ms in sorted(byrank.items())}

# ------------------------------------------------------------------ 7. key authority hit vs marks (A)
AH = json.load(open(ROOT + "/review_results/2026-10-09_real30_pool_dev/authority_hits.json"))["scores"]["A today"]
grp = {"key authority in A's top 5": [], "key authority not in A's top 5 (answerable questions)": []}
for qid, s in AH.items():
    if KEY[qid]["reachable"] is not True or qid not in per_q["ties to the lower mark"]["A today"]:
        continue
    d = per_q["ties to the lower mark"]["A today"][qid]
    grp["key authority in A's top 5" if s["hits"]["5"] else "key authority not in A's top 5 (answerable questions)"].append((qid, round(d["yes"], 2), round(d["useful"], 2), round(d["mis"], 2)))
out["key_authority_vs_marks_A"] = {k: {"questions": [x[0] for x in v], "avg_yes": round(sum(x[1] for x in v) / len(v), 3) if v else None, "avg_useful": round(sum(x[2] for x in v) / len(v), 3) if v else None, "detail": v} for k, v in grp.items()}

json.dump(out, open(HERE + "/analysis.json", "w"), indent=1, ensure_ascii=False, default=str)
print("written", HERE + "/analysis.json")
