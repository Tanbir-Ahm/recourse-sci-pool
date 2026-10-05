"""Measuring the checker against something independent of its own rules: the reporter's citator.

About 5,000 of the crawled judgments (to about 1985) print, in their header, the reporter's own list of later cases that cite them, each with a code:
followed, relied on, distinguished, explained, referred, overruled and so on (goodlaw.headers.CITATOR_CODES). Each entry names the citing case by its AIR page.
For every entry whose citing case is in our collection we run the checker on that one citing judgment and ask whether the treatment it reads agrees with the
code. That gives recall on overrulings (the code O / HO / NF entries) and a rate of false alarms (adverse readings where the reporter saw none).

Entries are split by target judgment: even crawl ids are the development half (rules may be tuned on it), odd ids the held-out half (reported once).
"""
import collections
import json
import re

from . import corpus as K
from . import mentions as M
from . import report as R
from . import treatment as T

# what the reporter's code means in the checker's vocabulary
EXPECT = {
    "O": "adverse", "HO": "adverse", "NF": "adverse",
    "D": "distinguishes", "E": "limits",
    "F": "positive", "RF": "positive", "APL": "positive", "APR": "positive", "AFR": "positive", "A": "positive", "AP": "positive", "REI": "positive", "REL": "positive",
    "R": "neutral", "MV": "neutral", "MR": "neutral", "C": "neutral", "OPN": "neutral", "ACC": "neutral",
}
ADVERSE = ("OVERRULES", "DISAGREES", "DOUBTS_REFERS")
POSITIVE = ("FOLLOWS", "NOT_OVERRULED")


def gold_pairs(corpus):
    """[(target doc_key, citing doc_key, code, cite)] for every citator entry whose citing case is in the collection (resolved by its own AIR citation)."""
    own = collections.defaultdict(list)
    for d in corpus.iter_docs():
        for k in d["cites"]:
            if k.startswith("air:"):
                own[k].append(d["doc_key"])
    pairs, unresolved = [], 0
    for d in corpus.iter_docs("dup_of IS NULL AND source='crawl' AND citator != '[]'"):
        for row in d["citator"]:
            key = f"air:{row['year']}:{row['page']}"
            hits = [h for h in own.get(key, []) if h != d["doc_key"]]
            if len(hits) == 1:
                pairs.append((d["doc_key"], hits[0], row["code"], row["cite"]))
            else:
                unresolved += 1
    return pairs, unresolved


def best_in_doc(corpus, target_key, citing_key, body_only=False):
    """The strongest treatment of the target found in the citing judgment (court's own voice, confident mentions only), or None if no mention is found.
    With body_only, mentions inside the headnote (and so inside its case-law table) are not read, only the court's own judgment after it: used when the answer key
    itself is printed in that headnote. The text is still read as a whole, as in the real checker, so a full citation in the headnote still raises the
    confidence of a short-name mention in the body ("Jasmine Kaur (Supra)")."""
    tdoc = corpus.get(target_key, with_text=False)
    cdoc = corpus.get(citing_key)
    target = M.Target.from_doc(tdoc)
    short = target.short_names(corpus)
    found, _ = M.extract(cdoc["text"], target, short, cdoc.get("body_start"), party_cases=target.party_case_patterns(corpus))
    if body_only:
        found = [m for m in found if not m["in_headnote"]]
    if not found:
        return None
    best = None
    for m in found:
        c = T.classify_in_context(m["sentence"], m["target_in_sentence"], m.get("next", ""))
        m.update(label=c["label"], cue=c["cue"], hedged=c["hedged"], binding=c["binding"])
        eligible = m["confidence"] in ("high", "medium") and m["speaker"] in ("court", "headnote")
        m["eligible"] = eligible
        rank = (eligible, T.STRENGTH.get(m["label"], -1) if m["label"] != "NOT_OVERRULED" else 3.5, m["binding"] == "strong", not m["hedged"])
        if best is None or rank > best[0]:
            best = (rank, m)
    return best[1]


_POOL = {}


def _init(path, body_only=False):
    _POOL["c"] = K.Corpus(path)
    _POOL["body_only"] = body_only


def _work(pair):
    t, c, code, cite = pair
    m = best_in_doc(_POOL["c"], t, c, _POOL.get("body_only", False))
    if m is None:
        return (t, c, code, cite, None, None, None, False, False, "strong", None)
    return (t, c, code, cite, m["label"], m["cue"], m["sentence"][:400], m["eligible"], m["hedged"], m["binding"], m["speaker"])


def run(corpus_path, pairs, workers=4, body_only=False):
    """Runs the checker on each pair's citing judgment (see best_in_doc for body_only)."""
    from multiprocessing import Pool
    with Pool(workers, initializer=_init, initargs=(corpus_path, body_only)) as pool:
        return pool.map(_work, pairs, chunksize=50)


def production_rows(corpus, pairs, body_only=False, log=None):
    """Like run(), but through the full mention finder for each target (candidates from the citation index and names, citations learned from the corpus), as the real
    report does. Slow (several seconds per target) but it is what a user gets; run() is a fast stand-in that cannot learn a case's other citations, so it finds fewer
    mentions. Meant for the pairs where the answer matters most, such as the adverse ones. Rows have the same fields as run()."""
    by_target = collections.defaultdict(list)
    for p in pairs:
        by_target[p[0]].append(p)
    out = []
    for n, (tkey, group) in enumerate(by_target.items(), 1):
        tdoc = corpus.get(tkey, with_text=False)
        target = M.Target.from_doc(tdoc)
        res = M.find_mentions(corpus, target)
        mentions = R.classify_mentions(corpus, res["mentions"], target)
        for t, c, code, cite in group:
            mine = [m for m in mentions if m["doc_key"] == c and not (body_only and m["in_headnote"])]
            best = None
            for m in mine:
                eligible = m["confidence"] in ("high", "medium") and m["speaker"] in ("court", "headnote")
                rank = (eligible, T.STRENGTH.get(m["label"], -1) if m["label"] != "NOT_OVERRULED" else 3.5, m["binding"] == "strong", not m["hedged"])
                if best is None or rank > best[0]:
                    best = (rank, m, eligible)
            if best is None:
                out.append((t, c, code, cite, None, None, None, False, False, "strong", None))
            else:
                m = best[1]
                out.append((t, c, code, cite, m["label"], m["cue"], m["sentence"][:400], best[2], m["hedged"], m["binding"], m["speaker"]))
        if log and n % 10 == 0:
            log(f"{n}/{len(by_target)} targets")
    return out


def _row(r):
    """(code, label as the report would use it, hedged, binding). Older 7-field rows carry no speaker or flags and are taken as eligible and strong. A mention
    found only in counsel's or a lower court's voice (or only by a weak name match) is not used by the report, so it is counted as no usable reading."""
    code, label = r[2], r[4]
    if len(r) < 11:
        return code, label, False, "strong"
    return code, (label if r[7] else ("NO_COURT_VOICE" if label is not None else None)), r[8], r[9]


def summarise(results):
    """Agreement tables for a list of results from run(). The by-code table and the 'adverse' and 'others' counts use the reading the report would use (the court's or
    the headnote's voice only); 'tiers' splits the adverse readings the way the report does, into clean ones (not hedged, cue clearly about the target) and possible
    ones (hedged, or another case may be what the cue is about)."""
    by_code = collections.defaultdict(collections.Counter)
    tiers = {"adverse_codes": collections.Counter(), "other_codes": collections.Counter()}
    for r in results:
        code, label, hedged, binding = _row(r)
        by_code[code][label or "NOT_FOUND"] += 1
        if label in ADVERSE:
            tier = "clean" if (not hedged and binding == "strong") else "possible"
            tiers["adverse_codes" if EXPECT.get(code) == "adverse" else "other_codes"][tier] += 1
    adverse_codes = [c for c in by_code if EXPECT.get(c) == "adverse"]
    out = {"by_code": {c: dict(v) for c, v in sorted(by_code.items(), key=lambda x: -sum(x[1].values()))}}
    n_adv = sum(sum(by_code[c].values()) for c in adverse_codes)
    found_adv = sum(v for c in adverse_codes for k, v in by_code[c].items() if k != "NOT_FOUND")
    tiers = {k: dict(v) for k, v in tiers.items()}
    hit_overrule = sum(by_code[c].get("OVERRULES", 0) for c in ("O", "HO"))
    n_o = sum(sum(by_code[c].values()) for c in ("O", "HO"))
    hit_adverse_any = sum(v for c in adverse_codes for k, v in by_code[c].items() if k in ADVERSE)
    non_adv = [c for c in by_code if EXPECT.get(c) in ("positive", "neutral", "distinguishes", "limits")]
    n_non = sum(sum(by_code[c].values()) for c in non_adv)
    found_non = sum(v for c in non_adv for k, v in by_code[c].items() if k != "NOT_FOUND")
    false_adv = sum(v for c in non_adv for k, v in by_code[c].items() if k in ADVERSE)
    false_over = sum(v for c in non_adv for k, v in by_code[c].items() if k == "OVERRULES")
    out["tiers"] = tiers
    out["adverse"] = {"pairs": n_adv, "mention_found": found_adv, "read_as_any_adverse": hit_adverse_any, "overruled_pairs": n_o, "read_as_overrules": hit_overrule}
    out["others"] = {"pairs": n_non, "mention_found": found_non, "read_as_adverse": false_adv, "read_as_overrules": false_over}
    pos_codes = [c for c in by_code if EXPECT.get(c) == "positive"]
    n_pos = sum(sum(by_code[c].values()) for c in pos_codes)
    out["positive"] = {"pairs": n_pos, "read_as_follows_or_not_overruled": sum(v for c in pos_codes for k, v in by_code[c].items() if k in POSITIVE),
                       "read_as_adverse": sum(v for c in pos_codes for k, v in by_code[c].items() if k in ADVERSE)}
    d = by_code.get("D", collections.Counter())
    out["distinguished"] = {"pairs": sum(d.values()), "read_as_distinguishes": d.get("DISTINGUISHES", 0)}
    return out


def split(pairs):
    """Development half (even target crawl ids) and held-out half (odd)."""
    dev = [p for p in pairs if int(p[0][1:]) % 2 == 0]
    held = [p for p in pairs if int(p[0][1:]) % 2 == 1]
    return dev, held


def known_cases(corpus, path, log=print):
    """Runs the full checker on each case in a known-cases file and compares the triage with what is known. Returns (rows, summary)."""
    from . import report as R
    spec = json.load(open(path, encoding="utf-8"))["cases"]
    rows = []
    for c in spec:
        doc = corpus.get(c["doc_key"], with_text=False)
        if not doc:
            rows.append({"name": c["name"], "error": "document not in the collection"})
            continue
        target = M.Target.from_doc(doc)
        target.aliases = c.get("aliases", [])
        b = R.build_bundle(corpus, target, doc)
        t = b["triage"]
        if c["expect"] == "adverse":
            ok = t in ("ADVERSE_SIGNAL", "QUESTIONED")
            exact = t == "ADVERSE_SIGNAL"
        else:
            ok = t != "ADVERSE_SIGNAL"
            exact = t in ("NO_ADVERSE_FOUND", "INSUFFICIENT")
        stat_ok = (b["statute_flag"] == c["statute_expect"]) if c.get("statute_expect") else None
        rows.append({"name": c["name"], "expect": c["expect"], "triage": t, "ok": ok, "exact": exact, "statute_flag": b["statute_flag"], "statute_ok": stat_ok,
                     "citing": b["summary"]["citing_judgments"], "adverse_strong": len(b["summary"]["adverse_strong"]), "adverse_possible": len(b["summary"]["adverse_possible"])})
        log(f"{'OK ' if ok else 'MISS'} {c['expect']:12} {t:17} citing {b['summary']['citing_judgments']:4}  {c['name']}")
    adv = [r for r in rows if r.get("expect") == "adverse"]
    good = [r for r in rows if r.get("expect") == "not_adverse"]
    summary = {"adverse_cases": len(adv), "adverse_flagged": sum(r["ok"] for r in adv), "adverse_flagged_as_signal": sum(r["exact"] for r in adv),
               "good_cases": len(good), "good_not_signalled": sum(r["ok"] for r in good), "good_clean": sum(r["exact"] for r in good)}
    return rows, summary
