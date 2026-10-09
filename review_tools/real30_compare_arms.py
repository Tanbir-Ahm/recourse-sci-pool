#!/usr/bin/env python3
"""Compares two pools of the same questions: the base (main index) and an arm (main index + side index). No reviewer mark, no new spend; reads two pool.json files and the private key.

    python review_tools/real30_compare_arms.py --base review_results/DATE_real30_pool_dev/pool.json --arm review_results/DATE_real30_pool_dev_plus_side_index/pool.json \
        --side-manifest review_data/side_index/DATE_x/SUPPLEMENT.json --overlay review_results/DATE_real30_pool_dev_plus_side_index/key_overlay.json --out review_results/DATE_real30_pool_dev_plus_side_index

Says, per version: how many answerable questions have a key authority in the top 5 in each pool (same questions, original key); where the first key authority moved; which old rulings sit in the top 5;
which judgments of the side index surfaced and where; and which passages of the arm no reviewer has seen (the base pool's marks cover only the passages the base pool showed). The overlay (optional)
gives the questions whose key authority only the side index holds (it never changes the key file) and is used for a second set of rates for the arm.
Source label: found by name in the index, no reviewer mark. PRIVATE (uses the key).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import real30_score as S                    # noqa: E402


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def side_hits(items, side_docs, titles, limit=10):
    """[(rank, doc, title)] for the passages of the first `limit` that come from a side-index judgment."""
    out = []
    for rank, it in enumerate(items[:limit], 1):
        for d in S.docs_of(it):
            if d in side_docs:
                out.append((rank, d, titles.get(d, str(d))))
                break
    return out


def compare(base, arm, key, overlay, side_docs, titles):
    bq = {q["qid"]: q for q in base["questions"]}
    aq = {q["qid"]: q for q in arm["questions"]}
    common = [q for q in bq if q in aq]
    bpool, apool = [bq[q] for q in common], [aq[q] for q in common]
    ok_key = S.with_overlay(key, overlay)
    versions = [v for v in S.score(bpool, key) if v in S.score(apool, key)]
    sb, sa = S.score(bpool, key, versions), S.score(apool, key, versions)
    sa_o = S.score(apool, ok_key, versions)
    summ_b, summ_a, summ_a_o = S.summarise(sb, key), S.summarise(sa, key), S.summarise(sa_o, ok_key)
    moved, surfaced, unseen = [], [], []
    for qid in common:
        for v in versions:
            if v not in sb or qid not in sb[v] or qid not in sa[v]:
                continue
            r0, r1 = sb[v][qid]["first_rank"], sa_o[v][qid]["first_rank"]
            reachable_before = key["questions"][qid]["reachable"]
            if reachable_before is True and r0 != r1:
                moved.append({"qid": qid, "version": v, "base": r0, "arm": r1})
            if reachable_before is False and r1 is not None:
                moved.append({"qid": qid, "version": v, "base": None, "arm": r1, "note": "only the side index holds the key authority"})
        for v in versions:
            items = aq[qid]["lists"].get(v) or []
            hits = side_hits(items, side_docs, titles, 10 if not v.startswith("S") else len(items))
            if hits:
                surfaced.append({"qid": qid, "version": v, "hits": [{"rank": r, "doc": d, "title": t} for r, d, t in hits]})
        seen = {r["h"] for r in bq[qid]["rows"]}
        new = [r for r in aq[qid]["rows"] if r["h"] not in seen]
        if new:
            unseen.append({"qid": qid, "new_rows": len(new), "of": len(aq[qid]["rows"]), "from_side_index": sum(1 for r in new if r["doc"] in side_docs)})
    stale = {}
    for v in versions:
        for tag, sc, k in (("base", sb, key), ("arm", sa_o, ok_key)):
            n = sum(len([x for x in s["stale"] if x["counts_as_stale"]]) for s in sc[v].values())
            stale.setdefault(v, {})[tag] = n
    return {"questions": common, "versions": versions, "rates_base": summ_b, "rates_arm_same_key": summ_a, "rates_arm_with_overlay": summ_a_o, "moved": moved, "surfaced": surfaced,
            "unseen": unseen, "stale_slots_top5": stale, "scores_base": sb, "scores_arm": sa_o}


def report(res, base_run, arm_run, key):
    kq = key["questions"]
    L = ["# Main index vs main index + side index (PRIVATE)", "",
         "**Source label: the named key authority found in the index by name; no reviewer mark.** It says whether the case the owner's file names is among a version's results, not whether a result answers the question. "
         "Never send to reviewers. Not lawyer-checked. Exploratory: tuning half only.", "",
         f"Base: index `{str(base_run.get('index_commit', ''))[:7]}`, {base_run.get('spend', {}).get('rerank_tokens', 0):,} re-rank tokens. "
         f"Arm: the same plus a side index of {(arm_run.get('side_index') or {}).get('documents', '?')} judgments / {(arm_run.get('side_index') or {}).get('passages', '?'):,} passages, "
         f"{arm_run.get('spend', {}).get('rerank_tokens', 0):,} re-rank tokens. {len(res['questions'])} questions in both.", "",
         "## Key authority in the top 5 (answerable questions; the same questions and the original key in both columns)", "",
         "| Version | Questions | Base: top 1 | top 5 | top 10 | Arm: top 1 | top 5 | top 10 |", "|---|---|---|---|---|---|---|---|"]
    for v in res["versions"]:
        b, a = res["rates_base"][v], res["rates_arm_same_key"][v]
        L.append(f"| {v} | {b['questions']} | {b['hit@1']} | {b['hit@5']} | {b['hit@10']} | {a['hit@1']} | {a['hit@5']} | {a['hit@10']} |")
    L += ["", "## With the side index's key authorities counted (the overlay)", "",
          "| Version | Questions (arm) | Arm: top 1 | top 5 | top 10 |", "|---|---|---|---|---|"]
    for v in res["versions"]:
        a = res["rates_arm_with_overlay"][v]
        L.append(f"| {v} | {a['questions']} | {a['hit@1']} | {a['hit@5']} | {a['hit@10']} |")
    L += ["", "## Where the first key authority moved", ""]
    if res["moved"]:
        L += ["| Question | Version | Base rank | Arm rank | Note |", "|---|---|---|---|---|"]
        L += [f"| {m['qid']} | {m['version']} | {m['base'] or '-'} | {m['arm'] or '-'} | {m.get('note', '')} |" for m in res["moved"]]
    else:
        L.append("Nowhere: every answerable question has the same first key-authority rank in both pools.")
    L += ["", "## Older rulings that count as stale, in the top 5 (passages over all questions)", "", "| Version | Base | Arm |", "|---|---|---|"]
    L += [f"| {v} | {res['stale_slots_top5'][v]['base']} | {res['stale_slots_top5'][v]['arm']} |" for v in res["versions"]]
    L += ["", "## Side-index judgments that surfaced (top 10 of a version; all that S showed)", ""]
    if res["surfaced"]:
        L += ["| Question | Version | Rank: judgment |", "|---|---|---|"]
        for s in res["surfaced"]:
            L.append(f"| {s['qid']} | {s['version']} | " + "; ".join(f"#{h['rank']} {h['title'][:60]}" for h in s["hits"]) + " |")
        qs = sorted({s["qid"] for s in res["surfaced"]})
        L += ["", f"Questions where at least one side-index judgment reached the top 10 of some version: {len(qs)} ({', '.join(qs)})."]
    else:
        L.append("None reached a top 10.")
    n_new = sum(u["new_rows"] for u in res["unseen"])
    L += ["", "## Passages of the arm that the base pool did not show (nobody has marked them)", "",
          f"{n_new} passages over {len(res['unseen'])} questions" + (f" ({sum(u['from_side_index'] for u in res['unseen'])} from the side index)." if res["unseen"] else "."), ""]
    if res["unseen"]:
        L += ["| Question | New passages | of the arm's rows | from the side index |", "|---|---|---|---|"]
        L += [f"| {u['qid']} | {u['new_rows']} | {u['of']} | {u['from_side_index']} |" for u in res["unseen"]]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--key", default=S.DEFAULT_KEY)
    ap.add_argument("--overlay")
    ap.add_argument("--side-manifest", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    base, arm, key = load(a.base), load(a.arm), load(a.key)
    man = load(a.side_manifest)
    side_docs = {d["doc"] for d in man["documents_detail"]}
    titles = {d["doc"]: d["title"] for d in man["documents_detail"]}
    overlay = load(a.overlay) if a.overlay else None
    res = compare(base, arm, key, overlay, side_docs, titles)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "arm_comparison.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(a.out, "ARM_COMPARISON.md"), "w", encoding="utf-8") as fh:
        fh.write(report(res, base.get("run", {}), arm.get("run", {}), key))
    print(f"wrote {a.out}/ARM_COMPARISON.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
