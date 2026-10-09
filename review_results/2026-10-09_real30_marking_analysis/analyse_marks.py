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
FUSED = json.load(open(ROOT + "/review_results/2026-10-09_real30_pool_dev/rerank_effect/fused_lists.json"))        # the 60 merged candidates per question, in the order they have before the re-ranker (save_fused_lists.py)

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
            loo = [sum(diffs[:i] + diffs[i + 1:]) / (len(diffs) - 1) for i in range(len(diffs))] if len(diffs) > 1 else []
            row[key] = {"version": sum(per_q[t][v][q][key] for q in common) / len(common), "A": sum(per_q[t]["A today"][q][key] for q in common) / len(common),
                        "diff": sum(diffs) / len(diffs), "ci95": boot(diffs), "better": sum(d > 1e-9 for d in diffs), "same": sum(abs(d) <= 1e-9 for d in diffs), "worse": sum(d < -1e-9 for d in diffs),
                        "leave_one_question_out": [min(loo), max(loo)] if loo else None,
                        "without_R14": (sum(d for q, d in zip(common, diffs) if q != "R14") / (len(common) - 1)) if "R14" in common and len(common) > 1 else None}
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
fused_pos = {qid: v["A_top10_fused_positions"][:5] for qid, v in FUSED["questions"].items() if qid not in {x for x, _ in FUSED["reproduction_problems"]}}
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

# ------------------------------------------------------------------ 8. why passages were called Misleading (my reading of the reasons: misleading_classification.json; R = replaced by a later ruling or statute, S = records a submission, O = other)
CLS = json.load(open(HERE + "/misleading_classification.json"))["passages"]
assert set(CLS) == {f"{m['qid']}#{m['no']}" for m in mis}, "the set of Misleading passages changed: classify the new ones in misleading_classification.json first"
for m in out["misleading_passages"]:
    m["class"] = CLS[f"{m['qid']}#{m['no']}"]["class"]
def most_runs_said_misleading(m):
    return m["votes"].get("Misleading", 0) * 2 > sum(m["votes"].values())
out["misleading_why"] = {"passages": len(mis), "by_class": dict(collections.Counter(m["class"] for m in out["misleading_passages"])),
                         "most_runs_said_misleading": sum(most_runs_said_misleading(m) for m in out["misleading_passages"]),
                         "most_runs_said_misleading_by_class": dict(collections.Counter(m["class"] for m in out["misleading_passages"] if most_runs_said_misleading(m)))}
# questions where A's top 5 carries replaced law: a passage of a listed stale ruling, or a passage classed R that some reviewer called Misleading
a_top5 = {(q["qid"], n) for q in pool for _, n in version_rows(q, "A today")}
repl_q = collections.defaultdict(list)
for m in out["misleading_passages"]:
    if m["class"] == "R" and (m["qid"], m["no"]) in a_top5:
        repl_q[m["qid"]].append(f"passage {m['no']} called Misleading")
for x in stale_rows:
    if x["version"] == "A today" and x["counts_as_stale"]:
        repl_q[x["qid"]].append(f"passage {x['no']} of the listed ruling {x['ruling']}")
out["A_top5_with_replaced_law"] = {"questions": sorted(repl_q), "of": len(pool), "detail": {k: sorted(set(v)) for k, v in sorted(repl_q.items())}}

# ------------------------------------------------------------------ 9. accuracy rating of version A (the search with the re-ranker): each tool alone and the consensus, with intervals
def boot_mean(vals, n=5000):
    r = random.Random(20261010)                  # a fresh generator per call: the same values always give the same interval, whatever was computed before
    ms = sorted(sum(vals[r.randrange(len(vals))] for _ in vals) / len(vals) for _ in range(n))
    return [round(ms[int(0.025 * n)], 3), round(ms[int(0.975 * n)], 3)]
def sd(vals):
    m = sum(vals) / len(vals)
    return (sum((x - m) ** 2 for x in vals) / (len(vals) - 1)) ** 0.5
def wilson(k, n, z=1.96):
    """95% Wilson interval for k questions out of n (a share of questions, so the sample is the 19 questions themselves)."""
    p_ = k / n
    centre = (p_ + z * z / (2 * n)) / (1 + z * z / n)
    half = z * ((p_ * (1 - p_) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)]
SOURCES = {"ChatGPT alone (order A run)": lambda p: runs[("ChatGPT", "A")].get(p),
           "Gemini alone (order A run)": lambda p: runs[("Gemini", "A")].get(p),
           "both tools, agreed only": agreed,
           "both tools, ties to the lower mark": lower,
           "both tools, ties to the higher mark": higher}
def per_question(f, k=5):
    per = {}
    for q in pool:
        ms = [f((q["qid"], n)) for _, n in version_rows(q, "A today")[:k]]
        j = [m for m in ms if m is not None]
        if j:
            d = {m: sum(x == m for x in j) / len(j) for m in ("Yes", "Partly", "No", "Misleading")}
            d["useful"] = d["Yes"] + d["Partly"]
            per[q["qid"]] = d
    return per
acc = {}
for name, f in SOURCES.items():
    per = per_question(f)
    row = {"questions": len(per)}
    for key in ("Yes", "Partly", "No", "Misleading", "useful"):
        row[key] = round(sum(per[q][key] for q in per) / len(per), 3)
    for key in ("Yes", "useful", "Misleading"):
        vals = [per[q][key] for q in per]
        mean = sum(vals) / len(vals)
        half = 1.96 * sd(vals) * (1 / len(vals) + 1 / 11) ** 0.5          # a fresh set of 11 questions (the sealed half) could average this far from the mean
        row[key + "_ci95_over_questions"] = boot_mean(vals)
        row[key + "_sd_between_questions"] = round(sd(vals), 3)
        row[key + "_range_for_11_new_questions"] = [round(max(0.0, mean - half), 3), round(min(1.0, mean + half), 3)]
    row["by_top_k"] = {str(k): {key: round(sum(d[key] for d in per_question(f, k).values()) / len(per_question(f, k)), 3) for key in ("Yes", "useful", "Misleading")} for k in (1, 3, 5)}
    row["by_kind"] = {kd: {"questions": len([q for q in per if kind_of(q) == kd]), **{key: round(sum(per[q][key] for q in per if kind_of(q) == kd) / len([q for q in per if kind_of(q) == kd]), 3) for key in ("Yes", "useful", "Misleading")}} for kd in ("everyday", "narrative", "legal")}
    if name != "both tools, agreed only":                                  # question-level measures need every passage to carry a mark
        lvl = collections.Counter()
        for qid, ms in {q["qid"]: [f((q["qid"], n)) for _, n in version_rows(q, "A today")] for q in pool}.items():
            lvl["questions"] += 1
            lvl["first_result_yes"] += ms[0] == "Yes"
            lvl["first_result_useful"] += ms[0] in ("Yes", "Partly")
            lvl["at_least_one_yes"] += "Yes" in ms
            lvl["no_useful_passage"] += not any(m in ("Yes", "Partly") for m in ms)
            lvl["misleading_in_top3"] += "Misleading" in ms[:3]
            lvl["misleading_in_top5"] += "Misleading" in ms
            lvl["replaced_law_in_top5"] += qid in repl_q
            lvl["clean_question"] += ("Yes" in ms) and ("Misleading" not in ms[:3]) and (qid not in repl_q)
        row["question_level"] = dict(lvl)
        row["question_level_wilson95"] = {k: wilson(v, lvl["questions"]) for k, v in lvl.items() if k != "questions"}
    acc[name] = row
out["accuracy_rating_A"] = acc
# how many individual passages in A's top 5 are replaced law (a listed stale ruling, or a passage classed R that some reviewer called Misleading)
stale_in_A = {(x["qid"], x["no"]) for x in stale_rows if x["version"] == "A today" and x["counts_as_stale"]}
r_in_A = {(m["qid"], m["no"]) for m in out["misleading_passages"] if m["class"] == "R"} & a_top5
out["A_top5_with_replaced_law"]["passages"] = {"listed_stale": len(stale_in_A), "called_misleading_and_classed_replaced": len(r_in_A), "either": len(stale_in_A | r_in_A), "of_slots": len(a_top5),
                                                "listed_stale_that_no_reviewer_called_misleading": sorted(f"{q}#{n}" for q, n in stale_in_A - r_in_A)}
# question by question: the marks of A's top 5 in rank order under the cautious and the generous settlement, and whether the question is 'clean'
bq = {}
for q in pool:
    its = version_rows(q, "A today")
    lo = [lower((q["qid"], n)) for _, n in its]
    hi = [higher((q["qid"], n)) for _, n in its]
    cg = [runs[("ChatGPT", "A")].get((q["qid"], n)) for _, n in its]
    gm = [runs[("Gemini", "A")].get((q["qid"], n)) for _, n in its]
    rep = q["qid"] in repl_q
    bq[q["qid"]] = {"kind": q["kind"], "domain": q["domain"], "key_reachable": KEY[q["qid"]]["reachable"], "replaced_law_in_top5": rep, "cautious": lo, "generous": hi, "ChatGPT": cg, "Gemini": gm,
                    "clean_cautious": ("Yes" in lo) and ("Misleading" not in lo[:3]) and not rep, "clean_generous": ("Yes" in hi) and ("Misleading" not in hi[:3]) and not rep}
out["accuracy_rating_A_by_question"] = bq
# the same shares on the subsets: the 16 questions without the three index gaps (R06, R15, R21), and the 14 answerable ones (also without the two controls R28, R29)
GAPS, CONTROLS = {"R06", "R15", "R21"}, {"R28", "R29"}
subsets = {"all 19": set(qinfo), "16 without the three index gaps": set(qinfo) - GAPS, "14 answerable (also without the two controls)": set(qinfo) - GAPS - CONTROLS}
sub = {}
for sname, qs in subsets.items():
    sub[sname] = {}
    for name, f in SOURCES.items():
        per = {q: d for q, d in per_question(f).items() if q in qs}
        row = {"questions": len(per)}
        for key in ("Yes", "useful", "Misleading"):
            vals = [per[q][key] for q in per]
            row[key] = round(sum(vals) / len(vals), 3)
            row[key + "_ci95_over_questions"] = boot_mean(vals)
        if name != "both tools, agreed only":
            lvl = collections.Counter()
            for qid in qs:
                d = bq[qid]
                ms = d["cautious"] if "lower" in name else d["generous"] if "higher" in name else d["ChatGPT"] if "ChatGPT" in name else d["Gemini"]
                lvl["questions"] += 1
                lvl["first_result_yes"] += ms[0] == "Yes"
                lvl["at_least_one_yes"] += "Yes" in ms
                lvl["clean_question"] += ("Yes" in ms) and ("Misleading" not in ms[:3]) and not d["replaced_law_in_top5"]
            row["question_level"] = dict(lvl)
        sub[sname][name] = row
out["accuracy_rating_A_subsets"] = sub

def round_floats(x, nd=9):
    """Floats to 9 decimals, so the file is byte-identical from run to run (the last digit of a kappa otherwise depends on the order a set of labels is visited in)."""
    if isinstance(x, float):
        return round(x, nd)
    if isinstance(x, dict):
        return {k: round_floats(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [round_floats(v, nd) for v in x]
    return x
json.dump(round_floats(out), open(HERE + "/analysis.json", "w"), indent=1, ensure_ascii=False, default=str)
print("written", HERE + "/analysis.json")
