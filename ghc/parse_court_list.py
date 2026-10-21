"""Parses one monthly list of judgments published by the Gauhati High Court ("JUDGMENTS FOR THE MONTH OF <MONTH>, <YEAR>", a Word table saved as PDF)
and matches each row with the open bucket's catalogue (by decision day and case number).
Usage: python3 -I parse_court_list.py LIST.pdf CATALOGUE.csv.gz OUT.csv"""
import csv, gzip, re, sys, collections
import pymupdf
ORD = re.compile(r"^(\d{1,2})(st|nd|rd|th)$"); MONTHS = "JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY AUGUST SEPTEMBER OCTOBER NOVEMBER DECEMBER".split()
norm = lambda s: re.sub(r"[^A-Z0-9]", "", s.upper())

def parse(pdf):
    d = pymupdf.open(pdf)
    L = [l.strip() for p in d for l in p.get_text().splitlines() if l.strip()]
    m = re.search(r"MONTH OF\s+([A-Z]+),?\s*(\d{4})", " ".join(L[:6]).upper())
    month, year = (MONTHS.index(m.group(1)) + 1, int(m.group(2))) if m else (None, None)
    rows, i = [], 0
    while i < len(L) - 1:
        if re.fullmatch(r"\d{1,3}", L[i]) and ORD.match(L[i + 1]):
            day = int(ORD.match(L[i + 1]).group(1)); j = i + 2; case = []
            while j < len(L) and not re.search(r"\d+\s*/\s*\d{4}", L[j]) and len(case) < 3: case.append(L[j]); j += 1
            if j < len(L): case.append(L[j]); j += 1
            p1 = []
            while j < len(L) and L[j].upper() != "VS" and len(p1) < 6: p1.append(L[j]); j += 1
            j += 1; rest = []
            while j < len(L) and not (re.fullmatch(r"\d{1,3}", L[j]) and j + 1 < len(L) and ORD.match(L[j + 1])): rest.append(L[j]); j += 1
            judges = [x for x in rest if re.match(r"(?i)^(the )?hon|^justice", x)]
            body = [x for x in rest if x not in judges]
            p2 = [x for x in body if x == x.upper()]; subj = [x for x in body if x != x.upper()]
            rows.append({"serial": int(L[i]), "day": day, "date": f"{year}-{month:02d}-{day:02d}" if month else "", "case_number": " ".join(case),
                         "petitioner": " ".join(p1), "respondent": " ".join(p2), "subject": " ".join(subj), "judges": " | ".join(judges)})
            i = j
        else: i += 1
    return rows

def main(pdf, catalogue, out):
    rows = parse(pdf)
    cat = list(csv.DictReader(gzip.open(catalogue, "rt")))
    idx = collections.defaultdict(list)
    for r in cat: idx[(r["decision_date"], norm(r["case_number"]))].append(r)
    for r in rows:
        m = idx.get((r["date"], norm(r["case_number"])))
        r["in_bucket"] = "yes" if m else "no"; r["bucket_key"] = m[0]["bucket_key"] if m else ""; r["bucket_bytes"] = m[0]["pdf_bytes"] if m else ""
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(rows), "rows;", sum(r["in_bucket"] == "yes" for r in rows), "found in the bucket;", sum(r["in_bucket"] == "no" for r in rows), "not found")
if __name__ == "__main__":
    main(*sys.argv[1:])
