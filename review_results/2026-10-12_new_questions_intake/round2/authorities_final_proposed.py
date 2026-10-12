"""Writes authorities_final_proposed.json: the authorities table (the one fix_test_set.py reads) for the round-2 file, with N12 dropped (owner, 2026-10-12).
= the round-1 table without the rows of N02, N12 and N15, plus the round-2 rows of N02 and N15 (N12's are not carried), plus the changes the writer made to other key rows:
  N19  Rishipal Singh Solanki is now listed as a primary authority next to Yuvaprakash;   N20  Mahmood Farooqui is listed as an acceptable authority (not in the index).
The writer's lists are carried as written. Where Claude found a problem in the indexed text the entry gets a 'note' (ignored by the sealing code); nothing is removed or re-ranked here: Mr. Advocate decides,
and the FINAL table is made from this one after his review. Private."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); INTAKE = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, INTAKE); sys.path.insert(0, HERE)
from authorities import A
from adjudication import ADJ, STALE
from authorities_round2 import A2_NEW, ADJ2, REPLACED
DROPPED = {"N12"}
NOTES = {
    ("N02", "D.K. Basu v. State of West Bengal (1996/97)"): "Mentions the 24-hour rule only as a recital of Article 22(2) and s.57 CrPC; Arnesh Kumar (doc 41736) states the rule in its own reasoning. Mr. Advocate: which is the primary?",
    ("N02", "Joginder Kumar v. State of U.P. (1994)"): "Not in the index; the opening-text hit 1000256233 is a different judgment quoting a High Court order that cites it.",
    ("N15", "Rajnesh v. Neha (2020)"): "The key gives the SCC cite (2020) 15 SCC 17; later judgments in the index cite (2021) 2 SCC 324 (e.g. doc 1000255376). Decided 4 Nov 2020.",
    ("N15", "Shyamlal Devda v. Parimala (2020)"): "The indexed judgment is about territorial jurisdiction under s.27 DV Act; it does not mention interim maintenance or social justice (the key says it does). Its SCC cite (2020) 3 SCC 14 is not repeated in any other indexed judgment. Mr. Advocate: keep or remove?",
    ("N20", "Mahmood Farooqui v. State (Govt. of NCT of Delhi) (2017)"): "Not in the index. The cite (2017) 6 SCC 631 given in the key is the cite of Vasanta Sampat Dupare v. State of Maharashtra in later judgments; Claude believes the Farooqui judgment is a Delhi High Court decision. Mr. Advocate to check.",
    ("N19", "P. Yuvaprakash v. State (2023)"): "About the age of a victim, not of an accused (round 1); the writer now lists it as primary together with Rishipal Singh Solanki.",
}
out = []
def entry(q, role, label, st, ds):
    e = {"qid": q, "role": role, "label": label, "status": st, "docs": ds}
    if role in ("trap_old", "note"):
        hit = next((s for s in STALE.get(q, []) if s[0] == label), None)
        counts = bool(hit[2]) if hit else False
        e["stale"] = {"kind": hit[1] if hit else "narrower or contested", "counts_as_stale": counts and st == "IN"}
    if (q, label) in NOTES:
        e["note"] = NOTES[(q, label)]
    return e
for q, role, label, toks, year, slack in A:
    if q in REPLACED or q in DROPPED:
        continue
    if q == "N19" and label.startswith("Rishipal Singh Solanki"):
        role = "primary"                                        # the writer's round-2 key lists both as primary
    st, ds = ADJ[label]
    out.append(entry(q, role, label, st, ds))
for q, role, label, toks, year, slack in A2_NEW:
    if q in DROPPED:
        continue
    st, ds = ADJ2[label]
    out.append(entry(q, role, label, st, ds))
order = {f"N{i:02d}": i for i in range(1, 31)}; order.update({"NR1": 31, "NR2": 32, "NR3": 33})
out.sort(key=lambda e: (order[e["qid"]], {"primary": 0, "acceptable": 1, "trap_old": 2, "note": 3}[e["role"]]))
path = os.path.join(HERE, "authorities_final_proposed.json")
json.dump(out, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(out), "entries;", sum(1 for e in out if e.get("stale", {}).get("counts_as_stale")), "count as stale;", sum(1 for e in out if "note" in e), "carry a note;", "questions:", len({e['qid'] for e in out}))
