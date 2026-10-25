#!/usr/bin/env python3
"""Whose words a passage puts forward, and what authority they carry. Deterministic, text only: no network, no model, no data file, nothing to spend.

Why it exists: a passage is retrieved because its words match the question, which is not the same as the court having decided anything in it. A passage can be a
lawyer's argument (which the court may go on to reject), a trial court's view the High Court is reciting, a party's allegation, or plain background narrative.
The tier test of 2026-10-25 found 6 of 65 shown passages were one of those (`review_results/2026-10-25_tier_test/`). The owner's rule (2026-10-25):

    1 Supreme Court   2 High Court   3 trial court   4 a lawyer's argument - never a binding principle, and never shown.

Two earlier attempts in this repository stop short of it. `sci_index.tag_doc` tags a whole passage facts/argument/reasoning/order and `sci_index.W` weights it;
the weights are soft (an argument scores 0.85 against reasoning's 1.0, above facts' 0.8), a high similarity overrides them, and 60 of those 65 passages were
tagged "reasoning", 51 of them with basis "default", which means no evidence at all. `goodlaw.mentions.speaker` does decide court / counsel / lower court /
headnote and the good-law checker drops counsel and lower-court sentences (`goodlaw/report.py`), but it reads ONE sentence and the search never calls it: run
over whole passages it called 11 of those 65 "counsel", 7 of them wrongly, because a court's own paragraph often reports the argument it is about to reject.

So this module works sentence by sentence and then decides for the passage:

  * `voice_of` labels one sentence COURT (the deciding court's own voice, which is also the default: a court is the author of everything in its judgment that
    it does not hand to someone else), HIGHER_COURT (a higher court quoted), LOWER_COURT (a trial court, the court below or the impugned order quoted),
    COUNSEL (a lawyer's submission), PARTY (a party's own allegation or case) or STATUTE (statutory words).
  * `substantive` asks whether that sentence states law (a rule, a test, a holding) rather than narrating who filed what when.
  * `classify` requires a shown passage to carry **at least one substantive sentence in a court's voice**. A passage that carries law only in a lawyer's or a
    party's voice, or that carries no law at all, is BLOCKED: the site must not show it. This is a decision in code, not a line in a prompt.
  * the passage's `tier` is 1, 2 or 3 by the court whose words carry that law (a trial court's view inside a High Court judgment is tier 3), so a caller can
    order by tier first and let the similarity score matter only inside a tier. A score can then never put a trial court or a lawyer above a higher court.

Limits, stated plainly: these are word patterns, so they are wrong sometimes, and the counts in `review_results/2026-10-25_voice_rule/` say how often on a
hand-labelled sample (the author's labels, not a lawyer's). The module says nothing about whether a judgment is still good law, and nothing here is a finding
that a passage is right or helpful: a passage can be the court's own words, correctly tier 1, and still go against the person asking.
"""
import re

try:
    from goodlaw import textutil as TU
except ImportError:                                  # exported beside this file as a flat bundle
    import textutil as TU

SC, HC, TRIAL = 1, 2, 3                              # the owner's order, 2026-10-25
COURT, HIGHER_COURT, LOWER_COURT, COUNSEL, PARTY, STATUTE = "court", "higher_court", "lower_court", "counsel", "party", "statute"
AUTHORITY_VOICES = (COURT, HIGHER_COURT, LOWER_COURT, STATUTE)                  # voices that can carry law; COUNSEL and PARTY never can
BLOCK_VOICES = (COUNSEL, PARTY)
I = re.I


def _R(p):
    return re.compile(p, I)


# ---------------------------------------------------------------- who is speaking in one sentence
# First person is decisive: a court that writes "we" or "this Court" is speaking in its own voice even while it describes the argument it is about to reject
# ("We are unable to accept the contention of learned counsel that ..."). Checked before every other cue for that reason.
FIRST_PERSON = _R(r"\b(?:we|I)\s+(?:are|am|have|had|do|did|find|hold|held|think|see|may|must|cannot|can|shall|would|should|also|further|therefore|thus|now|accordingly|respectfully|fail|accept|reject|agree|disagree|answer|propose|deem|direct|order|allow|dismiss|quash|set aside|confirm|uphold|notice|observe|consider)\b"
                   r"|\bin (?:our|my) (?:considered |humble |respectful |view|opinion|judgment)|\bour (?:considered )?(?:view|opinion|conclusion|judgment)\b"
                   r"|\b(?:I|we) (?:am|are) (?:of the|unable|satisfied|not|inclined|conscious|constrained)\b|\bthis Court (?:is|has|had|holds?|held|finds?|found|observes?|observed|cannot|does not|is of)\b"
                   r"|\bin the considered opinion of this [Cc]ourt\b|\bthis Court is of the (?:considered )?(?:view|opinion)\b"
                   # the court recording what it did with the lawyers: it heard them, considered their submissions, rejected or accepted them. These are the
                   # court's own words about an argument, and must not be read as the argument itself; they are checked first for that reason.
                   r"|^\s*(?:Also\s+)?Heard\b|\b(?:I|we) have (?:also )?heard\b|\b(?:having|after) (?:carefully )?(?:heard|considered|perused|gone through|going through)\b|\bheard (?:the )?learned\b"
                   r"|\b(?:considered|examined|rejected|accepted|repelled|negatived|dealt with|answered|unable to accept) the (?:contentions?|submissions?|arguments?|pleas?)\b"
                   r"|\bit is difficult to (?:accept|agree|hold|countenance)\b|\bcannot be (?:accepted|countenanced|sustained)\b|\bthere is no (?:substance|merit|force) in\b|\bwe find no (?:merit|substance|force)\b|\bis liable to be (?:rejected|repelled)\b")
# A lawyer must be the AGENT OF A REPORTING VERB to own a sentence ("Mr Borah, learned counsel, submits that ..."), never merely be mentioned in it: "this Court
# records its appreciation for the assistance rendered by the learned Amicus Curiae", "insofar as the apprehension given by the learned ASG is concerned, it is
# to be noted that ...", and "from the submissions made by the learned counsel, two issues have arisen" are all the court's own words. Mentioning alone cost
# 5 of the 140 labelled passages a wrong block.
_LAWYER = (r"(?:learned\s+)?(?:senior\s+)?(?:counsel|advocates?|amicus(?:\s+curiae)?|Public\s+Prosecutor|P\.?P\.?|A\.?P\.?P\.?|A\.?S\.?G\.?|Solicitor\s+General|Advocate\s+General|Attorney\s+General|"
           r"Standing\s+Counsel|Government\s+Advocate|Addl?\.?\s*P\.?P\.?|Special\s+(?:Public\s+)?Prosecutor)(?![A-Za-z])")
_SAYS = r"(?:submits?|submitted|contends?|contended|urges?|urged|argues?|argued|pleads?|pleaded|canvass\w+|prays?|prayed|points?\s+out|pointed\s+out|cites?|cited|refers?\s+to|referred\s+to|relies|relied|placed?\s+reliance|has\s+drawn|drew)"
COUNSEL_CUE = _R(rf"\b{_LAWYER}[^.]{{0,70}}?\b{_SAYS}\b" rf"|\b{_SAYS}\s+(?:by\s+)?(?:the\s+)?{_LAWYER}\b"
                 rf"|\b(?:Mr|Ms|Mrs|Dr|Shri|Sri|Smt)\.?\s+[A-Z][\w.]*(?:\s+[A-Z][\w.]*)*,?\s+(?:the\s+)?{_LAWYER}"
                 r"|\b(?:submits?|submitted|contends?|contended|urges?|urged|argues?|argued|pleads?|pleaded|canvassed)\s+that\b"
                 r"|\bit (?:is|was|has been) (?:further |also |strenuously |vehemently |fairly |firstly |next )*(?:submitted|contended|argued|urged|pleaded|canvassed)\b"
                 r"|\bthe (?:contention|submission|argument|plea|stand|grievance)s? (?:of [^.]{0,45}?)?(?:is|are|was|were) that\b|\bthe (?:contention|submission|argument|plea)s? (?:raised|advanced|put forward|canvassed|urged) (?:by|that|is|was)\b"
                 r"|\bon behalf of the (?:appellant|respondent|petitioner|accused|complainant|State|Union|revenue)s? (?:it (?:is|was)|submitted|contended|urged|argued)\b"
                 r"|\baccording to (?:the )?learned\s+(?:senior\s+)?(?:counsel|advocate|P\.?P\.?|Public Prosecutor|Addl|Additional|Government Advocate|Standing Counsel|A\.?S\.?G\.?|Solicitor|Attorney)\b")
PARTY_CUE = _R(r"\bthe (?:prosecution|complainant|informant|defence|petitioner|appellant|respondent|accused)(?:'s|s')? (?:case|version|story|allegation|claim) (?:is|was|has been) that\b"
               r"|\baccording to the (?:prosecution|complainant|informant|FIR|first information report|petitioner|appellant|respondent|accused|case of)\b"
               r"|\b(?:it is|it was|has been|have been) alleged\b|\balleges? that\b|\balleged that\b|\bthe allegation (?:is|was|being) that\b"
               r"|\bas (?:per|alleged in) the (?:FIR|first information report|complaint|ejahar)\b|\bin the (?:FIR|complaint|ejahar),? (?:it is|the informant|the complainant)\b"
               r"|\bthe (?:case|gravamen) of the (?:prosecution|complainant|informant)\b")
# A lower court is recognised only as the AGENT OF A REPORTING VERB ("the Magistrate held", "observed by the Court below"), never by being mentioned: a rule
# ABOUT magistrates ("the Magistrate is duty bound not to authorise detention", from Arnesh Kumar) is the deciding court's own statement of law, not a
# magistrate speaking. The window between the two is short for the same reason. Built from parts, because an alternative spliced into the middle of this
# pattern once made a bare court word match on its own, which demoted 3 of the 65 tier-test passages wrongly.
_LOWER_BODY = r"(?:learned\s+)?(?:trial\s+[Cc]ourt|[Cc]ourts?\s+below|[Ss]essions\s+(?:Court|Judge)|Additional\s+Sessions\s+Judge|(?:Chief\s+)?Judicial\s+Magistrate|Magistrate|C\.?J\.?M\.?|S\.?D\.?J\.?M\.?|Munsiff|Tribunal|first\s+appellate\s+[Cc]ourt|[Ss]ingle\s+Judge)"
_REPORTED = r"(?:held|has\s+held|had\s+held|observed|opined|concluded|recorded|rejected|dismissed|allowed|convicted|acquitted|took\s+the\s+view|was\s+of\s+the\s+view|has\s+taken|erred|framed|refused|declined|passed|drawn|came\s+to|returned\s+a\s+finding)"
_LOWER_TAIL = (r"|\bthe impugned (?:judgment|order|finding)s? (?:holds?|held|records?|recorded|observes?|observed|proceeds?|states?|is based)\b"
               r"|\bthe learned (?:trial )?[Cc]ourt\b|\bthe [Cc]ourt of learned\b")                # a judgment never calls itself "the learned Court": that is always the court below
LOWER_CUE = _R(rf"\b(?:the\s+)?{_LOWER_BODY}[^.]{{0,60}}?\b{_REPORTED}\b" rf"|\b{_REPORTED}\s+by\s+(?:the\s+)?{_LOWER_BODY}\b" + _LOWER_TAIL)
# In a Supreme Court judgment the High Court is the court below, and its view is often the one the Supreme Court is about to set aside, so it must not be read
# as the deciding court's own. In a High Court judgment the same words are that court itself or a fellow High Court, which `_lower_tier` puts at tier 2 either way.
_HC_BODY = r"(?:the\s+)?(?:Division\s+Bench\s+of\s+the\s+)?(?:[A-Z][a-z]+\s+)?High\s+Court"
LOWER_CUE_SC = _R(rf"\b(?:the\s+)?{_LOWER_BODY}[^.]{{0,60}}?\b{_REPORTED}\b" rf"|\b{_REPORTED}\s+by\s+(?:the\s+)?{_LOWER_BODY}\b"
                  rf"|\b{_HC_BODY}[^.]{{0,60}}?\b{_REPORTED}\b" rf"|\b{_REPORTED}\s+by\s+{_HC_BODY}\b" + _LOWER_TAIL)
HIGHER_CUE = _R(r"\b(?:the )?(?:Hon.?ble )?(?:Supreme Court|Apex Court|Hon.?ble Court|Constitution Bench|their Lordships|Privy Council)\b[^.]{0,140}?\b(?:held|has held|had held|observed|has observed|laid down|ruled|reiterated|clarified|cautioned|directed|summarised|summarized|explained|opined|concluded|stated|noted|issued|negatived|deprecated|upheld|struck down|answered|considered|interpreted|expounded)\b"
                r"|\b(?:in|vide)\s+[A-Z][\w.'()@-]*(?:\s+[A-Z&][\w.'()@-]*){0,6}\s+(?:v\.?|vs\.?|versus)\s+[A-Z][^.]{0,90}?\bit (?:was|has been) (?:held|observed|laid down|ruled)\b"
                r"|\bit (?:has been|was) (?:held|observed|laid down|ruled) (?:by|in) (?:the )?(?:Hon.?ble )?(?:Supreme Court|Apex Court|this Court|a Constitution Bench)\b"
                r"|\b(?:has|have) been (?:held|laid down|settled) by the (?:Hon.?ble )?(?:Supreme Court|Apex Court)\b"
                r"|\bthe (?:law|position|principle|ratio) (?:laid down|settled|propounded) (?:by|in) (?:the )?(?:Hon.?ble )?(?:Supreme Court|Apex Court)\b")
HIGH_COURT_NAMED = _R(r"\b(?:Gauhati|Guwahati|Delhi|Bombay|Madras|Calcutta|Kerala|Karnataka|Allahabad|Patna|Orissa|Rajasthan|Punjab|Madhya Pradesh|Andhra|Telangana|Gujarat|Jharkhand|Chhattisgarh|Uttarakhand|Himachal|Sikkim|Manipur|Meghalaya|Tripura|Jammu) High Court\b|\bthis High Court\b|\bthe High Court\b")
SC_NAMED = _R(r"\b(?:Supreme Court|Apex Court|Constitution Bench|their Lordships|Hon.?ble Court)\b")
STATUTE_CUE = _R(r"^\s*[\"“]?(?:Section|Sec\.|S\.)\s*\d|\bshall be punish\w+|\bwhoever\b|\bnotwithstanding anything contained\b|\bshall be deemed to\b|\bimprisonment which may extend\b|\bshall mean\b|\bliable to fine\b")
SETTLED = _R(r"\bit is (?:well |now |also )?(?:settled|trite|established)\b|\bis well settled\b|\bthe law (?:is|on) \b|\bthe [Cc]ourt is (?:required|bound|duty bound)\b|\bthe test (?:is|for)\b")
QUOTED_RULE = _R(r"\b(?:held|observed|laid down|ruled|reiterated) as (?:under|follows)\b|\bin the following (?:words|terms)\b|\bruns? as (?:under|follows)\b|\bis extracted (?:below|hereunder)\b")


MIN_WORDS = 12                                       # words: the lead sentence of a result must be at least this long, so that a page never quotes a fragment
MIN_VOICE = 6                                        # words: below this a sentence is not speech at all but a number or a marker ("48.", "JUDGE", "(emphasis added)"),
                                                     # and must not count as the court speaking - every passage starts with its paragraph number, and taking that
                                                     # for the court's own voice would make the block below unreachable
CARRY = 3                                            # sentences: how far the voice of an attributed run carries into sentences that have no cue of their own


def _starts_inside_quote(first_sentence):
    """Whether the passage begins in the middle of somebody's quoted words: a closing quotation mark stands before any opening one. A passage is a slice of a
    judgment, so a long quotation can be cut anywhere, and the slice then shows the words without showing whose they are."""
    close, open_ = first_sentence.find("”"), first_sentence.find("“")
    return close >= 0 and (open_ < 0 or close < open_)


def _quote_open(sent, was_open):
    """Whether a quotation is still open at the end of this sentence. A judgment hands a whole block to its speaker with a colon and an opening quotation mark
    ("the trial court drew the following conclusions ; “During his entire evidence PW1 has failed ..."), and the block often runs for many sentences and is
    never closed before the passage ends, so counting the marks is what keeps the speaker attached to it."""
    depth = (1 if was_open else 0) + sent.count("“") - sent.count("”")
    if sent.count("“") == 0 and sent.count("”") == 0 and sent.count('"') % 2:
        depth += -1 if was_open else 1                   # a plain " toggles; judgments mostly use the curly marks
    return depth > 0


def voice_of(sent, own_tier=None):
    """(voice, cue) for one sentence, or (None, None) when the sentence attributes its words to nobody. Order: the deciding court's own first person, which is
    decisive because a court writing "we" is speaking for itself even while describing the argument it is about to reject; then a lawyer; then a party's
    allegation; then a lower court; then a higher court; then statutory words.

    A sentence that attributes its words to nobody belongs to the court whose judgment it is: the court is the author of its judgment, and everything in it is
    the court's own unless the court hands it to someone else. (`goodlaw.mentions.speaker` takes the same default. The first version of this module demanded a
    positive court cue instead and so blocked 33 of the 65 passages of the tier test that I had read as on point.) `classify` applies that default, and carries
    an attributed voice over the next few sentences, because an argument or a quotation runs on past the sentence that introduces it."""
    s = sent.strip()
    lower = LOWER_CUE_SC if own_tier == SC else LOWER_CUE
    for rx, lab in ((FIRST_PERSON, COURT), (COUNSEL_CUE, COUNSEL), (PARTY_CUE, PARTY), (lower, LOWER_COURT), (HIGHER_CUE, HIGHER_COURT), (STATUTE_CUE, STATUTE)):
        m = rx.search(s)
        if m:
            return lab, m.group(0)[:70].strip()
    return None, None


# ---------------------------------------------------------------- does the sentence state law
NORMATIVE = _R(r"\b(?:shall|must|cannot|can ?not|could not|would not|will not|ought|has to be|have to be|is required|are required|is bound|is liable|is entitled|is mandatory|is directory|is not (?:enough|sufficient|permissible|maintainable|open)|is no bar|does not (?:arise|lie|bar|constitute|amount)|is sufficient|suffices)\b"
              r"|\bno (?:offence|case|ground|interference|presumption|evidence|material|justification|question) (?:is|of|for|can|could|would|whatsoever)\b|\bnot maintainable\b|\bcannot be sustained\b"
              r"|\bdo(?:es)? not (?:constitute|amount to|make out)\b|\bpunishes\b|\bpunishable\b|\bprovides that\b|\bapplies (?:when|only|to)\b|\b(?:duly )?complied with\b")
DOCTRINE = _R(r"\b(?:requirement|presumption|burden of proof|burden (?:lies|is)|onus|ingredients?|essential(?:s)? of|mens rea|actus reus|the test\b|twin conditions|principles? (?:of|laid|is|are)|ratio|jurisdiction|locus standi|limitation|bail|sentence|conviction|acquittal|quash\w*|compound\w*|inherent power|discretion|prima facie|reasonable (?:doubt|belief|suspicion)|standard of proof|legally enforceable debt|dishonest inducement|abetment|instigation|mitigating|aggravating)\b")
HOLDING = _R(r"\b(?:held|holds|hold|observed|laid down|settled|ruled|reiterated|clarified|expounded|opined|concluded|is the law|position of law|view (?:taken|that))\b|\bit is (?:well )?(?:settled|established|trite)\b|\bthe law (?:is|on)\b"
             r"|\bno hesitation\b|\bin (?:my|our) considered (?:view|opinion|judgment)\b"
             r"|\b(?:unable|not able) to (?:agree|accept|subscribe|uphold|sustain)\b|\bdo(?:es)? not agree\b|\bwe agree\b|\bset aside\b|\bis quashed\b|\bupheld?\b|\bapproved?\b|\baffirm(?:ed)?\b")
NARRATIVE_ONLY = _R(r"^\s*(?:this|the (?:instant|present))? ?(?:appeal|petition|revision|application|matter|case)s? (?:is|was|has been|have been|stands?) (?:filed|preferred|directed|registered|instituted|taken up|listed|disposed|heard)\b"
                    r"|\b(?:was|were|has been|have been) (?:registered|arrested|detained|summoned|served|issued|produced|remanded|released on bail|charge-?sheet\w*|committed for trial)\b"
                    r"|\bheard (?:the )?(?:learned|both|rival|Mr|Ms)\b|\bperused the (?:record|materials|case diary|lower court record)\b|\bI have (?:heard|perused|gone through)\b|\bwe have (?:heard|perused|gone through)\b")


def substantive(sent):
    """True when the sentence states law rather than narrating the file's history. A pure narrative sentence ("the appeal was filed", "the accused was arrested
    and detained for 21 days") carries no rule however well it matches a question, so it cannot be the words a result is shown for."""
    s = sent.strip()
    if len(s.split()) < 6:
        return False
    if NARRATIVE_ONLY.search(s) and not (NORMATIVE.search(s) or HOLDING.search(s)):
        return False
    return bool(NORMATIVE.search(s) or HOLDING.search(s) or (DOCTRINE.search(s) and len(s.split()) >= 10))


# ---------------------------------------------------------------- the deciding court
def deciding_court(src=None, doc=None):
    """(tier, name) of the court whose judgment this is, from the stored fields: the crawl (<1e9) and the open bucket (1e9 to 2e9) are the Supreme Court's own
    texts and law reports, and an extra source names its court. Unknown counts as neither, so such a passage can never be ordered above a known higher court."""
    name = (src or {}).get("court")
    if not name and doc is not None and doc < 2_000_000_000:
        name = "Supreme Court of India"
    if not name:
        return None, None
    if re.search(r"supreme court", name, I):
        return SC, name
    if re.search(r"high court", name, I):
        return HC, name
    if re.search(r"district|sessions|magistrate|tribunal|trial", name, I):
        return TRIAL, name
    return None, name


def _lower_tier(cue, sent):
    """The tier of the court below whose words these are: a High Court's at 2, anything under it at 3. In a Supreme Court judgment the High Court below is tier 2;
    in a High Court judgment the same words are that court's own or a fellow High Court's, which is tier 2 as well."""
    return HC if HIGH_COURT_NAMED.search(cue or "") or (HIGH_COURT_NAMED.search(sent) and not re.search(r"trial|[Ss]essions|Magistrate|Tribunal|Munsiff|[Cc]ourts? below", cue or "", I)) else TRIAL


def _quoted_tier(cue, sent, own_tier):
    """The tier of a court quoted inside a judgment: the Supreme Court when it is named, a High Court when one is named, else the deciding court's own."""
    t = f"{cue or ''} {sent}"
    if SC_NAMED.search(t):
        return SC
    if HIGH_COURT_NAMED.search(t):
        return HC
    return own_tier


# ---------------------------------------------------------------- the passage
def _tier_of(d, own_tier):
    """The tier of the court whose words one sentence carries. An unnamed quotation is nobody's: `None`, which sorts last and is never promoted."""
    if d.get("unnamed_quote"):
        return None
    if d.get("tier_hint"):
        return d["tier_hint"]
    if d["voice"] in (COURT, STATUTE):
        return own_tier
    if d["voice"] == LOWER_COURT:
        return _lower_tier(d["cue"], d["text"])
    return _quoted_tier(d["cue"], d["text"], own_tier)


def classify(text, src=None, doc=None, own_tier=None):
    """What one passage puts forward.

    {"tier": 1|2|3|None, "voice", "cue", "blocked", "reason", "states_law", "lead", "quote", "sentences": [(voice, substantive, sentence)], "court"}

    `blocked` is True only when no court speaks in the passage at all and a lawyer or a party does: then every word of it is theirs and it must not be shown.
    That line is deliberately narrow, because the cost of the two mistakes is not the same. Blocking a passage the court did write throws away law (an earlier
    version of this demanded a sentence that "states law", and on a random 3,000 passages it dropped the Supreme Court's own "We are in full agreement with the
    above conclusions of the High Court" and its reading of a statute, because they carry no cue word), while letting a court's own narrative through only puts
    it low in a list. So the narrative case is not blocked: `states_law` is False for it and the caller sorts it below the passages that do state law.

    `tier` is the court whose words carry the law (a trial court's view inside a High Court judgment is tier 3), so ordering by tier before score keeps a trial
    court and a lawyer below the higher courts. `quote` is the run of neighbouring sentences around `lead` that holds no lawyer's or party's words, so what a
    page shows is both a true quotation and nobody's argument. Any unexpected error is caught by `safe_classify`, which blocks the passage.
    """
    if own_tier is None:
        own_tier, court_name = deciding_court(src, doc)
    else:
        court_name = (src or {}).get("court")
    flat = TU.flatten(text or "")
    sents = [flat[a:b].strip() for a, b in TU.sentences(flat)] or ([flat] if flat else [])
    labelled, carried, left, hint = [], None, 0, None
    inside = _starts_inside_quote(sents[0] if sents else "")      # the passage was cut out of the middle of a quotation: everything up to the closing mark is
    unnamed = inside                                              # somebody's quoted words, and the passage does not show whose
    for s in sents:
        v, cue = voice_of(s, own_tier)
        if inside and carried:
            v, cue = carried, f'(inside the quoted "{carried}" passage)'  # an open quotation keeps its speaker even where the words read like the court's own
        elif v is not None and not (inside and unnamed):                  # ("I hold that ..." inside a quoted trial-court conclusion is the trial judge's I)
            carried, left = (v, CARRY) if v != COURT else (None, 0)       # the court's own voice ends an attributed run
        elif carried and left > 0 and not SETTLED.search(s):
            v, cue, left = carried, f'(carried from the "{carried}" sentence above)', left - 1
        elif v is None:
            v, cue = COURT, None                                          # unattributed: the court is the author of its own judgment
        labelled.append({"voice": v, "cue": cue, "substantive": substantive(s), "text": s, "unnamed_quote": inside and unnamed, "tier_hint": hint if inside else None})
        was, inside = inside, _quote_open(s, inside)
        if inside and not was:
            if carried == COUNSEL and (SC_NAMED.search(s) or HIGH_COURT_NAMED.search(s)):
                carried, left = HIGHER_COURT, CARRY               # a lawyer citing a judgment and quoting it: inside the marks the words are that court's
                hint = SC if SC_NAMED.search(s) else HC
            unnamed = carried is None                             # a quotation opened with nobody named to own it
        elif not inside:
            unnamed = False
    court_voice = [(i, d) for i, d in enumerate(labelled) if d["voice"] in AUTHORITY_VOICES and len(d["text"].split()) >= MIN_VOICE]
    if not court_voice:                                       # no court speaks in it at all: if a lawyer or a party does, every word of it is theirs
        if any(d["voice"] in BLOCK_VOICES for d in labelled):
            return {"tier": None, "voice": None, "cue": None, "blocked": True, "reason": "every word of it is a lawyer's or a party's", "states_law": False, "lead": None, "quote": "",
                    "sentences": [(d["voice"], d["substantive"], d["text"]) for d in labelled], "court": court_name, "own_tier": own_tier}
    own_words = [(i, d) for i, d in court_voice if len(d["text"].split()) >= MIN_WORDS] or court_voice
    if not own_words:
        return {"tier": None, "voice": None, "cue": None, "blocked": True, "reason": "there is nothing in it", "states_law": False, "lead": None, "quote": "",
                "sentences": [(d["voice"], d["substantive"], d["text"]) for d in labelled], "court": court_name, "own_tier": own_tier}
    carriers = [(i, d) for i, d in own_words if d["substantive"]]
    ranked = [((_tier_of(d, own_tier) or 9), i, d) for i, d in (carriers or own_words)]
    tier, lead, best = min(ranked, key=lambda x: (x[0], x[1]))
    lo = hi = lead
    while lo - 1 >= 0 and labelled[lo - 1]["voice"] not in BLOCK_VOICES:
        lo -= 1
    while hi + 1 < len(labelled) and labelled[hi + 1]["voice"] not in BLOCK_VOICES:
        hi += 1
    return {"tier": None if tier == 9 else tier, "voice": best["voice"], "cue": best["cue"], "blocked": False, "reason": None, "states_law": bool(carriers), "lead": lead,
            "quote": " ".join(d["text"] for d in labelled[lo:hi + 1]), "sentences": [(d["voice"], d["substantive"], d["text"]) for d in labelled], "court": court_name, "own_tier": own_tier}


def safe_classify(text, src=None, doc=None, own_tier=None):
    """`classify`, but any error blocks the passage instead of letting it through. The register bundle fails open because a missing warning leaves the answer as
    it is today; this one fails closed, because the thing it prevents is a lawyer's argument being shown as the law."""
    try:
        return classify(text, src, doc, own_tier)
    except Exception as exc:                                      # noqa: BLE001 - deliberately broad: nothing may escape into a shown list
        return {"tier": None, "voice": None, "cue": None, "blocked": True, "reason": f"could not be read ({type(exc).__name__})", "lead": None, "quote": "", "sentences": [], "court": None}


def effective_tier(verdict, own_tier=None, promote=False):
    """The tier a list orders by. Owner's decision, 2026-10-25: a passage never ranks above the court that wrote the judgment it stands in. So a High Court
    judgment quoting the Supreme Court stays at High Court rank (`promote=False`, the default), the words of a court below that court are pushed down to their own
    tier, and in a Supreme Court judgment, where the writer is already first, this is the strict order. `promote=True` is the plain reading, in which the quoted
    Supreme Court outranks the High Court that quotes it; it was measured (review_results/2026-10-25_voice_rule/) and not chosen."""
    t = verdict.get("tier")
    own = own_tier if own_tier is not None else verdict.get("own_tier")
    if promote or t is None or own is None:
        return t
    return max(t, own)


def sort_key(verdict, score, own_tier=None, promote=False):
    """Order for a list of results: the court's tier decides first (an unknown tier sorts last), then whether the passage states law at all, and the search
    score only separates results that are equal on both. So no similarity score, however high, can put a trial court's view above an observation of a higher
    court, nor a passage of pure narrative above one that states the law."""
    return (effective_tier(verdict, own_tier, promote) or 9, not verdict.get("states_law"), -float(score))


def order(results, score_of=lambda r: r.get("score", 0.0), verdict_of=lambda r: r["authority"]):
    """Blocked results removed, the rest ordered by tier then score."""
    return sorted((r for r in results if not verdict_of(r).get("blocked")), key=lambda r: sort_key(verdict_of(r), score_of(r)))


TIER_NAME = {SC: "the Supreme Court", HC: "a High Court", TRIAL: "the trial court"}


def voice_line(verdict):
    """The line a page must print above a result, saying whose words it is quoting. Owner's decision, 2026-10-25: the rule reads word patterns and is wrong
    sometimes (1 of 140 hand-labelled passages gave a trial court's words a High Court's rank), so the reader is told whose words they are and can catch what
    the rule cannot. Never says a case is good law, and never says the words are right. A result without a line is not allowed out (`tier_select.verify`)."""
    court = verdict.get("court") or "this court"
    v, t = verdict.get("voice"), verdict.get("tier")
    if verdict.get("blocked"):
        return None
    if t is None:
        line = "Quoted words: this passage does not show whose they are"
    elif v == COURT:
        line = f"{court}'s own words"
    elif v == HIGHER_COURT:
        line = f"{TIER_NAME.get(t, 'a higher court')}, as quoted by {court}"
    elif v == LOWER_COURT:
        line = (f"The trial court's view, as recorded by {court}, not this court's own holding" if t == TRIAL
                else f"The court below's view, as recorded by {court}, not this court's own holding")
    elif v == STATUTE:
        line = f"The words of a section, as set out by {court}"
    else:
        line = f"{court}'s own words"
    return line if verdict.get("states_law", True) else line + " (background to the case; it states no rule)"
