"""Does the authority step change ordinary questions for the worse?  (control for evaluate.py)

70 questions that were NOT written for the landmark test (they come from the question files of earlier work: the register exam, the ruler, the Act-shelf and JJ/dowry evaluations; the same pool as
review_results/2026-10-29_landmark_circumstantial/independent_pool.json) are put to the service with the authority step off and on.  For every question, the first 8 judgments of each list are scored with ONE common ruler:
the re-ranker's own score of the judgment's best passage among the passages of both lists (one extra re-rank call a question; the score of a passage does not depend on what it is ranked with).

    python3 control_unrelated.py --index-dir DIR --names ... --table ... [--side DIR ...] --out control_unrelated_<index>.json
Inside a loaded workbench: control_unrelated.run(svc, table, questions).

What it reports: the mean of that score over the first 8 judgments (off / on) and over the same number of judgments from each list (the step also puts more DIFFERENT judgments in the list, and a longer list of
different judgments has a lower average by itself); the score of the judgments the step brings in against the score of those it pushes out; how many of the 8 judgments the two lists share, how many questions get exactly
the same 8, and the extra passages the re-ranker had to read (its cost).  It does not say which list is better; it says whether the step moves ordinary questions and whether the passages it brings in are about as
relevant as the ones they replace.
"""
import argparse
import json
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)


def sample_questions(n=70, seed=7):
    pool = json.load(open(os.path.join(ROOT, "review_results", "2026-10-29_landmark_circumstantial", "independent_pool.json"), encoding="utf-8"))
    qs = []
    for f, v in pool.items():
        if f.startswith(("eval_questions", "register_exam", "review_data")):
            qs += [x for x in v if isinstance(x, str)]
    random.Random(seed).shuffle(qs)
    return qs[:n]


def lists(svc, q, table, params, same):
    import evaluate as EV
    svc.authority = table
    svc.auth_params = params if table is not None else None
    top, ann = EV.ranked(svc, q)
    docs = EV.docs_of(svc, top, same)[:8]
    rows = {}
    for rid, _s in top:
        rows.setdefault(svc.metas[rid]["doc"], []).append(rid)
    return docs, rows, (ann or {}).get("added", 0)


def run(svc, table, questions, params=None):
    import authority_search as AS
    params = params or AS.params_from_env()
    same = table.cluster_of
    out = []
    for q in questions:
        a_docs, a_rows, _ = lists(svc, q, None, params, same)
        b_docs, b_rows, added = lists(svc, q, table, params, same)
        need = sorted({r for rows in (a_rows, b_rows) for rs in rows.values() for r in rs})
        score = svc._rerank(q, need)                                        # one ruler for both lists
        best = lambda docs, rows: [max(score[r] for r in rows[d]) for d in docs if d in rows]
        sa, sb = best(a_docs, a_rows), best(b_docs, b_rows)
        m = min(len(a_docs), len(b_docs))                                     # the same number of judgments from each list (the step also puts more different judgments in the list, which alone lowers an average)
        sa_c, sb_c = best(a_docs[:m], a_rows), best(b_docs[:m], b_rows)
        ca, cb = {same(d) for d in a_docs}, {same(d) for d in b_docs}
        new_scores = [max(score[r] for r in b_rows[d]) for d in b_docs if same(d) not in ca]            # judgments only the step's list has
        gone_scores = [max(score[r] for r in a_rows[d]) for d in a_docs if same(d) not in cb]           # judgments only the plain list had
        out.append({"q": q, "off": a_docs, "on": b_docs, "score_off": statistics.mean(sa) if sa else 0.0, "score_on": statistics.mean(sb) if sb else 0.0,
                    "score_off_common": statistics.mean(sa_c) if sa_c else 0.0, "score_on_common": statistics.mean(sb_c) if sb_c else 0.0, "common_n": m,
                    "new_scores": new_scores, "gone_scores": gone_scores, "shared": len(ca & cb), "added": added})
    return out


def summarise(rows):
    new = [x for r in rows for x in r["new_scores"]]
    gone = [x for r in rows for x in r["gone_scores"]]
    return {"questions": len(rows), "mean_score_off": round(statistics.mean(r["score_off"] for r in rows), 3), "mean_score_on": round(statistics.mean(r["score_on"] for r in rows), 3),
            "mean_score_off_same_number_of_judgments": round(statistics.mean(r["score_off_common"] for r in rows), 3), "mean_score_on_same_number_of_judgments": round(statistics.mean(r["score_on_common"] for r in rows), 3),
            "judgments_brought_in": len(new), "mean_score_of_judgments_brought_in": round(statistics.mean(new), 3) if new else None,
            "judgments_pushed_out": len(gone), "mean_score_of_judgments_pushed_out": round(statistics.mean(gone), 3) if gone else None,
            "mean_shared_of_8": round(statistics.mean(r["shared"] for r in rows), 2), "same_eight": sum(1 for r in rows if r["shared"] == 8), "mean_passages_added": round(statistics.mean(r["added"] for r in rows), 1),
            "questions_score_fell_by_0.05_or_more_same_number": sum(1 for r in rows if r["score_on_common"] - r["score_off_common"] <= -0.05),
            "questions_score_rose_by_0.05_or_more_same_number": sum(1 for r in rows if r["score_on_common"] - r["score_off_common"] >= 0.05)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--names", required=True)
    ap.add_argument("--table", required=True)
    ap.add_argument("--side", action="append", default=[])
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    os.environ["SCI_NAMES_TABLE"] = a.names
    import authority_search as AS
    import sci_search_service as ss
    svc = ss.SearchService.load(a.index_dir, a.side)
    tab = AS.AuthorityTable.load(a.table, svc.info.get("index_commit"))
    rows = run(svc, tab, sample_questions())
    res = {"summary": summarise(rows), "settings": AS.params_from_env(), "index_commit": svc.info.get("index_commit"), "rows": rows}
    print(json.dumps(res["summary"], indent=1))
    if a.out:
        json.dump(res, open(a.out, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
