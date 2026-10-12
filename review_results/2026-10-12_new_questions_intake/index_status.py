"""Per question: are the named key authorities in the index? (uses authorities.py and adjudication.py; no index loading). Writes index_status.json. Private."""
import collections, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from authorities import A
from adjudication import ADJ, STALE
per = collections.defaultdict(lambda: {"primary": None, "acceptable": [], "trap_old": [], "note": []})
for q, role, label, toks, year, slack in A:
    st, ds = ADJ[label]
    item = {"label": label, "status": st, "docs": ds}
    if role == "primary":
        per[q]["primary"] = item
    else:
        per[q][role].append(item)
out = {}
prim_gap, no_key = [], []
for q in sorted(per):
    p, acc, tr = per[q]["primary"], per[q]["acceptable"], per[q]["trap_old"]
    acc_in = sum(1 for a in acc if a["status"] == "IN")
    keyin = (1 if p and p["status"] == "IN" else 0) + acc_in
    out[q] = {"primary_in_index": bool(p and p["status"] == "IN"), "primary_status": p["status"] if p else None, "acceptable_in": acc_in, "acceptable_total": len(acc), "key_reachable": bool(keyin),
              "older_rulings_in_index": sum(1 for t in tr if t["status"] == "IN"), "older_rulings_total": len(tr), "detail": per[q]}
    if p and p["status"] != "IN":
        prim_gap.append(q)
    if not keyin and p:
        no_key.append(q)
    print(f"{q:4} primary {p['status'] if p else '-':8} acceptable {acc_in}/{len(acc)}  older rulings in index {out[q]['older_rulings_in_index']}/{len(tr)}  key authority reachable: {'yes' if keyin else 'NO'}")
json.dump(out, open(os.path.join(HERE, "index_status.json"), "w", encoding="utf-8"), indent=1)
scored = [f"N{i:02d}" for i in range(1, 28)]
print("\nprimary authority outside the index (scored questions):", [q for q in prim_gap if q in scored], "| reserves:", [q for q in prim_gap if q not in scored])
print("no key authority in the index at all (scored):", [q for q in no_key if q in scored])
meas = [q for q, rows in STALE.items() if q in scored and any(r[2] and "NOT IN THE INDEX" not in r[1] for r in rows) and out[q]["older_rulings_in_index"] > 0]
print("currency traps whose older ruling is in the index (measurable):", meas)
