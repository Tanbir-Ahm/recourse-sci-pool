"""Reads the court's own judgment PDFs that the owner downloaded (zips in ghc/court_judgments/), stores their text on the data branch as
monthly shards tagged text_source "court", and marks court_file_received=yes in court_lists/by_month. AB, BA, bail, MC and IA types are skipped
(owner, 2026-10-21 and 2026-10-22). A file the court lists under several case numbers is stored once, with every case number kept.
Usage: python3 -I store_court_files.py ZIPDIR WORKDIR MISSING_CSV DATA_WORKTREE
WORKDIR must be a new empty folder (the zips are unpacked there; their contents are untrusted: only the PDF bytes are read)."""
import csv, gzip, importlib.util, json, os, re, sys, urllib.parse, zipfile, collections, datetime

zipdir, work, missing_csv, data = sys.argv[1:5]
spec = importlib.util.spec_from_file_location("fetch_ghc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fetch_ghc.py"))
fg = importlib.util.module_from_spec(spec); spec.loader.exec_module(fg)

def leaf(u): return re.sub(r"\s+", "", urllib.parse.unquote(u.rsplit("/", 1)[1])).lower()

rows = collections.defaultdict(list)
for r in csv.DictReader(open(missing_csv, encoding="utf-8")): rows[leaf(r["judgment_url"])].append(r)

os.makedirs(work, exist_ok=True)
pdfs = {}
for z in sorted(f for f in os.listdir(zipdir) if f.lower().endswith(".zip")):
    with zipfile.ZipFile(os.path.join(zipdir, z)) as zf:
        for i in zf.infolist():
            if i.is_dir() or not i.filename.lower().endswith(".pdf"): continue
            pdfs[re.sub(r"\s+", "", urllib.parse.unquote(os.path.basename(i.filename))).lower()] = zf.read(i)
print("PDF files in the zips:", len(pdfs))

report = {"stored": 0, "skipped_excluded": [], "not_in_list": [], "unreadable": [], "scan_like": [], "tiny": [], "already": 0}
shards = {}
today = datetime.date.today().isoformat()
for name, content in sorted(pdfs.items()):
    lr = rows.get(name) or rows.get(name[:-4]) or []
    if not lr: report["not_in_list"].append(name); continue
    first = lr[0]
    types = [r["case_number"].split("/")[0].strip().upper() for r in lr]
    if any(fg.excluded_type(r["case_number"]) for r in lr) or re.match(r"(?i)^(ab|ba|bail|mc|crlmc|ia|iacrl)\d", re.sub(r"[^A-Za-z0-9]", "", name)) and not re.match(r"(?i)^(crl|cr)", name):
        report["skipped_excluded"].append(name); continue
    try:
        text, repaired, pages, images, score = fg.read_pdf(content)
    except Exception as e:
        report["unreadable"].append((name, str(e)[:80])); continue
    n = len(text)
    if images and n < 300 * max(1, pages): report["scan_like"].append((name, pages, n))
    elif n < 600: report["tiny"].append((name, pages, n))
    hj, ho, reasoned, longord, dispo, reasoning = fg.flags(text)
    month = first["date"][:7]
    key = "court:" + name
    rec = {"cnr": "", "case_number": " ; ".join(dict.fromkeys(r["case_number"] for r in lr)), "parties": first["petitioner"] + " Vs " + first["respondent"],
           "decision_date": first["date"], "date_of_registration": "", "judge": first["judges"], "bench": "", "bucket_key": key, "bucket_url": "",
           "court_url": first["judgment_url"].replace("http://", "https://"), "pdf_bytes": len(content), "pages": pages, "chars": n, "pages_with_image": images,
           "text_repaired": repaired, "english_score": score, "head_judgment": hj, "head_order": ho, "disposition_marker": dispo, "reasoning_markers": reasoning,
           "reasoned_judgment": reasoned, "long_order_candidate": longord, "source": "Gauhati High Court, the court's own file (ghconline.gov.in), downloaded by the owner on 2026-10-22",
           "text_source": "court", "list_subject": first["subject"], "list_file": first["list_file"], "fetched_on": today, "text": text,
           "court_listed": True, "excluded_type": False}
    path = os.path.join(data, "shards", month + ".jsonl.gz")
    sh = shards.setdefault(path, fg.load_shard(path))
    if key in sh: report["already"] += 1
    sh[key] = rec; report["stored"] += 1
for path, sh in shards.items():
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for o in sh.values(): f.write(json.dumps(o, ensure_ascii=False) + "\n")

# mark court_file_received in the by-month tables
got = {n for n in pdfs if n not in {x for x in report["skipped_excluded"]} and n in rows or n[:-4] in rows}
marked = 0
for p in sorted(os.popen("ls %s/court_lists/by_month/*/*.csv" % data).read().split()):
    t = list(csv.DictReader(open(p, encoding="utf-8"))); fn = list(t[0].keys()) if t else None
    ch = False
    for r in t:
        if r.get("court_url") and leaf(r["court_url"]) in {g for g in got} and r["court_file_received"] != "yes": r["court_file_received"] = "yes"; ch = True; marked += 1
    if ch:
        w = csv.DictWriter(open(p, "w", newline="", encoding="utf-8"), fieldnames=fn); w.writeheader(); w.writerows(t)
print("rows marked court_file_received=yes:", marked)
for k, v in report.items(): print(k, v if isinstance(v, int) else len(v))
json.dump(report, open(os.path.join(work, "court_files_report.json"), "w"), indent=1)
