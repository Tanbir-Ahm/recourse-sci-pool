"""Still-good-law checker for Supreme Court of India judgments.

    python sci_goodlaw.py build  --crawl-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --corpus corpus.sqlite
    python sci_goodlaw.py find   --corpus corpus.sqlite "rangappa"
    python sci_goodlaw.py check  --corpus corpus.sqlite "Rangappa v. Sri Mohan" --year 2010 --out reports/
    python sci_goodlaw.py check  --corpus corpus.sqlite --doc-key c36322 --out reports/
    python sci_goodlaw.py batch  --corpus corpus.sqlite --targets goodlaw/targets/priority.json --out reports/
    python sci_goodlaw.py known  --corpus corpus.sqlite                      # the 20 known cases
    python sci_goodlaw.py library --recourse-dir ../tanbir-ahm/recourse      # snapshot the cases Recourse can show (goodlaw/targets/library.json)
    python sci_goodlaw.py cards  --corpus corpus.sqlite                      # precompute a currency card for every library case (cards/)
    python sci_goodlaw.py cards-review --sheet cards/REVIEW_SHEET.csv        # record the verdicts a person filled into the review sheet
    python sci_goodlaw.py card   "Rangappa v Sri Mohan"                      # what the answer step would be told about one case
    python sci_goodlaw.py eval   --corpus corpus.sqlite --half dev           # agreement with the reporter's citator (development half)
    python sci_goodlaw.py eval   --corpus corpus.sqlite --half dev --gold modern [--production]   # the same against the 2017-2023 case-law tables

`build` reads the two data branches into one searchable store (about 10 minutes, 2 GB) and indexes the citations in it. `check` writes a JSON bundle and a
Markdown report for one case: who cites it, what they do with it (with the exact sentences), what became of the statute sections it cites, a triage label
and a statement of what the collection can and cannot see. No code here decides that a case is good law; see goodlaw/report.py.
"""
import argparse
import json
import os
import sys

from goodlaw import corpus as K
from goodlaw import mentions as M
from goodlaw import report as R


def resolve(corpus, query=None, year=None, doc_key=None, pick=None):
    """The corpus document for a case, or raises ValueError listing the candidates."""
    if doc_key:
        d = corpus.get(doc_key, with_text=False)
        if not d:
            raise ValueError(f"no document {doc_key}")
        return d
    rows = corpus.find_title(query, 40)
    if year:
        rows = [d for d in rows if d["year"] == int(year)]
    if not rows:
        raise ValueError(f"no judgment found for {query!r}" + (f" in {year}" if year else ""))
    if pick is not None:
        return rows[int(pick) - 1]
    if len(rows) > 1:
        lines = "\n".join(f"  {i}. {d['doc_key']}  {d['title'][:70]}  ({d['date'] or d['year']}, bench {d['bench_size'] or '?'})" for i, d in enumerate(rows, 1))
        raise ValueError(f"{len(rows)} judgments match {query!r}; choose with --doc-key or --pick N:\n{lines}")
    return rows[0]


def check_one(corpus, doc, extra_cites=(), aliases=(), out_dir=None, log=print):
    target = M.Target.from_doc(doc)
    from goodlaw import cites as C
    for c in extra_cites:
        k = C.norm_cite(c)
        if k and k not in target.cites:
            target.cites.append(k)
    target.aliases = list(aliases)
    bundle = R.build_bundle(corpus, target, corpus.get(doc["doc_key"], with_text=False))
    md = R.render_markdown(bundle)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        base = os.path.join(out_dir, doc["doc_key"])
        with open(base + ".json", "w", encoding="utf-8") as fh:
            json.dump(bundle, fh, indent=1, ensure_ascii=False)
        with open(base + ".md", "w", encoding="utf-8") as fh:
            fh.write(md)
        log(f"wrote {base}.json and .md")
    return bundle, md


HERE = os.path.dirname(os.path.abspath(__file__))


def run_cards(a):
    from goodlaw import cardreader as CR
    from goodlaw import cards as CD
    from goodlaw import library as LB
    reviews_path = os.path.join(getattr(a, "out", os.path.join(HERE, "cards")), "reviews.json")
    if a.cmd == "card":
        index = CR.load(a.cards)
        card = CR.find(index, case_name=a.name, citation=a.citation)
        if card is None:
            print(f"no card for {a.name or a.citation!r}; the library has {len(index['cards'])} cases", file=sys.stderr)
            return 2
        result = CR.for_answer(card, today=a.today)
        print(json.dumps(result, indent=1, ensure_ascii=False))
        return 0
    cards_path = os.path.join(a.out, "currency_cards.json")
    if a.cmd == "cards-review":
        doc = json.load(open(cards_path, encoding="utf-8"))
        recorded, problems = CD.merge_review_sheet(a.sheet, doc["cards"], reviews_path)
        for p in problems:
            print("PROBLEM:", p, file=sys.stderr)
        CD.attach_reviews(doc["cards"], CD.load_reviews(reviews_path))
        with open(cards_path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
        print(f"{recorded} verdict(s) recorded in {reviews_path}; the cards now carry them" + (f"; {len(problems)} row(s) skipped" if problems else ""))
        return 1 if problems else 0
    snap = json.load(open(a.library, encoding="utf-8"))
    overrides = LB.load_overrides(a.overrides)
    sheet = os.path.join(a.out, "REVIEW_SHEET.csv")
    os.makedirs(a.out, exist_ok=True)
    if os.path.exists(sheet) and os.path.exists(cards_path):                       # verdicts a person filled in but nobody merged yet must not be lost when the sheet is rewritten
        old_doc = json.load(open(cards_path, encoding="utf-8"))
        recorded, problems = CD.merge_review_sheet(sheet, old_doc["cards"], reviews_path)
        if recorded:
            print(f"merged {recorded} verdict(s) from the existing review sheet before rebuilding")
        for p in problems:
            print("PROBLEM:", p, file=sys.stderr)
    old_cards = json.load(open(cards_path, encoding="utf-8"))["cards"] if os.path.exists(cards_path) else None
    cards, reports = CD.build_all(a.corpus, snap["cases"], overrides, today=a.today, workers=a.workers)
    CD.attach_reviews(cards, CD.load_reviews(reviews_path))
    doc = CD.write_cards(cards, reports, a.out, snap.get("snapshot"))
    changes = CD.compare(old_cards, cards)
    today = cards[0]["provenance"]["generated"]
    CD.write_changes(changes, os.path.join(a.out, "CHANGES.md"), today, first_run=old_cards is None)
    n_sheet = CD.write_review_sheet(cards, sheet)
    CD.write_match_check(cards, os.path.join(a.out, "MATCH_CHECK.csv"))
    print(f"{len(cards)} cards written to {a.out}: {doc['counts']}")
    print(f"{n_sheet} case(s) in the review sheet; {len([c for c in changes if c['worse']])} change(s) since the last run that need a look (see CHANGES.md)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--crawl-dir", default="../recourse-sci-pool-data")
    b.add_argument("--bucket-dir", default="../recourse-sci-bucket-data")
    b.add_argument("--corpus", default="corpus.sqlite")
    b.add_argument("--workers", type=int, default=4)
    f = sub.add_parser("find")
    f.add_argument("query")
    c = sub.add_parser("check")
    c.add_argument("query", nargs="?")
    c.add_argument("--year")
    c.add_argument("--doc-key")
    c.add_argument("--pick")
    c.add_argument("--cite", action="append", default=[], help='extra citation the case is known by, e.g. "(2010) 11 SCC 441"')
    c.add_argument("--alias", action="append", default=[], help="extra short name to look for alone, e.g. Koushal")
    c.add_argument("--out")
    c.add_argument("--json", action="store_true")
    bt = sub.add_parser("batch")
    bt.add_argument("--targets", required=True)
    bt.add_argument("--out", required=True)
    kn = sub.add_parser("known")
    kn.add_argument("--cases", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "goodlaw", "targets", "known.json"))
    lb = sub.add_parser("library")
    lb.add_argument("--recourse-dir", required=True, help="a checkout of the Recourse repository (read only: its registry code is run in a subprocess, nothing is written there)")
    lb.add_argument("--out", default=os.path.join(HERE, "goodlaw", "targets", "library.json"))
    cd = sub.add_parser("cards")
    cd.add_argument("--library", default=os.path.join(HERE, "goodlaw", "targets", "library.json"))
    cd.add_argument("--overrides", default=os.path.join(HERE, "goodlaw", "targets", "library_overrides.json"))
    cd.add_argument("--out", default=os.path.join(HERE, "cards"))
    cd.add_argument("--workers", type=int, default=4)
    cd.add_argument("--today", help="date to stamp on the cards (default: today)")
    cr = sub.add_parser("cards-review")
    cr.add_argument("--sheet", default=os.path.join(HERE, "cards", "REVIEW_SHEET.csv"))
    cr.add_argument("--out", default=os.path.join(HERE, "cards"))
    cs = sub.add_parser("card")
    cs.add_argument("name", nargs="?")
    cs.add_argument("--citation")
    cs.add_argument("--cards", default=os.path.join(HERE, "cards", "currency_cards.json"))
    cs.add_argument("--today")
    ev = sub.add_parser("eval")
    ev.add_argument("--half", choices=["dev", "held"], required=True)
    ev.add_argument("--confirm-held-out", action="store_true", help="the held-out half is for one reported run per rule set; say so to run it")
    ev.add_argument("--gold", choices=["citator", "modern"], default="citator", help="citator: the old reporters' citator codes (to about 1985); modern: the 2017-2023 case-law tables, read on the court's own text only")
    ev.add_argument("--production", action="store_true", help="with --gold modern: run the adverse pairs through the full mention finder (slow, learns citations) instead of the fast per-pair reader")
    ev.add_argument("--workers", type=int, default=4)
    ev.add_argument("--out", help="write the per-pair results here (JSON)")
    for p in (f, c, bt, kn, ev, cd):
        p.add_argument("--corpus", default="corpus.sqlite")
    a = ap.parse_args(argv)
    if a.cmd == "eval" and a.half == "held" and not a.confirm_held_out:
        print("the held-out half is run once per frozen rule set; add --confirm-held-out to run it", file=sys.stderr)
        return 2
    if a.cmd == "build":
        here = os.path.dirname(os.path.abspath(__file__))
        K.build(a.crawl_dir, a.bucket_dir, os.path.join(here, "coverage", "bucket_match", "registry.csv.gz"),
                os.path.join(here, "coverage", "bucket_match", "none_resolution.csv.gz"), a.corpus, a.workers)
        K.index_cites(a.corpus, a.workers)
        return 0
    if a.cmd == "library":
        from goodlaw import library as LB
        snap = LB.snapshot(a.recourse_dir)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, indent=1, ensure_ascii=False)
        classes = {}
        for c_ in snap["cases"]:
            classes[c_["court_class"]] = classes.get(c_["court_class"], 0) + 1
        print(f"{len(snap['cases'])} cases read from Recourse commit {snap['snapshot']['recourse_commit']}: {classes}; wrote {a.out}")
        return 0
    if a.cmd in ("cards", "cards-review", "card"):
        return run_cards(a)
    corpus = K.Corpus(a.corpus)
    if a.cmd == "find":
        for d in corpus.find_title(a.query, 40):
            print(f"{d['doc_key']:22} {d['date'] or d['year']!s:11} bench {d['bench_size'] or '?'!s:3} {d['title'][:90]}")
        return 0
    if a.cmd == "check":
        try:
            doc = resolve(corpus, a.query, a.year, a.doc_key, a.pick)
        except ValueError as e:
            print(e, file=sys.stderr)
            return 2
        bundle, md = check_one(corpus, doc, a.cite, a.alias, a.out)
        print(json.dumps(bundle, indent=1, ensure_ascii=False) if a.json else md)
        return 0
    if a.cmd == "known":
        from goodlaw import evaluate as E
        rows, summary = E.known_cases(corpus, a.cases)
        print(json.dumps(summary))
        return 0
    if a.cmd == "eval":
        from goodlaw import evaluate as E
        if a.gold == "modern":
            from goodlaw import modern_gold as G
            pairs, counts = G.gold_pairs(corpus)
            unresolved = f"{counts['rows'] - counts['pairs']} table rows were not usable: {counts}"
            dev, held = G.split(pairs)
            chosen = dev if a.half == "dev" else held
            if a.production:
                res = E.production_rows(corpus, [p for p in chosen if p[2] in ("O", "NF")], body_only=True, log=print)
            else:
                res = E.run(a.corpus, chosen, workers=a.workers, body_only=True)
        else:
            pairs, unresolved = E.gold_pairs(corpus)
            dev, held = E.split(pairs)
            res = E.run(a.corpus, dev if a.half == "dev" else held, workers=a.workers)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as fh:
                json.dump(res, fh)
        print(f"{a.half} ({a.gold}): {len(res)} pairs; unmatched: {unresolved}")
        print(json.dumps(E.summarise(res), indent=1))
        return 0
    if a.cmd == "batch":
        targets = json.load(open(a.targets, encoding="utf-8"))["targets"]
        rows = []
        for t in targets:
            try:
                doc = resolve(corpus, t.get("query"), t.get("year"), t.get("doc_key"), t.get("pick"))
            except ValueError as e:
                print(f"SKIP {t}: {str(e).splitlines()[0]}", file=sys.stderr)
                rows.append({"target": t, "error": str(e).splitlines()[0]})
                continue
            bundle, _ = check_one(corpus, doc, t.get("cites", []), t.get("aliases", []), a.out, log=lambda *_: None)
            s = bundle["summary"]
            rows.append({"target": t.get("name") or doc["title"], "doc_key": doc["doc_key"], "triage": bundle["triage"], "statute_flag": bundle["statute_flag"],
                         "citing_judgments": s["citing_judgments"], "latest_citing_year": s["latest_citing_year"], "adverse_strong": len(s["adverse_strong"]),
                         "adverse_possible": len(s["adverse_possible"])})
            print(f"{rows[-1]['triage']:17} {rows[-1]['target'][:60]:60} citing {s['citing_judgments']:4} latest {s['latest_citing_year']}")
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=1)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
