"""Pre-registered 2026-11-09 BEFORE the breach-of-trust pattern and the 'asks about offences' detector were written (owner: "Go" after the comparison with another tool's answer to the bank-accountant question, whose first answer named only BNS 344).
Written by Claude (not a lawyer). Run once on the old code (baseline), then once after the build; no tuning after.
POS_CBT: facts of a breach of trust (property entrusted, then misappropriated): BNS 316 must be a candidate.
NEG_CBT: money or employment facts without a breach of trust: BNS 316 must NOT be a candidate.
ASK_POS: an ask sentence in which a lawyer asks which offences, charges or sections: the first answer should be given the charge-map candidates.
ASK_NEG: ask sentences about bail, arrest, punishment of a named section and so on: must NOT trigger it.
"""
POS_CBT = [
 "My client, the cashier of a primary cooperative society, diverted Rs 14 lakh of the members' deposits to his brother's firm.",
 "The trustee of the temple trust withdrew Rs 9 lakh from the trust account for his own use and falsified the register.",
 "My client was the company's accounts manager and siphoned off Rs 30 lakh over three years by passing fictitious vendor bills.",
 "The clerk entrusted with the school's fee collection misappropriated about Rs 5 lakh.",
 "A bank manager withdrew funds from dormant customer accounts and transferred Rs 2 crore to his own account.",
 "My client, a partner in the firm, took the firm's sale proceeds of Rs 12 lakh and did not account for them.",
 "The treasurer of the housing society embezzled the maintenance fund of Rs 8 lakh.",
 "Our driver, who was entrusted with a truck load of goods worth Rs 6 lakh, sold the goods and kept the money.",
 "The agent collected Rs 4 lakh of premium from customers and misappropriated it instead of remitting it to the insurer.",
 "My client, a post office clerk, misappropriated Rs 3 lakh of deposits made by villagers.",
]
NEG_CBT = [
 "My client is accused of cheque dishonour for Rs 5 lakh given to a friend as a loan repayment.",
 "The employee was dismissed after the manager alleged that he came late to work.",
 "The landlord has not returned the security deposit of Rs 50,000.",
 "He cheated a stranger of Rs 2 lakh by promising a job.",
 "The bank manager refused to sanction my client's loan of Rs 10 lakh.",
 "The accountant filed the company's tax return late and the company paid a penalty of Rs 20,000.",
 "An agent sold my client's plot of land for Rs 40 lakh and my client received the full price.",
 "The cashier was injured in a robbery at the bank and Rs 3 lakh was lost in the incident.",
]
ASK_POS = [
 "What offences is he likely to face?",
 "Which sections can he be charged under?",
 "What charges will the police add?",
 "For what offences can the prosecution book my client on these facts?",
 "Under which sections is he liable?",
 "What are the likely charges against him?",
 "Which offences does this amount to?",
 "What penal provisions apply here?",
]
ASK_NEG = [
 "What are the grounds to seek bail?",
 "How does that change the bail position?",
 "What should I check about the arrest itself?",
 "Is the offence bailable?",
 "What is the punishment under section 318?",
 "Can the FIR be quashed?",
 "Which High Court has jurisdiction?",
 "What does section 344 say?",
]
