"""How many judgments that correct (overrule, reverse, set aside) a judgment the index holds are themselves missing from the index? Uses the Overruled Register (1,765 rows) only to find
the pairs, the corpus store to find each side, and the index's own document records to see what is embedded. Read-only; no search, no spend. PRIVATE (it names register rows)."""
import glob, gzip, json, os, re, sqlite3, sys
ROOT = "/home/user/recourse-sci-pool"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/review_tools")
from goodlaw import register as R
import real30_authority_coverage as C

SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad"
OUT = os.path.dirname(os.path.abspath(__file__))
INDEX = "/home/user/recourse-sci-index"
reg = R.Register.load()
con = sqlite3.connect(SP + "/corpus.sqlite")
docs = list(con.execute("select doc_key, source, src_id, bucket_path, title, pet, resp, year, cites, text_len, date, insc from docs"))
status = C.index_status(INDEX, [(k, s, sid, bp) for k, s, sid, bp, *_ in docs])      # doc_key -> (index doc id, 'in_index' | skip reason)

by_first, by_key, rec = {}, {}, {}
for k, s, sid, bp, title, pet, resp, year, cites, tl, date, insc in docs:
    name = (title or f"{pet} v. {resp}")
    name = re.sub(r"\s+versus\s+|\s+vs\.?\s+", " v. ", name, flags=re.I)
    keys = json.loads(cites) if cites else []
    rec[k] = {"name": name, "keys": keys, "year": year, "years": [year] if year else [], "text_len": tl or 0, "title": title, "date": date}
    s1, s2 = R.party_sigs(name)
    if R.indexable(list(s1), list(s2)):
        by_first.setdefault(s1[0], []).append(k)
    for kk in keys:
        by_key.setdefault(kk, []).append(k)


def find(side):
    """corpus docs that are the same decision as a register side (a shared citation key, or both parties in order and the years within one)."""
    out = set()
    for kk in side.get("keys", []):
        for k in by_key.get(kk, ()):
            if reg._same_decision(side, rec[k]):
                out.add(k)
    for nm in [side.get("name", "")] + list(side.get("alt_names", [])):
        s1, s2 = R.party_sigs(nm)
        if R.indexable(list(s1), list(s2)):
            for k in by_first.get(s1[0], ()):
                if reg._same_decision(dict(side, name=nm), rec[k]):
                    out.add(k)
    return sorted(out)


rows_out, missing = [], {}
cnt = {"rows": 0, "overruled_in_corpus": 0, "overruled_in_index": 0, "overruling_in_corpus": 0, "overruling_in_index": 0,
       "pairs_overruled_in_index_overruling_missing_from_index": 0, "of_which_overruling_in_collection_but_filtered_out": 0, "of_which_overruling_not_in_collection": 0}
for r in reg.rows:
    cnt["rows"] += 1
    a, b = find(r["overruled"]), find(r["overruling"])
    a_in = [k for k in a if status.get(k, (None, ""))[1] == "in_index"]
    b_in = [k for k in b if status.get(k, (None, ""))[1] == "in_index"]
    cnt["overruled_in_corpus"] += bool(a)
    cnt["overruled_in_index"] += bool(a_in)
    cnt["overruling_in_corpus"] += bool(b)
    cnt["overruling_in_index"] += bool(b_in)
    if a_in and not b_in:
        cnt["pairs_overruled_in_index_overruling_missing_from_index"] += 1
        kind = "filtered_out" if b else "not_in_collection"
        cnt["of_which_overruling_in_collection_but_filtered_out" if b else "of_which_overruling_not_in_collection"] += 1
        row = {"register_row": r["id"], "trust": r["trust"], "treatment": r["treatment"], "overruled_in_index": [(k, rec[k]["name"][:70]) for k in a_in][:2],
               "overruling": r["overruling"]["name"], "overruling_year": r["overruling"].get("year"), "overruling_court": r["overruling"].get("court"), "kind": kind,
               "overruling_docs": [(k, rec[k]["name"][:70], rec[k]["text_len"], status.get(k, (None, ""))[1]) for k in b][:3]}
        rows_out.append(row)
        for k in b:
            missing[k] = rec[k]["text_len"]
chars = sum(missing.values())
summary = {**cnt, "distinct_overruling_judgments_to_add_from_the_collection": len(missing), "their_characters": chars, "approx_tokens": round(chars / 3.87), "approx_dollars_at_0.12_per_million": round(chars / 3.87 * 0.12 / 1e6, 3)}
json.dump({"summary": summary, "pairs": rows_out}, open(OUT + "/overruling_gaps.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(summary, indent=1))
for x in rows_out[:60]:
    print(x["register_row"], x["trust"][:4], "|", x["overruled_in_index"][0][1][:45], "-> overruled by", x["overruling"][:45], x["overruling_year"], x["overruling_court"], "|", x["kind"], [(d[0], d[3]) for d in x["overruling_docs"]][:2])
