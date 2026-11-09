"""Pre-registered 2026-11-09, written AFTER the companion rule and its word list were frozen (set 4 was the development set: its questions were in front of me when the word list was written). Run ONCE, no tuning afterwards. Written by Claude (not a lawyer).
Same four groups as set 4. C = BNS 45, 49, 61."""
C = {"BNS 45", "BNS 49", "BNS 61"}
POS = [
 ("My brother and the other accused attacked the shopkeeper with iron rods and broke his leg.", {"BNS 115", "BNS 117", "BNS 118"} | C),
 ("Three persons forced an old man to sign a forged will and took away his house; my client is one of them.", {"BNS 318", "BNS 336", "BNS 340"} | C),
 ("My client with his accomplices blackmailed a woman by threatening to leak her nude pictures unless she paid Rs 2 lakh.", {"BNS 351", "BNS 308"} | C),
 ("Her colleagues, including my client, followed the girl home every evening and sent her obscene messages.", {"BNS 78"} | C),
 ("My mother-in-law, father-in-law and husband demand more dowry and beat me.", {"BNS 85"} | C),
 ("Along with his associates the accused secretly filmed a woman in a trial room and sent the video to a Telegram channel.", {"BNS 77", "ITACT 66E", "ITACT 67", "ITACT 67A"} | C),
 ("A gang of four forged a bank manager's signature and cheated several account holders of lakhs of rupees.", {"BNS 318", "BNS 336", "BNS 340"} | C),
 ("My son and his friends hit a boy with hockey sticks outside the college and he was hospitalised.", {"BNS 115", "BNS 117", "BNS 118"} | C),
 ("The accused and his two associates demanded Rs 5 lakh from the doctor, threatening to publish her intimate video.", {"BNS 351", "BNS 308"} | C),
 ("My client and others kept following a college girl and phoning her though she told them to stop.", {"BNS 78"} | C),
 ("The co-accused recorded a nude video of the complainant without consent and my client forwarded it to friends.", {"BNS 77", "ITACT 66E", "ITACT 67", "ITACT 67A"} | C),
 ("He and his cousins fabricated an appointment letter and cheated three youths of Rs 2 lakh each.", {"BNS 318", "BNS 336", "BNS 340"} | C),
]
NEG_SINGLE = [
 "The accused hit the vendor with a stick and broke his tooth.",
 "My client forged a certificate and cheated the bank of a loan.",
 "He sent her obscene messages and kept following her on the way to work.",
 "My neighbour threatens to circulate my daughter's intimate photographs unless I pay him.",
 "My husband beat me with a belt and his anger over dowry never ends.",
 "He took naked photographs of the girl without her knowledge and uploaded them.",
 "The accused attacked my father with an axe.",
 "My client cheated a farmer by forging the land papers.",
]
NEG_AFTER = [
 "My client and the others deleted the messages from the group chat after the police filed the case.",
 "They sheltered the accused wanted in the robbery in their house for two weeks.",
 "His friends helped him destroy the evidence on the phone after the incident, and the police are investigating.",
 "My client and his father hid an absconding accused in their godown.",
]
NEG_NONE = [
 "My client and others were found gambling in a public place.",
 "The tenants and the landlord are in a dispute about rent.",
 "My friends and I were stopped at a naka for not wearing helmets.",
 "Is a married woman entitled to maintenance after divorce?",
]
TRAP = []
