"""Measuring the second reader (goodlaw.reader) against the two answer keys, on the tuning halves only.

build   draws the pairs and writes, for each, the passages a reader would see (batch.jsonl, items with opaque ids in a shuffled order, so a reader cannot tell which answer
        key a pair came from) and, apart, key.json (what the answer key and the pattern rules say about each id). A reader must not open key.json before it has written its
        verdicts.
score   reads the verdicts, checks them (goodlaw.reader.check_verdict) and compares: recall on the pairs the reporters marked adverse, and what the reader does with pairs
        the pattern rules wrongly flagged and with pairs they left alone.

Pairs: the old reporters' citator (development half, even target ids) and the 2017-2023 case-law tables (tuning half, by the citing judgment's hash), read on the court's
own text for the modern ones. The held-out and untouched halves are never touched here.
"""
import collections
import json
import os
import random

from . import evaluate as E
from . import modern_gold as G
from . import reader as R

ADVERSE_RULE = E.ADVERSE


def _rows(corpus_path, pairs, body_only, workers):
    return E.run(corpus_path, pairs, workers=workers, body_only=body_only)


def draw(corpus, corpus_path, seed=11, per_cell=24, workers=4, log=print):
    """-> list of dict(era, set, target, citing, code, rule_label, rule_eligible, rule_hedged, rule_binding) for the sampled pairs.
    sets: 'adverse' (reporter marked overruled / not followed; every pair with a confident mention), 'rule_flagged' (reporter marked it not adverse, rules read it adverse),
    'rule_quiet' (reporter marked it not adverse, rules read nothing adverse)."""
    rng = random.Random(seed)
    sampled = []
    for era in ("old", "modern"):
        if era == "old":
            pairs, _ = E.gold_pairs(corpus)
            dev, _held = E.split(pairs)
            body_only = False
        else:
            pairs, _ = G.gold_pairs(corpus)
            dev, _held = G.split(pairs)
            body_only = True
        log(f"{era}: reading {len(dev)} pairs with the pattern rules")
        rows = _rows(corpus_path, dev, body_only, workers)
        adverse_codes = {c for c, v in E.EXPECT.items() if v == "adverse"}
        adv, flagged, quiet = [], [], []
        for r in rows:
            t, c, code, cite, label, cue, sent, eligible, hedged, binding, speaker = r
            rec = {"era": era, "target": t, "citing": c, "code": code, "rule_label": label, "rule_eligible": bool(eligible), "rule_hedged": bool(hedged), "rule_binding": binding,
                   "body_only": body_only}
            if code in adverse_codes:
                if label is not None:
                    adv.append(rec)
            elif label is not None:
                (flagged if (label in ADVERSE_RULE and eligible) else quiet).append(rec)
        for name, pool in (("adverse", adv), ("rule_flagged", flagged), ("rule_quiet", quiet)):
            pick = pool if name == "adverse" else rng.sample(pool, min(per_cell, len(pool)))
            for rec in pick:
                rec["set"] = name
                rec["population"] = len(pool)
            sampled += pick
        log(f"{era}: adverse pairs with a mention {len(adv)}; rule-flagged non-adverse {len(flagged)}; rule-quiet non-adverse {len(quiet)}")
    return sampled


def build(corpus, corpus_path, out_dir, seed=11, per_cell=24, workers=4, log=print):
    sampled = draw(corpus, corpus_path, seed, per_cell, workers, log)
    rng = random.Random(seed + 1)
    rng.shuffle(sampled)
    os.makedirs(out_dir, exist_ok=True)
    key, n_items = {}, 0
    with open(os.path.join(out_dir, "batch.jsonl"), "w", encoding="utf-8") as fh:
        for rec in sampled:
            tdoc = corpus.get(rec["target"], with_text=False)
            cdoc = corpus.get(rec["citing"], with_text=False)
            mentions = E.mentions_in_doc(corpus, rec["target"], rec["citing"], rec["body_only"])
            item_id = f"r{n_items + 1:03d}"
            item = R.make_item(item_id, f"{tdoc['title']} ({tdoc.get('year')})", cdoc["title"], cdoc.get("date") or cdoc.get("year"), mentions)
            if item is None:
                continue
            n_items += 1
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
            key[item_id] = rec
    with open(os.path.join(out_dir, "key.json"), "w", encoding="utf-8") as fh:
        json.dump(key, fh, indent=1)
    with open(os.path.join(out_dir, "INSTRUCTIONS.txt"), "w", encoding="utf-8") as fh:
        fh.write(R.INSTRUCTIONS + "\n")
    log(f"{n_items} items written to {out_dir}")
    return n_items


def load_verdicts(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            v = json.loads(line)
            out[v["id"]] = v
    return out


def score(out_dir, verdicts_path):
    items = {}
    for line in open(os.path.join(out_dir, "batch.jsonl"), encoding="utf-8"):
        it = json.loads(line)
        items[it["id"]] = it
    key = json.load(open(os.path.join(out_dir, "key.json")))
    verdicts = load_verdicts(verdicts_path)
    checked = {i: R.check_verdict(items[i], verdicts[i]) for i in items if i in verdicts}
    table = collections.defaultdict(lambda: collections.Counter())
    for i, rec in key.items():
        if i not in checked:
            table[(rec["era"], rec["set"])]["unread"] += 1
            continue
        c = checked[i]
        cell = table[(rec["era"], rec["set"])]
        cell["n"] += 1
        cell["rule_adverse"] += bool(rec["rule_label"] in ADVERSE_RULE and rec["rule_eligible"])
        cell["reader_adverse"] += R.is_adverse(c)
        cell["reader_overrules"] += bool(c["valid"] and c["treatment"] == "OVERRULES" and c["quote_verified"])
        cell["either_adverse"] += bool(R.is_adverse(c) or (rec["rule_label"] in ADVERSE_RULE and rec["rule_eligible"]))
        cell["both_adverse"] += bool(R.is_adverse(c) and rec["rule_label"] in ADVERSE_RULE and rec["rule_eligible"])
        cell["unverified"] += int(not c["quote_verified"] and c["treatment"] in R.ADVERSE)
        cell["invalid"] += int(not c["valid"])
        cell["reader_unclear"] += int(c["treatment"] == "UNCLEAR")
    return {f"{era}/{s}": dict(v) for (era, s), v in sorted(table.items())}, checked
