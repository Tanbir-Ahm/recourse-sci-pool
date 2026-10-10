"""Reassembles Vaquill's English judgments from their chunks (header removed, overlaps removed by char offsets) and compares them with our own text of the same judgment.
Counts and shares only are written out; no judgment text is saved. Args: meta.parquet en_text.parquet corpus.sqlite out.json sample_size"""
import sys, re, json, random, sqlite3, collections, statistics
import pandas as pd
import pyarrow.parquet as pq
meta_p, text_p, corpus_p, out_p, N = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
meta = pd.read_parquet(meta_p, columns=["case_id", "chunk_index", "language_code", "char_start", "char_end", "decision_date", "year"])
meta = meta[meta.language_code == "en"]
first = meta[meta.chunk_index == 0].set_index("case_id")
c = sqlite3.connect(f"file:{corpus_p}?mode=ro", uri=True)
ours = collections.defaultdict(list)
for did, insc, src, date in c.execute("select id, insc, source, date from docs where insc is not null and insc<>''"):
    ours[re.sub(r"[^0-9A-Za-z]", "", insc).upper()].append((did, src, date))
matched = []
for cid, r in first.iterrows():
    k = re.sub(r"[^0-9A-Za-z]", "", cid).upper()
    cands = [x for x in ours.get(k, []) if (x[2] or "")[:10] == r.decision_date[:10]]
    if cands:
        matched.append((cid, cands[0][0], cands[0][1], int(r.decision_date[:4])))
rnd = random.Random(20261010)
by_dec = collections.defaultdict(list)
for m in matched: by_dec[m[3] // 10 * 10].append(m)
sample = []
per = max(1, N // len(by_dec))
for dec, lst in sorted(by_dec.items()):
    sample += rnd.sample(lst, min(per, len(lst)))
want = {s[0] for s in sample}
print("matched", len(matched), "| sample", len(sample), "| decades", {k: len(v) for k, v in sorted(by_dec.items())})
# chunks of the sampled cases
tb = pq.read_table(text_p, filters=[("case_id", "in", list(want))]).to_pandas()
off = meta[meta.case_id.isin(want)].set_index(["case_id", "chunk_index"])[["char_start", "char_end"]]
HDR = re.compile(r"\ACase: [^\n]*\nSection: [^\n]*\n\n")
LONE = re.compile(r"(?m)^[A-H]\s*$")
RUN = re.compile(r"(?mi)^(?:\d{1,4}\s+)?(?:SUPREME COURT REPORTS.*|\[\d{4}\]\s+(?:SUPP\.\s+)?\d+\s+S\.C\.R\.(?:\s+\d+)?)\s*$")
TAGLINE = re.compile(r"(?m)^\[[A-Z_]+\]\s*#*\s*")
def reassemble(df, cid):
    d = df[df.case_id == cid].sort_values("chunk_index")
    parts, prev_end, checks = [], None, collections.Counter()
    for ci, t in zip(d.chunk_index, d.text_original):
        h = HDR.match(t)
        body = t[h.end():] if h else t
        cs, ce = off.loc[(cid, ci)]
        checks["header_found"] += bool(h)
        checks["len_matches_offsets"] += (len(body) == ce - cs)
        if prev_end is not None and cs < prev_end:
            skip = prev_end - cs
            checks["overlap_chunks"] += 1
            body = body[skip:]
        elif prev_end is not None:
            parts.append("\n\n")
        parts.append(body)
        prev_end = ce
    return "".join(parts), checks
def words(t, strip_clutter=True):
    if strip_clutter:
        t = TAGLINE.sub("", RUN.sub("", LONE.sub("", t)))
    return re.findall(r"[a-z0-9]+", t.lower())
def grams(w, n=5):
    return [" ".join(w[i:i + n]) for i in range(0, max(0, len(w) - n + 1))]
res = []
tot_checks = collections.Counter()
for cid, did, src, yr in sample:
    vt, chk = reassemble(tb, cid)
    tot_checks.update(chk)
    ot = c.execute("select text from texts where id=?", (did,)).fetchone()[0]
    wv, wo = words(vt), words(ot)
    gv, go = grams(wv), grams(wo)
    sv, so = set(gv), set(go)
    if not go or not gv:
        continue
    found_o = [g in sv for g in go]                      # our 5-grams present in Vaquill
    found_v = [g in so for g in gv]
    def longest_false(flags):
        best = cur = 0
        for f in flags:
            cur = 0 if f else cur + 1
            best = max(best, cur)
        return best
    first_hit = next((i for i, f in enumerate(found_o) if f), len(found_o))
    last_hit = next((i for i, f in enumerate(reversed(found_o)) if f), len(found_o))
    res.append({"case_id": cid, "year": yr, "our_source": src, "words_vaquill": len(wv), "words_ours": len(wo), "ratio": len(wv) / max(1, len(wo)),
                "ours_in_vaquill": sum(found_o) / len(found_o), "vaquill_in_ours": sum(found_v) / len(found_v),
                "longest_missing_run_in_vaquill": longest_false(found_o), "longest_extra_run_in_vaquill": longest_false(found_v),
                "ours_words_before_first_match": first_hit, "ours_words_after_last_match": last_hit,
                "margin_letters_vaquill": len(LONE.findall(vt)), "margin_letters_ours": len(LONE.findall(ot)), "tilde_vaquill": vt.count("~"), "tilde_ours": ot.count("~")})
json.dump(res, open(out_p, "w"))
print("integrity of reassembly:", dict(tot_checks))
med = lambda k: statistics.median(r[k] for r in res)
q = lambda k, p: sorted(r[k] for r in res)[int(p * (len(res) - 1))]
print("n compared:", len(res))
print("words, Vaquill / ours (median ratio):", round(med("ratio"), 3), "| p10", round(q("ratio", .1), 3), "p90", round(q("ratio", .9), 3))
print("share of OUR 5-grams found in Vaquill (median):", round(med("ours_in_vaquill"), 3), "p10", round(q("ours_in_vaquill", .1), 3), "p90", round(q("ours_in_vaquill", .9), 3))
print("share of VAQUILL 5-grams found in ours (median):", round(med("vaquill_in_ours"), 3), "p10", round(q("vaquill_in_ours", .1), 3), "p90", round(q("vaquill_in_ours", .9), 3))
print("longest run of our words missing from Vaquill (median / p90 / max):", med("longest_missing_run_in_vaquill"), q("longest_missing_run_in_vaquill", .9), max(r["longest_missing_run_in_vaquill"] for r in res))
print("longest run of Vaquill words absent from ours (median / p90 / max):", med("longest_extra_run_in_vaquill"), q("longest_extra_run_in_vaquill", .9), max(r["longest_extra_run_in_vaquill"] for r in res))
print("our words before first match in Vaquill (median/p90):", med("ours_words_before_first_match"), q("ours_words_before_first_match", .9), "| after last match:", med("ours_words_after_last_match"), q("ours_words_after_last_match", .9))
print("margin-letter lines per judgment: Vaquill median", med("margin_letters_vaquill"), "| ours median", med("margin_letters_ours"))
print("tilde per judgment: Vaquill median", med("tilde_vaquill"), "mean", round(statistics.mean(r["tilde_vaquill"] for r in res), 1), "| ours median", med("tilde_ours"), "mean", round(statistics.mean(r["tilde_ours"] for r in res), 1))
by = collections.defaultdict(list)
for r in res: by[r["year"] // 10 * 10].append(r["ours_in_vaquill"])
print("by decade, median share of our 5-grams found in Vaquill:", {k: round(statistics.median(v), 3) for k, v in sorted(by.items())})
by = collections.defaultdict(list)
for r in res: by[r["our_source"]].append(r["ours_in_vaquill"])
print("by our source:", {k: (len(v), round(statistics.median(v), 3)) for k, v in by.items()})
