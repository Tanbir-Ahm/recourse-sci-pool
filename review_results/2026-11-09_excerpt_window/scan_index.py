"""One pass over the newer wide index (audit copy of d8811a9): how long are the passages, how many are cut by the 600-character page excerpt and the 900-character window the answer model sees, and how many start with a court / bench / counsel heading.
Usage: python3 scan_index.py <index dir with *.meta.jsonl.gz> <out json>"""
import gzip, json, glob, re, sys, collections
HEAD = re.compile(r"^\W*(?:BEFORE\b|IN THE (?:SUPREME|HIGH) COURT|IN THE COURT OF|PETITIONER\s*:|APPELLANT\s*:|REPORTABLE|NON-?\s*REPORTABLE|CRIMINAL (?:APPELLATE|ORIGINAL|REVISIONAL) JURISDICTION|CIVIL APPELLATE|Page No\.?\s*#|THE GAUHATI HIGH COURT|GAUHATI HIGH COURT|HIGH COURT OF|JUDGMENT AND ORDER|JUDGMENT\b|ORDER\b|CAV\b|PRESENT\s*:|CORAM\s*:|HON'?BLE|HONOURABLE|Heard\b|Case No\.?\s*:|BENCH\s*:)", re.I)
d = sys.argv[1]; out = sys.argv[2]
rows = []
n = 0
for f in sorted(glob.glob(d + "/*.meta.jsonl.gz")):
    with gzip.open(f, "rt") as fh:
        for l in fh:
            m = json.loads(l)
            t = m.get("text") or ""
            rows.append((n, m["doc"], len(t), 1 if HEAD.match(t) else 0, 1 if str(m.get("pn") or "").startswith("preamble") or m.get("section") == "header" else 0))
            n += 1
json.dump(rows, open(out, "w"))
print("passages", n)
