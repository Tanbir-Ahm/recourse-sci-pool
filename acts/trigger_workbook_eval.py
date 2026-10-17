#!/usr/bin/env python3
"""Can the owner's trigger workbook (review_data/ruler/inputs/2026-10-12_trigger_workbook_with_spec_v2.xlsx) find the Act a question is about?  (2026-10-17)

Read-only and free (no model, no network). Compares, on the 75 Act-shelf gold questions (Recourse act_shelf/eval_questions.json, written 2026-10-16 by Claude):
  - the Act Directory as it is today (names, aliases, a few listed phrases),
  - Machine Spec v2 N1 (precise anchors) and N2 (N1 + plain-language anchors with exclusions), review_tools/machine_spec_v2.py,
  - the 'Layperson Trigger Additions' sheet's phrases used as matchers (literal and by word overlap),
  - a list of the Acts' OWN distinctive words, derived from the Acts' text (derive_vocabulary) and pruned by hand before testing.
It also runs the detectors on control questions that concern none of the five Acts, and on the owner's own sentences from the 2026-10-17 staging test.
Caveats printed with the numbers: the 75 questions are Claude's, not real users'; the pruning of the vocabulary list was done knowing some misses (in-sample for a few terms); no AI router is tested here (no Anthropic key in the sandbox).
Run: python acts/trigger_workbook_eval.py  [RECOURSE=/path/to/recourse checkout]"""
import collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
REC = os.environ.get("RECOURSE", "/home/user/recourse")
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, REC)
import machine_spec_v2 as M
import act_directory as AD
import openpyxl

MAP = {"PC Act": "pc_act_1988", "POCSO": "pocso_act_2012", "UAPA": "uapa_1967", "PMLA": "pmla_2002", "SC/ST": "sc_st_act_1989"}
SHELF = set(MAP.values())
Q = json.load(open(os.path.join(REC, "act_shelf/eval_questions.json")))["questions"]


def dir_(q): return {a["id"] for a in AD.detect(q)} & SHELF
def n1(q): return {MAP[a] for a in M.question_acts(q, "N1") if a in MAP}
def n2(q): return {MAP[a] for a in M.question_acts(q, "N2") if a in MAP}


# Statute vocabulary: terms the Acts themselves use that the BNS/BNSS and the other four Acts do not (see derive_vocabulary), pruned of generic words BEFORE the test.
LEX = {"pc_act_1988": [r"\bspecial judges?\b", r"\bundue advantage\b", r"\bprevention of corruption\b"],
       "pocso_act_2012": [r"\bpenetrative sexual\b", r"\baggravated sexual assault\b", r"\bpornograph\w*.{0,60}\b(child|minor)\b|\b(child|minor)\b.{0,60}pornograph\w*"],
       "uapa_1967": [r"\bterroris[mt]\w*", r"\bunlawful association\b", r"\bdeclared unlawful\b", r"\bproceeds of terrorism\b"],
       "pmla_2002": [r"\badjudicating authority\b", r"\bappellate tribunal\b", r"\breporting entit\w+", r"\bmoney[- ]laundering\b"],
       "sc_st_act_1989": [r"\bexclusive special court\b", r"\bscheduled (castes?|tribes?)\b", r"\batrocit\w+"]}
LEXC = {k: [re.compile(p, re.I | re.S) for p in v] for k, v in LEX.items()}
def lex(q): return {k for k, c in LEXC.items() if any(p.search(q) for p in c)}


def derive_vocabulary():
    STOP = set("a an the of to in on at for with by from and or but is are was were be been it its as if so shall may any all such this that these those which who whom he she they them their his her under act section sub clause provisions provision case other than into upon not no one two three also thereof therein hereby said".split())
    def grams(t):
        w = re.findall(r"[a-z][a-z\-']+", t.lower()); out = set()
        for n in (1, 2, 3):
            for i in range(len(w) - n + 1):
                g = w[i:i + n]
                if g[0] in STOP or g[-1] in STOP or (n == 1 and len(g[0]) < 6): continue
                out.add(" ".join(g))
        return out
    docs = {k: [grams((s.get("title") or "") + " " + (s.get("text") or "")) for s in json.load(open(os.path.join(REC, "act_shelf", k + ".json"))) if s.get("omitted") not in (True, "True")] for k in SHELF}
    bg = []
    for f in ("bharatiya_nyaya_sanhita_2023_chunks.json", "bharatiya_nagarik_suraksha_sanhita_2023_chunks.json"):
        bg += [grams(c["text"]) for c in json.load(open(os.path.join(REC, "chunks", f)))]
    res = {}
    for k in SHELF:
        others = [d for kk in SHELF if kk != k for d in docs[kk]]; cnt = collections.Counter(g for s in docs[k] for g in s); rows = []
        for g, c in cnt.items():
            if c < 3: continue
            fo = sum(g in s for s in others) / len(others); fb = sum(g in s for s in bg) / len(bg)
            if fb > 0.003 or fo > 0.03 or (c / len(docs[k])) / (fo + fb + 1e-4) < 8: continue
            rows.append((c, g))
        res[k] = [g for c, g in sorted(rows, key=lambda x: (-x[0], x[1]))]
    return res


def score(name, fn):
    ok = sum(q["act_key"] in fn(q["q"]) for q in Q); wr = sum(bool(fn(q["q"]) - {q["act_key"]}) for q in Q)
    lay = sum(q["act_key"] in fn(q["q"]) for q in Q if q["kind"] == "layman"); law = sum(q["act_key"] in fn(q["q"]) for q in Q if q["kind"] == "lawyer")
    print(f"{name:36s} right Act {ok}/75 = {ok/75:.0%}  (layman {lay}/34, lawyer {law}/41)  wrong-Act fires {wr}")


print("== 1. The 75 gold questions (5 Acts x 15) ==")
score("Directory today", dir_); score("Spec v2 N1 (precise)", n1); score("Spec v2 N2 (+ plain words)", lambda q: n1(q) | n2(q))
score("Directory + N2", lambda q: dir_(q) | n2(q)); score("Acts' own vocabulary only", lex); score("Directory + N2 + vocabulary", lambda q: dir_(q) | n2(q) | lex(q))
allf = lambda q: dir_(q) | n2(q) | lex(q)
for act in sorted(SHELF):
    sub = [q for q in Q if q["act_key"] == act]
    print(f"   {act:16s} n={len(sub)}  Directory {sum(act in dir_(q['q']) for q in sub):2d}  N2 {sum(act in n2(q['q']) for q in sub):2d}  all three {sum(act in allf(q['q']) for q in sub):2d}")
print("   still missed by all three:")
for q in Q:
    if q["act_key"] not in allf(q["q"]): print(f"     {q['id']} [{q['kind']}] {q['q']}")

print("\n== 2. The owner's own sentences (staging test 2026-10-17) and other plain-language bribery wording ==")
for t in ["My son works as a clerk in a government office. He was arrested yesterday for taking money from a contractor.",
          "Is it bailable? (Read with the earlier messages, this asks: Is the offence of a government clerk accepting money from a contractor bailable?)",
          "My son was caught taking money from a contractor in a government office", "An official took money from a contractor",
          "The tehsildar took Rs 10,000 from us to sign our land papers", "A police constable demanded money to not file a case against me",
          "The officer is demanding a percentage to clear my bill", "My father is a government employee and the vigilance department raided our house"]:
    print(f"   Directory={sorted(dir_(t))} N2={sorted(n2(t))} vocabulary={sorted(lex(t))}  <- {t[:90]}")

print("\n== 3. The 'Layperson Trigger Additions' sheet's own phrases used as matchers (5 shelf Acts) ==")
wb = openpyxl.load_workbook(os.path.join(ROOT, "review_data/ruler/inputs/2026-10-12_trigger_workbook_with_spec_v2.xlsx")); ws = wb["Layperson Trigger Additions"]
ROW = {"pc_act_1988": "Prevention of Corruption", "pocso_act_2012": "Protection of Children from Sexual", "uapa_1967": "Unlawful Activities", "pmla_2002": "Prevention of Money", "sc_st_act_1989": "Scheduled Castes and Scheduled Tribes"}
phr = {}
for r in range(5, 28):
    a = ws.cell(r, 1).value
    for k, v in ROW.items():
        if a and v in a: phr[k] = ([p.strip() for p in (ws.cell(r, 2).value or "").split(";") if p.strip()], [p.strip() for p in (ws.cell(r, 3).value or "").split(";") if p.strip()])
SW = set("a an the of to in on at for with by from and or but is are was were be been it its i me my we our you your he him his she her they them their this that these those as if so do does did can could will would should have has had not no any all some what which who whom when where why how than then there here into out up about over after before under again also just only very more most such".split())
def stem(w):
    w = w.lower()
    for s in ("ing", "ed", "es", "s"):
        if w.endswith(s) and len(w) - len(s) >= 3: return w[:-len(s)]
    return w
def toks(s): return {stem(w) for w in re.findall(r"[a-zA-Z0-9]+", s) if w.lower() not in SW and len(w) > 1}
def lay(q, th, broad):
    qt = toks(q); return {k for k, (hi, lo) in phr.items() if any(toks(p) and len(toks(p) & qt) / len(toks(p)) >= th for p in hi + (lo if broad else []))}
for th in (1.0, 0.67, 0.5):
    for broad in (False, True):
        ok = sum(q["act_key"] in lay(q["q"], th, broad) for q in Q); wr = sum(bool(lay(q["q"], th, broad) - {q["act_key"]}) for q in Q)
        print(f"   phrase words present >= {th:.0%}; {'high-signal + broad' if broad else 'high-signal only    '}: right Act {ok}/75 = {ok/75:.0%}, wrong-Act fires {wr}")
print("   owner's sentence at 50% overlap fires:", sorted({(k) for k in lay("My son works as a clerk in a government office. He was arrested yesterday for taking money from a contractor.", 0.5, True)}), "(PMLA fires on the word 'money')")

print("\n== 4. Act vocabulary derived from the Acts' own text (distinctive vs BNS/BNSS and the other four Acts); first terms per Act ==")
for k, v in derive_vocabulary().items(): print(f"   {k}: {len(v)} terms; " + "; ".join(v[:14]))
print("\nDone. Caveats: the 75 questions are Claude's; the vocabulary pruning was done knowing some misses; no AI router tested (no Anthropic key in the sandbox).")
