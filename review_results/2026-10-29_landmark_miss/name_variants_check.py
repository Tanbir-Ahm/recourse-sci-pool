"""How often do real passages of an index name three landmarks that the authority table (authority_graph.py) finds 0 times? Counts of judgments, by a loose pattern (RESULTS.md section 6)."""
import glob, gzip, json, re, collections, sys
IDX = sys.argv[1] if len(sys.argv) > 1 else "../recourse-sci-index/index"      # python3 name_variants_check.py <index folder that holds the *.meta.jsonl.gz files>
pats = {
    "Tukaram / Tuka Ram v. State of Maharashtra": re.compile(r"Tuka\s?ram[^.]{0,60}(?:v\.|vs\.?|versus)\s+(?:The\s+)?State\s+of\s+Maharashtra", re.I),
    "Md./Mohd. Ibrahim v. State of Bihar": re.compile(r"(?:Md|Mohd|Mohammad|Mohammed|Muhammad)\.?\s+Ibrahim[^.]{0,60}(?:v\.|vs\.?|versus)\s+(?:The\s+)?State\s+of\s+Bihar", re.I),
    "Surinder Kumar v. Union Territory/UT Chandigarh": re.compile(r"Surinder\s+Kumar[^.]{0,40}(?:v\.|vs\.?|versus)\s+(?:The\s+)?(?:Union\s+Territory|U\.?\s?T\.?)", re.I),
}
docs = {k: set() for k in pats}
n = 0
for f in sorted(glob.glob(IDX + "/*.meta.jsonl.gz")):
    with gzip.open(f, "rt", encoding="utf-8") as fh:
        for line in fh:
            m = json.loads(line)
            t = m.get("text") or ""
            n += 1
            for k, p in pats.items():
                if p.search(t):
                    docs[k].add(m["doc"])
print("passages read:", n)
for k, v in docs.items():
    print(f"{k}: named in {len(v)} judgments of the index (loose pattern)")
