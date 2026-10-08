"""Currency pass: what the Overruled Register and a list of known-stale cases say about saved search results. PRIVATE, like the pool.

It is a second, separate pass. The relevance marks come from AI tools that see only a question and a passage; this pass never goes to them, so a version's relevance score and
its currency figures stay independent. Nothing here is a verdict on good law: the register only words what a row says, and the known-stale list is a short list of cases whose
later history is known from outside (`goodlaw/targets/known.json` plus `review_data/ruler/known_stale_extra.json`, none of it lawyer-checked).

For every search version in a pool file it reports, over the passages the version put on top (its top 5; the whole shown set for versions starting with S or M):
  * how many passages come from a case the register holds (firm row, candidate row) or name such a case;
  * how many come from a known-stale case ('stale slots') and how many of those the register flagged (the rest got through);
  * what the register's demotion lock would change: the same lists with firm-row cases moved to the end, and the stale slots left.
It also says which known-stale cases the register holds at all, and whether it wrongly flags any of the known-settled cases (a false alarm).

    python review_tools/currency_pass.py --corpus PATH/corpus.sqlite --out review_results/DATE_currency_pass
"""
import argparse
import collections
import glob
import gzip
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
from goodlaw import register as R            # noqa: E402
from goodlaw import register_guard as G      # noqa: E402

DEFAULT_POOL = os.path.join(ROOT, "review_data", "pool_all.json")
DEFAULT_KNOWN = os.path.join(ROOT, "goodlaw", "targets", "known.json")
DEFAULT_EXTRA = os.path.join(ROOT, "review_data", "ruler", "known_stale_extra.json")
DEFAULT_INDEX = os.path.normpath(os.path.join(ROOT, "..", "recourse-sci-index"))
WHOLE_SET = ("S", "M")                       # scored on everything they showed, as in the relevance reader
STALE = ("adverse", "adverse_in_part")


def case_table(index_dir, corpus_path):
    """{index doc id: {doc_key, pet, resp, year, insc}}: the corpus store's description of each judgment the index holds."""
    bypath = {}
    for f in glob.glob(os.path.join(index_dir, "index", "*.docs.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if isinstance(r.get("src"), dict) and r["src"].get("path"):
                    bypath[r["src"]["path"]] = r["doc"]
    con = sqlite3.connect(corpus_path)
    out = {}
    for doc_key, src, sid, bp, pet, resp, year, insc in con.execute("select doc_key, source, src_id, bucket_path, pet, resp, year, insc from docs"):
        d = int(sid) if src == "crawl" else bypath.get(bp)
        if d is not None:
            out.setdefault(d, {"doc_key": doc_key, "pet": pet, "resp": resp, "year": year, "insc": insc})
    return out


def known_cases(known_path=DEFAULT_KNOWN, extra_path=DEFAULT_EXTRA):
    """[{name, doc_key, expect, basis}]; expect is adverse, adverse_in_part or not_adverse."""
    out = list(json.load(open(known_path, encoding="utf-8"))["cases"])
    if extra_path and os.path.exists(extra_path):
        out += json.load(open(extra_path, encoding="utf-8"))["cases"]
    return out


def name_year(label):
    """('Prabha Shankar Dubey v. State of M.P.', 2003) from 'Prabha Shankar Dubey v. State of M.P. (2003)'."""
    m = re.match(r"^(.*?)\s*\((\d{4})\)\s*$", label or "")
    return (m.group(1), int(m.group(2))) if m else (label, None)


def chunk(info, text):
    """What the register's retrieval lock wants: {case_name, year, citation, text}."""
    name = f"{info['pet']} v {info['resp']}" if info and info.get("pet") else None
    return {"case_name": name, "year": info.get("year") if info else None, "citation": info.get("insc") if info else None, "text": text}


def top_rows(rows, version, k):
    """The rows a version put on top, best first. Versions starting with S or M are taken whole."""
    got = sorted((r for r in rows if version in r["variants"]), key=lambda r: r["variants"][version])
    return got if version.split(" ")[0] in WHOLE_SET else got[:k]


def demoted(rows, flags_by_id, k, version):
    """The same version's list with firm-row cases moved to the end (what lock (a) does), cut to the same size."""
    got = sorted((r for r in rows if version in r["variants"]), key=lambda r: r["variants"][version])
    keep = [r for r in got if flags_by_id[id(r)]["action"] != "demote_and_badge"]
    last = [r for r in got if flags_by_id[id(r)]["action"] == "demote_and_badge"]
    ordered = keep + last
    return ordered if version.split(" ")[0] in WHOLE_SET else ordered[:k]


def register_view(reg, cases):
    """For each known case: does the register hold it, and on what trust. Settled cases the register flags are false alarms."""
    out = []
    for c in cases:
        name, year = name_year(c["name"])
        hits = [h for h in reg.lookup_case(name, year, None) if h["strength"] == "strong" and reg.clause(h["row"])]
        out.append({"name": c["name"], "expect": c["expect"], "in_register": bool(hits), "trust": sorted({h["row"]["trust"] for h in hits}),
                    "false_alarm": bool(hits) and c["expect"] == "not_adverse"})
    return out


def analyse(pool, reg, table, cases, k=5):
    key_doc = {info["doc_key"]: d for d, info in table.items()}
    stale = {key_doc[c["doc_key"]]: c["name"] for c in cases if c["expect"] in STALE and c.get("doc_key") in key_doc}
    settled = {key_doc[c["doc_key"]]: c["name"] for c in cases if c["expect"] == "not_adverse" and c.get("doc_key") in key_doc}
    flags_by_id, unmapped = {}, 0
    for q in pool:
        fl = G.retrieval_flags(reg, [chunk(table.get(r["doc"]), r["text"]) for r in q["rows"]])
        for r, f in zip(q["rows"], fl):
            flags_by_id[id(r)] = f
            unmapped += table.get(r["doc"]) is None
    versions = sorted({v for q in pool for r in q["rows"] for v in r["variants"]})
    per, listed = {}, []
    for v in versions:
        s = collections.Counter()
        for q in pool:
            top = top_rows(q["rows"], v, k)
            if not top:
                continue
            s["questions"] += 1
            for r in top:
                f = flags_by_id[id(r)]
                s["slots"] += 1
                s["own_firm"] += f["action"] == "demote_and_badge"
                s["own_candidate"] += f["action"] == "badge"
                s["names_flagged_case"] += f["action"] == "note"
                if r["doc"] in stale:
                    s["stale_slots"] += 1
                    s["stale_slots_flagged"] += f["action"] in ("demote_and_badge", "badge")
                    listed.append({"qid": q["qid"], "n": r["n"], "version": v, "doc": r["doc"], "case": stale[r["doc"]], "register_action": f["action"]})
                if r["doc"] in settled and f["action"] in ("demote_and_badge", "badge"):
                    s["settled_slots_flagged"] += 1
            after = demoted(q["rows"], flags_by_id, k, v)
            s["after_slots_changed"] += len({id(r) for r in top} - {id(r) for r in after})
            s["after_stale_slots"] += sum(1 for r in after if r["doc"] in stale)
        per[v] = dict(s)
    return {"top_k": k, "versions": per, "stale_slots": listed, "stale_docs": {str(d): n for d, n in stale.items()}, "settled_docs": {str(d): n for d, n in settled.items()},
            "passages": sum(len(q["rows"]) for q in pool), "passages_without_case_info": unmapped, "register": register_view(reg, cases)}


def report(res):
    L = ["# Currency pass (PRIVATE)", "",
         "**Source label: register and known-stale list only. Not relevance marks, not lawyer-checked. Never send to reviewers.** The register only subtracts trust or warns; it never says a case is good law.", "",
         f"{res['passages']} passages; {res['passages_without_case_info']} without case information. Top {res['top_k']} per version (the whole shown set for S and M versions).", ""]
    reg = res["register"]
    stale = [x for x in reg if x["expect"] in STALE]
    L += ["## Does the register hold the known-stale cases?", "",
          f"{sum(1 for x in stale if x['in_register'])} of {len(stale)} known-stale cases have a row the register would word. Those without one cannot be flagged, however well the search finds them.", "",
          "| Known-stale case | In the register | Trust |", "|---|---|---|"]
    L += [f"| {x['name']} | {'yes' if x['in_register'] else '**no**'} | {', '.join(x['trust']) or '-'} |" for x in stale]
    fa = [x for x in reg if x["false_alarm"]]
    L += ["", f"False alarms: {len(fa)} of {sum(1 for x in reg if x['expect'] == 'not_adverse')} known-settled cases are wrongly held by the register" + (": " + "; ".join(x["name"] for x in fa) if fa else "."), "",
          "## Per search version", "",
          "| Version | Questions | Top slots | Own case held (firm / candidate) | Names a held case | Known-stale slots | of which register flagged | After demotion: slots changed | After demotion: stale slots |", "|---|---|---|---|---|---|---|---|---|"]
    for v, s in res["versions"].items():
        L.append(f"| {v} | {s.get('questions', 0)} | {s.get('slots', 0)} | {s.get('own_firm', 0)} / {s.get('own_candidate', 0)} | {s.get('names_flagged_case', 0)} | {s.get('stale_slots', 0)} | "
                 f"{s.get('stale_slots_flagged', 0)} | {s.get('after_slots_changed', 0)} | {s.get('after_stale_slots', 0)} |")
    L += ["", "A known-stale slot is a passage from a case whose view has since been overtaken; it counts against a version whatever the relevance marks say. 'Flagged' means the register would have badged or demoted it; the rest would have gone out unwarned.", "",
          "## The stale passages", "", "| Question | Passage | Version | Case | Register action |", "|---|---|---|---|---|"]
    L += [f"| {x['qid']} | {x['n']} | {x['version']} | {x['case']} | {x['register_action'] or 'none'} |" for x in res["stale_slots"]]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pool", default=DEFAULT_POOL)
    ap.add_argument("--index", default=DEFAULT_INDEX)
    ap.add_argument("--corpus", required=True, help="the corpus store (corpus.sqlite)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--known", default=DEFAULT_KNOWN)
    ap.add_argument("--extra", default=DEFAULT_EXTRA)
    ap.add_argument("--top-k", type=int, default=5)
    a = ap.parse_args(argv)
    pool = json.load(open(a.pool, encoding="utf-8"))
    res = analyse(pool, R.Register.load(), case_table(a.index, a.corpus), known_cases(a.known, a.extra), a.top_k)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "currency_pass.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(a.out, "CURRENCY_PASS.md"), "w", encoding="utf-8") as fh:
        fh.write(report(res))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
