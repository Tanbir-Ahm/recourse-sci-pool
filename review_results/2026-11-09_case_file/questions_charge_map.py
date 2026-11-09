"""Pre-registered 2026-11-09 BEFORE the first run of run_charge_map.py. Written by Claude (not a lawyer). POS: (facts text, sections that must be among the candidates). NEG: facts that must produce NO candidate from the pattern table
(the meaning search is off in this run). The last items of each list are declared hard in advance."""
POS = [
 ("My client was arrested on the charges that he was recording a sexual molestation case. The prime accused was arrested on the charges of rape. My client was arrested as the said video was phone on his phone and was widely shared, and he was apparently present at the crime spot", {"BNS 77", "ITACT 66E", "ITACT 67A", "BNS 70", "BNS 3", "BNS 61", "BNS 49"}),
 ("The accused raped her and my client was standing guard outside the room. He was arrested with the accused.", {"BNS 70", "BNS 61"}),
 ("My client filmed the assault on his phone and then forwarded the video to friends.", {"BNS 77", "ITACT 67A"}),
 ("After the rape my client deleted the video from the phone to hide the evidence.", {"BNS 238"}),
 ("He recorded an intimate video of his girlfriend and threatened to post it online unless she paid him money.", {"BNS 77", "BNS 351", "BNS 308"}),
 ("My father was arrested for cheating a person of Rs 5 lakh by promising a government job. Police say there was forgery of an appointment letter.", {"BNS 318", "BNS 336", "BNS 340"}),
 ("My neighbour hit my husband with an iron rod during a quarrel over parking. He has a head injury.", {"BNS 115", "BNS 117", "BNS 118"}),
 ("A man keeps following my daughter to college and sends her messages every day.", {"BNS 78"}),
 ("My husband beats me and his family demands more dowry. They harass me every day.", {"BNS 85"}),
 ("My son gave a lift to a man who was absconding in a murder case and was arrested for helping him.", {"BNS 249"}),
 ("The accused is alleged to have gang raped a woman; my client drove the car and was at the spot.", {"BNS 70"}),
 ("My client shared a sexually explicit video of his ex-wife on a WhatsApp group.", {"ITACT 67A", "ITACT 67"}),
 # declared hard
 ("He secretly photographed a woman in a changing room and put the pictures on a website.", {"BNS 77"}),
 ("The accused forced himself on the woman; my client held her hands.", {"BNS 70"}),
]
NEG = [
 "My client was arrested for stealing a bicycle and wants bail.",
 "What is the difference between cognizable and non-cognizable offences?",
 "My brother was arrested for a cheque bounce and the case is in the magistrate's court.",
 "Police seized my phone during an investigation of my employer.",
 "My landlord is refusing to return my deposit.",
 "My client was arrested without a notice for an offence punishable with three years.",
 "He was booked for drunk driving and wants to know how to get bail.",
 "The bank froze my account after a complaint by a customer.",
 "The accused is alleged to have driven a vehicle rashly and caused an accident.",
 "My client's trial has been going on for nine years and he is in jail.",
 # declared hard (a word that also appears in an offence context)
 "She was present at the hearing along with the accused and his lawyer.",
 "The video of the hearing was deleted from the court's server.",
]
