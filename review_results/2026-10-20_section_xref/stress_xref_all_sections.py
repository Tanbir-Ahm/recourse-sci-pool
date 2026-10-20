"""
stress_xref_all_sections.py -- SECTION_XREF stress test: for EVERY section of the Act shelf (the nine Acts), ask "What does section N of the <Act> say?" through act_shelf.search with the section's own stored
vector as the question vector (no network, no model, no cost), with SECTION_XREF=on, and check the invariants:
  * every 'cited' match is a real, non-omitted section of the same Act, whose text is word for word the shelf's text, and carries cited_by = the asked section;
  * at most MAX_CITED cited matches; no section appears twice; the asked section's own match lists the cited numbers it cites;
  * a section that cites more than MAX_FANOUT others adds nothing.
Prints a table of how often a cited section was added.   Run from a Recourse checkout:  python -X utf8 stress_xref_all_sections.py <checkout>
"""
import json, os, sys, collections
RECOURSE = sys.argv[1] if len(sys.argv) > 1 else "."
sys.path.insert(0, RECOURSE); os.chdir(RECOURSE)
os.environ["ACT_SHELF"] = "on"; os.environ["SECTION_XREF"] = "on"
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
import numpy as np
import act_shelf as S
SH = S.load()["acts"]
EMB = json.load(open(os.path.join(S.SHELF_DIR, "shelf_embeddings.json"), encoding="utf-8"))
VEC = {r["chunk_id"]: np.array(r["embedding"], dtype=float) for r in EMB["records"]}
bad, rows = [], collections.Counter()
per_act = collections.defaultdict(lambda: [0, 0, 0])      # sections, with cited added, fan-out
for aid, st in SH.items():
    if not st.get("ok") or st.get("whole"):
        continue
    name = st["display"]
    for n, c in st["by_num"].items():
        if c.get("omitted"):
            continue
        q = f"What does section {n} of the {name} say?"
        vec = VEC.get(f"act:{c['act']}:{n}")
        if vec is None:
            continue
        r = S.search(q, [{"id": aid}], embed_fn=lambda t, v=vec: v)
        ms = r["matches"]
        nums = [m["section_number"] for m in ms]
        cited = [m for m in ms if m["retrieval"] == "cited"]
        cites, info = S.cited_sections(st, n)
        per_act[aid][0] += 1
        per_act[aid][1] += bool(cited)
        per_act[aid][2] += bool(info.get("fanout"))
        problems = []
        if "named" not in [m["retrieval"] for m in ms if m["section_number"] == n]:
            problems.append("asked section not named")
        if len(cited) > S.MAX_CITED: problems.append("too many cited")
        if len(nums) != len(set(nums)): problems.append("duplicate section")
        for m in cited:
            real = st["by_num"].get(m["section_number"])
            if not real or real.get("omitted") or m["text"] != real["text"] or m.get("cited_by") != n or m["section_number"] not in cites:
                problems.append(f"bad cited {m['section_number']}")
        holder = [m for m in ms if m["section_number"] == n and m["retrieval"] == "named"]
        if cited and holder and not set(m["section_number"] for m in cited) <= set(holder[0].get("cites") or []):
            problems.append("holder does not list cites")
        if info.get("fanout") and cited:
            problems.append("fan-out section added something")
        if problems:
            bad.append((aid, n, problems))
print(f"{'Act':<28}{'sections':>9}{'cited added':>13}{'fan-out':>9}")
for aid, (a, b, c) in per_act.items():
    print(f"{aid:<28}{a:>9}{b:>13}{c:>9}")
print("total", sum(v[0] for v in per_act.values()), "| violations:", len(bad), bad[:5])
sys.exit(1 if bad else 0)
