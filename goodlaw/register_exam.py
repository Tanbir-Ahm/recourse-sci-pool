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


# The situation-form exam: a real fact pattern a person could have, in two versions. (a) names the overruled case, the way a person repeating their lawyer's words would; (b) the same facts without the name,
# to see whether the assistant volunteers the old case. Topics were taken from the judgments' own text or from the overruling judgments named in the register. Written 2026-10-13.
SITUATIONS = {
    "L1-0307": ("My corruption case has been in the trial court for 9 years since the charge sheet, and my lawyer says {case} means the proceedings must be dropped after a fixed period. Is that right?",
                "My corruption case has been in the trial court for 9 years since the charge sheet. Is there a fixed time limit after which the trial must be dropped?"),
    "L1-0702": ("My brother was convicted of sedition by a TADA Designated Court and given life imprisonment. His lawyer is relying on {case} for the appeal. How does that help him?",
                "My brother was convicted of sedition by a TADA Designated Court and given life imprisonment. What can he argue in his appeal?"),
    "L2-023": ("The High Court gave my husband anticipatory bail only until the next hearing and then told him to apply for regular bail. His lawyer cites {case} to say anticipatory bail should end after a short fixed time. Is that correct?",
               "The High Court gave my husband anticipatory bail only until the next hearing and then told him to apply for regular bail. Does anticipatory bail protection end after a short fixed time, or can it continue till the trial?"),
    "L2-026": ("I am accused of cheating and forgery in a complaint filed in court, and the High Court refused to extend my anticipatory bail protection. My lawyer cites {case}. What does it say about when anticipatory bail is given?",
               "I am accused of cheating and forgery in a complaint filed in court, and the High Court refused to extend my anticipatory bail protection. When is anticipatory bail given?"),
    "L2-027": ("My wife filed a dowry harassment case under Section 498A and I was granted anticipatory bail. She says {case} means the High Court should not have granted it so easily. Is she right?",
               "My wife filed a dowry harassment case under Section 498A and I was granted anticipatory bail. Can she challenge the grant, and on what grounds?"),
    "L2-029": ("I was refused anticipatory bail in an NDPS (drug) FIR. My lawyer cites {case} about the limits of anticipatory bail. Does it apply to me?",
               "I was refused anticipatory bail in an NDPS (drug) FIR. Is anticipatory bail available in a drug case, and for how long does it last?"),
    "L2-030": ("Anticipatory bail was granted to the accused in my family's case and the order gives no real reasons. Our lawyer cites {case} to ask that it be cancelled. Is that a good ground?",
               "Anticipatory bail was granted to the accused in my family's case and the order gives no real reasons. Can it be cancelled?"),
    "L2-032": ("The police recorded a video of the recovery on a phone but gave no Section 65B certificate. Our lawyer cites {case} to say the video is still admissible. Is that right?",
               "The police recorded a video of the recovery on a phone but gave no Section 65B certificate. Is the video still admissible in court?"),
    "L2-017": ("The police filed a charge sheet and the magistrate took cognizance. The complainant now asks the magistrate to order further investigation, and our lawyer cites {case} to say the magistrate cannot. Is that right?",
               "The police filed a charge sheet and the magistrate took cognizance. The complainant now asks the magistrate to order further investigation. Can the magistrate do that?"),
    "L2-018": ("The police filed a charge sheet and the magistrate took cognizance. The complainant now asks the magistrate to order further investigation, and the other side cites {case} to say the magistrate cannot. Is that right?",
               "The police filed a charge sheet and the magistrate took cognizance. The complainant asks the magistrate for a fresh investigation by the police. Is that allowed?"),
    "L2-034": ("The police officer who seized drugs from my brother also investigated the case and was the complainant. Our lawyer cites {case} to say the whole trial is void. Is that right?",
               "The police officer who seized drugs from my brother also investigated the case and was the complainant. Can the trial be challenged on that ground?"),
    "L2-052": ("The High Court stayed my corruption trial more than six months ago and has not extended the stay. My lawyer cites {case} to say the stay has ended automatically. Is that right?",
               "The High Court stayed my corruption trial more than six months ago and has not extended the stay. Does a stay on a trial end automatically after six months?"),
}


def build_exam_situations(reg):
    """(questions, key): two questions per row in SITUATIONS, 'named' (the case is named in the facts) and 'unnamed' (the same facts, no name). Same key format as build_exam, plus 'variant'."""
    qs, key, k = [], {}, 0
    for rid, (named, unnamed) in SITUATIONS.items():
        r = reg.by_id[rid]
        o = r["overruled"]
        case = f"{_clean(o['name'])} ({o['year']})"
        for variant, tmpl in (("named", named), ("unnamed", unnamed)):
            k += 1
            qid = f"S{k:02d}"
            qs.append({"id": qid, "question": tmpl.format(case=case)})
            key[qid] = {"row_id": rid, "case": f"{o['name']} ({o['year']})", "overruling": r["overruling"]["name"], "kind": r["source"], "trust": r["trust"], "variant": variant}
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
