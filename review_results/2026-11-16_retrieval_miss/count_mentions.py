"""How many judgments of the newer index name each lead in their text (keyword search of the passages) against how many the authority table counts as naming it. Free (no model call)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, ROOT); os.chdir(ROOT)
os.environ["SCI_NAMES_TABLE"] = "names_table/names_table_d8811a9.json.gz"
import authority_search as AS, sci_search_service as ss
sides = ["review_data/side_index_d8811a9/" + d for d in sorted(os.listdir("review_data/side_index_d8811a9"))]
svc = ss.SearchService.load("/home/user/audit_idx/new", sides, client=object())
tab = AS.AuthorityTable.load("authority_table/authority_d8811a9.json.gz", svc.info.get("index_commit"))
LEADS = {42037: ("Gunmala Sales", ['"Gunmala"']), 27193: ("S.M.S. Pharmaceuticals 2005", ['"Neeta Bhalla"']), 28670: ("S.M.S. Pharmaceuticals 2007", ['"Neeta Bhalla"']), 31456: ("Aneeta Hada 2008", ['"Aneeta Hada"']),
         39265: ("Aneeta Hada 2012", ['"Aneeta Hada"']), 34971: ("K.K. Ahuja", ['"K.K. Ahuja"', '"Ahuja" AND "Vora"']), 1000254163: ("Sunita Palita", ['"Sunita Palita"']), 41801: ("Dashrath Rupsingh Rathod", ['"Dashrath Rupsingh"'])}
out = {}
for d, (name, qs) in LEADS.items():
    docs = set()
    for q in qs:
        for (rid,) in svc.fts.execute("select rowid from f where f match ?", (q,)):
            docs.add(svc.metas[rid]["doc"])
    cl = tab.cluster_of(d)
    own = set(tab.docs_of(cl)) | {d}
    named = len(docs - own)
    out[name] = {"judgments_whose_text_has_the_name": named, "authority_table_cited_by": tab.cited_by.get(cl), "cluster_records": len(tab.docs_of(cl))}
    print(f"{name:30} text mentions in {named:5} other judgments | authority table counts: {tab.cited_by.get(cl)}")
json.dump(out, open(os.path.join(HERE, "mentions.json"), "w"), indent=1)
