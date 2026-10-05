import gzip, json, glob, os
os.chdir("/home/user/recourse-sci-pool-data")
S = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad"
n = 0
with gzip.open(f"{S}/heads.jsonl.gz", "wt", encoding="utf-8") as out:
    for f in sorted(glob.glob("shards/*.jsonl.gz")):
        for l in gzip.open(f, "rt", encoding="utf-8"):
            r = json.loads(l)
            if r.get("status") != "ok": continue
            n += 1
            out.write(json.dumps(dict(id=r["id"], bytes=r.get("bytes"), pages=r.get("pages"), sha=r.get("sha256"), head=r["text"][:3500])) + "\n")
print("done", n)
