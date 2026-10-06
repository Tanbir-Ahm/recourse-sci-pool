"""Reads the structure the crawled and downloaded texts carry: parties, decision date, bench, citations, the reporter's citator, where the
court's own judgment begins. Pure functions on text; nothing here touches the corpus store.

The crawl's texts come in four layouts: (1) up to about 1994 a JUDIS header with PETITIONER, RESPONDENT, DATE OF JUDGMENT, BENCH, CITATION and a
CITATOR INFO block, then ACT, HEADNOTE, JUDGMENT; (2) about 1995 to 2007 the same without citator (CASE NO. first); (3) about 2008 to 2010 a plain
"IN THE SUPREME COURT OF INDIA" caption; (4) about 2010 to 2017 "Page 1 JUDGMENT" captions. The bucket's texts are law-report PDFs.
"""
import re
from datetime import date

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
_M = "|".join(m.capitalize() for m in MONTHS)

_OLD = re.compile(r"PETITIONER:\s*(?P<pet>.*?)\s*RESPONDENT:\s*(?P<resp>.*?)\s*(?=DATE OF JUDGMENT|BENCH:|CITATION:|ACT:|HEADNOTE:|JUDGMENT:|CASE NO)", re.S)
_OLD_DATE = re.compile(r"DATE OF JUDGMENT:?\s*(\d{1,2})/(\d{1,2})/(\d{4})")
_VS = re.compile(
    r"(?P<pet>[^\n]{2,220}?)\s*[.…]{2,}\s*(?:Appell|Petition|Applic|Plaint|Complain|Revisionist|Writ)\w*\s*(?:\(s\))?\s*"
    r"(?:-\s*)?(?:V\.?|Vs\.?|Versus|v/s)\s*-?\s*(?P<resp>.{2,240}?)\s*[.…]{2,}\s*(?:Respond|Defend|Opposite|Accused|Contesting)", re.I | re.S)
_TRAIL_VS = re.compile(r"\s*(?:-\s*)?(?:Vs?\.?|Versus|v/s)\s*-?\s*$", re.I)


def clean_name(s):
    s = re.sub(r"\s+", " ", s or "").strip(" .,;:-")
    s = _TRAIL_VS.sub("", s).strip(" .,;:-")
    return s


_VS_TOKEN = re.compile(r"(?:^|\s):?(?:-\s*)?(?:VERSUS|Versus|versus|VERUS|Verus|Vs\.?|VS\.?|vs\.?|V\.|v\.|v/s):?(?=\s|-|$)\s*-?\s*")
_APP_MARK = re.compile(r"[.…\s]*\(?(?:Appellant|Petitioner|Applicant|Plaintiff|Complainant|Revisionist|Writ Petitioner)s?\)?\s*(?:\(\s*s\s*\))?\s*[.…]*\s*$", re.I)
_RESP_MARK = re.compile(r"\s*[.…]*\s*\(?(?:Respondent|Opposite Party|Defendant|Accused|Contesting Respondent)s?\b", re.I)
_CAPTION_START = re.compile(r"(?:OF\s+(?:19|20)\d\d\s*\]?\)?|\(\s*arising[^)]*\)|\(\s*ARISING[^)]*\)|JURISDICTION|J U D G M E N T|\bNon-?Reportable\b|\bReportable\b|\bPage\s+\d+\b|\bJUDGMENT\b)", re.I)


def _caption_parties(flat):
    """Party names from a flattened caption such as 'ITC LTD. ... Appellant Vs. State of Uttar Pradesh & Ors. ... Respondents'."""
    for vm in _VS_TOKEN.finditer(flat):
        before, after = flat[:vm.start()], flat[vm.end():]
        am = _APP_MARK.search(before)
        if not am:
            continue
        pet_region = before[:am.start()]
        starts = list(_CAPTION_START.finditer(pet_region))
        pet = pet_region[starts[-1].end():] if starts else pet_region
        rm = _RESP_MARK.search(after[:400])
        if not rm:
            continue
        resp = after[:rm.start()]
        pet, resp = clean_name(pet[-220:]), clean_name(resp[:240])
        if len(pet) >= 2 and len(resp) >= 2:
            return pet, resp
    return None, None


_REPORT_TITLE = re.compile(r"(?P<pet>[A-Z][^()]{1,200}?)\s+v\.?\s+(?P<resp>[^()]{2,200}?)\s*\((?:Civil|Criminal|Special|Writ|Transfer|Review|Contempt|SLP|Original|Income|Tax|Arbitration)", re.I)


_REPORT_PREFIX = re.compile(r"^\s*(?:\[\s*(?:19|20)\d\d\s*\]\s*\d+\s*S\.?C\.?R\.?\s*\d+(?:\s*:\s*(?:19|20)\d\d\s+INSC\s+\d+)?|(?:19|20)\d\d\s*(?:\(\s*\d+\s*\)\s*)?(?:Supp\s*\(\s*\d+\s*\)\s*)?SCR\s*\d+)\s*")


def _strip_report_prefix(flat):
    return _REPORT_PREFIX.sub("", flat, count=1)


def parse_parties(text):
    """(petitioner, respondent, layout) from the opening of a crawled text, or (None, None, None)."""
    head = text[:4000]
    m = _OLD.search(head)
    if m and len(m["pet"]) < 300 and len(m["resp"]) < 300:
        return clean_name(m["pet"]), clean_name(m["resp"]), "judis"
    flat = re.sub(r"\s+", " ", head[:3000])
    pet, resp = _caption_parties(flat)
    if pet:
        return pet, resp, "caption"
    m = _VS.search(flat)
    if m:
        return clean_name(m["pet"]), clean_name(m["resp"]), "caption"
    m = _REPORT_TITLE.search(_strip_report_prefix(re.sub(r"\s+", " ", head[:900])))
    if m:
        pet, resp = clean_name(m["pet"][-200:]), clean_name(m["resp"])
        if len(pet) >= 2 and len(resp) >= 2:
            return pet, resp, "report"
    return None, None, None


def to_iso(d, m, y):
    try:
        return date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


_D_WORDS1 = re.compile(rf"\b({_M})\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s*((?:19|20)\d\d)\b")
_D_WORDS2 = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_M})\s*,?\s*((?:19|20)\d\d)\b")
_D_NUM = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-]((?:19|20)\d\d)\b")
_PLACE = re.compile(r"(?:New\s+Delhi|NEW\s+DELHI|Delhi|DELHI)\s*[;,.:]?\s*")


def _dates_in(s):
    """[(position, iso)] for every full date in s."""
    out = []
    for m in _D_WORDS1.finditer(s):
        out.append((m.start(), to_iso(m[2], MONTHS[m[1].lower()], m[3])))
    for m in _D_WORDS2.finditer(s):
        out.append((m.start(), to_iso(m[1], MONTHS[m[2].lower()], m[3])))
    for m in _D_NUM.finditer(s):
        out.append((m.start(), to_iso(m[1], m[2], m[3])))
    return sorted((p, d) for p, d in out if d)


def parse_date(text):
    """(iso date or None, source). The JUDIS header carries the date outright; later layouts only date the judgment at its end, usually on
    the line that names the place ("New Delhi; May 04, 2017."). source is 'header', 'tail_place', 'tail_any' or None."""
    m = _OLD_DATE.search(text[:4000])
    if m:
        iso = to_iso(m[1], m[2], m[3])
        if iso:
            return iso, "header"
    tail = text[-1500:]
    for pm in reversed(list(_PLACE.finditer(tail))):
        near = _dates_in(tail[pm.end():pm.end() + 45])
        if near:
            return near[0][1], "tail_place"
    found = _dates_in(tail)
    if found:
        return found[-1][1], "tail_any"
    return None, None


# ---------------------------------------------------------------- reporter citations in the header
_CITATION_BLOCK = re.compile(r"CITATION:\s*(?P<c>.*?)(?=CITATOR INFO|ACT:|HEADNOTE:|JUDGMENT:|\Z)", re.S)
_AIR = re.compile(r"\b((?:19|20)\d\d)\s+AIR\s*(?:SC\s*)?(\d+)\b")
_SCR = re.compile(r"\b(?:19|20)\d\d\s+(?:Supp\s*\(\d+\)\s*)?SCR\s*(?:\(\d+\)\s*)?\d+\b")
_SCC = re.compile(r"\b(?:19|20)\d\d\s+SCC\s*(?:Supp?l?\.?\s*)?(?:\(\s*\w+\s*\)\s*)?\d+\b")


def parse_header_citations(text):
    """Citations the JUDIS header gives for the judgment itself: {'air': ['1967 AIR 243'], 'scr': ['1966 SCR 209']} (old layout only)."""
    out = {"air": [], "scr": [], "scc": []}
    m = _CITATION_BLOCK.search(text[:5000])
    block = m["c"] if m else ""
    flat = re.sub(r"\s+", " ", block)
    out["air"] = [f"{y} AIR {p}" for y, p in _AIR.findall(flat)]
    out["scr"] = [re.sub(r"\s+", " ", m.group(0)) for m in _SCR.finditer(flat)]
    out["scc"] = [re.sub(r"\s+", " ", m.group(0)) for m in _SCC.finditer(flat)]
    # the 2000s layout prints one line such as "2001 Supp(1) SCR 598" right after JUDGMENT
    if not out["scr"]:
        m2 = re.search(r"\n\s*((?:19|20)\d\d\s+Supp\s*\(\d+\)\s+SCR\s+\d+|(?:19|20)\d\d\s+\(\d+\)\s+SCR\s+\d+)\s*\n", text[:3000])
        if m2:
            out["scr"].append(re.sub(r"\s+", " ", m2[1]))
    return out


# ---------------------------------------------------------------- the reporter's citator (old layout)
CITATOR_CODES = {
    "R": "referred", "RF": "relied on", "F": "followed", "D": "distinguished", "E": "explained", "C": "considered", "APL": "applied",
    "MV": "mentioned", "O": "overruled", "APR": "approved", "OPN": "opinion cited", "AFR": "affirmed", "HO": "held overruled", "A": "affirmed",
    "NF": "not followed", "REI": "reiterated", "MR": "mentioned", "AP": "approved", "REL": "relied on",
}
ADVERSE_CODES = {"O", "HO", "NF"}
_CITATOR_BLOCK = re.compile(r"CITATOR INFO\s*:?(?P<c>.*?)(?=\n\s*(?:ACT|HEADNOTE|JUDGMENT)\s*:)", re.S)
_CITATOR_LINE = re.compile(r"^\s*(?P<code>[A-Z]{1,4})\s+(?P<year>(?:19|20)\d\d)\s+(?P<rep>[A-Z ]{2,8}?)\s*(?P<page>\d+)\s*(?P<paras>\([^)]*\))?\s*$")


def parse_citator(text):
    """The reporter's own list of later cases that cite this one, as printed in the JUDIS header:
    [{'code': 'O', 'meaning': 'overruled', 'year': 1980, 'reporter': 'SC', 'page': 898, 'cite': '1980 SC 898', 'paras': '(15)'}]."""
    m = _CITATOR_BLOCK.search(text[:8000])
    if not m:
        return []
    out = []
    for ln in m["c"].split("\n"):
        mm = _CITATOR_LINE.match(ln)
        if mm:
            code = mm["code"]
            out.append({"code": code, "meaning": CITATOR_CODES.get(code, "unknown code"), "year": int(mm["year"]), "reporter": mm["rep"].strip(),
                        "page": int(mm["page"]), "cite": f"{mm['year']} {mm['rep'].strip()} {mm['page']}", "paras": (mm["paras"] or "").strip("() ")})
    return out


# ---------------------------------------------------------------- bench size
_BENCH = re.compile(r"BENCH:\s*(?P<b>.*?)(?=BENCH:|CITATION:|ACT:|HEADNOTE:|JUDGMENT:|CASE NO|PETITIONER:|\Z)", re.S)
_JJ_LINE = re.compile(r"[\[(]\s*(?P<names>[A-Za-z][^\[\]]{3,500}?)[,.\s]*(?:J\.?\s*J\.?|CJI|C\.J\.?I?\.?|J\.?)[\s,.]*[\]j)]")
_SIG = re.compile(r"(?:[.…_\-]{3,}|\s)\s*(?:CJI|C\.J\.I|C\.J|JJ|J)\s*\.?\s*(?:\(|\n|\Z|$)")


_DESIGNATION = re.compile(r"^(?:CJ[Il1]|CJI|CJ|C\.\s*J\.?(?:\s*I\.?)?|JJ?|J\.\s*J)\.?$", re.I)
_NOT_NAME_WORD = {"the", "of", "in", "on", "for", "to", "under", "act", "rules", "rule", "constitution", "section", "article", "held", "per", "himself", "herself", "court", "state", "union",
                  "india", "appeal", "petition", "civil", "criminal", "case", "judgment", "order", "advs", "adv", "counsel", "with", "by", "is", "was", "are", "an"}


def judge_names(text):
    """The judges' names in a bracketed list ("A. K. SIKRI AND ASHOK BHUSHAN"), or None when the text does not read as a list of names.

    A stray '[' or '(' in a headnote can start a 'list' that runs through prose to the next 'J.'; counting its commas and 'and's once gave benches of 12 to 26 judges.
    The list is cut back to what follows its last open bracket, and then it must be short, with no sentence punctuation, every part one to six words, no ordinary
    words of prose and no figure other than a lone digit (OCR for an initial). A designation ('CJ.', 'CJI') is not a name."""
    s = re.sub(r"\*", "", text)
    s = re.split(r"[\[(]", s)[-1]
    if len(s) > 320 or re.search(r"[:\u2013\u2014]", s):
        return None
    s = s.replace(";", ",")                                                           # OCR for a comma
    s = re.sub(r"\(\s*(?:CJ|J|C\.J\.?|CJI)\s*\)", "", s)
    s = re.sub(r"(?i)\b(?:CJ[Il1]|CJI|C\.\s*J\.\s*I\.?|C\.\s*J\.?|CJ\.?)(?=\W|$)", ",", s)
    parts = [p.strip() for p in re.split(r"\s*(?:&|,|\band\b|\n)\s*", s, flags=re.I) if re.search(r"[A-Za-z]{3,}", p) or _DESIGNATION.match(p.strip())]
    parts = [p for p in parts if not _DESIGNATION.match(p)]
    if not parts:
        return None
    for p in parts:
        words = p.split()
        if not 1 <= len(words) <= 6:
            return None
        for w in words:
            bare = w.strip(".,)")
            if re.search(r"\d", bare) and len(bare) > 1:
                return None
            if len(bare) >= 2 and bare.lower() in _NOT_NAME_WORD:
                return None
    return parts


def _count_names(s):
    parts = judge_names(s)
    return len(parts) if parts else 0


def bench_from_header(text):
    """(size, names) from the JUDIS BENCH: section; the first BENCH: line repeats the presiding judge, so the last BENCH: section is used.
    Returns (None, None) when absent. Lists in the 1995-2007 layout can omit judges; treat the number as a lower bound there."""
    ms = list(_BENCH.finditer(text[:3000]))
    if not ms:
        return None, None
    block = ms[-1]["b"].strip()
    if not block:
        return None, None
    # JUDIS lists one "SURNAME, INITIALS" per line; the 1995-2007 layout puts all names on one line separated by commas or '&'
    splitter = r"\n" if "\n" in block else r"&|,"
    names = [p.strip() for p in re.split(splitter, block) if re.search(r"[A-Za-z]{3,}", p)]
    names = [re.sub(r"\s*\(\s*(?:CJ|J|C\.J\.?|CJI)\s*\)\s*", "", n).strip() for n in names]
    names = [n for n in names if n]
    seen, uniq = set(), []
    for n in names:
        k = re.sub(r"\W+", "", n.lower())
        if k not in seen:
            seen.add(k)
            uniq.append(n)
    return (len(uniq), uniq) if uniq else (None, None)


def bench_from_report_line(text):
    """Bench from the law report's "[A. M. KHANWILKAR AND AJAY RASTOGI, JJ.]" line (bucket PDFs), or (None, None). A page's running header can carry
    just the author ("[DIPAK MISRA, CJI ]"), so of all bracketed judge lists near the top the one naming the most judges is taken."""
    best = (None, None)
    for m in _JJ_LINE.finditer(text[:6000]):
        names = re.sub(r"\*", "", m["names"])
        n = _count_names(names)
        if n and (best[0] is None or n > best[0]):
            best = (n, names)
    return best


def bench_from_signatures(text):
    """Number of distinct signature lines ("...............J." / "(NAME)") in the last 2,500 characters; None if fewer than 1."""
    tail = text[-2500:]
    sigs = re.findall(r"[.…_\-]{3,}\s*,?\s*(?:CJI|C\.J\.I\.?|CJ|JJ|J)\b\.?", tail)
    return len(sigs) if sigs else None


MAX_BENCH = 13          # the largest the Court has sat (Kesavananda Bharati); a count above it is a misreading, not a bench


def bench_size(text, layout=None):
    """(size, source) where source is 'header_full', 'report_line', 'header', 'signatures' or None. 'header_full' (the JUDIS layout with a citator,
    up to about 1994, lists every judge) and 'report_line' (the law report's bracketed list) are complete; 'header' (the 1995-2007 layout, which can omit
    judges) and 'signatures' are lower bounds, so the larger of the two is used and bench comparisons ignore them. A count above MAX_BENCH is dropped."""
    h, _ = bench_from_header(text)
    r, _ = bench_from_report_line(text) if layout != "judis" else (None, None)
    s = bench_from_signatures(text)
    h, r, s = (n if n and n <= MAX_BENCH else None for n in (h, r, s))
    if r:
        return max(r, s or 0), "report_line"
    if h and layout == "judis" and "CASE NO" not in text[:800]:      # the pre-1995 JUDIS layout (no CASE NO. line) lists every judge
        return h, "header_full"
    cands = [(n, src) for n, src in ((h, "header"), (s, "signatures")) if n]
    if cands:
        return max(cands)
    return None, None


# ---------------------------------------------------------------- where the court's own judgment begins (JUDIS layout)
_JUDGMENT_LINE = re.compile(r"(?m)^[ \t]*JUDGMENT:[ \t]*$")


def judis_body_start(text):
    """Offset just after the 'JUDGMENT:' heading of a JUDIS-layout text (everything before it is header, ACT and the reporter's HEADNOTE)."""
    m = _JUDGMENT_LINE.search(text[:60000])
    return m.end() if m else None


def parse_crawl(text):
    """Everything above in one dict for a crawled text."""
    pet, resp, layout = parse_parties(text)
    d, dsrc = parse_date(text)
    size, bsrc = bench_size(text, layout)
    cits = parse_header_citations(text)
    return {"pet": pet, "resp": resp, "layout": layout, "date": d, "date_source": dsrc, "bench_size": size, "bench_source": bsrc,
            "cite_air": cits["air"], "cite_scr": cits["scr"], "cite_scc": cits["scc"], "citator": parse_citator(text),
            "body_start": judis_body_start(text) if layout == "judis" else None}
