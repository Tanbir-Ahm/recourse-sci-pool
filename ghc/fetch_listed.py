"""Fetches from the open bucket every document that the Gauhati High Court's own monthly lists (2010 to 2017) name as a judgment, and marks all stored documents
with their list information. Regardless of size and of case type (the court itself lists some interlocutory and bail matters as judgments).
Usage: python3 -I fetch_listed.py DATA_WORKTREE ROWS.csv   (ROWS.csv = court_list_rows.csv from parse_court_lists.py)"""
import csv, gzip, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_ghc import read_pdf, flags, get, load_shard, excluded_type

def main(data, rows_csv):
    cat = {r["bucket_key"]: r for r in csv.DictReader(gzip.open(os.path.join(data, "catalogue", "ghc_to2017_catalogue.csv.gz"), "rt"))}
    info = {}
    for r in csv.DictReader(open(rows_csv)):
        if r["in_bucket"] == "yes" and r["bucket_key"] not in info:
            info[r["bucket_key"]] = {"court_listed": True, "list_date": r["date"], "list_case_number": r["case_number"], "list_subject": r["subject"], "list_judges": r["judges"], "court_judgment_url": r["judgment_url"], "list_file": r["list_file"]}
    shards = os.path.join(data, "shards"); have = set()
    for f in os.listdir(shards): have |= set(load_shard(os.path.join(shards, f)))
    todo = [cat[k] for k in info if k in cat and k not in have]
    print(f"{len(info)} listed judgments in the bucket; {len(todo)} not stored yet", flush=True)
    new = {}
    def flush_new():
        for month, rows in new.items():
            path = os.path.join(shards, f"{month}.jsonl.gz"); cur = load_shard(path)
            for o in rows: cur[o["bucket_key"]] = o
            with gzip.open(path + ".tmp", "wt", encoding="utf-8", compresslevel=9) as fh:
                for o in sorted(cur.values(), key=lambda o: (o["decision_date"], o["cnr"])): fh.write(json.dumps(o, ensure_ascii=False) + "\n")
            os.replace(path + ".tmp", path)
        new.clear()
    done = 0
    with ThreadPoolExecutor(3) as ex:
        for r, content in zip(todo, ex.map(lambda r: get(r["bucket_url"]), todo)):
            if content is None or content[:5] != b"%PDF-": print("FAILED", r["bucket_key"], flush=True); continue
            text, repaired, pages, images, sc = read_pdf(content)
            hj, ho, reasoned, long_order, dispo, reasoning = flags(text)
            o = {**{k: r[k] for k in ("cnr", "case_number", "parties", "decision_date", "date_of_registration", "judge", "bench", "bucket_key", "bucket_url")},
                 "pdf_bytes": int(float(r["pdf_bytes"])), "pages": pages, "chars": len(text), "pages_with_image": images, "text_repaired": repaired, "english_score": sc,
                 "head_judgment": hj, "head_order": ho, "disposition_marker": dispo, "reasoning_markers": reasoning, "reasoned_judgment": reasoned, "long_order_candidate": long_order,
                 "source": "Gauhati High Court, via open bucket indian-high-court-judgments (Dattam Labs, CC-BY-4.0)", "fetched_on": time.strftime("%Y-%m-%d"), "text": text}
            new.setdefault(r["decision_date"][:7], []).append(o); done += 1
            if done % 1000 == 0: flush_new(); print(done, "fetched", flush=True)
    flush_new()
    # mark every stored document with its list information
    marked = 0
    for f in sorted(os.listdir(shards)):
        path = os.path.join(shards, f); cur = load_shard(path)
        for k, o in cur.items():
            ym = o["decision_date"][:7]
            o["court_listed"] = bool(k in info) if "2010-01" <= ym <= "2017-12" and ym != "2010-12" else None
            o["excluded_type"] = excluded_type(o["case_number"])
            if k in info: o.update(info[k]); marked += 1
        with gzip.open(path + ".tmp", "wt", encoding="utf-8", compresslevel=9) as fh:
            for o in sorted(cur.values(), key=lambda o: (o["decision_date"], o["cnr"])): fh.write(json.dumps(o, ensure_ascii=False) + "\n")
        os.replace(path + ".tmp", path)
    subprocess.run(["git", "-C", data, "add", "-A"], check=True)
    subprocess.run(["git", "-C", data, "commit", "-q", "-m", f"Gauhati High Court: the court's own lists marked ({marked} judgments), {done} more fetched\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01BKA5VmevDP2GsevzgKkDnc"])
    subprocess.run(["git", "-C", data, "push", "-q", "origin", "claude/ghc-bucket"])
    print("DONE fetched", done, "marked", marked, flush=True)

if __name__ == "__main__":
    main(*sys.argv[1:])
