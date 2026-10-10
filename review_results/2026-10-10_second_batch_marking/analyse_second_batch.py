"""Deeper look at J and S's second-batch replies (EXPLORATORY unless it repeats a pre-registered number; no network, no spend, no key except the tuning half's key-authority labels).

    python3 -P analyse_second_batch.py --pool .../pool_with_rerank_arms.json --replies DIR_BOTH_BATCHES --out analysis.json

Reads the extended pool (pack v2) and all normalised replies (first batch A and B, second batch TA). Writes analysis.json and prints what it finds:
  A. the second batch alone: mark mix, agreement between the two tools, quotes not found;
  B. the challenger (rerank-3-lite) against today's re-ranker: which batch each entering and leaving passage was marked in, a batch-matched comparison, a bootstrap over questions, every passage with its marks;
  C. the key authority's passages: what the reviewers said about them (tuning half only);
  D. partial look at rerank-3 and rerank-2.5 (only the passages that were marked);
  E. the safety net and the re-ranker's own effect, question by question.
"""
import argparse
import collections
import json
import os
import random
import sys

ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT + "/review_tools")
import ingest_llm_reviews as ing      # noqa: E402
import score_rerank_arms as S         # noqa: E402
import score_challenger_arm as C      # noqa: E402

GRADE = {"Misleading": 0, "No": 1, "Partly": 2, "Yes": 3}
TOOLS = ("ChatGPT", "Gemini")
HERE = os.path.dirname(os.path.abspath(__file__))


def reply_details(folder):
    """{(tool, order, qid, no): {mark, reason, confidence}} read from the saved replies."""
    out = {}
    for fn in sorted(os.listdir(folder)):
        m = ing.NAME_RE.match(fn)
        if not m:
            continue
        qid, order = f"{m.group(1).upper()}{int(m.group(2)):02d}", m.group(3).upper()
        tool = "ChatGPT" if "chatgpt" in m.group(4).lower() else "Gemini"
        obj, note = ing.parse_reply(open(os.path.join(folder, fn), encoding="utf-8", errors="replace").read())
        if obj is None:
            continue
        for e in obj["marks"]:
            try:
                no = int(e.get("no"))
            except (TypeError, ValueError):
                continue
            mk = ing.norm_mark(e.get("mark"))
            if mk:
                out[(tool, order, qid, no)] = {"mark": mk, "reason": (e.get("reason") or "").strip(), "confidence": e.get("confidence"), "evidence": e.get("evidence")}
    return out


def resolve(votes, pick):
    return ing._resolve(votes, pick) if votes else None


def kappa(pairs):
    """Cohen's kappa for two raters over the four marks."""
    n = len(pairs)
    if not n:
        return None
    labels = list(GRADE)
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else None


def boot_diff(per_question, n=5000, seed=7):
    """per_question: {qid: (sum of grade differences, passages)} -> bootstrap CI of the pooled mean grade difference, resampling questions."""
    qs = list(per_question)
    r = random.Random(seed)
    means = []
    for _ in range(n):
        tot = cnt = 0
        for _ in qs:
            s, c = per_question[qs[r.randrange(len(qs))]]
            tot += s
            cnt += c
        means.append(tot / cnt if cnt else 0)
    means.sort()
    return [round(means[int(0.025 * n)], 3), round(means[int(0.975 * n)], 3)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--replies", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pool_list, passages = ing.load_pool(a.pool)
    runs, problems, ev = ing.load_replies(a.replies, passages, pool_list)
    det = reply_details(a.replies)
    qmap = {q["qid"]: q for q in pool_list}
    res = {}

    # ---------------------------------------------------------------- A. the second batch alone
    ta = {t: runs[(t, "TA")] for t in TOOLS}
    keys = sorted(set(ta["ChatGPT"]) & set(ta["Gemini"]))
    pairs = [(ta["ChatGPT"][k], ta["Gemini"][k]) for k in keys]
    useful = lambda m: m in ("Yes", "Partly")
    res["A_second_batch"] = {
        "passages_marked_by_both": len(keys),
        "mark_mix": {t: dict(collections.Counter(ta[t].values())) for t in TOOLS},
        "same_mark": round(sum(a_ == b_ for a_, b_ in pairs) / len(pairs), 3),
        "same_useful_or_not": round(sum(useful(a_) == useful(b_) for a_, b_ in pairs) / len(pairs), 3),
        "kappa": round(kappa(pairs), 3),
        "chatgpt_more_generous_on": sum(GRADE[a_] > GRADE[b_] for a_, b_ in pairs), "gemini_more_generous_on": sum(GRADE[b_] > GRADE[a_] for a_, b_ in pairs),
        "quotes_not_found_in_second_batch_files": sum(1 for fn, msg in problems if "_TA_" in fn and "quote" in msg), "second_batch_marks": sum(len(v) for v in ta.values())}
    first = [(runs[("ChatGPT", o)][k], runs[("Gemini", o)][k]) for o in ("A",) for k in runs[("ChatGPT", o)] if k in runs[("Gemini", o)]]
    res["A_first_batch_order_A_for_comparison"] = {"passages": len(first), "same_mark": round(sum(x == y for x, y in first) / len(first), 3), "kappa": round(kappa(first), 3)}

    # ---------------------------------------------------------------- B. the challenger against today's re-ranker
    base_arm = C.B_ARM
    groups = {q["qid"]: C.groups_of(q, base_arm) for q in pool_list}
    runkeys = lambda p: [k for k, d in runs.items() if p in d]
    comp = {"entering": collections.Counter(), "leaving": collections.Counter()}
    for qid, g in groups.items():
        for side, name in (("entering", "entering (R only)"), ("leaving", "leaving (baseline only)")):
            for n in g[name]:
                b1 = any(o in ("A", "B") for (_t, o) in runkeys((qid, n)))
                b2 = any(o == "TA" for (_t, o) in runkeys((qid, n)))
                comp[side]["first batch only" if b1 and not b2 else "second batch only" if b2 and not b1 else "both batches" if b1 and b2 else "none"] += 1
    res["B_where_the_marks_come_from"] = {k: dict(v) for k, v in comp.items()}

    def settle(subset_orders, pick):
        def f(p):
            votes = [runs[k][p] for k in runs if k[1] in subset_orders and p in runs[k]]
            return resolve(votes, pick)
        return f
    matched = {}
    for label, orders in (("first-batch marks only (A, B)", ("A", "B")), ("second-batch marks only (TA)", ("TA",)), ("all marks", ("A", "B", "TA"))):
        for pname, pick in (("ties to the lower mark", min), ("ties to the higher mark", max)):
            f = settle(orders, pick)
            row = {}
            for side, name in (("entering", "entering (R only)"), ("leaving", "leaving (baseline only)")):
                marks = [f((qid, n)) for qid, g in groups.items() for n in g[name]]
                j = [m for m in marks if m]
                row[side] = {"marked": len(j), "yes": sum(m == "Yes" for m in j), "useful": sum(useful(m) for m in j), "misleading": sum(m == "Misleading" for m in j), "mean_grade": round(sum(GRADE[m] for m in j) / len(j), 2) if j else None}
            matched[f"{label} / {pname}"] = row
    res["B_batch_matched"] = matched

    # grade difference with a bootstrap over questions (all marks, ties lower and higher)
    boots = {}
    for pname, pick in (("ties to the lower mark", min), ("ties to the higher mark", max)):
        f = settle(("A", "B", "TA"), pick)
        per_q = {}
        for qid, g in groups.items():
            ent = [GRADE[f((qid, n))] for n in g["entering (R only)"] if f((qid, n))]
            lea = [GRADE[f((qid, n))] for n in g["leaving (baseline only)"] if f((qid, n))]
            if ent and lea:
                per_q[qid] = (sum(ent) / len(ent) * len(ent) - sum(lea) / len(lea) * len(ent), len(ent))     # pairs the entering count with the leaving mean so questions with 1 or 3 passages weigh by passages
        tot = sum(s for s, c in per_q.values()) / sum(c for s, c in per_q.values())
        boots[pname] = {"mean_grade_entering_minus_leaving": round(tot, 3), "ci95_over_questions": boot_diff(per_q), "questions": len(per_q)}
    res["B_grade_difference"] = boots

    # every passage that enters or leaves, with both tools' marks (all runs) and the reasons for any Misleading
    table = []
    for qid, g in groups.items():
        for side, name in (("ENTERING", "entering (R only)"), ("LEAVING", "leaving (baseline only)")):
            for n in g[name]:
                p = passages[(qid, n)]
                marks = {f"{t}/{o}": det[(t, o, qid, n)]["mark"] for (t, o) in [(t, o) for t in TOOLS for o in ("A", "B", "TA")] if (t, o, qid, n) in det}
                mis = [f"{t}/{o}: {det[(t, o, qid, n)]['reason'][:230]}" for (t, o) in [(t, o) for t in TOOLS for o in ("A", "B", "TA")] if (t, o, qid, n) in det and det[(t, o, qid, n)]["mark"] == "Misleading"]
                table.append({"qid": qid, "side": side, "n": n, "title": p["title"], "para": p["pn"], "page": p["page"], "doc": p["doc"], "marks": marks, "misleading_reasons": mis})
    res["B_every_passage"] = table

    # ---------------------------------------------------------------- C. the key authority's passages
    real = json.load(open(ROOT + "/review_data/ruler/real30_v1.json"))
    dev = [q["id"] for q in real["questions"] if q["half"] == "dev"]
    key_all = json.load(open(ROOT + "/review_data/ruler/real30_key_v1.json"))["questions"]
    key = {q: key_all[q] for q in dev}
    del key_all
    f_lo, f_hi = settle(("A", "B", "TA"), min), settle(("A", "B", "TA"), max)
    keyrows = {}
    for qid in dev:
        kd = {int(d) for d in key[qid].get("key_docs", [])}
        rows = [r for r in qmap[qid]["rows"] if r["doc"] in kd and not r.get("anchor_of")]
        if rows:
            keyrows[qid] = [{"n": r["n"], "para": r["pn"], "variants": {k: v for k, v in r["variants"].items() if k in (C.B_ARM, C.R_ARM, "A today")}, "mark_lower": f_lo((qid, r["n"])), "mark_higher": f_hi((qid, r["n"]))} for r in rows]
    res["C_key_authority_passages"] = keyrows

    # ---------------------------------------------------------------- D. rerank-3 and rerank-2.5 (partial: only the passages that were marked)
    raw = json.load(open(ROOT + "/review_results/2026-10-10_reranker_test/results/raw_scores.json"))
    ch = json.load(open(ROOT + "/review_results/2026-10-10_reranker_test/results/challenger_rerank3lite_top5.json"))
    sys.path.insert(0, ROOT + "/review_results/2026-10-10_reranker_test")
    import reranker_test as T
    metas, qtext, qids, key_docs, cands, saved = T.load_world()
    h2n = {qid: {r["h"]: r["n"] for r in q["rows"] if not r.get("anchor_of")} for qid, q in qmap.items()}
    partial = {}
    for arm, label in (("N1", "rerank-3"), ("X", "rerank-2.5"), ("N2", "rerank-3-lite")):
        ent_all = {"yes": 0, "useful": 0, "mis": 0, "marked": 0, "unmarked": 0}
        lea_all = dict(ent_all)
        for qid in qids:
            nums = T.si.section_numbers(qtext[qid])
            sc = {int(r): s for r, s in raw[f"{arm}|{qid}"].items()}
            top = [metas[r]["h"] for r in T.ordering(metas, cands[qid], sc, nums)[:5]]
            base = [x["h"] for x in ch["baseline_top5"][qid]]
            for side, hs in ((ent_all, [h for h in top if h not in base]), (lea_all, [h for h in base if h not in top])):
                for h in hs:
                    n = h2n[qid].get(h)
                    mk = f_lo((qid, n)) if n else None
                    if mk is None:
                        side["unmarked"] += 1
                        continue
                    side["marked"] += 1
                    side["yes"] += mk == "Yes"
                    side["useful"] += useful(mk)
                    side["mis"] += mk == "Misleading"
        partial[label] = {"entering": ent_all, "leaving": lea_all}
    res["D_other_rerankers_partial_lower_ties"] = partial

    # ---------------------------------------------------------------- E. safety net and the re-ranker's own effect
    net = [(q["qid"], r["n"]) for q in pool_list for r in q["rows"] if C.S.M_ARM in r["variants"] and not r.get("anchor_of")]
    res["E_safety_net"] = {"passages": len(net), "marks_lower_ties": dict(collections.Counter(f_lo(p) for p in net)), "marks_higher_ties": dict(collections.Counter(f_hi(p) for p in net)),
                           "yes_by_both_tools_agreeing": sum(1 for p in net if all(runs[(t, o)].get(p) == "Yes" for (t, o) in [(t, o) for t in TOOLS for o in ("A", "B", "TA") if p in runs.get((t, o), {})]) and any(p in runs.get((t, o), {}) for (t, o) in [(t, o) for t in TOOLS for o in ("A", "B", "TA")]))}
    perq = {}
    for q in pool_list:
        g = S.lists_of(q)
        for pname, f in (("lower", f_lo), ("higher", f_hi)):
            sa = S.shares([f((q["qid"], n)) for n in g["A top 5"]])
            sn = S.shares([f((q["qid"], n)) for n in g["N top 5"]])
            if sa and sn:
                perq.setdefault(q["qid"], {})[pname] = {"A_yes": round(sa["yes"], 2), "N_yes": round(sn["yes"], 2), "A_useful": round(sa["useful"], 2), "N_useful": round(sn["useful"], 2), "A_mis": round(sa["mis"], 2), "N_mis": round(sn["mis"], 2)}
    res["E_reranker_effect_per_question"] = perq

    json.dump(res, open(a.out, "w"), indent=1)
    return res


if __name__ == "__main__":
    r = main()
    for k in ("A_second_batch", "A_first_batch_order_A_for_comparison", "B_where_the_marks_come_from", "B_grade_difference", "D_other_rerankers_partial_lower_ties", "E_safety_net"):
        print(k, json.dumps(r[k]))
    print("B_batch_matched:")
    for k, v in r["B_batch_matched"].items():
        print("  ", k, json.dumps(v))
