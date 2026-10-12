#!/usr/bin/env python3
"""Tests Mr. Advocate's regex audit (Legal_Act_Boost_Regex_Audit_and_Final_Anchors.docx, 2026-10-12) in code: do the patterns compile in Python, what do they match in our index, do they fire on the 30 used questions,
and do they behave on a small hand-made positive/negative suite. No Voyage calls, no spend. PRIVATE. The 30 questions are used up: this is a dev check, not evidence that the boost works."""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools"))
sys.path.insert(0, ROOT)
import pool_runner as PR
import sci_index as si

TXT = open("/tmp/claude-0/advocate_doc.txt", encoding="utf-8").read().split("\n")
ACTS = ["PWDVA", "NDPS", "POCSO", "SC/ST", "NI Act", "PMLA", "UAPA", "DPA", "JJ Act", "PC Act", "Arms Act", "IT Act", "MV Act"]
TITLES = ["Protection of Women from Domestic Violence Act, 2005", "Narcotic Drugs and Psychotropic Substances Act, 1985", "Protection of Children from Sexual Offences Act, 2012", "Scheduled Castes and Scheduled Tribes (Prevention of Atrocities) Act, 1989",
          "Negotiable Instruments Act, 1881", "Prevention of Money Laundering Act, 2002", "Unlawful Activities (Prevention) Act, 1967", "Dowry Prohibition Act, 1961", "Juvenile Justice (Care and Protection of Children) Act, 2015",
          "Prevention of Corruption Act, 1988", "Arms Act, 1959", "Information Technology Act, 2000", "Motor Vehicles Act, 1988"]
his = {}
for i, ln in enumerate(TXT):
    if ln.startswith("Risk rating:"):
        title = TXT[i - 1].strip()
        k = next((a for a, t in zip(ACTS, TITLES) if title.startswith(t.split(",")[0].split(" (")[0][:30])), None)
        if k is None:
            continue
        for j in range(i + 1, min(i + 12, len(TXT))):
            if TXT[j].startswith("Risk rating:"):
                break
            if TXT[j].startswith("Recommended question-side anchor"):
                his.setdefault(k, {})["q"] = TXT[j + 1].strip()
            if TXT[j].startswith("Recommended passage-side strong marker"):
                his.setdefault(k, {})["p"] = TXT[j + 1].strip()
for _a in ACTS:
    print("  parsed", _a, "| q:", his.get(_a, {}).get("q", "")[:60], "| p:", his.get(_a, {}).get("p", "")[:60])
print("Acts parsed:", len(his), "| with both patterns:", sum(1 for v in his.values() if "q" in v and "p" in v))
comp = {}
print("\n1. DO THE PATTERNS COMPILE IN PYTHON?")
for a in ACTS:
    for side in ("q", "p"):
        pat = his.get(a, {}).get(side)
        if pat is None:
            print(f"   {a} {side}: MISSING"); continue
        try:
            comp[(a, side)] = re.compile(pat)
            print(f"   {a:9} {side}: ok")
        except re.error as e:
            print(f"   {a:9} {side}: COMPILE ERROR: {e}")

# my own markers/anchors (from the 2026-10-11 review) for comparison
S = lambda p: re.compile(p, re.I)
C = lambda p: re.compile(p)
MINE_P = {
    "PWDVA": [S(r"protection of women from domestic violence act"), C(r"\bPWDVA\b|\bPWDV Act\b|\bD\.?V\.? Act\b"), S(r"section\s+(12|18|19|20|22|23)\s+of\s+the\s+(D\.?V\.?|domestic violence)")],
    "NDPS": [C(r"\bNDPS\b|\bN\.D\.P\.S"), S(r"narcotic drugs and psychotropic substances act")],
    "POCSO": [C(r"\bPOCSO\b|\bP\.O\.C\.S\.O"), S(r"protection of children from sexual offences")],
    "SC/ST": [C(r"\bSC\s*/\s*ST\b|\bSC\s*&\s*ST\b"), S(r"prevention of atrocities\)? act")],
    "NI Act": [S(r"negotiable instruments act"), C(r"\bN\.?\s?I\.? Act\b")],
    "PMLA": [C(r"\bPMLA\b"), S(r"prevention of money[- ]laundering act")],
    "UAPA": [C(r"\bUAPA\b"), S(r"unlawful activities \(prevention\) act")],
    "DPA": [S(r"dowry prohibition act")],
    "JJ Act": [S(r"juvenile justice \(care and protection of children\) act"), C(r"\bJJ Act\b|\bJJB\b"), S(r"juvenile justice board|child welfare committee")],
    "PC Act": [S(r"prevention of corruption act"), C(r"\bPC Act\b")],
    "Arms Act": [S(r"\barms act\b")],
    "IT Act": [S(r"information technology act"), C(r"\bIT Act\b")],
    "MV Act": [S(r"motor vehicles act"), C(r"\bMV Act\b")],
}
mine_p = lambda a, t: any(p.search(t) for p in MINE_P[a])
MINE_Q = {
    "PWDVA": [r"domestic (violence|abuse)", r"\bDV Act\b", r"\bPWDVA\b", r"shared household", r"(protection|residence) order", r"(threw|thrown|throw|throws|throwing|kicked|drove|driven) (me|her|us) out of (the |my |our )?(marital |matrimonial )?(house|home)", r"(husband|in-?laws?|mother-in-law) (hits?|beats?|beat|abuse[sd]?|tortures?|harass\w*) (me|her)"],
    "NDPS": [r"\bNDPS\b", r"narcotic", r"\b(ganja|charas|heroin|cocaine|MDMA|methamphetamine|opium|smack)\b", r"\bNCB\b", r"(commercial|intermediate|small) quantity", r"psychotropic"],
    "POCSO": [r"\bPOCSO\b", r"(child|minor|daughter|son|girl|boy|student)\b.{0,80}(touch|molest|sexual|rape|assault|abus)", r"(touch|molest|sexual|rape|assault|abus).{0,80}\b(child|minor|daughter|girl|boy|under[- ]?(18|eighteen)|\d{1,2}[- ]year[- ]old)"],
    "SC/ST": [r"\bSC\s*/\s*ST\b", r"atrocit(y|ies)", r"caste (name|abuse|slur|insult)", r"because of (my |his |her )?caste", r"\bdalit\b|\badivasi\b", r"scheduled (caste|tribe)"],
    "NI Act": [r"cheque.{0,40}(bounce|bounced|dishonou?r\w*|returned|unpaid)", r"(bounce|bounced|dishonou?r\w*).{0,40}cheque", r"section 138", r"\bNI Act\b|negotiable instruments"],
    "PMLA": [r"\bPMLA\b", r"money[- ]laundering", r"proceeds of crime", r"\bED\b.{0,60}(attach|froze|arrest|summon|question|case)", r"enforcement directorate"],
    "UAPA": [r"\bUAPA\b", r"anti[- ]terror", r"terror(ist|ism)? (act|funding|case|activity)", r"banned (organi[sz]ation|group)", r"unlawful activities"],
    "DPA": [r"\bdowry\b"], "JJ Act": [r"\bjuvenile", r"child in conflict with law", r"\bJJB\b", r"\b(15|16|17)[- ]year[- ]old.{0,60}(arrest|accused|police|theft|fight|crime)", r"minor.{0,40}(arrested|accused|in custody)"],
    "PC Act": [r"\bbribe", r"illegal gratification", r"prevention of corruption", r"\bPC Act\b", r"disproportionate assets", r"(public servant|government officer|official).{0,60}(took|asked for|demand\w*) (money|a bribe)"],
    "Arms Act": [r"\bArms Act\b", r"\b(firearm|pistol|revolver|rifle)\b", r"country[- ]made (pistol|gun)", r"\b(cartridges?|ammunition)\b"],
    "IT Act": [r"\bIT Act\b", r"information technology act", r"\bcyber", r"\bhack(ed|ing)\b", r"\bOTP\b", r"\bUPI\b", r"online (scam|fraud)", r"phishing", r"morphed", r"fake profile", r"section 66[A-D]?\b"],
    "MV Act": [r"motor vehicles act", r"drunk(en)? driving", r"rash (and negligent )?driving", r"hit[- ]and[- ]run", r"driving without (a )?licen[cs]e", r"dangerous driving"],
}
case_sens = ("ED", "OTP", "UPI", "NCB", "MDMA")
MINE_Q = {a: [re.compile(p) if any(c in p for c in case_sens) else re.compile(p, re.I) for p in ps] for a, ps in MINE_Q.items()}
mine_q = lambda a, t: any(p.search(t) for p in MINE_Q[a])

# 2. index
head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, _, _ = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
N = len(metas)
print(f"\n2. WHAT THE PASSAGE-SIDE MARKERS MATCH IN THE INDEX ({N:,} passages). 'his' = Mr. Advocate's, 'mine' = the 2026-10-11 draft. J3 = judgments with 3 or more marked passages")
hits = {a: {"his": collections.Counter(), "mine": collections.Counter()} for a in ACTS}
dis = {a: {"his_only": [], "mine_only": []} for a in ACTS}
for idx, m in enumerate(metas):
    t = m["text"]
    for a in ACTS:
        h = bool(comp.get((a, "p")) and comp[(a, "p")].search(t))
        mi = mine_p(a, t)
        if h:
            hits[a]["his"][m["doc"]] += 1
        if mi:
            hits[a]["mine"][m["doc"]] += 1
        if h and not mi and len(dis[a]["his_only"]) < 400:
            dis[a]["his_only"].append(idx)
        if mi and not h and len(dis[a]["mine_only"]) < 400:
            dis[a]["mine_only"].append(idx)
print(f"{'Act':9} {'his passages':>13} {'his J3':>7} | {'mine passages':>14} {'mine J3':>8} | {'only his (J3 docs)':>19} {'only mine (J3 docs)':>20}")
summary = {}
for a in ACTS:
    hp, mp = sum(hits[a]["his"].values()), sum(hits[a]["mine"].values())
    hj = {d for d, v in hits[a]["his"].items() if v >= 3}; mj = {d for d, v in hits[a]["mine"].items() if v >= 3}
    summary[a] = {"his_passages": hp, "his_J3": len(hj), "mine_passages": mp, "mine_J3": len(mj), "J3_only_his": len(hj - mj), "J3_only_mine": len(mj - hj)}
    print(f"{a:9} {hp:13,} {len(hj):7,} | {mp:14,} {len(mj):8,} | {len(hj - mj):19,} {len(mj - hj):20,}")

# 3. snippets of disagreement (what each side finds that the other does not)
import random
rnd = random.Random(7)
def snip(idx, pat):
    t = metas[idx]["text"]
    mm = pat.search(t) if pat else None
    s = max(0, (mm.start() if mm else 0) - 60)
    return re.sub(r"\s+", " ", t[s:s + 200]), metas[idx]["doc"]
print("\n3. WHAT ONLY HIS MARKER FINDS (3 random passages per Act) AND WHAT ONLY MINE FINDS (2 per Act)")
for a in ACTS:
    for tag, n in (("his_only", 3), ("mine_only", 2)):
        pool = dis[a][tag]
        for idx in rnd.sample(pool, min(n, len(pool))):
            sn, d = snip(idx, comp.get((a, "p")) if tag == "his_only" else None)
            print(f"   [{a} {tag}] doc {d}: ...{sn}")

# 4. questions
tun = json.load(open(os.path.join(ROOT, "review_results/2026-10-10_real30_rerank_test_pack_v2/pool_with_rerank_arms.json"), encoding="utf-8"))["questions"]
sealed = json.load(open(os.path.join(ROOT, "review_results/2026-10-10_sealed_run/pool.json"), encoding="utf-8"))["questions"]
qs = {q["qid"]: q["question"] for q in tun + sealed}
print("\n4. WHICH ACTS FIRE ON THE 30 USED QUESTIONS (his question-side vs mine)")
cnt_h, cnt_m = collections.Counter(), collections.Counter()
for qid in sorted(qs):
    fh = [a for a in ACTS if comp.get((a, "q")) and comp[(a, "q")].search(qs[qid])]
    fm = [a for a in ACTS if mine_q(a, qs[qid])]
    for a in fh: cnt_h[a] += 1
    for a in fm: cnt_m[a] += 1
    if fh or fm:
        print(f"   {qid}: his {fh or '-'} | mine {fm or '-'} | {qs[qid][:90]}")
print("   totals: his fires on", sum(1 for q in qs if any(comp.get((a, 'q')) and comp[(a, 'q')].search(qs[q]) for a in ACTS)), "of 30; mine on", sum(1 for q in qs if any(mine_q(a, qs[q]) for a in ACTS)), "of 30")

# 5. hand-made suite
suite = [
    ("my cheque bounced last month", "NI Act", True), ("the cheque was dishonoured and I sent a statutory notice", "NI Act", True), ("he gave me a cheque, it bounced", "NI Act", True), ("Section 138 NI Act complaint limitation", "NI Act", True),
    ("Is a statement under Section 67 NDPS admissible as confession?", "NDPS", True), ("Is a statement under Section 67 NDPS admissible as confession?", "IT Act", False), ("section 67 of the act statement to the officer", "IT Act", False),
    ("police found ganja in my cousin's bag", "NDPS", True), ("forensic report found cocaine traces in the deceased", "NDPS", False),
    ("My husband beats me and wants me out of the house, what can I do", "PWDVA", True), ("can I file a domestic violence case after three years", "PWDVA", True), ("my husband beats me, can I file a case under Section 498A", "PWDVA", False),
    ("a man touched my 12-year-old daughter's chest", "POCSO", True), ("POCSO Act bail for a 19 year old", "POCSO", True), ("rape of an adult woman, consent defence", "POCSO", False),
    ("ED attached my house, is this under PMLA", "PMLA", True), ("ED froze my bank account", "PMLA", True), ("a government officer asked me for a bribe", "PC Act", True), ("is previous sanction required under Section 19 of the PC Act", "PC Act", True),
    ("someone took my OTP and emptied my account", "IT Act", True), ("police found a country-made pistol in my car", "Arms Act", True), ("drunk driving accident death", "MV Act", True),
    ("an advocate called me a caste name in front of people", "SC/ST", True), ("SC/ST Act anticipatory bail", "SC/ST", True), ("dowry demanded by in-laws after marriage", "DPA", True), ("my 16 year old son arrested for theft", "JJ Act", True),
]
print("\n5. HAND-MADE SUITE (expected fire = True/False). Result per side: ok / MISS (should fire, did not) / FALSE (should not fire, did)")
tot = collections.Counter()
for text, act, exp in suite:
    h = bool(comp.get((act, "q")) and comp[(act, "q")].search(text)); m = mine_q(act, text)
    rh = "ok" if h == exp else ("MISS" if exp else "FALSE"); rm = "ok" if m == exp else ("MISS" if exp else "FALSE")
    tot[("his", rh)] += 1; tot[("mine", rm)] += 1
    print(f"   {act:8} exp {str(exp):5} his {rh:5} mine {rm:5} | {text}")
print("   totals:", dict(tot))

# 6. specific suspected defects
print("\n6. SPECIFIC CHECKS")
def count(rx, flags=re.I):
    r = re.compile(rx, flags); return sum(1 for m in metas if r.search(m["text"]))
print("   'Prevention of Money-Laundering Act' (hyphen) passages:", count(r"prevention of money-laundering act"), "| without hyphen:", count(r"prevention of money laundering act"))
print("   'Scheduled Castes and the Scheduled Tribes (Prevention of Atrocities) Act':", count(r"scheduled castes and the scheduled tribes \(prevention of atrocities\)"), "| without 'the':", count(r"scheduled castes and scheduled tribes \(prevention of atrocities\)"))
print("   'Domestic Violence Act' bare / 'Protection of Women from Domestic Violence Act':", count(r"domestic violence act"), "/", count(r"protection of women from domestic violence act"))
tmap = PR.titles([PR.DEFAULT_INDEX], metas, None)
docs = {m["doc"] for m in metas}
for key in ("HITESH VERMA", "NANJUNDASWAMY", "WATALI", "VIJAY MADANLAL"):
    found = [(d, str(tmap(d))[:80]) for d in docs if key in str(tmap(d)).upper()]
    print(f"   title containing {key}: {len(found)}", found[:2])
json.dump({"summary": summary}, open(os.path.join(HERE, "advocate_regex_test.json"), "w"), indent=1)
