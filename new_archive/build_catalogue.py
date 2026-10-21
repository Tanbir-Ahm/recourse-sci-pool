"""Builds catalogue.csv: one row per English judgment fetched from the court's newer archive, with its case name, numbers, date, link and
the translations the court lists for it. Names are read from page 1 of the judgment itself (the bucket's title is kept beside it when the bucket holds the same judgment).
Usage: python3 -I build_catalogue.py PDFDIR OUT.csv LINKS.txt RESULTS.csv [LINKS.txt RESULTS.csv ...]"""
import csv, os, re, sys, collections
import pymupdf

ROLE = re.compile(r"(?i)^[\s.…,:;()\-]*(appellants?|petitioners?|respondents?|applicants?|defendants?|plaintiffs?|opposite|contemnors?|caveators?|intervenors?|complainants?|accused)\b.*$|^[\s.…\-_]+$")
VS = re.compile(r"(?i)^\s*(versus|vs\.?|v\.?)\s*$")
STOP = re.compile(r"(?i)^\s*(with|and|j\s*u\s*d\s*g\s*m\s*e\s*n\s*t|o\s*r\s*d\s*e\s*r|reportable|non-?reportable|in the supreme court|\[?arising|\(?arising|civil appeal|criminal appeal|special leave|s\.l\.p|slp|writ petition|civil appellate|criminal appellate|original jurisdiction|appellate jurisdiction|\d{4}\s+insc|page\s+\d|\d+\s*$)")
YR = r"(?:\bof\s+|/)\s*(?:19|20)\d\d"
CASE = re.compile(r"(?i)((?:civil|criminal)\s+appeal[^\n]{0,60}?" + YR + r"|writ\s+petition[^\n]{0,60}?" + YR + r"|(?:special\s+leave\s+petition|slp)[^\n]{0,60}?" + YR + r"|(?:transfer|contempt|review|arbitration|curative)\s+petition[^\n]{0,60}?" + YR + r"|(?:civil|criminal)\s+misc[^\n]{0,60}?" + YR + r"|(?:civil|criminal)\s+appeal[^\n]{0,40})")

def clean(s):
    s = re.sub(r"[…]+|\.{2,}", " ", s)
    s = re.sub(r"(?i)\b(appellants?|respondents?|petitioners?)\s*\(s\)", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,;:-.")
    s = re.sub(r"(?i)(\s*\b(appellants?|respondents?|petitioners?|applicants?)\b\s*)+$", "", s).strip(" ,;:-.")
    while s.endswith(")") and s.count(")") > s.count("(") or s.startswith("(") and s.count("(") > s.count(")"):
        s = s[:-1].strip() if s.endswith(")") else s[1:].strip()
    return s

def parties(lines):
    k = next((i for i, l in enumerate(lines) if VS.match(l)), None)
    if k is None:
        return "", ""
    pet = []
    for l in reversed(lines[:k]):
        if STOP.match(l) or re.search(r"(?i)\bno\.?\s*\(?s?\)?\.?\s*[\d@]|\bof\s+\d{4}\b|arising", l): break
        if ROLE.match(l): 
            if pet: break
            continue
        pet.append(l)
    pet = list(reversed(pet))
    res = []
    for l in lines[k + 1:k + 8]:
        if STOP.match(l): break
        res.append(l)
        if re.search(r"(?i)(appellants?|respondents?|petitioners?|applicants?)\s*(\(s\))?\s*\.?\s*$", l): break
    return clean(" ".join(pet)), clean(" ".join(res))

def name_key(s):
    s = re.sub(r"(?i)\bm/s\.?", "ms", s.lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s.replace("versus", " v ").replace(" vs ", " v "))
    return re.sub(r"\s+", " ", s).strip()

def main(pdfdir, out, *pairs):
    links, results = pairs[0::2], pairs[1::2]
    trans = collections.defaultdict(list)           # (diary, date) -> translation links
    for lf in links:
        for u in (l.strip() for l in open(lf) if l.strip()):
            m = re.search(r"/supremecourt_vernacular/(\d{4})/(\d+)/.*_Judgement_(\d\d-[A-Za-z]{3}-\d{4})_([A-Z]{3})\.pdf$", u)
            if m: trans[(m.group(2) + "/" + m.group(1), m.group(3).title())].append(m.group(4) + "=" + u)
    rows = []
    for rf in results:
        for r in csv.DictReader(open(rf)):
            if r["kind"] != "english judgment" or not r["status"].startswith("ok"): continue
            d, y = r["diary"].split("/")
            f = os.path.join(pdfdir, f"{d}_{y}_{r['date']}.pdf")
            doc = pymupdf.open(f); t = doc[0].get_text()
            lines = [l.strip() for l in t.splitlines() if l.strip()]
            pet, res = parties(lines)
            ncite = re.search(r"\b(20\d\d)\s+INSC\s+(\d+)\b", t)
            cn = CASE.search(re.sub(r"\s+", " ", t[:1500]))
            dd, mm, yy = r["date"].split("-")
            mon = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()[int(mm) - 1]
            name = f"{pet} versus {res}" if pet and res else ""
            bname = r["bucket_title"] if r["bucket_match"] == "yes" else ""
            rows.append({
                "case_name": name or bname, "petitioner": pet, "respondent": res, "name_key": name_key(name or bname),
                "case_number": re.sub(r"\s+", " ", cn.group(1)).strip() if cn else "", "diary_no": r["diary"],
                "decision_date": f"{yy}-{mm}-{dd}", "neutral_citation": f"{ncite.group(1)} INSC {ncite.group(2)}" if ncite else "",
                "reportable": r["reportable"] or "unmarked", "criminal_heading": r["criminal"], "pages": r["pages"],
                "pdf_url": r["url"], "translations": " ".join(trans.get((r["diary"], f"{dd}-{mon}-{yy}"), [])),
                "in_bucket": r["bucket_match"], "bucket_title": bname, "sha256": r["sha256"], "fetched_on": "2026-10-21", "source": "court archive, newer path (api.sci.gov.in/supremecourt)",
            })
    rows.sort(key=lambda x: (x["decision_date"], x["diary_no"]))
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(rows), "rows;", sum(1 for r in rows if not r["petitioner"] or not r["respondent"]), "without a parsed pair of parties;", sum(1 for r in rows if not r["case_number"]), "without a case number;", sum(1 for r in rows if r["neutral_citation"]), "with a neutral citation;", sum(1 for r in rows if r["translations"]), "with translations")

if __name__ == "__main__":
    main(*sys.argv[1:])
