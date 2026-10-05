"""The statute dimension of "is this still good law": did the numbered provisions a judgment cites survive the 2023 recodification?

Mechanical and checkable, and kept apart from case-law treatment (Recourse's own two-dimension rule): this module reads the sections a judgment cites
most, looks each up in the NCRB concordance (IPC to BNS, CrPC to BNSS; vendored in data/, source and caveats in data/statute_concordance.SOURCE.txt) and says
whether it was renumbered, whether the table marks it substantively changed, or whether it has no counterpart. It does not say that the doctrine died: a
renumbered section usually carries its case law with it, and that is a case-law question.
"""
import collections
import json
import os
import re

from .textutil import flatten

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "statute_concordance.json")
with open(_PATH, encoding="utf-8") as _fh:
    _RAW = json.load(_fh)
_OLD_TO_NEW = _RAW["old_to_new"]

_ACTS = [
    ("IPC", r"(?:Indian\s+Penal\s+Code|I\.?\s*P\.?\s*C\b\.?)"),
    ("CrPC", r"(?:Code\s+of\s+Criminal\s+Procedure|Criminal\s+Procedure\s+Code|Cr\.?\s*P\.?\s*C\b\.?)"),
    ("NI Act", r"(?:Negotiable\s+Instruments\s+Act|N\.?\s*I\.?\s+Act)"),
    ("NDPS Act", r"(?:Narcotic\s+Drugs\s+and\s+Psychotropic\s+Substances\s+Act|N\.?\s*D\.?\s*P\.?\s*S\.?\s+Act)"),
    ("Evidence Act", r"(?:Indian\s+)?Evidence\s+Act"),
    ("PC Act", r"Prevention\s+of\s+Corruption\s+Act"),
    ("Constitution", r"Constitution(?:\s+of\s+India)?"),
]
_ACT_RX = [(name, re.compile(rx, re.I)) for name, rx in _ACTS]
_KW = r"(?:Sections?|Secs?\.?|Ss?\.|Articles?|Arts?\.?)"
_SECTION_LIST = re.compile(rf"{_KW}\s*((?:(?:{_KW}\s*)?\d{{1,3}}[A-Z]{{0,2}}(?:\s*\(\s*\w{{1,3}}\s*\))*\s*(?:,|and|&|/|read\s+with|r/w|to|or|-)?\s*)+)\s*(?:of\s+the\s+|of\s+|under\s+the\s+|under\s+)?(?:the\s+)?$", re.I)
_NUM = re.compile(r"(\d{1,3}[A-Z]{0,2})(?:\s*\(\s*(\w{1,3})\s*\))?")

NOT_TOUCHED = {"NI Act": "not part of the 2023 recodification", "NDPS Act": "not part of the 2023 recodification", "Constitution": "not part of the 2023 recodification",
               "PC Act": "not part of the 2023 recodification (other amendments are not tracked here)"}


def to_new(act, section):
    """List of successor provisions [{act, section, change}], [] if the section is in the table with no counterpart, None if it is not in the table."""
    base = re.sub(r"\s+", "", section)
    for key in (f"{act} {section}", f"{act} {base}"):
        if key in _OLD_TO_NEW:
            return [dict(e) for e in _OLD_TO_NEW[key]]
    m = re.match(r"\d+[A-Z]{0,2}", base)
    if m:
        pref = f"{act} {m.group(0)}("
        hits, seen = [], set()
        for k, entries in _OLD_TO_NEW.items():
            if k.startswith(pref):
                for e in entries:
                    if (e["act"], e["section"]) not in seen:
                        seen.add((e["act"], e["section"]))
                        hits.append(dict(e))
        if hits:
            return hits
    return None


def sections_cited(text, top=None):
    """Counter of (act, section) for the provisions a text cites with the act named right after them ("Section 138 of the Negotiable Instruments Act",
    "Sections 302 and 34 IPC"). Sub-sections are folded into the section. References like "Section 138 of the Act" are not counted."""
    flat = flatten(text)
    counts = collections.Counter()
    for act, rx in _ACT_RX:
        for m in rx.finditer(flat):
            window = flat[max(0, m.start() - 110):m.start()]
            lm = _SECTION_LIST.search(window)
            if not lm:
                continue
            for n in _NUM.finditer(lm.group(1)):
                counts[(act, n.group(1).upper())] += 1
    return counts if top is None else collections.Counter(dict(counts.most_common(top)))


def statute_dimension(text, top=6, min_count=1):
    """The provisions most cited in the text, each with what became of it: [{act, section, count, status, successors, note}]. status is one of
    'renumbered', 'renumbered_changed' (the table marks a substantive change), 'no_counterpart', 'not_in_table', 'unaffected', 'replaced_not_mapped'."""
    out = []
    for (act, section), n in sections_cited(text).most_common():
        if n < min_count or len(out) >= top:
            continue
        row = {"act": act, "section": section, "count": n, "successors": [], "status": None, "note": ""}
        if act in ("IPC", "CrPC"):
            succ = to_new(act, section)
            if succ is None:
                row["status"], row["note"] = "not_in_table", "section not found in the NCRB table"
            elif not succ:
                row["status"], row["note"] = "no_counterpart", "in the table with no counterpart (repealed or folded elsewhere)"
            else:
                row["successors"] = succ
                row["status"] = "renumbered_changed" if any(e["change"] for e in succ) else "renumbered"
                row["note"] = ("renumbered and the table marks a substantive change: check the element the case relied on" if row["status"] == "renumbered_changed"
                               else "renumbered; the table marks no substantive change")
        elif act == "Evidence Act":
            row["status"], row["note"] = "replaced_not_mapped", "replaced by the Bharatiya Sakshya Adhiniyam, 2023; section mapping is not in our table"
        elif act in NOT_TOUCHED:
            row["status"], row["note"] = "unaffected", NOT_TOUCHED[act]
        out.append(row)
    return out


def summarise(rows):
    """One flag for the report: STATUTE_CHANGED if any listed IPC/CrPC provision was renumbered, repealed or marked changed, else None. Renumbering is
    a fact about the section, not a verdict on the case."""
    hit = [r for r in rows if r["status"] in ("renumbered", "renumbered_changed", "no_counterpart", "replaced_not_mapped")]
    return "STATUTE_CHANGED" if hit else None
