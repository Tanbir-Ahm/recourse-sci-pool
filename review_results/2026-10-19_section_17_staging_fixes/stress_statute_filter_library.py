"""Stress test of the wider-search statute filter on the library's own judgment chunks (1,045): for fifteen (Act, section) pairs, every chunk that cites that section number is run through sci_search_tier._off_statute with the Act shelf's context for that section. Prints the decisions for eyeballing."""
import glob, json, os, re, sys
sys.path.insert(0, "/home/user/recourse"); os.chdir("/home/user/recourse")
os.environ["ACT_SHELF"] = "on"; os.environ.setdefault("ANTHROPIC_API_KEY", "dummy"); os.environ.setdefault("VOYAGE_API_KEY", "dummy")
import numpy as np
import act_shelf as S
import sci_search_tier as T
chunks = []
for f in sorted(glob.glob("chunks/*.json")):
    if "sanhita" in f:
        continue
    d = json.load(open(f, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("chunks") or d.get("items") or []
    for c in items:
        t = c.get("text") if isinstance(c, dict) else None
        if t:
            chunks.append((os.path.basename(f)[:38], t))
cases = [("pc_act_1988", "7"), ("pc_act_1988", "13"), ("pc_act_1988", "17"), ("pc_act_1988", "19"), ("pmla_2002", "45"), ("pmla_2002", "19"), ("pocso_act_2012", "29"), ("uapa_1967", "43D"), ("sc_st_act_1989", "18"),
         ("pocso_act_2012", "19"), ("dowry_prohibition_act_1961", "3"), ("pmla_2002", "3"), ("pmla_2002", "17"), ("uapa_1967", "13"), ("jj_act_2015", "15")]
print(f"{len(chunks)} judgment chunks in the library")
tot = drop = 0
rows = []
for aid, n in cases:
    ms = S.search(f"What does section {n} say?", [{"id": aid}], embed_fn=lambda t: np.zeros(1024), current_message=f"What does section {n} of the {S._state(aid)['name']} say?")["matches"]
    ctx = T.make_statute_context(S.statute_context(ms))
    if not ctx:
        print("no context for", aid, n)
        continue
    for fn, t in chunks:
        if not re.search(rf"\b[Ss]ections?\s+{n}\b(?![A-Za-z0-9])", t):
            continue
        why = T._off_statute(t, ctx)
        m = re.search(rf"[Ss]ections?\s+{n}\b", t)
        rows.append((aid, n, fn, bool(why), why or "", re.sub(r"\s+", " ", t[max(0, m.start() - 70): m.start() + 120])))
        tot += 1
        drop += bool(why)
print(f"{tot} (chunk, section) pairs cite the number; {drop} would be left out")
for r in rows:
    print(("DROP " if r[3] else "keep "), f"{r[0][:12]:12} s.{r[1]:4}", r[2][:30], "|", r[5][:170], "|", r[4][:60])
