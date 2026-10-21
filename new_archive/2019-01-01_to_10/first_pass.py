"""First pass on a list of links from the court's newer archive: classify, fetch English judgments once each, extract text, compare with the bucket by date and party words.
Usage: python3 -I first_pass.py LINKS.txt WORKDIR OUT.csv   (PDFs stay in WORKDIR, outside the repo; text is not committed)"""
import csv, gzip, hashlib, os, re, sys, time, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import requests, pymupdf
from sci_crawl import classify_response, USER_AGENT

MON = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
PAT = re.compile(r"/(supremecourt|supremecourt_vernacular)/(\d{4})/(\d+)/[^/]*_(Judgement|Order)_(\d\d)-([A-Za-z]{3})-(\d{4})(_[A-Z]{3})?\.pdf$")
STOP = set("AND ANR ANOTHER OTHERS ORS STATE UNION INDIA THROUGH LTD PVT LIMITED THE VERSUS DEAD LRS BY".split())

def words(s):
    return {w for w in re.findall(r"[A-Z]{4,}", s.upper()) if w not in STOP}

def main(links_file, work, out):
    os.makedirs(work, exist_ok=True)
    rows = list(csv.DictReader(gzip.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "coverage", "bucket_match", "worklist.csv.gz"), "rt")))
    links = list(dict.fromkeys(l.strip() for l in open(links_file) if l.strip()))
    res, sess = [], requests.Session()
    sess.headers["User-Agent"] = USER_AGENT
    for u in links:
        m = PAT.search(u)
        r = {"url": u, "kind": "", "diary": "", "date": "", "status": "", "pages": "", "chars": "", "images": "", "reportable": "", "sha256": "", "bucket_match": "", "bucket_title": "", "bucket_same_day": ""}
        if not m:
            r["kind"] = "malformed (no diary number in the link)"; res.append(r); continue
        folder, year, diary, typ, dd, mon, yy, lang = m.groups()
        r["diary"] = f"{diary}/{year}"; r["date"] = f"{dd}-{MON[mon]:02d}-{yy}"
        if folder == "supremecourt_vernacular": r["kind"] = "vernacular " + (lang or "")[1:]; res.append(r); continue
        if typ != "Judgement": r["kind"] = "order"; res.append(r); continue
        r["kind"] = "english judgment"
        time.sleep(1.5 + random.random() * 0.5)
        try:
            resp = sess.get(u, timeout=60)
        except Exception as e:
            r["status"] = "error: " + type(e).__name__; res.append(r); continue
        kind, note = classify_response(resp.status_code, resp.headers.get("content-type"), resp.content, resp.headers.get("content-length"))
        r["status"] = kind + (": " + note if note else "")
        if kind in ("blocked", "challenge"):
            res.append(r); print("STOP:", r["status"], u); break
        if kind != "ok": res.append(r); continue
        path = os.path.join(work, f"{diary}_{year}_{r['date']}.pdf"); open(path, "wb").write(resp.content)
        r["sha256"] = hashlib.sha256(resp.content).hexdigest()
        d = pymupdf.open(path); t = "\n".join(p.get_text() for p in d)
        r["pages"], r["chars"], r["images"] = len(d), len(t), sum(len(p.get_images()) for p in d)
        head = d[0].get_text()[:700].upper()
        r["reportable"] = "NON-REPORTABLE" if re.search(r"NON[- ]?REPORTABLE", head) else ("REPORTABLE" if "REPORTABLE" in head else "")
        # bucket: same decision date, then party words found in the first 3000 characters
        day = [b for b in rows if b["decision_date"] == r["date"]]
        r["bucket_same_day"] = len(day)
        top = words(t[:3000]); best = (0, "")
        for b in day:
            w = words(b["petitioner"] + " " + b["respondent"])
            if w:
                sc = len(w & top) / len(w)
                if sc > best[0]: best = (sc, b["title"])
        if best[0] >= 0.6: r["bucket_match"], r["bucket_title"] = "yes", best[1][:60]
        else: r["bucket_match"] = "no"
        res.append(r)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0].keys())); w.writeheader(); w.writerows(res)
    print(len(res), "rows written to", out)

if __name__ == "__main__":
    main(*sys.argv[1:4])
