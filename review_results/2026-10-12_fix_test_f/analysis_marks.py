"""Deeper reading of the stage F marks (after the scorer): per question, per version, and where the two tools disagree. LLM-judged; never 'X% accurate'. Reads pool.json, the replies and (for the named-authority sets) the sealed key."""
import sys, json, collections, statistics, os
sys.path.insert(0, "review_tools")
import ingest_llm_reviews as ing
D = "review_results/2026-10-12_fix_test_f"
pool, passages = ing.load_pool(D + "/pool.json")
runs, problems, ev = ing.load_replies(D + "/replies_for_the_reader", passages, pool)
key = json.load(open("review_data/ruler/fix_test_f_key_v1.json"))["questions"]
G = {"Misleading": 0, "No": 1, "Partly": 2, "Yes": 3}
chat = {p: m for (mod, o), r in runs.items() if mod == "ChatGPT" for p, m in r.items()}
gem = {p: m for (mod, o), r in runs.items() if mod == "Gemini" for p, m in r.items()}
V = list(pool[0]["lists"]); B, N1, N2 = V[0], [v for v in V if v.startswith("N1")][0], [v for v in V if v.startswith("N2")][0]
def grade(p, how):
    a, b = G[chat[p]], G[gem[p]]
    return {"ChatGPT": a, "Gemini": b, "lower": min(a, b), "higher": max(a, b)}[how]
out = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); out.append(s)
P("# Stage F marks: deeper reading (LLM-judged; key used only for the named-authority sets)\n")
# 1 tool behaviour
pairs = [(chat[p], gem[p]) for p in passages]
agree = sum(a == b for a, b in pairs) / len(pairs)
c = collections.Counter(chat.values()); g = collections.Counter(gem.values())
P(f"## 1. The two markers\nPassages {len(pairs)}; exact agreement {agree:.1%}.")
P("ChatGPT marks:", dict(c), "| Gemini marks:", dict(g))
conf = collections.Counter((a, b) for a, b in pairs if a != b)
P("Most common disagreements (ChatGPT, Gemini):", conf.most_common(6))
opp = [(p, chat[p], gem[p]) for p in passages if {chat[p], gem[p]} == {"Yes", "Misleading"} or {chat[p], gem[p]} == {"Yes", "No"}]
P("Passages where one says Yes and the other No/Misleading:", len(opp), [f"{p[0]}#{p[1]}" for p, _, _ in opp])
# 2 per question B vs arms
P("\n## 2. Per question, mean grade of the top 5 (both markers, ties to the lower mark) | Yes-count of the top 5")
rows = []
for q in pool:
    if q["domain"] == "K": continue
    t5 = {v: [passages[(q["qid"], next(r["n"] for r in q["rows"] if r["h"] == e["h"]))] for e in q["lists"][v][:5]] for v in (B, N1, N2)}
    def gr(v, how): return statistics.mean(grade((q["qid"], x["n"]), how) for x in t5[v])
    ys = {v: sum(1 for x in t5[v] if chat[(q["qid"], x["n"])] == "Yes" and gem[(q["qid"], x["n"])] == "Yes") for v in (B, N1, N2)}
    rows.append((q["qid"], q["domain"], gr(B, "lower"), gr(N1, "lower"), gr(N2, "lower"), ys[B], ys[N1], ys[N2]))
P("| Q | dom | B | N1 | N2 | B both-Yes | N1 | N2 |\n|---|---|---|---|---|---|---|---|")
for r in rows: P(f"| {r[0]} | {r[1]} | {r[2]:.1f} | {r[3]:.1f} | {r[4]:.1f} | {r[5]} | {r[6]} | {r[7]} |")
P("\nWeakest questions for B (lowest grade):", [(r[0], round(r[2], 1)) for r in sorted(rows, key=lambda r: r[2])[:8]])
P("Questions with a both-Yes in B's top 5: %d of %d; none: %s" % (sum(1 for r in rows if r[5] > 0), len(rows), [r[0] for r in rows if r[5] == 0]))
# 3 changed questions: which passages differ and what they were marked
P("\n## 3. The changed questions: passages that left and entered the top 5 (marks: ChatGPT/Gemini)")
for q in pool:
    qid = q["qid"]
    if qid in ("N28","N29","N30"): continue
    n_of = {r["h"]: r["n"] for r in q["rows"]}; row = {r["h"]: r for r in q["rows"]}
    b5 = [e["h"] for e in q["lists"][B][:5]]
    for v, name in ((N1, "N1"), (N2, "N2")):
        v5 = [e["h"] for e in q["lists"][v][:5]]
        if v5 == b5: continue
        if name == "N2" and [e["h"] for e in q["lists"][N1][:5]] == v5: continue    # identical to N1: shown once
        out_ = [h for h in b5 if h not in v5]; in_ = [h for h in v5 if h not in b5]
        tag = "N1=N2" if [e["h"] for e in q["lists"][N1][:5]] == [e["h"] for e in q["lists"][N2][:5]] else name
        mk = lambda h: f"{chat[(qid, n_of[h])][:1]}/{gem[(qid, n_of[h])][:1]}"
        P(f"- **{qid}** ({tag}): left B's top 5: " + "; ".join(f"{row[h]['title'][:40]} p.{row[h]['page']} [{mk(h)}]" for h in out_) + " | entered: " + "; ".join(f"{row[h]['title'][:40]} p.{row[h]['page']} [{mk(h)}]" for h in in_))
# 4 named authority
P("\n## 4. Named authority (sealed key) and the stale ruling")
for q in pool:
    qid = q["qid"]
    if qid not in key or qid in ("N28","N29","N30"): continue
    kd = set(key[qid]["key_docs"]); stale = {s["doc"] for s in key[qid]["stale_docs"] if s["counts_as_stale"]}
    def docs(v, k): return [e["doc"] for e in q["lists"][v][:k]]
    r5 = {name: sum(1 for d in docs(v, 5) if d in kd) for name, v in (("B", B), ("N1", N1), ("N2", N2))}
    r10 = {name: any(d in kd for d in docs(v, 10)) for name, v in (("B", B), ("N1", N1), ("N2", N2))}
    st = {name: sum(1 for d in docs(v, 5) if d in stale) for name, v in (("B", B), ("N1", N1), ("N2", N2))}
    if not r10["B"] or r5["B"] != r5["N1"] or r5["B"] != r5["N2"] or any(st.values()):
        P(f"- {qid}: key passages in top 5 (B/N1/N2) {r5['B']}/{r5['N1']}/{r5['N2']}; key doc anywhere in top 10 (B) {r10['B']}; stale in top 5 {st}")
none10 = [q["qid"] for q in pool if q["qid"] in key and key[q["qid"]]["key_docs"] and not any(e["doc"] in set(key[q["qid"]]["key_docs"]) for e in q["lists"][B][:10]) and q["qid"] not in ("N28","N29","N30")]
P("Questions where B shows NO key judgment in its top 10:", none10)
# 5 controls
P("\n## 5. Controls: B's top 5 and the marks (ChatGPT/Gemini)")
for qid in ("N28", "N29", "N30"):
    q = next(x for x in pool if x["qid"] == qid); n_of = {r["h"]: r["n"] for r in q["rows"]}; row = {r["h"]: r for r in q["rows"]}
    P(f"- {qid}: " + " | ".join(f"{str(row[e['h']]['title'])[:32]} p.{row[e['h']]['page']} [{chat[(qid, n_of[e['h']])][:1]}/{gem[(qid, n_of[e['h']])][:1]}]" for e in q["lists"][B][:5]))
open(D + "/MARKS_ANALYSIS.md", "w").write("\n".join(out))
