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
    python sci_goodlaw.py reader-eval build|score --out DIR [--verdicts FILE]   # the second reader on the tuning halves (blind batch, then score)
    python sci_goodlaw.py ik     status|plan|run|confirm [--kind meta --tids 1,2 --run-cap 1 --approved-rs 0.04 --plan-id ID]   # the Indian Kanoon API: dry run, caps, ledger (IK_PLAN.md)
    python sci_goodlaw.py eval   --corpus corpus.sqlite --half dev           # agreement with the reporter's citator (development half)
    python sci_goodlaw.py eval   --corpus corpus.sqlite --half dev --gold modern [--production]   # the same against the 2017-2023 case-law tables
    python sci_goodlaw.py register-build [--force]                           # the Overruled Register from the two outside lists (REGISTER.md); refuses to overwrite a reviewed register
    python sci_goodlaw.py register-check "Mohan Lal v State of Punjab" --year 2018 [--cite "(2018) 17 SCC 627"]   # what the register says about one case
    python sci_goodlaw.py register-scan  --file answer.txt                   # the answer guard on a finished answer (lock c)
    python sci_goodlaw.py register-flags --cards cards/currency_cards.json   # take the checker's ADVERSE_SIGNAL / QUESTIONED cards into the flag ledger
    python sci_goodlaw.py register-sweep --corpus corpus.sqlite              # find overrulings the register does not hold (proposals only)
    python sci_goodlaw.py register-exam build --out register_exam/ | score --answers answers.jsonl   # the trap-question exam (needs the assistant to produce the answers)
    python sci_goodlaw.py register-export-site --out DIR                     # the dependency-free bundle for the Recourse owner (REGISTER_SITE_PATCH.md)
    python sci_goodlaw.py register-review-queue --out review_queue.csv       # the weekly sheet (every 7 days)
    python sci_goodlaw.py register-review --sheet review_queue.csv --reviewer "Mr. Advocate"   # record the filled sheet

`build` reads the two data branches into one searchable store (about 10 minutes, 2 GB) and indexes the citations in it. `check` writes a JSON bundle and a
Markdown report for one case: who cites it, what they do with it (with the exact sentences), what became of the statute sections it cites, a triage label
and a statement of what the collection can and cannot see. No code here decides that a case is good law; see goodlaw/report.py.
"""
import argparse
import datetime
import json
import math
import os
import re
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
            json.dump({k: v for k, v in bundle.items() if not k.startswith("_")}, fh, indent=1, ensure_ascii=False)
        with open(base + ".md", "w", encoding="utf-8") as fh:
            fh.write(md)
        log(f"wrote {base}.json and .md")
    return bundle, md


HERE = os.path.dirname(os.path.abspath(__file__))


def _finite_rupees(text):
    v = float(text)
    if not math.isfinite(v) or v < 0:
        raise argparse.ArgumentTypeError(f"{text!r} is not a finite, non-negative number of rupees")
    return v


def _plain(text):
    """Text that came from the network, safe to print: control characters (including terminal escapes) become '?'."""
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", "?", str(text))


def run_ik(a):
    """status: what has been spent. plan: the dry run (no key needed, nothing sent). run: only with --run-cap, an --approved-rs equal to the plan's cost and the plan's --plan-id.
    confirm: record the price per call that the dashboard showed after the single probe of a kind of call. The ledger is fixed (goodlaw/data/ik_ledger.jsonl) and must exist."""
    from goodlaw import ik as IK
    client = IK.Client(cache_dir=a.cache, require_ledger=True)
    try:
        if a.action == "status":
            print(json.dumps(client.status(), indent=1))
            return 0
        if a.action == "confirm":
            if not (a.shape and a.price is not None and a.note):
                print("confirm needs --shape, --price (rupees per call, as the dashboard showed it) and --note (the balance before and after)", file=sys.stderr)
                return 2
            client.confirm_price(a.shape, a.price, a.note)
            print(f"recorded: {a.shape} costs Rs {a.price:.2f} per call")
            return 0
    except IK.IKError as e:
        print(f"{type(e).__name__}: {_plain(e)}", file=sys.stderr)
        return 1
    tids = [t.strip() for t in (a.tids or "").split(",") if t.strip()]
    if a.tids_file:
        with open(a.tids_file, encoding="utf-8") as fh:
            tids += [ln.split("#")[0].strip() for ln in fh if ln.split("#")[0].strip()]
    try:
        extra = {}
        for kv in a.extra or []:
            k, sep, v = kv.partition("=")
            if not sep or k in extra:
                raise ValueError(f"--extra needs name=number, once per name; got {kv!r}")
            extra[k] = int(v)
        if a.pairs_file:
            if a.kind != "fragment" or tids or a.query or a.query_template:
                raise ValueError("--pairs-file is for --kind fragment only, and replaces --tids, --tids-file, --query and --query-template")
            calls = []
            with open(a.pairs_file, encoding="utf-8") as fh:
                for n, ln in enumerate(fh, 1):
                    ln = ln.split("#")[0].strip()
                    if not ln:
                        continue
                    tid, sep, term = (x.strip() for x in ln.partition("|"))
                    if not sep or not term:
                        raise ValueError(f"{a.pairs_file} line {n}: expected 'id | search term'")
                    calls.append(IK.Call("fragment", tid=tid, query=term, extra=extra))
            if not calls:
                raise ValueError(f"{a.pairs_file} has no lines")
        elif "tid" in IK.KINDS[a.kind]["needs"]:
            if not tids:
                raise ValueError("no ids given (--tids or --tids-file)")
            calls = [IK.Call(a.kind, tid=t, query=a.query or "", page=a.page, extra=extra) for t in tids]
        elif a.kind == "search" and a.query_template:
            if a.query:
                raise ValueError("give --query or --query-template, not both")
            if a.query_template.count("{tid}") != 1 or "{" in a.query_template.replace("{tid}", "") or "}" in a.query_template.replace("{tid}", ""):
                raise ValueError("--query-template must contain {tid} exactly once and no other braces")
            if not tids:
                raise ValueError("no ids given (--tids or --tids-file)")
            bad = [t for t in tids if not IK.TID_RE.fullmatch(t)]
            if bad:
                raise ValueError(f"not an Indian Kanoon id: {bad[0]!r}")
            calls = [IK.Call("search", query=a.query_template.replace("{tid}", t), page=a.page, extra=extra) for t in tids]
        else:
            if tids:
                raise ValueError(f"{a.kind} takes no ids")
            calls = [IK.Call(a.kind, query=a.query or "", page=a.page, extra=extra)]
    except ValueError as e:
        print(f"bad call: {e}", file=sys.stderr)
        return 2
    if a.run_cap is None:
        print("--run-cap (rupees) is required for plan and run", file=sys.stderr)
        return 2
    try:
        if a.action == "plan":
            pl = client.plan(calls, a.run_cap, a.retry_failed, a.refetch)
            print(pl.text())
            return 1 if pl.problems else 0
        results = client.run(calls, a.run_cap, a.approved_rs, a.plan_id, a.retry_failed, a.refetch)
    except IK.IKError as e:
        print(f"{type(e).__name__}: {_plain(e)}", file=sys.stderr)
        return 1
    for c in calls:
        rec = results.get(c.key())
        if rec and c.kind == "meta":
            try:
                m = IK.parse_meta(rec["response"])
                print(f"{c.tid}  {_plain(m['date'])}  cited by {m['numcitedby']:4d}  {_plain(m['doctype'])}  {_plain(m['title'])[:70]}")
            except IK.IKBadResponse as e:
                print(f"{c.tid}: the saved answer is not readable as metadata: {_plain(e)}", file=sys.stderr)
        elif rec:
            print(f"{c.label()}: saved in {client._cache_path(c)}")
    return 0


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
    records_path = os.path.join(a.out, "reader_verdicts.jsonl")
    if a.cmd == "reader-import":
        batch_path = os.path.join(a.out, "reader_batch.jsonl")
        if not os.path.exists(batch_path):
            print(f"no batch to answer: {batch_path} does not exist (run `cards` first)", file=sys.stderr)
            return 2
        recorded, problems = CD.import_reader_verdicts(a.verdicts, batch_path, records_path, a.reader, a.today or datetime.date.today().isoformat())
        for p in problems:
            print("PROBLEM:", p, file=sys.stderr)
        print(f"{recorded} verdict(s) recorded in {records_path}" + (f"; {len(problems)} skipped" if problems else "") + "; run `cards` again to put them on the cards")
        return 1 if problems else 0
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
    records = CD.load_reader_records(records_path)
    cards, reports = CD.build_all(a.corpus, snap["cases"], overrides, today=a.today, workers=a.workers, reader_records=records)
    items_by_case = CD.split_reader_items(cards)
    n_batch = CD.write_reader_batch(CD.pending_items(cards, items_by_case, records), a.out)
    CD.attach_reviews(cards, CD.load_reviews(reviews_path))
    doc = CD.write_cards(cards, reports, a.out, snap.get("snapshot"))
    changes = CD.compare(old_cards, cards)
    today = cards[0]["provenance"]["generated"]
    CD.write_changes(changes, os.path.join(a.out, "CHANGES.md"), today, first_run=old_cards is None)
    n_sheet = CD.write_review_sheet(cards, sheet, CD.load_readings(os.path.join(a.out, "preliminary_readings.json")))
    CD.write_match_check(cards, os.path.join(a.out, "MATCH_CHECK.csv"))
    print(f"{len(cards)} cards written to {a.out}: {doc['counts']}")
    print(f"{n_sheet} case(s) in the review sheet; {len([c for c in changes if c['worse']])} change(s) since the last run that need a look (see CHANGES.md)")
    n_items = sum(len(v) for v in items_by_case.values())
    print(f"second reader: {n_items} judgment(s) worth reading across the cases, {n_items - n_batch} already read, {n_batch} in {os.path.join(a.out, 'reader_batch.jsonl')}")
    return 0


def run_register(a):
    """The Overruled Register commands (goodlaw/register*.py, REGISTER.md)."""
    from goodlaw import register as R
    from goodlaw import register_build as RB
    from goodlaw import register_guard as G
    from goodlaw import register_review as RV
    today = getattr(a, "today", None) or datetime.date.today().isoformat()
    path = getattr(a, "register", None) or R.DEFAULT_PATH
    if a.cmd == "register-build":
        if os.path.exists(path) and not a.force:
            old = R.Register.load(path)
            touched = [r["id"] for r in old.rows if len(r.get("history", [])) > 1 or r.get("review") or r["trust"] in ("reviewer_confirmed", "rejected")]
            if touched:
                print(f"{path} holds {len(touched)} row(s) a person has reviewed (for example {touched[0]}); rebuilding would lose their decisions. Use --force only to start over.", file=sys.stderr)
                return 2
        RB.build(a.pdf, path, built_on=today)
        return 0
    reg = R.Register.load(path)
    if a.cmd == "register-check":
        hits = reg.lookup_case(a.name, a.year, a.cite)
        if not hits:
            print("not in the register (no row matches by citation, or by both names and a year)")
        for h in hits:
            r = h["row"]
            print(f"{h['strength']:6} {h['how']:9} {r['id']} [{r['trust']}] {reg.clause(r) or '(unchecked: no wording)'}")
        return 0
    if a.cmd == "register-scan":
        res = G.guard_answer(reg, open(a.file, encoding="utf-8").read())
        print(json.dumps(res, indent=1, ensure_ascii=False))
        return 0
    if a.cmd == "register-exam":
        from goodlaw import register_exam as EX
        if a.action == "build":
            qs, key = EX.write_exam(reg, a.out, a.seed)
            kinds = {}
            for k in key.values():
                kinds[k["kind"]] = kinds.get(k["kind"], 0) + 1
            print(f"{len(qs)} questions {kinds} -> {a.out}")
            return 0
        key = json.load(open(os.path.join(a.out, "key.json"), encoding="utf-8"))
        table, res = EX.score(reg, EX.read_answers(a.answers), key)
        print(json.dumps(table))
        for qid, v in sorted(res.items()):
            if v in ("unmatched", "guard_note", "no_answer"):
                print(f"  {qid} {v}: {key[qid]['case']}")
        return 0 if table["passes"] else 1
    if a.cmd == "register-export-site":
        import shutil
        os.makedirs(a.out, exist_ok=True)
        for f_ in ("cites.py", "register.py", "register_guard.py"):
            shutil.copy(os.path.join(HERE, "goodlaw", f_), os.path.join(a.out, f_))
        open(os.path.join(a.out, "__init__.py"), "w", encoding="utf-8").write('"""The Overruled Register bundle (exported from recourse-sci-pool; see REGISTER.md there)."""\nfrom . import register, register_guard\n\n\ndef load(path=None):\n    import os\n    return register.Register.load(path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "register_slim.json"))\n')
        doc = {"schema": R.SCHEMA, **{k: v for k, v in reg.meta.items()}, "rows": R.slim(reg.rows), "slim": True}
        with open(os.path.join(a.out, "register_slim.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
        print(f"bundle in {a.out}: {len(doc['rows'])} rows, {os.path.getsize(os.path.join(a.out, 'register_slim.json')) // 1024} KB")
        return 0
    flags_path = a.flags_file if getattr(a, "flags_file", None) else RV.FLAGS_PATH
    props_path = a.proposals_file if getattr(a, "proposals_file", None) else RV.PROPOSALS_PATH
    if a.cmd == "register-flags":
        flags = RV.load_flags(flags_path)
        new, quiet = RV.flags_from_cards(json.load(open(a.cards, encoding="utf-8")), flags, today)
        RV._save(flags_path, flags)
        print(f"{len(new)} new flag(s) {new}; {len(quiet)} open flag(s) the checker no longer raises (they stay open until a person clears them) {quiet}")
        return 0
    if a.cmd == "register-sweep":
        from goodlaw import register_sweep as SW
        corpus = K.Corpus(a.corpus)
        found = SW.sweep(corpus, reg, a.min_year, a.min_bench)
        doc = RV.load_proposals(props_path)
        have = {(p["doc_key"], p.get("overruled_name"), p["evidence"][:80]): p for p in doc["proposals"]}
        added = 0
        for f in found:
            key = (f["doc_key"], f.get("overruled_name"), f["evidence"][:80])
            if key in have:
                have[key]["already_in_register"] = f["already_in_register"]
                continue
            n = 1 + max([int(p["id"].split("-")[1]) for p in doc["proposals"]] or [0])
            doc["proposals"].append({"id": f"P-{n:04d}", "state": "open", "next_due": None, "first_seen": today, "history": [{"on": today, "by": "register-sweep", "event": "found"}], **f})
            added += 1
        RV._save(props_path, doc)
        print(f"{len(found)} find(s), {added} new proposal(s), {sum(1 for p in doc['proposals'] if p['state'] == 'open' and not p.get('already_in_register'))} open in all -> {props_path}")
        return 0
    flags = RV.load_flags(flags_path)
    props = RV.load_proposals(props_path)
    if a.cmd == "register-review-queue":
        items = RV.build_queue(reg, flags, props, today, a.proposal_limit, a.match_limit, a.limit)
        RV.write_queue(items, a.out)
        kinds = {}
        for it in items:
            kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
        print(f"{len(items)} item(s) for the review of {today}: {kinds} -> {a.out}")
        return 0
    if a.cmd == "register-review":
        rows = reg.rows
        res = RV.apply_decisions(rows, flags, props, a.sheet, a.reviewer, today)
        meta = {k: v for k, v in reg.meta.items()}
        R.save(rows, meta, path)
        RV._save(flags_path, flags)
        RV._save(props_path, props)
        print(f"{len(res['applied'])} decision(s) recorded; {len(res['errors'])} not applied")
        for e in res["errors"]:
            print("  NOT APPLIED", e, file=sys.stderr)
        return 0 if not res["errors"] else 1
    return 1


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
    ik_ = sub.add_parser("ik", help="the Indian Kanoon API: `status`, `plan` (dry run, free), `run` (spends: needs --run-cap, --approved-rs and --plan-id from the plan) and `confirm` (record the dashboard price of a kind of call)")
    ik_.add_argument("action", choices=["status", "plan", "run", "confirm"])
    ik_.add_argument("--kind", choices=["meta", "doc", "fragment", "search"], default="meta")
    ik_.add_argument("--tids", help="comma-separated Indian Kanoon document ids")
    ik_.add_argument("--tids-file", help="one id per line ('#' starts a comment)")
    ik_.add_argument("--query", help="fragment and search: the query")
    ik_.add_argument("--page", type=int, default=0, help="search: the page, from 0")
    ik_.add_argument("--pairs-file", help="fragment: one call per line, 'id | search term' ('#' starts a comment); the passages around the term in that judgment")
    ik_.add_argument("--query-template", help="search with --tids/--tids-file: one search per id, the query being this text with {tid} replaced, for example 'citedby:{tid} doctypes:supremecourt'")
    ik_.add_argument("--extra", action="append", help="doc: an extra parameter, name=number (for example maxcitedby=10); each such shape needs its own single probe")
    ik_.add_argument("--run-cap", type=_finite_rupees, help="the most this run may spend, in rupees")
    ik_.add_argument("--approved-rs", type=_finite_rupees, help="run: the plan's cost, as read from `plan`; anything else is refused")
    ik_.add_argument("--plan-id", help="run: the plan id printed by `plan`; an approval is for that list of calls only")
    ik_.add_argument("--retry-failed", action="store_true", help="allow a call that failed before (read the rejected answer in the cache first)")
    ik_.add_argument("--refetch", action="store_true", help="allow paying again for a call whose answer is not in the cache (the cache does not survive a new session)")
    ik_.add_argument("--shape", help="confirm: the shape, for example meta or doc+maxcitedby=10")
    ik_.add_argument("--price", type=_finite_rupees, help="confirm: the price per call the dashboard showed")
    ik_.add_argument("--note", help="confirm: the balance before and after, in words")
    ik_.add_argument("--cache", default=os.path.join(HERE, "ik_cache"))
    ri = sub.add_parser("reader-import", help="check a reader's verdicts against cards/reader_batch.jsonl and store the valid ones; then run `cards` again")
    ri.add_argument("--verdicts", required=True, help="one JSON object per line: id, treatment, quote, note")
    ri.add_argument("--reader", default="a model session reading the passages", help="who read them, recorded with each verdict")
    ri.add_argument("--out", default=os.path.join(HERE, "cards"))
    ri.add_argument("--today")
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
    re_ = sub.add_parser("reader-eval", help="the second reader on the tuning halves: 'build' writes a blind batch and its key, 'score' compares a reader's verdicts with the key")
    re_.add_argument("action", choices=["build", "score"])
    re_.add_argument("--out", required=True, help="the folder for batch.jsonl, key.json and INSTRUCTIONS.txt")
    re_.add_argument("--verdicts", help="score: the reader's verdicts, one JSON object per line")
    re_.add_argument("--seed", type=int, default=11)
    re_.add_argument("--per-cell", type=int, default=24)
    re_.add_argument("--workers", type=int, default=4)
    rb = sub.add_parser("register-build", help="build the Overruled Register from the two outside lists")
    rb.add_argument("--pdf", default=os.path.join(HERE, "inbox", "520254941-List-of-Overruled-Cases.pdf"))
    rb.add_argument("--force", action="store_true", help="overwrite even a register a person has reviewed (their decisions are lost)")
    rk = sub.add_parser("register-check")
    rk.add_argument("name")
    rk.add_argument("--year")
    rk.add_argument("--cite")
    rs = sub.add_parser("register-scan")
    rs.add_argument("--file", required=True)
    rf = sub.add_parser("register-flags")
    rf.add_argument("--cards", default=os.path.join(HERE, "cards", "currency_cards.json"))
    rw = sub.add_parser("register-sweep")
    rw.add_argument("--min-year", type=int, default=2000)
    rw.add_argument("--min-bench", type=int, default=3)
    rq = sub.add_parser("register-review-queue")
    rq.add_argument("--out", required=True)
    rq.add_argument("--proposal-limit", type=int, default=20)
    rq.add_argument("--match-limit", type=int, default=20)
    rq.add_argument("--limit", type=int, default=60, help="the most items on one week's sheet (flags are never cut)")
    rx = sub.add_parser("register-exam")
    rx.add_argument("action", choices=["build", "score"])
    rx.add_argument("--out", default=os.path.join(HERE, "register_exam"))
    rx.add_argument("--answers")
    rx.add_argument("--seed", type=int, default=7)
    re2 = sub.add_parser("register-export-site")
    re2.add_argument("--out", required=True)
    rr = sub.add_parser("register-review")
    rr.add_argument("--sheet", required=True)
    rr.add_argument("--reviewer", default="Mr. Advocate")
    for p in (rb, rk, rs, rf, rw, rq, rr, rx, re2):
        p.add_argument("--register", help="register file (default goodlaw/data/register/register.json)")
        p.add_argument("--today", help="date to record (default: today)")
        p.add_argument("--flags-file")
        p.add_argument("--proposals-file")
    for p in (f, c, bt, kn, ev, cd, re_, rw):
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
    if a.cmd.startswith("register"):
        return run_register(a)
    if a.cmd == "ik":
        return run_ik(a)
    if a.cmd in ("cards", "cards-review", "card", "reader-import"):
        return run_cards(a)
    corpus = K.Corpus(a.corpus)
    if a.cmd == "reader-eval":
        from goodlaw import reader_eval as RE
        if a.action == "build":
            RE.build(corpus, a.corpus, a.out, a.seed, a.per_cell, a.workers)
            return 0
        if not a.verdicts:
            print("score needs --verdicts", file=sys.stderr)
            return 2
        table, _ = RE.score(a.out, a.verdicts)
        print(json.dumps(table, indent=1))
        return 0
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
        print(json.dumps({k: v for k, v in bundle.items() if not k.startswith("_")}, indent=1, ensure_ascii=False) if a.json else md)
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
