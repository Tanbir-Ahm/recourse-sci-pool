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
    OVERRULED_OTHER the target is the case that did the overruling ("T overruled X"), not the one overruled
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
FAR = 140          # a cue farther than this from the mention is flagged weak

I = re.I
RULES = [
    ("OVERRULES", [
        r"\b(?:stand(?:s|ing)?|is|are|was|were|be|been|hereby|also|expressly|accordingly)\s+(?:hereby\s+)?(?:expressly\s+)?over-?\s?rule[ds]?\b",
        r"(?<!legislatively )(?<!statutorily )\bover-?\s?rul(?:e|es|ed|ing)\b",
        r"\bno longer (?:a )?good law\b", r"\b(?:is|are|was|were) not (?:a )?good law\b", r"\bnot (?:to be )?(?:treated|regarded|considered) as (?:a )?good law\b",
        r"\bcannot be (?:treated|regarded|considered|said to be) (?:as )?(?:a )?good law\b",
        r"\b(?:does|do|did) not (?:lay down|represent|state|reflect) (?:the )?correct law\b", r"\bdoes not lay down the correct (?:law|proposition)\b",
        r"\b(?:was|were|is|are) (?:wrongly|incorrectly|erroneously) decided\b", r"\bwrongly decided\b", r"\bper incuriam\b",
        r"\b(?:is|are|was|were) (?:hereby )?disapproved\b", r"\bdisapprov(?:e|es|ed|ing)\b", r"\bnot (?:been )?correctly decided\b", r"\bnot (?:rightly|properly) decided\b",
        r"\b(?:stands?|is|are) (?:hereby )?(?:set at naught|nullified|negated|superseded by this)\b",
    ]),
    ("DISAGREES", [
        r"\bheld (?:to be )?(?:incorrect|erroneous|wrong|bad law)\b", r"\bdissent(?:ed|s|ing)? from\b", r"\bnot followed\b", r"\b(?:cannot|can not|could not|should not|ought not to) be followed\b",
        r"\b(?:unable|not able|not inclined|constrained) to (?:subscribe|agree|concur|accept)\b", r"\b(?:do|does|did|can) not (?:agree|concur|subscribe)\b",
        r"\bnot (?:able )?to agree\b", r"\b(?:respectfully|with respect,?) (?:differ|disagree|dissent)\b", r"\b(?:differ|disagree)s? (?:from|with) the (?:view|reasoning|ratio|decision|opinion)\b",
        r"\b(?:neither|not) borne out\b", r"\bcannot be (?:accepted|sustained|endorsed|approved|upheld|supported)\b", r"\bcannot (?:be )?(?:accept|sustain|endorse|approve|uphold)\b",
        r"\b(?:is|was|are|were) (?:not|neither) (?:sustainable|tenable|correct(?! to (?:say|read|hold|think|suggest|contend|assume|infer|conclude))|right|sound|justified)\b", r"\b(?:erroneous|incorrect|unsound|flawed) (?:view|reasoning|decision|ratio|conclusion|opinion)\b",
        r"\b(?:is|was) erroneous\b", r"\b(?:not|nor) (?:in )?(?:consonance|conformity|accord|keeping|line) with\b", r"\bruns? counter to\b", r"\bcontrary to the (?:law|dictum|ratio|view|decision|principle)s?\b", r"\bnot the correct (?:law|view|position|proposition)\b",
        r"\bdoes not (?:commend|find) (?:itself|favour|acceptance)\b",
        r"\bcannot be said to have been (?:correctly|properly|rightly) (?:appreciated|decided|understood|laid down|interpreted|construed|stated)\b",
        r"\bcannot be (?:accepted|taken|regarded|treated|said) as laying down (?:the )?(?:law|correct law) correctly\b", r"\b(?:do|does|did) not lay down the law correctly\b",
    ]),
    ("DOUBTS_REFERS", [
        r"\bdoubt(?:s|ed|ing)? (?:the |as to the |about the )?(?:correctness|soundness|reasoning|ratio|view|decision)\b", r"\bcorrectness of (?:the |that )?(?:view|decision|judgment|ratio)\b",
        r"\b(?:requires?|needs?|merits?|warrants?|calls? for|deserves?) (?:to be )?(?:re-?consider|re-?visit|re-?examin|re-?look|fresh look)\w*",
        r"\b(?:re-?consider(?:ation)?|re-?visit|re-?examin\w+)\b[^.]{0,60}\b(?:decision|view|ratio|judgment|case)\b",
        r"\brefer(?:red|ring|s)? (?:the (?:matter|question|issue|case)|it|them) to (?:a |the )?(?:larger|five|seven|nine|constitution|three)",
        r"\b(?:placed|laid|sent|put) (?:it |them |the (?:matter|question|issue|case) )?before (?:a |the )?(?:larger|five|seven|nine|constitution)",
        r"\breferred to (?:a |the )?(?:larger|five-?judge|seven-?judge|nine-?judge|three-?judge|constitution) bench\b(?!\s+(?:decision|judgment|ruling|case|opinion|authority|in\b))", r"\bfor (?:re-?consideration|re-?examination)\b", r"\bkept in abeyance\b", r"\bdoubted\b",
    ]),
    ("LEGISLATIVE", [
        r"\b(?:legislatively|statutorily)\s+(?:over-?\s?rul\w+|nullif\w+|negated|reversed|superseded|set aside|undone|abrogated)\b",
        r"\b(?:Parliament|Legislature|legislature)\b[^.]{0,120}\b(?:amend\w*|inserted|enacted|substituted|overcame|nullif\w+|remov\w+|in response)\b",
        r"\b(?:amend(?:ed|ment)|Amendment Act|inserted|substituted)\b[^.]{0,120}\b(?:in view of|pursuant to|consequent upon|in the wake of|to (?:overcome|nullify|remove|undo|get over|neutralise))\b",
        r"\b(?:overcome|nullif\w+|neutralis\w+|undo(?:es|ing|ne)?|get over)\b[^.]{0,80}\b(?:effect|decision|judgment|ratio)\b",
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
        r"(?<!\bas )(?<!\bthe )\bfollow(?:ed|ing|s)?\b(?!\s+(?:an?\s+)?(?:paragraphs?|paras?|passages?|observations?|extracts?|words|terms|reasons?|questions?|issues?|points?|manner|order|directions?|principles?|propositions?|consistent|suit)\b)", r"\bapprov(?:ed|ing|es|al)\b", r"\breaffirm(?:ed|ing|s)?\b", r"\breiterat(?:ed|es|ing)\b", r"\baffirm(?:ed|ing|s)?\b",
        r"\bin consonance with\b", r"\bin (?:line|conformity|accord) with\b", r"\bin (?:respectful )?agreement with\b", r"\b(?:rightly|correctly) (?:held|laid down|decided|observed|stated)\b",
        r"\brelied (?:upon|on)\b", r"\bapplying the (?:ratio|principle|law|test)\b", r"\b(?:ratio|law|principles?|test|dictum|view) (?:laid down|enunciated|propounded|culled out|settled)\b",
        r"\bsquarely covered\b", r"\bsettled by\b", r"\bbinding (?:precedent|on us)\b", r"\bwe (?:respectfully )?agree with\b",
    ]),
]
NOT_OVERRULED_RULES = [
    r"\bnothing to suggest\b[^;]{0,140}\bover-?\s?rul\w+", r"\bno (?:authority|decision|case|indication|material|ground)\b[^;]{0,80}\bover-?\s?rul\w+", r"\bnot (?:expressly |specifically )?over-?\s?rul\w+",
    r"\b(?:has|have|had) not been (?:overruled|doubted|disapproved|diluted|set aside|reconsidered|departed from|watered down)\b",
    r"\b(?:never|nowhere|not) (?:been )?(?:overruled|doubted|disapproved)\b", r"\bcontinues? to (?:hold the field|be (?:a )?good law|be binding|govern)\b",
    r"\bremains? (?:a )?(?:good law|binding|the law)\b", r"\bstill (?:holds|holds the field|good law|binding)\b", r"\bhas (?:stood|withstood) the test of time\b",
    r"\bcannot be said to have been (?:overruled|doubted|diluted)\b", r"\bnot (?:been )?(?:overruled|doubted)\b",
]
_COMPILED = [(label, [re.compile(p, I) for p in pats]) for label, pats in RULES]
_NOT_OVERRULED = [re.compile(p, I) for p in NOT_OVERRULED_RULES]
PRIORITY = ["OVERRULES", "DISAGREES", "DOUBTS_REFERS", "LEGISLATIVE", "DISTINGUISHES", "LIMITS", "FOLLOWS"]
STRENGTH = {"OVERRULED_OTHER": -0.5, "OVERRULES": 6, "DISAGREES": 5, "DOUBTS_REFERS": 4, "LEGISLATIVE": 3, "DISTINGUISHES": 2, "LIMITS": 1, "FOLLOWS": 0}

_VERB = re.compile(r"over-?\s?rul(?:e|es|ed|ing)|disapprov(?:e|es|ed|ing)", I)
_AUX_IN_CUE = re.compile(r"^(?:stand(?:s|ing)?|is|are|was|were|be|been|hereby|also|expressly|accordingly)\b", I)
_AUX_BEFORE = re.compile(r"\b(?:is|are|was|were|be|been|being|stand|stands|stood|get|gets|got)\s+(?:(?:hereby|also|expressly|specifically|thereby|now|already|since|later|subsequently|virtually|effectively|in effect|clearly|categorically|expressly|finally|neither|never|not|nor|ever|ultimately|partly|partially|in part)\s+)*$", I)


def voice(sentence, cue_span, target):
    """For a cue built on the verb overrule or disapprove: 'patient' if the target is the case overruled ("T was overruled", "overruling T", "T, over-ruled."),
    'agent' if the target is the case that did the overruling ("T overruled X", "overruled by T"). Anything else defaults to 'patient' so that doubt errs towards
    flagging."""
    cue = sentence[cue_span[0]:cue_span[1]]
    before = sentence[max(0, cue_span[0] - 40):cue_span[0]]
    after = sentence[cue_span[1]:cue_span[1] + 90]
    passive = bool(_AUX_IN_CUE.match(cue)) or bool(_AUX_BEFORE.search(before)) or bool(re.match(r"\s*by\b", after))
    if passive:
        gap = target[0] - cue_span[1]
        if 0 <= gap:
            return "agent"                                            # "T was overruled by X / in X": what follows a passive cue is the overruler, not the overruled
        lead = sentence[:target[0]].rstrip()
        between_t = sentence[target[1]:cue_span[0]]
        if (re.search(r"(?:^|\W)in(?:\s+the\s+(?:case|matter|decision|judgment|judgement)\s+of)?$", lead, I) and re.search(r"\b(?:decision|judgment|judgement|view|ruling|case|opinion|observation)s?\b", between_t, I)
                and any(target[1] <= a and b <= cue_span[0] for a, b in _other_mentions(sentence, target))):
            return "agent"                                            # "In T, the decision of Y has been overruled": T is where Y was overruled
        return "patient"
    if target[1] <= cue_span[0]:                                   # target before an active verb
        if re.match(r"\s*(?:[;.,:)]|$|Paras?\.?\s*\d)", sentence[cue_span[1]:cue_span[1] + 10]):
            return "patient"                                          # headnote style: "T, [cite], over-ruled." or "T over-ruled, because ..."
        if re.match(r"\s+(?:in|by)\s+(?:\[\d{4}\]|\(\d{4}\)|\d{4}\b|[A-Z][\w.&'-]*(?:\s+[A-Za-z.&'-]+){0,5}?\s+v\.?\s)", sentence[cue_span[1]:cue_span[1] + 60]):
            return "patient"                                          # "T, [cite], over-ruled in [cite]": the overruler is cited after the verb
        return "agent"
    between = sentence[cue_span[1]:target[0]]
    if re.match(r"\s*(?:in|by)\s*$", between):
        return "agent"                                                # "its partial overruling in T", "overruled by T": T is the case that did it
    if _GROUND.search(between[-60:]):
        return "agent"                                                # "overruled X in view of T": T is the reason, not the case overruled
    if "," in between or re.search(r"\b(?:and|but|while|whereas|which|that|held|holding|observed|said|stated|decided|ruled)\b", between, I):
        return "agent"                                                # "overruled its previous decision in X and held in Maneka Gandhi...": T is not the object
    return "patient"                                                  # "overruling T", "overruled the decision in T"


_AUTHORITY = re.compile(r"\b(?:curtail\w*|dilut\w*|restrict\w*|depart\w* from|deviat\w+ from|ignor\w+|overlook\w+|in ignorance of|disregard\w*(?: of)?|without (?:considering|noticing|referring to|adverting to|taking note of)|contrary to|in (?:(?:direct|open|complete|clear|sharp)\s+)?(?:conflict|contravention|violation|breach) (?:with|of)|inconsistent with|bypass\w*|failed to (?:consider|notice|follow)|did not (?:consider|notice|follow))\b(?:[\s,]+\w+){0,10}?[\s,]*$", I)
_PROPOSITION = re.compile(r"\b(?:held|observed|said|stated|decided|ruled|laid down|opined|noted|reiterated|concluded|took the view)\s+that\b", I)
_BLOCK_BETWEEN = re.compile(r"\b(?:and|reiterated|that|because|since|though|although|but|while|whereas|contention|argument|submission|stand|plea|counsel|learned|held|observed|said|stated|hold|holds|is|was|are|were|has|have|had|been|being|if|when|where|therefore|thus)\b", re.I)
_BLOCK_BEFORE = re.compile(r"\b(?:because|since|in view of|having regard|therefore|but|while|whereas|when|if|though|although|contention|argument|submission|counsel|good law|over-?\s?rul\w*|incuriam|wrongly decided)\b", re.I)


_VIEW_RELATIVE = re.compile(r"^\s*(?:to\s+)?(?:the\s+)?(?:view|opinion|reasoning|ratio|finding|conclusion|proposition|law|interpretation)\s+(?:which|that)\s+(?:has been|have been|was|were|is|had been)\s+(?:adopted|taken|expressed|laid down|held|propounded|rendered|given|enunciated|stated|arrived at)\s+(?:by\s+[\w\s.]{0,40}?)?in\s+(?:the\s+)?(?:above|said|aforesaid|earlier|previous|abovementioned)?\s*(?:decision|judgment|judgement|case)?\s*(?:of\s+this\s+Court\s+)?(?:in\s+)?$", I)
_RELATIVE_HELD = re.compile(r"\b(?:which|who|that)\s+(?:had\s+|have\s+)?(?:held|observed|laid down|decided|ruled|took the view|propounded)\s+that\b", I)   # "judgments in T, which held that ..., do not lay down the correct law": the clause describes T and the verdict is on T
_HELD_IN = re.compile(r"\b(?:held|observed|said|stated|decided|ruled|laid down|opined|noted|reiterated|concluded|pointed out|explained|clarified)\b[^.;]{0,40}?\b(?:in|by)\s+(?:the\s+(?:case|decision|judgment)\s+of\s+)?$", I)
_COMPLIANCE = re.compile(r"\b(?:mandate|directions?|guidelines?|norms?|procedure|requirements?|safeguards?|dictum|law laid down|principles?)\b", I)
_LOWER_ACTOR = re.compile(r"\b(?:High Court|Tribunal|Trial Court|trial court|Sessions|Magistrate|learned (?:Single )?Judge|Single Judge|Collector|Commissioner|Government|Board|State|Officer|authorit(?:y|ies)|Municipality|Corporation|accused|appellants?|respondents?|assessee|courts below|Court of Appeal|first appellate)\b", I)   # who "did not follow T": a body bound by T, so T is the authority it ignored
_DOUBLE_NEG = re.compile(r"\b(?:not|never|cannot|hardly)\b[^.;]{0,60}?\b(?:justified|right|entitled|inclined|free|at liberty|able|competent)\s+in\s+not\s*$", I)
_PRONOUN_SUBJECT = re.compile(r"\b(?:but|and|yet|however|though|while)\s+(?:it|this|that|the same)\s+(?:was|has been|had been|is|were)\s*$", I)
_AFFIRMING = re.compile(r"\b(?:affirm\w*|uphold\w*|upheld|approv\w+|confirm\w*|endors\w+|reiterat\w+|sustain\w*|accept\w*|reaffirm\w*|vindicat\w+)\s+(?:\w+\s+){0,2}$", I)
_GROUND = re.compile(r"\b(?:in view of|in the light of|on the strength of|on the basis of|by reason of|because of|having regard to|on account of|owing to|relying (?:up)?on|based (?:up)?on|in accordance with|in terms of)\b", I)
_BY_AUTHORITY = re.compile(r"^\s*(?:,\s*)?by\s+(?:(?i:(?:this|the|a|an|the said)\s+(?:\w+\s+){0,3}?(?:Court|Bench|Judges?)\b[\w\s,]{0,25}?)|(?:[A-Z][\w.]*,?\s+){1,4}(?:C\.?\s?J\.?(?:I\.?)?|J\.?|JJ\.?),?\s*)\bin\s*(?:(?i:the\s+(?:case|decision|judgment|matter)\s+of\s*))?$")
_IGNORED_MID = re.compile(r"\b(?:ignor\w+|overlook\w+|in ignorance of|disregard\w*|without (?:considering|noticing|referring to|adverting to|taking note of)|failed to (?:consider|notice|follow)|did not (?:consider|notice|follow))\b", I)
_DECISION_IDIOM = re.compile(r"as laying down (?:the )?(?:law|correct law) correctly|lay down the law correctly|no longer (?:a )?good law|(?:is|are|was|were) not (?:a )?good law|not (?:to be )?(?:treated|regarded|considered) as (?:a )?good law|cannot be (?:treated|regarded|considered|said to be) (?:as )?(?:a )?good law|"
                             r"(?:does|do|did) not (?:lay down|represent|state|reflect) (?:the )?correct law|(?:was|were|is|are) (?:wrongly|incorrectly|erroneously) decided|wrongly decided|per incuriam|"
                             r"not (?:been )?correctly decided|not (?:rightly|properly) decided|held (?:to be )?(?:incorrect|erroneous|wrong|bad law)|over-?\s?rul|disapprov", re.I)
_HEADNOTE_WORDS = r"explained|followed|referred to|referred|distinguished|relied on|relied upon|approved|applied|considered|affirmed|partly|partially|since|also|and|but|not|held|observed"


def attached(sentence, span, target):
    """Is a disagreement-type cue about the target, rather than about something the target is merely cited for? A cue after the target must follow it closely
    with no comma, semicolon or reporting word in between ("T cannot be accepted"); a cue before the target must introduce it directly ("unable to subscribe
    to the view taken in T"), not through a clause ("... cannot be accepted, in view of T", "we are unable to agree with counsel that T says ...")."""
    if span[1] <= target[0] and (_GROUND.search(sentence[span[1]:target[0]]) or _BY_AUTHORITY.match(sentence[span[1]:target[0]])):
        return False                                                  # "not tenable having regard to T", "held erroneous by this Court in T": T is the ground or the authority
    if span[0] >= target[1] and (_DECISION_IDIOM.fullmatch(sentence[span[0]:span[1]].strip()) or _DECISION_IDIOM.search(sentence[span[0]:span[1]])):
        return True                                                   # these idioms judge a decision they follow; the distance and clause checks are enough (before the target the usual between-checks apply)
    if span[0] >= target[1]:                                          # target first, then the cue
        if re.search(r"(?:decision|view|ratio|judgment|judgement|case|opinion|holding)s?$", sentence[span[0]:span[1]].strip(), I) and any(span[1] <= a <= span[1] + 40 for a, _ in _other_mentions(sentence, target)):
            return False                                              # "T contains observations which throw doubt on the correctness of the decision in X", "T ... re-examined the ratio of X": X is the object
        between = sentence[target[1]:span[0]]
        if not re.sub(r"\[[^\]]*\]|\([^)]*\)|\d+|S\.?\s?C\.?\s?R\.?|SCC|AIR|SC|Supp\w*|Suppl|\b(?:" + _HEADNOTE_WORDS + r")\b|[\s,.;:=&]+", "", between, flags=re.I):
            return True                                               # a law report's list entry: "T, [1950] S.C.R. 88, held incorrect."
        return len(between) <= 80 and not re.search(r"[;,]", between) and not _BLOCK_BEFORE.search(between)
    between = sentence[span[1]:target[0]]                             # cue first, then the target
    if _VIEW_RELATIVE.match(between):
        return True                                                   # "unable to subscribe to the view which has been adopted in the above decision in T": the view is T's
    if "," in between and re.match(r"referred", sentence[span[0]:span[1]], I):
        return False                                                  # "the issues referred to a larger Bench, referred to hereinabove, the decision in T is to be considered"
    m = re.search(r"\bthat\s+(?:the|its|their|this)\s+(?:decision|view|judgment|ruling|reasoning|ratio|holding)\b(?:\s+\w+){0,4}\s+(?:in|of|by)\s*$", between, re.I)
    if m and len(between[:m.start()].split()) <= 3 and "," not in between[:m.start()]:
        between = re.sub(r"\bthat\b", "", between, count=1, flags=re.I)     # "felt that the decision of this Court in T might need reconsideration" (not "unable to agree with the view of Judge J that the ratio in T ...")
    return len(between) <= 90 and not _BLOCK_BETWEEN.search(between) and not re.search(r"[;]", between)


_RELATIONAL = re.compile(r"\b(?:(?:not|nor) (?:in )?(?:consonance|conformity|accord|keeping|line) with|runs? counter to|contrary to the)\b", I)
_NEG_FOLLOW = re.compile(r"\b(?:not|never|cannot|can not|nor|unable to|neither)\s+(?:be\s+|been\s+|being\s+|have\s+|has\s+|had\s+|to\s+)?(?:at all\s+)?$", I)
_REJECTING = re.compile(r"\b(?:(?:do|does|did)\s+not\s+accede|decline[sd]?|refuse[sd]?|not\s+(?:inclined|persuaded|prepared)|reject(?:s|ed)?\s+the\s+(?:submission|contention|argument|plea|claim)|negativ(?:e|ed)\s+the\s+(?:submission|contention|argument|plea|claim))\b[^.;]{0,140}$", I)
_NOT_A_NEGATION = re.compile(r"\b(?:hesitat\w*|cannot but|can not but|not only|but also|not merely|no doubt|not (?:be )?(?:unmindful|oblivious))\b[^.]{0,25}$", I)
_NEGATION = re.compile(r"\b(?:not|never|nowhere|cannot|can not|neither|nor|hardly|no|without)\b(?:\s+\w+){0,3}\s*$|\b(?:cannot|can not|could not|not|never)\s+be\s+(?:said|held|regarded|understood|construed|inferred|read)\s+(?:to|that)\b[^.;]{0,100}$|\b(?:not|never)\s+(?:prepared|willing|inclined|able)\s+to\s+(?:hold|say|accept|agree)\s+that\b[^.;]{0,100}$|\b(?:nothing|no\s+\w+)\b[^.;]{0,80}\b(?:can|could|would)\s+be\s+(?:said|held|regarded|treated)\s+to\s+be\s*$|\b(?:do|does|did)\s+not\s+accede\b[^.;]{0,140}$|\b(?:decline[sd]?|refuse[sd]?|not\s+(?:inclined|persuaded|prepared))\b[^.;]{0,140}$", I)
_HEDGE = re.compile(r"\b(?:if|in case|in the event|ought|whether|unless|until|till|even if|as if|suggest(?:s|ed|ing)?|argue[sd]?|contend(?:s|ed|ing)?|submit(?:s|ted)?|urge[sd]?|plea|alleg\w+|claim\w*|"
                    r"possib\w+|might|may|could|would|should|question (?:of|whether))\b(?:[\s,.]+\w+){0,10}[\s,]*$", I)
_REPORTED = re.compile(r"\b(?:if|in case|in the event|whether|unless|till|until|pray\w*|suggest\w*|criticism|hypothes\w+|argue\w*|contend\w*|contention\w*|negativ\w+|challeng\w+|submit\w*|urge\w*|plea\w*|alleg\w+|claim\w*|counsel|(?:neither|no|nor|without)\s+(?:the\s+)?(?:need|necessity|occasion))\b", I)


_HEDGE_AFTER = re.compile(r"^[^.;]{0,60}?\b(?:open to doubt|is doubtful|are doubtful|doubtful whether|questionable|debatable|not free from doubt|(?:was|were|is|are|has been|have been)\s+(?:\w+\s+){0,2}?(?:repelled|rejected|negatived|repulsed|turned down|refuted|not accepted))\b", I)


def is_hedged_after(sentence, cue_end):
    """The words after the cue take it back: 'was wrongly decided is open to doubt', 'no longer good law ... was repelled'."""
    return bool(_HEDGE_AFTER.search(sentence[cue_end:cue_end + 120]))


def is_hedged(sentence, cue_start):
    """The cue sits in a reported argument or a conditional: a reporting or conditional word within 200 characters before it with no semicolon or colon between,
    or a modal (may, might, could, would, should) within a few words."""
    before = re.sub(r"\bas it may\b", " ", sentence[max(0, cue_start - 200):cue_start], flags=I)          # "be that as it may" is not a possibility
    last = None
    for m in _REPORTED.finditer(before):
        last = m
    if last and not re.search(r"[;:]", before[last.end():]):
        return True
    return bool(_HEDGE.search(re.sub(r"\bas it may\b", " ", sentence[max(0, cue_start - 90):cue_start], flags=I)))


_NOT_ABOUT_CASE = re.compile(r"\bover-?\s?rul\w*\s+(?:the |that |this |his |her |their |any |all )?(?:objections?|plea|contention|ground|submission|argument|claim|preliminary|order of|decision of the (?:trial|learned|single))|\b(?:contentions?|objections?|pleas?|submissions?|arguments?|grounds?)\b[^.;]{0,80}\b(?:is|are|was|were|stands?)\s+(?:hereby\s+)?over-?\s?rul", I)
_OTHER_CASE = re.compile(r"\b[A-Z][\w.'&-]*(?:\s+[A-Za-z.'&()-]+){0,5}?\s+(?:v\.?|vs\.?|versus)\s+[A-Z]")


_POSSESSIVE_CASE = re.compile(r"\b[A-Z][\w.&'-]*(?:\s+(?:[A-Z][\w.&'-]*|of|and|&|the|Co\.?|Ltd\.?)){0,6}\s*[’']s\s+case\b")


_SUPRA_CASE = re.compile(r"\b[A-Z][\w.&'-]*(?:\s+(?:[A-Z][\w.&'-]*|of|and|&|the)){0,6}\s*\([Ss]upra\)")


def _other_mentions(sentence, target):
    """Spans of other case names or citations in the sentence (not overlapping the target's span)."""
    spans = [(m.start(), m.end()) for m in _OTHER_CASE.finditer(sentence)]
    spans += [(m.start(), m.end()) for m in _SUPRA_CASE.finditer(sentence)]
    spans += [(m.start(), m.end()) for m in _POSSESSIVE_CASE.finditer(sentence)]
    spans += [(s, e) for _, s, e in C.find_cites(sentence)]
    return [(s, e) for s, e in spans if e <= target[0] or s >= target[1]]


def _separated(span, target, sentence):
    """True if a semicolon lies between the cue and the target: in a law report's list of cases ("A, over-ruled; B, referred to") each clause is about its own case."""
    lo, hi = (span[1], target[0]) if span[0] < target[0] else (target[1], span[0])
    between = sentence[lo:hi]
    if re.search(r"\bParas?\.?\s*\d", between):
        return True                                                   # the digital law reports' case-law tables: "[cite] overruled Para 2 [cite] relied on Para 3": each entry ends at its paragraph number
    return ";" in between or bool(re.search(r"\[\d{1,4}\s?[A-Z](?:\s?-\s?[A-Z0-9]+)?(?:\s?;[^\]]*)?\]", between))   # a semicolon, or a law report's paragraph reference such as [128A-C] or [570 G; 571 A] (a year in brackets, [1969], is a citation, not a paragraph reference)


def _distance(span, target):
    if span[0] >= target[1]:
        return span[0] - target[1]
    if span[1] <= target[0]:
        return target[0] - span[1]
    return 0


_COORD = re.compile(r"\s*(?:,|;|and|&|as well as|as also|and also|also|,\s*and)?\s*", re.I)


def _binding(cue, others, target, sentence):
    """'weak' when another case, not coordinated with the target, lies between the cue and the target (the cue may be about that other
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
    def competing(s, e):
        """Only a case lying between the cue and the target group can steal the cue; "X overruled T" has X before the cue, as the verb's other argument."""
        if lo <= s and e <= hi:
            return False
        if group[0] >= cue[1]:
            return cue[1] <= s and e <= group[0]
        if group[1] <= cue[0]:
            return group[1] <= s and e <= cue[0]
        return False
    return "weak" if any(competing(s, e) for s, e in mentions) else "strong"


def classify(sentence, target):
    """-> dict(label, cue, cue_span, negated, hedged, binding, all) for one flattened sentence and the (start, end) of the target mention in it."""
    others = _other_mentions(sentence, target)
    found = []
    for label, patterns in _COMPILED:
        for rx in patterns:
            for m in rx.finditer(sentence):
                span = (m.start(), m.end())
                if _distance(span, target) > MAX_DISTANCE or _separated(span, target, sentence):
                    continue
                if label == "OVERRULES" and _NOT_ABOUT_CASE.search(sentence[max(0, m.start() - 10):m.end() + 40]):
                    continue
                if label == "OVERRULES" and re.match(r"per incuriam", m.group(0), I) and re.search(r"(?:doctrine|principles?|rule|question|plea|concept|expression|term|test|issue)s?\s+(?:of\s+|on\s+|as to\s+)?$", sentence[max(0, m.start() - 45):m.start()], I):
                    continue                                              # "the principles of per incuriam": the doctrine is the topic, not a verdict on the case
                if label == "DOUBTS_REFERS" and re.match(r"correctness of", m.group(0), I) and _AFFIRMING.search(sentence[max(0, m.start() - 40):m.start()]):
                    continue                                              # "affirmed the correctness of the decision in T" supports T
                before = sentence[max(0, m.start() - 45):m.start()]
                negated = bool(_NEGATION.search(sentence[max(0, m.start() - 140):m.start()])) and label in ("OVERRULES", "DISAGREES", "DOUBTS_REFERS", "DISTINGUISHES")
                if (label == "FOLLOWS" and _NEG_FOLLOW.search(before) and not _NOT_A_NEGATION.search(before)
                        and not re.match(r"in (?:consonance|conformity|accord|line|keeping)\b", m.group(0), I)):      # those are handled as relational cues
                    neg_start = span[0] - len(_NEG_FOLLOW.search(before).group(0))
                    if _DOUBLE_NEG.search(sentence[max(0, neg_start - 90):neg_start + len(_NEG_FOLLOW.search(before).group(0))]):
                        found.append({"label": "FOLLOWS", "was": "FOLLOWS", "cue": "not justified in not following", "cue_span": span, "negated": False, "hedged": False,
                                      "binding": _binding(span, others, target, sentence), "distance": _distance(span, target)})
                        continue                                      # "we will not be justified in not following T": a double negative, T is followed
                    if (neg_start >= target[1] and _COMPLIANCE.search(sentence[max(0, target[0] - 160):target[0]])
                            and re.search(r"\b(?:has|have|had)\s+(?:not|never)\s+been\s+$", sentence[max(0, span[0] - 30):span[0]], I)
                            and not re.match(r"\s*(?:by|in)\b", sentence[span[1]:span[1] + 10], I)):
                        found.append({"label": "FOLLOWS", "was": "DISAGREES", "cue": "mandate not complied with (T is the authority)", "cue_span": span, "negated": False, "hedged": False,
                                      "binding": _binding(span, others, target, sentence), "distance": _distance(span, target)})
                        continue                                      # "cases in which the mandate of Sections 41, 41-A and T has not been followed": non-compliance with T, not a judgment on T
                    gerund = bool(re.search(r"\b(?:by|to)\s*$", sentence[max(0, neg_start - 6):neg_start], I))
                    if (neg_start < target[0] and (re.search(r"\b(?:has|have|had|did|does|do)\s*$", sentence[max(0, neg_start - 12):neg_start], I) or gerund)
                            and _LOWER_ACTOR.search(sentence if gerund else sentence[max(0, neg_start - 100):neg_start])):
                        found.append({"label": "FOLLOWS", "was": "DISAGREES", "cue": "has not followed (T is the authority)", "cue_span": span, "negated": False, "hedged": False,
                                      "binding": _binding(span, others, target, sentence), "distance": _distance(span, target)})
                        continue
                    if not (attached(sentence, (neg_start, span[1]), target)
                            or (neg_start >= target[1] and neg_start - target[1] <= 100 and _PRONOUN_SUBJECT.search(sentence[target[1]:neg_start]))):
                        continue                                      # "the affidavit has not been affirmed by the deponent": the negated verb is not about the target
                    found.append({"label": "DISAGREES", "was": "FOLLOWS", "cue": _NEG_FOLLOW.search(before).group(0) + m.group(0), "cue_span": span, "negated": False, "hedged": bool(_HEDGE.search(before)) or is_hedged(sentence, neg_start) or is_hedged_after(sentence, span[1]),
                                  "binding": _binding(span, others, target, sentence), "distance": _distance(span, target)})
                    continue
                # cues that already contain a negation ("not good law", "not borne out") are not flipped by a nearby 'not', but a rejection of the whole proposition still flips them
                if re.match(r"(?:not|no longer|neither|cannot|do(?:es)? not|did not|is not|are not|was not|were not)\b", m.group(0), I) or re.search(r"\bnot\b", m.group(0), I):
                    negated = bool(_REJECTING.search(sentence[max(0, m.start() - 140):m.start()])) and label in ("OVERRULES", "DISAGREES", "DOUBTS_REFERS", "DISTINGUISHES")
                hedged = is_hedged(sentence, m.start()) or is_hedged_after(sentence, m.end())
                binding = _binding(span, others, target, sentence)
                if label in ("OVERRULES", "DISAGREES") and span[1] <= target[0] and _IGNORED_MID.search(sentence[span[1]:target[0]]):
                    found.append({"label": "FOLLOWS", "was": label, "cue": "ignoring T (T is the authority ignored)", "cue_span": span, "negated": False, "hedged": hedged,
                                  "binding": binding, "distance": _distance(span, target)})
                    continue
                if label in ("OVERRULES", "DISAGREES") and span[0] >= target[1]:
                    # "judgments that ignored T ... are per incuriam": T is the authority they ignored; "where it was held in T that the view ... is overruled": the cue belongs to the proposition
                    am = _AUTHORITY.search(sentence[:target[0]])
                    if am:
                        found.append({"label": "FOLLOWS", "was": label, "cue": am.group(0).strip(), "cue_span": span, "negated": False, "hedged": hedged,
                                      "binding": binding, "distance": _distance(span, target)})
                        continue
                    if _PROPOSITION.search(sentence[target[1]:span[0]]) and not (_DECISION_IDIOM.search(m.group(0)) and _RELATIVE_HELD.search(sentence[target[1]:span[0]])):
                        continue
                    if _HELD_IN.search(sentence[:target[0]]) and re.match(r"\s*(?:\(\w+\)\s*)?(?:\(supra\)\s*)?that\b", sentence[target[1]:]):
                        continue                                          # "it was held by this Court in T that the assumption ... was not correct": the proposition is T's holding
                if (label in ("DISAGREES", "DOUBTS_REFERS") or (label == "OVERRULES" and not _VERB.search(m.group(0)))) and not attached(sentence, span, target):
                    continue
                if _distance(span, target) > FAR and binding == "strong":
                    binding = "weak"                                          # a cue far from the mention is probably about something else
                if label == "DISAGREES" and re.match(r"not follow", m.group(0), I) and re.search(r"\b(?:has|have|had|did|does|do|was|were)\s*$", sentence[max(0, m.start() - 12):m.start()], I) and span[0] < target[0]:
                    found.append({"label": "FOLLOWS", "was": "DISAGREES", "cue": "has not followed (T is the authority)", "cue_span": span, "negated": False, "hedged": hedged,
                                  "binding": binding, "distance": _distance(span, target)})
                    continue
                if label == "DISAGREES" and _RELATIONAL.search(m.group(0)) and span[1] <= target[0]:
                    # "X is not in consonance with T": T is the standard X is measured against, so this supports T
                    found.append({"label": "FOLLOWS", "was": "DISAGREES", "cue": m.group(0), "cue_span": span, "negated": False, "hedged": hedged, "binding": binding, "distance": _distance(span, target)})
                    continue
                if label == "OVERRULES" and _VERB.search(m.group(0)) and voice(sentence, span, target) == "agent":
                    found.append({"label": "OVERRULED_OTHER", "cue": m.group(0), "cue_span": span, "negated": negated, "hedged": hedged, "binding": binding, "distance": _distance(span, target)})
                    continue
                found.append({"label": label, "cue": m.group(0), "cue_span": span, "negated": negated, "hedged": hedged, "binding": binding, "distance": _distance(span, target)})
    for rx in _NOT_OVERRULED:
        for m in rx.finditer(sentence):
            if _distance((m.start(), m.end()), target) <= MAX_DISTANCE and not _separated((m.start(), m.end()), target, sentence):
                found.append({"label": "NOT_OVERRULED", "cue": m.group(0), "cue_span": (m.start(), m.end()), "negated": False, "hedged": bool(_HEDGE.search(sentence[max(0, m.start() - 45):m.start()])),
                              "binding": _binding((m.start(), m.end()), others, target, sentence), "distance": _distance((m.start(), m.end()), target)})
    # "nothing to suggest that ... overruled": the existence-negating phrase covers the cue it contains
    covers = [f["cue_span"] for f in found if f["label"] == "NOT_OVERRULED"]
    if covers:
        found = [f for f in found if f["label"] == "NOT_OVERRULED" or not any(a - 2 <= f["cue_span"][0] and f["cue_span"][1] <= b + 2 for a, b in covers)]
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


_MARKER = r"(?:Thus|Therefore|Accordingly|Hence|Consequently|In (?:view of the above|the result|that view|the circumstances|these circumstances)|For (?:these|the above|the said) reasons)"
_NOUN = r"(?:decision|judgment|judgement|view|case|ratio|holding|ruling|reasoning|opinion|proposition|law|authority)"
_ANAPHOR = re.compile(rf"^(?:{_MARKER}\s*,?\s+)?(?:That|This|The said|The aforesaid|The above|The same|Such|Said)\s+(?:\w+\s+){{0,3}}?{_NOUN}\b"
                      rf"|^{_MARKER}\s*,?\s+the\s+(?:(?:earlier|said|previous)\s+)?(?:decision|judgment|judgement|view|ratio|holding|ruling|reasoning|opinion|proposition)\b", I)   # a bare "The decision ..." opens a sentence about any decision, so it counts only after a concluding marker ("Thus, the decision is required to be overruled")
_NON_ADVERSE = ("NEUTRAL", "FOLLOWS", "LIMITS", "DISTINGUISHES", "NOT_OVERRULED", "OVERRULED_OTHER")


def classify_in_context(sentence, target, next_sentence=""):
    """classify(), plus one step of anaphora: if the mention's own sentence shows nothing adverse and the next sentence opens by pointing back at it
    ("That decision ...", "The said view ...") and carries an adverse cue, the next sentence's cue is used, marked `anaphoric` and weak, so it can raise a
    question but never counts as a clean overruling."""
    c = classify(sentence, target)
    if c["label"] in _NON_ADVERSE and next_sentence:
        m = _ANAPHOR.match(next_sentence)
        if m:
            d = classify(next_sentence, (0, m.end()))
            if d["label"] in ("OVERRULES", "DISAGREES", "DOUBTS_REFERS", "LEGISLATIVE") and not d["negated"] and d["distance"] is not None:
                d = dict(d)
                d.update(anaphoric=True, binding="weak", all=c["all"] + [(d["label"], d["cue"])])
                return d
    c = dict(c)
    c["anaphoric"] = False
    return c
