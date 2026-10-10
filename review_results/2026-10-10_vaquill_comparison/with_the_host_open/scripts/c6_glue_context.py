import sys, re
import pyarrow.parquet as pq
tb = pq.read_table(sys.argv[1], filters=[("case_id", "=", "2021_INSC_473")]).to_pandas().sort_values("chunk_index")
txt = "\n".join(tb.text_original)
for pat in ("highcourt", "HighCourt", "ofAllahabad", "writpetition", "labourcourt", "beforethe"):
    for m in list(re.finditer(pat, txt, flags=re.I))[:2]:
        s = txt[max(0, m.start() - 70): m.end() + 70]
        print(pat, "->", repr(s))
        print("    code points around match:", [hex(ord(ch)) for ch in txt[m.start()-1:m.start()]] , "...", [hex(ord(ch)) for ch in txt[m.end():m.end()+1]])
# any exotic separators in the text?
import collections
cnt = collections.Counter(ch for ch in txt if ord(ch) > 127 or ord(ch) < 32)
print("non-ASCII/control characters present:", cnt.most_common(12))
