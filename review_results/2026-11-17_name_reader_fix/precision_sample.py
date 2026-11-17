"""PRECISION of the links the fixed reader ADDED. Edges (citing judgment -> cited case) present in the NEW table and absent from the OLD one are the new links. A fixed-seed random sample (random.Random(20261117)) of them is printed
with the sentence of the citing judgment that produced the link, for a person to read: is the citing sentence really naming the case it was linked to? Free (no model call).
    python3 precision_sample.py --old OLD --new NEW --n 60 --out FILE.json"""
import argparse, gzip, json, os, random, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); os.chdir(ROOT)
ap = argparse.ArgumentParser(); ap.add_argument("--old", required=True); ap.add_argument("--new", required=True); ap.add_argument("--n", type=int, default=60); ap.add_argument("--out", required=True)
ap.add_argument("--edges", default="added", help="added = edges in NEW not in OLD; old = edges of the OLD table that the NEW table also has (the unchanged base)"); ap.add_argument("--seed", type=int, default=20261117); ap.add_argument("--names", default="names_table/names_table_d8811a9.json.gz"); ap.add_argument("--index-dir", default="/home/user/audit_idx/new"); a = ap.parse_args()
import authority_graph as G, sci_index as si
old = json.load(gzip.open(a.old, "rt")); new = json.load(gzip.open(a.new, "rt"))
oe = {(c, x) for c, L in old["cites"].items() for x in L}; ne = {(c, x) for c, L in new["cites"].items() for x in L}
added = sorted(ne - oe); lost = sorted(oe - ne)
print("edges old", len(oe), "new", len(ne), "added", len(added), "lost", len(lost))
names = {r["doc"]: r for r in json.load(gzip.open(a.names, "rt", encoding="utf-8"))["rows"] if r.get("name")}
pool = added if a.edges == "added" else sorted(oe & ne)
rng = random.Random(a.seed); sample = rng.sample(pool, min(a.n, len(pool)))
want = {int(c) for c, _ in sample}
metas = []
sides = ["review_data/side_index_d8811a9/" + d for d in sorted(os.listdir("review_data/side_index_d8811a9"))]
for d in [a.index_dir] + sides:
    mm, _M, _ = si._load_index(d)
    metas += [m for m in mm if m["doc"] in want]
by_doc = {}
for m in metas:
    by_doc.setdefault(m["doc"], []).append(m["text"])
res = G.Resolver(names); cid = G.clusters(names)
out = []
for c, x in sample:
    c, x = int(c), int(x)
    snippet = None
    for t in by_doc.get(c, []):
        for m in G._VS.finditer(t):
            left, right = G._left(t, m.start()), G._right(t, m.end())
            t1, t2 = G.party_tokens(" ".join(left)), G.party_tokens(" ".join(right))
            if t1 and t2:
                hit = res.resolve(t1, "".join(t2[:3]), None, None)
                if any(cid[d] == x for d in hit):
                    snippet = t[max(0, m.start() - 90):m.end() + 110].replace("\n", " ")
                    break
        if snippet:
            break
    out.append({"citing": c, "citing_name": (names.get(c) or {}).get("name"), "cited": x, "cited_name": (names.get(x) or {}).get("name"), "snippet": snippet})
json.dump({"added": len(added), "lost": len(lost), "sample": out}, open(a.out, "w"), indent=1)
for i, o in enumerate(out, 1):
    print(f"[{i}] {o['citing_name'] or o['citing']}  ->  {o['cited_name']}\n     {(o['snippet'] or 'None')[:230]}")
