"""Stores the extracted text of fetched judgments as monthly compressed shards on the data branch (claude/sci-court-newer).
Usage: python3 -I store_text.py PDFDIR DATA_WORKTREE RESULTS.csv [RESULTS.csv ...]
One shard per decision month: shards/YYYY-MM.jsonl.gz, one JSON object per judgment (raw text, pages joined by a form feed; nothing cleaned).
Idempotent: a judgment already in its shard (same pdf_url) is not added twice. PDFs are read from PDFDIR and never stored."""
import csv, gzip, json, os, re, sys
import pymupdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_catalogue import parties, CASE, name_key

def row_for(r, pdfdir):
    d, y = r["diary"].split("/")
    dd, mm, yy = r["date"].split("-")
    doc = pymupdf.open(os.path.join(pdfdir, f"{d}_{y}_{r['date']}.pdf"))
    pages = [p.get_text() for p in doc]
    t = pages[0]
    lines = [l.strip() for l in t.splitlines() if l.strip()]
    pet, res = parties(lines)
    nc = re.search(r"\b(20\d\d)\s+INSC\s+(\d+)\b", t)
    cn = CASE.search(re.sub(r"\s+", " ", t[:1500]))
    suo = res == "(suo motu / in re)"
    name = (pet if suo else f"{pet} versus {res}") if pet and res else ""
    bname = r["bucket_title"] if r["bucket_match"] == "yes" else ""
    return {"pdf_url": r["url"], "diary_no": r["diary"], "decision_date": f"{yy}-{mm}-{dd}", "case_name": name or bname,
            "petitioner": pet, "respondent": "" if suo else res, "case_number": re.sub(r"\s+", " ", cn.group(1)).strip() if cn else "",
            "neutral_citation": f"{nc.group(1)} INSC {nc.group(2)}" if nc else "", "reportable": r["reportable"] or "unmarked",
            "pages": len(pages), "sha256": r["sha256"], "in_bucket": r["bucket_match"], "bucket_title": bname,
            "source": "Supreme Court of India, api.sci.gov.in/supremecourt (newer archive)", "fetched_on": "2026-10-21",
            "text": "\n\f\n".join(pages)}

def main(pdfdir, data, *results):
    os.makedirs(os.path.join(data, "shards"), exist_ok=True); os.makedirs(os.path.join(data, "state"), exist_ok=True)
    sp = os.path.join(data, "state", "processed.json")
    done = json.load(open(sp)) if os.path.exists(sp) else {}
    new = {}
    for rf in results:
        for r in csv.DictReader(open(rf)):
            if r["kind"] != "english judgment" or not r["status"].startswith("ok"): continue
            dd, mm, yy = r["date"].split("-")
            new.setdefault(f"{yy}-{mm}", []).append(r)
    added = 0
    for month, rs in sorted(new.items()):
        path = os.path.join(data, "shards", f"{month}.jsonl.gz")
        have = {}
        if os.path.exists(path):
            for line in gzip.open(path, "rt", encoding="utf-8"):
                o = json.loads(line); have[o["pdf_url"]] = o
        for r in rs:
            if r["url"] not in have:
                have[r["url"]] = row_for(r, pdfdir); added += 1
        rows = sorted(have.values(), key=lambda o: (o["decision_date"], o["diary_no"]))
        with gzip.open(path + ".tmp", "wt", encoding="utf-8", compresslevel=9) as fh:
            for o in rows: fh.write(json.dumps(o, ensure_ascii=False) + "\n")
        os.replace(path + ".tmp", path)
    for rf in results: done[rf] = sum(1 for _ in csv.DictReader(open(rf)))
    json.dump(done, open(sp, "w"), indent=1, sort_keys=True)
    print(f"added {added} judgments to {len(new)} monthly shards")

if __name__ == "__main__":
    main(*sys.argv[1:])
