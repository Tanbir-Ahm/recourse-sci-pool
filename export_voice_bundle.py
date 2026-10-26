#!/usr/bin/env python3
"""Writes the dependency-free bundle of the voice-and-authority rule for the Recourse site: authority.py, the sentence helpers it uses, and an __init__.py.
Nothing else from this repository is needed. No network, no cost. See VOICE_SITE_PATCH.md for where the site calls it.
  python3 -I export_voice_bundle.py OUT_DIR
"""
import csv, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
INIT = '''"""The voice-and-authority rule, exported from recourse-sci-pool (review_results/2026-10-25_voice_rule/ there says how it was measured).

    from passage_authority import authority
    v = authority.safe_classify(text, src={"court": "Gauhati High Court"})
    if v["blocked"]: ...                      # every word of it is a lawyer's or a party's: do not show it
    v["tier"], v["voice"], v["quote"]         # 1 Supreme Court / 2 High Court / 3 trial court; whose words they are; the part to quote

    lab = hc_labels.card(src_of_the_judgment, result)       # heading, bench_label, url, voice_line, quote  (src: the stored fields of the judgment)

Nothing here says a case is good law, and nothing here is a finding that a passage is right or helpful."""
from . import authority, hc_labels, textutil
'''


def main(out):
    os.makedirs(out, exist_ok=True)
    shutil.copy(os.path.join(HERE, "authority.py"), os.path.join(out, "authority.py"))
    shutil.copy(os.path.join(HERE, "goodlaw", "textutil.py"), os.path.join(out, "textutil.py"))
    src = open(os.path.join(out, "authority.py"), encoding="utf-8").read()      # inside the bundle the two files sit side by side
    open(os.path.join(out, "authority.py"), "w", encoding="utf-8").write(src.replace("from goodlaw import textutil as TU", "from . import textutil as TU", 1))
    shutil.copy(os.path.join(HERE, "hc_labels.py"), os.path.join(out, "hc_labels.py"))
    keep = ("url", "date", "case_number", "title", "bench", "state")                    # the slim table: no old wording, no judges' names
    rows = list(csv.DictReader(open(os.path.join(HERE, "ghc", "court_lists", "court_file_labels.csv"), encoding="utf-8", newline="")))
    with open(os.path.join(out, "court_file_labels.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(keep)); w.writeheader(); w.writerows({k: r[k] for k in keep} for r in rows)
    open(os.path.join(out, "__init__.py"), "w", encoding="utf-8").write(INIT)
    return sorted(os.listdir(out))


if __name__ == "__main__":
    print("bundle in", sys.argv[1] + ":", ", ".join(main(sys.argv[1])))
