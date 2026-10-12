"""Evaluates Machine Spec v2 (review_tools/machine_spec_v2.py) on the index and the 30 used questions. Dev check only (the 30 are used up). No Voyage calls. PRIVATE."""
import collections, json, os, random, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, ROOT)
import machine_spec_v2 as S, pool_runner as PR, sci_index as si
head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, _, _ = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
N = len(metas)
marked = {a: collections.defaultdict(set) for a in S.ACTS}
by_pass = {a: [] for a in S.ACTS}
for i, m in enumerate(metas):
    for a in S.passage_acts(m["text"]):
        marked[a][m["doc"]].add(m["h"]); by_pass[a].append(i)
labels = S.judgment_labels((m["doc"], m["h"], m["text"]) for m in metas)
# previous numbers (draft v1 'mine', and Mr. Advocate's, from the 2026-10-12 tests)
v1 = {"PWDVA": (262, 18), "NDPS": (2584, 222), "POCSO": (721, 58), "SC/ST": (543, 52), "NI Act": (1935, 186), "PMLA": (810, 48), "UAPA": (568, 40), "DPA": (536, 56), "JJ Act": (677, 67), "PC Act": (3374, 401), "Arms Act": (2056, 253), "IT Act": (234, 16), "MV Act": (210, 16)}
adv = {"PWDVA": (0, 0), "NDPS": (2817, 251), "POCSO": (775, 59), "SC/ST": (331, 37), "NI Act": (1666, 177), "PMLA": (901, 48), "UAPA": (592, 43), "DPA": (573, 64), "JJ Act": (899, 93), "PC Act": (3401, 405), "Arms Act": (2063, 254), "IT Act": (238, 16), "MV Act": (210, 16)}
print(f"1. PASSAGE MARKERS IN THE INDEX ({N:,} passages). v2 = distinct passages; labelled = judgments with 3+ marked passages (66A rule applied to the IT Act)")
print(f"{'Act':9} {'v2 passages':>12} {'v2 labelled':>12} | {'draft v1 passages':>18} {'v1 labelled':>12} | {'Advocate passages':>18} {'labelled':>9}")
for a in S.ACTS:
    p = sum(len(v) for v in marked[a].values())
    print(f"{a:9} {p:12,} {len(labels[a]):12,} | {v1[a][0]:18,} {v1[a][1]:12,} | {adv[a][0]:18,} {adv[a][1]:9,}")
# NDPS: labelled judgments with no passage naming the NDPS Act at all
nd = re.compile(r"\bNDPS\b|Narcotic Drugs and Psychotropic Substances Act", re.S)
has_nd = collections.Counter(m["doc"] for m in metas if nd.search(m["text"]))
print("\n2. NDPS labelled judgments with NO passage that names the NDPS Act:", sum(1 for d in labels["NDPS"] if has_nd.get(d, 0) == 0), "of", len(labels["NDPS"]), "(Mr. Advocate's draft: 15 of 61 among those carrying the two standalone phrases)")
# sample passages the v2 marker flags, 3 per Act, to read
rnd = random.Random(11)
print("\n3. SAMPLES OF PASSAGES THE v2 MARKER FLAGS (3 per Act, random)")
for a in S.ACTS:
    for i in rnd.sample(by_pass[a], min(3, len(by_pass[a]))):
        t = re.sub(r"\s+", " ", metas[i]["text"])
        ms = [p.search(metas[i]["text"]) for p in S.COMPILED[a]["passage"]]
        ms = [x for x in ms if x]; k = min(ms, key=lambda x: x.start()).start() if ms else 0
        print(f"   [{a}] doc {metas[i]['doc']}: ...{re.sub(chr(10), ' ', metas[i]['text'][max(0, k - 50):k + 130])}")
# 4. used questions
tun = json.load(open(os.path.join(ROOT, "review_results/2026-10-10_real30_rerank_test_pack_v2/pool_with_rerank_arms.json"), encoding="utf-8"))["questions"]
sealed = json.load(open(os.path.join(ROOT, "review_results/2026-10-10_sealed_run/pool.json"), encoding="utf-8"))["questions"]
qs = {q["qid"]: q["question"] for q in tun + sealed}
print("\n4. WHICH ACTS FIRE ON THE 30 USED QUESTIONS")
n1 = n2 = 0
for qid in sorted(qs):
    a1, a2 = S.question_acts(qs[qid], "N1"), S.question_acts(qs[qid], "N2")
    n1 += bool(a1); n2 += bool(a2)
    if a1 or a2:
        print(f"   {qid}: N1 {sorted(a1) or '-'} | N2 {sorted(a2) or '-'} | {qs[qid][:80]}")
print(f"   N1 fires on {n1} of 30, N2 on {n2} of 30")
json.dump({"labelled": {a: len(labels[a]) for a in S.ACTS}, "passages": {a: sum(len(v) for v in marked[a].values()) for a in S.ACTS}}, open(os.path.join(HERE, "spec_v2_index_counts.json"), "w"), indent=1)
