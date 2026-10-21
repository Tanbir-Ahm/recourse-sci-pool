"""Re-fetches every English judgment whose result row is not ok (transient proxy or connection errors), once each, and replaces the row in that month's results.csv.
Usage: python3 -I retry_failed.py PDFDIR [REFRESH_LIST.csv.gz]   (then run store_text.py for the changed months)"""
import csv, glob, os, subprocess, sys, tempfile
pdfdir = sys.argv[1]; extra = sys.argv[2:] 
here = os.path.dirname(os.path.abspath(__file__)); changed = []
for rf in sorted(glob.glob(os.path.join(here, "20[0-9][0-9]-[0-9][0-9]", "results.csv"))):
    rows = list(csv.DictReader(open(rf)))
    bad = [r for r in rows if r["kind"] == "english judgment" and not r["status"].startswith("ok")]
    if not bad: continue
    with tempfile.TemporaryDirectory() as t:
        lf, out = os.path.join(t, "links.txt"), os.path.join(t, "res.csv")
        open(lf, "w").write("\n".join(r["url"] for r in bad) + "\n")
        subprocess.run([sys.executable, "-I", "-W", "ignore", os.path.join(here, "first_pass.py"), lf, pdfdir, out] + extra, check=False)
        new = {r["url"]: r for r in csv.DictReader(open(out))} if os.path.exists(out) else {}
    fixed = 0
    for i, r in enumerate(rows):
        if r["url"] in new and new[r["url"]]["status"].startswith("ok") and not r["status"].startswith("ok"): rows[i] = new[r["url"]]; fixed += 1
    with open(rf, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(os.path.basename(os.path.dirname(rf)), "retried", len(bad), "fixed", fixed, flush=True)
    if fixed: changed.append(rf)
print("CHANGED", " ".join(changed))
