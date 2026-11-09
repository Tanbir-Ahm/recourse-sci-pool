# Harbouring alias, version 2: pre-registration (2026-11-09)

**Why a version 2.** Version 1 was measured on its pre-registered set (`PREREGISTRATION.md`, `questions_harbour.py`). Result: the library search already brought BNS 249 for 20 of 24 positives and BNS 253 / 254 for 8 of 8 and 4 of 4 BEFORE any alias; version 1 added one (21 of 24) and fixed the seen question. Its rule "at least 22 of 24" FAILED (21). The three misses it left are phrasings with no word of harbouring: "drove an absconding accused to the bus stand", "had been staying at my guest house", "took the prime accused to another town". I looked at those three, so version 2's groups are informed by them and MUST be tested on a NEW set, not on that one.

**Version 2** (`groups_as_written_v2.py`, committed before the new set was run): three groups added to the entry `bns_249_harbour` only (transport of an accused, staying at my premises, renting a room), each also needing a "wanted person" word. Version 1's groups are unchanged.

**The new set** (`questions_harbour_v2.py`, 16 positives with phrasing of this kind, 30 negatives of which three are deliberate traps that the groups will probably fire on: the police taking an absconder to the station, and two people accompanying a wanted relative to surrender). Written by Claude after v1's result and before v2 was run.

**Success rule fixed in advance.** v2 on the new set: BNS 249 reaches the prompt for at least 12 of 16 (v1 alone is measured on the same set as the baseline); at most 3 of 30 negatives fire; no loss on the v1 set (21 of 24, 8 of 8, 4 of 4, 0 of 40 negatives fire, seen question fixed); 0 fires of the three Acts' entries on the 202 questions of the earlier sets that are not about harbouring. A failure is reported, not tuned away on this set.
