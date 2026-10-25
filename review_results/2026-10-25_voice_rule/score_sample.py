"""Scores authority.py against the hand labels, by the rules of PLAN_AND_RULES.md. No network, no cost.
Usage: python3 -I score_sample.py MY_LABELS.json RULE_VERDICTS.json [SAMPLE.json]"""
import collections, json, sys

labels = json.load(open(sys.argv[1], encoding="utf-8"))
verdicts = {str(r["id"]): r for r in json.load(open(sys.argv[2], encoding="utf-8"))}
text = {str(r["id"]): r for r in json.load(open(sys.argv[3], encoding="utf-8"))} if len(sys.argv) > 3 else {}
TIER = {1: "SC", 2: "HC", 3: "trial", None: "none"}

rows = []
for i, (mine_block, mine_tier) in labels.items():
    v = verdicts[i]["rule"]
    rows.append({"id": int(i), "from": verdicts[i]["from"], "mine_block": mine_block == "yes", "mine_tier": mine_tier,
                 "rule_block": bool(v["blocked"]), "rule_tier": TIER[v["tier"]], "states_law": v.get("states_law"), "reason": v.get("reason")})

tp = [r for r in rows if r["rule_block"] and r["mine_block"]]
fp = [r for r in rows if r["rule_block"] and not r["mine_block"]]
fn = [r for r in rows if not r["rule_block"] and r["mine_block"]]
prec = len(tp) / max(len(tp) + len(fp), 1)
rec = len(tp) / max(len(tp) + len(fn), 1)
print(f"BLOCK  rule blocks {len(tp) + len(fp)} of {len(rows)}; I blocked {len(tp) + len(fn)}")
print(f"  V1 precision {100 * prec:.0f}% ({len(tp)}/{len(tp) + len(fp)}) - needs 90%  -> {'PASS' if prec >= 0.90 else 'FAIL'}")
print(f"  V2 recall    {100 * rec:.0f}% ({len(tp)}/{len(tp) + len(fn)}) - needs 70%  -> {'PASS' if rec >= 0.70 else 'FAIL'}")
print("  wrongly blocked:", [r["id"] for r in fp])
print("  missed:", [r["id"] for r in fn])

# V3 is scored on the passages where I named a court, and separately on every passage
named = [r for r in rows if r["mine_tier"] != "none" and not r["rule_block"]]
agree = [r for r in named if r["rule_tier"] == r["mine_tier"]]
all_tier = [r for r in rows if not r["rule_block"] and not r["mine_block"]]
agree_all = [r for r in all_tier if r["rule_tier"] == r["mine_tier"] or (r["mine_tier"] == "none" and r["states_law"] is False)]
promoted = [r for r in rows if r["mine_tier"] == "trial" and not r["rule_block"] and r["rule_tier"] in ("SC", "HC")]
print(f"\nTIER   V3 agreement where I named a court: {100 * len(agree) / max(len(named), 1):.0f}% ({len(agree)}/{len(named)}) - needs 85% -> {'PASS' if len(agree) / max(len(named), 1) >= 0.85 else 'FAIL'}")
print(f"  a passage I called a trial court's given tier 1 or 2: {len(promoted)} {[r['id'] for r in promoted]} - needs 0 -> {'PASS' if not promoted else 'FAIL'}")
print(f"  (for information) counting 'no law, and the rule agrees there is none' as agreement: {100 * len(agree_all) / max(len(all_tier), 1):.0f}% ({len(agree_all)}/{len(all_tier)})")
print("  disagreements where I named a court:")
for r in named:
    if r["rule_tier"] != r["mine_tier"]:
        print(f"    {r['id']:>4}: mine {r['mine_tier']:<6} rule {r['rule_tier']:<6} states_law={r['states_law']}  {(text.get(str(r['id']), {}).get('text') or '')[:95]}")
print("\nconfusion (mine -> rule), blocked excluded:")
for k, n in sorted(collections.Counter((r["mine_tier"], r["rule_tier"]) for r in all_tier).items(), key=lambda x: str(x[0])):
    print("   ", k, n)
print("\nby where the passage came from:")
for src in ("random", "blocked pool"):
    g = [r for r in rows if r["from"] == src]
    print(f"   {src}: {len(g)} passages; I blocked {sum(r['mine_block'] for r in g)}; the rule blocked {sum(r['rule_block'] for r in g)}")
json.dump(rows, open("sample_scored.json", "w"), indent=1)
