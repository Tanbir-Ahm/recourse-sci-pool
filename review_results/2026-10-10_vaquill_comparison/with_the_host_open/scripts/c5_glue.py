"""How often are words glued together (missing spaces) in Vaquill's text versus ours? A token counts as 'glued' if it is outside the vocabulary but splits into two in-vocabulary words (each >= 3 letters)."""
import sys, re, json, random, sqlite3, collections, statistics
import pandas as pd, pyarrow.parquet as pq
sys.path.insert(0, sys.argv[6])
import c1_helpers as H
meta_p, text_p, corpus_p, sample_p, out_p = sys.argv[1:6]
c = sqlite3.connect(f"file:{corpus_p}?mode=ro", uri=True)
rnd = random.Random(11)
ids = [r[0] for r in c.execute("select id from docs where source='bucket' and year>=2019")]; rnd.shuffle(ids)
cnt = collections.Counter()
for did in ids[:1500]:
    t = c.execute("select text from texts where id=?", (did,)).fetchone()[0]
    cnt.update(w for w in re.findall(r"[a-z]+", t.lower()) if len(w) > 1)
vocab = {w for w, n in cnt.items() if n >= 8}
common = {w for w, n in cnt.items() if n >= 30 and len(w) >= 3}      # parts must be fairly common words
def glued(w):
    if w in vocab or len(w) < 7: return False
    return any(w[:i] in common and w[i:] in common for i in range(3, len(w) - 2))
tok = lambda t: [w for w in re.findall(r"[a-z]+", t.lower()) if len(w) > 1]
res = json.load(open(sample_p))
meta = pd.read_parquet(meta_p, columns=["case_id", "chunk_index", "language_code", "char_start", "char_end"]); meta = meta[meta.language_code == "en"]
want = {r["case_id"] for r in res}
tb = pq.read_table(text_p, filters=[("case_id", "in", list(want))]).to_pandas()
off = meta[meta.case_id.isin(want)].set_index(["case_id", "chunk_index"])[["char_start", "char_end"]]
ours = {}
for did, insc, src, date in c.execute("select id, insc, source, date from docs where insc is not null and insc<>''"):
    ours.setdefault(re.sub(r"[^0-9A-Za-z]", "", insc).upper(), []).append((did, src, date))
clean = lambda t: H.TAGLINE.sub("", H.RUN.sub("", H.LONE.sub("", t)))
out = []
for r in res:
    cid = r["case_id"]; k = re.sub(r"[^0-9A-Za-z]", "", cid).upper()
    did = [x for x in ours[k] if x[1] == r["our_source"]][0][0]
    ot = c.execute("select text from texts where id=?", (did,)).fetchone()[0]
    vt = H.reassemble(tb, cid, off)
    tv, to = tok(clean(vt)), tok(clean(ot))
    gv, go = sum(glued(w) for w in tv), sum(glued(w) for w in to)
    out.append({"case_id": cid, "year": r["year"], "source": r["our_source"], "glue_vaquill": gv / max(1, len(tv)), "glue_ours": go / max(1, len(to)), "tokens_v": len(tv)})
json.dump(out, open(out_p, "w"))
med = lambda xs: round(statistics.median(xs), 4)
print("glued-word rate (share of tokens), median over judgments; judgments with rate >1%")
for label, sel in (("all", out), ("our source crawl (older judis PDFs)", [o for o in out if o["source"] == "crawl"]), ("our source bucket (same e-SCR PDFs as Vaquill)", [o for o in out if o["source"] == "bucket"]), ("decision year 2018+", [o for o in out if o["year"] >= 2018]), ("decision year before 2018", [o for o in out if o["year"] < 2018])):
    if not sel: continue
    print(f"  {label:48s} n={len(sel):3d}  Vaquill median {med([o['glue_vaquill'] for o in sel]):.4f} (>1%: {sum(o['glue_vaquill']>0.01 for o in sel)})   ours median {med([o['glue_ours'] for o in sel]):.4f} (>1%: {sum(o['glue_ours']>0.01 for o in sel)})")
by = collections.defaultdict(list)
for o in out: by[o["year"] // 10 * 10].append(o)
print("  by decade, Vaquill median glue:", {d: med([o["glue_vaquill"] for o in v]) for d, v in sorted(by.items())})
print("  by decade, share of judgments where Vaquill glue >1%:", {d: round(sum(o["glue_vaquill"] > 0.01 for o in v) / len(v), 2) for d, v in sorted(by.items())})
