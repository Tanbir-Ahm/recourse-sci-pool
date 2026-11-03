"""
16 FRESH evidence questions + 8 more negatives, written 2026-11-03 AFTER the evidence word pass (act_detect.py, EVIDENCE_DETECT) and the other fixes were built and BEFORE any of these was run. Written by Claude (not a lawyer), in
a different voice from the frozen set on purpose (the frozen set and the word pass have the same author, so a good score there can be the author's habits; this set is a check on that, not a cure for it).
The expected BSA sections were chosen from the section headings in act_shelf/bsa_2023.json (title only). None names the Act.
POS = [(question, {act: {sections}}, kind)];  NEG2 = [question that is NOT about the law of evidence].
"""
POS = [
    ("Is an admission made by one party to a case binding on him later?", {"BSA": {"16", "25"}}, "evidence"),
    ("Can the court take notice of a fact such as a public holiday without anybody proving it?", {"BSA": {"51", "52"}}, "evidence"),
    ("Is a certified copy of a public document, like a land record, accepted as proof without calling the officer who made it?", {"BSA": {"75", "76"}}, "evidence"),
    ("What is primary evidence of a document?", {"BSA": {"57"}}, "evidence"),
    ("Can a blind or deaf person be a witness in a criminal trial?", {"BSA": {"124", "125"}}, "evidence"),
    ("If a husband and wife are both accused in a case, can one give evidence against the other?", {"BSA": {"126"}}, "evidence"),
    ("Does the law presume that a document which is thirty years old is genuine?", {"BSA": {"92"}}, "evidence"),
    ("Can emails that are five years old be presumed to be genuine electronic records?", {"BSA": {"93"}}, "evidence"),
    ("Can an accused be convicted on the testimony of just one witness?", {"BSA": {"139"}}, "evidence"),
    ("What does the law say about leading questions put to a witness in examination-in-chief?", {"BSA": {"146"}}, "evidence"),
    ("Can a lawyer be asked to disclose in court what his client told him?", {"BSA": {"132", "134"}}, "evidence"),
    ("How is the signature on a will proved in court?", {"BSA": {"65", "67"}}, "evidence"),
    ("Is an entry in a shopkeeper's account book relevant evidence in a dispute about money?", {"BSA": {"28"}}, "evidence"),
    ("The weapon was recovered after the accused pointed out where it was hidden. Is that recovery enough to prove guilt?", {"BSA": {"23"}}, "evidence"),
    ("A woman says she was raped and the accused says she consented. Does the court presume anything about her consent?", {"BSA": {"120"}}, "evidence"),
    ("Is a girl of nine allowed to give evidence in a trial, or is she too young?", {"BSA": {"124"}}, "evidence"),
]
NEG2 = [
    "Can the police arrest me for a cheque that bounced?",
    "On what grounds can a magistrate refuse bail?",
    "My employer filed a false case of theft against me. What can I do?",
    "How long does a murder trial usually take, and can I ask for it to be speeded up?",
    "A man died in a road accident and the driver ran away. What is the case against the driver?",
    "The court has issued a non-bailable warrant against me. What should I do?",
    "Is it an offence to share someone's private photos on WhatsApp?",
    "The police have filed a chargesheet. What happens next?",
]
