"""Tests for review_tools/machine_spec_v2.py. Run: python review_tools/test_machine_spec_v2.py
The cases were written before the first run of the v2 patterns: positives, hard negatives, twin pairs, and a regression case for each defect found in Mr. Advocate's audit. They are the author's cases (Claude's), not a lawyer's."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import machine_spec_v2 as S

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


check("every pattern compiles", len(S.COMPILED) == 13 and all(len(c["passage"]) and len(c["N1"]) and len(c["N2_extra"]) for c in S.COMPILED.values()))
# (question, act, N1 fires, N2 fires)
Q = [
    # NI Act
    ("my cheque bounced last month", "NI Act", True, True), ("he gave me a cheque, it bounced", "NI Act", True, True), ("the cheque was dishonoured and I sent a statutory notice", "NI Act", True, True),
    ("Section 138 NI Act complaint limitation", "NI Act", True, True), ("the payee presented a dishonoured cheque at a branch in another city", "NI Act", True, True), ("cheque forged by my employee, bank paid it", "NI Act", False, False),
    # NDPS
    ("Is a statement under Section 67 NDPS admissible as confession?", "NDPS", True, True), ("Is a statement under Section 67 NDPS admissible as confession?", "IT Act", False, False), ("section 67 of the act statement to the officer", "IT Act", False, False),
    ("police found ganja in my cousin's bag", "NDPS", False, True), ("forensic report found cocaine traces in the deceased", "NDPS", False, False), ("NCB made my cousin sign a statement, the ganja was his", "NDPS", False, True),
    ("whether commercial quantity bars bail", "NDPS", True, True), ("my son was prescribed codeine syrup by a doctor", "NDPS", False, False),
    # PWDVA and its twin
    ("can I file a domestic violence case after three years", "PWDVA", True, True), ("My husband beats me and wants me out of the house, what can I do", "PWDVA", False, True),
    ("my husband beats me, can I file a case under Section 498A", "PWDVA", False, False), ("my husband threw me out of the house, can I claim a residence order under the DV Act", "PWDVA", True, True),
    ("my husband's lawyer says shared household means only his house", "PWDVA", False, False), ("matrimonial dispute about the marital home and a protection order against the neighbour", "PWDVA", False, False),
    # POCSO and its twin
    ("a man touched my 12-year-old daughter's chest", "POCSO", False, True), ("POCSO Act bail for a 19 year old", "POCSO", True, True), ("rape of an adult woman, consent defence", "POCSO", False, False),
    ("my daughter, 26, says her boss molested her", "POCSO", False, False), ("penetrative sexual assault on a girl under 18", "POCSO", True, True), ("minor dispute over land between brothers", "POCSO", False, False),
    # SC/ST
    ("an advocate called me a caste name in front of people", "SC/ST", False, True), ("SC/ST Act anticipatory bail", "SC/ST", True, True), ("reservation certificate dispute for a scheduled caste candidate", "SC/ST", False, True),
    ("Scheduled Castes and the Scheduled Tribes (Prevention of Atrocities) Act bail", "SC/ST", True, True), ("insult and abuse by a neighbour over a boundary", "SC/ST", False, False),
    # PMLA
    ("ED attached my house, is this under PMLA", "PMLA", True, True), ("ED froze my bank account", "PMLA", False, True), ("under the Prevention of Money-Laundering Act, bail section 45", "PMLA", True, True),
    ("the bank froze my account for KYC", "PMLA", False, False), ("proceeds of crime and provisional attachment", "PMLA", True, True),
    # UAPA
    ("bail under Section 43D(5) UAPA", "UAPA", True, True), ("booked under the anti-terror law, linked to a banned group", "UAPA", False, True), ("terror attack news analysis", "UAPA", False, False),
    # DPA
    ("dowry demanded by in-laws after marriage", "DPA", True, True), ("complaint under the Dowry Prohibition Act for a dowry demand", "DPA", True, True), ("gifts at the wedding were voluntary", "DPA", False, False),
    # JJ Act
    ("my 16 year old son arrested for theft", "JJ Act", False, True), ("claim of juvenility before the Juvenile Justice Board", "JJ Act", True, True), ("my 16-year-old daughter was touched by her teacher and we went to the police", "JJ Act", False, False),
    # PC Act
    ("a government officer asked me for a bribe", "PC Act", False, True), ("is previous sanction required under Section 19 of the PC Act", "PC Act", True, True), ("my landlord took a deposit from me", "PC Act", False, False),
    ("disproportionate assets of a public servant", "PC Act", True, True),
    # Arms Act
    ("police found a country-made pistol in my car", "Arms Act", False, True), ("my neighbour threatens people with a knife", "Arms Act", False, False), ("unlicensed firearm and Arms Act section 25", "Arms Act", True, True),
    # IT Act
    ("someone took my OTP and emptied my account", "IT Act", False, True), ("Information Technology Act section 66C identity theft online", "IT Act", True, True), ("my IT department is outsourcing work", "IT Act", False, False),
    ("whoever uses a password online without consent, Section 66C", "IT Act", True, True),
    # additions from Mr. Advocate's second review (plain-language tier only)
    ("Can my in-laws evict me from their house?", "PWDVA", False, True), ("He broke the court's protection order. What can I do?", "PWDVA", False, True), ("an abusive husband keeps threatening me", "PWDVA", False, True),
    ("we are divorcing by mutual consent and sharing the marital home papers", "PWDVA", False, False), ("mental cruelty as a ground for divorce", "PWDVA", False, False),
    ("What happens if police find drugs in my bag?", "NDPS", False, True), ("I was caught with illegal tablets", "NDPS", False, True), ("the doctor gave me drugs for my fever and police asked nothing", "NDPS", False, False),
    ("The government banned our organisation", "UAPA", False, True), ("I was arrested for supporting a separatist movement", "UAPA", False, True), ("Police searched my body without giving me a choice", "NDPS", False, False),
    # MV Act
    ("drunk driving accident death", "MV Act", True, True), ("rash and negligent driving by a truck driver", "MV Act", False, True), ("I want to buy a second-hand car", "MV Act", False, False),
]
bad = []
for text, act, e1, e2 in Q:
    r1 = act in S.question_acts(text, "N1"); r2 = act in S.question_acts(text, "N2")
    if r1 != e1 or r2 != e2:
        bad.append((act, text[:60], "N1", r1, e1, "N2", r2, e2))
check(f"question-side cases ({len(Q)} cases, N1 and N2 each)", not bad, bad)
# N2 contains N1: whatever fires in N1 fires in N2
allq = [t for t, *_ in Q]
check("N2 fires wherever N1 fires (N2 is a superset)", all(set(S.question_acts(t, "N1")) <= set(S.question_acts(t, "N2")) for t in allq))
# regression cases for the defects found in Mr. Advocate's audit
P = [
    ("under the Prevention of Money-Laundering Act, 2002", "PMLA", True), ("under the Prevention of Money Laundering Act, 2002", "PMLA", True),
    ("the Scheduled Castes and the Scheduled Tribes (Prevention of Atrocities) Act, 1989 applies", "SC/ST", True), ("the Scheduled Castes and Scheduled Tribes (Prevention of Atrocities) Act applies", "SC/ST", True),
    ("an application under Section 12 of the Domestic Violence Act", "PWDVA", True), ("the Domestic Violence Act", "PWDVA", True), ("the Protection Officer filed a domestic incident report", "PWDVA", True),
    ("he was in conscious possession of the RDX recovered from that room", "NDPS", False), ("computer parts in commercial quantity valued at Rs 18 lakh", "NDPS", False),
    ("conscious possession of heroin in commercial quantity", "NDPS", True), ("the accused is liable under Section 37 of the NDPS Act", "NDPS", True),
    ("the accused committed rape and sexual assault upon his minor niece", "POCSO", False), ("aggravated penetrative sexual assault on a child below twelve", "POCSO", True),
    ("it was held that the complaint under Section 138 of the Negotiable Instruments Act was barred", "NI Act", True), ("the cheque was dishonoured", "NI Act", False),
    ("Section 4 of the DP Act, 1961", "DPA", True), ("demand of dowry in a cruelty case under 498A", "DPA", False),
    ("the SC/ST community members were present in the village meeting", "SC/ST", False), ("Section 3(1)(r) of the SC/ST Act", "SC/ST", True),
    ("Section 66C of the Information Technology Act", "IT Act", True), ("they have to set it act aside", "IT Act", False),
    ("under Section 185 of the Motor Vehicles Act", "MV Act", True), ("terrorist act as defined in Section 15 of the UAPA", "UAPA", True),
    ("Section 7 of the Prevention of Corruption Act", "PC Act", True), ("the Arms Act, 1959 applies", "Arms Act", True), ("a juvenile in conflict with law before the Juvenile Justice Board", "JJ Act", True),
]
bad = [(a, t[:50], exp, a in S.passage_acts(t)) for t, a, exp in P if (a in S.passage_acts(t)) != exp]
check(f"passage-side cases ({len(P)})", not bad, bad)
# judgment labels: three DISTINCT passages needed; the same passage repeated counts once; Section 66A judgments are not labelled as IT Act
mk = "an application under Section 12 of the Domestic Violence Act"
lab = S.judgment_labels([(1, "a", mk), (1, "b", mk + " second"), (2, "a", mk), (2, "a", mk), (2, "a", mk), (3, "x", mk), (3, "y", mk), (3, "z", mk)])
check("a judgment is labelled only with 3 distinct marked passages", lab["PWDVA"] == {3}, lab["PWDVA"])
it = "an offence under Section 66A of the Information Technology Act"
lab = S.judgment_labels([(9, str(i), it + str(i)) for i in range(4)] + [(8, str(i), "Section 66C of the Information Technology Act " + str(i)) for i in range(3)])
check("a judgment with 3 or more Section 66A passages is not labelled as IT Act, others are", lab["IT Act"] == {8}, lab["IT Act"])
check("export carries all 13 Acts", len(S.export()["acts"]) == 13)
print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
