"""Shows what the stage F search returned, WITHOUT opening the answer key (the key is opened only in stage 2 of the scoring, after the marks).
Reads pool.json (questions, the ordered top 10 of B and of each finalist, the pooled passages) and writes SEARCH_RESULTS.md: the run facts, which questions the finalists changed, and for those questions the top 5 of B, N1-125 and N2-125 side by side.
Run: python3 -P review_results/2026-10-12_fix_test_f/show_search_results.py [POOL.json]"""
import json, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
POOL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "pool.json")
OUT = os.path.join(os.path.dirname(os.path.abspath(POOL)), "SEARCH_RESULTS.md")
P = json.load(open(POOL, encoding="utf-8"))
run = P["run"]


def pick(names, prefix):
    hit = [n for n in names if n.startswith(prefix)]
    return hit[0] if hit else None


def short(t, n=70):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def year(title):
    m = re.search(r"\((\d{2})[-/](\d{2})[-/]((?:19|20)\d\d)\)", title or "")
    return m[3] if m else ""


def case_name(title):
    t = re.sub(r"\s*\(\d{2}[-/]\d{2}[-/]\d{4}\)\s*$", "", title or "").strip()
    return short(t, 64)


qs = P["questions"]
names = list(qs[0]["lists"])
B, N1, N2 = pick(names, "B "), pick(names, "N1-125"), pick(names, "N2-125")
rows_by = [{r["h"]: r for r in q["rows"]} for q in qs]
fix = run.get("fix_test") or {}
sp = run.get("spend") or {}
lines = ["# Stage F search results (the key is closed; no marks yet)", "",
         f"Run: {run.get('when')}; index {str(run.get('index_commit'))[:10]}; label: {fix.get('label') or run.get('label')}; versions: B, {N1}, {N2}.",
         f"Spend: {json.dumps(sp)}", ""]
summary = []
for qi, q in enumerate(qs):
    L = {v: [e["h"] for e in q["lists"][v]] for v in (B, N1, N2)}
    top5 = {v: L[v][:5] for v in L}
    docs5 = {v: [e["doc"] for e in q["lists"][v][:5]] for v in L}
    fired = q.get("acts_fired") or {}
    f1, f2 = (fired.get("N1") or fired.get(N1) or []), (fired.get("N2") or fired.get(N2) or [])
    d1 = "same" if top5[N1] == top5[B] else ("same passages, new order" if set(top5[N1]) == set(top5[B]) else f"{len(set(top5[N1]) - set(top5[B]))} new")
    d2 = "same" if top5[N2] == top5[B] else ("same passages, new order" if set(top5[N2]) == set(top5[B]) else f"{len(set(top5[N2]) - set(top5[B]))} new")
    summary.append((q["qid"], q["domain"], f1, f2, d1, d2))
n = len(qs)
c1 = sum(1 for s in summary if s[4] != "same"); c2 = sum(1 for s in summary if s[5] != "same")
lines += ["## 1. In one table", "", f"{n} questions. **N1-125 changed B's top 5 on {c1}; N2-125 on {c2}.** An Act 'fires' when the question's words match the pinned Machine Spec; only then can a finalist differ from B.", "",
          "| Question | Domain | Act fired (N1) | Act fired (N2) | N1 top 5 vs B | N2 top 5 vs B |", "|---|---|---|---|---|---|"]
for qid, dom, f1, f2, d1, d2 in summary:
    lines.append(f"| {qid} | {dom} | {', '.join(f1) or '-'} | {', '.join(f2) or '-'} | {d1} | {d2} |")
lines += ["", "## 2. The questions where a finalist changed the top 5 (B | N1-125 | N2-125; passage = page number inside the judgment)", ""]
for qi, q in enumerate(qs):
    L = {v: q["lists"][v][:5] for v in (B, N1, N2)}
    if [e["h"] for e in L[N1]] == [e["h"] for e in L[B]] and [e["h"] for e in L[N2]] == [e["h"] for e in L[B]]:
        continue
    lines += [f"### {q['qid']} (domain {q['domain']})", "", f"*{short(q['question'], 400)}*", ""]
    lines += ["| Place | B | N1-125 | N2-125 |", "|---|---|---|---|"]
    for i in range(5):
        cell = []
        for v in (B, N1, N2):
            e = L[v][i]
            r = rows_by[qi].get(e["h"], {})
            mark = "" if (v == B or e["h"] == L[B][i]["h"]) else " **(changed)**"
            cell.append(f"{case_name(r.get('title'))} ({year(r.get('title'))}), p.{r.get('page', '?')}{mark}")
        lines.append(f"| {i + 1} | " + " | ".join(cell) + " |")
    lines.append("")
same = [q["qid"] for q in qs if all([e["h"] for e in q["lists"][v][:5]] == [e["h"] for e in q["lists"][B][:5]] for v in (N1, N2))]
lines += ["## 3. Identical top 5 under all three versions", "", f"{len(same)} questions: {', '.join(same)}. They add nothing to the comparison between versions; they count only toward the floors.", ""]
pooled = [len(q["rows"]) for q in qs]
lines += ["## 4. What goes to J and S", "", f"Pooled passages per question: {min(pooled)} to {max(pooled)} (total {sum(pooled)}), B's top 10 plus each finalist's top 5, shuffled; the pack does not say which version a passage came from.", ""]
open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("wrote", OUT, "| questions", n, "| N1 changed", c1, "| N2 changed", c2, "| identical", len(same))
