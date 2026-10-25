"""Re-reads the Gauhati High Court's monthly lists of judgments (2010 to 2017; "JUDGMENTS FOR THE MONTH OF <MONTH>, <YEAR>") with every word in the column it stands in.
parse_court_lists.py told the columns apart by how a line looked (a line that starts "the hon" or "justice" is a judge, any other capitals are the respondent) and found a
case number by `digits/year`, so (1) a judge's name that wrapped onto a second line (MADAN B. LOKUR, GOSWAMI) was read as part of the respondent: 333 of the 631 stored titles
whose respondent is a State or the Union end with a judge's name; and (2) a case number with a bench in brackets (77(AT)/2010) was not found, so the next three lines (the
parties) were swallowed into the case number and the columns of that row shifted (166 of the 1,830 rows of missing_judgments_all.csv).
Here the judge column starts at the x of the header "JUDGMENT DELIVERED BY", the subject column at the x of "SUBJECT", and the case number may carry a bench in brackets.
Rows, serial numbers, dates and links are found as before. Usage: python3 -I reparse_court_lists.py LISTS_DIR OUT.csv[.gz]"""
import collections, csv, glob, gzip, os, re, sys
import pymupdf
ORD = re.compile(r"^(\d{1,2})\s*(st|nd|rd|th)$", re.I)
MONTHS = "JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY AUGUST SEPTEMBER OCTOBER NOVEMBER DECEMBER".split()
norm = lambda s: re.sub(r"[^A-Z0-9]", "", s.upper())
CASEPAT = re.compile(r"\d+\s*(?:\(\s*[A-Za-z]+\s*\))?\s*/\s*\d{4}")
VS = re.compile(r"(?i)^(v\.?\s*/?\s*s\.?|versus)$")
VS_IN = re.compile(r"(?<!\w)(?:VS|Vs|V/S|VERSUS)(?!\w)")
JUDGE = re.compile(r"(?i)^(the )?hon.{0,3}ble\b|^justice\b")
NEW_JUDGE = re.compile(r"(?<!\bTHE)\s+(?=(?:THE\s+)?HON.{0,3}BLE\b)", re.I)

def columns(d):
    """x of the headers JUDGMENT DELIVERED BY and SUBJECT (None when the list has no subject column), read on the first page."""
    W = d[0].get_text("words")
    for k, w in enumerate(W):
        if w[4].upper().startswith("DELIVERED"):
            b = next((b for b in W[max(0, k - 3):k] if b[4].upper().startswith("JUDGMENT") and abs(b[1] - w[1]) < 3), None)
            if b:
                s = [x[0] for x in W if x[4].upper().startswith("SUBJECT") and abs(x[1] - w[1]) < 12]
                return b[0], (s[0] if s else None)
    raise ValueError("no JUDGMENT DELIVERED BY header on the first page")

def lines(d, jx, sx):
    """[[party-column text, subject-column text, judge-column text, page, bbox]] one per text line in reading order; each word goes to the column it stands in."""
    out = []
    for pi, p in enumerate(d):
        key = None
        for x0, y0, x1, y1, w, bn, ln, wn in p.get_text("words"):
            if (bn, ln) != key: out.append(["", "", "", pi, (x0, y0, x1, y1)]); key = (bn, ln)
            c = 2 if x0 >= jx - 6 else 1 if sx and x0 >= sx - 6 else 0
            out[-1][c] = (out[-1][c] + " " + w).strip()
    for l in out:                                       # a judge's name set in the subject column (seen once, June 2012) is still a judge's name; in the party column it may be a party ("The Hon'ble Gauhati High Court & Ors")
        if JUDGE.match(l[1]) and not l[2]: l[2], l[1] = l[1], ""
    return out

def judges_of(parts):
    """The judge-column lines of a row as a list of judges: a new judge starts at "THE HON'BLE" / "HON'BLE", any other line goes on with the last."""
    j = []
    for t in parts:
        for k, x in enumerate(NEW_JUDGE.split(t)):
            if k == 0 and j and not JUDGE.match(x): j[-1] += " " + x
            else: j.append(x)
    return j

def parse(pdf):
    d = pymupdf.open(pdf); jx, sx = columns(d); L = lines(d, jx, sx)
    head = " ".join(" ".join(l[:3]) for l in L[:8]).upper()
    m = re.search(r"MONTH OF\s+([A-Z]+),?\s*(\d{4})", head)
    month, year = (MONTHS.index(m.group(1)) + 1, int(m.group(2))) if m else (None, None)
    starts = [k for k, l in enumerate(L) if ORD.match(l[0]) and not l[1] and not l[2]]
    rows = []
    for n, s in enumerate(starts):
        e = starts[n + 1] if n + 1 < len(starts) else len(L)
        seg = L[s + 1:e]
        if n + 1 < len(starts) and seg and re.fullmatch(r"\d{1,3}", seg[-1][0]) and not seg[-1][1] and not seg[-1][2]: seg = seg[:-1]
        serial = int(L[s - 1][0]) if s and re.fullmatch(r"\d{1,3}", L[s - 1][0]) and not L[s - 1][1] and not L[s - 1][2] else None
        c0 = [l[0] for l in seg if l[0]]; case = []
        while c0 and not CASEPAT.search(c0[0]) and len(case) < 3: case.append(c0.pop(0))
        if c0: case.append(c0.pop(0))
        p1 = []
        while c0 and not VS.match(c0[0]): p1.append(c0.pop(0))
        if c0: c0.pop(0)
        day = int(ORD.match(L[s][0]).group(1))
        rows.append({"serial": serial, "day": day, "date": f"{year}-{month:02d}-{day:02d}" if month else "", "case_number": " ".join(case), "petitioner": " ".join(p1),
                     "respondent": " ".join(c0), "subject": " ".join(l[1] for l in seg if l[1]), "judges": " | ".join(judges_of([l[2] for l in seg if l[2]]))})
    links, ri = [], 0
    for pi, p in enumerate(d):
        for l in p.get_links():
            if l.get("uri"): links.append((pi, l["from"], l["uri"], norm(p.get_textbox(l["from"]))))
    assign = collections.defaultdict(list)
    for pi, rect, uri, tb in links:
        j = ri
        while j < len(rows) and not (tb and tb in norm(rows[j]["case_number"])): j += 1
        if j >= len(rows): j = min(ri, len(rows) - 1)
        if rows: assign[j].append(uri); ri = j
    for j, r in enumerate(rows): r["judgment_url"] = assign[j][0] if assign[j] else ""
    return year, month, rows, len(links)

def main(lists_dir, out):
    allrows, report = [], []
    for f in sorted(glob.glob(os.path.join(lists_dir, "*.pdf"))):
        try: year, month, rows, nl = parse(f)
        except Exception as ex: report.append((os.path.basename(f), "ERROR " + type(ex).__name__ + ": " + str(ex)[:60])); continue
        report.append((os.path.basename(f), year, month, len(rows), nl, sum(bool(r["judgment_url"]) for r in rows)))
        for r in rows: r["list_file"] = os.path.basename(f); allrows.append(r)
    with (gzip.open(out, "wt", newline="", encoding="utf-8") if out.endswith(".gz") else open(out, "w", newline="", encoding="utf-8")) as fh:
        w = csv.DictWriter(fh, fieldnames=list(allrows[0].keys())); w.writeheader(); w.writerows(allrows)
    return report, allrows

if __name__ == "__main__":
    rep, rows = main(*sys.argv[1:])
    for r in rep: print(*r)
    print(len(rows), "judgments listed")
