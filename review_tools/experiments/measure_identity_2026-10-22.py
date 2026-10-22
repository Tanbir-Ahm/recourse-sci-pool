"""One-off measurement (2026-10-22): how many index judgments and search hits can goodlaw/passage_input.py name, and what the chat formatter does with them.

    python review_tools/experiments/measure_identity_2026-10-22.py --corpus corpus.sqlite --index-docs DIR --pool review_results/2026-10-12_fix_test_f/pool.json --out review_results/2026-10-22_identity_measure

DIR holds `index/*.docs.jsonl.gz` (the index branch's document records). Read-only on the corpus, the index records and the pool; no network, no spend. The pool is the stage F run's pooled hits
for the 29 questions (it is a private answer key: only totals for the recipe that stayed, 'B baseline', are written here, nothing per version, no passage text and no question text).
Writes OUT/numbers.json and OUT/unidentified.csv (index doc ids and the reason, nothing else).
"""
import argparse
import collections
import csv
import glob
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

from goodlaw import cardreader as CR  # noqa: E402
from goodlaw import chat_format as CF  # noqa: E402
from goodlaw import corpus as K  # noqa: E402
from goodlaw import passage_input as PI  # noqa: E402
from goodlaw import register as R  # noqa: E402

RECIPE = "B baseline (rerank-3-lite)"            # the recipe that stayed after stage F (FOLLOW_UPS.md, 2026-10-12)


def read_docs(index_docs):
    rows = []
    for f in sorted(glob.glob(os.path.join(index_docs, "index", "*.docs.jsonl.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            rows += [json.loads(line) for line in fh if line.strip()]
    return rows


def why_not(doc, docs, corpus):
    """The reason a judgment cannot be named, in plain words."""
    if doc >= PI.BUCKET_BASE:
        path = (((docs.get(doc) or {}).get("src") or {}).get("path"))
        if not path:
            return "bucket judgment: the index record has no path"
        d = corpus.get("b" + path, with_text=False)
        key = "b" + path
    else:
        key = f"c{doc}"
        d = corpus.get(key, with_text=False)
    if not d:
        return f"not in the corpus ({key})"
    return "in the corpus but with no title, petitioner or respondent"


def name_agrees(corpus_name, pool_title):
    """Do the corpus name's distinctive words appear (60% or more) in the pool's title, which is either 'A versus B (date)' or, where the old harness had nothing better, the opening header text?"""
    ta, tb = set(K.name_key(corpus_name).split()), set(K.name_key(pool_title).split())
    return bool(ta) and len(ta & tb) / len(ta) >= 0.6


def tally(items):
    return dict(collections.Counter(items).most_common())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--index-docs", required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    corpus = K.Corpus(a.corpus)
    rows = read_docs(a.index_docs)
    kept = [r for r in rows if "skip" not in r]
    docs = PI.IndexDocs(rows)
    who = PI.ChainIdentity(PI.CorpusIdentity(corpus, docs), PI.IndexRowIdentity(docs))
    corpus_only = PI.CorpusIdentity(corpus, docs)

    # ---- every kept judgment in the index ---------------------------------------------------------------------------------------------------------------------------------------
    per = {"crawl": collections.Counter(), "bucket": collections.Counter()}
    passages = {"crawl": collections.Counter(), "bucket": collections.Counter()}
    sources, unidentified = collections.Counter(), []
    cite_have = collections.Counter()
    for r in kept:
        side = "bucket" if r["doc"] >= PI.BUCKET_BASE else "crawl"
        n = r.get("passages") or 0
        ident = who(r["doc"])
        per[side]["docs"] += 1
        passages[side]["passages"] += n
        if ident:
            per[side]["identified"] += 1
            passages[side]["identified"] += n
            sources[(side, ident.name_source)] += 1
            reliable = ident.date_source in K.RELIABLE and bool(ident.date)
            per[side]["year_read_from_judgment"] += 1 if reliable else 0
            per[side]["year_known"] += 1 if ident.year else 0
            per[side]["has_citation"] += 1 if ident.citation else 0
        else:
            unidentified.append((r["doc"], side, why_not(r["doc"], docs, corpus), n))
    doc_level = {}
    for side in ("crawl", "bucket"):
        d, p = per[side], passages[side]
        doc_level[side] = {"docs": d["docs"], "identified": d["identified"], "share_identified": round(d["identified"] / d["docs"], 4) if d["docs"] else None,
                           "passages": p["passages"], "passages_in_identified_docs": p["identified"],
                           "share_of_passages_identified": round(p["identified"] / p["passages"], 4) if p["passages"] else None,
                           "year_known": d["year_known"], "year_read_from_judgment": d["year_read_from_judgment"], "has_citation": d["has_citation"]}
    doc_level["name_sources"] = {f"{s}/{n}": c for (s, n), c in sources.items()}
    doc_level["corpus_alone_identified"] = sum(1 for r in kept if corpus_only(r["doc"]))
    doc_level["unidentified_reasons"] = tally(f"{side}: {why}" for _, side, why, _ in unidentified)

    # ---- the stage F pool's hits ----------------------------------------------------------------------------------------------------------------------------------------------------
    pool = json.load(open(a.pool, encoding="utf-8"))
    reg, cards = R.Register.load(), CR.load(os.path.join(ROOT, "cards", "currency_cards.json"))
    fmts = {"coverage_note": CF.Formatter(reg, cards, quiet_policy="coverage_note", today="2026-10-22"), "silent": CF.Formatter(reg, cards, quiet_policy="silent", today="2026-10-22")}

    def classify(msg, passage):
        if not passage["identified"]:
            return "unidentified (not checked)"
        if not msg.lines:
            return "no line (quiet card, silent policy)"
        rule = msg.lines[0].rule
        return {1: "register, confirmed", 2: "register, candidate", 3: "card: adverse", 4: "card: questioned", 5: "quiet card", 6: "not checked (no card or too few)", 7: "statute note only"}[rule]

    def run(hit_rows, label):
        out = {"hits": len(hit_rows), "by_policy": {}}
        ident_n = year_est = cite_n = 0
        names = {"agree": 0, "disagree": 0, "no_pool_title": 0}
        disagreements = []
        for h in hit_rows:
            p = PI.passage_from_hit({"doc": h["doc"], "pn": h.get("pn"), "page": h.get("page"), "h": h.get("h"), "text": h["text"]}, who)
            if p["identified"]:
                ident_n += 1
                year_est += 1 if p["source_info"]["notes"] else 0
                cite_n += 1 if p["citation"] else 0
                t = h.get("title") or ""
                if not t:
                    names["no_pool_title"] += 1
                elif name_agrees(p["case_name"], t):
                    names["agree"] += 1
                else:
                    names["disagree"] += 1
                    disagreements.append((int(h["doc"]), p["case_name"][:90], t[:90]))
        out.update(identified=ident_n, share_identified=round(ident_n / len(hit_rows), 4), year_estimated_not_read=year_est, with_citation=cite_n, name_check_against_pool_title=names)
        for pol, f in fmts.items():
            cls = collections.Counter()
            warn = 0
            for h in hit_rows:
                p = PI.passage_from_hit({"doc": h["doc"], "pn": h.get("pn"), "page": h.get("page"), "h": h.get("h"), "text": h["text"]}, who)
                m = f.format(p)
                c = classify(m, p)
                cls[c] += 1
                warn += 1 if any(x.level in (CF.RED, CF.AMBER) for x in m.lines) else 0
            out["by_policy"][pol] = {"first_line": dict(cls.most_common()), "with_a_warning_or_caution": warn}
        return out, disagreements

    qs = pool["questions"]
    pooled = [r for q in qs for r in q["rows"]]
    by_h = [{r["h"]: r for r in q["rows"]} for q in qs]
    shown = {}
    for k in (5, 10):
        shown[k] = [by_h[i][e["h"]] for i, q in enumerate(qs) for e in q["lists"][RECIPE][:k]]
    results = {"index_snapshot": pool["run"].get("index_commit"), "corpus": corpus.stats(), "questions": len(qs), "every_kept_judgment_in_the_index": doc_level}
    results["all_pooled_hits"], dis = run(pooled, "all pooled")
    results["recipe_top5"], _ = run(shown[5], "top5")
    results["recipe_top10"], _ = run(shown[10], "top10")
    results["pool_title_disagreements"] = [{"doc": d, "corpus_name": c, "pool_title": t} for d, c, t in dis[:25]]
    carded = {PI.CorpusIdentity(corpus, docs)(h["doc"]).name for h in shown[10] if who(h["doc"])}
    distinct = {int(h["doc"]) for h in shown[10]}
    on_cards = sum(1 for h in {int(x["doc"]): x for x in shown[10]}.values() if CR.find(cards, case_name=(who(h["doc"]) or PI.Identity("", None, "")).name, citation=(who(h["doc"]) or PI.Identity("", None, "")).citation or None))
    results["card_coverage"] = {"cards_in_the_file": len(cards["cards"]), "kept_judgments_in_the_index": len(kept), "share_of_index_with_a_card": round(len(cards["cards"]) / len(kept), 4),
                                "distinct_judgments_in_the_recipe_top10_hits": len(distinct), "of_which_have_a_card": on_cards}
    with open(os.path.join(a.out, "numbers.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(a.out, "unidentified.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["index_doc", "side", "reason", "passages"])
        w.writerows(sorted(unidentified))
    print(json.dumps(results, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
