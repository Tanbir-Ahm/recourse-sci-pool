import sys, json, collections
import pandas as pd
D = sys.argv[1]
pay = json.load(open(D + "/sc_payloads.json"))
n = len(pay)
print("SC payload sample:", n)
print("language_code:", collections.Counter(p["language_code"] for p in pay))
nz = lambda k: sum(1 for p in pay if p.get(k) not in (None, "", [], {}, 0))
for k in ["acts_referenced", "cases_cited", "cited_by_count", "treatment_mentions", "petitioners_all", "case_number", "scc_citation", "air_citation", "has_legacy_fonts", "pdf_url", "pdf_urls"]:
    print(f"  {k:20s} non-empty in {nz(k)} of {n} ({nz(k)/n:.0%})")
print("decision_date format sample:", [p["decision_date"] for p in pay[:4]])
tm = [p for p in pay if p.get("treatment_mentions")]
print("\ntreatment_mentions examples:")
for p in tm[:4]:
    print("  ", p["chunk_id"], json.dumps(p["treatment_mentions"])[:400])
print("\npdf_url hosts/patterns:", collections.Counter(p["pdf_url"].split("/")[2][:12] + "/" + "/".join(p["pdf_url"].split("/")[3:5]) for p in pay if p.get("pdf_url")))
# compare with the parquet text
t = pd.read_parquet(sys.argv[2], columns=["case_id", "chunk_index", "text_original"])
key = {(r.case_id, int(r.chunk_index)): r.text_original for r in t.itertuples()}
same = diff = missing = 0
ex = []
for p in pay:
    if p["language_code"] != "EN": continue
    v = key.get((p["case_id"], p["chunk_index"]))
    if v is None: missing += 1
    elif v == p["text"]: same += 1
    else:
        diff += 1
        if len(ex) < 2: ex.append((p["chunk_id"], len(v), len(p["text"])))
print("\npayload text vs parquet text_original (same chunk): identical", same, "| different", diff, "| chunk not in parquet", missing, ex)
