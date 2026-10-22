"""What did the search index get from the court's newer archive, and does it agree with the text store? Reads files only: no network, no key, no spend, nothing changed.

    python review_tools/experiments/newer_index_check_2026-10-22.py --index-dir <checkout of claude/sci-index> --store corpus.sqlite --out review_results/2026-10-22_newer_index_check

Counts what the index's own ledger says about the extra blocks (ids from 2,000,000,000: the Gauhati High Court set below 2,000,250,000, the Supreme Court newer archive from it), prices
the tokens at the listed $0.12 per million, and then compares the Supreme Court newer-archive judgments the index embedded with the text store's verdict on each: a judgment of its own, or a
second copy of a bucket text (the same judgment the index already holds under a bucket id). It also compares the pairs the store calls copies with the pairs in the newest dedupe plan on the
index branch (state/fixes/plans), so that a person reading the plan can see what the store adds and where the two disagree. The plan is not applied by anything here.
"""
import argparse
import csv
import glob
import gzip
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

import sci_index as si  # noqa: E402
from goodlaw import corpus as K  # noqa: E402
from goodlaw import passage_input as PI  # noqa: E402

GHC_BASE, SCI_BASE, PRICE = 2_000_000_000, 2_000_250_000, 0.12


def kind(i):
    return "crawl" if i < 1_000_000_000 else ("bucket" if i < GHC_BASE else ("ghc_court" if i < SCI_BASE else "sci_newer"))


def runs(text, n=8, limit=20000):
    w = re.findall(r"[a-z0-9]+", text[:limit].lower())
    return {" ".join(w[i:i + n]) for i in range(max(len(w) - n + 1, 0))}


def share(a, b):
    ra, rb = runs(a), runs(b)
    return round(len(ra & rb) / min(len(ra), len(rb)), 3) if ra and rb else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--store", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    led = si.ledger(a.index_dir)
    res = {"by_source": {}}
    docs = {}
    for start, v in led.items():
        k = kind(start)
        g = res["by_source"].setdefault(k, {"blocks": 0, "docs_recorded": 0, "passages": 0, "tokens": 0})
        g["blocks"] += 1
        g["docs_recorded"] += v["docs"]
        g["passages"] += v["passages"]
        g["tokens"] += v["tokens"]
        if start >= 1_000_000_000:
            for line in gzip.open(os.path.join(a.index_dir, "index", v["base"] + ".docs.jsonl.gz"), "rt", encoding="utf-8"):
                r = json.loads(line)
                docs[r["doc"]] = r
    for k in ("ghc_court", "sci_newer"):
        g = res["by_source"][k]
        g["dollars_at_listed_price"] = round(g["tokens"] / 1e6 * PRICE, 2)
        ds = [r for d, r in docs.items() if kind(d) == k]
        g["judgments_kept"] = sum(1 for r in ds if "skip" not in r)
        g["skipped"] = dict(sorted({s: sum(1 for r in ds if r.get("skip") == s) for s in {r.get("skip") for r in ds if "skip" in r}}.items()))
    res["tokens_spent_ever"] = si.tokens_spent(a.index_dir)
    logs = []
    for p in sorted(glob.glob(os.path.join(a.index_dir, "state", "shifts", "20261022T*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        logs.append({k: d.get(k) for k in ("started_at", "ended_at", "ceiling", "stop_reason", "blocks_done", "docs_embedded", "passages", "tokens", "wasted_tokens")})
    res["shifts_on_2026_10_22"] = logs

    con = sqlite3.connect(f"file:{a.store}?mode=ro", uri=True)
    store = {r[0]: r for r in con.execute("select src_id, doc_key, dup_of, maybe_dup_of, id from docs where source='court'")}
    by_path = {d["src"]["path"]: i for i, d in docs.items() if kind(i) == "bucket" and d.get("src", {}).get("path")}
    kept_sci = {i: r for i, r in docs.items() if kind(i) == "sci_newer" and "skip" not in r}
    verdict = {"judgment": 0, "judgment_uncertain": 0, "copy_of_a_bucket_text": 0, "second_copy_inside_the_archive": 0, "not_in_the_store": 0}
    store_pairs = {}                                           # sci_newer index doc -> the index doc it copies
    for i, r in kept_sci.items():
        st = store.get(r["src"]["path"])
        if not st:
            verdict["not_in_the_store"] += 1
        elif st[2] is None:
            verdict["judgment_uncertain" if st[3] else "judgment"] += 1
        elif st[2].startswith("b"):
            verdict["copy_of_a_bucket_text"] += 1
            store_pairs[i] = by_path.get(st[2][1:])
        else:
            verdict["second_copy_inside_the_archive"] += 1
            other = next((j for j, rr in kept_sci.items() if rr["src"]["path"] and store.get(rr["src"]["path"]) and store[rr["src"]["path"]][1] == st[2]), None)
            store_pairs[i] = other
    res["sci_newer_kept_by_the_stores_verdict"] = verdict
    res["sci_newer_kept_passages_in_store_copies"] = sum(r.get("passages", 0) for i, r in kept_sci.items() if i in store_pairs)
    res["sci_newer_kept_passages_total"] = sum(r.get("passages", 0) for r in kept_sci.values())

    # what the pilot's connector makes of the extra judgments (goodlaw/passage_input.py): named, from where, under which court, and whether a copy is read as the judgment it copies
    idocs = PI.IndexDocs(list(docs.values()))
    who = PI.ChainIdentity(PI.CorpusIdentity(K.Corpus(a.store), idocs), PI.IndexRowIdentity(idocs))
    ident = {"sci_newer": {"kept": 0, "named": 0, "named_by_the_corpus": 0, "read_as_the_judgment_it_copies": 0, "courts": {}, "passages": 0, "passages_in_named": 0},
             "ghc_court": {"kept": 0, "named": 0, "named_by_the_corpus": 0, "read_as_the_judgment_it_copies": 0, "courts": {}, "passages": 0, "passages_in_named": 0}}
    for i, r in docs.items():
        k = kind(i)
        if k not in ident or "skip" in r:
            continue
        g = ident[k]
        n = r.get("passages", 0)
        g["kept"] += 1
        g["passages"] += n
        w = who(i)
        if w:
            g["named"] += 1
            g["passages_in_named"] += n
            g["named_by_the_corpus"] += 1 if w.name_source == "corpus" else 0
            g["courts"][w.court or "(none)"] = g["courts"].get(w.court or "(none)", 0) + 1
            own = K.newer_key({"diary_no": r["src"].get("case_id") or "", "decision_date": r["src"].get("date") or ""}) if k == "sci_newer" else None
            g["read_as_the_judgment_it_copies"] += 1 if (w.doc_key and own and w.doc_key != own) else 0
    res["pilot_identity"] = ident

    plans = sorted(glob.glob(os.path.join(a.index_dir, "state", "fixes", "plans", "*-plan.json")))
    plan_pairs = {}
    if plans:
        plan = json.load(open(plans[-1], encoding="utf-8"))
        res["dedupe_plan"] = {"file": os.path.basename(plans[-1]), "groups": len(plan["groups"]), "review_pairs": len(plan.get("review", [])), "rules": plan.get("rules")}
        for g in plan["groups"]:
            ids = [int(x) for x in g["members"]]
            sci = [x for x in ids if kind(x) == "sci_newer"]
            oth = [x for x in ids if kind(x) != "sci_newer"]
            for x in sci:
                plan_pairs[x] = (oth[0] if oth else None, g["keep"], g["reason"])
        res["dedupe_plan"]["groups_that_keep_the_newer_archive_copy"] = sum(1 for g in plan["groups"] if kind(int(g["keep"])) == "sci_newer")
        res["dedupe_plan"]["groups_that_keep_the_other_copy"] = sum(1 for g in plan["groups"] if kind(int(g["keep"])) != "sci_newer")
    both = sorted(i for i in store_pairs if i in plan_pairs)
    store_only = sorted(i for i in store_pairs if i not in plan_pairs)
    plan_only = sorted(i for i in plan_pairs if i not in store_pairs)
    res["comparison"] = {"store_copies_among_kept": len(store_pairs), "also_in_the_plan": len(both), "store_only": len(store_only), "plan_only": len(plan_only),
                         "store_only_passages": sum(kept_sci[i].get("passages", 0) for i in store_only if i in kept_sci)}

    rows = []
    for i in store_only:
        r = kept_sci[i]
        st = store[r["src"]["path"]]
        other = store_pairs[i]
        orow = con.execute("select t.text from docs d join texts t on t.id = d.id where d.doc_key=?", (st[2],)).fetchone()
        mine = con.execute("select t.text from texts t where t.id=?", (st[4],)).fetchone()
        rows.append({"index_doc": i, "title": r["src"].get("title"), "date": r["src"].get("date"), "passages": r.get("passages"), "store_key": st[1], "copy_of_store_key": st[2],
                     "copy_of_index_doc": other, "share_of_8_word_runs": share(mine[0], orow[0]) if orow and mine else None})
    rows.sort(key=lambda r: (-(r["passages"] or 0), r["index_doc"]))
    prow = []
    for i in plan_only:
        r = docs.get(i)
        st = store.get((r or {}).get("src", {}).get("path"))
        prow.append({"index_doc": i, "title": (r or {}).get("src", {}).get("title"), "date": (r or {}).get("src", {}).get("date"), "plan_pairs_it_with_index_doc": plan_pairs[i][0],
                     "plan_keeps": plan_pairs[i][1], "plan_reason": plan_pairs[i][2], "store_says": ("judgment of its own" if st and st[2] is None else (st[2] if st else "not in the store"))})
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "numbers.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    for name, data in (("store_copies_not_in_the_plan.csv", rows), ("plan_pairs_the_store_does_not_call_copies.csv", prow)):
        with open(os.path.join(a.out, name), "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0].keys()) if data else ["none"])
            w.writeheader()
            w.writerows(data)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
