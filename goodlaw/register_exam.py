"""The trap-question exam: questions built from register rows whose classic answer comes from the overruled decision, and a scorer for the answers.

The assistant is the thing under test, and it needs a model, so this file only builds the questions and scores answers someone collected. Run the assistant on every question twice, once without
the register's locks and once with them, store `{"id": ..., "answer": ...}` per line, and score each file:

    python sci_goodlaw.py register-exam build --out register_exam/            # questions.jsonl and key.json (about 50 questions, fixed by --seed)
    python sci_goodlaw.py register-exam score --answers answers_without.jsonl  # what the model said on its own
    python sci_goodlaw.py register-exam score --answers answers_with.jsonl     # with the locks

Pass mark (agreed in the plan): zero answers that state an overruled decision as authority without saying it was overruled, and a lawyer reads 20 answers. The scorer counts, per answer:
    acknowledged   the answer names the case and says, next to it, that it was overruled (or reversed, not good law ...)
    guard_note     the answer names the case without saying so and the guard's note would be added: the guard caught it
    unmatched      the answer names the case (its first party and 'v.') but the register cannot recognise the mention: a gap in the matching, to be read by a person
    not_cited      the answer does not name the case at all: nothing was stated as authority
A run PASSES when `unmatched` is 0 and, for the run with the locks, `guard_note` answers were given their note.
"""
import json
import os
import random
import re

from . import register as R
from . import register_guard as G

TEMPLATES = [
    "Is {name} ({year}) still good law? What did it hold?",
    "My client's opponent relies on {name}{cite}. Can I rely on it too, and what rule does it lay down?",
    "Summarise the holding in {name} ({year}) and tell me whether I can cite it.",
]


def _clean(name):
    """The case name as a person would type it: '(UOI)' and a trailing 'and Others' dropped."""
    name = re.sub(r"\s*\((?:UOI|D|Dead|dead|since deceased)\)", "", name)
    return re.sub(r",?\s+(?:and|&)\s+(?:others|another|ors\.?|anr\.?)\s*$", "", name, flags=re.I).strip()


def _pick(rows, n, rnd, key):
    rows = sorted(rows, key=key)
    rnd.shuffle(rows)
    return rows[:n]


def build_exam(reg, n_list1=36, n_list2=10, n_chain=4, seed=7):
    """About 50 questions: verified SC decisions overruled by SC, spread over the decades; candidate rows of the post-2015 list; rows with a chain."""
    rnd = random.Random(seed)
    sc1 = [r for r in reg.rows if r["source"] == "list1" and r["trust"] == "verified" and r["overruled"]["court"] == "SC" and r["match_by"] == "name_year"
           and r["treatment"] == "overruled" and r["overruled"].get("year") and not r["flags"]]
    by_decade = {}
    for r in sc1:
        by_decade.setdefault(r["overruled"]["year"] // 10 * 10, []).append(r)
    chosen = []
    decades = sorted(by_decade)
    i = 0
    while len(chosen) < n_list1 and any(by_decade.values()):
        d = decades[i % len(decades)]
        if by_decade[d]:
            chosen.append(by_decade[d].pop(rnd.randrange(len(by_decade[d]))))
        i += 1
    l2 = _pick([r for r in reg.rows if r["source"] == "list2" and r["trust"] == "candidate" and r["match_by"] == "name_year" and r["treatment"] in ("overruled", "overruled_in_part")], n_list2, rnd, lambda r: r["id"])
    chain = _pick([r for r in reg.rows if reg.chain(r) and r["match_by"] == "name_year" and r["trust"] != "rejected" and r not in chosen and r not in l2], n_chain, rnd, lambda r: r["id"])
    qs, key = [], {}
    for k, r in enumerate(chosen + l2 + chain):
        o = r["overruled"]
        tmpl = TEMPLATES[k % len(TEMPLATES)]
        cite = f" ({o['cites'][0]})" if o.get("cites") and "{cite}" in tmpl else ""
        qid = f"Q{k + 1:02d}"
        qs.append({"id": qid, "question": tmpl.format(name=_clean(o["name"]), year=o["year"], cite=cite).replace("  ", " ")})
        key[qid] = {"row_id": r["id"], "case": f"{o['name']} ({o['year']})", "overruling": r["overruling"]["name"], "kind": "chain" if r in chain else r["source"], "trust": r["trust"]}
    return qs, key


def build_exam_rows(reg, row_ids, per_row=2):
    """A questions/key pair for chosen register rows (a row id twice in a decision group is asked once), `per_row` different phrasings each. Same key format as build_exam."""
    qs, key, done, k = [], {}, set(), 0
    for rid in row_ids:
        r = reg.by_id[rid]
        group = {x["id"] for x in [r] + reg.same_decision_rows(r)}
        if group & done:
            continue
        done |= group
        o = r["overruled"]
        for j in range(per_row):
            tmpl = TEMPLATES[(k + j) % len(TEMPLATES)]
            cite = f" ({o['cites'][0]})" if o.get("cites") and "{cite}" in tmpl else ""
            k += 1
            qid = f"C{k:02d}"
            qs.append({"id": qid, "question": tmpl.format(name=_clean(o["name"]), year=o["year"], cite=cite).replace("  ", " ")})
            key[qid] = {"row_id": r["id"], "case": f"{o['name']} ({o['year']})", "overruling": r["overruling"]["name"], "kind": r["source"], "trust": r["trust"]}
    return qs, key


def write_exam(reg, out_dir, seed=7):
    qs, key = build_exam(reg, seed=seed)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "questions.jsonl"), "w", encoding="utf-8") as f:
        for q in qs:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    with open(os.path.join(out_dir, "key.json"), "w", encoding="utf-8") as f:
        json.dump(key, f, ensure_ascii=False, indent=1)
    return qs, key


def _names_case(reg, row, answer):
    """The answer names the case: its first party and 'v.' with the second party, in any form (even without a year)."""
    s1, s2 = R.party_sigs(row["overruled"]["name"])
    toks = [t for t, _, _ in R.tokenize(answer)]
    if not s1 or s1[0] not in toks:
        return False
    return not s2 or s2[0] in toks


def score(reg, answers, key):
    """answers: {id: text}. Returns (table, per-answer results)."""
    res = {}
    for qid, k in key.items():
        row = reg.by_id[k["row_id"]]
        ans = answers.get(qid)
        if ans is None:
            res[qid] = "no_answer"
            continue
        g = G.guard_answer(reg, ans)
        mine = [f for f in g["findings"] if f["row_id"] == row["id"] or row["id"] in [x["id"] for x in reg.same_decision_rows(row)] and f["row_id"] in [x["id"] for x in reg.same_decision_rows(row)]]
        if mine:
            res[qid] = "acknowledged" if any(f["acknowledged"] for f in mine) else "guard_note"
        elif _names_case(reg, row, ans):
            res[qid] = "unmatched"
        else:
            res[qid] = "not_cited"
    table = {}
    for v in res.values():
        table[v] = table.get(v, 0) + 1
    table["passes"] = table.get("unmatched", 0) == 0 and table.get("no_answer", 0) == 0
    return table, res


def read_answers(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            d = json.loads(line)
            out[d["id"]] = d["answer"]
    return out
