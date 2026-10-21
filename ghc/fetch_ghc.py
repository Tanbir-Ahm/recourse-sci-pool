"""Fetches Gauhati High Court documents of a minimum size from the open bucket (s3://indian-high-court-judgments, CC-BY-4.0, Dattam Labs),
reads their text, repairs the shifted-letter encoding of the Arunachal Pradesh bench files, flags judgments, and stores monthly shards on the data branch.
Usage: python3 -I fetch_ghc.py DATA_WORKTREE MIN_BYTES [LIMIT]
Resumable: documents already in a shard are skipped. Two to three requests at a time, small pauses (the publisher asks for low concurrency)."""
import csv, gzip, io, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import pymupdf, requests

def stop_score(s):
    low = s.lower(); n = max(1, len(s))
    return (low.count(" the ") + low.count(" of ") + low.count(" and ")) / n * 1000

def shift(s):  # the bench's PDFs store every character 29 code points lower; undo it
    return "".join(chr(ord(c) + 29) if 3 <= ord(c) <= 0x5d else c for c in s)

def read_pdf(content):
    doc = pymupdf.open(stream=content, filetype="pdf")
    raw, rep, images = [], [], 0
    for p in doc:
        lines = []
        for b in p.get_text("dict")["blocks"]:
            for l in b.get("lines", []): lines.append("".join(s["text"] for s in l["spans"]))
        raw.append("\n".join(lines)); rep.append("\n".join(shift(l) for l in lines)); images += len(p.get_images()) > 0
    t_raw, t_rep = "\n\f\n".join(raw), "\n\f\n".join(rep)
    s_raw, s_rep = stop_score(t_raw), stop_score(t_rep)
    repaired = s_rep >= 5 and s_rep > 3 * s_raw
    return (t_rep if repaired else t_raw), repaired, len(doc), images, round(max(s_raw, s_rep), 1)

def flags(text):
    compact = re.sub(r"[^A-Z]", "", text[:2500].upper())
    hj = "JUDGMENT" in compact or "JUDGEMENT" in compact
    ho = "ORDER" in compact
    n = len(text)
    dispo = bool(re.search(r"(?i)\b(is|are|stands?) (hereby )?(partly |accordingly )?(allowed|dismissed|disposed|rejected|set aside|quashed|affirmed)\b|\bin the result\b|\bno order as to costs\b", text[-2500:]))
    reasoning = len(re.findall(r"(?i)\b(held|therefore|hence|contended|submitted|in view of|having regard to|observed|considered)\b", text))
    reasoned = bool(n >= 3000 and (hj or (dispo and reasoning >= 5)))
    return hj, ho, reasoned, bool(not reasoned and ho and n >= 10000), dispo, reasoning

def get(url):
    for i in range(3):
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200: time.sleep(0.05); return r.content
        except requests.RequestException: pass
        time.sleep(2 + 3 * i)
    return None

def load_shard(path):
    out = {}
    if os.path.exists(path):
        for line in gzip.open(path, "rt", encoding="utf-8"):
            o = json.loads(line); out[o["bucket_key"]] = o
    return out

def main(data, min_bytes, limit=None):
    cat = list(csv.DictReader(gzip.open(os.path.join(data, "catalogue", "ghc_to2017_catalogue.csv.gz"), "rt")))
    skip_types = {"AB"}  # anticipatory bail matters: the owner does not want them (2026-10-21)
    todo = [r for r in cat if r["pdf_bytes"] and float(r["pdf_bytes"]) >= float(min_bytes) and r["case_number"].split("/")[0].strip().upper() not in skip_types]
    os.makedirs(os.path.join(data, "shards"), exist_ok=True)
    have = set()
    for f in os.listdir(os.path.join(data, "shards")):
        have |= set(load_shard(os.path.join(data, "shards", f)))
    todo = [r for r in todo if r["bucket_key"] not in have]
    if limit: todo = todo[:int(limit)]
    print(f"{len(todo)} documents to fetch (already stored: {len(have)})", flush=True)
    pending, done = {}, 0
    def flush():
        for month, rows in pending.items():
            path = os.path.join(data, "shards", f"{month}.jsonl.gz")
            cur = load_shard(path)
            for o in rows: cur[o["bucket_key"]] = o
            with gzip.open(path + ".tmp", "wt", encoding="utf-8", compresslevel=9) as fh:
                for o in sorted(cur.values(), key=lambda o: (o["decision_date"], o["cnr"])): fh.write(json.dumps(o, ensure_ascii=False) + "\n")
            os.replace(path + ".tmp", path)
        pending.clear()
        subprocess.run(["git", "-C", data, "add", "-A"], check=True)
        if subprocess.run(["git", "-C", data, "diff", "--cached", "--quiet"]).returncode:
            subprocess.run(["git", "-C", data, "commit", "-q", "-m", f"Gauhati High Court text: {done} documents so far\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01BKA5VmevDP2GsevzgKkDnc"], check=True)
            subprocess.run(["git", "-C", data, "push", "-q", "origin", "claude/ghc-bucket"])
    with ThreadPoolExecutor(3) as ex:
        for r, content in zip(todo, ex.map(lambda r: get(r["bucket_url"]), todo)):
            if content is None or not content[:5] == b"%PDF-":
                print("FAILED", r["bucket_key"], flush=True); continue
            text, repaired, pages, images, sc = read_pdf(content)
            hj, ho, reasoned, long_order, dispo, reasoning = flags(text)
            o = {**{k: r[k] for k in ("cnr", "case_number", "parties", "decision_date", "date_of_registration", "judge", "bench", "bucket_key", "bucket_url")},
                 "pdf_bytes": int(float(r["pdf_bytes"])), "pages": pages, "chars": len(text), "pages_with_image": images, "text_repaired": repaired, "english_score": sc,
                 "head_judgment": hj, "head_order": ho, "disposition_marker": dispo, "reasoning_markers": reasoning, "reasoned_judgment": reasoned, "long_order_candidate": long_order,
                 "source": "Gauhati High Court, via open bucket indian-high-court-judgments (Dattam Labs, CC-BY-4.0)", "fetched_on": time.strftime("%Y-%m-%d"), "text": text}
            pending.setdefault(r["decision_date"][:7], []).append(o); done += 1
            if done % 500 == 0: flush(); print(done, "stored", flush=True)
    flush(); print("DONE", done, flush=True)

if __name__ == "__main__":
    main(*sys.argv[1:])
