"""
test_act_directory_controls.py -- the Act Directory (site_patch/act_directory.py, a copy of Recourse's) run over every question this repository holds: the situation exam, the criminal and trap exams,
the owner's 30 real questions, the question writer's N01-N30, the ruler questions and every pool run (193 distinct questions on 2026-10-16). Precision first: no match is better than a wrong one.

What it asserts: every question that draws a notice is in GOLDEN below (each was read by Claude on 2026-10-16 and is right: the question names or clearly describes that Act), and every GOLDEN entry is still
found. A NEW question that draws a notice fails this test until someone reads it and adds it to GOLDEN, which is the point: a wrong notice is noise. It also prints the recall on the six situation questions
that are about Acts the library does not hold (S01, S02, S23, S24 corruption; S03, S04 TADA). Run: python -X utf8 test_act_directory_controls.py
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "site_patch"))
os.environ.pop("ACT_DIRECTORY", None)
import act_directory as AD

FAILURES = []


def check(cond, msg):
    print(f"[{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        FAILURES.append(msg)


GOLDEN = {
    "My corruption case has been in the trial court for 9 years since the c": ["pc_act_1988"],
    "My brother was convicted of sedition by a TADA Designated Court and gi": ["tada_1987"],
    "The High Court stayed my corruption trial more than six months ago and": ["pc_act_1988"],
    "Whether a certificate under Section 63 BSA (formerly Section 65B Evide": ["bsa_2023", "evidence_act_1872"],
    "Is a statement recorded by an officer under Section 67 of the NDPS Act": ["evidence_act_1872"],
    "A man touched my 12-year-old daughter's chest over her clothes. Someon": ["pocso_act_2012"],
    "Whether anticipatory bail under Section 438 CrPC is maintainable in a ": ["sc_st_act_1989"],
    "Whether, in a case under the UAPA investigated by the State police, an": ["uapa_1967"],
    "After a fight over a drain, our neighbour has filed a case saying my f": ["sc_st_act_1989"],
    "My son has been booked in a POCSO case. Police say his Aadhaar shows h": ["pocso_act_2012", "jj_act_2015"],
    "In 2023, a drunk driver drove his SUV onto the footpath at night and k": ["mv_act_1988"],
    "Whether a dying declaration recorded by a Magistrate under Section 32 ": ["evidence_act_1872"],
    "Whether a Special Court under the PMLA must give the proposed accused ": ["pmla_2002"],
    "My uncle is a clerk in the revenue office and was caught in an anti-co": ["pc_act_1988"],
}

files = sorted(set(glob.glob(os.path.join(HERE, "register_exam", "**", "questions.jsonl"), recursive=True) + glob.glob(os.path.join(HERE, "review_results", "**", "questions.jsonl"), recursive=True)))
questions = {}
for f in files:
    for line in open(f, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        q = next((d[k] for k in ("question", "text", "q", "query") if isinstance(d.get(k), str)), None)
        if q:
            questions.setdefault(q.strip(), os.path.relpath(f, HERE))
check(len(files) >= 10 and len(questions) >= 150, f"the question files are found ({len(files)} files, {len(questions)} distinct questions)")

hits = {}
for q, f in questions.items():
    ids = [a["id"] for a in AD.detect(q)]
    if ids:
        hits[q[:70]] = ids
unexpected = {k: v for k, v in hits.items() if k not in GOLDEN}
changed = {k: (v, hits.get(k)) for k, v in GOLDEN.items() if hits.get(k) != v}
check(not unexpected, f"no question draws a notice that has not been read and approved ({list(unexpected.items())[:3]})")
check(not changed, f"every approved question still draws exactly the approved Acts ({list(changed.items())[:3]})")
check(len(hits) == len(GOLDEN) == 14, f"14 distinct questions draw a notice out of {len(questions)}")

# the six situation questions about Acts the library does not hold
sit = [json.loads(l) for l in open(os.path.join(HERE, "register_exam", "situation", "questions.jsonl"), encoding="utf-8") if l.strip()]
about = {"S01": "pc_act_1988", "S02": "pc_act_1988", "S03": "tada_1987", "S04": "tada_1987", "S23": "pc_act_1988", "S24": "pc_act_1988"}
found = {r["id"]: [a["id"] for a in AD.detect(r["question"])] for r in sit}
check(all(found[i] == [aid] for i, aid in about.items()), f"recall: all six situation questions about uncovered Acts get the right Act ({ {i: found[i] for i in about} })")
check(all(found[i] == [] for i in found if i not in about), "precision: the other 18 situation questions draw nothing")
print(f"\nrecall on the six: 6 of 6; notices drawn across all {len(questions)} questions: {len(hits)}")

print("\nALL PASSED" if not FAILURES else f"\n{len(FAILURES)} FAILED: {FAILURES}")
sys.exit(1 if FAILURES else 0)
