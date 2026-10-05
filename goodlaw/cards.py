"""Currency cards: the checker's report for every case Recourse can show, computed ahead of time and saved, so that answering a question is a lookup.

One card per library case (goodlaw.library). A card says what the checker found, in two voices that are kept apart:

  user_facing_note  one or two plain sentences, safe to show a user or to hand to the answer-writing model; None unless the checker found something to warn about
                    (ADVERSE_SIGNAL, QUESTIONED). Never says a case "is good law": silence in what we hold is not that.
  evidence          the quoted sentences, the judgments they come from, bench sizes, cues and caveats, for the person who reviews the flagged cases.

This follows Recourse's own convention (citation_currency.py): a plain `user_facing_note` for the user, an audit trail for the developer, no note at all for a case with no
known adverse treatment. A card is a proposal for a person to confirm, not a decision: `review` carries a person's verdict, valid only while the card's `fingerprint` (its
status and its evidence) is unchanged. Recourse's own human-verified records take precedence over any card.

goodlaw/cardreader.py is the other half: a stdlib-only reader (with the wording rules) that Recourse can copy.
"""
import collections
import csv
import datetime
import hashlib
import json
import os
import re
import subprocess

from . import cites as C
from . import library as LB
from . import mentions as M
from . import report as R
from . import treatment as T

SCHEMA = "goodlaw-card-1"
CHECKED = ("ADVERSE_SIGNAL", "QUESTIONED", "NO_ADVERSE_FOUND", "INSUFFICIENT")
UNCHECKED = ("NOT_IN_COLLECTION", "NOT_CHECKABLE_HIGH_COURT", "AMBIGUOUS_MATCH")
VERDICTS = ("CONFIRMED_ADVERSE", "FALSE_ALARM", "NEEDS_RESEARCH")
SEVERITY = {"ADVERSE_SIGNAL": 3, "QUESTIONED": 2, "NO_ADVERSE_FOUND": 1, "INSUFFICIENT": 1, "NOT_IN_COLLECTION": 0, "NOT_CHECKABLE_HIGH_COURT": 0, "AMBIGUOUS_MATCH": 0}
LABEL_TEXT = "pattern-rule reading of Supreme Court texts; not lawyer-validated"
QUOTE_CAP = 700

UNCHECKED_TEXT = {
    "NOT_IN_COLLECTION": "This case is not in our collection of Supreme Court judgments, so what later judgments did with it was not checked.",
    "NOT_CHECKABLE_HIGH_COURT": "This is a High Court decision; our collection holds only Supreme Court judgments, so what later judgments did with it was not checked.",
    "AMBIGUOUS_MATCH": "We could not tell which judgment in our collection this case is, so what later judgments did with it was not checked.",
}


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")[:90] or "case"


def _cap(text):
    text = text or ""
    return (text if len(text) <= QUOTE_CAP else text[:QUOTE_CAP].rsplit(" ", 1)[0] + " ..."), len(text) > QUOTE_CAP


def _evidence(m, group):
    quote, cut = _cap(m.get("sentence"))
    return {"group": group, "doc_key": m.get("doc_key"), "title": m.get("title"), "date": m.get("date"), "year": m.get("year"), "bench_size": m.get("bench_size"),
            "bench_relation": m.get("bench_relation"), "label": m.get("label"), "cue": m.get("cue"), "speaker": m.get("speaker"), "confidence": m.get("confidence"),
            "hedged": m.get("hedged"), "binding": m.get("binding"), "anaphoric": m.get("anaphoric", False), "kind": m.get("kind"), "tier": m.get("tier"),
            "quote": quote, "quote_truncated": cut, "quote_verified": m.get("quote_verified"), "reasons": m.get("why_not_a_clean_overruling") or []}


def _citator_evidence(row, group):
    cc = row.get("citing_case") or {}
    return {"group": group, "doc_key": cc.get("doc_key"), "title": cc.get("title"), "date": cc.get("date"), "year": int(cc["date"][:4]) if cc.get("date") else None, "bench_size": None,
            "bench_relation": "unknown", "label": "OVERRULES" if row.get("code") in ("O", "HO") else "DISAGREES", "cue": f"reporter's citator code {row.get('code')}", "speaker": "the law reporter's citator",
            "confidence": "high", "hedged": False, "binding": "strong", "anaphoric": False, "kind": f"reporter's citator: {row.get('meaning')}", "tier": "citator",
            "quote": f"{row.get('code')} ({row.get('meaning')}): {row.get('cite')}" + (f" paras {row['paras']}" if row.get("paras") else ""), "quote_truncated": False, "quote_verified": None, "reasons": []}


def _date_key(e):
    return e.get("date") or f"{e.get('year') or 0}-12-31"


def select_evidence(summary):
    """The evidence a reviewer needs, most important first: strong signals, the reporter's citator, possible signals that are not weak, the legislature's response, and a few
    weak ones that were set aside (so that a quiet label does not hide them)."""
    out = []
    strong = sorted(summary.get("adverse_strong") or [], key=_date_key, reverse=True)
    out += [_evidence(m, "strong") for m in strong[:3]]
    out += [_citator_evidence(r, "citator") for r in ((summary.get("citator_adverse_overruled") or []) + (summary.get("citator_adverse_other") or []))[:3]]
    possible = sorted([m for m in (summary.get("adverse_possible") or []) if not m.get("weak")], key=lambda m: (T.STRENGTH.get(m.get("label"), -1), _date_key(m)), reverse=True)
    out += [_evidence(m, "possible") for m in possible[:3]]
    out += [_evidence(m, "legislative") for m in sorted(summary.get("legislative") or [], key=_date_key, reverse=True)[:2]]
    weak = [m for m in (summary.get("adverse_possible") or []) if m.get("weak")]
    weak = sorted(weak, key=lambda m: (T.STRENGTH.get(m.get("label"), -1), _date_key(m)), reverse=True)
    out += [_evidence(m, "weak") for m in weak[:3]]
    return out


def _bench_words(n):
    return {3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 9: "nine", 11: "eleven", 13: "thirteen"}.get(n)


def user_note(status, evidence):
    """The plain sentence(s) for a user, or None. Built only from what the evidence shows; it says 'appears to' because a rule read it, and never says 'good law'."""
    strong = [e for e in evidence if e["group"] in ("strong", "citator")]
    if status == "ADVERSE_SIGNAL":
        judgments = [e for e in strong if e["group"] == "strong"]
        if judgments:
            best = max(judgments, key=_date_key)
            n = best.get("bench_size")
            who = f"A later {_bench_words(n)}-judge bench of the Supreme Court" if n and n >= 3 and _bench_words(n) else "A later Supreme Court judgment"
            plural = len(judgments) > 1 and len({e["doc_key"] for e in judgments}) > 1
            if plural:
                who, verb = "Later Supreme Court judgments", "appear"
                when = f" (the latest in {best['year']})" if best.get("year") else ""
            else:
                verb = "appears"
                when = f" ({best['year']})" if best.get("year") else ""
            return f"{who}{when} {verb} to overrule or reject this case, in whole or in part, so check it before relying on this case."
        return "The law reporters' own note marks this case as overruled by a later Supreme Court judgment, so check it before relying on this case."
    if status == "QUESTIONED":
        labels = {e["label"] for e in evidence if e["group"] in ("possible", "strong", "citator", "legislative")}
        parts = []
        if "OVERRULES" in labels:
            parts.append("may have overruled it")
        if "DISAGREES" in labels:
            parts.append("disagreed with it")
        if "DOUBTS_REFERS" in labels:
            parts.append("doubted it or referred it to a larger bench")
        legislative = "LEGISLATIVE" in labels
        if parts:
            joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
            return f"Later Supreme Court judgments have {joined}" + (", and the legislature has since responded to it" if legislative else "") + "; its reach may be narrower than it first appears."
        if legislative:
            return "The legislature has since responded to this case, so check whether the law has been changed."
        return "Later Supreme Court judgments have questioned this case; its reach may be narrower than it first appears."
    return None


STATUTE_MIN_CITED = 3      # a section cited once or twice is usually incidental (a precedent's own facts, a passing reference); the note is for sections the judgment discusses


def statute_note(statute_flag, dimension):
    """A mechanical note when the judgment repeatedly discusses an IPC or CrPC section that the 2023 codes renumbered, repealed or changed; None otherwise. It is about the
    section's number, not the doctrine. Recourse's curated records (SUPERSEDED_BY_STATUTE) are the authority on this and take precedence."""
    if not statute_flag:
        return None
    rows = [r for r in dimension if r.get("status") in ("renumbered", "renumbered_changed", "no_counterpart", "replaced_not_mapped") and (r.get("count") or 0) >= STATUTE_MIN_CITED]
    rows.sort(key=lambda r: -(r.get("count") or 0))
    bits = []
    for r in rows[:2]:
        succ = ", ".join(f"{s['act']} section {s['section']}" for s in r.get("successors") or [])
        if r["status"] in ("renumbered", "renumbered_changed") and succ:
            bits.append(f"{r['act']} section {r['section']} (renumbered as {succ}" + ("; the table also marks a change in content)" if r["status"] == "renumbered_changed" else ")"))
        else:
            bits.append(f"{r['act']} section {r['section']} ({r.get('note') or 'changed in the 2023 codes'})")
    if not bits:
        return None
    return "The judgment repeatedly discusses " + " and ".join(bits) + ". That is a change of number, not a finding that the ruling no longer applies."


def fingerprint(card):
    """A short hash of what a reviewer judged: the status and each piece of evidence (which judgment, which reading). It changes when the checker's findings change."""
    sig = sorted(f"{e['group']}|{e.get('doc_key')}|{e.get('label')}|{(e.get('cue') or '').lower()}" for e in card.get("evidence") or [])
    return hashlib.sha1(("|".join([card["status"]] + sig)).encode()).hexdigest()[:12]


def _base_card(case, match, today, commit, corpus_info):
    return {"schema": SCHEMA,
            "case": {"name": case["case_name"], "citation": case.get("citation"), "year": case.get("year"), "court_class": case.get("court_class"), "court": case.get("court"),
                     "pools": case.get("pools"), "case_key": case.get("case_key"), "topic": case.get("topic"), "citation_keys": [k for k, _, _ in C.find_cites(case.get("citation") or "")],
                     "recourse_curated": case.get("recourse_currency") or []},
            "corpus": {"doc_key": None, "title": None, "date": None, "year": None, "bench_size": None, "source": None, "cites": [], "match": {"method": match.get("method"), "confidence": match.get("confidence"),
                       "note": match.get("note"), "candidates": match.get("candidates")}},
            "status": None, "statute_flag": None, "user_facing_note": None, "statute_note": None, "evidence": [], "support": None, "coverage": None, "statute_dimension": [],
            "provenance": {"generated": today, "checker_commit": commit, "label": LABEL_TEXT, "evaluation": "goodlaw/EVALUATION.md", "corpus": corpus_info},
            "fingerprint": None, "review": None, "changed_since_last_run": None, "report_file": None}


def unchecked_card(case, match, today, commit, corpus_info):
    card = _base_card(case, match, today, commit, corpus_info)
    card["status"] = match["status"] if match["status"] in UNCHECKED else "NOT_IN_COLLECTION"
    card["internal_note"] = UNCHECKED_TEXT[card["status"]] + (f" ({match['note']})" if match.get("note") else "")
    card["fingerprint"] = fingerprint(card)
    return card


def card_from_bundle(case, match, doc, bundle, today, commit, corpus_info, report_file=None):
    card = _base_card(case, match, today, commit, corpus_info)
    s = bundle["summary"]
    card["corpus"].update(doc_key=doc["doc_key"], title=doc["title"], date=doc.get("date"), year=doc.get("year"), bench_size=doc.get("bench_size"), source=doc.get("source"),
                          cites=list(doc.get("cites") or []))
    card["status"] = bundle["triage"]
    card["statute_flag"] = bundle["statute_flag"]
    card["evidence"] = select_evidence(s)
    card["user_facing_note"] = user_note(card["status"], card["evidence"])
    card["statute_note"] = statute_note(bundle["statute_flag"], bundle["statute_dimension"])
    ct = s.get("case_law_table") or {}
    card["support"] = {"citing_judgments": s["citing_judgments"], "latest_citing_year": s["latest_citing_year"], "citing_in_last_10_years": s["citing_in_last_10_years"],
                       "by_treatment": s["by_treatment"], "weak_signals_set_aside": s.get("weak_signals_set_aside", 0),
                       "recent_approving": [{"title": m["title"], "date": m["date"], "cue": m["cue"], "quote": _cap(m["sentence"])[0]} for m in (bundle.get("recent_approving") or [])[:3]],
                       "case_law_table": {"judgments_with_a_row": ct.get("judgments_with_a_row", 0), "by_what_the_reporter_marked": ct.get("by_what_the_reporter_marked", {}),
                                          "recent_relied_on": (ct.get("recent_relied_on") or [])[:3]}}
    cv = bundle["coverage"]
    card["coverage"] = {"collection_runs_to": cv["collection_runs_to"], "share_of_later_judgments_we_hold": cv["share_of_later_judgments_we_hold"], "later_years": cv["later_years"], "note": cv["note"]}
    card["statute_dimension"] = bundle["statute_dimension"]
    card["internal_note"] = {
        "ADVERSE_SIGNAL": "A later judgment appears to overrule or reject this case; read the evidence before relying on it.",
        "QUESTIONED": "Later judgments disagree with, doubt, limit or refer this case, or the legislature responded to it.",
        "NO_ADVERSE_FOUND": f"No overruling or doubt found in the {s['citing_judgments']} later judgments we hold that cite it (collection runs to {cv['collection_runs_to']}; we hold about "
                            f"{int((cv['share_of_later_judgments_we_hold'] or 0) * 100)}% of what Indian Kanoon lists after it). This is silence in what we hold, not a finding about the law.",
        "INSUFFICIENT": f"Only {s['citing_judgments']} later judgments in our collection cite this case; too few to say anything.",
    }[card["status"]]
    card["report_file"] = report_file
    card["fingerprint"] = fingerprint(card)
    return card


def code_version(path=None):
    """The git commit of the checker's code (with '+uncommitted changes' when the code differs from it), or None when it is not a git checkout."""
    cwd = path or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            return None
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "--", "goodlaw", "sci_goodlaw.py"], cwd=cwd, capture_output=True, text=True, timeout=30)
        return out.stdout.strip() + (" +uncommitted changes" if dirty.stdout.strip() else "")
    except Exception:
        return None


def corpus_fingerprint(corpus):
    rows = dict(corpus.con.execute("SELECT source, COUNT(*) FROM docs WHERE dup_of IS NULL GROUP BY source").fetchall())
    last = corpus.con.execute("SELECT MAX(date) FROM docs WHERE dup_of IS NULL").fetchone()[0]
    return {"judgments": rows, "latest_judgment_date": last}


# ---------------------------------------------------------------- building every card
_POOL = {}


def _init(path):
    from . import corpus as K
    _POOL["corpus"] = K.Corpus(path)


def _work(args):
    case, match, today, commit, info = args
    corpus = _POOL["corpus"]
    doc = corpus.get(match["doc_key"], with_text=False)
    target = M.Target.from_doc(doc)
    for k, _, _ in C.find_cites(case.get("citation") or ""):      # the library's own citation is a citation of the case
        if k not in target.cites:
            target.cites.append(k)
    bundle = R.build_bundle(corpus, target, doc, today=today)
    name = slug(case["case_name"])
    card = card_from_bundle(case, match, doc, bundle, today, commit, info, report_file=f"reports/{name}.md")
    return card, R.render_markdown(bundle)


def build_all(corpus_path, library_cases, overrides=None, today=None, workers=4, log=print):
    """-> ([card, ...], {slug: markdown report}). Matches every library case to a judgment (goodlaw.library), then runs the checker on each matched one in parallel."""
    from multiprocessing import Pool
    from . import corpus as K
    today = today or datetime.date.today().isoformat()
    corpus = K.Corpus(corpus_path)
    commit, info = code_version(), corpus_fingerprint(corpus)
    cards, jobs = {}, []
    for case in library_cases:
        match = LB.match_case(corpus, case, overrides)
        if match["status"] == "MATCHED":
            jobs.append((case, match, today, commit, info))
        else:
            cards[case["case_name"]] = unchecked_card(case, match, today, commit, info)
    log(f"{len(jobs)} cases matched to a judgment, {len(cards)} not checkable; running the checker on {len(jobs)}")
    reports = {}
    if jobs:
        with Pool(workers, initializer=_init, initargs=(corpus_path,)) as pool:
            for n, (card, md) in enumerate(pool.imap_unordered(_work, jobs), 1):
                cards[card["case"]["name"]] = card
                reports[slug(card["case"]["name"])] = md
                if n % 10 == 0:
                    log(f"  {n}/{len(jobs)}")
    ordered = [cards[c["case_name"]] for c in library_cases]
    return ordered, reports


# ---------------------------------------------------------------- reviews, changes, sheets
def load_reviews(path):
    if path and os.path.exists(path):
        return json.load(open(path, encoding="utf-8")).get("reviews", [])
    return []


def attach_reviews(cards, reviews):
    """The latest review of each case goes on its card, marked `current` only if the card's fingerprint is the one the reviewer saw."""
    latest = {}
    for r in reviews:
        latest[r["case_name"]] = r
    for card in cards:
        r = latest.get(card["case"]["name"])
        card["review"] = None if not r else dict(r, current=(r.get("fingerprint") == card["fingerprint"]))
    return cards


def compare(old_cards, new_cards):
    """What changed since the last run: [{case, kind, detail, worse}], worse ones first. A status that moved towards a warning, evidence that appeared, a match that moved, a review
    that went stale."""
    old = {c["case"]["name"]: c for c in old_cards or []}
    out = []
    for c in new_cards:
        name = c["case"]["name"]
        o = old.get(name)
        if o is None:
            out.append({"case": name, "kind": "new case", "detail": c["status"], "worse": SEVERITY[c["status"]] >= 2})
            continue
        if o["status"] != c["status"]:
            out.append({"case": name, "kind": "status changed", "detail": f"{o['status']} -> {c['status']}", "worse": SEVERITY[c["status"]] > SEVERITY[o["status"]]})
        if (o["corpus"]["doc_key"] or None) != (c["corpus"]["doc_key"] or None):
            out.append({"case": name, "kind": "matched judgment changed", "detail": f"{o['corpus']['doc_key']} -> {c['corpus']['doc_key']}", "worse": True})
        before = {(e["group"], e.get("doc_key")) for e in o.get("evidence") or [] if e["group"] in ("strong", "citator", "possible", "legislative")}
        after = {(e["group"], e.get("doc_key")) for e in c.get("evidence") or [] if e["group"] in ("strong", "citator", "possible", "legislative")}
        if after - before and o["status"] == c["status"]:
            out.append({"case": name, "kind": "new evidence", "detail": ", ".join(sorted(f"{g}:{d}" for g, d in after - before)), "worse": True})
        if c.get("review") and not c["review"].get("current") and (o.get("review") or {}).get("current"):
            out.append({"case": name, "kind": "review no longer current", "detail": "the evidence changed after a person reviewed it", "worse": True})
    gone = set(old) - {c["case"]["name"] for c in new_cards}
    out += [{"case": n, "kind": "no longer in the library", "detail": old[n]["status"], "worse": False} for n in sorted(gone)]
    out.sort(key=lambda x: (not x["worse"], x["case"]))
    return out


def write_changes(changes, path, today, first_run=False):
    L = [f"# Changes since the last run ({today})", ""]
    if first_run:
        L += ["This is the first run: there was no earlier set of cards to compare with.", ""]
    elif not changes:
        L += ["Nothing changed: every case has the same status, the same matched judgment and the same evidence as before.", ""]
    else:
        worse = [c for c in changes if c["worse"]]
        L += [f"{len(worse)} change(s) towards a warning or needing a look; {len(changes) - len(worse)} other.", ""]
        for c in changes:
            L.append(f"- {'**' if c['worse'] else ''}{c['case']}{'**' if c['worse'] else ''}: {c['kind']}: {c['detail']}")
        L.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def _recourse_status(card):
    cur = card["case"].get("recourse_curated") or []
    return "; ".join(f"{r['status']} ({r['doctrine_key']}, checked {r.get('last_checked_date') or 'date not recorded'})" for r in cur) or "no curated record"


SHEET_COLUMNS = ["case_name", "why_in_sheet", "checker_label", "recourse_curated_status", "strongest_evidence", "where", "report_file", "match_check", "your_verdict", "reviewer", "review_date", "note"]


def review_rows(cards):
    """The cases a person should look at, most pressing first: a flagged case Recourse's own record calls GOOD_LAW; any other flagged case; a case we could not match."""
    rows = []
    for c in cards:
        flagged = c["status"] in ("ADVERSE_SIGNAL", "QUESTIONED")
        curated_good = any(r["status"] == "GOOD_LAW" for r in c["case"].get("recourse_curated") or [])
        if not flagged and c["status"] != "AMBIGUOUS_MATCH":
            continue
        why = []
        if flagged and curated_good:
            why.append(f"Recourse's record says GOOD_LAW but the checker says {c['status']}")
        elif flagged:
            why.append(f"the checker says {c['status']}")
        if c["status"] == "AMBIGUOUS_MATCH":
            why.append("could not tell which judgment this is")
        ev = [e for e in c["evidence"] if e["group"] in ("strong", "citator", "possible", "legislative")] or c["evidence"]
        top = ev[0] if ev else None
        m = c["corpus"]
        match_txt = (f"{m['doc_key']} {m['title']} ({m['date'] or m['year']}, bench {m['bench_size'] or '?'}); matched by {m['match']['method']} ({m['match']['confidence']})" if m["doc_key"]
                     else "; ".join(f"{x['doc_key']} {x['title'][:50]} ({x['year']})" for x in (m["match"].get("candidates") or [])) or "no candidate")
        rows.append({"case_name": c["case"]["name"], "why_in_sheet": "; ".join(why), "checker_label": c["status"], "recourse_curated_status": _recourse_status(c),
                     "strongest_evidence": (f"[{top['kind'] or top['group']}] {top['quote']}" if top else ""),
                     "where": (f"{top['title']} ({top['date'] or top['year']}, bench {top['bench_size'] or '?'}; compared with the case's bench: {top['bench_relation']})" if top else ""),
                     "report_file": c.get("report_file") or "", "match_check": match_txt, "your_verdict": "", "reviewer": "", "review_date": "", "note": ""})
    rows.sort(key=lambda r: (0 if r["why_in_sheet"].startswith("Recourse's record") else (1 if r["checker_label"] == "ADVERSE_SIGNAL" else (2 if r["checker_label"] == "QUESTIONED" else 3)), r["case_name"]))
    return rows


def write_review_sheet(cards, path):
    rows = review_rows(cards)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def write_match_check(cards, path):
    """Every library case with the judgment it was matched to, so a person can glance down the list; the ones matched on the name alone (not on a citation or the court's own
    file) come first."""
    rows = []
    for c in cards:
        m = c["corpus"]
        rows.append({"case_name": c["case"]["name"], "library_citation": c["case"]["citation"], "status": c["status"], "matched_doc_key": m["doc_key"] or "", "matched_title": m["title"] or "",
                     "matched_date": m["date"] or "", "method": m["match"]["method"] or "", "confidence": m["match"]["confidence"] or "", "note": m["match"]["note"] or ""})
    def rank(r):
        if r["status"] == "AMBIGUOUS_MATCH":
            return 0
        if r["status"] in ("NOT_CHECKABLE_HIGH_COURT", "NOT_IN_COLLECTION"):
            return 4
        if r["confidence"] == "medium":
            return 1
        return 3 if r["method"] in ("citation", "source_url", "override") else 2
    rows.sort(key=lambda r: (rank(r), r["case_name"]))
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def merge_review_sheet(sheet_path, cards, reviews_path, today=None):
    """Records the verdicts a person filled into the review sheet. -> (recorded, problems). A row without a verdict is skipped; an unknown verdict or case is reported and skipped."""
    today = today or datetime.date.today().isoformat()
    by_name = {c["case"]["name"]: c for c in cards}
    reviews = load_reviews(reviews_path)
    recorded, problems = 0, []
    with open(sheet_path, encoding="utf-8", newline="") as fh:
        for n, row in enumerate(csv.DictReader(fh), 2):
            verdict = (row.get("your_verdict") or "").strip().upper().replace(" ", "_")
            if not verdict:
                continue
            card = by_name.get(row.get("case_name"))
            if card is None:
                problems.append(f"row {n}: no such case {row.get('case_name')!r}")
                continue
            if verdict not in VERDICTS:
                problems.append(f"row {n}: {row.get('case_name')!r}: verdict {row.get('your_verdict')!r} is not one of {', '.join(VERDICTS)}")
                continue
            reviews.append({"case_name": card["case"]["name"], "fingerprint": card["fingerprint"], "verdict": verdict, "reviewer": (row.get("reviewer") or "").strip(), "date": (row.get("review_date") or "").strip() or today,
                            "note": (row.get("note") or "").strip(), "recorded": today})
            recorded += 1
    with open(reviews_path, "w", encoding="utf-8") as fh:
        json.dump({"reviews": reviews}, fh, indent=1, ensure_ascii=False)
    return recorded, problems


def write_cards(cards, reports, out_dir, library_snapshot=None):
    os.makedirs(os.path.join(out_dir, "reports"), exist_ok=True)
    for name, md in reports.items():
        with open(os.path.join(out_dir, "reports", f"{name}.md"), "w", encoding="utf-8") as fh:
            fh.write(md)
    doc = {"schema": SCHEMA, "generated": cards[0]["provenance"]["generated"] if cards else None, "library": library_snapshot, "counts": dict(collections.Counter(c["status"] for c in cards)), "cards": cards}
    with open(os.path.join(out_dir, "currency_cards.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    return doc
