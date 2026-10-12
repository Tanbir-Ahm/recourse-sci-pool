#!/usr/bin/env python3
"""Reads the saved AI-reviewer replies, validates them, aggregates them and scores the search versions on what each one showed.

Every number it prints is LLM-judged. Marks from a filled review sheet are labelled 'human-judged (not a lawyer)' (--human) or 'expert-checked' (--expert,
for a lawyer's sheet only). Nothing here is lawyer validation unless a lawyer's sheet is passed with --expert.

  python review_tools/ingest_llm_reviews.py --replies DIR --out OUTDIR [--pool review_data/pool_all.json] [--human sheet.xlsx ...] [--expert lawyer_sheet.xlsx ...]

Reply file names:  Q03_A_ChatGPT5.txt   (question, order A or B, model name); top-up batch: Q03_TA_ChatGPT5.txt, Q03_TB_Gemini.txt
The pool (review_data/pool_all.json) is the PRIVATE answer key: it records which search version showed each passage. Never send it to reviewers.
"""
import argparse, collections, csv, itertools, json, os, re, sys

MARKS = ["Yes", "Partly", "No", "Misleading"]
NAME_RE = re.compile(r"^([QRN])(\d{1,2})_(T?[AB])_(.+?)\.(?:txt|json|md)$", re.I)       # Q01_A_ChatGPT5.txt (the first 12 questions); R01_A_Gemini.txt (the 30 real questions); N01_A_Gemini.txt (the fix test's 30 new questions)
DEFAULT_POOL = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "review_data", "pool_all.json"))
SET_VARIANTS = ("S ", "M ")          # versions named like 'S site shown' are sets of what a method showed, scored on all of it, not on a top 5
MARK_ALIASES = {"yes": "Yes", "partly": "Partly", "partial": "Partly", "partially": "Partly", "no": "No", "misleading": "Misleading"}
QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " ", "…": "..."})


def norm(s):
    return re.sub(r"\s+", " ", (s or "").translate(QUOTES)).strip().casefold()


# ----------------------------------------------------------------------------- parsing
def _loads_tolerant(s):
    """json.loads, then a repair pass: // comments, trailing commas, smart quotes around keys are NOT guessed at."""
    try:
        return json.loads(s)
    except ValueError:
        pass
    t = re.sub(r"(?m)^\s*//.*$", "", s)
    t = re.sub(r'(?<=[,\]\}0-9"])\s+//[^\n"]*$', "", t, flags=re.M)
    t = re.sub(r",\s*([\]}])", r"\1", t)
    return json.loads(t)


def parse_reply(text):
    """Returns (obj, note). obj is None when no JSON object with a 'marks' list can be recovered."""
    t = (text or "").strip().lstrip("﻿")
    fence = re.findall(r"```(?:json|JSON)?\s*(.*?)```", t, flags=re.S)
    for chunk in fence + [t]:
        try:
            obj = _loads_tolerant(chunk.strip())
            if isinstance(obj, dict) and isinstance(obj.get("marks"), list):
                return obj, "ok" if chunk.strip() == t else "extracted from code fence"
        except ValueError:
            pass
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", t):
        try:
            obj, _ = dec.raw_decode(t[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("marks"), list):
            return obj, "extracted from surrounding text"
    # last resort: repair the first plausible object span
    first, last = t.find("{"), t.rfind("}")
    if 0 <= first < last:
        try:
            obj = _loads_tolerant(t[first:last + 1])
            if isinstance(obj, dict) and isinstance(obj.get("marks"), list):
                return obj, "repaired (comments or trailing commas)"
        except ValueError:
            pass
    return None, "no valid JSON object with a 'marks' list (truncated or not JSON)"


def norm_mark(m):
    return MARK_ALIASES.get(re.sub(r"[^a-z]", "", str(m).lower()))


# ----------------------------------------------------------------------------- statistics
def cohen_kappa(a, b):
    """a, b: equal-length lists of labels. Returns (kappa or None, percent agreement)."""
    n = len(a)
    if n == 0:
        return None, None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    pe = sum(ca[k] / n * cb[k] / n for k in set(ca) | set(cb))
    return (None if pe >= 1.0 else (po - pe) / (1 - pe)), po


def fmt(x, p=2):
    return "n/a" if x is None else f"{x:.{p}f}"


# ----------------------------------------------------------------------------- load
def load_pool(path):
    pool = json.load(open(path, encoding="utf-8"))
    if isinstance(pool, dict):                       # the pool runner's file: {"run": ..., "questions": [...]}
        pool = pool["questions"]
    passages = {}
    for q in pool:
        for r in q["rows"]:
            passages[(q["qid"], r["n"])] = dict(r, qid=q["qid"], kind=q["kind"], landmark_doc=q.get("landmark_doc"))
    return pool, passages


def kind_group(kind):
    """The first 12 questions are 'lay' or 'legal'; the 30 real ones are 'everyday', 'narrative' or 'legal'. Everyday and narrative questions are the plain-language group."""
    return "lay" if kind in ("lay", "everyday", "narrative") else kind


def load_replies(folder, passages, pool):
    """Returns runs {(model, order): {(qid, no): mark}}, a problems list, and evidence stats."""
    runs = collections.defaultdict(dict)
    problems, ev = [], collections.Counter()
    expected = {q["qid"]: {r["n"] for r in q["rows"] if not r.get("topup")} for q in pool}
    expected_top = {q["qid"]: {r["n"] for r in q["rows"] if r.get("topup")} for q in pool}
    for fn in sorted(os.listdir(folder)):
        m = NAME_RE.match(fn)
        if not m:
            if fn != "PUT_SAVED_REPLIES_HERE.txt":
                problems.append((fn, "file name does not match Qnn_A_model.txt or Rnn_A_model.txt: skipped"))
            continue
        qid, order = f"{m.group(1).upper()}{int(m.group(2)):02d}", m.group(3).upper()
        model = re.sub(r"(?:\.(?:txt|json|md))+$", "", m.group(4), flags=re.I)        # 'Gemini.txt.txt' (a hidden extension added twice) is still 'Gemini'
        is_top = order.startswith("T")
        exp = (expected_top if is_top else expected).get(qid)
        if exp is None or (is_top and not exp):
            problems.append((fn, f"unknown question {qid}" if exp is None else f"{qid} has no top-up passages: skipped")); continue
        obj, note = parse_reply(open(os.path.join(folder, fn), encoding="utf-8", errors="replace").read())
        if obj is None:
            problems.append((fn, note)); continue
        if note != "ok":
            problems.append((fn, f"parsed, but {note}"))
        if obj.get("question_id") not in (None, qid):
            problems.append((fn, f"reply says question_id={obj.get('question_id')} but file is {qid}: skipped")); continue
        seen = {}
        for e in obj["marks"]:
            try:
                no = int(e.get("no"))
            except (TypeError, ValueError, AttributeError):
                problems.append((fn, f"entry without a usable 'no': {str(e)[:60]}")); continue
            mk = norm_mark(e.get("mark"))
            if no not in exp:
                problems.append((fn, f"passage no. {no} is not part of this {'top-up ' if is_top else ''}batch for {qid}")); continue
            if mk is None:
                problems.append((fn, f"passage {no}: mark {e.get('mark')!r} is not Yes/Partly/No/Misleading")); continue
            if no in seen:
                problems.append((fn, f"passage {no} marked twice: first mark kept")); continue
            seen[no] = mk
            quote = norm(e.get("evidence"))
            ev["marks"] += 1
            if not quote:
                ev["no_evidence"] += 1
            elif quote in norm(passages[(qid, no)]["text"]):
                ev["found"] += 1
            else:
                ev["not_found"] += 1
                problems.append((fn, f"passage {no}: evidence quote is not in the passage text (possible invented quote)"))
        missing = sorted(exp - set(seen))
        if missing:
            problems.append((fn, f"passages not marked: {missing}"))
        key = (model, order)
        for no, mk in seen.items():
            if (qid, no) in runs[key]:
                problems.append((fn, f"duplicate file for {qid} {model} {order}: later file overwrote passage {no}"))
            runs[key][(qid, no)] = mk
    return runs, problems, ev


# ----------------------------------------------------------------------------- analysis
def consensus(votes):
    c = collections.Counter(votes)
    if not c:
        return None, 0.0
    top = c.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return "split", top[0][1] / len(votes)
    return top[0][0], top[0][1] / len(votes)


def analyse(runs, passages, pool):
    keys = sorted(runs)
    cons = {}
    for p in passages:
        votes = [runs[k][p] for k in keys if p in runs[k]]
        mk, share = consensus(votes)
        cons[p] = dict(mark=mk, share=share, n=len(votes), votes={f"{m}/{o}": runs[(m, o)].get(p) for m, o in keys},
                       any_misleading="Misleading" in votes)
    pair = []
    for k1, k2 in itertools.combinations(keys, 2):
        common = sorted(set(runs[k1]) & set(runs[k2]))
        if not common:
            continue
        a, b = [runs[k1][p] for p in common], [runs[k2][p] for p in common]
        k4, po = cohen_kappa(a, b)
        useful = lambda x: "useful" if x in ("Yes", "Partly") else "not"
        kb, pob = cohen_kappa([useful(x) for x in a], [useful(x) for x in b])
        same_model = k1[0] == k2[0]
        pair.append(dict(a=f"{k1[0]}/{k1[1]}", b=f"{k2[0]}/{k2[1]}", n=len(common), kind="same model, A vs B" if same_model else "different models",
                         agree4=po, kappa4=k4, agree_useful=pob, kappa_useful=kb))
    # variant scoring: for each search variant, how good are its top 5 passages
    per_variant = collections.defaultdict(lambda: collections.defaultdict(list))
    for q in pool:
        for r in q["rows"]:
            c = cons[(q["qid"], r["n"])]
            for v, rank in r["variants"].items():
                if v.startswith(SET_VARIANTS) or rank <= 5:
                    per_variant[v][q["qid"]].append(c["mark"])
    var_rows = []
    for v in sorted(per_variant):
        qs = per_variant[v]
        def mean_of(f, kind=None):
            vals = []
            for qid, marks in qs.items():
                if kind and kind_group(next(q["kind"] for q in pool if q["qid"] == qid)) != kind:
                    continue
                judged = [m for m in marks if m not in (None, "split")]
                if judged:
                    vals.append(f(judged))
            return sum(vals) / len(vals) if vals else None
        yes = lambda ms: sum(m == "Yes" for m in ms) / len(ms)
        use = lambda ms: sum(m in ("Yes", "Partly") for m in ms) / len(ms)
        mis = lambda ms: sum(m == "Misleading" for m in ms) / len(ms)
        judged_q = sum(1 for ms in qs.values() if any(m not in (None, "split") for m in ms))      # questions where this version has at least one marked passage
        var_rows.append(dict(variant=v, questions=judged_q, top5_slots=sum(len(m) for m in qs.values()),
                             unjudged=sum(m in (None, "split") for ms in qs.values() for m in ms),
                             yes=mean_of(yes), useful=mean_of(use), misleading=mean_of(mis),
                             yes_lay=mean_of(yes, "lay"), yes_legal=mean_of(yes, "legal"),
                             useful_lay=mean_of(use, "lay"), useful_legal=mean_of(use, "legal")))
    return cons, pair, var_rows


def read_expert(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Review"]
    marks = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        qid, no, mark = row[0], row[1], row[4]
        if isinstance(no, (int, float)) and isinstance(qid, str) and mark:
            mk = norm_mark(mark)
            if mk:
                marks[(qid, int(no))] = mk
    return marks


def compare_expert(cons, expert):
    common = [p for p in sorted(expert) if cons.get(p, {}).get("mark") not in (None, "split")]
    if not common:
        return None
    a = [cons[p]["mark"] for p in common]; b = [expert[p] for p in common]
    k4, po = cohen_kappa(a, b)
    u = lambda x: "useful" if x in ("Yes", "Partly") else "not"
    ku, pu = cohen_kappa([u(x) for x in a], [u(x) for x in b])
    conf = collections.Counter(zip(b, a))
    return dict(n=len(common), agree4=po, kappa4=k4, agree_useful=pu, kappa_useful=ku, confusion=conf)


RANK = {"Misleading": 0, "No": 1, "Partly": 2, "Yes": 3}       # less favourable to more favourable, used only to settle ties


def _resolve(votes, pick):
    """Plurality mark; when marks tie for most votes, `pick` (min or max) chooses the less or more favourable of the tied ones."""
    c = collections.Counter(v for v in votes if v)
    if not c:
        return None
    top = max(c.values())
    return pick((m for m, n in c.items() if n == top), key=RANK.get)


def _scores_by_variant(pool, mark_of):
    """{variant: {question: (yes share, yes-or-partly share, misleading share, marked slots)}}, with the same slot rules as analyse():
    a search version is scored on its top 5, 'S ...' and 'M ...' sets on everything they showed. mark_of(qid, n) gives a mark or None."""
    out = collections.defaultdict(dict)
    for q in pool:
        buckets = collections.defaultdict(list)
        for r in q["rows"]:
            m = mark_of(q["qid"], r["n"])
            for v, rank in r["variants"].items():
                if v.startswith(SET_VARIANTS) or rank <= 5:
                    buckets[v].append(m)
        for v, ms in buckets.items():
            judged = [m for m in ms if m is not None]
            if judged:
                n = len(judged)
                out[v][q["qid"]] = (sum(m == "Yes" for m in judged) / n, sum(m in ("Yes", "Partly") for m in judged) / n, sum(m == "Misleading" for m in judged) / n, n)
    return out


def sensitivity(runs, passages, pool, baseline="A today"):
    """How much do the version scores depend on how disagreements between runs are handled?
    Treatments: 'agreed' (the headline rule: a passage counts only when the plurality is clear), 'lower' / 'higher' (a tie goes to the less / more
    favourable tied mark), and each run on its own. Returns one row per version, with its macro-averaged Yes and Yes-or-Partly share under every
    treatment and, against the baseline version on the SAME questions, in how many treatments it comes out above, equal or below."""
    keys = sorted(runs)
    votes = {p: [runs[k][p] for k in keys if p in runs[k]] for p in passages}

    def agreed(q, n):
        c = collections.Counter(votes[(q, n)]).most_common()
        return None if not c or (len(c) > 1 and c[0][1] == c[1][1]) else c[0][0]
    treatments = [("agreed", agreed),
                  ("lower", lambda q, n: _resolve(votes[(q, n)], min)),
                  ("higher", lambda q, n: _resolve(votes[(q, n)], max))]
    treatments += [(f"run {m}/{o}", (lambda q, n, k=(m, o): runs[k].get((q, n)))) for m, o in keys]
    scored = {t: _scores_by_variant(pool, fn) for t, fn in treatments}
    run_labels = [t for t, _ in treatments if t.startswith("run ")]

    def macro(per_q, qids, i):
        vals = [per_q[q][i] for q in qids if q in per_q]
        return sum(vals) / len(vals) if vals else None
    rows = []
    for v in sorted({v for t in scored for v in scored[t]}):
        cells = {}
        for t in scored:
            per_q = scored[t].get(v, {})
            cells[t] = dict(questions=len(per_q), slots=sum(x[3] for x in per_q.values()), yes=macro(per_q, per_q, 0), useful=macro(per_q, per_q, 1), misleading=macro(per_q, per_q, 2))
        above = equal = below = 0
        if v != baseline:
            for t in scored:
                a, b = scored[t].get(v, {}), scored[t].get(baseline, {})
                common = [q for q in a if q in b]
                if common:
                    x, y = macro(a, common, 0), macro(b, common, 0)
                    above += x > y + 1e-9; below += x < y - 1e-9; equal += abs(x - y) <= 1e-9
        ys = [cells[t]["yes"] for t in run_labels if cells[t]["yes"] is not None]
        us = [cells[t]["useful"] for t in run_labels if cells[t]["useful"] is not None]
        rows.append(dict(variant=v, cells=cells, questions=cells["higher"]["questions"], runs_yes=(min(ys), max(ys)) if ys else None,
                         runs_useful=(min(us), max(us)) if us else None, above=above, equal=equal, below=below, baseline=baseline, is_baseline=(v == baseline)))
    return rows


# ----------------------------------------------------------------------------- report
def write_outputs(out, runs, problems, ev, cons, pair, var_rows, passages, experts, label, sens=None):
    os.makedirs(out, exist_ok=True)
    keys = sorted(runs)
    with open(os.path.join(out, "llm_marks.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Q", "No", "judgment_id", "consensus", "agreement_share", "n_votes", "any_Misleading"] + [f"{m}/{o}" for m, o in keys] + ["source"])
        for p in sorted(passages):
            c = cons[p]
            w.writerow([p[0], p[1], passages[p]["doc"], c["mark"], fmt(c["share"]), c["n"], c["any_misleading"]] + [c["votes"][f"{m}/{o}"] for m, o in keys] + ["LLM-judged"])
    L = [f"# LLM review results ({label})", "", "**Source label for everything below: LLM-judged. None of it is lawyer-validated.**", ""]
    L += [f"Runs read: {len(keys)} ({', '.join(f'{m}/{o}' for m, o in keys)}); passages covered by at least one run: {sum(c['n'] > 0 for c in cons.values())} of {len(passages)}.", ""]
    L += ["## File problems", ""] + ([f"- `{fn}`: {msg}" for fn, msg in problems] if problems else ["- none"]) + [""]
    if ev["marks"]:
        L += ["## Evidence quotes", "", f"- {ev['found']} of {ev['marks']} quotes found verbatim in the passage; {ev['not_found']} not found (possible invented quotes); {ev['no_evidence']} empty.", ""]
    L += ["## Agreement between runs", "", "| Run A | Run B | Comparison | Passages | Agree (4 marks) | Kappa (4 marks) | Agree (useful vs not) | Kappa (useful vs not) |", "|---|---|---|---|---|---|---|---|"]
    for p in pair:
        L.append(f"| {p['a']} | {p['b']} | {p['kind']} | {p['n']} | {fmt(p['agree4'])} | {fmt(p['kappa4'])} | {fmt(p['agree_useful'])} | {fmt(p['kappa_useful'])} |")
    if not pair:
        L.append("| - | - | - | - | - | - | - | - |")
    L += ["", "Rule of thumb: kappa below 0.4 is weak agreement, 0.4 to 0.6 moderate, above 0.6 good. 'Same model, A vs B' measures sensitivity to passage order.", ""]
    dist = collections.Counter(c["mark"] for c in cons.values())
    L += ["## Consensus marks (plurality of all runs)", "", " | ".join(f"{k}: {dist.get(k, 0)}" for k in MARKS + ["split", None]), "",
          f"Passages marked Misleading by at least one run: {sum(c['any_misleading'] for c in cons.values())}", ""]
    L += ["## How good is what each search version shows (LLM-judged consensus)", "",
          "| Version | Questions judged | Top-5 slots | Unjudged slots | Yes share | Yes or Partly | Misleading | Yes (plain questions) | Yes (legal questions) |", "|---|---|---|---|---|---|---|---|---|"]
    for r in var_rows:
        L.append(f"| {r['variant']} | {r['questions']} | {r['top5_slots']} | {r['unjudged']} | {fmt(r['yes'])} | {fmt(r['useful'])} | {fmt(r['misleading'])} | {fmt(r['yes_lay'])} | {fmt(r['yes_legal'])} |")
    L += ["", "Shares are averaged per question over the passages each version placed in its top 5; versions whose name starts with S or M (the site's own search, my pipeline's top 6) are scored on everything they showed. Only passages that were in the pool can be scored; 'L landmark key passages' is the set of verified paragraphs, not a search version.", ""]
    if sens and len(runs) > 1:
        two = lambda lo_hi: "-" if lo_hi is None else (f"{lo_hi[0]:.2f}" if abs(lo_hi[0] - lo_hi[1]) < 0.005 else f"{lo_hi[0]:.2f} to {lo_hi[1]:.2f}")
        cell = lambda c: "-" if c["yes"] is None else f"{c['yes']:.2f} / {c['useful']:.2f}"
        L += ["## Sensitivity: do the scores depend on how disagreements between runs are handled?", "",
              "The table above counts a passage only when the runs agree on its mark, so every passage they disagree on drops out. Here the same scores are recomputed four ways. "
              "Each cell is 'Yes share / Yes-or-Partly share', averaged per question over the questions marked so far. "
              "'Ties to the lower mark' and 'Ties to the higher mark' keep every disagreement and settle it the unfavourable or favourable way. "
              "'Each run alone' is the lowest to the highest score any single run gives. A version whose passages are only partly marked so far (for example the site's own extra passages before the top-up is marked) is scored on what has been marked. The last column compares each version with the baseline "
              f"({sens[0]['baseline']}) on the questions both were marked on, counting the treatments (agreed, lower, higher, each run) in which it comes out above, equal or below.", "",
              "| Version | Questions judged | Agreed only | Ties to the lower mark | Ties to the higher mark | Each run alone | Against the baseline (same questions) |", "|---|---|---|---|---|---|---|"]
        for r in sens:
            alone = "-" if r["runs_yes"] is None else f"{two(r['runs_yes'])} / {two(r['runs_useful'])}"
            vs = "baseline" if r["is_baseline"] else f"above in {r['above']}, equal in {r['equal']}, below in {r['below']}"
            L.append(f"| {r['variant']} | {r['questions']} | {cell(r['cells']['agreed'])} | {cell(r['cells']['lower'])} | {cell(r['cells']['higher'])} | {alone} | {vs} |")
        L += ["", "Read it this way: a difference between versions is worth acting on only if it points the same way in every column and holds over more than a few questions. "
              "With 12 questions only big differences show; gaps that appear in one column and vanish in another are noise from the AI reviewer's own unsteadiness.", ""]
        with open(os.path.join(out, "llm_sensitivity.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["version", "treatment", "questions_judged", "marked_slots", "yes_share", "yes_or_partly_share", "misleading_share", "source"])
            for r in sens:
                for t, c in r["cells"].items():
                    w.writerow([r["variant"], t, c["questions"], c["slots"], fmt(c["yes"]) if c["yes"] is not None else "", fmt(c["useful"]) if c["useful"] is not None else "", fmt(c["misleading"]) if c["misleading"] is not None else "", "LLM-judged"])
    for name, label_h, res in experts:
        L += [f"## Comparison with {label_h} marks: {name} ({label_h} marks vs LLM consensus)", ""]
        if res is None:
            L += ["- no overlapping marked passages", ""]; continue
        L += [f"- Passages compared: {res['n']}; agree on 4 marks: {fmt(res['agree4'])}; kappa: {fmt(res['kappa4'])}; agree on useful vs not: {fmt(res['agree_useful'])}; kappa: {fmt(res['kappa_useful'])}", "",
              "| Reviewer \\ LLM | " + " | ".join(MARKS) + " |", "|---|" + "---|" * len(MARKS)]
        for e in MARKS:
            L.append(f"| {e} | " + " | ".join(str(res["confusion"].get((e, l), 0)) for l in MARKS) + " |")
        L.append("")
    open(os.path.join(out, "llm_summary.md"), "w", encoding="utf-8").write("\n".join(L))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--replies", required=True, help="folder with the saved replies"); ap.add_argument("--pool", default=DEFAULT_POOL); ap.add_argument("--out", required=True)
    ap.add_argument("--human", action="append", default=[], help="a filled review sheet from a person who is not a lawyer (labelled human-judged)")
    ap.add_argument("--expert", action="append", default=[], help="a filled review sheet from a lawyer (labelled expert-checked)")
    ap.add_argument("--label", default="real replies")
    a = ap.parse_args(argv)
    pool, passages = load_pool(a.pool)
    runs, problems, ev = load_replies(a.replies, passages, pool)
    cons, pair, var_rows = analyse(runs, passages, pool)
    sens = sensitivity(runs, passages, pool)
    experts = [(os.path.basename(p), "human-judged (not a lawyer)", compare_expert(cons, read_expert(p))) for p in a.human]
    experts += [(os.path.basename(p), "expert-checked", compare_expert(cons, read_expert(p))) for p in a.expert]
    text = write_outputs(a.out, runs, problems, ev, cons, pair, var_rows, passages, experts, a.label, sens)
    print(text)
    return dict(runs=runs, problems=problems, ev=ev, cons=cons, pair=pair, var_rows=var_rows, experts=experts, sens=sens)


if __name__ == "__main__":
    main()
