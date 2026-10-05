"""Reading the precomputed currency cards at answer time.

Standard library only, apart from goodlaw/cites.py (also standard library only): copy `cardreader.py` and `cites.py` next to each other, plus `cards/currency_cards.json`, and the
answer step can look a case up without the corpus, the checker or a database.

    index = load("cards/currency_cards.json")
    card = find(index, case_name="Rangappa v Sri Mohan")          # the exact case_name string the chunks carry; falls back to a squashed name, then to a citation
    result = for_answer(card, today="2026-10-05")
    if result["user_facing_note"]:
        ...                                                        # fold it in as one short clause, as Recourse does with its own currency notes

The rules this applies (see cards/README.md):
  * Only a warning or a caution carries a note. A case the checker found nothing against, or could not check, has none: silence in what we hold is not a finding, so nothing is
    said (Recourse already learned that hand-wringing about unverified cases reads badly).
  * No note ever says a case "is good law" or similar; `check_wording` is the guard that tests use.
  * A person's review overrides the checker's reading, but only while it is current (the card's fingerprint is the one the person saw).
  * Recourse's own human-verified records come first; this reader is for the cases they do not cover, and for a warning they have not yet seen.
"""
import datetime
import json
import re

try:
    from . import cites as C
except ImportError:                      # copied next to cites.py
    import cites as C

FORBIDDEN = ("good law", "bad law", "still valid", "no longer valid", "safe to rely", "binding authority", "valid law")
CONFIRMED_NOTE = "A later Supreme Court judgment overrules or rejects this case, in whole or in part, so check it before relying on this case."
LEVELS = {"ADVERSE_SIGNAL": "warning", "QUESTIONED": "caution"}


def _squash(s):
    s = re.sub(r"\b(?:versus|vs\.?|v\.?)\b", " v ", (s or "").lower())
    return re.sub(r"[^a-z0-9]", "", s)


def _date(d):
    if isinstance(d, datetime.date):
        return d
    return datetime.date.fromisoformat(str(d)[:10]) if d else datetime.date.today()


def load(path_or_doc):
    """Reads the cards file (or takes the loaded document) -> an index for `find`."""
    doc = path_or_doc if isinstance(path_or_doc, dict) else json.load(open(path_or_doc, encoding="utf-8"))
    cards = doc["cards"]
    by_name, by_squash, by_key = {}, {}, {}
    for c in cards:
        name = c["case"]["name"]
        by_name[name] = c
        by_squash.setdefault(_squash(name), c)
        for k in list(c["case"].get("citation_keys") or []) + list((c.get("corpus") or {}).get("cites") or []):
            try:
                for v in C.key_variants(k):
                    by_key.setdefault(v, c)
            except Exception:
                by_key.setdefault(k, c)
    return {"cards": cards, "by_name": by_name, "by_squash": by_squash, "by_key": by_key, "generated": doc.get("generated"), "counts": doc.get("counts")}


def find(index, case_name=None, citation=None):
    """The card for a case, or None: by the exact name, then the name with punctuation and 'v'/'vs' ignored, then a citation."""
    if case_name:
        if case_name in index["by_name"]:
            return index["by_name"][case_name]
        hit = index["by_squash"].get(_squash(case_name))
        if hit:
            return hit
    if citation:
        for key, _, _ in C.find_cites(citation):
            for v in C.key_variants(key):
                if v in index["by_key"]:
                    return index["by_key"][v]
    return None


def check_wording(text):
    """The forbidden phrases found in a user-facing text (an empty list means it is fine)."""
    low = (text or "").lower()
    return [p for p in FORBIDDEN if p in low]


def for_answer(card, today=None, max_age_days=45):
    """What the answer step needs for one case.

    level            'warning', 'caution' or 'none'
    user_facing_note a short plain text for the user (or None), safe to show or to give the answer-writing model
    statute_note     a mechanical note when the case turns on a section the 2023 codes renumbered (None otherwise); Recourse's curated record is the authority on this
    decided_by       'checker' or 'human review (...)'
    stale            the card is older than max_age_days (rebuild after each monthly refresh)
    under_review     a person marked the case as needing research
    internal_note    for logs and developers, never for the user
    """
    if card is None:
        return {"case_name": None, "status": "NO_CARD", "level": "none", "user_facing_note": None, "statute_note": None, "decided_by": None, "stale": False, "under_review": False,
                "internal_note": "no card for this case", "card_generated": None}
    status = card["status"]
    level = LEVELS.get(status, "none")
    note = card.get("user_facing_note")
    decided_by = "checker"
    under_review = False
    internal = card.get("internal_note") or ""
    review = card.get("review")
    if review and review.get("current"):
        verdict = review.get("verdict")
        decided_by = f"human review ({review.get('reviewer') or 'reviewer not named'}, {review.get('date')})"
        if verdict == "CONFIRMED_ADVERSE":
            level, note = "warning", CONFIRMED_NOTE
        elif verdict == "FALSE_ALARM":
            level, note = "none", None
            internal += " A person reviewed the flagged passages and judged them not adverse."
        elif verdict == "NEEDS_RESEARCH":
            under_review = True
    elif review:
        internal += " A person reviewed an earlier version of the evidence; that review no longer applies."
    generated = (card.get("provenance") or {}).get("generated")
    stale = bool(generated) and (_date(today) - _date(generated)).days > max_age_days
    if stale:
        internal += f" This card was built on {generated}; rebuild it."
    bad = check_wording(note)
    if bad:                               # a guard, not an expectation: never let a forbidden phrase through
        note, internal = None, internal + f" The note was withheld because it contained {bad}."
    return {"case_name": card["case"]["name"], "status": status, "level": level, "user_facing_note": note, "statute_note": card.get("statute_note"), "decided_by": decided_by, "stale": stale,
            "under_review": under_review, "internal_note": internal.strip(), "card_generated": generated}
