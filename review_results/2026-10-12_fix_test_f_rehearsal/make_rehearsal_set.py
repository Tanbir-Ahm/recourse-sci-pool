"""Builds a REHEARSAL question set and key in the format of fix_test_set.py from the 30 questions that are already used up (review_data/ruler/real30_v1.json and its key), so that the whole stage F path
(search, pack, scorer, reading sheet) can be exercised on real passages without touching the new questions. Same domain plan (A3 B3 C3 D2 E3 F3 G3 H3 I2 J2 K3), ids N01 to N30 in domain order. Look-alike and soft-overlap
flags are INVENTED here (look-alike on every second question) only to exercise the code. NOT a result about anything. Writes rehearsal_set.json and rehearsal_key.json next to this script."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools"))
import fix_test_set as FT
real = json.load(open(os.path.join(ROOT, "review_data/ruler/real30_v1.json"), encoding="utf-8"))
key = json.load(open(os.path.join(ROOT, "review_data/ruler/real30_key_v1.json"), encoding="utf-8"))["questions"]
order = sorted(real["questions"], key=lambda q: (q["domain"], q["id"]))
numb = {"none": "none", "IPC/CrPC": "IPC/CrPC", "BNS/BNSS": "BNS/BNSS"}
qs, kq = [], {}
for i, q in enumerate(order, 1):
    nid = f"N{i:02d}"
    qs.append({"id": nid, "domain": q["domain"], "kind": q["kind"], "numbering": numb[q["numbering"]], "text": q["text"], "trap": bool(q["trap"]), "best_law_era": q["best_law_era"] if q["best_law_era"] in ("2017 or later", "before 2017") else "2017 or later",
               "language": q["language"], "control_type": ("K1" if q["domain"] == "K" and q["control_type"] == "civil/tax/divorce" else "K2" if q["domain"] == "K" and q["control_type"] == "High Court only or 2026" else "K3" if q["domain"] == "K" else None),
               "acts": [], "acts_named": False, "look_alike": i % 2 == 0 and q["domain"] != "K", "twin_of": None, "soft_overlap": i in (4, 6, 7, 13)})
    k = key[q["id"]]
    kq[nid] = {"id": nid, "key_docs": k["key_docs"], "primary_key_docs": k.get("primary_key_docs", []), "stale_docs": k["stale_docs"], "reachable": k["reachable"], "authorities": [], "expected_answer": "(rehearsal)", "soft_overlap": i in (4, 6, 7, 13)}
public = {"schema": FT.SCHEMA, "built": "2026-10-12", "questions": qs, "index_snapshot": real["index_snapshot"], "provenance": {"rehearsal": True, "writer_text_sha256": None, "writer_hash_matches": False, "unused_reserves": []}}
keyd = {"schema": FT.SCHEMA + "-key", "built": "2026-10-12", "questions": kq}
public["freeze"] = {"sha256": FT.freeze_digest(public), "key_sha256": FT.key_digest(keyd), "questions": [q["id"] for q in qs], "note": "REHEARSAL on used questions"}
json.dump(public, open(os.path.join(HERE, "rehearsal_set.json"), "w", encoding="utf-8"), indent=1, sort_keys=True)
json.dump(keyd, open(os.path.join(HERE, "rehearsal_key.json"), "w", encoding="utf-8"), indent=1, sort_keys=True)
print("problems:", FT.check(public, keyd) or "none", "| domains", sorted({q["domain"] for q in qs}), "| look-alikes", sum(q["look_alike"] for q in qs))
