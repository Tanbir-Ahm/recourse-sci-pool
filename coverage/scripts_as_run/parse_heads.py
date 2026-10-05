import gzip, json, re, sys, collections
sys.path.insert(0, "/home/user/recourse-sci-pool")
import sci_index as si
S = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad"
# old-format block, searched anywhere in the first 3,000 characters (the raw text opens with 'http://JUDIS.NIC.IN / SUPREME COURT OF INDIA / Page 1 of N')
OLD = re.compile(r"CASE NO\.?:?\s*(?P<caseno>.*?)\s*PETITIONER:\s*(?P<pet>.*?)\s*RESPONDENT:\s*(?P<resp>.*?)\s*DATE OF JUDGMENT:?\s*(?P<date>\d{1,2}/\d{1,2}/\d{4}|\S+)", re.S)
OLD2 = re.compile(r"PETITIONER:\s*(?P<pet>.*?)\s*RESPONDENT:\s*(?P<resp>.*?)\s*(?:DATE OF JUDGMENT:?\s*(?P<date>\d{1,2}/\d{1,2}/\d{4}|\S+))?\s*(?:BENCH|JUDGMENT)", re.S)
VS = re.compile(r"(?P<pet>[^\n]{2,220}?)\s*[.…]{2,}\s*(?:Appellant|Petitioner|Applicant|Plaintiff)[^\n]{0,40}?\s+(?:V\.?|Vs\.?|Versus|v/s)\s*\.?\s+(?P<resp>.{2,220}?)\s*[.…]{2,}\s*(?:Respondent|Defendant|Opposite)", re.I | re.S)
DATE = re.compile(r"(?:Dated|Date)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4})|\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4})", re.I)
kinds = collections.Counter(); rows = []
for l in gzip.open(f"{S}/heads.jsonl.gz", "rt", encoding="utf-8"):
    r = json.loads(l); head = r["head"]
    flat = re.sub(r"\s+", " ", head)
    kind = pet = resp = date = caseno = None
    m = OLD.search(flat[:3000])
    if m and len(m["pet"]) < 250 and len(m["resp"]) < 250: kind, pet, resp, date, caseno = "old", m["pet"], m["resp"], m["date"], m["caseno"]
    else:
        m = OLD2.search(flat[:3000])
        if m and len(m["pet"]) < 250 and len(m["resp"]) < 250: kind, pet, resp, date = "old-lite", m["pet"], m["resp"], m["date"]
        else:
            m = VS.search(flat[:3000])
            if m: kind, pet, resp = "versus", m["pet"].strip(), m["resp"].strip()
    kinds[kind or "none"] += 1
    rows.append(dict(id=r["id"], kind=kind, pet=pet, resp=resp, date=date, caseno=caseno, bytes=r["bytes"], pages=r["pages"], sha=r["sha"]))
n = len(rows); print("judgments:", n)
for k, v in kinds.most_common(): print(f"  {k:9} {v:6,}  ({100*v/n:.1f}%)")
json.dump(rows, open(f"{S}/crawl_table.json", "w"))
