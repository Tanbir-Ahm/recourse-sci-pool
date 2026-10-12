"""Trigger check (rules section 11.2, item 4): do the Machine Spec v2 anchors (N1 precise, N2 broad) fire on the Act the writer tagged? Measured on the question texts only; nothing is searched.
The spec is the one frozen with the fix-test rules (hashes in review_data/ruler/fix_test_rules_v2.freeze); nothing here changes it. Private."""
import json, os, sys
import openpyxl
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools"))
import machine_spec_v2 as S
AMAP = {"PWDVA": "PWDVA", "NDPS Act": "NDPS", "POCSO Act": "POCSO", "SC/ST Act": "SC/ST", "NI Act": "NI Act", "PMLA": "PMLA", "UAPA": "UAPA", "Dowry Prohibition Act": "DPA", "JJ Act": "JJ Act", "PC Act": "PC Act", "Arms Act": "Arms Act", "IT Act": "IT Act", "MV Act": "MV Act"}
wb = openpyxl.load_workbook(os.path.join(ROOT, "review_data/ruler/inputs/2026-10-12_Fix_Test_New_Questions_N01-N30_as_received.xlsx"))
rows = list(wb["Questions"].iter_rows(values_only=True)); hdr = rows[0]
out, tot = [], {"tagged_scored": 0, "n1_hit": 0, "n2_hit": 0, "n1_exact": 0, "n2_exact": 0, "misfire_n1": [], "misfire_n2": [], "fires_n1": [], "fires_n2": [], "missed_both": []}
for r in rows[1:]:
    d = dict(zip(hdr, r)); qid = d["Id"]
    tag = (d['Act(s) concerned (from the 13, or "none")'] or "").strip()
    tags = set() if tag.lower() == "none" else {AMAP[x.strip()] for x in tag.replace(" + ", ";").split(";")}
    n1, n2 = set(S.question_acts(d["Question text"], "N1")), set(S.question_acts(d["Question text"], "N2"))
    out.append({"id": qid, "tags": sorted(tags), "n1": sorted(n1), "n2": sorted(n2)})
    scored = qid.startswith("N") and not qid.startswith("NR") and d["Domain (A to K)"] != "K"
    if not scored:
        continue
    if tags:
        tot["tagged_scored"] += 1
        tot["n1_hit"] += bool(tags & n1); tot["n2_hit"] += bool(tags & n2)
        if not (tags & n2):
            tot["missed_both"].append(qid)
    if n1:
        tot["fires_n1"].append(qid)
    if n2:
        tot["fires_n2"].append(qid)
    if n1 - tags:
        tot["misfire_n1"].append((qid, sorted(n1 - tags)))
    if n2 - tags:
        tot["misfire_n2"].append((qid, sorted(n2 - tags)))
json.dump({"per_question": out, "totals": tot}, open(os.path.join(HERE, "trigger_check.json"), "w"), indent=1)
print(f"tagged scored questions: {tot['tagged_scored']}; the tagged Act fires under N1 on {tot['n1_hit']}, under N2 on {tot['n2_hit']}")
print("fires at all (scored):  N1", len(tot["fires_n1"]), tot["fires_n1"], "\n                        N2", len(tot["fires_n2"]), tot["fires_n2"])
print("fires for an Act the writer did not tag (misfire): N1", tot["misfire_n1"], "N2", tot["misfire_n2"])
print("tagged but neither N1 nor N2 fires:", tot["missed_both"])
print("N1 and N2 differ only on:", sorted(set(tot["fires_n2"]) - set(tot["fires_n1"])))
