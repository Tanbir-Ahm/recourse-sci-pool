"""The bench a case is said to have been decided by, as later judgments describe it.

Old and middle-aged texts often carry only a lower bound for a case's bench (a short header, or the signature lines), so whether a later bench is larger than the case's
cannot be settled from the case's own text. Later judgments say it in passing: "a three-Judge Bench of this Court in X v. Y", "X v. Y (supra), a Constitution Bench
decision". This module reads such a descriptor attached to a mention of the case, and `estimate` combines the descriptors found in the judgments that cite it.

A descriptor counts only if it sits in the mention's own sentence, close to the mention, with no other case named between the two. Several judgments must agree.
How often this is right was measured against cases whose bench is known from their own text (see goodlaw/EVALUATION.md, step 4).
"""
import collections
import re

NUMBERS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "thirteen": 13,
           "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "9": 9, "11": 11, "13": 13}
_NUM = r"(?P<n>two|three|four|five|six|seven|eight|nine|ten|eleven|thirteen|2|3|4|5|6|7|9|11|13)"
_JUDGE = r"(?:learned |Hon'?ble |Hon’ble )?[Jj]udges?(?:['’]s?)?"
_FORMS = [
    re.compile(rf"\b{_NUM}[\s-]+{_JUDGE}[\s-]+(?:Constitution[\s-]+)?[Bb]ench\b"),                  # a three-Judge Bench / three Judges' Bench
    re.compile(rf"\b[Bb]ench\s+of\s+{_NUM}\s+(?:learned\s+|Hon'?ble\s+|Hon’ble\s+)?[Jj]udges?\b"),   # a Bench of three Judges
    re.compile(rf"\b{_NUM}\s+(?:learned\s+|Hon'?ble\s+|Hon’ble\s+)?[Jj]udges?\b(?=[^.]{{0,12}}\b(?:held|observed|decided|ruled|laid|in)\b)"),   # three Judges held / in
]
_CONSTITUTION = re.compile(r"\bConstitution[\s-]+[Bb]ench\b")
_DIVISION = re.compile(r"\bDivision[\s-]+[Bb]ench\b(?!\s+(?:of|in)\s+(?:the\s+)?(?:\w+\s+){0,3}High\s+Court)")
_ANOTHER_CASE = re.compile(r"\b(?:v\.|vs\.?|versus)\s|\(\d{4}\)\s*\d+\s*[A-Z]|\bAIR\s+\d{4}|\[\d{4}\]|\bSCC\b|\bSCR\b", re.I)
BEFORE, AFTER = 130, 70


def descriptors(text):
    """[(start, end, size, exact)] for the bench descriptors in a piece of text. 'Constitution Bench' alone means at least five (size 5, not exact); 'Division Bench'
    means two."""
    out = []
    for rx in _FORMS:
        for m in rx.finditer(text):
            out.append((m.start(), m.end(), NUMBERS[m.group("n").lower()], True))
    for m in _CONSTITUTION.finditer(text):
        if not any(a <= m.start() < b for a, b, _, _ in out):
            out.append((m.start(), m.end(), 5, False))
    for m in _DIVISION.finditer(text):
        out.append((m.start(), m.end(), 2, True))
    return sorted(out)


def attached_size(sentence, span):
    """(size, exact) a descriptor attached to the mention at `span` (start, end) of `sentence` gives, or None. The descriptor must be within BEFORE characters before the
    mention or AFTER after it, with no other case or citation between it and the mention."""
    s, e = span
    best = None
    for a, b, n, exact in descriptors(sentence):
        if b <= s and s - b <= BEFORE:
            gap = sentence[b:s]
        elif a >= e and a - e <= AFTER:
            gap = sentence[e:a]
        else:
            continue
        if _ANOTHER_CASE.search(gap):
            continue
        dist = (s - b) if b <= s else (a - e)
        if best is None or dist < best[0]:
            best = (dist, (n, exact))
    return best[1] if best else None


def estimate(mentions, min_docs=2):
    """(size, exact, agreeing judgments, judgments with a descriptor) from the descriptors attached to the confident mentions (a full or party-pair match, in the court's or
    counsel's own text, not the headnote), or None when fewer than `min_docs` judgments give one or they disagree. A judgment counts once."""
    per_doc = {}
    for m in mentions:
        if m.get("tier") not in ("cite", "pair") or m.get("in_headnote"):
            continue
        got = attached_size(m["sentence"], m["target_in_sentence"])
        if got:
            per_doc.setdefault(m["doc_key"], collections.Counter())[got] += 1
    votes = collections.Counter()
    for c in per_doc.values():
        votes[c.most_common(1)[0][0]] += 1
    if not votes:
        return None
    (size, exact), n = votes.most_common(1)[0]
    total = sum(votes.values())
    if n < min_docs or n * 5 < total * 4:          # fewer than two judgments, or less than four in five agree
        return None
    return size, exact, n, total
