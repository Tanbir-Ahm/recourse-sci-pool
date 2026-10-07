import sys, json, collections, time
sys.path.insert(0, "/home/user/recourse-sci-pool")
from goodlaw import evaluate as E
SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/"
half = sys.argv[1]
pairs = [p for p in json.load(open(SP + "ovr/pairs_final.json")) if p["half"] == half]
tup = [(p["target"], p["citing"], "O", str(p["no"])) for p in pairs]
t = time.time()
res = E.run(SP + "corpus.sqlite", tup, workers=4)
print("fast reader on", len(res), "pairs in %.0fs" % (time.time() - t))
out = []
for p, r in zip(pairs, res):
    out.append(dict(no=p["no"], target=p["target"], citing=p["citing"], label=r[4], cue=r[5], sentence=r[6], eligible=r[7], hedged=r[8], binding=r[9], speaker=r[10]))
json.dump(out, open(SP + f"ovr/fast_{half}.json", "w"), ensure_ascii=False, indent=0)
C = collections.Counter(o["label"] for o in out)
print(C)
adv = [o for o in out if o["label"] in E.ADVERSE]
print("adverse reading:", len(adv), "of", len(out))
print("adverse reading by an eligible (court/headnote, confident) mention:", sum(1 for o in adv if o["eligible"]))
print("no mention found:", C[None])
