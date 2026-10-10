"""Shows what the differences between Vaquill's text and ours look like, on a few sampled judgments (screen only; nothing saved)."""
import sys, re, json, difflib, collections, sqlite3
import pandas as pd, pyarrow.parquet as pq
sys.path.insert(0, sys.argv[5])
meta_p, text_p, corpus_p, sample_p = sys.argv[1:5]
res = json.load(open(sample_p))
import c1_helpers as H
meta = pd.read_parquet(meta_p, columns=["case_id", "chunk_index", "language_code", "char_start", "char_end"]); meta = meta[meta.language_code == "en"]
c = sqlite3.connect(f"file:{corpus_p}?mode=ro", uri=True)
pick = []
srt = sorted(res, key=lambda r: r["ours_in_vaquill"])
pick = [srt[len(srt) // 2], srt[len(srt) // 2 + 20], srt[len(srt) // 10], srt[len(srt) // 50]]
for r in pick:
    cid = r["case_id"]
    print("=" * 100); print(cid, "year", r["year"], "ours_in_vaquill", round(r["ours_in_vaquill"], 3), "ratio", round(r["ratio"], 3), "source", r["our_source"])
    tb = pq.read_table(text_p, filters=[("case_id", "=", cid)]).to_pandas()
    off = meta[meta.case_id == cid].set_index(["case_id", "chunk_index"])[["char_start", "char_end"]]
    vt = H.reassemble(tb, cid, off)
    k = re.sub(r"[^0-9A-Za-z]", "", cid).upper()
    did = [x for x in c.execute("select id, insc from docs where insc is not null") if re.sub(r"[^0-9A-Za-z]", "", x[1]).upper() == k][0][0]
    ot = c.execute("select text from texts where id=?", (did,)).fetchone()[0]
    wv, wo = H.words(vt), H.words(ot)
    sm = difflib.SequenceMatcher(None, wo, wv, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != "equal"]
    kinds = collections.Counter(o[0] for o in ops)
    print("opcodes:", dict(kinds), "| words ours", len(wo), "vaquill", len(wv), "| matcher ratio", round(sm.ratio(), 3))
    sizes = collections.Counter()
    for tag, i1, i2, j1, j2 in ops:
        a, b = i2 - i1, j2 - j1
        sizes["small(<=3 words)" if max(a, b) <= 3 else ("medium(4-30)" if max(a, b) <= 30 else "large(>30)")] += 1
    print("size of differences:", dict(sizes))
    shown = 0
    for tag, i1, i2, j1, j2 in ops:
        if max(i2 - i1, j2 - j1) > 40 and shown < 3:
            print(f"  LARGE {tag}: ours[{i1}:{i2}] ({i2-i1} words) = {' '.join(wo[i1:i1+25])!r}...  |  vaquill[{j1}:{j2}] ({j2-j1} words) = {' '.join(wv[j1:j1+25])!r}...")
            shown += 1
    shown = 0
    for tag, i1, i2, j1, j2 in ops:
        if max(i2 - i1, j2 - j1) <= 6 and shown < 14:
            print(f"  {tag:8s} ours={' '.join(wo[max(0,i1-3):i1])} [{' '.join(wo[i1:i2])}]   vaquill=[{' '.join(wv[j1:j2])}]")
            shown += 1
