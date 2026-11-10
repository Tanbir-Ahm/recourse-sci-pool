"""Pre-registered 2026-11-10, written AFTER the road-accident rule was restructured (vehicle + accident cue + death or injury, with guards) using sets 9, 10 and 11 (all development sets now). Run ONCE, no tuning afterwards. Written by Claude (not a lawyer). Same three groups as set 9."""
POS_DEATH = [
 "My client was driving a Swift Dzire towards Nashik at night when it hit a stationary truck on the highway; his friend sitting beside him died.",
 "A garbage truck operated by the municipal contractor's driver, my client, ran over a sweeper on the road near the dump yard and killed her.",
 "The accused drove his Innova through a red light and struck a rickshaw, whose driver died in the accident.",
 "A passenger bus driven by my client fell into a ditch on the ghat road; eleven passengers died and he was arrested for the accident.",
 "My client was driving a cement mixer in the town when the vehicle toppled onto a parked car, and the man sitting in the car was killed.",
 "While my client was taking a U-turn on the highway his pickup was hit by a speeding bus; the bus driver and one passenger died and my client has been named as the cause of the accident.",
]
POS_HURT = [
 "The scooter ridden by my client skidded and his pillion rider, a woman, broke her wrist.",
 "My client's truck rear-ended a cart on the highway and the cart owner was admitted to hospital with serious injuries.",
 "A bus driven by the accused hit a lamp post while overtaking and four passengers were injured.",
 "My client was driving his Bullet and could not control it at the turn; he dashed into a hawker, who suffered head injuries.",
 "A cab driver, my client, opened the door without looking and a passing cyclist fell and fractured his collar bone.",
]
NEG = [
 "My client is a bus driver who was falsely implicated in a theft case at the depot.",
 "The accused was driving a stolen car when the police stopped him and found a pistol under the seat.",
 "A mob burnt the bus after the accident and my client, the conductor, has been named in the FIR for rioting.",
 "My client's car was damaged by a fallen tree during the storm and the insurer has rejected the claim.",
 "The driver of the truck is accused of selling the load of rice on the way and keeping the proceeds.",
 "A pedestrian died of electrocution from a fallen wire on the road and the family wants to file a case against the electricity board.",
 "My client, a taxi driver, is accused of molesting a woman passenger during the ride.",
 "The company driver was beaten up by the manager after he refused to work overtime.",
]
