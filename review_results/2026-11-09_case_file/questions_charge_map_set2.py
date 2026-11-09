"""Pre-registered 2026-11-09 BEFORE the second run of run_charge_map.py (after the first run, on set 1, showed the word lists lacked 'intimate', 'nude' and 'assault' as sexual words and 'stood guard' as presence). NEW questions, written before the lists were widened.
POS: (facts, sections that must be among the candidates). NEG: no candidate expected. Written by Claude (not a lawyer)."""
POS = [
 ("My client recorded an intimate video of his wife without her knowledge and uploaded it online.", {"BNS 77", "ITACT 66E", "ITACT 67A"}),
 ("A nude photograph of the complainant was circulated by my client on social media after she refused him.", {"ITACT 66E", "ITACT 67A"}),
 ("He forced himself on her while my client waited outside the house and then drove them away.", {"BNS 70"}),
 ("The woman was gang raped; my client was one of the men who accompanied the accused.", {"BNS 70", "BNS 61"}),
 ("My client is accused of assisting the rapist by arranging the room, and the phone footage was found with him.", {"BNS 70", "BNS 77"}),
 ("The accused is charged with raping a colleague; my client, a friend, was there when it happened and recorded the scene.", {"BNS 70", "BNS 77"}),
 ("He cheated investors using fake documents and forged signatures.", {"BNS 318", "BNS 336", "BNS 340"}),
 ("The accused struck the victim with a knife and caused a deep wound.", {"BNS 115", "BNS 117", "BNS 118"}),
 ("The accused keeps stalking a woman by following her daily and messaging her.", {"BNS 78"}),
 ("His wife says her in-laws demanded dowry and tortured her.", {"BNS 85"}),
 ("My client erased the CCTV footage after the incident to protect his friend.", {"BNS 238"}),
 ("The accused blackmailed the woman with her nude photos, demanding money.", {"BNS 351", "BNS 308"}),
]
NEG = [
 "My client was caught driving without a licence.",
 "The tenant refuses to vacate the premises after the lease ended.",
 "He was arrested for a protest outside the collectorate.",
 "My client's bank account was frozen on a police request.",
 "The accused is a government servant charged under the Prevention of Corruption Act.",
 "She was present at the wedding along with her family.",
 "My client wants to know whether the arrest memo must be signed.",
 "The witness deleted old messages from her phone to free storage space.",
]
