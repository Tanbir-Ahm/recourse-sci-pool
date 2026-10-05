"""Metadata-only matching of the open bucket against our crawl. No PDF is downloaded.

Steps: (1) read the bucket's per-year metadata tables, drop second listings of the same judgment (same file path, date and title);
(2) attach each judgment's PDF size from the bucket's anonymous file listing; (3) for judgments dated on or before 4 May 2017
(the crawl's last date) look for the same judgment in the crawl by party names (found in the first 3,500 characters of each crawled
text) and, where the crawl text gave a date, by date as well.

Tiers (strongest first):
  T1  both parties' distinctive words are found in a crawled text AND that text's own date equals the bucket's decision date
  T2  names match (as T1) and the crawled text gives a date within 7 days of the bucket's but not equal
  T3  names match (as T1) in a crawled text that gave no date; accepted only if exactly one such text exists
  T3x names match several undated crawled texts (ambiguous) - counted as matched but flagged
  none no crawled text matches
Writes registry.csv, summary.json.
"""
import csv, collections, datetime, glob, gzip, json, re, sys
import pandas as pd

S = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad"
CUT = pd.Timestamp("2017-05-04")
STOP = set("""versus vs v and ors anr anrs others another the of in for to by through lrs lr dead legal representatives
representative thr his her their its etc ltd limited pvt private co company shri sri smt dr mr mrs ms m s no nos""".split())


def toks(s):
    return [t for t in re.findall(r"[a-z0-9]+", str(s).lower()) if t not in STOP and len(t) > 1]


# ---- bucket ---------------------------------------------------------------------------------------------------------
parts = []
for f in sorted(glob.glob(f"{S}/bucket/meta_*.parquet")):
    d = pd.read_parquet(f)
    parts.append(d)
raw = pd.concat(parts, ignore_index=True)
norm = lambda s: re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()
raw["tk"] = raw.title.map(norm)
bk = raw.drop_duplicates(["path", "decision_date", "tk"]).reset_index(drop=True)
bk["d"] = pd.to_datetime(bk.decision_date, format="%d-%m-%Y")
sizes = json.load(open(f"{S}/match/bucket_pdf_sizes.json"))
dy = bk.d.dt.year.astype(str)


def pick_key(row_year_folder_candidates, path):
    for y in row_year_folder_candidates:
        k = f"data/pdf/year={y}/english/{path}_EN.pdf"
        if k in sizes:
            return k
    return None


# the bucket stores some judgments under the year folder of the decision, some of the listing's own year; try both
keys = []
for i, r in bk.iterrows():
    keys.append(pick_key([str(r.d.year), str(r.year), str(r.d.year + 1), str(r.d.year - 1)], r.path))
bk["key"] = keys
bk["size"] = bk.key.map(sizes)
print("distinct judgments", len(bk), "raw rows", len(raw), "no pdf found", bk["size"].isna().sum(), file=sys.stderr)

# ---- crawl ----------------------------------------------------------------------------------------------------------
table = {r["id"]: r for r in json.load(open(f"{S}/crawl_table.json"))}
heads = {}
for l in gzip.open(f"{S}/heads.jsonl.gz", "rt", encoding="utf-8"):
    r = json.loads(l)
    heads[r["id"]] = set(toks(r["head"]))


def cdate(r):
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})$", r.get("date") or "")
    if not m:
        return None
    try:
        return datetime.date(int(m[3]), int(m[2]), int(m[1]))
    except ValueError:
        return None


cd = {i: cdate(table[i]) for i in heads}
post = collections.defaultdict(set)
for i, ts in heads.items():
    for t in ts:
        post[t].add(i)
df_ = {t: len(v) for t, v in post.items()}


def party_sets(r):
    p, q = toks(r.petitioner if isinstance(r.petitioner, str) else ""), toks(r.respondent if isinstance(r.respondent, str) else "")
    if not p or not q:
        p = toks(str(r.title).split(" versus ")[0]); q = toks(" ".join(str(r.title).split(" versus ")[1:]))
    return set(p), set(q)


def candidates(P, Q):
    allt = P | Q
    if not allt:
        return set()
    rare = sorted(allt, key=lambda t: df_.get(t, 0))
    # require the 2 rarest tokens (that exist in the crawl heads) to co-occur, then score coverage of both parties
    use = [t for t in rare if df_.get(t, 0) > 0][:2]
    if not use or (len(use) < min(2, len(allt)) and any(df_.get(t, 0) == 0 for t in rare[:2])):
        return set()
    c = None
    for t in use:
        c = post[t] if c is None else c & post[t]
        if not c:
            return set()
    return c


def cover(S_, heads_ts):
    return len(S_ & heads_ts) / len(S_) if S_ else 1.0


out = []
tier_counts = collections.Counter()
for r in bk.itertuples():
    if r.d > CUT:
        out.append((r.Index, "after", "")); continue
    P, Q = party_sets(r)
    best = {"T1": [], "T2": [], "T3": []}
    for i in candidates(P, Q):
        if min(cover(P, heads[i]), cover(Q, heads[i])) < 0.75:
            continue
        d = cd[i]
        if d is None:
            best["T3"].append(i)
        elif d == r.d.date():
            best["T1"].append(i)
        elif abs((d - r.d.date()).days) <= 7:
            best["T2"].append(i)
    if best["T1"]:
        out.append((r.Index, "T1", ";".join(map(str, sorted(best["T1"])))))
    elif best["T2"]:
        out.append((r.Index, "T2", ";".join(map(str, sorted(best["T2"])))))
    elif len(best["T3"]) == 1:
        out.append((r.Index, "T3", str(best["T3"][0])))
    elif len(best["T3"]) > 1:
        out.append((r.Index, "T3x", ";".join(map(str, sorted(best["T3"])))))
    else:
        out.append((r.Index, "none", ""))
res = pd.DataFrame(out, columns=["i", "tier", "crawl_ids"]).set_index("i")
bk = bk.join(res)
bk["dyear"] = bk.d.dt.year
bk[["decision_date", "dyear", "title", "path", "key", "size", "case_id", "citation", "tier", "crawl_ids"]].to_csv("registry.csv", index=False)
print(bk.tier.value_counts().to_string(), file=sys.stderr)
