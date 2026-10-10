"""Which tokens make Vaquill's text noisier than ours? Screen output only."""
import sys, re, json, random, sqlite3, collections
import pandas as pd, pyarrow.parquet as pq
sys.path.insert(0, sys.argv[5])
import c1_helpers as H
meta_p, text_p, corpus_p, oov_p = sys.argv[1:5]
oov = json.load(open(oov_p))
c = sqlite3.connect(f"file:{corpus_p}?mode=ro", uri=True)
rnd = random.Random(11)
ids = [r[0] for r in c.execute("select id from docs where source='bucket' and year>=2019")]; rnd.shuffle(ids)
cnt = collections.Counter()
for did in ids[:1500]:
    t = c.execute("select text from texts where id=?", (did,)).fetchone()[0]
    cnt.update(w for w in re.findall(r"[a-z]+", t.lower()) if len(w) > 1)
vocab = {w for w, n in cnt.items() if n >= 8}
meta = pd.read_parquet(meta_p, columns=["case_id", "chunk_index", "language_code", "char_start", "char_end"]); meta = meta[meta.language_code == "en"]
ours = {}
for did, insc, src, date in c.execute("select id, insc, source, date from docs where insc is not null and insc<>''"):
    ours.setdefault(re.sub(r"[^0-9A-Za-z]", "", insc).upper(), []).append((did, src, date))
def show(group, label, n=3):
    sel = sorted(group, key=lambda o: -(o["oov_vaquill"] - o["oov_ours"]))[:n]
    tb = pq.read_table(text_p, filters=[("case_id", "in", [o["case_id"] for o in sel])]).to_pandas()
    off = meta[meta.case_id.isin([o["case_id"] for o in sel])].set_index(["case_id", "chunk_index"])[["char_start", "char_end"]]
    for o in sel:
        vt = H.reassemble(tb, o["case_id"], off)
        clean = lambda t: H.TAGLINE.sub("", H.RUN.sub("", H.LONE.sub("", t)))
        toks = [w for w in re.findall(r"[a-z]+", clean(vt).lower()) if len(w) > 1]
        bad = collections.Counter(w for w in toks if w not in vocab)
        print(f"\n[{label}] {o['case_id']} year {o['year']} source {o['source']} OOV vaquill {o['oov_vaquill']:.3f} ours {o['oov_ours']:.3f}")
        print("  most frequent out-of-vocabulary tokens in Vaquill's text:", bad.most_common(22))
        # show a raw excerpt around some noisy spot
        m = re.search(r".{80}(?:~|\bwh\b|\bth\b).{80}", clean(vt), flags=re.S)
        if m: print("  raw excerpt:", repr(m.group(0)))
show([o for o in oov if o["year"] >= 2020], "2020s", 3)
show([o for o in oov if 1990 <= o["year"] < 2000 and o["source"] == "crawl"], "1990s crawl", 2)
