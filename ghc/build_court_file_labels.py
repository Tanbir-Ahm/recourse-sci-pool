"""Builds court_lists/court_file_labels.csv: for each court file of 2010-2017 in the index (scope ghc_court, not skipped), the title, case number and bench read from the monthly lists
by position (reparse_court_lists.py) in place of the ones stored when the files were indexed (hc_labels.py reads this table). A document is matched to its list row by the file name of its
address, its date and its first case number. Nothing may be added that the stored title and citation did not hold, and every word taken out of the title must stand in the row's judge or
subject text; a document that fails a test stops the run, so the table cannot hold an invented word.
Usage: python3 -I build_court_file_labels.py INDEX_DIR REPARSED_ROWS.csv.gz OUT.csv"""
import collections, csv, glob, gzip, json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import hc_labels as hl
norm = lambda s: re.sub(r"[^A-Z0-9]", "", s.upper())
words = lambda s: collections.Counter(w for w in re.findall(r"[A-Z0-9]+", s.upper()) if w != "VS")

def main(index_dir, rows_csv, out):
    by = collections.defaultdict(list)
    for r in csv.DictReader(gzip.open(rows_csv, "rt", encoding="utf-8", newline="")):
        if r["judgment_url"]: by[hl.leaf(r["judgment_url"])].append(r)
    docs = []
    for f in sorted(glob.glob(os.path.join(index_dir, "index", "*.docs.jsonl.gz"))):
        for l in gzip.open(f, "rt", encoding="utf-8"):
            r = json.loads(l)
            if (r.get("src") or {}).get("scope") == "ghc_court" and not r.get("skip"): docs.append((r["doc"], r["src"]))
    rows, how = [], collections.Counter()
    for doc, s in sorted(docs):
        first = hl.case_numbers(s["citation"]).split(" ; ")[0]
        m = [r for r in by.get(hl.leaf(s["url"]), []) if r["date"] == s["date"] and norm(r["case_number"]) == norm(first)]
        if not m: raise SystemExit(f"doc {doc}: no list row for {s['url']} {s['date']} {first}")
        n = m[0]; title = hl.squash(" Vs ".join(x for x in (n["petitioner"], n["respondent"]) if x)); old = hl.squash(s["title"]); cits = hl.case_numbers(s["citation"])
        removed, added = words(old) - words(title), words(title) - words(old)
        if added and not set(added) <= set(words(s["citation"])): raise SystemExit(f"doc {doc}: words not in the stored title or citation: {dict(added)}")
        if removed and not set(removed) <= set(words(n["judges"])) | set(words(n["subject"])): raise SystemExit(f"doc {doc}: words taken out that are not judge or subject text: {dict(removed)}")
        k = "rebuilt from the case number text" if added else "judge or subject words removed" if removed else "unchanged"; how[k] += 1
        b = hl.court_file_bench(cits, title)
        rows.append({"doc": doc, "url": s["url"], "date": s["date"], "case_number": cits, "title": title, "bench": b[0] if b else "", "state": b[1] if b else "", "how": k,
                     "old_title": old, "old_case_number": hl.squash(s["citation"]), "judges": n["judges"]})
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    return len(rows), how, collections.Counter(r["bench"] or "none" for r in rows)

if __name__ == "__main__":
    n, how, bench = main(*sys.argv[1:])
    print(n, "court files;", dict(how)); print("bench:", dict(bench))
