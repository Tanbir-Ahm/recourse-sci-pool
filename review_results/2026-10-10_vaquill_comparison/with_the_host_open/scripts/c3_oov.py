"""Reference-free OCR-noise check: share of word tokens that are not in a vocabulary built from clean, typeset 2019+ judgments of our own bucket text.
Compares Vaquill's reassembled English text with our text of the same judgments, by source of our text and decade. Counts only."""
import sys, re, json, random, sqlite3, collections, statistics
import pandas as pd, pyarrow.parquet as pq
sys.path.insert(0, sys.argv[6])
import c1_helpers as H
meta_p, text_p, corpus_p, sample_p, out_p = sys.argv[1:6]
c = sqlite3.connect(f"file:{corpus_p}?mode=ro", uri=True)
# vocabulary from clean modern bucket texts (not part of the sample)
res = json.load(open(sample_p)); in_sample = {r["case_id"] for r in res}
rnd = random.Random(11)
ids = [r[0] for r in c.execute("select id from docs where source='bucket' and year>=2019")]
rnd.shuffle(ids)
cnt = collections.Counter()
for did in ids[:1500]:
    t = c.execute("select text from texts where id=?", (did,)).fetchone()[0]
    cnt.update(w for w in re.findall(r"[a-z]+", t.lower()) if len(w) > 1)
vocab = {w for w, n in cnt.items() if n >= 8}
print("vocabulary size", len(vocab), "from", min(1500, len(ids)), "typeset 2019+ judgments")
tok = lambda t: [w for w in re.findall(r"[a-z]+", t.lower()) if len(w) > 1]
oov = lambda ws: sum(w not in vocab for w in ws) / max(1, len(ws))
meta = pd.read_parquet(meta_p, columns=["case_id", "chunk_index", "language_code", "char_start", "char_end"]); meta = meta[meta.language_code == "en"]
tb = pq.read_table(text_p, filters=[("case_id", "in", list(in_sample))]).to_pandas()
off = meta[meta.case_id.isin(in_sample)].set_index(["case_id", "chunk_index"])[["char_start", "char_end"]]
rows = []
for r in res:
    cid = r["case_id"]
    k = re.sub(r"[^0-9A-Za-z]", "", cid).upper()
    did = [x[0] for x in c.execute("select id, insc from docs where insc is not null and source=?", (r["our_source"],)) if re.sub(r"[^0-9A-Za-z]", "", x[1]).upper() == k][0] if False else None
    rows.append(r)
# map case -> our doc id once
ours = {}
for did, insc, src, date in c.execute("select id, insc, source, date from docs where insc is not null and insc<>''"):
    ours.setdefault(re.sub(r"[^0-9A-Za-z]", "", insc).upper(), []).append((did, src, date))
out = []
for r in res:
    cid = r["case_id"]; k = re.sub(r"[^0-9A-Za-z]", "", cid).upper()
    did = [x for x in ours[k] if x[1] == r["our_source"]][0][0]
    ot = c.execute("select text from texts where id=?", (did,)).fetchone()[0]
    vt = H.reassemble(tb, cid, off)
    # strip clutter the way the comparison did (margin letters, running headers, tags) so that only word errors are counted
    clean = lambda t: H.TAGLINE.sub("", H.RUN.sub("", H.LONE.sub("", t)))
    out.append({"case_id": cid, "year": r["year"], "source": r["our_source"], "oov_vaquill": oov(tok(clean(vt))), "oov_ours": oov(tok(clean(ot)))})
json.dump(out, open(out_p, "w"))
def med(xs): return round(statistics.median(xs), 4)
print("OOV rate (share of tokens outside the clean-text vocabulary), median over judgments:")
print("  all:       Vaquill", med([o["oov_vaquill"] for o in out]), "| ours", med([o["oov_ours"] for o in out]), "| n", len(out))
for src in ("crawl", "bucket"):
    s = [o for o in out if o["source"] == src]
    print(f"  our source {src:6s}: Vaquill {med([o['oov_vaquill'] for o in s])} | ours {med([o['oov_ours'] for o in s])} | n {len(s)} | Vaquill worse in {sum(o['oov_vaquill'] > o['oov_ours'] for o in s)} of {len(s)}")
by = collections.defaultdict(list)
for o in out: by[o["year"] // 10 * 10].append(o)
print("  by decade (Vaquill / ours):", {d: (med([o["oov_vaquill"] for o in v]), med([o["oov_ours"] for o in v])) for d, v in sorted(by.items())})
