#!/usr/bin/env python3
"""Second part of the trigger-workbook review. (a) A literal question-side matcher (anchors written by hand from the workbook's high-signal phrases) for the 13 Acts that have enough material in the index,
run on the 30 used questions. (b) How much of a "labelled" judgment does a passage-level marker actually mark? (c) A semantic alternative: embed the workbook's phrases once, route each question to the Act whose
phrase is closest. Spend: well under one cent. PRIVATE, diagnosis only; the 30 questions are used up."""
import collections
import json
import os
import re
import sys

import numpy as np
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools"))
sys.path.insert(0, ROOT)
import pool_runner as PR
import sci_index as si

I = re.I
ANCH = {   # question-side literal anchors; case-insensitive unless marked
    "PWDVA": [r"domestic (violence|abuse)", r"\bDV Act\b", r"\bPWDVA\b", r"shared household", r"(protection|residence) order", r"(threw|thrown|throw|throws|throwing|kicked|drove|driven) (me|her|us) out of (the |my |our )?(marital |matrimonial )?(house|home)", r"(husband|in-?laws?|mother-in-law) (hits?|beats?|beat|abuse[sd]?|tortures?|harass\w*) (me|her)"],
    "NDPS": [r"\bNDPS\b", r"narcotic", r"\b(ganja|charas|heroin|cocaine|MDMA|methamphetamine|opium|smack)\b", r"\bNCB\b", r"(commercial|intermediate|small) quantity", r"psychotropic"],
    "POCSO": [r"\bPOCSO\b", r"(child|minor|daughter|son|girl|boy|student)\b.{0,80}(touch|molest|sexual|rape|assault|abus)", r"(touch|molest|sexual|rape|assault|abus).{0,80}\b(child|minor|daughter|girl|boy|under[- ]?(18|eighteen)|\d{1,2}[- ]year[- ]old)"],
    "SC/ST": [r"\bSC\s*/\s*ST\b", r"atrocit(y|ies)", r"caste (name|abuse|slur|insult)", r"because of (my |his |her )?caste", r"\bdalit\b|\badivasi\b", r"scheduled (caste|tribe)"],
    "NI Act": [r"cheque.{0,40}(bounce|bounced|dishonou?r\w*|returned|unpaid)", r"(bounce|bounced|dishonou?r\w*).{0,40}cheque", r"section 138", r"\bNI Act\b|negotiable instruments"],
    "PMLA": [r"\bPMLA\b", r"money[- ]laundering", r"proceeds of crime", r"\bED\b.{0,60}(attach|froze|arrest|summon|question|case)", r"enforcement directorate"],
    "UAPA": [r"\bUAPA\b", r"anti[- ]terror", r"terror(ist|ism)? (act|funding|case|activity)", r"banned (organi[sz]ation|group)", r"unlawful activities"],
    "DPA": [r"\bdowry\b"],
    "JJ Act": [r"\bjuvenile", r"child in conflict with law", r"\bJJB\b", r"\b(15|16|17)[- ]year[- ]old.{0,60}(arrest|accused|police|theft|fight|crime)", r"minor.{0,40}(arrested|accused|in custody)"],
    "PC Act": [r"\bbribe", r"illegal gratification", r"prevention of corruption", r"\bPC Act\b", r"disproportionate assets", r"(public servant|government officer|official).{0,60}(took|asked for|demand\w*) (money|a bribe)"],
    "Arms Act": [r"\bArms Act\b", r"\b(firearm|pistol|revolver|rifle)\b", r"country[- ]made (pistol|gun)", r"\b(cartridges?|ammunition)\b"],
    "IT Act": [r"\bIT Act\b", r"information technology act", r"\bcyber", r"\bhack(ed|ing)\b", r"\bOTP\b", r"\bUPI\b", r"online (scam|fraud)", r"phishing", r"morphed", r"fake profile", r"section 66[A-D]?\b"],
    "MV Act": [r"motor vehicles act", r"drunk(en)? driving", r"rash (and negligent )?driving", r"hit[- ]and[- ]run", r"driving without (a )?licen[cs]e", r"dangerous driving"],
}
ANCH = {a: [re.compile(p, I) if "ED" not in p and "OTP" not in p and "UPI" not in p and "NCB" not in p and "MDMA" not in p else re.compile(p) for p in ps] for a, ps in ANCH.items()}

tun = json.load(open(os.path.join(ROOT, "review_results/2026-10-10_real30_rerank_test_pack_v2/pool_with_rerank_arms.json"), encoding="utf-8"))["questions"]
sealed = json.load(open(os.path.join(ROOT, "review_results/2026-10-10_sealed_run/pool.json"), encoding="utf-8"))["questions"]
qs = {q["qid"]: q["question"] for q in tun + sealed}
print("(a) LITERAL MATCHER on the 30 used questions (Acts kept: 13)")
fired = {}
for qid in sorted(qs):
    f = {a: [p.pattern[:38] for p in ps if p.search(qs[qid])][:2] for a, ps in ANCH.items()}
    f = {a: v for a, v in f.items() if v}
    fired[qid] = f
    print(f"{qid}: {qs[qid][:118]}\n      -> {f if f else '(no Act)'}")
cnt = collections.Counter(a for f in fired.values() for a in f)
print("\nfired on (of 30):", dict(cnt.most_common()), "| questions with no Act:", sum(1 for f in fired.values() if not f))

# (b) share of a labelled judgment's passages that a passage-level marker marks
sys.path.insert(0, HERE)
head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, _, _ = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
MARK = {"PWDVA": r"protection of women from domestic violence act|\bPWDVA\b|\bD\.?V\.? Act\b", "NDPS": r"\bNDPS\b|narcotic drugs and psychotropic substances act", "POCSO": r"\bPOCSO\b|protection of children from sexual offences",
        "SC/ST": r"\bSC\s*/\s*ST\b|prevention of atrocities", "NI Act": r"negotiable instruments act|\bN\.?\s?I\.? Act\b", "PMLA": r"\bPMLA\b|prevention of money[- ]laundering act", "UAPA": r"\bUAPA\b|unlawful activities \(prevention\) act",
        "DPA": r"dowry prohibition act", "PC Act": r"prevention of corruption act|\bPC Act\b", "Arms Act": r"\barms act\b"}
tot = collections.Counter(m["doc"] for m in metas)
print("\n(b) For judgments with 3 or more passages carrying the Act's strong marker: what share of their passages carries it?")
for a, pat in MARK.items():
    rx = re.compile(pat, I if a not in ("PWDVA", "POCSO", "UAPA", "PMLA") else 0) if False else re.compile(pat, I)
    per = collections.Counter(m["doc"] for m in metas if rx.search(m["text"]))
    lab = [d for d, v in per.items() if v >= 3]
    shares = [per[d] / tot[d] for d in lab]
    print(f"  {a:9} labelled judgments {len(lab):4}; mean share of their passages marked {100 * np.mean(shares):5.1f}%; judgments where under 10% are marked: {sum(1 for s in shares if s < 0.10)} of {len(lab)}")

# (c) semantic routing: embed the workbook's phrases once
wb = openpyxl.load_workbook(os.path.join(ROOT, "review_data/ruler/inputs/2026-10-11_owner_trigger_workbook.xlsx"), data_only=True)
main = [r for r in wb["Revised Trigger Map"].iter_rows(min_row=3, values_only=True) if r[0] and r[1] and not str(r[0]).startswith("Act / statute")]
lay = {r[0]: r for r in wb["Layperson Trigger Additions"].iter_rows(min_row=3, values_only=True) if r[0] and r[1] and not str(r[0]).startswith("Act / statute")}
SHORT = ["PWDVA", "NDPS", "POCSO", "SC/ST", "NI Act", "PMLA", "UAPA", "DPA", "JJ Act", "BNS/IPC", "BNSS/CrPC", "BSA/IEA", "PC Act", "Arms Act", "IT Act", "ITPA", "PCMA", "PCR Act", "MV Act", "PDPP", "Companies Act", "CGST", "Muslim Women Act"]
KEEP = list(ANCH)
bank = []
for a, row in zip(SHORT, main):
    if a not in KEEP:
        continue
    lr = lay.get(row[0])
    for cell in ([row[1]] + ([lr[1]] if lr else [])):
        for p in re.split(r";|\n", cell or ""):
            p = re.sub(r"\(.*?\)", "", p).strip()
            if p:
                bank.append((a, p))
client = si.make_client()
def emb(texts):
    out = []
    for i in range(0, len(texts), 128):
        r = client.embed(texts[i:i + 128], model="voyage-law-2", input_type="query")
        out += [np.asarray(e, dtype=np.float32) for e in r.embeddings]
    return np.vstack([v / (np.linalg.norm(v) or 1) for v in out])
B = emb([p for _, p in bank]); Q = emb([qs[q] for q in sorted(qs)])
sims = Q @ B.T
print(f"\n(c) SEMANTIC ROUTING: {len(bank)} phrases of 13 Acts embedded once. For each question: the two closest Acts (max cosine over the Act's phrases)")
for i, qid in enumerate(sorted(qs)):
    best = {}
    for j, (a, _) in enumerate(bank):
        best[a] = max(best.get(a, -1), float(sims[i, j]))
    top = sorted(best.items(), key=lambda x: -x[1])[:2]
    print(f"{qid}: " + ", ".join(f"{a} {s:.2f}" for a, s in top) + f"   | literal: {list(fired[qid]) or '-'}")
