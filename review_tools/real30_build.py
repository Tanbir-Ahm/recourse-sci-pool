"""Builds the 30-question set from the owner's workbook (received 2026-10-09): the question file, the sealed split and the private key.

    python review_tools/real30_build.py build [--index-dir ../recourse-sci-index] [--force]
    python review_tools/real30_build.py check

`build` reads review_data/ruler/inputs/2026-10-09_owner_30_questions.xlsx and writes
  * review_data/ruler/real30_v1.json      the questions only (what searches, pools and reviewers may see), the link-first split, both freeze hashes, the index snapshot;
  * review_data/ruler/real30_key_v1.json  the private key: expected answers, authorities (key and older rulings, with whether the index can reach them), trap pairs, sources.
The key is never read by a search or a pack builder. The split follows `real30_links_v1.json` (a question that shares a case or doctrine group with a ruler topic takes that topic's side)
and the plain hash rule for the rest (real_questions.py). Both files are written before any search is run on these questions. PRIVATE, like the rest of review_data/.
"""
import argparse
import glob
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import real_questions as RQ

DATA = os.path.join(ROOT, "review_data", "ruler")
SOURCE = os.path.join(DATA, "inputs", "2026-10-09_owner_30_questions.xlsx")
LINKS = os.path.join(DATA, "real30_links_v1.json")
STALE = os.path.join(DATA, "real30_stale_status_v1.json")
COVERAGE = os.path.join(ROOT, "review_results", "2026-10-09_real30_file_review", "authority_coverage.json")
OUT_Q = os.path.join(DATA, "real30_v1.json")
OUT_KEY = os.path.join(DATA, "real30_key_v1.json")
DEFAULT_INDEX = os.path.normpath(os.path.join(ROOT, "..", "recourse-sci-index"))

PHRASING = {"E": "everyday", "L": "legal", "N": "narrative"}
SECTIONS = {"NEW": "BNS/BNSS", "OLD": "IPC/CrPC", "NONE": "none"}
CONTROL_KINDS = {"K1": "civil/tax/divorce", "K2": RQ.CUTOFF_TRAP, "K3": "statute table answers it"}   # K2 (Q29) is relabelled: older law answers it, so it is not a clean control
PROVENANCE = {"statement": "Owner, 2026-10-09: the questions were 'retrieved from real legal scenarios and from recognised government websites'. Checked: the story questions retell the reported case they test "
                           "(Q1, Q7, Q12, Q19). They are not client messages, and the file does not say which question came from which page.",
              "label": "re-told from reported cases and government sources (owner's statement); not client messages; per-question source not recorded",
              "reading": "every figure from this set is a best case: a question that describes the case it is meant to find is easier than a real client's"}


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def read_workbook(path=SOURCE):
    """(rows, key) from the owner's workbook. rows are intake dicts (RQ.COLUMNS plus owner_q); key maps 'Q1'.. to the answer-side fields."""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    traps, verify = {}, []
    if "Currency Traps" in wb.sheetnames:
        for r in list(wb["Currency Traps"].iter_rows(values_only=True))[1:]:
            if r and r[0]:
                traps[str(r[0]).strip()] = {"outdated": str(r[1] or "").strip(), "current": str(r[2] or "").strip(), "changed": str(r[3] or "").strip()}
    if "To Verify" in wb.sheetnames:
        verify = [str(r[1]).strip() for r in list(wb["To Verify"].iter_rows(values_only=True))[1:] if r and r[1]]
    rows, key = [], {}
    for r in list(wb["30 Questions"].iter_rows(values_only=True))[1:]:
        if not r or not r[0] or not r[3]:
            continue
        q, dom, _, text, phr, sec, cte, ctl, expected, authority, urls, conf = (list(r) + [None] * 12)[:12]
        q = str(q).strip()
        text = str(text).strip().strip('"“”').strip()
        trap, era = "no", "unsure"
        if cte and str(cte).startswith("CT"):
            trap = "yes" if "CT: Y" in cte else "no"
            era = "2017 or later" if "Era: Y" in cte else "before 2017"
        kind = str(ctl or "").split(":")[0].strip()
        rows.append({"owner_q": q, "id": "", "question": text, "kind": PHRASING[str(phr).strip()], "numbering": SECTIONS[str(sec).strip()], "domain": str(dom).strip(), "trap": trap,
                     "trap_note": "", "best_law_era": era, "language": "English", "control_type": CONTROL_KINDS.get(kind, "") if str(dom).strip() == "K" else "", "anonymised_ok": "yes"})
        key[q] = {"owner_q": q, "owner_control_label": str(ctl or "").strip(), "owner_ct_era": str(cte or "").strip(), "expected_answer": str(expected or "").strip(),
                  "key_authority_text": str(authority or "").strip(), "source_urls": [u.strip() for u in str(urls or "").split("\n") if u.strip()], "confidence": str(conf or "").strip("[] "),
                  "trap_pair": traps.get(q), "to_verify": [t for t in verify if re.search(rf"\b{q}\b", t)]}
    return rows, key


def read_links(path=LINKS):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["links"]


def index_snapshot(index_dir):
    """Which index the experiment runs on: the branch head and the counts, so that a later change of the index can be refused."""
    sha = subprocess.run(["git", "-C", index_dir, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    sys.path.insert(0, ROOT)
    import sci_index as si
    led = si.ledger(index_dir)
    embedded = 0
    for f in glob.glob(os.path.join(index_dir, "index", "*.docs.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    embedded += 1 if (r.get("skip") is None and r.get("passages", 0) > 0) else 0
    return {"branch": "claude/sci-index", "commit": sha, "judgments_embedded": embedded, "passages": sum(v["passages"] for v in led.values()),
            "note": "The experiment runs on this index only; a changed head is refused by the pool runner."}


def authorities_for(q, coverage, stale):
    """The authorities named for one question (owner's Q number), with whether the index holds them and what the older rulings' later history is."""
    out = []
    for c in coverage:
        if c["q"] != q:
            continue
        docs = sorted({h["index_doc"] for h in c["hits"] if h["state"] == "in_index"})
        a = {"label": c["label"], "role": c["role"], "where": c["where"], "doc_keys": [h["doc_key"] for h in c["hits"] if h["state"] == "in_index"], "index_docs": docs}
        if c["role"] == "stale":
            a["status"] = stale[c["label"]]
        out.append(a)
    return out


def build_key(rows, owner_key, coverage, stale, questions):
    """The private key, one entry per question id."""
    key = {}
    for q in questions:
        k = dict(owner_key[q["owner_q"]])
        auth = authorities_for(q["owner_q"], coverage, stale)
        key_auth = [a for a in auth if a["role"] == "key"]
        k.update({"id": q["id"], "authorities": auth,
                  "key_docs": sorted({d for a in key_auth for d in a["index_docs"]}),
                  "primary_key_docs": key_auth[0]["index_docs"] if key_auth else [],
                  "stale_docs": [{"doc": d, "label": a["label"], "kind": a["status"]["kind"], "counts_as_stale": a["status"]["counts_as_stale"]} for a in auth if a["role"] == "stale" for d in a["index_docs"]],
                  "reachable": bool(key_auth) and any(a["where"] == "in_index" for a in key_auth[:1]) if q["domain"] != "K" else None})
        key[q["id"]] = k
    return key


def build(index_dir=DEFAULT_INDEX, source=SOURCE, links_path=LINKS, coverage_path=COVERAGE, stale_path=STALE, today=None):
    rows, owner_key = read_workbook(source)
    prov = dict(PROVENANCE, source_file=os.path.relpath(source, ROOT), source_sha256=sha256_file(source))
    real, warnings, gaps = RQ.build(rows, today=today, links=read_links(links_path), snapshot=index_snapshot(index_dir), provenance=prov)
    with open(coverage_path, encoding="utf-8") as fh:
        coverage = json.load(fh)
    with open(stale_path, encoding="utf-8") as fh:
        stale = json.load(fh)["rulings"]
    key = {"schema": "real-key-1", "built": real["built"], "note": "PRIVATE answer key. Never sent to Voyage, ChatGPT, Gemini, J or S, and never read by a search or a pack builder. Expected answers and "
           "authorities are the owner's file (an AI research pass, only partly checked) plus this project's reading of the older rulings; none of it is lawyer-checked.",
           "source_sha256": prov["source_sha256"], "split_sha256": real["freeze"]["split_sha256"], "questions": build_key(rows, owner_key, coverage, stale, real["questions"])}
    return real, key, warnings, gaps


def check(real=None, key=None, ruler_path=None):
    """Problems: the question file's own check, the key matching it, the owner's file unchanged, the index head unchanged."""
    real = real or RQ.load(OUT_Q)
    with open(OUT_KEY, encoding="utf-8") as fh:
        key = key or json.load(fh)
    bad = RQ.check(real, ruler_path)
    if sorted(key["questions"]) != sorted(q["id"] for q in real["questions"]):
        bad.append("the key and the question file do not hold the same questions")
    if key.get("split_sha256") != real["freeze"]["split_sha256"]:
        bad.append("the key was built for a different split")
    src = os.path.join(ROOT, real["provenance"]["source_file"])
    if os.path.exists(src) and sha256_file(src) != real["provenance"]["source_sha256"]:
        bad.append("the owner's workbook has changed since the build")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--index-dir", default=DEFAULT_INDEX)
    b.add_argument("--force", action="store_true", help="overwrite existing files (this changes the seal; refused once any sealed question has been handed out)")
    sub.add_parser("check")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        bad = check(ruler_path=os.path.join(DATA, "ruler_v2.json"))
        print("problems:", bad or "none")
        return 1 if bad else 0
    if (os.path.exists(OUT_Q) or os.path.exists(OUT_KEY)) and not a.force:
        print("the question file or key exists; a rebuild changes the seal. Use --force only on purpose.")
        return 2
    if os.path.exists(OUT_Q) and RQ.read_runs(RQ.DEFAULT_RUNS):
        print("the sealed questions were already handed out; the question set can no longer be rebuilt.")
        return 2
    real, key, warnings, gaps = build(a.index_dir)
    for path, obj in ((OUT_Q, real), (OUT_KEY, key)):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    sealed = real["freeze"]["questions"]
    print(f"{len(real['questions'])} questions; sealed {len(sealed)}: {', '.join(sealed)}")
    print("freeze (sealed content)", real["freeze"]["sha256"])
    print("split (sides and links) ", real["freeze"]["split_sha256"])
    print("index snapshot", real["index_snapshot"]["commit"][:7], real["index_snapshot"]["passages"], "passages,", real["index_snapshot"]["judgments_embedded"], "judgments")
    for w in warnings:
        print("WARNING:", w)
    for g in gaps:
        print("GAP:", g)
    return 0


if __name__ == "__main__":
    sys.exit(main())
