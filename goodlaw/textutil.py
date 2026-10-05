"""Text helpers shared by the mention finder and the treatment classifier: one canonical flattening of a judgment's text, sentence boundaries that
do not break on legal abbreviations, and a best-effort paragraph number.

Every quote the checker shows is a substring of `flatten(text)` of the judgment it comes from; `quote_in_text` is the check.
"""
import re

_ABBREV = {
    "v", "vs", "no", "nos", "dr", "mr", "mrs", "ms", "st", "co", "ltd", "pvt", "ors", "anr", "anrs", "art", "arts", "sec", "secs", "sub", "cl", "para", "paras",
    "viz", "etc", "hon", "j", "jj", "cj", "cji", "smt", "shri", "sri", "ss", "vol", "pp", "ex", "re", "dt", "insc", "scc", "air", "scr", "sc", "cri", "lj",
    "all", "bom", "del", "cal", "mad", "ker", "punj", "guj", "raj", "mp", "up", "wp", "crl", "sl", "slp", "ibid", "supp", "cr", "pc", "ipc", "crpc", "pr",
    "prof", "rev", "ch", "sch", "ors", "inc", "corp", "dept", "govt", "assn", "assoc", "bros", "m", "s", "p", "c", "d", "u", "w", "o", "b", "f", "g", "h",
    "k", "l", "n", "r", "t", "y", "e", "a", "i", "x", "z", "q",
}
_BOUNDARY = re.compile(r"([.?!])([\"')\]”’]*)(?:\s+(?=[A-Z0-9(\[“\"'‘])|(?=\[\d))")


_PAGE_HEADER = re.compile(r"https?://JUDIS\.NIC\.IN\s+SUPREME\s+COURT\s+OF\s+INDIA\s+Page\s+\d+\s+of\s+\d+", re.I)


_FOOTNOTE_CITE = re.compile(r"(?:S\.?\s?C\.?\s?R\.?|S\.?\s?C\.?\s?C\.?|I\.?\s?T\.?\s?R\.?|S\.?\s?T\.?\s?C\.?|A\.?\s?I\.?\s?R\.?(?:\s+\d{4})?\s+S\.?\s?C\.?)\s*\d+(?:\s+at\s+\d+)?$", re.I)   # a footnote's citation line followed by the page number of the next page of text: "[1963] 3 S.C.R. 338 at 366. 501 The conduct ..."


_RUNNING_HEAD = re.compile(r"(?:\b[A-H]\s+){4,8}(?:\d{1,4}\s+)?|\b[A-Z][A-Z0-9 .()&',/-]{6,90}?\s+(?:v\.?|versus|vs\.?)\s+[A-Z][A-Z0-9 .()&',/-]{2,60}?\s*\[[A-Z][A-Z .,&'-]{2,45}?,?\s*(?:C\.?J\.?(?:I\.?)?|J\.?|JJ\.?)\]")   # the margin letters "A B C D E F G H 705" and the running caption "JUSTICE K S PUTTASWAMY (RETD) v. UNION OF INDIA [ASHOK BHUSHAN, J.]" of the digital law reports


def flatten(text):
    """The text with every run of whitespace (line wraps, page breaks) turned into a single space, and the JUDIS site's running page header
    ("http://JUDIS.NIC.IN SUPREME COURT OF INDIA Page 4 of 6", repeated on every page of the later crawled texts) removed so that it neither
    glues two sentences together nor sits inside a quoted passage."""
    return re.sub(r"\s+", " ", _RUNNING_HEAD.sub(" ", _PAGE_HEADER.sub(" ", text))).strip()


def sentences(flat):
    """[(start, end)] spans of sentences in an already flattened text. A full stop after a legal abbreviation, an initial or a number does not end
    a sentence; one followed by a capital letter, digit, bracket or quote does."""
    spans, start = [], 0
    for m in _BOUNDARY.finditer(flat):
        if m.group(1) == ".":
            before = flat[start:m.start()]
            word = re.findall(r"[A-Za-z]+$", before)
            if word and word[0].lower() in _ABBREV and (len(word[0]) <= 1 or word[0].lower() in _ABBREV):
                continue
            if re.search(r"\d$", before) and re.match(r"\d", flat[m.end():m.end() + 1] or "") and not _FOOTNOTE_CITE.search(before):
                continue
        end = m.start() + len(m.group(1)) + len(m.group(2))
        spans.append((start, end))
        start = m.end()
    if start < len(flat):
        spans.append((start, len(flat)))
    return spans


def sentence_index(spans, pos):
    """Index of the sentence containing character position pos (the last one if pos is past the end)."""
    lo, hi = 0, len(spans) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if spans[mid][1] <= pos:
            lo = mid + 1
        else:
            hi = mid
    return lo


def paragraph_number(text, pos_in_flat, flat=None):
    """Best-effort number of the numbered paragraph a position falls in: the last "12." that begins a line (in the raw text) before it. Returns
    None when the raw text has no such markers. Approximate; for a human to find the place, not for any decision."""
    flat = flat if flat is not None else flatten(text)
    probe = flat[max(0, pos_in_flat - 40):pos_in_flat + 40]
    raw_pos = text.find(probe[:30]) if len(probe) >= 30 else -1
    if raw_pos < 0:
        return None
    raw_pos += pos_in_flat - max(0, pos_in_flat - 40)
    best = None
    for m in re.finditer(r"(?m)^\s*(\d{1,3})\s*[.)]\s+\S", text[:raw_pos + 1]):
        best = int(m.group(1))
    return best


def quote_in_text(quote, text):
    """True if quote (whitespace-insensitive) occurs word for word in text."""
    return flatten(quote) in flatten(text)
