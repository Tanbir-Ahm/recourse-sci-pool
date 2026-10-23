"""Fetches the criminal-type Gauhati High Court documents decided 2018 to 2026 from the open bucket (s3://indian-high-court-judgments, CC-BY-4.0, Dattam Labs), reads their text,
flags real judgments and stores monthly shards on the data branch (`shards_post2017/YYYY-MM.jsonl.gz`). Owner approved on 2026-10-23: all 15,423 documents of the worklist, with check-ins.
Usage: python3 -I fetch_post2017.py WORKLIST.csv.gz DATA_WORKTREE SECONDS
Resumable and idempotent (a document already in its shard is skipped); newest month first; 2 requests at a time with a pause; stops at once on a refusal (403, 429) and says so.
A document counts as a judgment signal if: the court lists it as a judgment (court_listed), its heading after the cause title says JUDGMENT, or its body is 5,000+ characters."""
import csv, gzip, hashlib, importlib.util, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests

work, data, seconds = sys.argv[1], sys.argv[2], float(sys.argv[3])
spec = importlib.util.spec_from_file_location("fetch_ghc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fetch_ghc.py"))
fg = importlib.util.module_from_spec(spec); spec.loader.exec_module(fg)
B = "https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com"
UA = "recourse-sci-pool research fetcher (low rate, 2 at a time; contact: owner)"
OUT = os.path.join(data, "shards_post2017")
NEUTRAL = re.compile(r"\b(20\d\d:GAU-[A-Z]{2}:\d+(?:-[A-Z]+)?)")

class Refused(Exception): pass

def get(url):
    last = None
    for i in range(4):
        try:
            r = requests.get(url, timeout=90, headers={"User-Agent": UA})
            if r.status_code == 200: time.sleep(0.05); return r.content, 200
            if r.status_code in (403, 429): last = r.status_code; time.sleep(5 + 5 * i); continue
            if r.status_code == 404: return None, 404
            last = r.status_code
        except requests.RequestException as e: last = type(e).__name__
        time.sleep(2 + 3 * i)
    if last in (403, 429): raise Refused(f"the bucket answered {last} repeatedly")
    return None, last

def body_start(t):
    for pat in (r"\n\s*BEFORE\b", r"HON.?BLE\s+(?:THE\s+)?(?:MR\.?|MRS\.?|MS\.?|CHIEF)"):
        m = re.search(pat, t)
        if m: return m.start()
    return 0

def one(row):
    time.sleep(0.3)
    key = f"data/pdf/year={row['year']}/court=18_6/bench={row['bench']}/{row['fname']}"
    c, st = get(f"{B}/{key}")
    if c is None: return {"bucket_key": key, "error": str(st), "cnr": row["cnr"], "decision_date": row["decision_date"]}
    try: text, rep, pages, images, score = fg.read_pdf(c)
    except Exception as e: return {"bucket_key": key, "error": "unreadable: " + str(e)[:60], "cnr": row["cnr"], "decision_date": row["decision_date"]}
    bs = body_start(text); body = text[bs:]
    heading = bool(re.search(r"JUDGMENT|JUDGEMENT", body[:700].upper()))
    long_ = len(body) >= 5000
    nc = row["neutral_citation"] or (NEUTRAL.search(text[:1500]).group(1) if NEUTRAL.search(text[:1500]) else "")
    title = row["title"]; case_number = title.split(" of ")[0]; parties = title.split(" of ", 1)[1] if " of " in title else title
    return {"cnr": row["cnr"], "case_number": case_number, "parties": parties, "decision_date": row["decision_date"], "date_of_registration": row["date_of_registration"], "judge": row["judge"],
            "bench": row["bench"], "bucket_key": key, "bucket_url": f"{B}/{key}", "bucket_disposal": row["disposal_nature"], "pdf_bytes": len(c), "sha256": hashlib.sha256(c).hexdigest(),
            "pages": pages, "chars": len(text), "body_start": bs, "body_chars": len(body), "pages_with_image": images, "text_repaired": rep, "english_score": score,
            "scan_like": bool(images and len(text) < 300 * max(1, pages)), "court_listed": row["court_listed"] == "yes", "neutral_citation": nc, "court_url": row["court_url"],
            "signal_heading_judgment": heading, "signal_long_body": long_, "reasoned_signal": bool(row["court_listed"] == "yes" or heading or long_),
            "source": "Gauhati High Court, via open bucket indian-high-court-judgments (Dattam Labs, CC-BY-4.0)", "fetched_on": time.strftime("%Y-%m-%d"), "text": text}

def load(path):
    out = {}
    if os.path.exists(path):
        for l in gzip.open(path, "rt", encoding="utf-8"): o = json.loads(l); out[o["bucket_key"]] = o
    return out

def save(path, d):
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        for o in d.values(): f.write(json.dumps(o, ensure_ascii=False) + "\n")
    os.replace(tmp, path)

rows = list(csv.DictReader(gzip.open(work, "rt", encoding="utf-8")))
bymonth = {}
for r in rows: bymonth.setdefault(r["decision_date"][:7], []).append(r)
os.makedirs(OUT, exist_ok=True)
t0 = time.time(); fetched = errs = 0; reason = "completed all months"
try:
    for month in sorted(bymonth, reverse=True):
        path = os.path.join(OUT, month + ".jsonl.gz"); have = load(path)
        todo = [r for r in bymonth[month] if f"data/pdf/year={r['year']}/court=18_6/bench={r['bench']}/{r['fname']}" not in have or "error" in have.get(f"data/pdf/year={r['year']}/court=18_6/bench={r['bench']}/{r['fname']}", {})]
        if not todo: continue
        i = 0
        with ThreadPoolExecutor(2) as ex:
            while i < len(todo):
                if time.time() - t0 > seconds: reason = "time budget used up"; break
                chunk = todo[i:i + 24]; i += 24
                for rec in ex.map(one, chunk):
                    have[rec["bucket_key"]] = rec; fetched += "error" not in rec; errs += "error" in rec
        save(path, have)
        if reason != "completed all months": break
        print(f"month {month} done: {len(have)} of {len(bymonth[month])}", flush=True)
except Refused as e:
    reason = f"STOP: {e}"
    try: save(path, have)
    except NameError: pass
done = sum(1 for m in bymonth for _ in [0] if os.path.exists(os.path.join(OUT, m + ".jsonl.gz")))
tot = ok = 0
for m in bymonth:
    p = os.path.join(OUT, m + ".jsonl.gz")
    if os.path.exists(p):
        d = load(p); ok += sum("error" not in v for v in d.values())
print(f"SESSION END: fetched {fetched} this session, errors {errs}; stored documents with text: {ok} of {len(rows)}; reason: {reason}")
