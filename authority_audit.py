#!/usr/bin/env python3
"""Runs authority.py over every passage of a finished index and prints the counts, so a change in the rules shows up as a change in numbers. No network, no
model, no spending; nothing is written to the index.

Two uses. As a **baseline**: the counts of 2026-10-25 are recorded in review_results/2026-10-25_voice_rule/RESULTS_IN_PLAIN_TERMS.md, and a later run that moves
them has changed what the site would show. As a **check**: `--assert-baseline FILE` fails if the share of blocked passages, or of any tier, has moved by more
than the tolerance, which is what would happen if a cue were broken by an edit (one spliced alternative once made a bare court word match on its own).

  python3 -I authority_audit.py INDEX_DIR [--out counts.json] [--assert-baseline counts.json] [--tolerance 0.02] [--limit N]
"""
import argparse, collections, glob, gzip, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # python3 -I drops the script's own directory

import authority as A
import sci_index as si


def audit(index_dir, limit=None):
    metas, _, _ = si._load_index(index_dir)
    src = {}
    for f in sorted(glob.glob(os.path.join(index_dir, "index", "*.docs.jsonl.gz"))):
        for line in gzip.open(f, "rt", encoding="utf-8"):
            r = json.loads(line)
            if r.get("src"):
                src[r["doc"]] = r["src"]
    rows = metas[:limit] if limit else metas
    counts = collections.Counter()
    t0 = time.time()
    for m in rows:
        v = A.safe_classify(m["text"], src=src.get(m["doc"]), doc=m["doc"])
        court = "HC" if (src.get(m["doc"]) or {}).get("court", "").find("High Court") >= 0 else "SC"
        counts["passages"] += 1
        counts[f"court:{court}"] += 1
        counts["blocked" if v["blocked"] else f"tier:{v['tier']}"] += 1
        counts[f"voice:{v['voice']}"] += 1
        if not v["blocked"] and not v["states_law"]:
            counts["states_no_law"] += 1
        if v["blocked"]:
            counts[f"blocked:{court}"] += 1
    counts["seconds"] = round(time.time() - t0)
    return counts


def shares(counts):
    n = counts["passages"] or 1
    return {k: counts[k] / n for k in counts if k.startswith(("tier:", "voice:")) or k in ("blocked", "states_no_law")}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("index_dir")
    p.add_argument("--out")
    p.add_argument("--assert-baseline")
    p.add_argument("--tolerance", type=float, default=0.02)
    p.add_argument("--limit", type=int)
    a = p.parse_args()
    counts = audit(a.index_dir, a.limit)
    n = counts["passages"]
    for k in sorted(counts):
        print(f"  {k:<22} {counts[k]:>8}" + (f"  {100 * counts[k] / n:5.1f}%" if k.startswith(("tier:", "voice:", "blocked", "court:", "states_no")) else ""))
    if a.out:
        json.dump(dict(counts), open(a.out, "w"), indent=1)
        print("written to", a.out)
    if a.assert_baseline:
        base = json.load(open(a.assert_baseline, encoding="utf-8"))
        now, then = shares(counts), shares(collections.Counter(base))
        bad = [(k, then.get(k, 0), now.get(k, 0)) for k in set(now) | set(then) if abs(now.get(k, 0) - then.get(k, 0)) > a.tolerance]
        for k, b, c in sorted(bad):
            print(f"MOVED {k}: {100 * b:.1f}% -> {100 * c:.1f}%")
        print(f"{'FAIL' if bad else 'OK'}: {len(bad)} share(s) moved by more than {100 * a.tolerance:.0f} points")
        sys.exit(1 if bad else 0)
