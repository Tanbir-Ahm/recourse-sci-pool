"""Still-good-law checker for Supreme Court of India judgments.

    python sci_goodlaw.py build  --crawl-dir ../recourse-sci-pool-data --bucket-dir ../recourse-sci-bucket-data --corpus corpus.sqlite
    python sci_goodlaw.py find   --corpus corpus.sqlite "rangappa"
    python sci_goodlaw.py check  --corpus corpus.sqlite "Rangappa v. Sri Mohan" --year 2010 --out reports/
    python sci_goodlaw.py check  --corpus corpus.sqlite --doc-key c36322 --out reports/
    python sci_goodlaw.py batch  --corpus corpus.sqlite --targets goodlaw/targets/priority.json --out reports/

`build` reads the two data branches into one searchable store (about 10 minutes, 2 GB) and indexes the citations in it. `check` writes a JSON bundle and a
Markdown report for one case: who cites it, what they do with it (with the exact sentences), what became of the statute sections it turns on, a triage label
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
    for p in (f, c, bt):
        p.add_argument("--corpus", default="corpus.sqlite")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        here = os.path.dirname(os.path.abspath(__file__))
        K.build(a.crawl_dir, a.bucket_dir, os.path.join(here, "coverage", "bucket_match", "registry.csv.gz"),
                os.path.join(here, "coverage", "bucket_match", "none_resolution.csv.gz"), a.corpus, a.workers)
        K.index_cites(a.corpus, a.workers)
        return 0
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
