"""Pre-registered 2026-11-09, written AFTER the breach-of-trust pattern and the offence-ask detector were frozen (set 6 was the development set: its questions were in view when they were written). Run ONCE, no tuning afterwards. Written by Claude (not a lawyer). Same four groups as set 6."""
POS_CBT = [
 "My client is the secretary of a charitable society and is accused of using Rs 11 lakh of donations for building his own house.",
 "The warehouse supervisor sold part of the stored grain worth Rs 18 lakh and pocketed the money, though the stock was in his custody.",
 "A senior clerk at the municipal office diverted Rs 7 lakh of property tax collections into a personal account.",
 "The company's director transferred Rs 40 lakh of customer advances to a firm owned by his wife and never returned them.",
 "My client was a broker who received Rs 25 lakh from a client to buy shares and misappropriated the sum.",
 "The caretaker of the estate, who held the tenants' rent of Rs 6 lakh on behalf of the owner, did not account for it.",
 "An employee of the courier company opened the parcels entrusted to him and sold the gold ornaments inside.",
 "The executor of the will sold the deceased's shares and kept the Rs 15 lakh instead of dividing it among the heirs.",
]
NEG_CBT = [
 "The tenant refuses to vacate the flat although the lease has expired.",
 "My client gave a post-dated cheque for Rs 3 lakh which was dishonoured and the payee has filed a complaint.",
 "The manager of the shop shouted at the customer and refused to give a refund of Rs 2,000.",
 "A partner in the firm wants to retire and asks how the firm's assets will be divided.",
 "The company has delayed the salary of its employees for two months.",
 "The agent did not turn up for the registration of the sale deed.",
 "He borrowed Rs 5 lakh from a friend and has not repaid it yet.",
 "The driver rammed the truck into a divider and the goods worth Rs 4 lakh were damaged.",
]
ASK_POS = [
 "Which provisions of the BNS could the police invoke against him?",
 "What are the possible offences here?",
 "For which offences can he be prosecuted?",
 "Tell me what charges he faces.",
 "What sections is he likely to be booked under?",
 "Which other offences could be added to the FIR?",
 "Under what sections can my client be charged?",
 "What offences does this set of facts disclose?",
]
ASK_NEG = [
 "Can he get anticipatory bail?",
 "How long can the police keep him in custody?",
 "Is section 316 of the BNS bailable?",
 "What is the limitation for filing the complaint?",
 "Which court will try the case?",
 "How do I get the FIR copy?",
 "What is the meaning of dishonest intention?",
 "What does the Supreme Court say about parity in bail?",
]
