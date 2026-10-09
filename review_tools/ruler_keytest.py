"""The automatic key test on a pool of the ruler's questions: is the ruler's key paragraph, or at least the expected judgment, among a version's top results? No reviewer mark is needed.

    python review_tools/ruler_keytest.py --pool review_results/DATE_ruler_pool_dev/pool.json --out review_results/DATE_ruler_pool_dev

A key paragraph is one of Recourse's hand-verified excerpts (or, for the first six topics, this project's own pick) that `ruler.py` matched to index passages by 8-word shingle containment. Two tests per
version and question, each as the rank (counting passages, best first) of the first hit and whether it is in the top 1, 3, 5 and 10: (1) the KEY PARAGRAPH test, the exact verified passage (strict: another passage of
the same judgment does not count); (2) the EXPECTED JUDGMENT test, any passage of a judgment the ruler lists as the expected or an acceptable one (this is the landmark test of the first pack, counted by passages
here). Versions starting with S show only a few passages and are scored on everything they showed. A hit says the verified paragraph or judgment was found, not that the other passages are good; both are weak
measures on their own, biased towards famous settled topics (Recourse's picks). Source label: key match, no reviewer mark. PRIVATE.
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import ruler as RU

KS = (1, 3, 5, 10)


def key_hashes(ruler):
    """{question id: set of passage hashes that hold a key paragraph of its topic}."""
    topics = {t["id"]: t for t in ruler["topics"]}
    out = {}
    for q in ruler["questions"]:
        t = topics[q["topic"]]
        out[q["id"]] = {m["h"] for k in t["key_passages"] if k.get("resolved") for m in k["matches"]}
    return out


def expected_docs(ruler):
    """{question id: set of index judgments the ruler lists as expected or acceptable for its topic}."""
    topics = {t["id"]: t for t in ruler["topics"]}
    return {q["id"]: {e["doc"] for e in topics[q["topic"]].get("expected", []) + topics[q["topic"]].get("also_acceptable", [])} for q in ruler["questions"]}


def _first(items, hit):
    return next((i for i, it in enumerate(items, 1) if hit(it)), None)


def score(pool, keys, docs=None):
    """{version: {qid: {first_rank, hits, doc_rank, doc_hits, shown}}}. `docs` ({qid: expected judgments}) adds the expected-judgment test."""
    versions = sorted({v for q in pool for v in q["lists"]})
    out = {v: {} for v in versions}
    for q in pool:
        wanted = keys[q["qid"]]
        wdocs = (docs or {}).get(q["qid"], set())
        for v in versions:
            items = q["lists"].get(v)
            if items is None:
                continue
            whole = v.split(" ")[0] in ("S", "M")
            top = items if whole else items[:10]
            fr = _first(top, lambda it: it["h"] in wanted)
            dr = _first(top, lambda it: bool(({it["doc"], *it.get("also", [])}) & wdocs)) if wdocs else None
            out[v][q["qid"]] = {"first_rank": fr, "hits": {str(n): bool(fr and fr <= n) for n in KS}, "doc_rank": dr, "doc_hits": {str(n): bool(dr and dr <= n) for n in KS}, "shown": len(top)}
    return out


def summarise(scores, pool):
    kind = {q["qid"]: q["kind"] for q in pool}
    out = {}
    for v, per in scores.items():
        row = {"questions": len(per)}
        for n in KS:
            row[f"top{n}"] = sum(s["hits"][str(n)] for s in per.values())
            row[f"doc_top{n}"] = sum(s["doc_hits"][str(n)] for s in per.values())
            for k in ("everyday", "legal"):
                row[f"top{n}_{k}"] = sum(s["hits"][str(n)] for qid, s in per.items() if kind[qid] == k)
                row[f"doc_top{n}_{k}"] = sum(s["doc_hits"][str(n)] for qid, s in per.items() if kind[qid] == k)
        row["everyday"] = sum(1 for qid in per if kind[qid] == "everyday")
        row["legal"] = sum(1 for qid in per if kind[qid] == "legal")
        out[v] = row
    return out


def report(pool, scores, summary, run=None):
    L = ["# Key test on the ruler's tuning half (PRIVATE)", "",
         "**Source label: the verified key paragraph, or the expected judgment, found by hash and id; no reviewer mark.** A hit says it was found, not that the other passages are good. "
         "The key paragraphs and expected judgments are Recourse's picks and this project's own, not lawyer-checked, and biased towards famous settled topics; do not compare these figures with the live site, which was tuned on them.", ""]
    if run:
        L += [f"Run: {run.get('when', '')}; index head `{run.get('index_commit', '')[:7]}`; {len(pool)} questions; re-rank tokens billed {run.get('spend', {}).get('rerank_tokens', 0):,}.", ""]
    L += ["## Expected judgment found (any passage of it), per version", "",
          "| Version | Questions (everyday / legal) | in top 1 | top 3 | top 5 | top 10 | top 5, everyday | top 5, legal |", "|---|---|---|---|---|---|---|---|"]
    for v, r in summary.items():
        L.append(f"| {v} | {r['questions']} ({r['everyday']} / {r['legal']}) | {r['doc_top1']} | {r['doc_top3']} | {r['doc_top5']} | {r['doc_top10']} | {r['doc_top5_everyday']} of {r['everyday']} | {r['doc_top5_legal']} of {r['legal']} |")
    L += ["", "## Key paragraph found (the exact verified passage), per version", "",
          "| Version | Questions | in top 1 | top 3 | top 5 | top 10 | top 5, everyday | top 5, legal |", "|---|---|---|---|---|---|---|---|"]
    for v, r in summary.items():
        L.append(f"| {v} | {r['questions']} | {r['top1']} | {r['top3']} | {r['top5']} | {r['top10']} | {r['top5_everyday']} of {r['everyday']} | {r['top5_legal']} of {r['legal']} |")
    L += ["", "The second test is strict: another passage of the same judgment does not count. S shows only a few passages, so its 'top 10' is what it showed.", "",
          "## Per question (rank of the first hit: judgment / exact paragraph; '-' = not found)", "",
          "| Question | Topic | Kind | " + " | ".join(summary) + " |", "|---|---|---|" + "---|" * len(summary)]
    for q in pool:
        cells = []
        for v in summary:
            s = scores[v].get(q["qid"], {})
            cells.append(f"{'#' + str(s['doc_rank']) if s.get('doc_rank') else '-'} / {'#' + str(s['first_rank']) if s.get('first_rank') else '-'}")
        L.append(f"| {q['qid']} | {q.get('domain', '')} | {q['kind']} | " + " | ".join(cells) + " |")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pool", required=True)
    ap.add_argument("--ruler", default=os.path.join(ROOT, "review_data", "ruler", "ruler_v2.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    with open(a.pool, encoding="utf-8") as fh:
        doc = json.load(fh)
    pool = doc["questions"]
    ruler = RU.load(a.ruler)
    keys = key_hashes(ruler)
    scores = score(pool, keys, expected_docs(ruler))
    summary = summarise(scores, pool)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "key_test.json"), "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "scores": scores}, fh, indent=1)
        fh.write("\n")
    with open(os.path.join(a.out, "KEY_TEST.md"), "w", encoding="utf-8") as fh:
        fh.write(report(pool, scores, summary, doc.get("run")))
    print(f"wrote {a.out}")
    for v, r in summary.items():
        print(f"{v:18} questions {r['questions']:>2}  expected judgment top1 {r['doc_top1']:>2} top5 {r['doc_top5']:>2} top10 {r['doc_top10']:>2} | exact key paragraph top1 {r['top1']:>2} top5 {r['top5']:>2} top10 {r['top10']:>2}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
