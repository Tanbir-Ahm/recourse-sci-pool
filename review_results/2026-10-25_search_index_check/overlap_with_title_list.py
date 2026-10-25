"""Scratch: second, looser pass over the full-text index's judgments that the strict date+name match did not find in the title index."""
import gzip, json, re, sqlite3, collections, datetime
STOP = {"v", "vs", "versus", "the", "of", "and", "anr", "ors", "another", "others", "in", "re", "etc", "ltd", "co", "pvt", "p", "m", "s", "state", "union", "india"}
def toks(s): return frozenset(t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if t not in STOP and len(t) > 1)
c = sqlite3.connect("file:/home/user/recourse/case_lookup_index.db?mode=ro", uri=True)
rows = c.execute("select case_id, title, petitioner, respondent, decision_date from cases").fetchall()
by_date = collections.defaultdict(list); by_year = collections.defaultdict(list)
for cid, title, pet, resp, date in rows:
    t = toks((pet or "") + " " + (resp or "")) or toks(title)
    by_date[date].append((cid, t)); by_year[date[:4]].append((cid, t))
nd = json.load(gzip.open("/home/user/recourse-sci-pool/names_table/names_table.json.gz", "rt", encoding="utf-8"))["rows"]
def jac(a, b): return len(a & b) / len(a | b) if a and b else 0.0
def near_dates(d):
    base = datetime.date.fromisoformat(d)
    for k in range(-3, 4):
        yield (base + datetime.timedelta(days=k)).isoformat()
strict = loose = still = undated_found = undated_not = y2026 = 0
still_ex = []
for r in nd:
    d = r.get("date"); t = toks((r.get("petitioner") or "") + " " + (r.get("respondent") or ""))
    if not d:
        best = max((jac(t, tt) for lst in by_year.values() for _, tt in lst), default=0) if t else 0
        if best >= 0.8: undated_found += 1
        else: undated_not += 1
        continue
    if d.startswith("2026"): y2026 += 1; continue
    best = max((jac(t, tt) for cid, tt in by_date.get(d, [])), default=0)
    if best >= 0.5: strict += 1; continue
    best2 = max((jac(t, tt) for dd in near_dates(d) for cid, tt in by_date.get(dd, [])), default=0)
    if best2 >= 0.4: loose += 1; continue
    best3 = max((jac(t, tt) for cid, tt in by_year.get(d[:4], [])), default=0)
    if best3 >= 0.7: loose += 1; continue
    still += 1
    if len(still_ex) < 8: still_ex.append((d, r["name"]))
print("strict match (same date, names alike):", strict)
print("loose match (date within 3 days, or same year with very alike names):", loose)
print("dated before 2026, still not found:", still, still_ex)
print("2026 (title list has none):", y2026)
print("undated: found by name alone (>=0.8):", undated_found, "| not found:", undated_not)
print("total", strict + loose + still + y2026 + undated_found + undated_not)
