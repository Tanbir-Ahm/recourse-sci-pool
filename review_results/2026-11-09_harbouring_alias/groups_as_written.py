"""The word groups of the harbouring alias, exactly as written on 2026-11-09 BEFORE the question set was run (see PREREGISTRATION.md). Copied unchanged into Recourse statute_aliases.py."""
NOUN = (r"(?:him|her|them|someone|somebody|the (?:accused|offender|man|boy|woman|person|fugitive|culprit|absconder)|"
        r"my (?:brother|son|friend|husband|cousin|relative|nephew|uncle|neighbou?r|employee|worker|father|driver)|"
        r"a (?:friend|relative|man|person|stranger|colleague|fugitive|accused|offender)|an (?:accused|offender|absconder|acquaintance))")
HIDE = r"\b(?:hid|hide|hiding|hidden|conceal\w*|shelter\w*|harbou?r\w*)\s+" + NOUN + r"\b"
GIVE = r"\b(?:gave|give|giving|given|offered|offering|provided|providing)\b[^.?!]{0,40}?\b(?:lift|ride|shelter|refuge|hiding place|place to stay|accommodation|food and (?:money|shelter)|money and (?:food|shelter))\b"
LET = r"\b(?:let|allowed|letting|allowing)\s+" + NOUN + r"\s+(?:stay|sleep|live|hide)\b"
HELPFLEE = r"\bhelp\w*\s+" + NOUN + r"\s+(?:to\s+)?(?:hide|flee|abscond|run away|go into hiding|stay hidden|evade)\b"
WANTED = (r"(?:abscond\w*|fugitive|on the run|running (?:away )?from (?:the )?police|wanted (?:by|for|in)\b|wanted (?:man|person)|proclaimed offender|"
          r"\bpolice (?:was|were|are|is) (?:looking|searching|hunting|after)\b|sought by (?:the )?police|evading (?:arrest|the police)|prime accused|main accused|principal accused|"
          r"\b(?:fled|escaped|flee|fleeing)\b|jumped bail)")
ESCAPED_OR_ORDERED = (r"(?:escap\w+\s+(?:from\s+)?(?:lawful\s+|police\s+|judicial\s+)?(?:custody|jail|prison|lock-?up)|jail\s?break|prison\s?break|"
                      r"(?:warrant|order)\w*\b[^.?!]{0,40}\b(?:arrest|apprehen\w+)|(?:arrest|apprehension)\b[^.?!]{0,40}\b(?:ordered|warrant)|ordered\s+(?:his|her|their|the)\s+arrest|police\s+ordered)")
ROBBERS = r"\b(?:robber\w*|dacoit\w*|decoit\w*|robbed)\b"

ENTRIES = [
    {"id": "bns_249_harbour", "act": "BNS", "section": "249", "groups": [
        [r"\bharbou?r\w*", r"\b(?:offenders?|accused|criminals?|fugitives?|absconders?|culprits?)\b"],
        [HIDE, WANTED],
        [GIVE, WANTED],
        [LET, WANTED],
        [HELPFLEE],
        [r"\bscreen\w*\s+(?:an?\s+|the\s+)?(?:offender|accused|person|him|her)\s+from\s+(?:legal\s+)?(?:punishment|arrest|the police)"],
        [r"\baccessory after the fact\b"],
    ]},
    {"id": "bns_253_harbour_escaped_or_ordered", "act": "BNS", "section": "253", "groups": [
        [HIDE, ESCAPED_OR_ORDERED], [GIVE, ESCAPED_OR_ORDERED], [LET, ESCAPED_OR_ORDERED], [HELPFLEE, ESCAPED_OR_ORDERED],
        [r"\b(?:harbou?r\w*|conceal\w*)", ESCAPED_OR_ORDERED],
    ]},
    {"id": "bns_254_harbour_robbers", "act": "BNS", "section": "254", "groups": [
        [HIDE, ROBBERS], [GIVE, ROBBERS], [LET, ROBBERS], [HELPFLEE, ROBBERS],
        [r"\bharbou?r\w*", ROBBERS],
    ]},
]
