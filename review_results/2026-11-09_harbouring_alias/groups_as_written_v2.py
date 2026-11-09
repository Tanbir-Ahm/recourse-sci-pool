"""Version 2 word groups for BNS 249, written 2026-11-09 AFTER version 1 was measured (v1 missed three transport / stay phrasings on its own set: 'drove an absconding accused to the bus stand', 'staying at my guest house',
'took the prime accused to another town') and BEFORE the v2 question set was written or run. They add three groups to the entry bns_249_harbour; version 1's groups are unchanged. The v2 questions are a NEW set."""
from groups_as_written import NOUN, WANTED
NOUN_ACC = (r"(?:him|her|them|the (?:prime |main |principal )?(?:accused|offender|man|fugitive|absconder|culprit)|(?:an? )?(?:absconding|wanted) \w+|"
            r"my (?:brother|son|friend|husband|cousin|relative|nephew|uncle|neighbou?r|employee|worker|father)|a (?:friend|relative|man|person|stranger|colleague|fugitive|accused|offender))")
TRANSPORT = r"\b(?:drove|driven|driving|took|taken|taking|dropped|dropping|carried|carrying|transported|ferried|escorted|accompanied)\s+" + NOUN_ACC + r"\b[^.?!]{0,30}?\b(?:to|away|across|out of|from)\b"
STAY = r"\b(?:staying|stayed|stays|lodged|lodging|living|lived|residing|resided|sleeping|slept|put up|putting up)\s+(?:at|in|with|inside)\s+(?:my|our|his|her)\s+(?:house|home|guest ?house|farm\w*|shop|room|flat|hotel|lodge|property|place|godown|office)\b"
RENT = r"\b(?:rented|let out|leased|gave on rent|sublet)\s+(?:a|my|the|one)\s+(?:room|flat|house|shop|godown|portion)\s+to\s+"
V2_GROUPS_249 = [[TRANSPORT, WANTED], [STAY, WANTED], [RENT, WANTED]]
