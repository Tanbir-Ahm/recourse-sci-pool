import sys, json, gzip, re, collections
D = sys.argv[1]
tags = collections.Counter(); n = tot = 0
stem = {"OVERRULED": "overrul", "DISTINGUISHED": "distinguish", "APPLIED": "appl", "HARMONIZED": "harmoni", "FOLLOWED": "follow", "APPROVED": "approv", "DOUBTED": "doubt", "REVERSED": "revers", "AFFIRMED": "affirm", "CRITICIZED": "criticiz", "EXPLAINED": "explain", "QUESTIONED": "question", "DISAPPROVED": "disapprov", "MODIFIED": "modif"}
present = collections.Counter(); absent = collections.Counter(); ex = []
nonempty_fields = collections.Counter(); n_all = 0
with gzip.open(D + "/sc_shard0_payload.jsonl.gz", "rt", encoding="utf-8") as fh:
    for line in fh:
        p = json.loads(line); n_all += 1
        for k in ("acts_referenced", "cases_cited", "cited_by_count", "petitioners_all", "case_number", "scc_citation", "air_citation"):
            if p.get(k) not in (None, "", [], {}, 0): nonempty_fields[k] += 1
        tm = p.get("treatment_mentions")
        if not tm: continue
        tot += 1
        t = p["text"].lower()
        for tag in tm:
            tags[tag] += 1
            s = stem.get(tag.upper(), tag.lower()[:6])
            (present if s in t else absent)[tag] += 1
        if len(ex) < 3 and "OVERRULED" in tm:
            m = re.search(r".{120}overrul.{120}", p["text"], flags=re.I | re.S)
            ex.append((p["chunk_id"], tm, m.group(0).replace("\n", " ") if m else None))
print("shard 0 SC points:", n_all, "| with treatment_mentions:", tot, f"({tot/n_all:.1%})")
print("tag counts:", dict(tags.most_common(12)))
print("tag word present in chunk text / absent:", {k: (present[k], absent[k]) for k in tags})
print("fields non-empty over ALL shard-0 SC points:", {k: nonempty_fields[k] for k in ("acts_referenced", "cases_cited", "cited_by_count", "petitioners_all", "case_number", "scc_citation", "air_citation")})
for e in ex: print(e)
