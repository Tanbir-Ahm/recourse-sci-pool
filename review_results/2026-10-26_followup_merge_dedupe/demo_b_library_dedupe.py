"""(b) on real data: a question for which the reviewed library and the wider search both hold Pankaj Bansal v. Union of India (2023). Real library retrieval (Voyage, a fraction of a cent) and the REAL wider search
(newer index d8811a9, Voyage embed + rerank); then Recourse's feed_block without and with the library's judgments excluded, and attach() on an answer that names the case. No answer model.
Run: python3 demo_b_library_dedupe.py REPO INDEX_DIR RECOURSE_DIR"""
import contextlib, glob, io, json, os, sys, time
repo, idx, rec = sys.argv[1:4]
sys.path.insert(0, repo); sys.path.insert(0, rec); os.chdir(repo)
os.environ["SCI_INDEX_COMMIT"] = "d8811a910c73b0159bea7bcf3183ea258120db5b"
os.environ["SCI_NAMES_TABLE"] = os.path.join(repo, "names_table/names_table_d8811a9.json.gz")
import sci_search_service as S
svc = S.SearchService.load(idx, side_dirs=sorted(glob.glob(os.path.join(repo, "review_data/side_index_d8811a9/*/"))))
Q = "Must the police give the grounds of arrest in writing to a person arrested under the money laundering law?"
found = svc.search(Q, k=10)
os.chdir(rec)
from semantic_retrieval import find_relevant_sections
with contextlib.redirect_stdout(io.StringIO()):
    lib = find_relevant_sections(Q)
lib_matches = (lib.get("matches") or []) + (lib.get("judgment_matches") or [])
print("library state:", lib.get("state"), "| library judgments:", sorted({m.get("case_name") for m in lib.get("judgment_matches") or []}))
print("wider search cases:", [r["case_name"] for r in found["results"]][:10])
import sci_search_tier as T
os.environ["SCI_SEARCH_MODE"] = "feed"; os.environ["SCI_SEARCH_URL"] = "http://127.0.0.1:9"
T.search = lambda *a, **k: found
def feed(exclude):
    T.reset()
    with contextlib.redirect_stdout(io.StringIO()):
        b = T.feed_block(Q, exclude_names=exclude) if exclude is not None else T.feed_block(Q)
    return b, [c["case_name"] for c in T._LOCAL.cases]
b0, c0 = feed(None)
b1, c1 = feed(T.library_keys(lib_matches))
print("\nfed to the model WITHOUT the exclusion:", c0)
print("fed to the model WITH the exclusion   :", c1)
print("left out:", [c for c in c0 if c not in c1])
ans = "Pankaj Bansal v. Union of India (2023) held that the grounds of arrest must be furnished in writing. " + " ".join(f"{c} is also relevant." for c in c1[:1])
T.reset()
with contextlib.redirect_stdout(io.StringIO()):
    T.feed_block(Q)                                         # the prompt WITHOUT the exclusion (the worst case: the library match arrived later)
    r = T.attach(Q, {"state": "single_match", "response_text": ans, "matches": lib_matches})
print("\nattach() with the library matches known: wider-search list on the page:", [c["case_name"] for c in r.get("sci_related_judgments") or []])
print("labelled 'wider search' in the answer text:", r["response_text"].count(T.LABEL), "time(s)")
print("ANSWER TEXT AFTER attach():", r["response_text"])
