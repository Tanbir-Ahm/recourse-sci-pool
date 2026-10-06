"""A second reader: a model reads the passages around each mention of a case and says how the later judgment treats it.

The pattern rules (goodlaw.treatment) read one sentence at a time and miss overrulings stated in other words, in the next paragraph, or by a reference to "that view". A
model can read the passage. This module prepares what the model reads and checks what it says; it does not call a model. The protocol is a file:

    export   candidate passages (the mentions of one case in one later judgment, the ones that carry treatment vocabulary first) -> a JSON-lines batch, one item each
    read     a model (a session reading the batch, or any other) writes one verdict per item: a treatment, and the sentence that shows it, copied exactly
    import   each verdict is checked: the treatment must be one of the listed words and the quote must occur word for word in the item's passages

A verdict whose quote is not in the passages is kept but marked unverified and is never used as evidence. Nothing here is a finding of law: a model's reading is a proposal for
a person to confirm, labelled as such wherever it is shown.
"""
import collections
import hashlib
import re

from .textutil import flatten

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

# vocabulary that suggests a passage says something about the standing of a case; used only to choose which passages a reader sees first. STRONG words say it outright
# (weight 4); WEAK words are the ordinary talk of citing a case (weight 1) and must not outrank a passage with a strong word, as they did in the first blind run, where an
# explicit "we overrule the decision in X" was left out in favour of passages with many weak words.
STRONG_CUES = re.compile(
    r"over-?rul|(?:no longer|not) (?:a )?good law|bad in law|per incuri\w*|(?:wrongly|incorrectly) decided|erroneous|(?:is|was|are|were|be) (?:not )?(?:correct|incorrect|wrong)|"
    r"not (?:the )?correct|do(?:es)? not (?:lay down|represent|state|hold the field)|will not lay down|respectfully (?:disagree|differ)|with respect,? (?:we )?(?:differ|disagree)|"
    r"unable to (?:agree|subscribe|accept)|(?:do(?:es)? not|cannot) (?:agree|accept|approve|subscribe)|decline[sd]? to follow|not (?:be )?followed|disapprov|dissent|doubt|"
    r"reconsider|re-?examin|larger bench|(?:not|never) approved|departed from|stands? (?:modified|overruled)|no longer (?:holds?|stands?|valid|binding)", re.I)
WEAK_CUES = re.compile(
    r"set aside|reversed|distinguish|not applicable|inapplicable|no application|to that extent|cannot be read as|not (?:be )?relied|affirm|approv|reaffirm|followed|relied|"
    r"referred to|reference to|with respect|obiter|explained", re.I)
CUE_VOCAB = re.compile(STRONG_CUES.pattern + "|" + WEAK_CUES.pattern, re.I)       # kept for callers that only need 'has any cue'

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


def cue_score(text):
    """4 for each distinct strong cue and 1 for each distinct weak cue (at most 3 in all), so one strong word always outranks any number of weak ones."""
    strong = {m.group(0).lower() for m in STRONG_CUES.finditer(text)}
    weak = {m.group(0).lower() for m in WEAK_CUES.finditer(text)} - strong
    return 4 * len(strong) + min(len(weak), 3)


def candidate_passages(mentions, limit=MAX_PASSAGES, must=()):
    """[{where, text}] for the mentions of one case in one later judgment: confident mentions only; the mentions whose positions are in `must` (the ones the pattern rules read as
    adverse) first, then those whose passage carries the most treatment vocabulary (strong words outweigh weak), then the first mention; at most `limit` (`must` mentions are
    always shown, even beyond it), never the same sentence twice. `where` says whether the passage is in the law report's headnote or the judgment."""
    scored, seen = [], set()
    for i, m in enumerate(mentions):
        if m.get("confidence") not in ("high", "medium"):
            continue
        key = flatten(m["sentence"])[:200]
        if key in seen:
            continue
        seen.add(key)
        text = passage(m)
        scored.append((0 if i in must else 1, -cue_score(text), 0 if m.get("confidence") == "high" else 1, i, {"where": "headnote" if m.get("in_headnote") else "judgment", "text": text}))
    scored.sort(key=lambda x: x[:4])
    forced = [x for x in scored if x[0] == 0]
    out = [x[4] for x in scored[:max(limit, len(forced))]]
    return out


def make_item(item_id, case, later_title, later_date, mentions, limit=MAX_PASSAGES, must=()):
    """One batch item, or None when the judgment has no confident mention of the case."""
    ps = candidate_passages(mentions, limit, must)
    if not ps:
        return None
    return {"id": item_id, "case": case, "later_judgment": later_title, "date": later_date, "passages": ps}


def _plain(text):
    """Text for comparing a quote with a passage: whitespace flattened and the markers that show the case («, ») removed, since a reader may or may not copy them."""
    return re.sub(r"\s+", " ", flatten(text).replace("\u00ab", "").replace("\u00bb", "")).strip()


def check_verdict(item, verdict):
    """-> dict(id, treatment, quote, note, valid, quote_verified, problems). A treatment outside the list is invalid; a quote not found word for word in the item's passages makes
    the verdict unverified (the quote is blanked, so it can never be shown as evidence)."""
    problems = []
    treatment = str(verdict.get("treatment", "")).strip().upper()
    if treatment not in TREATMENTS:
        problems.append(f"treatment {verdict.get('treatment')!r} is not one of {TREATMENTS}")
    quote = _plain(str(verdict.get("quote") or ""))
    verified = True
    if quote:
        verified = any(quote in _plain(p["text"]) for p in item["passages"])
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


# ---------------------------------------------------------------- the production batch: what a reader is asked to read for each case, and how the answers go back
RULE_ADVERSE = ("OVERRULES", "DISAGREES", "DOUBTS_REFERS")      # the pattern rules' adverse labels (goodlaw.treatment)
READER_LABEL = "second reading by a model (a session reading the passages); not lawyer-validated and not independent of the checker's author"


def passage_hash(passages):
    """A short hash of what the reader was shown; a verdict applies only while the passages are unchanged."""
    return hashlib.sha1("\n".join(f"{p['where']}|{p['text']}" for p in passages).encode("utf-8")).hexdigest()[:12]


def items_for_target(target_key, case_name, mentions):
    """The items a reader should read for one case: one per later judgment in which the pattern rules read the case as adverse (whoever is speaking: the reader decides that) or
    a passage carries a strong treatment word (STRONG_CUES). Each item shows the rules' flagged sentences first. Items carry `_rule` (the labels the rules gave, for the
    comparison afterwards; never shown to the reader) and `hash`. `mentions` are the classified mentions (goodlaw.report.classify_mentions)."""
    by_doc = collections.OrderedDict()
    for m in mentions:
        by_doc.setdefault(m["doc_key"], []).append(m)
    items = []
    for doc_key, ms in by_doc.items():
        flagged = {i for i, m in enumerate(ms) if m.get("label") in RULE_ADVERSE and m.get("confidence") in ("high", "medium")}
        ps = candidate_passages(ms, MAX_PASSAGES, flagged)
        if not ps or not (flagged or any(STRONG_CUES.search(p["text"]) for p in ps)):
            continue
        items.append({"id": f"{target_key}:{doc_key}", "case": case_name, "later_judgment": ms[0]["title"], "date": ms[0].get("date") or ms[0].get("year"), "passages": ps,
                      "hash": passage_hash(ps), "_rule": sorted({m["label"] for i, m in enumerate(ms) if i in flagged})})
    return items


def public(item):
    """The item as a reader sees it (no rule labels, no hash)."""
    return {k: v for k, v in item.items() if not k.startswith("_") and k != "hash"}


def summarise(items, records):
    """What the second reading says about one case: `records` maps an item id to its stored verdict {treatment, quote, note, hash, reader, date}. A record counts only if its hash is the
    item's current one and its quote is still found in the passages. Returns None when there is nothing to read."""
    if not items:
        return None
    read, pending, adverse, dismissed = 0, [], [], []
    for it in items:
        rec = records.get(it["id"])
        if not rec or rec.get("hash") != it["hash"]:
            pending.append(it["id"])
            continue
        c = check_verdict(it, rec)
        if not c["valid"]:
            pending.append(it["id"])
            continue
        read += 1
        if is_adverse(c):
            adverse.append({"id": it["id"], "later_judgment": it["later_judgment"], "date": it["date"], "treatment": c["treatment"], "quote": c["quote"], "note": c["note"], "rules_agree": bool(it["_rule"])})
        elif it["_rule"]:
            dismissed.append({"id": it["id"], "later_judgment": it["later_judgment"], "date": it["date"], "rules_read": it["_rule"], "reader_says": c["treatment"], "note": c["note"]})
    return {"label": READER_LABEL, "items": len(items), "read": read, "pending": len(pending), "adverse": adverse, "confirmed": sum(1 for a in adverse if a["rules_agree"]),
            "reader_only": [a for a in adverse if not a["rules_agree"]], "dismissed": dismissed}
