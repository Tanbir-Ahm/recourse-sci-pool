"""The currency report for one case: evidence a person can read in a few minutes, a triage label, and a plain statement of what the corpus covers.

Triage labels (never a verdict, never "good law"):
  ADVERSE_SIGNAL   a later judgment of this Court, speaking in its own voice, appears to overrule or reject the case, by a bench at least as large, or the
                   reporter's own citator lists it as overruled. Read before relying on the case.
  QUESTIONED       later judgments disagree with, doubt, refer, or limit the case; a smaller bench appears to overrule it; the cue is hedged or may be about another
                   case; or the legislature responded to it. Read them.
  NO_ADVERSE_FOUND at least MIN_CITING later judgments that we hold cite the case and none of the above turned up. This is silence in what we hold, and the
                   coverage block says how much that is.
  INSUFFICIENT     fewer than MIN_CITING later citing judgments found; too little to say anything.
A separate STATUTE_CHANGED flag says the IPC or CrPC provisions the judgment cites most were renumbered, repealed or changed by the 2023 recodification.
"""
import collections
import csv
import json
import os
import re
from datetime import date

from . import cites as C
from . import mentions as M
from . import statutes as S
from . import tables as TB
from . import treatment as T
from .textutil import flatten, quote_in_text

MIN_CITING = 3
ADVERSE = ("OVERRULES", "DISAGREES", "DOUBTS_REFERS")
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEAR_COUNTS = os.path.join(_HERE, "coverage", "year_counts.csv")

PLAIN = {
    "ADVERSE_SIGNAL": "A later judgment of the Supreme Court appears to overrule or reject this case. A lawyer must read it before anyone relies on this case.",
    "QUESTIONED": "Later judgments disagree with, doubt, limit or refer this case, or the legislature responded to it. Read them before relying on it.",
    "NO_ADVERSE_FOUND": "No overruling or doubt was found in the later judgments we hold that cite this case. That is silence in what we hold, not a finding that it is good law: see the coverage block.",
    "INSUFFICIENT": "Too few later judgments in our collection cite this case to say anything.",
}


RELIABLE_BENCH = ("header_full", "report_line")


def bench_relation(citing, target, citing_source=None, target_source=None):
    """'larger', 'equal' or 'smaller' when it can be established, otherwise 'unknown'.

    Both benches complete (the JUDIS header up to about 1994, or the law report's judge list): compare them. A count from a short header or from signature lines is
    only a lower bound, since those can miss judges, so with one bound only the comparison that no missing judge could reverse is made: the target's bound already
    exceeds the complete citing bench ('smaller': the target's bench is at least as large as the bound), or the citing bound already exceeds the complete target bench
    ('larger'). With two bounds nothing is concluded."""
    if not citing or not target:
        return "unknown"
    citing_ok, target_ok = citing_source in RELIABLE_BENCH, target_source in RELIABLE_BENCH
    if citing_ok and target_ok:
        return "larger" if citing > target else ("equal" if citing == target else "smaller")
    if citing_ok and target > citing:
        return "smaller"
    if target_ok and citing > target:
        return "larger"
    return "unknown"


def classify_mentions(corpus, mentions, target):
    """Adds treatment, cue and bench relation to each mention; checks each sentence word for word against its judgment's text."""
    texts = {}
    for m in mentions:
        c = T.classify_in_context(m["sentence"], m["target_in_sentence"], m.get("next", ""))
        m.update(label=c["label"], cue=c["cue"], negated=c["negated"], hedged=c["hedged"], binding=c["binding"], labels_all=c["all"], anaphoric=c.get("anaphoric", False))
        m["bench_relation"] = bench_relation(m.get("bench_size"), target.bench_size, m.get("bench_source"), target.bench_source)
        if m["doc_id"] not in texts:
            texts[m["doc_id"]] = corpus.text_of(m["doc_id"])
        m["quote_verified"] = quote_in_text(m["sentence"], texts[m["doc_id"]])
    return mentions


def _eligible(m):
    """Counts as this Court's own treatment: the court is speaking, the target is the clear subject of the cue, and the citation is not doubtful."""
    return m["speaker"] == "court" and m["confidence"] in ("high", "medium")


def strongest_per_doc(mentions):
    """{doc_key: best mention} by adverse strength then recency of paragraph order; eligible mentions only."""
    best = {}
    for m in mentions:
        if not _eligible(m):
            continue
        rank = (T.STRENGTH.get(m["label"], -1) if m["label"] != "NOT_OVERRULED" else 3.5, m["binding"] == "strong", not m["hedged"])
        if m["doc_key"] not in best or rank > best[m["doc_key"]][0]:
            best[m["doc_key"]] = (rank, m)
    return {k: v[1] for k, v in best.items()}


def _brief(m):
    return {"doc_key": m["doc_key"], "title": m["title"], "date": m["date"], "year": m["year"], "bench_size": m["bench_size"], "bench_relation": m["bench_relation"], "source": m["source"],
            "label": m["label"], "cue": m["cue"], "hedged": m["hedged"], "binding": m["binding"], "anaphoric": m.get("anaphoric", False), "speaker": m["speaker"], "confidence": m["confidence"], "tier": m["tier"],
            "sentence": m["sentence"], "prev": m["prev"], "next": m["next"], "quote_verified": m["quote_verified"], "in_headnote": m["in_headnote"]}


def coverage(corpus, target_year, year_counts_path=YEAR_COUNTS):
    """How much of what came after the case this collection can see: our texts by decade against Indian Kanoon's own yearly count (a screenshot of 2026-10-05)."""
    ik = {}
    if os.path.exists(year_counts_path):
        for r in csv.DictReader(open(year_counts_path, encoding="utf-8")):
            if r["indiankanoon"]:
                ik[int(r["year"])] = int(r["indiankanoon"])
    ours = dict(corpus.con.execute("SELECT year, COUNT(*) FROM docs WHERE dup_of IS NULL AND year IS NOT NULL GROUP BY year").fetchall())
    start = max((target_year or 0) + 1, 1968)
    rows, tot_o, tot_i = [], 0, 0
    for a in range((start // 10) * 10, 2030, 10):
        lo, hi = max(a, start), min(a + 9, 2026)
        if lo > hi:
            continue
        o = sum(ours.get(y, 0) for y in range(lo, hi + 1))
        i = sum(ik.get(y, 0) for y in range(lo, hi + 1))
        tot_o, tot_i = tot_o + o, tot_i + i
        rows.append({"years": f"{lo}-{hi}", "our_judgments": o, "indiankanoon_lists": i, "share": round(o / i, 2) if i else None})
    last = corpus.con.execute("SELECT MAX(date) FROM docs WHERE date IS NOT NULL AND date_source IN ('header','tail_place','bucket')").fetchone()[0]
    return {"collection_runs_to": last, "later_years": rows, "share_of_later_judgments_we_hold": round(tot_o / tot_i, 2) if tot_i else None,
            "note": "Indian Kanoon's counts are typed from a screenshot of its yearly list (2026-10-05) and may include orders or duplicates; the share is a rough guide. "
                    "The collection is the Supreme Court's own site to 4 May 2017 and the open Dattam Labs bucket after that, which holds only part of each year."}


def citator_block(corpus, doc):
    """The reporter's own list of later citing cases printed in the judgment's header (old judgments only), with each citing case found in our collection."""
    out = []
    for row in doc.get("citator") or []:
        key = C.norm_cite(row["cite"])
        found = [d for d in corpus.by_cite(key) if d["doc_key"] != doc["doc_key"]][:1] if key else []
        out.append({**row, "citing_case": ({"doc_key": found[0]["doc_key"], "title": found[0]["title"], "date": found[0]["date"]} if found else None)})
    return out


WEAK_ONLY_BELOW = 10      # a case cited this few times is flagged on weak readings alone; a heavily cited one is not (some sentence among hundreds always looks odd)


def triage(summary):
    if summary["adverse_strong"] or summary["citator_adverse_overruled"]:
        return "ADVERSE_SIGNAL"
    firm = [m for m in summary["adverse_possible"] if not m.get("weak")]
    weak = [m for m in summary["adverse_possible"] if m.get("weak")]
    if firm or summary["legislative"] or summary["citator_adverse_other"]:
        return "QUESTIONED"
    if weak and summary["citing_judgments"] < WEAK_ONLY_BELOW:
        return "QUESTIONED"
    if summary["citing_judgments"] >= MIN_CITING:
        return "NO_ADVERSE_FOUND"
    return "INSUFFICIENT"


def _collapse(items):
    """One entry per (judgment, label, cue): a judgment that repeats the same sentence pattern many times (a table of directions, each ending 'has not been followed') shows
    the first and a count of the others."""
    out, seen = [], {}
    for m in items:
        key = (m["doc_key"], m["label"], (m["cue"] or "").lower())
        if key in seen:
            seen[key]["repeats"] = seen[key].get("repeats", 0) + 1
        else:
            seen[key] = m
            out.append(m)
    return out


def _table_into_lists(rows, target, adverse_strong, adverse_possible):
    """Adds the law reporters' case-law table rows that mark the target overruled (or disapproved, or not followed) to the adverse lists, as the reporter's own statement
    and not as a reading of a sentence, and returns a summary of every row (counts by what the reporter marked, most recent 'relied on' ones). An overruling by a smaller
    bench than the target's goes to the possible list; a judgment already in the strong list is not listed twice."""
    strong_docs = {m["doc_key"] for m in adverse_strong}
    by_code, relied = collections.Counter(), []
    for r in rows:
        by_code[TB.MEANING.get(r["code"], r["code"])] += 1
        if r["code"] in ("RF", "F"):
            relied.append(r)
        if r["code"] not in TB.ADVERSE_LABEL:
            continue
        relation = bench_relation(r["bench_size"], target.bench_size, r["bench_source"], target.bench_source)
        brief = {"doc_key": r["doc_key"], "title": r["title"], "date": r["date"], "year": r["year"], "bench_size": r["bench_size"], "bench_relation": relation, "source": r["source"],
                 "label": TB.ADVERSE_LABEL[r["code"]], "cue": r["code_text"], "hedged": False, "binding": "strong", "anaphoric": False, "speaker": "the law report's case-law table",
                 "confidence": "high", "tier": "table", "sentence": r["quote"], "prev": "", "next": "", "quote_verified": r["quote_verified"], "in_headnote": True}
        clean_adverse = relation != "smaller" if r["code"] == "O" else relation == "larger"
        if clean_adverse:
            if r["doc_key"] not in strong_docs:
                brief["kind"] = f"law report's case-law table marks it {r['code_text']}"
                adverse_strong.append(brief)
                strong_docs.add(r["doc_key"])
        else:
            brief["why_not_a_clean_overruling"] = ["by a smaller bench than the target's, which cannot overrule it" if relation == "smaller" and r["code"] == "O"
                                                   else "the reporter marks disapproval or non-following, not an overruling"]
            brief["weak"] = False
            adverse_possible.append(brief)
    relied.sort(key=lambda r: r["date"] or f"{r['year']}-12-31", reverse=True)
    return {"judgments_with_a_row": len({r["doc_key"] for r in rows}), "rows": len(rows), "by_what_the_reporter_marked": dict(by_code),
            "recent_relied_on": [{"title": r["title"], "date": r["date"], "year": r["year"], "marked": r["code_text"], "para": r["para"], "quote": r["quote"], "quote_verified": r["quote_verified"]} for r in relied[:5]]}


def build_bundle(corpus, target, doc=None, today=None):
    today = today or date.today().isoformat()
    res = M.find_mentions(corpus, target)
    mentions = classify_mentions(corpus, res["mentions"], target)
    eligible = [m for m in mentions if _eligible(m)]
    best = strongest_per_doc(mentions)
    by_label = collections.Counter(m["label"] for m in best.values())

    adverse_strong, adverse_possible, legislative, not_courts_own = [], [], [], []
    for m in mentions:
        if m["label"] not in ADVERSE and m["label"] != "LEGISLATIVE":
            continue
        if m["confidence"] == "low":
            continue
        if m["speaker"] in ("counsel", "lower_court"):
            b = _brief(m)
            b["why_not_a_clean_overruling"] = [f"said by {m['speaker'].replace('_', ' ')}, not as this Court's own holding"]
            not_courts_own.append(b)
            continue
        clean = (m["binding"] == "strong" and not m["hedged"] and m["confidence"] in ("high", "medium"))
        if m["label"] == "LEGISLATIVE":
            if not m["in_headnote"]:
                legislative.append(_brief(m))
        elif m["label"] == "OVERRULES" and clean and m["bench_relation"] in ("larger", "equal", "unknown"):
            b = _brief(m)
            b["kind"] = "law report's headnote says overruled" if m["in_headnote"] else "overruled by this Court"
            adverse_strong.append(b)
        elif m["label"] == "DISAGREES" and clean and m["bench_relation"] == "larger":
            b = _brief(m)
            b["kind"] = "rejected by a larger bench (disagreement by a bench that can overrule)"
            adverse_strong.append(b)
        else:
            reason, weak = [], False
            if m.get("anaphoric"):
                reason.append("the cue is in the sentence after the one naming the case (\"That decision ...\"), so it may be about something else")
                weak = True
            if m["hedged"]:
                reason.append("worded as an argument, a condition or a possibility")
                weak = True
            if m["binding"] == "weak":
                reason.append("another case is named nearer the cue, or the cue is far from the mention, so it may be about something else")
                weak = True
            if m["label"] == "OVERRULES" and m["bench_relation"] == "smaller":
                reason.append("by a smaller bench than the target's, which cannot overrule it")
            if m["label"] == "DISAGREES" and m["bench_relation"] == "smaller":
                reason.append("a smaller bench's disagreement does not bind or weaken a larger bench's ruling")
                weak = True
            if m["in_headnote"]:
                reason.append("in the law report's headnote, not the judgment")
                weak = True
            if m["label"] in ("DISAGREES", "DOUBTS_REFERS") and not reason:
                reason.append("disagreement or doubt, not an overruling")
            b = _brief(m)
            b["why_not_a_clean_overruling"] = reason
            b["weak"] = weak
            adverse_possible.append(b)

    table_rows = TB.evidence(corpus, target, mentions)
    table_summary = _table_into_lists(table_rows, target, adverse_strong, adverse_possible)
    adverse_strong, adverse_possible, legislative, not_courts_own = (_collapse(x) for x in (adverse_strong, adverse_possible, legislative, not_courts_own))
    citator = citator_block(corpus, doc) if doc else []
    citator_overruled = [c for c in citator if c["code"] in ("O", "HO")]
    citator_other = [c for c in citator if c["code"] == "NF"]
    docs_hi = {m["doc_key"] for m in mentions if m["confidence"] in ("high", "medium")}
    years = sorted({m["year"] for m in mentions if m["year"] and m["doc_key"] in docs_hi})
    decades = collections.Counter((y // 10) * 10 for y in [m["year"] for m in {m["doc_key"]: m for m in mentions if m["doc_key"] in docs_hi}.values() if m["year"]])
    positives = [m for m in best.values() if m["label"] in ("FOLLOWS", "NOT_OVERRULED")]
    positives.sort(key=lambda m: m["date"] or f"{m['year']}-12-31", reverse=True)
    sd = S.statute_dimension(corpus.text_of(doc["id"])) if doc else []

    summary = {
        "citing_judgments": len(docs_hi), "citing_judgments_all_confidence": len({m["doc_key"] for m in mentions}), "by_treatment": dict(by_label),
        "latest_citing_year": years[-1] if years else None, "citing_in_last_10_years": sum(1 for m in {m["doc_key"]: m for m in mentions if m["doc_key"] in docs_hi}.values() if m["year"] and m["year"] >= int(today[:4]) - 10),
        "citing_by_decade": dict(sorted(decades.items())), "adverse_strong": adverse_strong, "adverse_possible": adverse_possible, "legislative": legislative, "argued_or_lower_court": not_courts_own,
        "citator_adverse_overruled": citator_overruled, "citator_adverse_other": citator_other, "case_law_table": table_summary,
    }
    summary["weak_signals_set_aside"] = len([m for m in adverse_possible if m.get("weak")]) if triage(summary) in ("NO_ADVERSE_FOUND", "INSUFFICIENT") else 0
    label = triage(summary)
    bundle = {
        "target": {"name": target.name, "pet": target.pet, "resp": target.resp, "year": target.year, "date": target.date, "doc_key": target.doc_key, "bench_size": target.bench_size,
                   "cites": target.cites, "learned_cites": target.learned_cites},
        "generated": today,
        "triage": label, "plain": PLAIN[label] + (f" {summary['weak_signals_set_aside']} weak or ambiguous readings were set aside; they are listed below so you can check them." if summary["weak_signals_set_aside"] else ""), "statute_flag": S.summarise(sd),
        "summary": summary,
        "recent_approving": [_brief(m) for m in positives[:5]],
        "reporter_citator": citator,
        "statute_dimension": sd,
        "coverage": coverage(corpus, target.year),
        "how_found": res["by_tier"],
        "limits": ["Triage is a reading aid made by pattern rules over the sentences that name the case; it is not legal advice and not a verdict.",
                   "Only Supreme Court judgments we hold are searched; High Court treatment and judgments we lack are invisible.",
                   "Each quoted sentence was checked word for word against the judgment's text; the reading of it is a rule's, so a person must confirm.",
                   "The law reporter's case-law table (judgments of 2017 to 2023) is the reporter's annotation, not the court's words; judgments of 2024 on print no such table."],
    }
    return bundle


def render_markdown(b):
    t, s = b["target"], b["summary"]
    L = [f"# Currency report: {t['name']} ({t['year']})", "",
         f"**Triage: {b['triage']}**" + (f"  |  **{b['statute_flag']}**" if b["statute_flag"] else ""), "", b["plain"], "",
         f"Generated {b['generated']}. Source label: pattern-rule reading of Supreme Court texts; not lawyer-validated.", "",
         "## Who cites it", "",
         f"- Later judgments citing it (high or medium confidence): **{s['citing_judgments']}**; latest in {s['latest_citing_year']}; {s['citing_in_last_10_years']} in the last 10 years.",
         f"- How its own text treats it, by the strongest sentence in each citing judgment: " + (", ".join(f"{k.lower().replace('_', ' ')} {v}" for k, v in sorted(s["by_treatment"].items(), key=lambda x: -x[1])) or "none read"),
         f"- By decade: " + (", ".join(f"{d}s {n}" for d, n in s["citing_by_decade"].items()) or "none"),
         f"- Found by: " + ", ".join(f"{k} {v}" for k, v in b["how_found"].items()) + (f"; citations learned from the texts: {', '.join(t['learned_cites'])}" if t["learned_cites"] else ""), ""]

    def block(title, items, adverse=True):
        if not items:
            return
        L.extend([f"## {title}", ""])
        for m in items:
            L.append(f"- {('[' + m['kind'] + '] ') if m.get('kind') else ''}**{m['title']}** ({m['date'] or m['year']}; bench {m['bench_size'] or 'unknown'}; bench compared with the target's: {m['bench_relation']}; {m['label'].lower().replace('_', ' ')}; cue: \"{m['cue']}\"; speaker: {m['speaker']}; confidence {m['confidence']}; quote verified: {m['quote_verified']})")
            L.append(f"  > {m['sentence']}")
            if m.get("repeats"):
                L.append(f"  (the same wording appears {m['repeats']} more time{'s' if m['repeats'] > 1 else ''} in this judgment)")
            if m.get("why_not_a_clean_overruling"):
                L.append(f"  Why not a clean overruling: {'; '.join(m['why_not_a_clean_overruling'])}.")
        L.append("")

    block("Appears to overrule or reject it (read these first)", s["adverse_strong"])
    block("Disagree, doubt, limit, or an overruling with a caveat (weak readings are marked in their reasons)", s["adverse_possible"])
    block("The legislature responded", s["legislative"])
    ct = s.get("case_law_table") or {}
    if ct.get("rows"):
        L.extend(["## What the law reporter's case-law table says (judgments of 2017 to 2023 only)", "",
                  f"- The Supreme Court Reports print, in the headnote of each judgment, a table of the cases it cites and what it did with each. {ct['judgments_with_a_row']} later judgments have a row for this case; "
                  + "; ".join(f"{k} {v}" for k, v in sorted(ct["by_what_the_reporter_marked"].items(), key=lambda x: -x[1])) + ". This is the reporter's annotation, not the court's own words."])
        for r in ct["recent_relied_on"]:
            L.append(f"  - {r['title']} ({r['date'] or r['year']}): marked \"{r['marked']}\", {r['para']}. Quote verified: {r['quote_verified']}")
        L.append("")
    block("An overruling or doubt said by counsel or a lower court (not this Court's own words; does not change the triage)", s["argued_or_lower_court"])
    if b["reporter_citator"]:
        L.extend(["## The reporter's own citator (printed in the judgment's header; later cases to about 1994)", ""])
        for c in b["reporter_citator"]:
            who = f" -> {c['citing_case']['title']} ({c['citing_case']['date']})" if c["citing_case"] else ""
            L.append(f"- {c['code']} ({c['meaning']}): {c['cite']}{(' paras ' + c['paras']) if c['paras'] else ''}{who}")
        L.append("")
    block("Recent judgments citing it with approval", b["recent_approving"])
    if b["statute_dimension"]:
        L.extend(["## Statute dimension (what became of the sections the judgment cites)", ""])
        for r in b["statute_dimension"]:
            succ = ", ".join(f"{e['act']} {e['section']}" + (" (changed)" if e["change"] else "") for e in r["successors"])
            L.append(f"- {r['act']} s.{r['section']} (cited {r['count']}x): {r['note']}" + (f" -> {succ}" if succ else ""))
        L.append("")
    cv = b["coverage"]
    L.extend(["## What this collection can and cannot see", "", f"- Collection runs to {cv['collection_runs_to']}.",
              f"- Of the judgments Indian Kanoon lists after this case, we hold about {int((cv['share_of_later_judgments_we_hold'] or 0) * 100)}%."])
    for r in cv["later_years"]:
        L.append(f"  - {r['years']}: we hold {r['our_judgments']} of {r['indiankanoon_lists']} ({int((r['share'] or 0) * 100)}%)")
    L.append(f"- {cv['note']}")
    L.extend(["", "## Limits", ""] + [f"- {x}" for x in b["limits"]])
    return "\n".join(L) + "\n"
