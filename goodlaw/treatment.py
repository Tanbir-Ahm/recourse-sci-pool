"""What a later judgment does with an earlier one, read from the sentence that names it.

`classify(sentence, (start, end))` takes one flattened sentence and the character span of the mention of the target case in it, and returns the
strongest treatment found near the mention, the exact words that show it (the cue), and flags that say how far to trust it:

    OVERRULES      "stands overruled", "is not good law", "per incuriam", "wrongly decided", "no longer good law"
    DISAGREES      "we are unable to subscribe to the view", "does not agree", "is not borne out", "cannot be accepted", "erroneous"
    DOUBTS_REFERS  "doubt the correctness", "needs reconsideration", "referred to a larger bench"
    LEGISLATIVE    the sentence ties the case to an amendment or Act that overcame it
    DISTINGUISHES  "distinguished", "has no application", "different on facts"
    LIMITS         "clarified", "explained", "confined to", "must be read in the context"
    FOLLOWS        "followed", "approved", "reaffirmed", "relied upon", "in consonance with"
    NOT_OVERRULED  "has not been overruled", "continues to hold the field", "remains good law"
    NEUTRAL        named, no cue found

A cue only counts when it is within `MAX_DISTANCE` characters of the mention, and negation flips it ("has not been overruled" is NOT_OVERRULED, not
OVERRULES). Flags: `hedged` (the cue sits in a "whether", "if", "it was argued" frame), `binding` ('weak' when another case is named between the cue and the
target, so the cue may be about that other case). Who is speaking (court, counsel, a lower court, the headnote) and bench strength are decided by the caller
because they need more than one sentence.

Rule-based and conservative on purpose: it is a triage aid and every result carries the words that caused it, so a person can check in seconds.
"""
import re

from . import cites as C

MAX_DISTANCE = 230

I = re.I
RULES = [
    ("OVERRULES", [
        r"\b(?:stand(?:s|ing)?|is|are|was|were|be|been|hereby|also|expressly|accordingly)\s+(?:hereby\s+)?(?:expressly\s+)?overrule[ds]?\b",
        r"\boverrul(?:e|es|ed|ing)\b",
        r"\bno longer (?:a )?good law\b", r"\b(?:is|are|was|were) not (?:a )?good law\b", r"\bnot (?:to be )?(?:treated|regarded|considered) as (?:a )?good law\b",
        r"\bcannot be (?:treated|regarded|considered|said to be) (?:as )?(?:a )?good law\b",
        r"\b(?:does|do|did) not (?:lay down|represent|state|reflect) (?:the )?correct law\b", r"\bdoes not lay down the correct (?:law|proposition)\b",
        r"\b(?:was|were|is|are) (?:wrongly|incorrectly|erroneously) decided\b", r"\bwrongly decided\b", r"\bper incuriam\b",
        r"\b(?:is|are|was|were) (?:hereby )?disapproved\b", r"\bdisapprov(?:e|es|ed|ing)\b", r"\bnot (?:been )?correctly decided\b",
        r"\b(?:stands?|is|are) (?:hereby )?(?:set at naught|nullified|negated|superseded by this)\b",
    ]),
    ("DISAGREES", [
        r"\b(?:unable|not able|not inclined|constrained) to (?:subscribe|agree|concur|accept)\b", r"\b(?:do|does|did|can) not (?:agree|concur|subscribe)\b",
        r"\bnot (?:able )?to agree\b", r"\b(?:respectfully|with respect,?) (?:differ|disagree|dissent)\b", r"\b(?:differ|disagree)s? (?:from|with) the (?:view|reasoning|ratio|decision|opinion)\b",
        r"\b(?:neither|not) borne out\b", r"\bcannot be (?:accepted|sustained|endorsed|approved|upheld|supported)\b", r"\bcannot (?:be )?(?:accept|sustain|endorse|approve|uphold)\b",
        r"\b(?:is|was|are|were) (?:not|neither) (?:sustainable|tenable|correct|right|sound|justified)\b", r"\b(?:erroneous|incorrect|unsound|flawed) (?:view|reasoning|decision|ratio|conclusion|opinion)\b",
        r"\b(?:is|was) erroneous\b", r"\b(?:not|nor) (?:in )?(?:consonance|conformity|accord|keeping|line) with\b", r"\bruns? counter to\b", r"\bcontrary to the (?:law|dictum|ratio|view|decision|principle)s?\b", r"\bnot the correct (?:law|view|position|proposition)\b",
        r"\bdoes not (?:commend|find) (?:itself|favour|acceptance)\b",
    ]),
    ("DOUBTS_REFERS", [
        r"\bdoubt(?:s|ed|ing)? (?:the |as to the |about the )?(?:correctness|soundness|reasoning|ratio|view|decision)\b", r"\bcorrectness of (?:the |that )?(?:view|decision|judgment|ratio)\b",
        r"\b(?:requires?|needs?|merits?|warrants?|calls? for|deserves?) (?:to be )?(?:re-?consider|re-?visit|re-?examin|re-?look|fresh look)\w*",
        r"\b(?:re-?consider(?:ation)?|re-?visit|re-?examin\w+)\b[^.]{0,60}\b(?:decision|view|ratio|judgment|case)\b", r"\blarger bench\b",
        r"\brefer(?:red|ring|s)? (?:the (?:matter|question|issue|case)|it|them) to (?:a |the )?(?:larger|five|seven|nine|constitution|three)",
        r"\breferred to (?:a |the )?(?:larger|five-?judge|seven-?judge|nine-?judge|three-?judge|constitution) bench\b", r"\bfor (?:re-?consideration|re-?examination)\b", r"\bkept in abeyance\b",
    ]),
    ("LEGISLATIVE", [
        r"\b(?:Parliament|Legislature|legislature)\b[^.]{0,120}\b(?:amend\w*|inserted|enacted|substituted|overcame|nullif\w+|remov\w+|in response)\b",
        r"\b(?:amend(?:ed|ment)|Amendment Act|inserted|substituted)\b[^.]{0,120}\b(?:in view of|pursuant to|consequent upon|in the wake of|to (?:overcome|nullify|remove|undo|get over|neutralise))\b",
        r"\b(?:overcome|nullif\w+|neutralis\w+|undo\w*|get over)\b[^.]{0,80}\b(?:effect|decision|judgment|ratio)\b",
    ]),
    ("DISTINGUISHES", [
        r"\bdistinguish(?:ed|able|ing|es)?\b", r"\b(?:has|have) no application\b", r"\b(?:is|are) not applicable\b", r"\binapplicable\b", r"\bnot attracted\b",
        r"\bcannot be (?:applied|invoked|pressed into service|extended)\b", r"\b(?:differ|different)(?:s|ent)? (?:on|from|in) (?:its |their |the )?facts\b",
        r"\bstands? on (?:a )?(?:different|distinct) footing\b", r"\bfacts? (?:of|in) (?:that|the said|the present) case (?:are|were) (?:different|distinct)\b", r"\bdoes not (?:help|assist|advance|apply)\b",
    ]),
    ("LIMITS", [
        r"\bclarif(?:y|ied|ies|ying|ication)\b", r"\bexplain(?:ed|s|ing)?\b", r"\bconfined to\b", r"\bmust be read (?:in|as|with)\b", r"\bto be (?:understood|read) (?:in|as)\b",
        r"\brestricted to\b", r"\bread(?:ing)? down\b", r"\blimited to the facts\b", r"\bnot (?:to be )?(?:read|treated) as laying down\b",
    ]),
    ("FOLLOWS", [
        r"\bfollow(?:ed|ing|s)?\b", r"\bapprov(?:ed|ing|es|al)\b", r"\breaffirm(?:ed|ing|s)?\b", r"\breiterat(?:ed|es|ing)\b", r"\baffirm(?:ed|ing|s)?\b",
        r"\bin consonance with\b", r"\bin (?:line|conformity|accord) with\b", r"\bin (?:respectful )?agreement with\b", r"\b(?:rightly|correctly) (?:held|laid down|decided|observed|stated)\b",
        r"\brelied (?:upon|on)\b", r"\bapplying the (?:ratio|principle|law|test)\b", r"\b(?:ratio|law|principles?|test|dictum|view) (?:laid down|enunciated|propounded|culled out|settled)\b",
        r"\bsquarely covered\b", r"\bsettled by\b", r"\bbinding (?:precedent|on us)\b", r"\bwe (?:respectfully )?agree with\b",
    ]),
]
NOT_OVERRULED_RULES = [
    r"\b(?:has|have|had) not been (?:overruled|doubted|disapproved|diluted|set aside|reconsidered|departed from|watered down)\b",
    r"\b(?:never|nowhere|not) (?:been )?(?:overruled|doubted|disapproved)\b", r"\bcontinues? to (?:hold the field|be (?:a )?good law|be binding|govern)\b",
    r"\bremains? (?:a )?(?:good law|binding|the law)\b", r"\bstill (?:holds|holds the field|good law|binding)\b", r"\bhas (?:stood|withstood) the test of time\b",
    r"\bcannot be said to have been (?:overruled|doubted|diluted)\b", r"\bnot (?:been )?(?:overruled|doubted)\b",
]
_COMPILED = [(label, [re.compile(p, I) for p in pats]) for label, pats in RULES]
_NOT_OVERRULED = [re.compile(p, I) for p in NOT_OVERRULED_RULES]
PRIORITY = ["OVERRULES", "DISAGREES", "DOUBTS_REFERS", "LEGISLATIVE", "DISTINGUISHES", "LIMITS", "FOLLOWS"]
STRENGTH = {"OVERRULES": 6, "DISAGREES": 5, "DOUBTS_REFERS": 4, "LEGISLATIVE": 3, "DISTINGUISHES": 2, "LIMITS": 1, "FOLLOWS": 0}

_RELATIONAL = re.compile(r"\b(?:(?:not|nor) (?:in )?(?:consonance|conformity|accord|keeping|line) with|runs? counter to|contrary to the)\b", I)
_NEGATION = re.compile(r"\b(?:not|never|nowhere|cannot|can not|nor|hardly|no|without)\b(?:\s+\w+){0,3}\s*$", I)
_HEDGE = re.compile(r"\b(?:if|whether|unless|until|even if|as if|suggest(?:s|ed|ing)?|argue[sd]?|contend(?:s|ed|ing)?|submit(?:s|ted)?|urge[sd]?|plea|alleg\w+|claim\w*|"
                    r"possib\w+|might|may|could|would|should|question (?:of|whether))\b(?:\s+\w+){0,6}\s*$", I)
_NOT_ABOUT_CASE = re.compile(r"\boverrul\w*\s+(?:the |that |this |his |her |their |any )?(?:objections?|plea|contention|ground|submission|argument|claim|preliminary)", I)
_OTHER_CASE = re.compile(r"\b[A-Z][\w.'&-]*(?:\s+[A-Za-z.'&()-]+){0,5}?\s+(?:v\.?|vs\.?|versus)\s+[A-Z]")


def _other_mentions(sentence, target):
    """Spans of other case names or citations in the sentence (not overlapping the target's span)."""
    spans = [(m.start(), m.end()) for m in _OTHER_CASE.finditer(sentence)]
    spans += [(s, e) for _, s, e in C.find_cites(sentence)]
    return [(s, e) for s, e in spans if e <= target[0] or s >= target[1]]


def _distance(span, target):
    if span[0] >= target[1]:
        return span[0] - target[1]
    if span[1] <= target[0]:
        return target[0] - span[1]
    return 0


_COORD = re.compile(r"\s*(?:,|;|and|&|as well as|as also|and also|also|,\s*and)?\s*", re.I)


def _binding(cue, others, target, sentence):
    """'weak' when another case, not coordinated with the target, is nearer to the cue than the target is (the cue may be about that other
    case); 'strong' otherwise. Mentions joined by 'and', '&' or commas, with or without citations, count as one group ("A, B and C stand overruled")."""
    lo, hi = target
    mentions = sorted(others)
    changed = True
    while changed:
        changed = False
        for s, e in mentions:
            if lo <= s and e <= hi:
                continue
            if s >= hi and _COORD.fullmatch(sentence[hi:s] or ""):
                hi, changed = e, True
            elif e <= lo and _COORD.fullmatch(sentence[e:lo] or ""):
                lo, changed = s, True
    group = (lo, hi)
    d_group = _distance(cue, group)
    return "weak" if any(not (lo <= s and e <= hi) and _distance(cue, (s, e)) <= d_group for s, e in mentions) else "strong"


def classify(sentence, target):
    """-> dict(label, cue, cue_span, negated, hedged, binding, all) for one flattened sentence and the (start, end) of the target mention in it."""
    others = _other_mentions(sentence, target)
    found = []
    for label, patterns in _COMPILED:
        for rx in patterns:
            for m in rx.finditer(sentence):
                span = (m.start(), m.end())
                if _distance(span, target) > MAX_DISTANCE:
                    continue
                if label == "OVERRULES" and _NOT_ABOUT_CASE.search(sentence[max(0, m.start() - 10):m.end() + 40]):
                    continue
                before = sentence[max(0, m.start() - 45):m.start()]
                negated = bool(_NEGATION.search(before)) and label in ("OVERRULES", "DISAGREES", "DOUBTS_REFERS", "DISTINGUISHES")
                # cues that already contain a negation ("not good law", "not borne out") are not flipped by it
                if re.match(r"(?:not|no longer|neither|cannot|do(?:es)? not|did not|is not|are not|was not|were not)\b", m.group(0), I) or re.search(r"\bnot\b", m.group(0), I):
                    negated = False
                hedged = bool(_HEDGE.search(before))
                binding = _binding(span, others, target, sentence)
                if label == "DISAGREES" and _RELATIONAL.search(m.group(0)) and span[1] <= target[0]:
                    # "X is not in consonance with T": T is the standard X is measured against, so this supports T
                    found.append({"label": "FOLLOWS", "was": "DISAGREES", "cue": m.group(0), "cue_span": span, "negated": False, "hedged": hedged, "binding": binding, "distance": _distance(span, target)})
                    continue
                found.append({"label": label, "cue": m.group(0), "cue_span": span, "negated": negated, "hedged": hedged, "binding": binding, "distance": _distance(span, target)})
    for rx in _NOT_OVERRULED:
        for m in rx.finditer(sentence):
            if _distance((m.start(), m.end()), target) <= MAX_DISTANCE:
                found.append({"label": "NOT_OVERRULED", "cue": m.group(0), "cue_span": (m.start(), m.end()), "negated": False, "hedged": bool(_HEDGE.search(sentence[max(0, m.start() - 45):m.start()])),
                              "binding": _binding((m.start(), m.end()), others, target, sentence), "distance": _distance((m.start(), m.end()), target)})
    # "X is neither borne out ... nor in consonance with T": the cues before the relational one are about X, not about T
    gov = [f for f in found if f.get("was") == "DISAGREES" and f["label"] == "FOLLOWS" and f["distance"] <= 80]
    if gov:
        first = min(f["cue_span"][0] for f in gov)
        found = [f for f in found if f in gov or f["label"] not in ("OVERRULES", "DISAGREES", "DOUBTS_REFERS") or f["cue_span"][0] >= first]
    # a negated adverse cue is the opposite statement: "has not been overruled" says the case stands; "cannot be distinguished" says it governs
    for f in found:
        if f["negated"]:
            if f["label"] in ("OVERRULES", "DISAGREES", "DOUBTS_REFERS"):
                f["was"], f["label"] = f["label"], "NOT_OVERRULED"
            elif f["label"] == "DISTINGUISHES":
                f["was"], f["label"] = f["label"], "FOLLOWS"
    if not found:
        return {"label": "NEUTRAL", "cue": None, "cue_span": None, "negated": False, "hedged": False, "binding": "strong", "distance": None, "all": []}

    def rank(f):
        base = STRENGTH.get(f["label"], -1) if f["label"] != "NOT_OVERRULED" else 3.5
        return (base - (0.5 if f["hedged"] else 0) - (0.4 if f["binding"] == "weak" else 0), -f["distance"])

    best = max(found, key=rank)
    out = dict(best)
    out["all"] = [(f["label"], f["cue"]) for f in sorted(found, key=rank, reverse=True)]
    return out
