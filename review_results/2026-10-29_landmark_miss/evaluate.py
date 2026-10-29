"""Runs the landmark questions through the REAL search service code, with and without the authority step, and counts how often an expected landmark is among the first judgments returned.

    python3 evaluate.py --index-dir DIR --names names_table/names_table_d8811a9.json.gz --table authority_table/authority_d8811a9.json.gz --half dev --out evaluation_dev.json [--side DIR ...]

`--half dev|frozen|all`. The frozen half is meant to be run ONCE, with the settings fixed, after everything was tuned on the dev half (the file landmark_questions_v1.json was committed before any search was run).
Costs about 0.15 cent a question (one query embedding and one re-rank call; with the authority step the re-ranker sees up to 30 more passages). A hit is: at least one expected judgment among the first 8 distinct
judgments (the website feeds the model at most 8) / among the first 10. "The same judgment" means the same CASE: the index holds some cases under two or three document numbers (the table's `cluster` field lists them),
and a list that holds the case under another of its numbers is a hit (found 2026-10-29 on the dev half: question L028, expected record 41145, list held its duplicate 32923; the two numbers are one case, Hardeep Singh).
The first dev runs (evaluation_dev_service_code.json, evaluation_dev_old_index.json) counted by document number; the later files count by case. The frozen half is counted by case only.
Inside a loaded workbench (a process that already holds the service), call run(svc, questions, authority=None|AuthorityTable, params, same_case=function) directly.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)


def docs_of(svc, top, same=lambda d: d):
    """The first judgments of a ranked list of passages, each case once (a case held under two document numbers counts once; the number of its first appearance is kept)."""
    out, seen = [], set()
    for rid, _s in top:
        d = svc.metas[rid]["doc"]
        if same(d) not in seen:
            seen.add(same(d))
            out.append(d)
    return out


def run(svc, questions, authority=None, params=None, same_case=None):
    """[{'id', 'half', 'style', 'hit8', 'hit10', 'docs': first 10 distinct judgments, 'best_position', 'added'}] for the questions, with the service's authority step on (a loaded AuthorityTable) or off (None).
    `same_case`: document number -> number shared by the records of one case (AuthorityTable.cluster_of); without it every document number is a case of its own."""
    import authority_search as AS
    svc.authority = authority
    svc.auth_params = params or (AS.params_from_env() if authority is not None else None)
    same = same_case or (lambda d: d)
    out = []
    for q in questions:
        top, ann = svc.ranked_ex(q["text"], 10)
        docs = docs_of(svc, top, same)
        exp = {same(d) for d in q["expected"]}
        listed = [same(d) for d in docs]
        pos = [listed.index(e) + 1 for e in exp if e in listed]
        out.append({"id": q["id"], "group": q["group"], "half": q["half"], "style": q["style"], "hit8": bool(exp & set(listed[:8])), "hit10": bool(exp & set(listed[:10])), "docs": docs[:10], "best_position": min(pos) if pos else None,
                    "added": (ann or {}).get("added", 0)})
    return out


def summarise(rows):
    n = len(rows)
    f = lambda key, sel=lambda r: True: sum(1 for r in rows if sel(r) and r[key])
    by = lambda sel: [r for r in rows if sel(r)]
    return {"questions": n, "hit8": f("hit8"), "hit10": f("hit10"), "hit8_pct": round(100 * f("hit8") / n, 1) if n else None, "hit10_pct": round(100 * f("hit10") / n, 1) if n else None,
            "lay_hit8": f("hit8", lambda r: r["style"] == "lay"), "lay_n": len(by(lambda r: r["style"] == "lay")), "lawyer_hit8": f("hit8", lambda r: r["style"] == "lawyer"), "lawyer_n": len(by(lambda r: r["style"] == "lawyer"))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--names", required=True)
    ap.add_argument("--table", required=True)
    ap.add_argument("--side", action="append", default=[])
    ap.add_argument("--questions", default=os.path.join(HERE, "landmark_questions_v1.json"))
    ap.add_argument("--half", choices=("dev", "frozen", "all"), default="dev")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    os.environ["SCI_NAMES_TABLE"] = a.names
    import authority_search as AS
    import sci_search_service as ss
    svc = ss.SearchService.load(a.index_dir, a.side)
    qs = [q for q in json.load(open(a.questions, encoding="utf-8"))["questions"] if a.half == "all" or q["half"] == a.half]
    have = {m["doc"] for m in svc.metas}
    qs = [dict(q, expected=[d for d in q["expected"] if d in have]) for q in qs]
    qs = [q for q in qs if q["expected"]]                      # a question whose landmarks are not in THIS index cannot be answered by it
    tab = AS.AuthorityTable.load(a.table, svc.info.get("index_commit"))
    base = run(svc, qs, same_case=tab.cluster_of)
    new = run(svc, qs, tab, same_case=tab.cluster_of)
    import hashlib
    sha = lambda path: hashlib.sha256(open(path, "rb").read()).hexdigest()
    res = {"half": a.half, "settings": AS.params_from_env(), "baseline": summarise(base), "authority": summarise(new), "index_commit": svc.info.get("index_commit"), "judgments": svc.info.get("documents"),
           "counted_by": "case (records of one case, as the table's clusters list them, count once)",
           "sha256": {"authority_search.py": sha(os.path.join(ROOT, "authority_search.py")), "sci_search_service.py": sha(os.path.join(ROOT, "sci_search_service.py")), "authority_graph.py": sha(os.path.join(ROOT, "authority_graph.py")),
                      "table": sha(a.table), "questions": sha(a.questions), "evaluate.py": sha(os.path.join(HERE, "evaluate.py"))},
           "rows_baseline": base, "rows_authority": new}
    if a.half == "all":
        res["by_half"] = {h: {"baseline": summarise([r for r in base if r["half"] == h]), "authority": summarise([r for r in new if r["half"] == h])} for h in ("dev", "frozen")}
    print(json.dumps({k: res[k] for k in ("half", "settings", "baseline", "authority", "index_commit", "sha256", "by_half") if k in res}, indent=1))
    if a.out:
        json.dump(res, open(a.out, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
