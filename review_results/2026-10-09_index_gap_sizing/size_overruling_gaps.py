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


def _tok(t):
    return [x for x in re.findall(r"[a-z]{4,}", (t or "").lower())]


def _fuzzy(a, b):
    import difflib
    return a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.85


def parties_agree(side_name, doc_name):
    """Spelling-tolerant check that two names are the same case. For each party, one of the register name's longer words (6 letters or more; any word of 4 or more when it has none) has a close
    match among the words of the same party of the corpus title: Samsher/Shamsher, Allianz/Alliance, 'Vinubhai Haribhai Malaviya' / 'HARIBHAI MALAVIYA', 'Justice K S Puttaswamy' / 'K.S. Puttaswamy'
    pass; a different case that merely shares a citation key does not."""
    sa, sb = R.party_sigs(side_name), R.party_sigs(doc_name)
    for pa, pb in zip(sa, sb):
        wa, wb = _tok(" ".join(pa)), _tok(" ".join(pb))
        if not wa or not wb:
            continue
        long_words = [w for w in wa if len(w) >= 6] or wa
        if not any(_fuzzy(w, x) for w in long_words for x in wb):
            return False
    return True


# Corpus titles that lost a word, and a register name with a typo, found by hand (the register's own name matching cannot see them): register name -> corpus document keys
ALIASES = {"Vinubhai Haribhai Malaviya v. State of Gujarat": ["b2019_15_936_989"],            # held as 'HARIBHAI MALAVIYA AND ORS. versus THE STATE OF GUJARAT AND ANR.'
           "P. Prabhakaran v. P. Jayarajan": ["c26708", "c30898"]}                        # the register has 'P.', the judgment is 'K. Prabhakaran v. P. Jayarajan' (2005)


def find(side, strict=True):
    """corpus docs that are the same decision as a register side: a shared citation key or both parties in order with the years within one (the register's own rule), and, when strict,
    the names must also agree (a shared SCR page number alone matched other cases: Dagi Ram, Prabhakaran Nair, T.M. Balakrishna Mudaliar), and a document of exactly the register's year is
    preferred to one a year away (later orders of the same name are not the decision)."""
    out = set()
    names = [side.get("name", "")] + list(side.get("alt_names", []))
    for kk in side.get("keys", []):
        for k in by_key.get(kk, ()):
            if reg._same_decision(side, rec[k]) and (not strict or any(parties_agree(nm, rec[k]["name"]) for nm in names)):
                out.add(k)
    for nm in names:
        s1, s2 = R.party_sigs(nm)
        if R.indexable(list(s1), list(s2)):
            for k in by_first.get(s1[0], ()):
                if reg._same_decision(dict(side, name=nm), rec[k]):
                    out.add(k)
    if strict:
        for nm, keys in ALIASES.items():
            if any(R.party_sigs(nm)[0][-1:] == R.party_sigs(x)[0][-1:] and R.party_sigs(nm)[1][:1] == R.party_sigs(x)[1][:1] for x in names):
                out.update(k for k in keys if k in rec)
    if strict and side.get("year"):
        exact = {k for k in out if rec[k]["year"] == side["year"]}
        if exact:
            out = exact
    return sorted(out)


HELD = ("in_index", "duplicate", "near_duplicate", "in_crawl")        # the index holds this judgment, or an identical or near-identical copy of it


def held(k):
    return status.get(k, (None, ""))[1] in HELD


def size(strict):
    rows_out, missing = [], {}
    cnt = {"rows": 0, "overruled_in_corpus": 0, "overruled_in_index": 0, "overruling_in_corpus": 0, "overruling_in_index": 0,
           "pairs_overruled_in_index_overruling_missing_from_index": 0, "of_which_overruling_in_collection_but_filtered_out": 0, "of_which_overruling_not_in_collection": 0}
    for r in reg.rows:
        cnt["rows"] += 1
        a, b = find(r["overruled"], strict), find(r["overruling"], strict)
        a_in = [k for k in a if held(k)]
        b_in = [k for k in b if held(k)]
        cnt["overruled_in_corpus"] += bool(a)
        cnt["overruled_in_index"] += bool(a_in)
        cnt["overruling_in_corpus"] += bool(b)
        cnt["overruling_in_index"] += bool(b_in)
        if a_in and not b_in:
            cnt["pairs_overruled_in_index_overruling_missing_from_index"] += 1
            kind = "not_in_collection" if not b else ("filtered_out" if any(status.get(k, (None, ""))[1] == "not_criminal" for k in b) else "other_skip")
            cnt["of_which_overruling_in_collection_but_filtered_out" if kind == "filtered_out" else "of_which_overruling_not_in_collection" if kind == "not_in_collection" else "of_which_other_skip"] = \
                cnt.get("of_which_overruling_in_collection_but_filtered_out" if kind == "filtered_out" else "of_which_overruling_not_in_collection" if kind == "not_in_collection" else "of_which_other_skip", 0) + 1
            row = {"register_row": r["id"], "trust": r["trust"], "treatment": r["treatment"], "overruled_in_index": [(k, rec[k]["name"][:70], status[k][0]) for k in a_in][:2],
                   "overruling": r["overruling"]["name"], "overruling_year": r["overruling"].get("year"), "overruling_court": r["overruling"].get("court"), "kind": kind,
                   "overruling_docs": [(k, rec[k]["name"][:70], rec[k]["text_len"], status.get(k, (None, ""))[1], status.get(k, (None, ""))[0], rec[k]["year"]) for k in b][:3]}
            rows_out.append(row)
            if kind == "filtered_out":
                for k in b:
                    if status.get(k, (None, ""))[1] == "not_criminal":
                        missing[k] = rec[k]["text_len"]
    chars = sum(missing.values())
    summary = {**cnt, "distinct_overruling_judgments_to_add_from_the_collection": len(missing), "their_characters": chars, "approx_tokens": round(chars / 3.87),
               "approx_dollars_at_0.12_per_million": round(chars / 3.87 * 0.12 / 1e6, 3)}
    return summary, rows_out


strict_summary, strict_rows = size(True)
meta = {k: (s_, sid, bp, title, year, date, insc) for k, s_, sid, bp, title, pet, resp, year, cites, tl, date, insc in docs}
supp = {}
for x in strict_rows:
    if x["kind"] != "filtered_out":
        continue
    for k, name, tl, state, idx_doc, y in x["overruling_docs"]:
        if state != "not_criminal":
            continue
        source, sid, bp, title, year, date, insc = meta[k]
        e = supp.setdefault(k, {"doc_key": k, "source": source, "src_id": sid, "bucket_path": bp, "index_doc": idx_doc, "title": re.sub(r"\s+", " ", title or name), "year": year, "date": date,
                                "insc": insc, "text_len": tl, "register_rows": []})
        e["register_rows"].append({"row": x["register_row"], "corrects": x["overruled_in_index"][0][1], "correcting_judgment_named_in_register": x["overruling"], "trust": x["trust"]})
json.dump({"note": "The correcting judgments that sit in the collection but that the index left out as 'not criminal law' (cue-word density under 10 per 10,000 characters, no criminal heading), each linked in the Overruled "
                   "Register to a ruling the index holds. Names checked as well as citation keys. Input of review_tools/build_supplement.py. PRIVATE (names register rows).",
           "docs": sorted(supp.values(), key=lambda e: -e["text_len"])}, open(OUT + "/supplement_docs.json", "w"), indent=1, ensure_ascii=False)
loose_summary, loose_rows = size(False)
json.dump({"summary": strict_summary, "pairs": strict_rows,
           "earlier_loose_matching": {"note": "first version of this sizing (2026-10-09): a shared citation key alone made two judgments 'the same decision'. It also matched Dagi Ram Pindi Lal and Mohan Kumar Singhania "
                                              "(for Aslam Babalal Desai), T.M. Balakrishna Mudaliar (for Kartar Singh), Prabhakaran Nair (for Antulay), later Common Cause orders and the 2016 reference order in Mukund Dewangan; "
                                              "the figures above require the names to agree as well and prefer the register's own year.", "summary": loose_summary, "pairs": loose_rows}},
          open(OUT + "/overruling_gaps.json", "w"), indent=1, ensure_ascii=False)
print("STRICT", json.dumps(strict_summary, indent=1))
print("LOOSE (earlier)", json.dumps({k: loose_summary[k] for k in ("pairs_overruled_in_index_overruling_missing_from_index", "of_which_overruling_in_collection_but_filtered_out", "of_which_overruling_not_in_collection", "distinct_overruling_judgments_to_add_from_the_collection", "approx_dollars_at_0.12_per_million")}))
for x in strict_rows:
    print(x["register_row"], x["trust"][:4], "|", x["overruled_in_index"][0][1][:40], "-> overruled by", x["overruling"][:45], x["overruling_year"], "|", x["kind"], [(d[0], d[1][:30], d[5], d[2]) for d in x["overruling_docs"]][:3])
