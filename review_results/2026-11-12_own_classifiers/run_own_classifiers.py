"""Runner for questions.json (frozen in commit 98f7ff1 before this file was written). Baseline = offence_class.OWN_CLASSIFIERS emptied (the behaviour of Recourse 6116d84); after = the registry on.
Needs the Recourse checkout on sys.path and VOYAGE_API_KEY (search by meaning). Writes results.json."""
import os, sys, json, io, contextlib
os.environ.update({"ACT_SHELF": "on", "ACT_DETECT": "wide", "SHELF_COMPANIONS": "on", "OTHER_LAW_CLASS": "on"})
sys.path.insert(0, "/home/user/recourse")
import chat_assistant as CA, offence_class as O
REG = dict(O.OWN_CLASSIFIERS)
Q = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "questions.json")))["questions"]

def run(q, registry):
    O.OWN_CLASSIFIERS.clear(); O.OWN_CLASSIFIERS.update(registry)
    with contextlib.redirect_stdout(io.StringIO()):
        ms = CA._act_shelf_matches(q, q)
        blk = O.other_law_block(ms)
    secs = sorted({(m.get("act_key"), str(m.get("section_number"))) for m in ms})
    return ms, secs, blk

out = []
for item in Q:
    act = item["act"]
    r = {"id": item["id"], "act": act, "bailish": bool(item.get("bailish")), "control": bool(item.get("control"))}
    for tag, reg in (("before", {}), ("after", REG)):
        ms, secs, blk = run(item["q"], reg)
        mine = [s for k, s in secs if k == act]
        gov = REG.get(act, [])
        default_lines = [l for l in blk.split("\n") if l.startswith("- ") and ("Part II row:" in l) and (l.split(" section ")[0].lower().startswith(act.split("_")[0][:4]) or True)]
        # a Part II default line naming a section of THIS act
        names = {m.get("act_display") for m in ms if m.get("act_key") == act}
        dl = [l for l in default_lines if any(n and l.startswith("- " + n) for n in names)]
        r[tag] = {"act_found": bool(mine), "sections": mine, "classifier_in_material": all(g in mine for g in gov) if gov else None,
                  "part2_default_lines_for_act": len(dl), "block": blk, "all_sections": [f"{k}:{s}" for k, s in secs]}
    out.append(r)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json"), "w"), indent=1)
own = [r for r in out if not r["control"]]
ctl = [r for r in out if r["control"]]
def n(rs, tag, f): return sum(1 for r in rs if f(r[tag]))
print("own-classifier Acts:", len(own), "questions")
print(" Act found (before/after):", n(own, "before", lambda t: t["act_found"]), n(own, "after", lambda t: t["act_found"]))
print(" classifier section in material (before/after):", n(own, "before", lambda t: t["classifier_in_material"]), n(own, "after", lambda t: t["classifier_in_material"]))
print(" a Part II default offered for the Act (before/after):", n(own, "before", lambda t: t["part2_default_lines_for_act"] > 0), n(own, "after", lambda t: t["part2_default_lines_for_act"] > 0))
print(" among bail-words questions: classifier in material (before/after):", n([r for r in own if r["bailish"]], "before", lambda t: t["classifier_in_material"]), n([r for r in own if r["bailish"]], "after", lambda t: t["classifier_in_material"]), "of", len([r for r in own if r["bailish"]]))
print("controls:", len(ctl), "unchanged (sections and block identical before/after):", sum(1 for r in ctl if r["before"]["all_sections"] == r["after"]["all_sections"] and r["before"]["block"] == r["after"]["block"]))
for r in out:
    b, a = r["before"], r["after"]
    print(f"{r['id']:4} act_found={a['act_found']!s:5} classifier={a['classifier_in_material']!s:5} default_before={b['part2_default_lines_for_act']} default_after={a['part2_default_lines_for_act']} sections_after={a['sections']}")
