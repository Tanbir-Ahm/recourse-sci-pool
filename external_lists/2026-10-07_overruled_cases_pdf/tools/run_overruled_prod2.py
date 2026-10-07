import sys, json, collections, time
sys.path.insert(0, "/home/user/recourse-sci-pool")
from goodlaw import evaluate as E, corpus as K
SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/"
half, i, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
pairs = [p for p in json.load(open(SP + "ovr/pairs_clean.json")) if p["half"] == half]
pairs = pairs[i::n]
tup = [(p["target"], p["citing"], "O", str(p["no"])) for p in pairs]
corpus = K.Corpus(SP + "corpus.sqlite")
t = time.time()
res = E.production_rows(corpus, tup, log=lambda s: print(s, "%.0fs" % (time.time() - t), flush=True))
byno = {int(r[3]): r for r in res}
out = []
for p in pairs:
    r = byno[p["no"]]
    out.append(dict(no=p["no"], target=p["target"], citing=p["citing"], label=r[4], cue=r[5], sentence=r[6], eligible=r[7], hedged=r[8], binding=r[9], speaker=r[10]))
json.dump(out, open(SP + f"ovr/prod_{half}_part{i}.json", "w"), ensure_ascii=False, indent=0)
print("done", len(out), "%.0fs" % (time.time() - t), flush=True)
