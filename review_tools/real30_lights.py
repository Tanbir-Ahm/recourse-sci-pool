"""The two lights per domain for each search version, from reviewer marks (LLM-judged until a lawyer's sheet is added), the pool and the private key.

    python review_tools/real30_lights.py --pool POOL.json --replies REPLIES_DIR --out OUTDIR [--real review_data/ruler/real30_v1.json]

Thresholds are the draft of PLAN_30_REAL_QUESTIONS.md section 11, [Guessing], adjustable only before any mark is seen (they are fixed here before any reply exists):
  RELEVANCE light (search alone; a question whose key authority the index cannot reach and the controls are left out and reported apart). For each question, the share of the top 5 passages
  (everything an S version showed) marked Yes or Partly among those marked; for the domain, the average of those shares and the number of questions with a Misleading in the top 3.
    green: average share at least 0.80 and no question with a Misleading in its top 3;  red: average share under 0.60, or a Misleading in the top 3 on more than half the questions;  amber: otherwise.
  CURRENCY light (the domain's trap questions: those with an older ruling that counts as stale, i.e. overruled, modified, recalled or replaced by statute). A question 'lets a stale ruling through'
    when a passage of one of its older rulings is in the top 5 of the version.
    green: none does;  red: more than half do;  amber: otherwise;  'no trap' when the domain has none. A narrower or contested older ruling does not count.
The lights are computed under every way of settling disagreements between the reviewers' runs (agreed only, ties to the lower mark, ties to the higher mark, each run alone), because a version is preferred
only if it points the same way in all of them. Two or three questions per domain is a first reading, not proof; both lights are final only after the sealed run. PRIVATE.
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import ingest_llm_reviews as ing
import real_questions as RQ

GREEN_SHARE, RED_SHARE = 0.80, 0.60
DEFAULT_KEY = os.path.join(ROOT, "review_data", "ruler", "real30_key_v1.json")
DEFAULT_REAL = os.path.join(ROOT, "review_data", "ruler", "real30_v1.json")


def slots(q, version, k=5):
    """The rows a version put in its top k (all it showed, for S and M), best first."""
    got = sorted((r for r in q["rows"] if version in r["variants"]), key=lambda r: r["variants"][version])
    return got if version.split(" ")[0] in ("S", "M") else [r for r in got if r["variants"][version] <= k]


def question_relevance(q, version, mark_of):
    """(useful share, misleading in the top 3, passages marked) for one question and version; None when nothing of its was marked."""
    rows = slots(q, version)
    marks = [(r, mark_of(q["qid"], r["n"])) for r in rows]
    judged = [(r, m) for r, m in marks if m in ing.MARKS]
    if not judged:
        return None
    useful = sum(1 for _, m in judged if m in ("Yes", "Partly")) / len(judged)
    mis3 = any(m == "Misleading" and r["variants"][version] <= 3 for r, m in judged)
    return useful, mis3, len(judged)


def relevance_light(per_question):
    """per_question: list of (useful share, misleading in top 3, n) for the domain's scored questions."""
    if not per_question:
        return "no data", None, 0
    share = sum(x[0] for x in per_question) / len(per_question)
    mis = sum(1 for x in per_question if x[1])
    if share < RED_SHARE or mis > len(per_question) / 2:
        return "red", share, mis
    if share >= GREEN_SHARE and mis == 0:
        return "green", share, mis
    return "amber", share, mis


def currency_light(letting_through):
    """letting_through: list of booleans, one per trap question of the domain."""
    if not letting_through:
        return "no trap", 0, 0
    n = sum(letting_through)
    return ("green" if n == 0 else "red" if n > len(letting_through) / 2 else "amber"), n, len(letting_through)


def lights(pool, key, mark_of, versions=None):
    """{version: {domain: {relevance: (colour, share, misleading questions, questions), currency: (colour, let through, trap questions)}}} under one treatment of the marks."""
    kq = key["questions"]
    versions = versions or sorted({v for q in pool for r in q["rows"] for v in r["variants"]})
    out = {}
    for v in versions:
        by = collections.defaultdict(lambda: {"rel": [], "cur": []})
        for q in pool:
            k = kq[q["qid"]]
            if k["reachable"] is True and q["domain"] != "K":
                rel = question_relevance(q, v, mark_of)
                if rel:
                    by[q["domain"]]["rel"].append(rel)
            stale = {s["doc"] for s in k["stale_docs"] if s["counts_as_stale"]}
            if stale and q["domain"] != "K":
                top = q["lists"].get(v)
                if top is None:
                    continue
                top5 = top if v.split(" ")[0] in ("S", "M") else top[:5]
                by[q["domain"]]["cur"].append(any(({it["doc"], *it.get("also", [])} & stale) for it in top5))
        out[v] = {}
        for d, parts in sorted(by.items()):
            col, share, mis = relevance_light(parts["rel"])
            ccol, n, nt = currency_light(parts["cur"])
            out[v][d] = {"relevance": (col, share, mis, len(parts["rel"])), "currency": (ccol, n, nt)}
    return out


def treatments(runs, passages):
    """{name: mark_of(qid, n)}: the reviewers' runs settled four ways (the same ones as ingest_llm_reviews.sensitivity)."""
    keys = sorted(runs)
    votes = {p: [runs[k][p] for k in keys if p in runs[k]] for p in passages}

    def agreed(q, n):
        c = collections.Counter(votes[(q, n)]).most_common()
        return None if not c or (len(c) > 1 and c[0][1] == c[1][1]) else c[0][0]
    t = {"agreed only": agreed, "ties to the lower mark": lambda q, n: ing._resolve(votes[(q, n)], min), "ties to the higher mark": lambda q, n: ing._resolve(votes[(q, n)], max)}
    t.update({f"run {m}/{o}": (lambda q, n, k=(m, o): runs[k].get((q, n))) for m, o in keys})
    return t


def report(results, domains):
    names = {"green": "GREEN", "amber": "amber", "red": "RED", "no data": "no data", "no trap": "no trap"}
    L = ["# Readiness lights per domain (PRIVATE, LLM-judged until a lawyer's sheet is added)", "",
         "Two lights, from the draft thresholds fixed before any mark was seen (see the docstring of `real30_lights.py`). Questions whose key authority the index cannot reach and the controls are left out. "
         "Two or three questions per domain is a first reading, not proof; both lights are final only after the sealed run. A version is preferred only if it points the same way in every treatment.", ""]
    treatments_ = list(results)
    versions = sorted({v for t in results.values() for v in t})
    for v in versions:
        L += [f"## {v}", "", "| Domain | " + " | ".join(f"{t}: relevance / currency" for t in treatments_) + " |", "|---|" + "---|" * len(treatments_)]
        for d in sorted({d for t in results.values() for d in t.get(v, {})}):
            cells = []
            for t in treatments_:
                c = results[t].get(v, {}).get(d)
                if not c:
                    cells.append("-")
                    continue
                r, cu = c["relevance"], c["currency"]
                share = "" if r[1] is None else f" ({r[1]:.0%}, {r[2]} mis., n={r[3]})"
                cells.append(f"{names[r[0]]}{share} / {names[cu[0]]}" + (f" ({cu[1]} of {cu[2]})" if cu[2] else ""))
            L.append(f"| {d}: {domains.get(d, '')[:28]} | " + " | ".join(cells) + " |")
        L.append("")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pool", required=True)
    ap.add_argument("--replies", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--key", default=DEFAULT_KEY)
    ap.add_argument("--real", default=DEFAULT_REAL)
    a = ap.parse_args(argv)
    pool, passages = ing.load_pool(a.pool)
    runs, problems, _ = ing.load_replies(a.replies, passages, pool)
    with open(a.key, encoding="utf-8") as fh:
        key = json.load(fh)
    results = {name: lights(pool, key, fn) for name, fn in treatments(runs, passages).items()}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "lights.json"), "w", encoding="utf-8") as fh:
        json.dump({"results": results, "file_problems": problems}, fh, indent=1, default=list)
        fh.write("\n")
    with open(os.path.join(a.out, "LIGHTS.md"), "w", encoding="utf-8") as fh:
        fh.write(report(results, {d: v[0] for d, v in RQ.DOMAINS.items()}))
    print(f"wrote {a.out}; {len(runs)} runs; {len(problems)} file problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
