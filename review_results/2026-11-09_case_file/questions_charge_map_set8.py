"""Pre-registered 2026-11-09, written AFTER the breach-of-trust word lists were widened using sets 6 and 7 (so those two are development sets now). Run ONCE, no tuning afterwards. Written by Claude (not a lawyer). Only the breach-of-trust groups are used; the offence-ask detector was not changed after set 6 and set 7 held it out (8 of 8, 0 of 8)."""
POS_CBT = [
 "My client, the manager of a village credit society, lent members' savings to his relatives without records and later could not account for Rs 22 lakh.",
 "The estate agent collected Rs 9 lakh as advance from buyers on behalf of the builder and spent it on his own business.",
 "The hospital's pharmacist, who was in charge of the stock of medicines, sold them privately and kept about Rs 5 lakh.",
 "A club treasurer transferred Rs 3 lakh of the members' subscriptions to his personal account and has not returned it.",
 "My client was the guardian of two minors and used Rs 12 lakh of their fixed deposit for his own business.",
 "The cooperative dairy's secretary received milk payments of Rs 8 lakh meant for the farmers and misappropriated the money.",
 "The jeweller's employee, who had been given gold ornaments for polishing, disappeared with them.",
 "An advocate's clerk collected Rs 1.5 lakh from a client for court fees and never deposited it.",
]
NEG_CBT = [
 "A shopkeeper sold a defective mobile phone to my client for Rs 15,000 and refuses to refund it.",
 "My client received a notice from the income tax department for non-payment of Rs 6 lakh in tax.",
 "The company director was arrested after a road accident in which a pedestrian was injured.",
 "An employee took a week of leave without informing the manager.",
 "The bank refused to release the funds in my client's account because of a court order.",
 "The trust deed was executed but the trustees have not yet met.",
 "The supervisor used abusive language against the workers on the factory floor.",
 "My client's partner left the firm and started a competing business nearby.",
]
