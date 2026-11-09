"""Pre-registered 2026-11-09 BEFORE any run of the 'companion' rule (abetment BNS 45/49 and conspiracy BNS 61 offered when the facts show more than one person and one of the table's patterns fires). Written by Claude (not a lawyer), before the rule was written.
POS: facts with more than one person involved in the offence itself; every listed section must be among the candidates (the pattern's own sections plus BNS 45, 49 and 61).
NEG_SINGLE: a pattern fires, one person only; BNS 45, 49 and 61 must NOT be among the candidates.
NEG_AFTER: several persons, but the pattern is about what happens AFTER the offence (hiding evidence, sheltering a wanted man): abetment/conspiracy of the earlier offence is not offered by this rule; 45, 49 and 61 must NOT be among the candidates.
NEG_NONE: no pattern fires (several persons or not): no candidate at all.
TRAP: declared in advance as questions the word list will probably get wrong (the victim is the group; 'and his brother' is the victim's brother); counted separately.
"""
C = {"BNS 45", "BNS 49", "BNS 61"}
POS = [
 ("My client and two of his friends beat the complainant with sticks and fractured his arm.", {"BNS 115", "BNS 117", "BNS 118"} | C),
 ("The accused and his brother threatened to post the girl's naked photographs unless she paid Rs 50,000.", {"BNS 351", "BNS 308"} | C),
 ("My uncle and his partner cheated a widow of her savings with a forged sale deed.", {"BNS 318", "BNS 336", "BNS 340"} | C),
 ("A group of boys kept following my sister and messaging her even after she blocked them.", {"BNS 78"} | C),
 ("My husband and his parents torture me for dowry.", {"BNS 85"} | C),
 ("My client along with a co-accused took an intimate video of a woman without consent and shared it.", {"BNS 77", "ITACT 66E", "ITACT 67", "ITACT 67A"} | C),
 ("The driver and his helper held the victim down while the accused beat him with an iron rod.", {"BNS 115", "BNS 117", "BNS 118"} | C),
 ("Two men forged an appointment letter and cheated my son of Rs 3 lakh.", {"BNS 318", "BNS 336", "BNS 340"} | C),
 ("My client, together with his cousin, blackmailed the woman with her private video.", {"BNS 351", "BNS 308"} | C),
 ("He and his friends filmed the girl naked in the hostel bathroom and uploaded the clips online.", {"BNS 77", "ITACT 66E", "ITACT 67", "ITACT 67A"} | C),
]
NEG_SINGLE = [
 "My client beat the complainant with an iron rod during a quarrel.",
 "He threatened to post her naked photographs unless she paid him Rs 20,000.",
 "My uncle cheated a widow of her savings using a forged signature.",
 "A man follows my sister to college and keeps messaging her.",
 "He secretly recorded an intimate video of his colleague and shared it.",
 "My husband beats me and demands dowry.",
]
NEG_AFTER = [
 "He and his friends gave a lift to a man who was absconding in a murder case.",
 "My client and his brother deleted the CCTV footage from the shop's system after the police registered the FIR.",
]
NEG_NONE = [
 "My client and his friends were arrested for selling liquor without a licence.",
 "The company has not paid my salary for four months.",
 "What are the grounds for cancelling bail?",
]
TRAP = [
 "My client beat the complainant and his brother with an iron rod during a quarrel.",
 "The accused threatened to post the girl's naked photographs; she and her parents went to the police.",
]
