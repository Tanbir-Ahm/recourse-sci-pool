"""For each entry of the 'overruled after 2015' PDF, find the overruling judgment in our collection and print the sentences of it that mention the earlier case,
with those that carry an adverse cue first. Read-only on the corpus. Run with python3 (our own code), data from the PDF is only parsed as JSON.
usage: python3 verify_after2015.py OUT.txt"""
import sys, re, json, sqlite3, collections
sys.path.insert(0, "/home/user/recourse-sci-pool")
from goodlaw import corpus as K, textutil as X

SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/"
rows = json.load(open(SP + "pdf2_in/rows.json"))
C = K.Corpus(SP + "corpus.sqlite")
con = C.con

# the overruling judgments as found in the collection (checked by hand against dates and benches)
B = {
    "K.S. Puttaswamy (Retd.) v. Union of India": "b2017_10_569_999",
    "Krishna Kumar Singh v. State of Bihar": "c44452",
    "State of Jharkhand v. Hindustan Construction Co. Ltd.": "b2017_13_1009_1052",
    "Commissioner of Customs v. Dilip Kumar & Co.": "b2018_7_1191_1231",
    "Navtej Singh Johar v. Union of India": "b2018_7_379_746",
    "Joseph Shine v. Union of India": "b2018_11_765_950",
    "Nusli Neville Wadia v. Ivory Properties": "b2019_15_795_864",
    "Vijay Industries v. CIT": "b2019_4_928_944",
    "Vinubhai Haribhai Malaviya v. State of Gujarat": "b2019_15_936_989",
    "Ravinder Kaur Grewal v. Manjit Kaur": "b2019_11_74_134",
    "Sushila Aggarwal v. State (NCT of Delhi)": "b2020_2_1_131",
    "Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal": "b2020_7_180_282",
    "Mukesh Singh v. State (Narcotic Branch of Delhi)": "b2020_9_245_302",
    "Vineeta Sharma v. Rakesh Sharma": "b2020_10_135_237",
    "Vidya Drolia v. Durga Trading Corporation": "b2020_11_1001_1180",
    "Vikash Kumar v. UPSC": "b2021_12_311_364",
    "Government of Maharashtra v. Borse Brothers Engineers & Contractors": "b2021_3_193_254",
    "Indore Development Authority v. Manoharlal": "b2020_3_1_328",
    "Delhi Development Authority v. Asha Prakash / later application of Indore Development Authority": "b2023_1_919_924",
    "Union of India v. Parshotam Dass": None,
    "Arup Bhuyan v. State of Assam (larger Bench)": "b2023_8_496_580",
    "Unicorn Industries v. Union of India": "b2019_17_1013_1047",
    "Aligarh Muslim University v. Naresh Agarwal": "b2024_11_1647_2038",
    "State of Punjab v. Davinder Singh": "b2024_8_1321_1672",
    "Mineral Area Development Authority v. Steel Authority of India": "b2024_7_1549_1846",
    "State of U.P. v. Lalta Prasad Vaish & Sons": "b2024_10_1931_2182",
    "High Court Bar Association, Allahabad v. State of U.P.": "b2024_2_946_988",
    "Bajaj Allianz General Insurance Co. Ltd. v. Rambha Devi": "b2024_11_541_640",
    "N.N. Global Mercantile Pvt. Ltd. v. Indo Unique Flame Ltd. (Constitution Bench)": "b2023_9_285_492",
    "Radhika Agarwal v. Union of India": "b2025_2_1331_1395",
}
CUE = re.compile(r"overrul|over-rul|not (?:a )?good law|no longer (?:a )?good law|per incuriam|wrongly decided|incorrectly decided|disapprov|not (?:the )?correct|does not lay down|do not lay down|"
                 r"erroneous|cannot be (?:sustained|accepted|upheld)|reversed|set aside|not (?:been )?(?:rightly|correctly)|bad in law|stand[s]? overruled|no longer holds|dissent|not binding", re.I)
STOP = set("v vs versus the and of in re state union india ltd limited pvt private co corporation dead lrs through retd".split())


def aliases(name):
    first = re.split(r"\s+v\.?\s+", name, maxsplit=1)[0]
    first = re.sub(r"\([^)]*\)", " ", first)
    toks = [t for t in re.findall(r"[A-Za-z][A-Za-z.&']*", first) if t.lower().strip(".") not in STOP]
    out = []
    if toks:
        out.append(r"\W*".join(re.escape(t.strip(".")) for t in toks))                       # the first party in full
    for t in toks:
        w = t.strip(".")
        if len(w) >= 6 and w.isalpha():
            n = C.doc_frequency(w.lower()) or 0
            if n <= 400:
                out.append(re.escape(w))
    return list(dict.fromkeys(out))


def snippets(text, aliases_, width=330):
    hits = []
    for a in aliases_:
        for m in re.finditer(a, text, re.I):
            hits.append((m.start(), m.end(), a))
    hits.sort()
    out, last = [], -10**9
    for s, e, a in hits:
        if s - last < 250:
            continue
        last = s
        lo, hi = max(0, s - width), min(len(text), e + width)
        win = text[lo:hi]
        cue = bool(CUE.search(text[max(0, s - 220):e + 260]))
        out.append((cue, s, re.sub(r"\s+", " ", win)))
    return out


report = []
cache = {}
for r in rows:
    bk = B.get(r["b"])
    head = f'#{r["no"]:>2} A: {r["a"]} ({r["a_year"]})  <-  B: {r["b"]} ({r["b_year"]})  [{r["status"]}]'
    if not bk:
        report.append(head + "\n   B NOT IN THE COLLECTION: cannot read it here.\n")
        continue
    d = C.get(bk, with_text=False)
    if bk not in cache:
        cache[bk] = X.flatten(C.get(bk)["text"])
    text = cache[bk]
    al = aliases(r["a"])
    sn = snippets(text, al)
    cue_sn = [x for x in sn if x[0]]
    report.append(head + f'\n   B in collection: {bk} {d["date"]} bench>= {d["bench_size"]} | aliases {al[:4]} | mentions {len(sn)}, with an adverse cue nearby {len(cue_sn)}')
    for cue, pos, win in (cue_sn[:3] if cue_sn else sn[:2]):
        report.append(f'   {"[CUE]" if cue else "[no cue]"} @{pos}: …{win}…')
    report.append("")
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(report))
print("rows:", len(rows), "report chars:", len("\n".join(report)))
