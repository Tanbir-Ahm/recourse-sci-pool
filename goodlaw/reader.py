"""A second reader: a model reads the passages around each mention of a case and says how the later judgment treats it.

The pattern rules (goodlaw.treatment) read one sentence at a time and miss overrulings stated in other words, in the next paragraph, or by a reference to "that view". A
model can read the passage. This module prepares what the model reads and checks what it says; it does not call a model. The protocol is a file:

    export   candidate passages (the mentions of one case in one later judgment, the ones that carry treatment vocabulary first) -> a JSON-lines batch, one item each
    read     a model (a session reading the batch, or any other) writes one verdict per item: a treatment, and the sentence that shows it, copied exactly
    import   each verdict is checked: the treatment must be one of the listed words and the quote must occur word for word in the item's passages

A verdict whose quote is not in the passages is kept but marked unverified and is never used as evidence. Nothing here is a finding of law: a model's reading is a proposal for
a person to confirm, labelled as such wherever it is shown.
"""
import re

from .textutil import flatten, quote_in_text

TREATMENTS = ("OVERRULES", "DISAGREES", "DOUBTS", "DISTINGUISHES", "FOLLOWS", "CITED", "UNCLEAR")
ADVERSE = ("OVERRULES", "DISAGREES", "DOUBTS")

INSTRUCTIONS = """You are checking how a later judgment of the Supreme Court of India treats an earlier case. Each item names the earlier case and gives passages from the later
judgment (the earlier case is marked with « »). Decide the strongest stance the later COURT itself takes towards THE EARLIER CASE, not towards other cases named in the passage.
Ignore what counsel argue, what a lower court held, and what a party contends, unless the Court adopts it. Ignore a case that is only cited for a rule of law.

  OVERRULES      the Court says the earlier case is overruled, is no longer good law, is wrongly decided and not to be followed, or sets it aside in whole or in part
  DISAGREES      the Court declines to follow it, holds it incorrect, per incuriam or not a correct statement of the law (without calling it overruled)
  DOUBTS         the Court doubts its correctness, or refers it (or the question it decided) to a larger bench
  DISTINGUISHES  the Court holds it inapplicable on the facts or the point, and leaves it standing
  FOLLOWS        the Court applies, relies on, approves, reaffirms or affirms it
  CITED          the case is only mentioned, summarised or quoted, with no stance of the Court's own
  UNCLEAR        the passages do not let you tell

Answer with one JSON object per item: {"id": ..., "treatment": <one word above>, "quote": <the shortest sentence or sentences that show the stance, copied exactly from the
passages; empty for CITED and UNCLEAR>, "note": <at most one short sentence, optional>}."""

# vocabulary that suggests a passage says something about the standing of a case; used only to choose which passages a reader sees first
CUE_VOCAB = re.compile(
    r"over-?rul|no longer (?:a )?good law|not (?:a )?good law|bad in law|per incuriam|wrongly decided|incorrectly decided|erroneous|incorrect|not (?:the )?correct|"
    r"do(?:es)? not (?:lay down|represent|state) (?:the )?(?:correct )?law|respectfully (?:disagree|differ)|with (?:great )?respect|cannot (?:be )?(?:sustain|accept|approve|follow)|"
    r"not (?:been )?(?:follow|approv|accept)|decline[sd]? to follow|disapprov|dissent|doubt|reconsider|re-?examin|larger bench|referred to|reference to|"
    r"set aside|reversed|distinguish|not applicable|inapplicable|no application|departed from|stands? (?:modified|overruled)|to that extent|cannot be read as|"
    r"not (?:be )?relied|affirm|approv|reaffirm|followed|relied", re.I)

MAX_PASSAGES = 4
SIDE = 350            # characters kept on each side of the mention inside a long sentence
CONTEXT = 320         # characters of the neighbouring sentences kept


def _clip_sentence(sentence, span):
    a, b = span
    if len(sentence) > 2 * SIDE + (b - a):
        lo, hi = max(0, a - SIDE), min(len(sentence), b + SIDE)
        return ("…" if lo else "") + sentence[lo:a] + "«" + sentence[a:b] + "»" + sentence[b:hi] + ("…" if hi < len(sentence) else "")
    return sentence[:a] + "«" + sentence[a:b] + "»" + sentence[b:]


def passage(m):
    """The text a reader sees for one mention: the sentence before, the sentence with the case marked, the sentence after."""
    prev, nxt = (m.get("prev") or "")[-CONTEXT:], (m.get("next") or "")[:CONTEXT]
    return " ".join(x for x in (prev, _clip_sentence(m["sentence"], m["target_in_sentence"]), nxt) if x).strip()


def candidate_passages(mentions, limit=MAX_PASSAGES):
    """[{where, text}] for the mentions of one case in one later judgment: confident mentions only, those whose passage carries treatment vocabulary first (more distinct cues
    first), then the first mention, at most `limit`, never the same sentence twice. `where` says whether the passage is in the law report's headnote or the judgment."""
    scored, seen = [], set()
    for i, m in enumerate(mentions):
        if m.get("confidence") not in ("high", "medium"):
            continue
        key = flatten(m["sentence"])[:200]
        if key in seen:
            continue
        seen.add(key)
        text = passage(m)
        cues = len({c.group(0).lower() for c in CUE_VOCAB.finditer(text)})
        scored.append((-cues, 0 if m.get("confidence") == "high" else 1, i, {"where": "headnote" if m.get("in_headnote") else "judgment", "text": text}))
    scored.sort(key=lambda x: x[:3])
    out = [s[3] for s in scored[:limit]]
    return out


def make_item(item_id, case, later_title, later_date, mentions, limit=MAX_PASSAGES):
    """One batch item, or None when the judgment has no confident mention of the case."""
    ps = candidate_passages(mentions, limit)
    if not ps:
        return None
    return {"id": item_id, "case": case, "later_judgment": later_title, "date": later_date, "passages": ps}


def check_verdict(item, verdict):
    """-> dict(id, treatment, quote, note, valid, quote_verified, problems). A treatment outside the list is invalid; a quote not found word for word in the item's passages makes
    the verdict unverified (the quote is blanked, so it can never be shown as evidence)."""
    problems = []
    treatment = str(verdict.get("treatment", "")).strip().upper()
    if treatment not in TREATMENTS:
        problems.append(f"treatment {verdict.get('treatment')!r} is not one of {TREATMENTS}")
    quote = flatten(str(verdict.get("quote") or ""))
    verified = True
    if quote:
        verified = any(quote_in_text(quote, p["text"]) for p in item["passages"])
        if not verified:
            problems.append("the quote does not occur word for word in the passages")
    elif treatment in ADVERSE + ("DISTINGUISHES", "FOLLOWS"):
        verified = False
        problems.append("a stance without the sentence that shows it")
    return {"id": item["id"], "treatment": treatment if treatment in TREATMENTS else None, "quote": quote if verified else "", "note": str(verdict.get("note") or "")[:300],
            "valid": treatment in TREATMENTS, "quote_verified": bool(quote) and verified, "problems": problems}


def is_adverse(checked):
    """A verified adverse reading: the treatment is adverse and its quote is in the passages."""
    return bool(checked and checked["valid"] and checked["treatment"] in ADVERSE and checked["quote_verified"])
