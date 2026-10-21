"""Parses the Gauhati High Court's monthly lists of judgments (2010 to 2017; "JUDGMENTS FOR THE MONTH OF <MONTH>, <YEAR>") and matches each row with the open bucket.
Rows start at an ordinal date ("5th"), optionally preceded by a serial number (older lists have none). Each row's hyperlink (to the judgment on ghconline.gov.in) is read from the PDF.
Usage: python3 -I parse_court_lists.py LISTS_DIR CATALOGUE.csv.gz OUT.csv"""
import collections, csv, glob, gzip, os, re, sys
import pymupdf
ORD = re.compile(r"^(\d{1,2})\s*(st|nd|rd|th)$", re.I)
MONTHS = "JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY AUGUST SEPTEMBER OCTOBER NOVEMBER DECEMBER".split()
norm = lambda s: re.sub(r"[^A-Z0-9]", "", s.upper())
CASEPAT = re.compile(r"\d+\s*/\s*\d{4}")
VS = re.compile(r"(?i)^(v\.?\s*/?\s*s\.?|versus)$")

def parse(pdf):
    d = pymupdf.open(pdf)
    lines = []  # (text, page, y)
    for pi, p in enumerate(d):
        for b in p.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                t = "".join(s["text"] for s in l["spans"]).strip()
                if t: lines.append((t, pi, l["bbox"]))
    head = " ".join(t for t, _, _ in lines[:8]).upper()
    m = re.search(r"MONTH OF\s+([A-Z]+),?\s*(\d{4})", head)
    month, year = (MONTHS.index(m.group(1)) + 1, int(m.group(2))) if m else (None, None)
    L = [t for t, _, _ in lines]
    rows, i = [], 0
    while i < len(L):
        if ORD.match(L[i]):
            serial = int(L[i - 1]) if i and re.fullmatch(r"\d{1,3}", L[i - 1]) else None
            day = int(ORD.match(L[i]).group(1)); j = i + 1; case = []
            while j < len(L) and not CASEPAT.search(L[j]) and len(case) < 3: case.append(L[j]); j += 1
            if j < len(L): case.append(L[j]); j += 1
            p1 = []
            while j < len(L) and not VS.match(L[j]) and not ORD.match(L[j]) and not (re.fullmatch(r"\d{1,3}", L[j]) and j + 1 < len(L) and ORD.match(L[j + 1])) and len(p1) < 6: p1.append(L[j]); j += 1
            if j < len(L) and VS.match(L[j]): j += 1
            rest = []
            while j < len(L) and not ORD.match(L[j]) and not (re.fullmatch(r"\d{1,3}", L[j]) and j + 1 < len(L) and ORD.match(L[j + 1])): rest.append(L[j]); j += 1
            judges = [x for x in rest if re.match(r"(?i)^(the )?hon|^justice", x)]
            body = [x for x in rest if x not in judges]
            rows.append({"serial": serial, "day": day, "date": f"{year}-{month:02d}-{day:02d}" if month else "", "case_number": " ".join(case),
                         "petitioner": " ".join(p1), "respondent": " ".join(x for x in body if x == x.upper()), "subject": " ".join(x for x in body if x != x.upper()),
                         "judges": " | ".join(judges), "_first": i, "_last": j})
            i = j
        else: i += 1
    # hyperlinks: the link whose text box lies on the row's case-number line(s)
    flat = [(pi, bb) for _, pi, bb in lines]
    links = []
    for pi, p in enumerate(d):
        for l in p.get_links():
            if l.get("uri"): links.append((pi, l["from"], l["uri"], norm(p.get_textbox(l["from"]))))
    ri = 0; assign = collections.defaultdict(list)
    for pi, rect, uri, tb in links:
        j = ri
        while j < len(rows) and not (tb and tb in norm(rows[j]["case_number"])): j += 1
        if j >= len(rows): j = min(ri, len(rows) - 1)
        if rows: assign[j].append(uri); ri = j
    for j, r in enumerate(rows):
        r["judgment_url"] = assign[j][0] if assign[j] else ""; r.pop("_first"); r.pop("_last")
    return year, month, rows, len(links)

def main(lists_dir, catalogue, out):
    cat = list(csv.DictReader(gzip.open(catalogue, "rt")))
    idx = collections.defaultdict(list)
    for r in cat: idx[(r["decision_date"], norm(r["case_number"]))].append(r)
    allrows = []; report = []
    for f in sorted(glob.glob(os.path.join(lists_dir, "*.pdf"))):
        try: year, month, rows, nl = parse(f)
        except Exception as e: report.append((os.path.basename(f), "ERROR " + type(e).__name__)); continue
        ser = [r["serial"] for r in rows if r["serial"]]
        report.append((os.path.basename(f), year, month, len(rows), nl, sum(bool(r["judgment_url"]) for r in rows), (max(ser) if ser else "-")))
        for r in rows:
            m = idx.get((r["date"], norm(r["case_number"])))
            r.update(list_file=os.path.basename(f), in_bucket="yes" if m else "no", bucket_key=m[0]["bucket_key"] if m else "", bucket_bytes=m[0]["pdf_bytes"] if m else "")
            allrows.append(r)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(allrows[0].keys())); w.writeheader(); w.writerows(allrows)
    return report, allrows

if __name__ == "__main__":
    rep, rows = main(*sys.argv[1:])
    for r in rep: print(*r)
    print(len(rows), "judgments listed;", sum(r["in_bucket"] == "yes" for r in rows), "found in the bucket")
