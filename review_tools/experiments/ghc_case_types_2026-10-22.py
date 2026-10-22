"""Were the Gauhati High Court judgments the index embedded all criminal? Reads the index's own document records only: no network, no key, no spend, nothing changed.

    python review_tools/experiments/ghc_case_types_2026-10-22.py --index-dir <checkout of claude/sci-index> --out review_results/2026-10-22_index_holdings

The index decides "criminal" by a wording test on the text (`sci_index.is_criminal`: a criminal case-type heading in the first 1,500 characters, or at least 10 criminal-law terms per 10,000
characters), not by the court's case type. This script takes the case type the court itself gave, from the case number in the index record ("Crl.A(J)/12/2018", "WP(C)/3193/2012"), calls a
number criminal when its type contains crl, criminal, bail, death sentence, AB or BA, and crosses that with whether the index embedded the judgment. It answers two questions: how many embedded
judgments have a non-criminal case type, and how many criminal-type judgments the wording test did not embed. A case type is the court's label, not a reading of the judgment: a civil writ
petition can still be about a police or prison matter, and the script says nothing about that.
"""
import argparse
import collections
import gzip
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

import sci_index as si  # noqa: E402

EXTRA = 2_000_000_000


def case_type(case_number):
    s = (case_number or "").strip()
    m = re.match(r"^([A-Za-z][A-Za-z .()&/\-]*?)\s*[/(]?\s*\d", s)
    return (m.group(1).strip() if m else s[:24]) or "(no case number)"


def is_criminal_type(t):
    return bool(re.search(r"crl|criminal|bail|death sentence|\bab\b|\bba\b|cr\.p|cr\.a|c\.r\.l", t.lower()))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    led = si.ledger(a.index_dir)
    rows = []
    for start, v in sorted(led.items()):
        if start < EXTRA or 2_000_250_000 <= start < 2_000_500_000:
            continue                                                  # the Gauhati sources only: the court's own files (below 2,000,250,000) and the open-bucket text (from 2,000,500,000)
        scope = "court_files" if start < 2_000_250_000 else "open_bucket_text"
        for line in gzip.open(os.path.join(a.index_dir, "index", v["base"] + ".docs.jsonl.gz"), "rt", encoding="utf-8"):
            d = json.loads(line)
            d["_scope"] = scope
            d["_type"] = case_type(d["src"].get("citation") or d["src"].get("case_id"))
            d["_crim"] = is_criminal_type(d["_type"])
            rows.append(d)
    res = {"recorded": len(rows), "embedded": sum(1 for d in rows if "skip" not in d), "by_source": {}}
    for scope in ("court_files", "open_bucket_text"):
        rs = [d for d in rows if d["_scope"] == scope]
        emb = [d for d in rs if "skip" not in d]
        skp = [d for d in rs if "skip" in d]
        e_other = [d for d in emb if not d["_crim"]]
        res["by_source"][scope] = {
            "recorded": len(rs), "embedded": len(emb), "embedded_with_a_criminal_case_type": sum(1 for d in emb if d["_crim"]), "embedded_with_another_case_type": len(e_other),
            "embedded_other_types": dict(collections.Counter(d["_type"] for d in e_other).most_common()), "passages_embedded": sum(d["passages"] for d in emb),
            "passages_in_other_types": sum(d["passages"] for d in e_other), "not_embedded": len(skp), "not_embedded_with_a_criminal_case_type": sum(1 for d in skp if d["_crim"]),
            "other_type_embedded_density_min_median_max": [round(x, 1) for x in (min(d["density"] for d in e_other), statistics.median(d["density"] for d in e_other), max(d["density"] for d in e_other))] if e_other else None,
            "other_type_embedded_admitted_by_the_header_not_the_density": sum(1 for d in e_other if d["density"] < si.DENSITY_THRESHOLD),
        }
    emb_all = [d for d in rows if "skip" not in d]
    res["all_embedded_criminal_case_type"] = sum(1 for d in emb_all if d["_crim"])
    res["all_embedded_other_case_type"] = sum(1 for d in emb_all if not d["_crim"])
    res["criminal_case_types_not_embedded"] = sum(1 for d in rows if "skip" in d and d["_crim"])
    res["criminal_types_embedded_share_of_all_criminal_types_recorded"] = round(res["all_embedded_criminal_case_type"] / (res["all_embedded_criminal_case_type"] + res["criminal_case_types_not_embedded"]), 4)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "ghc_case_types.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
