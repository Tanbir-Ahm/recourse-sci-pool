import sys, json, re, textwrap
sys.path.insert(0, "/home/user/recourse-sci-pool")
from goodlaw import corpus as K
SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/"
corpus = K.Corpus(SP + "corpus.sqlite")
clean = {p["no"]: p for p in json.load(open(SP + "ovr/pairs_clean.json"))}
res = json.load(open(SP + "ovr/fast_tune.json"))
ADV = ("OVERRULES", "DISAGREES", "DOUBTS_REFERS")
STOP = set("vs v the and others another of in re state union india uoi ors anr co ltd limited private pvt etc by through its dead lrs lr thr m/s versus commissioner".split())
CUE = re.compile(r'overrul|over-rul|no longer good law|not good law|wrongly decided|incorrectly decided|not correctly decided|does not lay down|do not lay down|per incuriam|cannot be (?:sustained|upheld|accepted)|bad in law|not (?:the )?correct (?:view|law)|is not correct|erroneous|disapprove|dissent|differ(?:s|ed)? from', re.I)
out = []
for r in res:
    if r["no"] not in clean or r["label"] in ADV: continue
    p = clean[r["no"]]
    t = corpus.get(p["target"], with_text=False); c = corpus.get(p["citing"])
    first = [w for w in re.sub(r'[^a-z ]', ' ', (t["pet"] or t["title"]).lower()).split() if w not in STOP and len(w) > 3][:2]
    resp = [w for w in re.sub(r'[^a-z ]', ' ', (t["resp"] or "").lower()).split() if w not in STOP and len(w) > 3][:1]
    text = c["text"]
    hits = []
    for m in CUE.finditer(text):
        win = text[max(0, m.start() - 500): m.end() + 500].lower()
        if first and all(w in win for w in first[:1]) :
            hits.append(re.sub(r'\s+', ' ', text[max(0, m.start() - 220): m.end() + 220]))
    out.append((r["no"], p["t_title"][:50], p["c_title"][:50], r["label"], hits[:2]))
json.dump(out, open(SP + "ovr/miss_context.json", "w"), ensure_ascii=False, indent=0)
print(len(out), "non-adverse pairs;", sum(1 for o in out if o[4]), "with an overrule-type phrase near the case's name")
