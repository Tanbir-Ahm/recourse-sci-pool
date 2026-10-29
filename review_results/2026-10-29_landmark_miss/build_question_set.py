"""Writes landmark_questions_v1.json: questions with the landmark judgment(s) a lawyer would expect, written by Claude BEFORE any search was run on them.
The expected judgments are chosen from Claude's own knowledge of Indian criminal law and resolved to document ids in the index through the NAMES TABLE only (a lookup by name; no retrieval result was looked at).
A judgment that is not in the index is not used (a search cannot find what is not there). Run: python3 build_question_set.py"""
import gzip, hashlib, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
names = {r["doc"]: r for r in json.load(gzip.open(os.path.join(ROOT, "names_table", "names_table_d8811a9.json.gz"), "rt", encoding="utf-8"))["rows"]}

# group id -> (topic, [expected docs], [(style, question text)])
G = {
 "anticipatory_bail": ("anticipatory bail (Section 438 CrPC)", [4562, 1000252377, 37199], [
    ("lay", "I am afraid the police will arrest me in a false case. Can I get bail before I am arrested, and does it end after a fixed time?"),
    ("lawyer", "What principles govern the grant of anticipatory bail under Section 438 CrPC, and can the court limit it to a fixed period?")]),
 "bail_guidelines": ("bail guidelines, offences not needing arrest", [1000254065, 1000255527], [
    ("lay", "I have been in jail for two years waiting for trial for a minor offence. Can the court give me bail?"),
    ("lawyer", "What guidelines has the Supreme Court laid down on grant of bail and on arrests that are not required in offences punishable up to seven years?")]),
 "arrest_safeguards": ("arrest and custody safeguards", [13877, 14580], [
    ("lay", "What are my rights when the police arrest me? Do they have to tell my family and can they hold me without a medical check?"),
    ("lawyer", "What procedural safeguards must the police follow on arrest and detention to prevent custodial torture?")]),
 "arrest_498a": ("arrest in a dowry harassment case", [41736, 1000250996], [
    ("lay", "My husband's family has been named in a dowry harassment case. Can the police arrest them straight away?"),
    ("lawyer", "Must a police officer be satisfied under Section 41 CrPC before arresting in a Section 498A case, and what should the magistrate check at remand?")]),
 "498a_general_allegations": ("498A, relatives named with vague allegations", [1000253702, 36664], [
    ("lay", "My in-laws are named in my wife's complaint but there is nothing specific against them. Can the court throw out the case against them?"),
    ("lawyer", "When can proceedings under Section 498A IPC against the husband's relatives be quashed for want of specific allegations?")]),
 "default_bail": ("default bail", [17702, 1000250154, 1000252765], [
    ("lay", "The police did not file the chargesheet within 90 days of my arrest. Can I be released as of right?"),
    ("lawyer", "Is the right to default bail under Section 167(2) CrPC indefeasible, and till when can it be claimed?")]),
 "uapa_bail": ("UAPA bail", [1000252904, 1000251566], [
    ("lay", "I have been held under the anti-terror law for years and my trial has not begun. Can the court grant me bail because of the delay?"),
    ("lawyer", "What is the standard for bail under Section 43D(5) UAPA, and does long incarceration justify bail despite the statutory bar?")]),
 "pmla_arrest_bail": ("PMLA grounds of arrest and bail", [1000255278, 1000255745, 1000250373, 1000254150], [
    ("lay", "The Enforcement Directorate arrested me in a money laundering case. Do they have to tell me the reasons in writing?"),
    ("lawyer", "Are the twin conditions for bail under Section 45 PMLA valid, and what must an arrest under the Act communicate to the accused?")]),
 "undertrials": ("undertrial prisoners, speedy trial", [4792, 4819, 4841, 18409], [
    ("lay", "Many poor people stay in jail for years because they cannot pay bail or their trial never starts. Is there a right to a speedy trial?"),
    ("lawyer", "Is the right to a speedy trial part of Article 21, and can a long delay end a criminal case?")]),
 "bail_after_conviction": ("bail pending appeal; bail is the rule", [5242, 5183], [
    ("lay", "I was convicted and have filed an appeal. Can I get bail while the appeal is pending?"),
    ("lawyer", "What is the approach to bail pending appeal against conviction, and is bail the rule and jail the exception?")]),
 "bail_factors": ("bail factors in serious offences", [17683], [
    ("lawyer", "Which factors must the court weigh in deciding bail in a serious non-bailable offence, and must it give reasons?")]),
 "quash_fir": ("quashing a police case", [7332, 1000250282], [
    ("lay", "The police case against me is false and politically motivated. Can the High Court cancel it?"),
    ("lawyer", "In what categories of cases can an FIR or criminal proceeding be quashed under Section 482 CrPC or Article 226?")]),
 "compounding_quash": ("settlement of non-compoundable offences", [37152, 39579, 41348, 1000250282], [
    ("lay", "We have settled our dispute out of court but the offence is serious. Can the court still close the case?"),
    ("lawyer", "Can the High Court quash proceedings for a non-compoundable offence on the basis of a compromise, and what guides it?")]),
 "civil_dispute_criminal": ("civil dispute given a criminal colour", [35436, 1000251250, 1000253806], [
    ("lay", "A business partner has filed a cheating case against me over money we owe each other. Is it right to use a criminal case for a civil dispute?"),
    ("lawyer", "When does a purely civil or commercial dispute amount to cheating or criminal breach of trust, and when should such proceedings be quashed?")]),
 "section_319": ("summoning additional accused", [41145], [
    ("lay", "The trial is half over and a new person's name has come up in the evidence. Can the court add him as an accused?"),
    ("lawyer", "What is the test for summoning an additional accused under Section 319 CrPC, and at what stage can it be done?")]),
 "double_jeopardy": ("same facts tried twice", [39250], [
    ("lawyer", "Can a person be prosecuted both under Section 138 of the NI Act and for cheating on the same transaction, or does the bar on double jeopardy apply?")]),
 "hostile_witness": ("fair trial, hostile witnesses", [26084, 27561], [
    ("lay", "The main witness turned hostile after being threatened. What can the court do to protect a fair trial?"),
    ("lawyer", "What is the duty of the trial court when witnesses turn hostile, and how is a fair trial protected?")]),
 "dying_declaration": ("dying declaration", [12461], [
    ("lay", "Can a person be convicted only on the basis of what the victim said just before dying?"),
    ("lawyer", "What principles govern the reliability of a dying declaration as the sole basis of conviction?")]),
 "burden_home_crime": ("burden of proof, crime inside a home", [28109], [
    ("lay", "A wife was found dead in the house where only she and her husband lived. Who has to explain what happened?"),
    ("lawyer", "How does Section 106 of the Evidence Act operate where an offence takes place inside the privacy of a home?")]),
 "last_seen": ("last seen together", [41316, 28685], [
    ("lay", "The accused was last seen with the deceased and the body was found the next day. Is that enough to convict him?"),
    ("lawyer", "What is the evidentiary value of the last-seen-together circumstance?")]),
 "section_27_recovery": ("recovery on disclosure", [5883, 164], [
    ("lay", "The police say they recovered the weapon because I told them where it was. How much of my statement can be used against me?"),
    ("lawyer", "How much of an accused's statement to the police leading to a recovery is admissible under Section 27 of the Evidence Act?")]),
 "electronic_evidence": ("electronic evidence certificate", [1000252655], [
    ("lay", "The prosecution wants to use a phone video as evidence. What must they produce to make it valid in court?"),
    ("lawyer", "Is a certificate under Section 65B(4) of the Evidence Act mandatory for admitting electronic records such as CCTV footage?")]),
 "police_statement_contradiction": ("statements to police, contradiction", [374], [
    ("lawyer", "How can a witness's earlier statement to the police be used to contradict him at trial under Section 162 CrPC?")]),
 "related_witness": ("relatives as witnesses", [1026], [
    ("lay", "The only witnesses are the victim's relatives. Can the court still rely on them?"),
    ("lawyer", "Is the testimony of related or interested witnesses to be discarded, or only scrutinised with care?")]),
 "self_incrimination": ("self-incrimination, forced tests", [36303, 4157, 5091], [
    ("lay", "Can the police force me to take a lie detector or narco test?"),
    ("lawyer", "What is the scope of Article 20(3), and are compelled narco-analysis or brain mapping tests permissible?")]),
 "sanction_public_servant": ("sanction to prosecute a public servant", [793], [
    ("lay", "Can a policeman be taken to court for something he did while on duty, without the government's permission?"),
    ("lawyer", "When is sanction required under Section 197 CrPC to prosecute a public servant for acts done in the discharge of official duty?")]),
 "death_penalty_rarest": ("death penalty, rarest of rare", [4726, 4795, 9766, 34632], [
    ("lay", "When can a court give the death penalty?"),
    ("lawyer", "What is the rarest of rare doctrine, and how must aggravating and mitigating circumstances be balanced before a death sentence?")]),
 "death_penalty_validity": ("constitutionality of the death penalty, mandatory death", [6696, 9810, 4726], [
    ("lay", "Is the death penalty legal in India, and can a judge be forced to give it?"),
    ("lawyer", "Is a mandatory death sentence valid, and is the death penalty itself constitutional?")]),
 "sentencing_principles": ("principles of sentencing", [39837], [
    ("lawyer", "What principles should a court follow in deciding the quantum of punishment, and should it consider the circumstances of the offender?")]),
 "murder_vs_culpable_homicide": ("culpable homicide vs murder", [5531], [
    ("lay", "What is the difference between murder and culpable homicide?"),
    ("lawyer", "When does causing an injury that is sufficient in the ordinary course of nature to cause death amount to murder under Section 300 IPC?")]),
 "unlawful_assembly": ("unlawful assembly, common object", [3223], [
    ("lay", "I was in a crowd where someone was killed but I did not do anything. Can I be convicted for murder too?"),
    ("lawyer", "What is required to convict a person with the aid of Section 149 IPC for the act of another member of an unlawful assembly?")]),
 "sudden_fight": ("sudden fight, exception to murder", [8015], [
    ("lay", "I killed a man in a sudden quarrel without planning it. Is that murder?"),
    ("lawyer", "What are the requirements of the exception for a sudden fight in the heat of passion under Section 300 IPC?")]),
 "common_intention": ("common intention, section 34", [860], [
    ("lawyer", "What must the prosecution prove to apply Section 34 IPC, and must there be a prior meeting of minds?")]),
 "rape_consent": ("rape, consent and submission", [4992, 40276], [
    ("lay", "Does it count as consent if the woman does not resist or shout?"),
    ("lawyer", "What is the difference between consent and submission in a rape case, and what weight does the victim's testimony carry?")]),
 "modesty": ("outraging modesty", [10468], [
    ("lay", "What counts as outraging the modesty of a woman?"),
    ("lawyer", "How is the offence of outraging the modesty of a woman under Section 354 IPC made out?")]),
 "pocso_contact": ("POCSO skin-to-skin", [1000253440], [
    ("lawyer", "Does sexual assault under the POCSO Act require skin-to-skin physical contact?")]),
 "medical_negligence": ("criminal liability for medical negligence", [27088], [
    ("lay", "A patient died after an operation. Can the doctor be arrested for negligence?"),
    ("lawyer", "What is the standard of gross negligence for prosecuting a medical professional under Section 304A IPC?")]),
 "abetment_suicide": ("abetment of suicide", [1000252755, 35671], [
    ("lay", "My daughter killed herself after her husband's family harassed her. Can they be charged with abetting her suicide?"),
    ("lawyer", "What must be shown to constitute abetment of suicide under Section 306 IPC, and when is mere harassment not enough?")]),
 "cheating_breach_of_contract": ("cheating vs breach of contract", [20323, 20022, 35436], [
    ("lay", "A builder took my money and did not deliver the flat. Is this cheating or only a breach of contract?"),
    ("lawyer", "What distinguishes criminal cheating under Section 420 IPC from a mere breach of contract, and when must dishonest intention exist?")]),
 "dowry_death": ("dowry death presumption", [17435, 19141], [
    ("lay", "My sister died within three years of her marriage and her in-laws say it was suicide. Will the law presume they are responsible?"),
    ("lawyer", "What must be proved to attract the presumption under Section 113B of the Evidence Act in a Section 304B IPC dowry death case?")]),
 "juvenile_age": ("juvenile age determination", [26757, 26764, 30900], [
    ("lay", "I was 17 when the offence was alleged but I am 21 now. Will I be treated as a child?"),
    ("lawyer", "Which date is relevant for determining whether an accused is a juvenile, and how is the age to be established?")]),
 "maintenance_guidelines": ("maintenance, disclosures", [1000252794], [
    ("lay", "How does the court decide how much maintenance a wife and children should get while the case is pending?"),
    ("lawyer", "What directions on affidavit of disclosure and the criteria for interim maintenance has the Supreme Court issued?")]),
 "dv_shared_household": ("domestic violence, right of residence", [1000253984], [
    ("lay", "I left my husband's house because of violence. Can I still claim a right to live there under the domestic violence law?"),
    ("lawyer", "Can a woman who has left the shared household still seek relief under the Protection of Women from Domestic Violence Act?")]),
 "sc_st_bail": ("SC/ST Act arrest and bail", [1000250634], [
    ("lay", "A man is accused under the SC/ST atrocities law. Can the police arrest him immediately and can he get anticipatory bail?"),
    ("lawyer", "What safeguards apply to arrest and anticipatory bail under the SC/ST (Prevention of Atrocities) Act?")]),
 "sc_st_public_view": ("SC/ST Act, insult within public view", [1000252799], [
    ("lay", "A man was abused by a landlord inside the landlord's house with no one else around. Does the atrocities law apply?"),
    ("lawyer", "Does an insult or intimidation inside a building amount to an offence 'in any place within public view' under the SC/ST Act?")]),
 "adultery": ("adultery", [1000251042], [
    ("lay", "Is adultery still a crime in India?"),
    ("lawyer", "Is Section 497 IPC on adultery constitutionally valid?")]),
 "criminal_defamation": ("criminal defamation", [44579], [
    ("lay", "Can a person be jailed for defaming someone?"),
    ("lawyer", "Is criminal defamation under Sections 499 and 500 IPC constitutionally valid?")]),
 "pc_act_demand": ("corruption, proof of demand", [1000254584], [
    ("lay", "A clerk is accused of taking a bribe but the complainant turned hostile. Can the clerk still be convicted?"),
    ("lawyer", "Can a public servant be convicted under the Prevention of Corruption Act in the absence of direct evidence of demand?")]),
 "cheque_presumption": ("cheque presumption, blank cheque", [1000251356, 36322], [
    ("lay", "I gave someone a signed blank cheque as security and they filled in an amount. Can I be punished if it bounces?"),
    ("lawyer", "Does the presumption under Section 139 of the NI Act apply to a signed blank cheque given as security?")]),
 "cheque_jurisdiction": ("cheque bounce, where to file", [41801], [
    ("lay", "Where can a cheque bounce case be filed: where I bank or where the other person banks?"),
    ("lawyer", "Which court has territorial jurisdiction to try a complaint under Section 138 of the NI Act?")]),
 "cheque_compounding": ("cheque bounce, settlement", [1000250291, 41436], [
    ("lay", "We have settled the cheque bounce case. Can it be closed, and what happens if the other side delays?"),
    ("lawyer", "Can an offence under Section 138 NI Act be compounded, and what directions govern the pace of such cases?")]),
 "ndps_search": ("NDPS, personal search", [30317, 37060], [
    ("lay", "Police found drugs in my bag after searching me. Did they have to tell me I could be searched before a magistrate?"),
    ("lawyer", "What is the requirement of informing the accused of the right to be searched before a gazetted officer under Section 50 NDPS?")]),
 "ndps_statement": ("NDPS, statements to officers", [1000252784], [
    ("lay", "The narcotics officers made me sign a statement. Can it be used against me in court?"),
    ("lawyer", "Is a statement recorded under Section 67 NDPS Act admissible as a confession?")]),
 "ndps_bail_burden": ("NDPS bail conditions, reverse burden", [1000253281, 31821], [
    ("lay", "Why is it so hard to get bail in a drugs case?"),
    ("lawyer", "How do the twin conditions under Section 37 NDPS operate, and does the reverse burden of proof violate Article 21?")]),
 "circumstantial": ("circumstantial evidence", [9517, 1154], [
    ("lay", "The police have no eyewitness against my brother, only a chain of circumstances. Can the court still convict him?"),
    ("lawyer", "What are the conditions for a conviction resting wholly on circumstantial evidence?")]),
}

qs = []
for gid, (topic, exp, items) in G.items():
    for style, text in items:
        qs.append({"id": f"L{len(qs) + 1:03d}", "group": gid, "topic": topic, "style": style, "text": text, "expected": exp, "expected_names": [names[d]["name"] for d in exp if d in names]})
missing = sorted({d for g in G.values() for d in g[1] if d not in names})
assert not missing, missing
# halves: alternate groups in the order written, so the same landmark is never in both halves
for q in qs:
    q["half"] = "dev" if list(G).index(q["group"]) % 2 == 0 else "frozen"
body = [{k: q[k] for k in ("id", "group", "text", "expected")} for q in qs]
out = {"schema": "landmark-questions-1", "written": "2026-10-29", "written_by": "Claude, from his own knowledge of Indian criminal law, BEFORE any search was run on these questions. Not a lawyer's list.",
       "rule": "A question is a hit when at least one of its expected judgments (a document id of the newer index d8811a9, found by NAME in the names table) is among the judgments the search returns for it. Judgments that are not in the index were not used.",
       "questions": qs, "sha256_of_questions_and_expected": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()}
json.dump(out, open(os.path.join(HERE, "landmark_questions_v1.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print(len(qs), "questions in", len(G), "groups;", Counter(q["half"] for q in qs), Counter(q["style"] for q in qs))
print("expected judgments:", len({d for g in G.values() for d in g[1]}))
print("sha256", out["sha256_of_questions_and_expected"])
