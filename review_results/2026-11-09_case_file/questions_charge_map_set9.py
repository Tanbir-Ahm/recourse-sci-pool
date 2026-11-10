"""Pre-registered 2026-11-10 BEFORE the road-accident pattern was written (owner: "Build the road-accident pattern", after the truck-driver hit-and-run test whose charge table held only BNS 106). Written by Claude (not a lawyer).
POS_DEATH: a vehicle hits someone who dies: BNS 106 and BNS 281 must be candidates.
POS_HURT: a vehicle hits someone who is injured, no death: BNS 281 and BNS 125 must be candidates.
NEG: no road accident, or a deliberate killing with a vehicle, or no vehicle: neither 106 nor 281 nor 125 may be offered by the table's patterns.
Run once on the old code (baseline), then once after the build. It is a development set (the word lists are written with it in view); a fresh set 10 follows the build."""
POS_DEATH = [
 "My client's bus hit a cyclist at a junction in Nagpur and the cyclist died in hospital the next day.",
 "The tractor driven by my client overturned on a village road and the labourer sitting on the trolley was killed.",
 "A speeding car knocked down an elderly woman near the market; she died on the spot and the driver, my client, was arrested.",
 "My client was riding his motorcycle fast when he collided with a pedestrian, who succumbed to the injuries.",
 "The tanker driver reversed without a helper and ran over a child playing behind the vehicle; the child died.",
 "My client's autorickshaw struck a scooter at night and the pillion rider lost his life.",
 "The accused, a van driver, was talking on the phone when the van rammed into a parked bike and its owner standing beside it died.",
 "My client's lorry skidded on a wet road and crushed a motorcyclist to death.",
]
POS_HURT = [
 "My client's car hit a pedestrian at a crossing and the pedestrian suffered a fractured leg.",
 "The scooter driven by the accused struck a schoolgirl, who was hospitalised with head injuries.",
 "A tempo driven by my client collided with an autorickshaw and three passengers were injured.",
 "My client was driving the jeep that knocked down a farmer on the highway; the farmer sustained grievous injuries.",
 "The bus driver braked late and the bus hit the car ahead, injuring two persons.",
 "My client's bike hit an old man while overtaking and the old man suffered a deep wound on the head.",
]
NEG = [
 "The accused deliberately drove his car over his rival and killed him after a dispute over land.",
 "The surgeon's negligence during the operation caused the patient's death and the family has filed a complaint.",
 "My client works as a driver for a transport company and has not been paid his salary for four months.",
 "The driver was arrested for carrying contraband concealed in his truck.",
 "A man died of a heart attack in a bus while travelling to Pune.",
 "My client is accused of cheating the car dealer by giving a bounced cheque for the purchase of a car.",
 "The car was stolen from outside my client's house and the police have not registered the FIR.",
 "The accused beat a driver with an iron rod after a quarrel over parking and the driver was injured.",
 "The truck owner is accused of not paying the road tax and the vehicle was seized by the transport office.",
 "The driver's licence of my client has been suspended and he wants to challenge the order.",
]
