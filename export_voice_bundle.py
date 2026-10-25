#!/usr/bin/env python3
"""Writes the dependency-free bundle of the voice-and-authority rule for the Recourse site: authority.py, the sentence helpers it uses, and an __init__.py.
Nothing else from this repository is needed. No network, no cost. See VOICE_SITE_PATCH.md for where the site calls it.
  python3 -I export_voice_bundle.py OUT_DIR
"""
import os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
INIT = '''"""The voice-and-authority rule, exported from recourse-sci-pool (review_results/2026-10-25_voice_rule/ there says how it was measured).

    from passage_authority import authority
    v = authority.safe_classify(text, src={"court": "Gauhati High Court"})
    if v["blocked"]: ...                      # every word of it is a lawyer's or a party's: do not show it
    v["tier"], v["voice"], v["quote"]         # 1 Supreme Court / 2 High Court / 3 trial court; whose words they are; the part to quote

Nothing here says a case is good law, and nothing here is a finding that a passage is right or helpful."""
from . import authority, textutil
'''


def main(out):
    os.makedirs(out, exist_ok=True)
    shutil.copy(os.path.join(HERE, "authority.py"), os.path.join(out, "authority.py"))
    shutil.copy(os.path.join(HERE, "goodlaw", "textutil.py"), os.path.join(out, "textutil.py"))
    src = open(os.path.join(out, "authority.py"), encoding="utf-8").read()      # inside the bundle the two files sit side by side
    open(os.path.join(out, "authority.py"), "w", encoding="utf-8").write(src.replace("from goodlaw import textutil as TU", "from . import textutil as TU", 1))
    open(os.path.join(out, "__init__.py"), "w", encoding="utf-8").write(INIT)
    return sorted(os.listdir(out))


if __name__ == "__main__":
    print("bundle in", sys.argv[1] + ":", ", ".join(main(sys.argv[1])))
