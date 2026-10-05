import gzip, json, glob, re, os, collections
os.chdir("/home/user/recourse-sci-pool-data")
T={"Rangappa (2010)":(r"Rangappa",36322),"Bhajan Lal (1990)":(r"Bhajan\s+Lal",None),"Baldev Singh (1999)":(r"Baldev\s+Singh",30317),
   "Jadeja (2010)":(r"Vijaysinh|Jadeja",37060),"Noor Aga (2008)":(r"Noor\s+Aga",31821),"Arnesh Kumar (2014)":(r"Arnesh\s+Kumar",41736),
   "Md. Ibrahim (2009)":(r"(?:Md|Mohd|Mohammed)\.?\s+Ibrahim",35436),"Nanda Gopalan (2015)":(r"Nanda\s+Gopalan",42630),"Lalita Kumari (2013)":(r"Lalita\s+Kumari",40960)}
rx={k:re.compile(v[0]) for k,v in T.items()}
found={k:set() for k in T}
for f in sorted(glob.glob("shards/*.jsonl.gz")):
    for l in gzip.open(f,"rt",encoding="utf-8"):
        r=json.loads(l)
        if r["status"]!="ok": continue
        t=r["text"]
        for k,(p,tid) in T.items():
            if tid is not None and r["id"]<=tid: continue
            if rx[k].search(t): found[k].add(r["id"])
json.dump({k:sorted(v) for k,v in found.items()},open("/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/cite_full.json","w"))
print({k:len(v) for k,v in found.items()})
