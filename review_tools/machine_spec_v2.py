#!/usr/bin/env python3
"""Machine Spec v2 (DRAFT of 2026-10-12; not frozen): the named-Act boost's question-side anchors and passage-side markers for 13 Acts, after Mr. Advocate's regex audit and the code tests of it
(review_results/2026-10-12_advocate_regex_review/). PRIVATE. Nothing here says that an Act applies to a case; it is a ranking hint.

Two question-side tiers (the fix-test arms):
  N1  precise anchors: Mr. Advocate's patterns, repaired (one did not compile), made symmetric, with his own rules applied to his own anchors (no bare section numbers, no standalone generic words).
  N2  broader: N1 plus plain-language anchors (everyday wording), each Act with its own exclusion guard; N2 = N1 or the extra anchors.
Passage side (shared by both arms): a strong marker per Act; a judgment is LABELLED with an Act if at least LABEL_MIN distinct passages (distinct by text hash) carry a strong marker of that Act. The IT Act label is
withheld from a judgment that has 3 or more passages mentioning Section 66A (struck down in 2015; never surface it as a live offence).

Conventions: patterns are compiled case-insensitive with DOTALL; acronyms are case-sensitive through (?-i:...) groups; near(a, b, n) means a within n characters of b in either order.
"""
import re

LABEL_MIN = 3
FLAGS = re.I | re.S


def near(a, b, n=100):
    return rf"(?:(?:{a}).{{0,{n}}}(?:{b})|(?:{b}).{{0,{n}}}(?:{a}))"


def alt(*parts):
    return "(?:" + "|".join(parts) + ")"


SPEC = {}

# ------------------------------------------------------------------ PWDVA
_t = r"(?:Protection of Women from Domestic Violence Act|\bDomestic Violence Act|(?-i:\bPWDVA\b|\bPWDV Act\b|\bDV Act\b|\bD\.V\. Act\b))"
SPEC["PWDVA"] = {
    "name": "Protection of Women from Domestic Violence Act, 2005",
    "passage": [_t, r"\bsections?\s*(?:12|17|18|19|20|21|22|23|31)\s+of\s+(?:the\s+)?" + _t[:-1] + r")", r"\bprotection officers?\b", r"\baggrieved woman\b", near(r"\bshared household\b", r"\b(?:residence|protection|monetary|compensation|ex parte)\s+orders?\b", 100)],
    "N1": [_t, r"\bdomestic violence\b", r"\baggrieved woman\b", r"\bprotection officer\b", near(r"\b(?:shared household|residence order|protection order|monetary relief|compensation order)\b", r"\b(?:domestic|violence|abus\w+|aggrieved|DV Act|PWDVA|residence order|protection order|monetary relief|maintenance|evict\w*)\b", 120)],
    "N2_extra": [r"\bdomestic abuse\b", r"\bfamily violence\b", r"\b(?:threw|thrown|throw|throws|throwing|kicked|drove|driven)\s+(?:me|her|us|my wife|his wife)\s+out of\s+(?:the |my |our |his )?(?:marital |matrimonial |shared )?(?:house|home)\b",
                 r"\b(?:husband|in-?laws?|mother-in-law|partner|boyfriend)\b.{0,30}\b(?:hits?|beats?|beat|beating|abus\w+|tortur\w+|harass\w+|threaten\w*)\s+(?:me|her)\b", r"\bright to (?:stay|live|reside) in (?:the|my|our) (?:house|home)\b",
                 near(r"\b(?:evict\w*|throw\w*\s+(?:me\s+)?out|kick\w*\s+(?:me\s+)?out)\b", r"\b(?:in-?laws?|husband|matrimonial|marital|mother-in-law)\b", 60), near(r"\b(?:matrimonial|marital) home\b", r"\b(?:right|stay|live|reside|evict\w*|throw\w*|name)\b", 60),
                 r"\b(?:abusive|violent)\s+(?:husband|partner|boyfriend|spouse)\b", near(r"\b(?:emotional|mental|physical|verbal)\s+(?:abuse|torture)\b", r"\b(?:husband|wife|partner|in-?laws?|home|house)\b", 80), near(r"\bprotection order\b", r"\b(?:broke|broken|breach\w*|violat\w*)\b", 40)],
    "N2_exclude": r"\b(?:498-?A|section\s*85|BNS\s*85|304-?B|dowry death)\b",
}
# ------------------------------------------------------------------ NDPS
_t = r"(?:(?-i:\bNDPS\b)(?:\s+Act)?|Narcotic Drugs and Psychotropic Substances Act)"
_drugs = r"\b(?:ganja|charas|hashish|heroin|cocaine|MDMA|methamphetamine|opium|poppy husk|poppy straw|smack|brown sugar|marijuana|cannabis|ecstasy|LSD|tramadol|codeine)\b"
SPEC["NDPS"] = {
    "name": "Narcotic Drugs and Psychotropic Substances Act, 1985",
    "passage": [_t, r"\bsections?\s*(?:20|21|22|27A|29|37|42|43|50|52A|57|67)\s+of\s+the\s+(?:(?-i:NDPS)|Narcotic Drugs and Psychotropic Substances)\s*Act", near(r"\b(?:commercial quantity|conscious possession|intermediate quantity|small quantity)\b", r"(?:\bNDPS\b|\bnarcotic|\bpsychotropic|\bcontraband\b|" + _drugs[2:-2] + r"|\bsection\s*(?:20|21|37)\b)", 200)],
    "N1": [_t, r"\b(?:commercial quantity|intermediate quantity|conscious possession|psychotropic substances?|narcotic drugs?)\b", near(_drugs, r"\b(?:seiz\w+|possess\w*|recover\w*|commercial quantity|contraband)\b", 100),
           near(r"\b(?:recovery|seizure)\b", r"\b(?:NDPS|narcotic drug|psychotropic substance|contraband)\b", 100), near(r"\b(?:no recovery|nothing recovered|no contraband recovered)\b", r"\b(?:NDPS|narcotic|psychotropic|drug possession|commercial quantity|seizure)\b", 100)],
    "N2_extra": [near(_drugs, r"\b(?:found|caught|arrest\w*|police|NCB|bag|car|room|carry\w*|sell\w*|sold|peddl\w+|smuggl\w+|bail|statement)\b", 80), r"(?-i:\bNCB\b)", r"\bnarcotics?\b", near(r"\b(?:drug|drugs)\b", r"\b(?:case|peddling|trafficking|dealer|smuggling|bail|seized|caught)\b", 40),
                 near(r"\b(?:drug|drugs|narcotic\w*|contraband|illegal tablets?|illegal pills?)\b", r"\b(?:police|find|found|bag|arrested|caught|seized|carrying|search\w*|funded|delivery|gang|tip|confess\w*|admit\w*|samples?|seizure|magistrate|gazetted)\b", 80)],
    "N2_exclude": r"\b(?:forensic|toxicolog\w*|post-?mortem|autopsy|traces? of|prescri\w+|pharmacy|medicine|doctor|hospital|patient|treatment|illness|fever)\b",
}
# ------------------------------------------------------------------ POCSO
_t = r"(?:(?-i:\bPOCSO\b)(?:\s+Act)?|\bP\.O\.C\.S\.O|Protection of Children from Sexual Offences Act)"
SPEC["POCSO"] = {
    "name": "Protection of Children from Sexual Offences Act, 2012",
    "passage": [_t, r"\b(?:aggravated )?penetrative sexual assault\b", r"\bsections?\s*(?:3|4|5|6|7|8|9|10|11|12|18|19|21|23|29|30|33|34|35|36|42A)\s+of\s+the\s+(?:(?-i:POCSO)|Protection of Children from Sexual Offences)\s*Act"],
    "N1": [_t, r"\b(?:child sexual abuse|sexual assault of a child|sexual harassment of a child|(?:aggravated )?penetrative sexual assault|special court under POCSO)\b", near(r"\b(?:sexual assault|sexual harassment|rape|molestation)\b", r"\b(?:child|minor|below\s+18|under\s+18|under\s+eighteen)\b", 100)],
    "N2_extra": [near(r"\b(?:touch\w*|molest\w*|sexual\w*|rape\w*|abus\w*|assault\w*|misbehav\w*|obscene|inappropriate\w*)\b", r"\b(?:daughter|son|child|children|minor|girl|boy|student|(?:[0-9]|1[0-7])[- ]?year[- ]?old|under[- ]?(?:18|eighteen))\b", 100)],
    "N2_exclude": r"\b(?:1[89]|[2-9][0-9])[- ]?year[- ]?old\b|\baged\s*(?:1[89]|[2-9][0-9])\b|\b(?:adult|boss|employer|colleague|workplace)\b",
}
# ------------------------------------------------------------------ SC/ST
_t = r"(?:Scheduled Castes and (?:the )?Scheduled Tribes\s*\(Prevention of Atrocities\)\s*Act|(?-i:\bSC\s*/?\s*ST\b|\bSCST\b)\s*(?:\(Prevention of Atrocities\)\s*)?Act|Prevention of Atrocities\)?\s*Act)"
SPEC["SC/ST"] = {
    "name": "Scheduled Castes and Scheduled Tribes (Prevention of Atrocities) Act, 1989",
    "passage": [_t, r"\bsections?\s*(?:3|14|15A|18|18A)\s*(?:\(\s*\d\s*\))?\s*(?:\(\s*[a-z]{1,2}\s*\))?\s+of\s+the\s+" + _t[:-1] + r")"],
    "N1": [_t, near(r"\b(?:atrocity case|special court under the SC/ST Act|caste-based abuse|intentional insult or intimidation)\b", r"(?:(?-i:\bSC\b|\bST\b)|scheduled caste|scheduled tribe|public view|SC/ST Act)", 100)],
    "N2_extra": [r"\bcaste[- ](?:name|abuse|slur|insult|based|discrimination)\b", r"\bbecause of (?:my |his |her |their )?caste\b", r"\b(?:dalit|adivasi)\b", r"\bscheduled (?:castes?|tribes?)\b", near(r"\batrocit(?:y|ies)\b", r"\b(?:caste|tribe|tribal|dalit)\b", 100)],
    "N2_exclude": None,
}
# ------------------------------------------------------------------ NI Act
_t = r"(?:Negotiable Instruments Act|(?-i:\bNI Act\b|\bN\.I\. Act\b))"
SPEC["NI Act"] = {
    "name": "Negotiable Instruments Act, 1881 (section 138)",
    "passage": [_t, near(r"\bsection\s*138\b", r"(?:Negotiable Instruments|(?-i:NI Act))", 80), r"\bcomplaint under section\s*138\b", near(r"\bdishonou?r of (?:the |a )?cheque\b", r"(?:statutory notice|legally enforceable debt|Negotiable Instruments)", 100)],
    "N1": [_t, near(r"\bcheques?\b", r"\b(?:bounc\w+|dishonou?r\w*)\b", 60), r"\bsection\s*138\b", near(r"\bcheque\b", r"\b(?:returned unpaid|statutory notice|demand notice|drawer|payee)\b", 100)],
    "N2_extra": [near(r"\bcheques?\b", r"\b(?:returned|unpaid|insufficient funds|not enough money|no balance|stopped payment|legal notice)\b", 100)],
    "N2_exclude": None,
}
# ------------------------------------------------------------------ PMLA
_t = r"(?:Prevention of Money[- ]?Laundering Act|(?-i:\bPMLA\b))"
SPEC["PMLA"] = {
    "name": "Prevention of Money-Laundering Act, 2002",
    "passage": [_t, near(r"\bproceeds of crime\b", r"\b(?:scheduled offence|laundering|attachment|confiscation)\b", 100), near(r"\bmoney[- ]laundering\b", r"\b(?:proceeds of crime|scheduled offence|Enforcement Directorate|provisional attachment)\b", 120),
                r"\bsections?\s*(?:3|4|5|8|17|19|24|44|45|50|66|70)\s+of\s+the\s+" + _t[:-1] + r")"],
    "N1": [_t, r"\bmoney[- ]laundering\b", r"\bproceeds of crime\b", near(r"\bprovisional attachment\b", r"\b(?:PMLA|money laundering|proceeds of crime)\b", 100), near(r"\bEnforcement Directorate\b", r"\b(?:PMLA|money laundering|proceeds of crime|attachment)\b", 100)],
    "N2_extra": [near(r"(?-i:\bED\b)", r"\b(?:attach\w*|froze|frozen|arrest\w*|summon\w*|question\w*|raid\w*|case|notice|bail)\b", 60), r"\bEnforcement Directorate\b"],
    "N2_exclude": None,
}
# ------------------------------------------------------------------ UAPA
_t = r"(?:(?-i:\bUAPA\b)|Unlawful Activities \(Prevention\) Act)"
SPEC["UAPA"] = {
    "name": "Unlawful Activities (Prevention) Act, 1967",
    "passage": [_t, r"\bsection\s*43D\s*\(\s*5\s*\)", near(r"\bterrorist act\b", r"(?:\bUAPA\b|\bsection\s*1[56]\b)", 100), near(r"\bterrorist organisation\b", r"(?:\bUAPA\b|\bSchedule\b|\bmembership\b)", 100),
                r"\bsections?\s*(?:10|13|15|16|17|18|20|38|39|40|43D|43E)\s+of\s+the\s+" + _t[:-1] + r")"],
    "N1": [_t, near(r"\bterrorist act\b", r"\b(?:UAPA|unlawful activities|terrorist organisation|section\s*43D)\b", 100), near(r"\bterrorist organisation\b", r"\b(?:UAPA|unlawful activities|membership|funding)\b", 100), r"\bsection\s*43D\s*\(\s*5\s*\)"],
    "N2_extra": [r"\banti[- ]terror (?:law|act)\b", near(r"\bterror\w*", r"\b(?:booked|arrested|accused|charged|FIR|bail|case)\b", 60), r"\bbanned\s+(?:our\s+|the\s+|an?\s+)?(?:organi[sz]ation|group|association)\b", r"\bterror funding\b", near(r"\b(?:separatist|unlawful association)\b", r"\b(?:arrest\w*|accused|booked|supporting|member\w*|belong\w*|links?)\b", 60)],
    "N2_exclude": None,
}
# ------------------------------------------------------------------ DPA
_t = r"(?:Dowry Prohibition Act|(?-i:\bDP Act\b))"
SPEC["DPA"] = {
    "name": "Dowry Prohibition Act, 1961",
    "passage": [_t, r"\bprohibition of the giving or taking of dowry\b"],
    "N1": [_t, near(r"\bdowry\b", r"\b(?:demand\w*|giving|taking|agreement|section\s*[34])\b", 100), near(r"\bsection\s*[34]\b", r"\b(?:Dowry Prohibition Act|dowry demand|giving or taking dowry)\b", 80)],
    "N2_extra": [r"\bdowry\b"],
    "N2_exclude": None,
}
# ------------------------------------------------------------------ JJ Act
_t = r"(?:Juvenile Justice\s*(?:\(Care and Protection of Children\))?\s*Act|(?-i:\bJJ Act\b|\bJJB\b))"
SPEC["JJ Act"] = {
    "name": "Juvenile Justice (Care and Protection of Children) Act, 2015",
    "passage": [_t, r"\bjuvenile justice board\b", r"\bchild in conflict with law\b", r"\bchild in need of care and protection\b", near(r"\bpreliminary assessment\b", r"\bjuvenile justice\b", 100)],
    "N1": [_t, r"\bjuvenile justice board\b", r"\bchild in conflict with law\b", r"\bchild in need of care and protection\b", near(r"\bjuvenile\b", r"\b(?:Juvenile Justice Act|board|observation home|place of safety|child in conflict with law)\b", 100)],
    "N2_extra": [r"\bjuvenile\b", near(r"\b(?:1[0-7]|[5-9])[- ]?year[- ]?old\b", r"\b(?:arrest\w*|accused|custody|theft|fight|jail)\b", 60), near(r"\bminor\b", r"\b(?:arrested|accused|custody|jail)\b", 40), r"\bobservation home\b", r"\b(?:proof of age|age determination)\b"],
    "N2_exclude": r"\b(?:sexual\w*|touch\w*|molest\w*|rape\w*|abus\w*)\b",
}
# ------------------------------------------------------------------ PC Act
_t = r"(?:Prevention of Corruption Act|(?-i:\bPC Act\b))"
SPEC["PC Act"] = {
    "name": "Prevention of Corruption Act, 1988",
    "passage": [_t, r"\bsections?\s*(?:7|7A|8|9|11|12|13|17|17A|19|20)\s+of\s+the\s+" + _t[:-1] + r")", near(r"\bdisproportionate assets\b", r"\b(?:known sources? of income|public servant|PC Act|check period)\b", 100)],
    "N1": [_t, near(r"\bdisproportionate assets\b", r"\b(?:public servant|Prevention of Corruption Act|PC Act|check period|known sources? of income)\b", 100), near(r"\b(?:illegal gratification|undue advantage)\b", r"\b(?:public servant|PC Act|Prevention of Corruption Act|trap case)\b", 100),
           near(r"\btrap case\b", r"\b(?:bribe|public servant|PC Act)\b", 100), near(r"\b(?:previous|prior)\s+(?:approval|sanction)\b", r"\b(?:PC Act|Prevention of Corruption Act)\b", 100)],
    "N2_extra": [r"\bbribe\w*", r"\billeg(?:al)? gratification\b", r"\bdisproportionate assets\b", r"\banti-?corruption\b", r"\bvigilance\b", near(r"\b(?:officer|official|clerk|inspector|government employee|public servant)\b", r"\b(?:asked for|demanded|took|accepting|accepted)\b.{0,30}\b(?:money|bribe|commission|percentage)\b", 80),
                 near(r"\b(?:pending work|expedite official work)\b", r"\b(?:demand|bribe|undue advantage|public servant|illegal gratification)\b", 100)],
    "N2_exclude": None,
}
# ------------------------------------------------------------------ Arms Act
SPEC["Arms Act"] = {
    "name": "Arms Act, 1959",
    "passage": [r"\bArms Act\b", r"\bunlicensed firearm\b|\bpossession of an unlicensed\b", near(r"\bfirearm\b", r"\b(?:licen[cs]e|section\s*25|section\s*27)\b", 100)],
    "N1": [r"\bArms Act\b", near(r"\bfirearm\b", r"\b(?:licen[cs]e|possession|seizure|ammunition)\b", 100), near(r"\b(?:pistol|revolver|country[- ]made (?:gun|pistol|weapon)|cartridges?|ammunition)\b", r"\b(?:Arms Act|licen[cs]e|seiz\w+|possession)\b", 100)],
    "N2_extra": [near(r"\b(?:gun|pistol|revolver|rifle|firearm|bullets?|cartridges?)\b", r"\b(?:found|recovered|seized|caught|car|bag|police|carrying|without)\b", 80)],
    "N2_exclude": None,
}
# ------------------------------------------------------------------ IT Act
_t = r"(?:Information Technology Act|(?-i:\bIT Act\b))"
_itctx = r"(?:(?-i:\bIT Act\b)|Information Technology|\bcyber|\bonline\b|\bcomputer\b|\belectronic\b|\binternet\b|social media|\bvideo\b|\bphoto)"
SPEC["IT Act"] = {
    "name": "Information Technology Act, 2000",
    "passage": [_t, r"\bsections?\s*(?:43|66|66C|66D|66E|67|67A|67B|69A|72|79)\s+of\s+the\s+" + _t[:-1] + r")"],
    "N1": [_t, near(r"\bcyber(?:crime| fraud|stalking|harassment)\b", r"(?:\bIT Act\b|Information Technology Act|computer resource|electronic record)", 100), r"\b(?:identity theft|cheating by personation using (?:a )?computer resource)\b", near(r"\bsection\s*(?:66C|66D|67A|67B|69A)\b", _itctx, 100)],
    "N2_extra": [r"(?-i:\bOTP\b)", r"(?-i:\bUPI\b)", r"\bhack(?:ed|ing)\b", r"\bonline (?:scam|fraud|cheating)\b", r"\bphishing\b", r"\bmorphed\b", r"\bfake (?:profile|account)\b", r"\bcyber\w*"],
    "N2_exclude": None,
    "label_exclude_passage": r"\bsection\s*66A\b",     # a judgment with 3+ such passages is not labelled (struck down 2015)
}
# ------------------------------------------------------------------ MV Act
_t = r"(?:Motor Vehicles Act|(?-i:\bMV Act\b))"
SPEC["MV Act"] = {
    "name": "Motor Vehicles Act, 1988",
    "passage": [_t],
    "N1": [_t, r"\bdrunk(?:en)? driving\b", r"\bdriving without a valid licen[cs]e\b", near(r"\bsection\s*(?:184|185)\b", r"(?:Motor Vehicles Act|\bMV Act\b|drunk|driving licen[cs]e)", 100)],
    "N2_extra": [r"\brash (?:and negligent )?driving\b", r"\bhit[- ]and[- ]run\b", r"\bdriving without (?:a )?licen[cs]e\b", r"\bdangerous driving\b", r"\bdrunk and driv\w+", r"\bdriving (?:after|under the influence)\b", near(r"\baccident\b", r"\b(?:drunk|alcohol|drinking)\b", 60)],
    "N2_exclude": None,
}

ACTS = list(SPEC)


def _compile(pats):
    return [re.compile(p, FLAGS) for p in pats]


COMPILED = {a: {"passage": _compile(s["passage"]), "N1": _compile(s["N1"]), "N2_extra": _compile(s["N2_extra"]), "N2_exclude": re.compile(s["N2_exclude"], FLAGS) if s.get("N2_exclude") else None,
                "label_exclude": re.compile(s["label_exclude_passage"], FLAGS) if s.get("label_exclude_passage") else None} for a, s in SPEC.items()}


def question_acts(q, tier):
    """{act: [index of the first anchor that fired]} for tier 'N1' (precise) or 'N2' (precise or plain-language, with each Act's exclusion guard on the plain-language part)."""
    out = {}
    for a, c in COMPILED.items():
        hit = next((i for i, p in enumerate(c["N1"]) if p.search(q)), None)
        if hit is not None:
            out[a] = ["N1", hit]
        elif tier == "N2" and not (c["N2_exclude"] and c["N2_exclude"].search(q)):
            hit = next((i for i, p in enumerate(c["N2_extra"]) if p.search(q)), None)
            if hit is not None:
                out[a] = ["N2", hit]
    return out


def passage_acts(text):
    """The Acts whose strong marker the passage carries."""
    return {a for a, c in COMPILED.items() if any(p.search(text) for p in c["passage"])}


def judgment_labels(passages):
    """passages: iterable of (doc, text_hash, text). Returns {act: set(docs)} where the judgment has LABEL_MIN or more DISTINCT marked passages (and the IT Act's 66A exclusion holds)."""
    count = {a: {} for a in COMPILED}
    excl = {}
    seen = set()
    for doc, h, text in passages:
        if (doc, h) in seen:
            continue
        seen.add((doc, h))
        for a in passage_acts(text):
            count[a].setdefault(doc, set()).add(h)
        c = COMPILED["IT Act"]["label_exclude"]
        if c.search(text):
            excl[doc] = excl.get(doc, 0) + 1
    out = {}
    for a in COMPILED:
        docs = {d for d, hs in count[a].items() if len(hs) >= LABEL_MIN}
        if a == "IT Act":
            docs = {d for d in docs if excl.get(d, 0) < 3}
        out[a] = docs
    return out


def export():
    return {"version": "v2 draft 2026-10-12", "label_min": LABEL_MIN, "flags": "IGNORECASE|DOTALL; acronyms case-sensitive via (?-i:...)", "acts": {a: {k: v for k, v in s.items()} for a, s in SPEC.items()}}
