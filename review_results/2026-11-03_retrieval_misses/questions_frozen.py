"""
48 FROZEN questions for the 'measure the misses, fix the common ones' work (owner's "Yes, measure the misses and fix the common ones", 2026-11-03).

WRITTEN BY CLAUDE (not a lawyer) and COMMITTED BEFORE ANY RETRIEVAL WAS RUN ON THEM.
The expected sections were chosen from the question alone and each number was checked against the TITLE only:
  * BNS / BNSS: the first line of the library's own chunk for that section number (chunks/*.json);
  * BSA: the section heading in act_shelf/bsa_2023.json.
No retrieval result, no score and no model answer was looked at to choose or to keep a section.

Not the 29 questions of 2026-10-31 and not the 36 of 2026-11-03 (those are 'dev' sets now: they have been looked at, and the failures on them are what the fixes may be designed on).
Sections already used as expected sections in those two sets (BNS 64 75 78 80 85 86 103 106 111 115 117 137 152 189 191 303 308 316 317 318 324 329 331 336 351 356;
BNSS 35 47 48 53 58 63 144 173 175 180 187 250 251 359 396 478 479 480 482 483 489 528) were avoided, with ONE exception: the dowry-death question (BNS 80) is kept because its point is the BSA presumption (118).

POS = [(question, {act: {section numbers that clearly answer it}}, kind)]
  act is 'BNS', 'BNSS' or 'BSA'. kind: 'offence' (a plain account of what happened), 'procedure' (what the police / court may or must do), 'evidence' (is it admissible / who proves).
  A question that names its Act in so many words has 'named' in its kind (e.g. 'evidence-named'); those show whether naming the Act changes what reaches the model.
Nothing here is a statement of good law; 'clearly answers' means: a lawyer reading the section title would say the question is about it.
"""
POS = [
    # ---- BNS: offences, plain accounts (16) ----
    ("A man on a motorcycle snatched my gold chain from my neck and drove away. What offence is that?", {"BNS": {"304"}}, "offence"),
    ("Three men stopped me on the road, showed a knife and took my phone and wallet. What is this offence and its punishment?", {"BNS": {"309"}}, "offence"),
    ("Seven men broke into a jeweller's shop at night, tied up the owner and took the gold. What offence did they commit?", {"BNS": {"310"}}, "offence"),
    ("A shopkeeper mixed a harmful substance in the milk he sells and many people fell ill. Is there a criminal offence?", {"BNS": {"274", "275"}}, "offence"),
    ("A truck driver was driving very fast on a public road and hit a scooter; the rider died. Which section applies to the driver?", {"BNS": {"281"}}, "offence"),
    ("A man secretly filmed a woman changing clothes in a trial room and showed the video to friends.", {"BNS": {"77"}}, "offence"),
    ("A man touched a woman inappropriately in a crowded bus. What is the offence?", {"BNS": {"74"}}, "offence"),
    ("A woman killed herself after her employer harassed her and told her to go and die. Can the employer be held responsible?", {"BNS": {"108"}}, "offence"),
    ("He fired a pistol at me from close range but missed. What is he charged with?", {"BNS": {"109"}}, "offence"),
    ("In a fight, one man hit another on the head with an iron rod and broke his skull. What offence is that?", {"BNS": {"118"}}, "offence"),
    ("My landlord locked me inside the flat for a whole day and would not let me leave. Is that a crime?", {"BNS": {"127"}}, "offence"),
    ("My domestic servant stole cash from the cupboard in my house. What is the punishment?", {"BNS": {"305", "306"}}, "offence"),
    ("Someone called me pretending to be from my bank and took my money; he used a false name and a false employee id.", {"BNS": {"319"}}, "offence"),
    ("A witness lied on oath in the trial court. What can happen to him?", {"BNS": {"229", "227"}}, "offence"),
    ("An agent promised a village girl a job in the city and sold her to a brothel. Which section covers this?", {"BNS": {"143"}}, "offence"),
    ("A person posted a drawing meant to insult the religion of a community and hurt their feelings. Is that punishable?", {"BNS": {"299"}}, "offence"),
    # ---- BNSS: procedure (16) ----
    ("Can the police search my house without a search warrant?", {"BNSS": {"185"}}, "procedure"),
    ("The police took my phone and laptop during their investigation without giving me any paper. Is that allowed?", {"BNSS": {"106", "94"}}, "procedure"),
    ("In a rape case, how fast must the police finish the investigation?", {"BNSS": {"193"}}, "procedure"),
    ("Can a rape complainant be medically examined, and who can order it?", {"BNSS": {"184"}}, "procedure"),
    ("I want to file a private complaint before a magistrate. How does the magistrate take cognizance and what does he examine first?", {"BNSS": {"223", "210"}}, "procedure"),
    ("The accused has absconded. Can the court try him in his absence?", {"BNSS": {"356"}}, "procedure"),
    ("Can an accused plead guilty and ask for a reduced sentence? Within what time must the application be filed?", {"BNSS": {"290", "289"}}, "procedure"),
    ("I was convicted by the Sessions Court. Can I appeal and where?", {"BNSS": {"415", "413"}}, "procedure"),
    ("Can the High Court call for the record of a trial court and examine it if the order seems wrong?", {"BNSS": {"438"}}, "procedure"),
    ("The magistrate fears that a man will disturb the peace in the village. Can he be asked to give security?", {"BNSS": {"126"}}, "procedure"),
    ("Can a witness give evidence by video conference and can the trial be held online?", {"BNSS": {"530"}}, "procedure"),
    ("Is there a witness protection scheme for people who fear the accused?", {"BNSS": {"398"}}, "procedure"),
    ("Within how many days must a trial court pronounce its judgment after the arguments end?", {"BNSS": {"392"}}, "procedure"),
    ("A 19-year-old first-time offender was convicted of a minor offence. Can he be released on probation?", {"BNSS": {"401"}}, "procedure"),
    ("The accused fears he cannot get a fair trial in this district. Can the case be moved to another court?", {"BNSS": {"447", "446"}}, "procedure"),
    ("Can a magistrate record a confession from the accused during the investigation, and how?", {"BNSS": {"183"}}, "procedure"),
    # ---- BSA: evidence (16); the first 12 do not name the Act, the last 4 do ----
    ("Is a confession made to a police officer admissible against the accused in court?", {"BSA": {"23"}}, "evidence"),
    ("The victim of a stabbing told the doctor who attended him that his neighbour attacked him and died the next day. Can that statement be used in court?", {"BSA": {"26"}}, "evidence"),
    ("Can WhatsApp chats and CCTV footage be used as evidence in court, and what must go with them?", {"BSA": {"61", "63"}}, "evidence"),
    ("In a criminal trial who has to prove guilt? Does the accused have to prove that he is innocent?", {"BSA": {"104", "105"}}, "evidence"),
    ("A married woman died within five years of marriage and her family says she was harassed for dowry. Does the court presume anything?", {"BSA": {"118"}, "BNS": {"80"}}, "evidence"),
    ("Can the prosecution tell the court that the accused has a bad character and earlier cases against him?", {"BSA": {"49"}}, "evidence"),
    ("Can a court convict a person on the evidence of an accomplice alone?", {"BSA": {"138"}}, "evidence"),
    ("Is a photocopy of a document accepted in court or must the original be produced?", {"BSA": {"58", "60"}}, "evidence"),
    ("Is a handwriting expert's opinion binding on the court?", {"BSA": {"39", "41"}}, "evidence"),
    ("After his arrest the accused told the police where he had hidden the stolen goods and they were recovered there. Can that part of his statement be used against him?", {"BSA": {"23"}}, "evidence"),
    ("A prosecution witness turned hostile and now denies what he told the police. What can the prosecutor do?", {"BSA": {"157", "148"}}, "evidence"),
    ("Can the defence cross-examine a rape complainant about her past sexual experience?", {"BSA": {"48"}}, "evidence"),
    ("Under the Bharatiya Sakshya Adhiniyam, can a husband be forced to disclose in court what his wife told him during the marriage?", {"BSA": {"128"}}, "evidence-named"),
    ("What does the Bharatiya Sakshya Adhiniyam say about a confession made by one accused that also implicates his co-accused?", {"BSA": {"24"}}, "evidence-named"),
    ("Under the Bharatiya Sakshya Adhiniyam, how many witnesses are needed to prove a fact?", {"BSA": {"139"}}, "evidence-named"),
    ("Does the Bharatiya Sakshya Adhiniyam allow the judge himself to put questions to a witness?", {"BSA": {"168"}}, "evidence-named"),
]
