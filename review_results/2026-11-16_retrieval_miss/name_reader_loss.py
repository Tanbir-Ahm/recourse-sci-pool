"""How much of the authority table's blindness is the name reader? On every passage of the newer index: count 'X v. Y' mentions the reader returns, and how many occurrences of ' v. ' sit right after a dotted abbreviation
(Ltd. Pvt. Co. Corp.) where the reader returns nothing. Free (no model call)."""
import os, re, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, ROOT); os.chdir(ROOT)
os.environ["SCI_NAMES_TABLE"] = "names_table/names_table_d8811a9.json.gz"
import authority_graph as G, sci_search_service as ss
sides = ["review_data/side_index_d8811a9/" + d for d in sorted(os.listdir("review_data/side_index_d8811a9"))]
svc = ss.SearchService.load("/home/user/audit_idx/new", sides, client=object())
DOT = re.compile(r"\b(?:Ltd|Pvt|Co|Corp|Inc|Bros|Mfg|Assn|Govt|Dept)\.\s+(?:v|vs|versus)\.?\s", re.I)
VS = re.compile(r"\s(?:v|vs)\.\s")
tot_vs = dot_vs = read_all = read_dot = 0
for rid in range(len(svc.metas)):
    t = svc._text(rid)
    if " v" not in t:
        continue
    n_vs = len(VS.findall(t))
    if not n_vs:
        continue
    n_dot = len(DOT.findall(t))
    got = len(G.mentions(t))
    tot_vs += n_vs; dot_vs += n_dot; read_all += got
    if n_dot:
        # mentions the reader returned in passages that have a dotted-abbreviation v. : an upper bound of what it reads after them
        read_dot += got
print(json.dumps({"passages": len(svc.metas), "v_occurrences": tot_vs, "after_dotted_abbreviation": dot_vs, "share_after_dotted_abbreviation": round(dot_vs / max(tot_vs, 1), 4), "mentions_read": read_all, "mention_per_v": round(read_all / max(tot_vs, 1), 3)}, indent=1))
t = "in S.M.S. Pharmaceuticals Ltd. v. Neeta Bhalla and Another [(2005) 8 SCC 89]"
t2 = "in S.M.S. Pharmaceuticals Ltd v. Neeta Bhalla and Another [(2005) 8 SCC 89]"
print("reader on the dotted form:", G.mentions(t), "| same sentence with 'Ltd' (no dot):", G.mentions(t2))
