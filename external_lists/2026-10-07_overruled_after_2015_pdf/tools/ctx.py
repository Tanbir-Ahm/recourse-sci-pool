"""usage: python3 ctx.py DOCKEY REGEX [width] [max] -- print windows around regex matches in one collection judgment (read-only)."""
import sys, re
sys.path.insert(0, "/home/user/recourse-sci-pool")
from goodlaw import corpus as K, textutil as X
SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/"
C = K.Corpus(SP + "corpus.sqlite")
d = C.get(sys.argv[1])
t = X.flatten(d["text"])
w = int(sys.argv[3]) if len(sys.argv) > 3 else 350
mx = int(sys.argv[4]) if len(sys.argv) > 4 else 6
print("DOC", sys.argv[1], d.get("title"), d.get("date"), "chars", len(t))
last = -10**9; n = 0
for m in re.finditer(sys.argv[2], t, re.I):
    if m.start() - last < w: continue
    last = m.start(); n += 1
    if n > mx: break
    print(f"--- @{m.start()}: …" + re.sub(r"\s+", " ", t[max(0, m.start()-w): m.end()+w]) + "…")
print("matches shown:", min(n, mx))
