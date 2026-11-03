"""
35 SET-3 questions (17 BNS, 18 BNSS; the first draft of this line said 36, a miscount), written 2026-11-03 AFTER the widening floor was moved from 0.60 to 0.55 using the development sets and the frozen set (which therefore is a development set for that one number now),
and BEFORE any of these was run. Written by Claude (not a lawyer). Expected sections were chosen from the question alone and checked against the first line of the library's chunk for that number (title only).
Sections already used in the earlier sets (see questions_frozen.py) were avoided. Narrative and short forms are mixed on purpose: the frozen set showed that the cross-encoder scores narratives lower than the short
'What is the punishment for X' form.
POS = [(question, {act: {sections}}, kind)]
"""
POS = [
    # ---- BNS ----
    ("Two friends planned together to rob a jeweller and were arrested before they did anything. Are they guilty of any offence?", {"BNS": {"61"}}, "offence"),
    ("He tried to break open an ATM but the alarm rang and he ran away. What is the offence?", {"BNS": {"62"}}, "offence"),
    ("Five men took turns to rape a woman in a moving vehicle. Which section applies?", {"BNS": {"70"}}, "offence"),
    ("My husband married another woman without divorcing me. What can I do?", {"BNS": {"82"}}, "offence"),
    ("In a sudden quarrel he hit his neighbour with a stick and the neighbour died; he says he never meant to kill. Is it murder?", {"BNS": {"105", "101"}}, "offence"),
    ("A man threw acid on a girl who refused his proposal.", {"BNS": {"124"}}, "offence"),
    ("Two men dragged my brother into a car by force and drove away with him.", {"BNS": {"138", "137"}}, "offence"),
    ("The kidnappers phoned the family, demanded money and threatened to kill the child.", {"BNS": {"140"}}, "offence"),
    ("I told the police a false story so that my neighbour would be arrested. What is my exposure?", {"BNS": {"217"}}, "offence"),
    ("I physically stopped the municipal officer from removing the encroachment from my shop.", {"BNS": {"221"}}, "offence"),
    ("The accused broke free from the policemen and ran away while he was being taken to court.", {"BNS": {"262"}}, "offence"),
    ("A factory releases poisonous fumes and the whole colony falls ill. Is there a criminal case against the owner?", {"BNS": {"270"}}, "offence"),
    ("A man was selling obscene books and pictures near a school.", {"BNS": {"294"}}, "offence"),
    ("A drunk man abused people and sang obscene songs outside a temple, annoying everyone.", {"BNS": {"296"}}, "offence"),
    ("I found a wallet with money on the road and kept it without telling anyone. Is that a crime?", {"BNS": {"314"}}, "offence"),
    ("A gang of boys regularly snatches mobile phones in the market, working together as a group.", {"BNS": {"112"}}, "offence"),
    ("Someone promised him money to kill his business rival and he did it. What is the liability of the one who promised?", {"BNS": {"45"}}, "offence"),
    ("Is a person who gives shelter to an offender liable to punishment?", {"BNS": {"249"}}, "offence"),
    # ---- BNSS ----
    ("Can the police stop my lawyer from meeting me while they question me?", {"BNSS": {"38"}}, "procedure"),
    ("Can an ordinary person arrest a thief caught in the act, and what must he do next?", {"BNSS": {"40"}}, "procedure"),
    ("Can the police tie up an accused or use more force than is needed to stop him from escaping?", {"BNSS": {"46"}}, "procedure"),
    ("Can the police search an arrested person and take his belongings?", {"BNSS": {"49"}}, "procedure"),
    ("The court has declared my brother a proclaimed person because he did not appear. What does that mean?", {"BNSS": {"84"}}, "procedure"),
    ("The police want to attach a house that they say was bought with the proceeds of a crime. Can they do that?", {"BNSS": {"107"}}, "procedure"),
    ("A girl is being kept against her will in a house. How can a magistrate order her to be found and produced?", {"BNSS": {"101"}}, "procedure"),
    ("How is a warrant of arrest executed outside the district of the court that issued it?", {"BNSS": {"80", "81", "82"}}, "procedure"),
    ("I want a copy of the police report and the documents the prosecution relies on. Am I entitled to them?", {"BNSS": {"230"}}, "procedure"),
    ("Can the judge question the accused himself about the evidence against him during the trial?", {"BNSS": {"351"}}, "procedure"),
    ("Can the public prosecutor withdraw a case from trial?", {"BNSS": {"360"}}, "procedure"),
    ("Can the court order an accused to give a specimen signature or handwriting?", {"BNSS": {"349"}}, "procedure"),
    ("What happens in a case if the accused is of unsound mind and cannot make his defence?", {"BNSS": {"367"}}, "procedure"),
    ("Is there a time limit after which a court cannot take cognizance of a minor offence?", {"BNSS": {"514"}}, "procedure"),
    ("Can the police take an arrested person to a doctor for examination to collect evidence of the offence?", {"BNSS": {"51"}}, "procedure"),
    ("Can witnesses be asked to identify me in an identification parade after my arrest?", {"BNSS": {"54"}}, "procedure"),
    ("Who is responsible for the health and safety of an accused while he is in custody?", {"BNSS": {"56"}}, "procedure"),
]
