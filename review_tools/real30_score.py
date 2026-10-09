"""Scores a pool of the 30 questions without any human mark: is the key authority among a version's top results, and did a known-stale ruling get through?

    python review_tools/real30_score.py --pool review_results/DATE_real30_pool_dev/pool.json --out review_results/DATE_real30_pool_dev

Reads the pool (what the runner wrote: each question's rows and, per version, its ordered top passages) and the private key (`real30_key_v1.json`: the index documents of each question's key
authorities and of the older rulings). For each version and question it reports the rank of the first key authority (counting passages, best first) and whether one is in the top 1, 5 and 10;
and which older rulings sit in the top 5, split into those that count as known-stale (overruled, modified, recalled, replaced by statute) and those that are only narrower or contested.
Questions whose key authority the index cannot reach (R06, R15, R21) and the controls are reported apart, never in the rates. Versions starting with S show only a few passages and are
scored on everything they showed. Source label: found in the index by name, no reviewer mark; says nothing about whether the passage answers the question. PRIVATE.
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DEFAULT_KEY = os.path.join(ROOT, "review_data", "ruler", "real30_key_v1.json")
KS = (1, 5, 10)


def docs_of(item):
    """The documents a listed passage stands for: its own judgment and any other judgment that holds identical text."""
    return {item["doc"], *item.get("also", [])}


def first_rank(items, wanted):
    """Rank (1-based, counting passages) of the first passage that comes from a wanted document, or None."""
    for rank, it in enumerate(items, 1):
        if docs_of(it) & wanted:
            return rank
    return None


def with_overlay(key, overlay):
    """A copy of the key in which the overlay's questions have the key documents of the side index and count as answerable. The key file is not changed."""
    out = json.loads(json.dumps(key))
    for qid, o in (overlay or {}).get("questions", {}).items():
        q = out["questions"][qid]
        q["key_docs"] = sorted(set(q["key_docs"]) | set(o["key_docs"]))
        q["reachable"] = True
        q["authorities"] = list(q["authorities"]) + [{"label": o.get("label", "side-index authority"), "role": "key"}]
    return out


def score(pool, key, versions=None):
    """{version: {qid: {first_rank, hits: {k: bool}, stale: [...]}}} for the questions in the pool. `pool` questions carry lists: {version: [{doc, also, h}, ...]} best first."""
    kq = key["questions"]
    versions = versions or sorted({v for q in pool for v in q["lists"]})
    out = {v: {} for v in versions}
    for q in pool:
        k = kq[q["qid"]]
        wanted = set(k["key_docs"])
        stale = {s["doc"]: s for s in k["stale_docs"]}
        for v in versions:
            items = q["lists"].get(v)
            if items is None:
                continue
            whole = v.split(" ")[0] in ("S", "M")
            top5 = items if whole else items[:5]
            fr = first_rank(items, wanted) if wanted else None
            found = []
            for rank, it in enumerate(top5, 1):
                for d in docs_of(it):
                    if d in stale:
                        found.append({"rank": rank, "doc": d, "label": stale[d]["label"], "kind": stale[d]["kind"], "counts_as_stale": stale[d]["counts_as_stale"]})
            out[v][q["qid"]] = {"first_rank": fr, "hits": {str(n): bool(fr and fr <= n) for n in KS}, "shown": len(items), "stale": found}
    return out


def summarise(scores, key, only=None):
    """Per version, over the questions whose key authority the index can reach: how many have it in the top 1, 5 and 10, and the stale and narrower passages in the top 5.
    The stale passages on the index-gap questions (where the key authority is missing) are counted apart: they are the case where only an old ruling is on offer.
    `only` limits the count to a set of question ids (for a like-with-like comparison on the questions a version was run on)."""
    kq = key["questions"]
    out = {}
    for v, per in scores.items():
        rate = {"questions": 0, **{f"hit@{n}": 0 for n in KS}, "stale_slots": 0, "stale_questions": 0, "narrower_slots": 0, "gap_stale_slots": 0, "gap_stale_questions": 0}
        for qid, s in per.items():
            if only is not None and qid not in only:
                continue
            st = [x for x in s["stale"] if x["counts_as_stale"]]
            if kq[qid]["reachable"] is False:
                rate["gap_stale_slots"] += len(st)
                rate["gap_stale_questions"] += bool(st)
                continue
            if kq[qid]["reachable"] is not True:
                continue
            rate["questions"] += 1
            for n in KS:
                rate[f"hit@{n}"] += s["hits"][str(n)]
            rate["stale_slots"] += len(st)
            rate["stale_questions"] += bool(st)
            rate["narrower_slots"] += sum(1 for x in s["stale"] if not x["counts_as_stale"])
        out[v] = rate
    return out


def report(pool, key, scores, summary, run=None):
    kq = key["questions"]
    L = ["# Authority-hit test and stale rulings (PRIVATE)", "",
         "**Source label: the named key authority found in the index by name; no reviewer mark.** It says whether the case the owner's file names is among a version's results, not whether a result answers the question. "
         "Never send to reviewers. Not lawyer-checked.", ""]
    if run:
        L += [f"Run: {run.get('when', '')}; index head `{run.get('index_commit', '')[:7]}`; {len(pool)} questions; re-rank tokens billed {run.get('spend', {}).get('rerank_tokens', 0):,}.", ""]
    L += ["## Per version (questions whose key authority the index holds)", "",
          "| Version | Questions | Key authority in top 1 | in top 5 | in top 10 | Known-stale passages in top 5 (questions) | Narrower or contested older rulings in top 5 | Known-stale passages in top 5 on the index-gap questions (questions) |", "|---|---|---|---|---|---|---|---|"]
    for v, r in summary.items():
        L.append(f"| {v} | {r['questions']} | {r['hit@1']} | {r['hit@5']} | {r['hit@10']} | {r['stale_slots']} ({r['stale_questions']}) | {r['narrower_slots']} | {r['gap_stale_slots']} ({r['gap_stale_questions']}) |")
    L += ["", "S shows only a few passages, so its 'top 10' is what it showed. The last column counts old rulings that sit in the top 5 where the index lacks the ruling that corrects them: only the old law is on offer.", ""]
    rewritten = {q["qid"] for q in pool if "C rewrite" in q["lists"]}
    if rewritten:
        like = summarise(scores, key, only=rewritten)
        answerable = sorted(q for q in rewritten if kq[q]["reachable"] is True)
        L += [f"## Like with like: only the {len(answerable)} answerable questions that have a blind rewrite ({', '.join(answerable)}; the rewritten index-gap questions and controls are left out)", "",
              "| Version | Questions | Key authority in top 1 | in top 5 | in top 10 |", "|---|---|---|---|---|"]
        L += [f"| {v} | {r['questions']} | {r['hit@1']} | {r['hit@5']} | {r['hit@10']} |" for v, r in like.items() if r["questions"]]
        L += ["", "C and F are run only on the questions that have a rewrite, so their rows above cover fewer questions than A, B, E and S; this table puts all versions on the same questions.", ""]
    L += ["## Per question", ""]
    versions = list(summary)
    L += ["| Question | Domain | Key authority | " + " | ".join(versions) + " |", "|---|---|---|" + "---|" * len(versions)]
    for q in pool:
        k = kq[q["qid"]]
        cells = []
        for v in versions:
            s = scores[v].get(q["qid"])
            if s is None:
                cells.append("-")
            elif k["reachable"] is not True:
                cells.append("n/a" + (f" (stale in top 5: {len(s['stale'])})" if s["stale"] else ""))
            else:
                st = [x for x in s["stale"] if x["counts_as_stale"]]
                cells.append(("#" + str(s["first_rank"]) if s["first_rank"] else "not in top " + str(s["shown"])) + (f"; stale {len(st)}" if st else ""))
        L.append(f"| {q['qid']} | {q.get('domain', '')} | {', '.join(a['label'].split(' (')[0] for a in k['authorities'] if a['role'] == 'key')[:60] or '-'} | " + " | ".join(cells) + " |")
    apart = [q["qid"] for q in pool if kq[q["qid"]]["reachable"] is False]
    ctrl = [q["qid"] for q in pool if kq[q["qid"]]["reachable"] is None]
    L += ["", "## Scored apart", "",
          f"Index gaps (the key authority is filtered out of the index or absent): {', '.join(apart) or 'none in this pool'}. Controls (no key authority): {', '.join(ctrl) or 'none in this pool'}.", "",
          "## Older rulings in the top 5", "", "| Question | Version | Rank | Ruling | What happened | Counts as stale |", "|---|---|---|---|---|---|"]
    for v, per in scores.items():
        for qid, s in per.items():
            for x in s["stale"]:
                L.append(f"| {qid} | {v} | {x['rank']} | {x['label']} | {x['kind']} | {'yes' if x['counts_as_stale'] else 'no'} |")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pool", required=True)
    ap.add_argument("--key", default=DEFAULT_KEY)
    ap.add_argument("--overlay", help="key documents that only a side index holds (JSON {questions: {R21: {key_docs: [...], label: ...}}}); counted as answerable for this pool; the key file is not changed")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    with open(a.pool, encoding="utf-8") as fh:
        doc = json.load(fh)
    with open(a.key, encoding="utf-8") as fh:
        key = json.load(fh)
    if a.overlay:
        with open(a.overlay, encoding="utf-8") as fh:
            key = with_overlay(key, json.load(fh))
    pool = doc["questions"]
    scores = score(pool, key)
    summary = summarise(scores, key)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "authority_hits.json"), "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "scores": scores}, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(a.out, "AUTHORITY_HITS.md"), "w", encoding="utf-8") as fh:
        fh.write(report(pool, key, scores, summary, doc.get("run")))
    print(f"wrote {a.out}")
    for v, r in summary.items():
        print(f"{v:18} questions {r['questions']:>2}  top1 {r['hit@1']:>2}  top5 {r['hit@5']:>2}  top10 {r['hit@10']:>2}  stale slots {r['stale_slots']} ({r['stale_questions']} questions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
