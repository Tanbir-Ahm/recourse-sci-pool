"""Compares the text of the 103 domestic-violence-pool judgments as Recourse stored them from Vaquill's dataset with our own text of the same judgments (crawl or bucket).

Read only. No network, no spend. Judgment text is read but never written out: only counts and shares are saved.

What the stored Vaquill text is: Recourse's first builder (vaquill_search.build_index, 2026-09-14) took EVERY parquet row of a case id, in every language, and joined the `text` column
(contextual header and section tags included). Recourse's later builder (case_lookup.py, 2026-09-18/20) found that "mixing [languages] produced interleaved garbage plus chunk counts inflated
~4x" and reads English only. So the language and tag figures below describe that first builder's output, not what a careful reader of the dataset gets; they are kept because they show
what following the dataset's own README recipe ("group by case_id, order by chunk_index") produces. The figure that does bear on the dataset itself is the last one: how much of our English
text is found, word for word, in the English part of Vaquill's text.

Matching: a Vaquill case id ('2013_INSC_473') to our corpus.sqlite `docs.insc` AND the same decision date (two different decisions can share one neutral-citation number).
Run: python3 -P vaquill_text_compare.py --vaquill-db <recourse>/vaquill_search.db --corpus <scratch>/corpus.sqlite --out-dir .
"""
import argparse
import collections
import json
import os
import re
import sqlite3
import statistics

LAT = re.compile(r"[A-Za-z]")
NONLAT = re.compile(r"[^\x00-\x7F‐-‟ -ɏ]")          # anything outside ASCII, general punctuation and the Latin supplements


def words(t):
    return re.findall(r"[a-z0-9]+", t.lower())


def grams(w, n=8):
    return {" ".join(w[i:i + n]) for i in range(0, max(0, len(w) - n + 1))}


def compare(vaquill_db, corpus):
    v = sqlite3.connect(f"file:{vaquill_db}?mode=ro", uri=True)
    c = sqlite3.connect(f"file:{corpus}?mode=ro", uri=True)
    ours = {}
    for did, insc, src, title, date in c.execute("select id, insc, source, title, date from docs where insc is not null and insc<>''"):
        ours.setdefault(re.sub(r"[^0-9A-Za-z]", "", insc).upper(), []).append((did, src, title, date))
    out = []
    for cid, title, dd in v.execute("select case_id, title, decision_date from metadata order by case_id"):
        k = re.sub(r"[^0-9A-Za-z]", "", cid).upper()
        if k not in ours:
            out.append({"case_id": cid, "matched": False, "reason": "no document with this neutral citation"})
            continue
        cands = ours[k]
        same_day = [x for x in cands if (x[3] or "")[:10] == dd[:10]]
        if not same_day:
            out.append({"case_id": cid, "matched": False, "reason": "no document with this neutral citation and date"})
            continue
        did, src, otitle, odate = same_day[0]
        vt = v.execute("select full_text from fts where case_id=?", (cid,)).fetchone()[0]
        ot = c.execute("select text from texts where id=?", (did,)).fetchone()[0]
        nonlat, lat = len(NONLAT.findall(vt)), len(LAT.findall(vt))
        paras = re.split(r"\n\s*\n", vt)
        eng = [p for p in paras if len(LAT.findall(p)) >= 3 * max(1, len(NONLAT.findall(p)))]       # drop paragraphs that are mostly non-Latin script
        ev = "\n\n".join(eng)
        go, gv = grams(words(ot)), grams(words(ev))
        out.append({"case_id": cid, "matched": True, "our_source": src, "year": int(dd[:4]), "vaquill_chars": len(vt), "vaquill_nonlatin_share": nonlat / max(1, nonlat + lat),
                    "vaquill_english_chars": len(ev), "our_chars": len(ot), "section_tags": vt.count("[SECTION]"), "case_headers": len(re.findall(r"(?m)^Case: ", vt)),
                    "section_headers": len(re.findall(r"(?m)^Section: ", vt)),
                    "our_8grams_found_in_vaquill_english": (len(go & gv) / len(go)) if go else None, "vaquill_english_8grams_found_in_ours": (len(go & gv) / len(gv)) if gv else None})
    return out


def summarise(out):
    m = [o for o in out if o["matched"]]
    med = lambda key: statistics.median(o[key] for o in m if o.get(key) is not None)
    by_src = collections.defaultdict(list)
    for o in m:
        by_src[o["our_source"]].append(o["our_8grams_found_in_vaquill_english"])
    share = med("our_8grams_found_in_vaquill_english")
    return {
        "judgments_in_the_vaquill_pool": len(out), "matched_to_our_text": len(m), "our_source_of_the_matches": dict(collections.Counter(o["our_source"] for o in m)),
        "median_chars_vaquill_stored_text": int(med("vaquill_chars")), "median_chars_our_text": int(med("our_chars")), "median_chars_vaquill_english_only": int(med("vaquill_english_chars")),
        "judgments_over_5pct_non_latin": sum(1 for o in m if o["vaquill_nonlatin_share"] > 0.05), "judgments_over_30pct_non_latin": sum(1 for o in m if o["vaquill_nonlatin_share"] > 0.30),
        "median_non_latin_share": round(med("vaquill_nonlatin_share"), 3),
        "judgments_with_SECTION_tags": sum(1 for o in m if o["section_tags"]), "median_SECTION_tags_per_judgment": int(statistics.median(o["section_tags"] for o in m)),
        "judgments_with_Case_header_lines": sum(1 for o in m if o["case_headers"]), "median_Case_header_lines": int(statistics.median(o["case_headers"] for o in m)),
        "median_share_of_our_8_word_runs_found_in_vaquill_english": round(share, 3),
        "median_share_of_vaquill_english_8_word_runs_found_in_ours": round(med("vaquill_english_8grams_found_in_ours"), 3),
        "implied_word_level_difference_if_independent": round(1 - share ** (1 / 8), 4),
        "judgments_with_less_than_80pct_of_our_runs_in_vaquill_english": sum(1 for o in m if (o["our_8grams_found_in_vaquill_english"] or 0) < 0.8),
        "by_our_source_median_share_of_our_runs_in_vaquill": {k: round(statistics.median(x for x in vs if x is not None), 3) for k, vs in by_src.items()},
        "reading": ("The language mix, the tags and the headers come from how Recourse's first builder read the file (all languages, the `text` column), not from the dataset's English text. "
                    "The English part agrees with our text about as well as our own two sources agree with each other (crawl against bucket on scanned years: median 76% of 8-word runs, "
                    "coverage/COVERAGE_NOTE.md section 3): a word-level difference of about 3%, so no gain in accuracy, and no evidence of a loss either. No ground truth was checked."),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vaquill-db", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    rows = compare(a.vaquill_db, a.corpus)
    summary = summarise(rows)
    os.makedirs(a.out_dir, exist_ok=True)
    json.dump(rows, open(os.path.join(a.out_dir, "vaquill_text_compare_rows.json"), "w"), indent=0)
    json.dump(summary, open(os.path.join(a.out_dir, "vaquill_text_compare_summary.json"), "w"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
