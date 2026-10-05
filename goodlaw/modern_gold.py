"""An answer key for recent judgments, read from the law reporters' own "Case Law Reference" tables.

From about 2017 the Supreme Court Reports print, in the headnote of each judgment, a table of every earlier case the judgment cites, with what the court did
with it and the paragraph:

    Case Law Reference
    [2006] 3 SCR 420
    referred to
    Para 4
    [1993] 3 SCR 128
    distinguished
    Para 14

That is the same kind of answer key as the old reporters' citator (goodlaw.evaluate), but for modern text, and it sits in the citing judgment itself. So the
checker must be tested on the court's own words after the headnote (`body_only`), never on the table, or it would be reading the answer off the page.

Rows become pairs (cited case, citing judgment, code, citation as printed) when the printed citation resolves to exactly one judgment in the collection. The codes
use the same letters as the old citator so goodlaw.evaluate.summarise reads them: O (overruled, not good law, per incuriam), NF (not approved, disapproved, not
followed, dissented from), F / RF / APL (followed, relied on, approved, applied), D (distinguished, inapplicable), E (explained, clarified), R (referred to).

Pairs are split by a stable hash of the citing judgment: one half is for tuning rules, the other is kept untouched until a result is to be reported.
"""
import re
import zlib

from . import cites as C

_END = re.compile(r"\n\s*(?:CIVIL|CRIMINAL|ORIGINAL|WRIT|TRANSFER|INCOME|ELECTION|SPECIAL|ADMIRALTY|APPELLATE|REVIEW|CONTEMPT|ARBITRATION|COMPANY)\b[^\n]{0,60}(?:JURISDICTION|PETITION|APPEAL)", re.I)

# (pattern on the lower-cased code text, letter), first match wins; the more specific patterns come first
CODE_RULES = [
    (r"overrul|not (?:a )?good law|not (?:the )?correct law|per incuriam", "O"),
    (r"disapprov|not approved|not followed|dissent", "NF"),
    (r"inapplicab|not applicable|distinguish", "D"),
    (r"explain|clarif", "E"),
    (r"relied o[nil]", "RF"),                      # "relied oil" is the OCR's reading of "relied on"
    (r"followed|affirm|approved|applied|held applicable|upheld", "F"),
    (r"referred|discussed|considered|cited|noted", "R"),
]


def code_letter(text):
    """The citator letter for a table's code text, or None when it is not a recognised treatment."""
    t = re.sub(r"\s+", " ", text.lower()).strip(" .")
    for pattern, letter in CODE_RULES:
        if re.search(pattern, t):
            return letter
    return None


_OCR_SERIES = re.compile(r"(\d)\s+s[eo]c\s+(\d)", re.I)
_OCR_YEAR = re.compile(r"^\s*[\[\(c1l]?\s*((?:19|20)\d\d)\s*[\]\)1l]?\s+(?=\d{1,3}\s+(?:Suppl\.?\s+)?(?:SCR|SCC|S\.C\.R|sec)\b|(?:Suppl\.?\s+)?(?:SCR|S\.C\.R)\b)", re.I)


def repair_cite(raw):
    """A table citation with the scanner's usual damage mended: a bracket read as ')' or '1' ("[1993) 2 SCR 581", "[19971 2 SCR 389", "119741 2 SCR 768"), 'SCC' read
    as 'sec' ("(1994) 4 sec 260"), a volume put in brackets ("[2010] (3) SCR 609"). Applied only to the table's own citation lines, where the shape is known."""
    s = re.sub(r"\s+", " ", raw).strip()
    s = _OCR_SERIES.sub(lambda m: f"{m.group(1)} SCC {m.group(2)}", s)
    m = _OCR_YEAR.match(s)
    if m:
        year, rest = m.group(1), s[m.end():]
        if re.match(r"(?:\d{1,3}\s+)?(?:Suppl\.?\s+)?(?:SCR|S\.C\.R)\b", rest, re.I):
            s = f"[{year}] {rest}"
        else:
            s = f"({year}) {rest}"
    s = re.sub(r"(\[(?:19|20)\d\d\])\s*\((\d{1,3})\)\s*(SCR)", r"\1 \2 \3", s, flags=re.I)
    return s


def table_region(text, body_start=None):
    """The part of a judgment's text that holds its case-law table (after the heading 'Case Law Reference', before the first 'APPELLATE JURISDICTION'-type line),
    or None."""
    i = text.find("Case Law Reference")
    if i < 0:
        return None
    limit = body_start or len(text)
    m = _END.search(text, i + 18, limit + 200)
    j = m.start() if m else min(limit, i + 6000)
    return text[i + 18:j]


def table_rows(text, body_start=None):
    """[(citation as printed, code text, paragraphs text)] for the case-law table in a judgment's text; empty when it has none. Each row is three lines, the
    citation, the treatment and 'Para n'; a row whose lines do not fit that shape is skipped."""
    region = table_region(text, body_start)
    if not region:
        return []
    lines = [l.strip() for l in region.split("\n") if l.strip()]
    rows = []
    for k, line in enumerate(lines):
        if k >= 2 and re.match(r"Paras?\b", line, re.I) and not re.match(r"Paras?\b", lines[k - 1], re.I) and not re.match(r"Paras?\b", lines[k - 2], re.I):
            rows.append((lines[k - 2], lines[k - 1], line))
    return rows


def gold_pairs(corpus, source="bucket", years=(2017, 2023), log=None):
    """([(target doc_key, citing doc_key, code letter, citation as printed)], counts). Only judgments whose body start is known are used (the checker is
    tested on the body, never on the table). A row counts only when its citation resolves to exactly one other judgment in the collection."""
    pairs, counts = [], {"judgments_with_table": 0, "rows": 0, "no_code": 0, "no_citation_key": 0, "not_in_collection": 0, "ambiguous": 0, "no_body_start": 0, "pairs": 0}
    lo, hi = years
    for d in corpus.iter_docs(f"dup_of IS NULL AND source='{source}' AND year BETWEEN {int(lo)} AND {int(hi)}"):
        text = corpus.text_of(d["id"])
        rows = table_rows(text, d.get("body_start"))
        if not rows:
            continue
        counts["judgments_with_table"] += 1
        if not d.get("body_start"):
            counts["no_body_start"] += 1
            continue
        for cite, code_text, _para in rows:
            counts["rows"] += 1
            letter = code_letter(code_text)
            if letter is None:
                counts["no_code"] += 1
                continue
            key = C.norm_cite(repair_cite(cite))
            if not key:
                counts["no_citation_key"] += 1
                continue
            hits = [h for h in corpus.by_cite(key) if h["doc_key"] != d["doc_key"]]
            if not hits:
                counts["not_in_collection"] += 1
            elif len(hits) > 1:
                counts["ambiguous"] += 1
            else:
                pairs.append((hits[0]["doc_key"], d["doc_key"], letter, cite))
                counts["pairs"] += 1
    return pairs, counts


def split(pairs):
    """(tuning half, untouched half) by a stable hash of the citing judgment, so every row of one judgment's table stays on one side."""
    tune = [p for p in pairs if zlib.crc32(p[1].encode()) % 2 == 0]
    kept = [p for p in pairs if zlib.crc32(p[1].encode()) % 2 == 1]
    return tune, kept
