"""Compare readings of the same page and build the list a person must confirm.

  python checker.py A_reading.txt B_reading.txt > checks.json              (two readings: items and line differences)
  python checker.py --page typed|handwritten --a view1.txt --b view2.txt [--c view3.txt] [--finish-a STOP --finish-b STOP --finish-c STOP] \
                    [--known known_names.json] > page_check.json            (the whole page check: traffic light, plan section 11)
  python checker.py --selftest

Each reading is a harness output (TRANSCRIPTION then TRANSLATION). The transcription is compared letter by letter; the English is compared
only between the two readings, sentence by sentence. The two readings are two blind reads of the SAME page: view 1 the image as given,
view 2 a padded copy (plan section 11 and 10p). An optional third view (ultra-high detail) is used only to show which side of a disagreement
it sides with: a hint for a person, never an answer.
Two kinds of item are produced:
  DISAGREE      the two readers differ (a number, a date, a name, a unit, or a whole line): look at the page.
  CONFIRM       the readers agree, but it is a date, amount, number, unit, section number or name: still confirm it.
                Agreement is not correctness; three readers once agreed on a wrong age, and two runs once agreed on a wrong date.
The tool never marks anything as correct. A person closes every item. Green means "spot-check", never "right".
redundancy.py adds checks that need no model (impossible dates, numbering gaps, English amounts in digits and words that disagree, near-miss names).

Languages: the structure does not depend on the language, but the thresholds were taken from Assamese pages only, and the
patterns for units, honorifics and names were written for Assamese/Bengali script, Devanagari (Hindi, Marathi) and Kannada.
Digits are folded for nine Indian scripts. Units and honorifics for Telugu, Tamil, Malayalam and Gujarati are UNVERIFIED
additions (not checked by a reader of those languages). Kannada and Hindi pages have not been run through this file.
No case data belongs in this folder; the selftest uses invented text.
"""
import argparse, difflib, json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_DIGITS = {}
# Bengali/Assamese, Devanagari, Gurmukhi, Gujarati, Odia, Tamil, Telugu, Kannada, Malayalam digits
for base in (0x09E6, 0x0966, 0x0A66, 0x0AE6, 0x0B66, 0x0BE6, 0x0C66, 0x0CE6, 0x0D66):
    for i in range(10):
        _DIGITS[base + i] = ord("0") + i
UNITS = ["বিঘা", "কঠা", "লেছা", "লেচা", "बीघा", "बिस्वा", "ಎಕರೆ", "ಗುಂಟೆ", "bigha", "katha", "lessa", "acre", "guntha",
         "एकड़", "एकड", "गुंठा", "ఎకరం", "ఎకరా", "గుంట", "ஏக்கர்", "சென்ட்"]      # the last row is unverified (see the docstring)
HONOR = r"(?:শ্ৰীমতী|শ্ৰী|শ্রী|ড°|ডঃ|श्रीमती|श्री|ಶ್ರೀಮತಿ|ಶ್ರೀ|శ్రీమతి|శ్రీ|ശ്രീ|શ્રી|திருமதி|திரு|Smt\.?|Sri|Shri|Mr\.?|Mrs\.?|Dr\.?)"


def norm(s):
    """Comparison form: NFC, digits of all three scripts to ASCII, Assamese ra and wa to the Bengali letters, spaces collapsed."""
    s = unicodedata.normalize("NFC", s).translate(_DIGITS).replace("ৰ", "র").replace("ৱ", "ব")
    return re.sub(r"\s+", " ", s).strip()


def transcription_lines(text):
    head = text.split("TRANSLATION")[0] if "TRANSLATION" in text else text
    out = []
    for l in head.splitlines():
        l = l.strip()
        if not l or re.match(r"^\W*TRANSCRIPTION\W*$", l) or re.match(r"^\[COLUMN \d+\]$", l):
            continue
        out.append(re.sub(r"^\d{1,3}\.\s+", "", l))              # an item number, not a year at the start of a line ("1950. March 14")
    return out


# Month names for dates written in words ("1940ರ ಆಗಸ್ಟ್ 21ರಂದು", "21 August 1940"). BEST EFFORT, NOT CHECKED BY A READER OF THE LANGUAGES: a month name that is missing
# here only means that date is not recognised as a date (it still shows as numbers); a wrong one could make a non-date look like one, and a person checks every item.
_MONTH_NAMES = {
    1: "january জানুৱাৰী জানুৱাৰি জানুয়ারি জানুয়ারী जनवरी ಜನವರಿ", 2: "february ফেব্ৰুৱাৰী ফেব্ৰুৱাৰি ফেব্রুয়ারি फरवरी फ़रवरी ಫೆಬ್ರವರಿ ಫೆಬ್ರುವರಿ",
    3: "march মাৰ্চ মার্চ मार्च ಮಾರ್ಚ್ ಮಾರ್ಚ", 4: "april এপ্ৰিল এপ্রিল अप्रैल ಏಪ್ರಿಲ್ ಏಪ್ರಿಲ", 5: "may মে मई ಮೇ", 6: "june জুন जून ಜೂನ್ ಜೂನ",
    7: "july জুলাই जुलाई ಜುಲೈ", 8: "august আগষ্ট আগস্ট अगस्त ಆಗಸ್ಟ್ ಆಗಸ್ಟ", 9: "september ছেপ্তেম্বৰ ছেপ্টেম্বৰ সেপ্টেম্বর सितंबर सितम्बर ಸೆಪ್ಟೆಂಬರ್ ಸೆಪ್ಟೆಂಬರ",
    10: "october অক্টোবৰ অক্টোবর अक्टूबर अक्तूबर ಅಕ್ಟೋಬರ್ ಅಕ್ಟೋಬರ", 11: "november নৱেম্বৰ নবেম্বৰ নভেম্বর नवंबर नवम्बर ಜ್ನವೆಂಬರ್ ನವೆಂಬರ್ ನವೆಂಬರ",
    12: "december ডিচেম্বৰ ডিসেম্বর दिसंबर दिसम्बर ಡಿಸೆಂಬರ್ ಡಿಸೆಂಬರ"}
_MONTH_TOKENS = sorted(((norm(w).lower(), m) for m, ws in _MONTH_NAMES.items() for w in ws.split()), key=lambda x: -len(x[0]))
_MONTH_RE = re.compile("|".join(re.escape(w) for w, _ in _MONTH_TOKENS))
_MONTH_OF = dict(_MONTH_TOKENS)


def _letter_edge(s, i):
    """True if position i in s is not inside a word (a letter or a combining mark on that side)."""
    return not (0 <= i < len(s) and unicodedata.category(s[i])[0] in "LM")


def month_dates(s):
    """Dates written with a month name in one line of a reading: a month name with a day (1 or 2 digits) and a year (4 digits) within 16 characters.
    Returns [(start, end, canonical 'YYYY-MM-DD')]. The canonical form lets '1940ರ ಆಗಸ್ಟ್ 21ರಂದು' in two readings match even if the endings differ."""
    out = []
    for m in _MONTH_RE.finditer(s.lower()):
        if not (_letter_edge(s, m.start() - 1) and _letter_edge(s, m.end())):
            continue
        lo, hi = max(0, m.start() - 16), min(len(s), m.end() + 16)
        years = [(abs(y.start() - m.start()), y) for y in re.finditer(r"(?<!\d)(?:1[89]\d\d|20\d\d)(?!\d)", s[lo:hi])]
        days = [(abs(d.start() - m.start()), d) for d in re.finditer(r"(?<!\d)\d{1,2}(?!\d)", s[lo:hi])]
        if years and days:
            y = min(years, key=lambda x: x[0])[1]; d = min(days, key=lambda x: x[0])[1]
            a, b = min(y.start(), d.start(), m.start() - lo) + lo, max(y.end(), d.end(), m.end() - lo) + lo
            out.append((a, b, "%s-%02d-%02d" % (y.group(0), _MONTH_OF[m.group(0)], int(d.group(0)))))
    return out


def extract_items(lines):
    items = []
    for ln, raw in enumerate(lines, 1):
        s = re.sub("[\u200c\u200d]", "", norm(raw)); used = []
        def add(kind, m, value=None):
            items.append({"type": kind, "value": (value or m.group(0)).strip(" ,;:.|"), "norm": norm(value or m.group(0)).strip(" ,;:.|").lower(), "line": ln})
            used.append(m.span())
        for m in re.finditer(r"\b\d{1,2}\s*[/\-.।৷]\s*\d{1,2}\s*[/\-.।৷]\s*\d{2,4}\b", s):
            canon = "/".join((q.lstrip("0") or "0") for q in re.split(r"\s*[/\-.।৷]\s*", m.group(0)))          # 09/4/25 and 9/4/25 are the same date
            items.append({"type": "date", "value": m.group(0).strip(" ,;:.|"), "norm": canon, "line": ln}); used.append(m.span())
        for a, b, canon in month_dates(s):                                                          # a date written with a month name
            items.append({"type": "date", "value": s[a:b].strip(" ,;:.|"), "norm": canon, "line": ln}); used.append((a, b))
        for m in re.finditer(r"(?:₹|Rs\.?|रु(?:पये|\.)?|টকা|ರೂ)\s*[0-9][0-9,.]*|[0-9][0-9,.]*\s*(?:/-|টকা|रुपये|ರೂಪಾಯಿ|rupees)", s, re.I): add("amount", m)
        for m in re.finditer(r"(?:section|sec\.?|धारा|ধাৰা|ধারা|ಕಲಂ)\s*\d+[A-Za-z]?", s, re.I): add("section", m)
        for u in UNITS:
            for m in re.finditer(re.escape(norm(u)), s, re.I): add("unit", m)
        for m in re.finditer(HONOR + r"\s*([^\s,;:()\[\]]+(?:\s+[^\s,;:()\[\]]+)?)", s): add("name", m, m.group(1))
        for m in re.finditer(r"\b(?:[A-Z][a-z]+\.?\s+){1,3}[A-Z][a-z]+\b|\b(?:[A-Z]{2,}\s+){1,3}[A-Z]{2,}\b", s):
            if not re.match(HONOR + r"\b", m.group(0)):        # "Shri Ramesh Kumar" is already caught after its honorific
                add("name", m)
        for m in re.finditer(r"\d+(?:[.,]\d+)*(?:-\d+(?:[.,]\d+)*)*", s):
            digits = re.sub(r"\D", "", m.group(0))
            if len(digits) >= 2 and set(digits) != {"0"} and not any(a <= m.start() < b for a, b in used):          # "-000-" is a separator, not a value
                add("number", m)
    return items


def compare(text_a, text_b):
    la, lb = transcription_lines(text_a), transcription_lines(text_b)
    ia, ib = extract_items(la), extract_items(lb)
    ka = {(i["type"], i["norm"]): i for i in ia}; kb = {(i["type"], i["norm"]): i for i in ib}
    result = []
    for k in ka:
        if k in kb:
            result.append({"status": "CONFIRM", "type": k[0], "A": ka[k]["value"], "B": kb[k]["value"], "line_A": ka[k]["line"], "line_B": kb[k]["line"]})
    ona = [k for k in ka if k not in kb]; onb = [k for k in kb if k not in ka]
    for k in list(ona):                           # pair near misses of the same kind: 98599-79979 against 98659-79979
        best = max((o for o in onb if o[0] == k[0]), key=lambda o: difflib.SequenceMatcher(None, k[1], o[1]).ratio(), default=None)
        if best and difflib.SequenceMatcher(None, k[1], best[1]).ratio() >= 0.6:
            result.append({"status": "DISAGREE", "type": k[0], "A": ka[k]["value"], "B": kb[best]["value"], "line_A": ka[k]["line"], "line_B": kb[best]["line"]})
            ona.remove(k); onb.remove(best)
    for k in ona: result.append({"status": "DISAGREE", "type": k[0], "A": ka[k]["value"], "B": None, "line_A": ka[k]["line"], "line_B": None})
    for k in onb: result.append({"status": "DISAGREE", "type": k[0], "A": None, "B": kb[k]["value"], "line_A": None, "line_B": kb[k]["line"]})
    na, nb = [norm(x) for x in la], [norm(x) for x in lb]
    diffs = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, na, nb, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        for k in range(max(i2 - i1, j2 - j1)):
            a = la[i1 + k] if i1 + k < i2 else None; b = lb[j1 + k] if j1 + k < j2 else None
            ratio = difflib.SequenceMatcher(None, norm(a or ""), norm(b or "")).ratio() if a and b else 0.0
            diffs.append({"line_A": i1 + k + 1 if a else None, "line_B": j1 + k + 1 if b else None, "A": a, "B": b, "similarity": round(ratio, 2)})
    ca, cb = sum(len(x) for x in na), sum(len(x) for x in nb)
    summary = {"lines_A": len(la), "lines_B": len(lb), "characters_A": ca, "characters_B": cb,
               "disagreements": sum(1 for r in result if r["status"] == "DISAGREE"), "to_confirm": sum(1 for r in result if r["status"] == "CONFIRM"),
               "differing_lines": len(diffs),
               "possible_dropped_text": bool(ca and cb and min(ca, cb) / max(ca, cb) < 0.85)}
    result.sort(key=lambda r: (r["status"] != "DISAGREE", r["line_A"] or r["line_B"] or 0))
    return {"summary": summary, "items": result, "line_diffs": diffs}


# ---- the whole page check (plan section 11) ------------------------------------------------------------------------
# These numbers are a FIRST GUESS taken from a handful of Assamese comparisons (run-to-run agreement of argon on four typed pages was 86 to 98
# percent). Tune them on the 30-page test.
GREEN_AGREE = 97.0       # letter agreement needed for green
RED_AGREE = 90.0         # below this the page is red
DROP_RATIO = 0.85        # a reading with less than this share of the other's letters has probably dropped text
ENGLISH_WOBBLE = 0.85    # an English sentence more different than this between the two runs is flagged
PAGE_TYPES = ("typed", "handwritten")


def letters(text):
    """A reading reduced to its letters for comparison: transcription lines only, line-end hyphens joined, then only
    letters, vowel signs and digits kept, in the comparison form of norm()."""
    t = "\n".join(transcription_lines(text))
    t = re.sub(r"-\s*\n\s*", "", t)
    t = norm(t)
    return "".join(c for c in t if unicodedata.category(c)[0] in "LMN").lower()


def edit_distance(a, b):
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def agreement(text_a, text_b):
    """Percent of letters that agree: 100 minus edit distance over the longer reading. Over 6000 letters it uses difflib's
    ratio instead (a little more generous) so a long page does not take minutes, and says so."""
    a, b = letters(text_a), letters(text_b)
    if not a or not b:
        return {"percent": 0.0, "method": "no text in one of the readings", "letters_A": len(a), "letters_B": len(b)}
    if max(len(a), len(b)) > 6000:
        pct, method = 100 * difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), "difflib ratio (long page)"
    else:
        pct, method = 100 * (1 - edit_distance(a, b) / max(len(a), len(b))), "edit distance"
    return {"percent": round(pct, 1), "method": method, "letters_A": len(a), "letters_B": len(b),
            "share": round(min(len(a), len(b)) / max(len(a), len(b)), 2)}


ORDER_OK_AGREE = 95.0       # below the red line in order but at least this with the lines in any order: a block was read in a different place, not different text


def agreement_unordered(text_a, text_b):
    """Agreement with the LINES of each reading sorted first, so a stamp block or a note that one reading put in a different place does not count as different text."""
    srt = lambda t: "TRANSCRIPTION\n" + "\n".join(sorted(transcription_lines(t)))
    return agreement(srt(text_a), srt(text_b))


_ABBREV = re.compile(r"\b(?:vs|v|no|nos|sec|secs|art|arts|dr|mr|mrs|ms|smt|shri|sri|crl|cri|i\.e|e\.g|etc|viz|cf|ors|anr|pp|para|paras|ltd|st|rs|govt|addl|hon|secy|dept|asst|p\.s)\.|\b(?:[A-Za-z]\.){2,}|\b[A-Z]\.(?=\s*[A-Z\[(])", re.I)


def english_sentences(text):
    """The English part of a harness output as sentences (the harness uses the LAST TRANSLATION heading). A full stop after an abbreviation
    (vs., No., S.C.C., an initial like S. N.) does not end a sentence, so two drafts that differ only in how they break such a line still match."""
    i = text.rfind("TRANSLATION")
    if i < 0:
        return []
    tail = re.sub(r"\s+", " ", text[i + len("TRANSLATION"):].lstrip("*:# \n-")).strip()
    tail = _ABBREV.sub(lambda m: m.group(0).replace(".", "\u2024"), tail)
    return [x.replace("\u2024", ".") for x in re.split(r"(?<=[.?!])\s+", tail) if x]


def english_wobble(text_a, text_b):
    """English sentences that changed between two runs of the same reader (a wrong meaning given both times is not caught)."""
    la, lb = english_sentences(text_a), english_sentences(text_b)
    out = []
    ops = difflib.SequenceMatcher(None, [x.lower() for x in la], [x.lower() for x in lb], autojunk=False).get_opcodes()
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            continue
        for k in range(max(i2 - i1, j2 - j1)):
            a = la[i1 + k] if i1 + k < i2 else None
            b = lb[j1 + k] if j1 + k < j2 else None
            r = difflib.SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio() if a and b else 0.0
            if r < ENGLISH_WOBBLE:
                out.append({"run1": a, "run2": b, "similarity": round(r, 2)})
    return out


_TERM = re.compile(r"\b[A-Z][A-Za-z.'\-]*(?:\s+(?:(?i:of|and|the|for|in)\s+)?[A-Z][A-Za-z.'\-]*)+")


_MONTHS = "january february march april may june july august september october november december".split()
_TERM_EDGE = set(_MONTHS) | set("on in the this that these those it its he she they we our however thereafter meanwhile under even but and also held where when while although "
                                 "since because therefore hence thus then now further learned".split())


def english_terms(text):
    """Named things in an English draft: runs of capitalised words (court, party and statute names, titles) and numbers of two or more digits, lower-cased."""
    i = text.rfind("TRANSLATION")
    t = re.sub(r"\s+", " ", text[i + len("TRANSLATION"):] if i >= 0 else text)
    names = set()
    for m in _TERM.finditer(t):
        words = re.sub(r"[.\s]+", " ", re.sub(r"\.\s*-+\s*", ". ", m.group(0))).strip().lower().split()
        while words and words[0] in _TERM_EDGE:                  # a sentence-opening word that is not part of the name ("On April", "However")
            words.pop(0)
        while words and words[-1] in _TERM_EDGE:
            words.pop()
        if words and not (len(words) == 1 and words[0] in _TERM_EDGE) and not all(w in _TERM_EDGE for w in words):
            names.add(" ".join(words))
    def _num(n):
        n = re.sub(r"[,.]$", "", n).lower()
        return "/".join((q.lstrip("0") or "0") for q in n.split("/")) if re.fullmatch(r"\d+/\d+/\d+", n) else n          # 09/4/25 and 9/4/25 are one number
    nums = {_num(n) for n in re.findall(r"\d[\d,./]*(?:[A-Z](?![A-Za-z]))?", t) if len(re.sub(r"\D", "", n)) >= 2}
    return names, nums


def english_term_differences(text_a, text_b):
    """Names and numbers that one English draft has and the other lacks. Catches 'Union of India' against 'Union Government of India', which a
    sentence-by-sentence comparison can miss because the rest of the sentence is the same. Noisy by nature: a list to look at."""
    na, da = english_terms(text_a); nb, db = english_terms(text_b)
    out = [{"kind": "name", "only_in_view_1": sorted(na - nb), "only_in_view_2": sorted(nb - na)}] if (na - nb or nb - na) else []
    if da - db or db - da:
        out.append({"kind": "number", "only_in_view_1": sorted(da - db), "only_in_view_2": sorted(db - da)})
    return out


def reading_problem(text, finish=None):
    """Why a reading cannot be trusted at all, or None. finish is the model's finish reason when the harness recorded one."""
    if not text or not text.strip():
        return "no reading"
    if finish is not None and finish != "STOP":
        return "cut off (finish reason %s)" % finish
    if "TRANSLATION" not in text:
        return "no TRANSLATION section: the reading stopped early or ignored the format"
    if not transcription_lines(text):
        return "empty transcription"
    return None


def doubtful_marks(text):
    """How many words the reader itself marked as doubtful in the transcription."""
    head = text.split("TRANSLATION")[0] if "TRANSLATION" in text else text
    return head.count("[unclear]") + head.count("(?)") + head.count("[struck: ?]")


_MARKS = (("struck out", re.compile(r"~~(.+?)~~", re.S)),
          ("inserted above the line", re.compile(r"\^([^\^\n]+?)\^")),
          ("stamp or seal over text", re.compile(r"\[(?:stamp|seal) over text\]", re.I)),
          ("struck out, unreadable", re.compile(r"\[struck: ?\?\]", re.I)),
          ("doubtful reading, explained", re.compile(r"<doubtful:\s*([^>]*)>", re.S)))
CORRECTION_KINDS = ("struck out", "inserted above the line", "stamp or seal over text", "struck out, unreadable")      # what a person must look at on the page; 'doubtful' is a note about meaning


def correction_marks(text):
    """The marks the reader put in (prompts/read_translate_marked.txt) for crossed-out words, words inserted above the line, stamps over writing and doubtful readings it
    explained, found in the TRANSCRIPTION and in the TRANSLATION part of one reading. [{'kind', 'text', 'where' ('original' or 'English'), 'line'}]. Nothing is judged here."""
    if not text:
        return []
    i = text.rfind("TRANSLATION")
    parts = (("original", text[:i] if i >= 0 else text), ("English", text[i + len("TRANSLATION"):] if i >= 0 else ""))
    out = []
    for where, part in parts:
        for kind, rx in _MARKS:
            for m in rx.finditer(part):
                ls = part.rfind("\n", 0, m.start()) + 1; le = part.find("\n", m.end()); le = len(part) if le < 0 else le
                out.append({"kind": kind, "text": (m.group(1).strip() if m.groups() else ""), "where": where, "line": re.sub(r"\s+", " ", part[ls:le]).strip()[:140]})
    return out


def merge_marks(reads):
    """reads: [(view name, reading text)]. The marks of all the readings as one list; each says which views have it (a mark found in only some of the readings is how a
    crossed-out word that one reading dropped shows up). Marks are matched by kind, part and the flat text; the same stamp twice is matched in order."""
    merged, count = {}, {}
    for name, text in reads:
        seen = {}
        for m in correction_marks(text):
            key = (m["kind"], m["where"], _flat(m["text"]))
            n = seen[key] = seen.get(key, 0) + 1
            k = key + (n,)
            if k not in merged:
                merged[k] = dict(m, views=[])
            merged[k]["views"].append(name)
    return [dict(v, in_all=len(v["views"]) == len(reads)) for v in merged.values()]


def parse_sense(text):
    """The list a sense-check call returns (prompts/sense_check.txt), or None when it cannot be read. Each item: {'quote', 'problem', 'severity'}."""
    m = re.search(r"\[.*\]", text or "", re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    if not isinstance(data, list):
        return None
    return [{"quote": str(d["quote"]).strip(), "problem": str(d.get("problem", "")).strip(), "severity": "high" if str(d.get("severity", "")).lower() == "high" else "low"}
            for d in data if isinstance(d, dict) and str(d.get("quote", "")).strip()]


def match_sense(items, english):
    """Keep only the sense-check findings whose quote really is in the English (a checker can invent a quote); returns (kept, number dropped). Whitespace and case are ignored."""
    flat = lambda t: re.sub(r"\s+", " ", t or "").strip().lower()
    e = flat(english)
    kept = [i for i in items if len(flat(i["quote"])) >= 6 and flat(i["quote"]) in e]
    return kept, len(items) - len(kept)


def apply_sense(out, kept, dropped=0):
    """Put the sense-check findings into a page or document check: amber at most, never red, never a verdict. A green page with a finding becomes amber."""
    out["sense_flags"] = kept; out["sense_unmatched"] = dropped
    if not kept:
        return out
    hi = sum(1 for k in kept if k["severity"] == "high")
    out["reasons_amber"].append("the sense check found %d sentence(s) or phrase(s) that may not make sense%s: look at each against the page (see 'Read these first')" % (len(kept), " (%d high)" % hi if hi else ""))
    if out.get("light") == "green":
        out["light"] = "amber"
        out["person_task"] = "Look at every flagged item and line against the page image, then tick the must-check list (%d item(s))." % len(out.get("must_check", []))
    return out


def _val_re(v):
    return r"(?<![\d/.,\-])" + re.escape(v) + r"(?![\d/])"


def mark_disagreements(english, items):
    """The English that is shown to be read, with every value that the readings of the page disagree on printed as BOTH values, so a wrong guess never reads as fact:
    '[02/4/25 or 9/4/25 (third look: 9/4/25): check]'. items: [{'A', 'B', 'third_view', ...}] (view 1's value, view 2's value, the side the third look takes). A value found in
    one reading only is shown as '[02/4/25: found in one reading only: check]'. Only a value that appears in the English as written can be marked; the others are returned as
    unplaced. Returns (marked text, number marked, unplaced items). The checks themselves run on the unmarked English."""
    text, placed, unplaced = english or "", 0, []
    for it in items or []:
        a, b = it.get("A"), it.get("B")
        if not (a or b):
            continue
        target = next((v for v in (a, b) if v and re.search(_val_re(v), text)), None)
        core = "%s or %s" % (a, b) if (a and b) else "%s: found in one reading only" % (a or b)
        if target is None:
            if not any("[" + core in text for _ in (0,)):
                unplaced.append(it)
            continue
        if "[" + core in text:
            continue
        side = {"view 1": a, "view 2": b}.get(it.get("third_view"))
        note = " (third look: %s)" % side if side else ""
        text = re.sub(_val_re(target), lambda m: "[%s%s: check]" % (core, note), text)
        placed += 1
    return text, placed, unplaced


def _flat(s):
    s = norm(s).replace("'", ".")
    s = re.sub(r"[।৷]", "/", s)
    return re.sub(r"[\s\u200c\u200d]+", "", re.sub(r"\s*/\s*", "/", s)).lower()


def tiebreak(items, run3):
    """For items the first two views disagree on, which side a third view reads. A hint for a person, never an answer."""
    head = _flat("\n".join(transcription_lines(run3)))
    out = []
    for i in items:
        if i["status"] != "DISAGREE" or not (i["A"] and i["B"]):
            continue
        a, b = _flat(i["A"]) in head, _flat(i["B"]) in head
        out.append({"type": i["type"], "view1": i["A"], "view2": i["B"], "third_view": "view 1" if a and not b else "view 2" if b and not a else "both" if a and b else "neither"})
    return out


DIGIT_TYPES = ("date", "amount")        # values whose digits matter most: every page that has one gets a third look (plan section 10w)
CONTRA_TYPES = ("date", "amount", "number", "section")   # what the third view is compared on once it exists (no false alarm on 12 pages that have a third view: 10y)


def third_view_contradictions(items, run3):
    """Items the first two views AGREE on (so the check list shows them as 'still confirm') that the ultra-high-detail view does not read the same way.
    Found on the first fresh document (10w): both views read a year as 2023, the page says 2026, and only the third view read it right. Returns
    [{'type', 'views_1_and_2', 'third_view'}]; third_view is the nearest value of that type the third view read, or None. A hint, never an answer."""
    third = extract_items(transcription_lines(run3))
    have = {(i["type"], i["norm"]) for i in third}
    seen = {}
    for i in third:
        seen.setdefault(i["type"], []).append(i["value"])
    out = []
    for i in items:
        if i["status"] != "CONFIRM" or i["type"] not in CONTRA_TYPES or not i["A"]:
            continue
        mine = extract_items([i["A"]])                      # the same canonical form the first two views were compared in
        if mine and all((m["type"], m["norm"]) in have for m in mine):
            continue
        near = difflib.get_close_matches(i["A"], seen.get(i["type"], []), n=1, cutoff=0.0)
        out.append({"type": i["type"], "views_1_and_2": i["A"], "third_view": near[0] if near else None})
    return out


def third_view_reason(items, agr_pct):
    """Why a page gets a third look, or None: the first two views disagree on an item, agree on fewer letters than GREEN_AGREE, or the page holds a date or
    an amount (agreement between two views of the same image is not proof of a digit)."""
    if any(i["status"] == "DISAGREE" for i in items):
        return "the first two views disagree on an item"
    if agr_pct is not None and agr_pct < GREEN_AGREE:
        return "the first two views agree on fewer letters than %.0f%%" % GREEN_AGREE
    if any(i["type"] in DIGIT_TYPES for i in items):
        return "the page holds a date or an amount: a second look at ultra-high detail"
    return None


def _glossary_note(out, amber, readings):
    """Glossary notes (glossary.py) for one or more readings: [(label, original-script text, English text)]. Adds them to out and one line to the amber reasons."""
    import glossary
    notes = glossary.notes_for_readings(readings)
    out["glossary_notes"] = notes
    if notes:
        strong = [n for n in notes if n["level"] == "strong"]
        amber.append("glossary: %d note(s) on words with a settled legal meaning%s: look at them (entries not yet approved by a lawyer are a prompt to look, not a rule)" % (
            len(notes), (" (%d where the English uses a rendering to avoid)" % len(strong)) if strong else ""))


def check_page(page_type, run1, run2, run3=None, finish1=None, finish2=None, finish3=None, known=None):
    """The traffic light for one page read as an image. page_type: typed or handwritten. run1, run2: two blind readings of the same page
    (the image as given, and a padded copy); run3: the optional ultra-high-detail reading. Returns a dict; 'light' is green, amber or red.
    It never says a page is correct."""
    import redundancy
    if page_type not in PAGE_TYPES:
        raise ValueError("page_type must be one of %s" % (PAGE_TYPES,))
    red, amber, notes = [], [], []
    out = {"page_type": page_type, "thresholds": {"green_agree": GREEN_AGREE, "red_agree": RED_AGREE, "drop_ratio": DROP_RATIO,
                                                  "english_wobble": ENGLISH_WOBBLE, "status": "first guess, tune on the 30-page test"}}
    for name, text, fin in (("view 1 (image as given)", run1, finish1), ("view 2 (padded copy)", run2, finish2)):
        p = reading_problem(text, fin)
        if p:
            red.append("%s: %s" % (name, p))
    if run3 is not None:
        p = reading_problem(run3, finish3)
        if p:
            notes.append("view 3 (ultra-high detail) cannot be used: %s" % p); run3 = None
    items = []
    if run1 and run1.strip() and run2 and run2.strip():
        agr = agreement(run1, run2)
        out["agreement_view1_vs_view2"] = agr
        if agr["percent"] < RED_AGREE:
            un = agreement_unordered(run1, run2)
            if un["percent"] >= ORDER_OK_AGREE:               # same text, different order of blocks (10ak): amber, not red
                out["agreement_unordered"] = un
                amber.append("the two views agree on only %.1f%% of letters in order, but on %.1f%% when the order of the lines is ignored: a block (a stamp, a note) was read in a different place" % (agr["percent"], un["percent"]))
            else:
                red.append("the two views agree on only %.1f%% of letters (red below %.0f%%)" % (agr["percent"], RED_AGREE))
        elif agr["percent"] < GREEN_AGREE:
            amber.append("the two views agree on %.1f%% of letters (green needs %.0f%% or more)" % (agr["percent"], GREEN_AGREE))
        if agr.get("share", 1) < DROP_RATIO:
            red.append("one view has much less text than the other (%.0f%% of the letters): possible dropped text" % (100 * agr["share"]))
        c12 = compare(run1, run2)
        out["line_differences"] = c12["line_diffs"]
        if c12["summary"]["disagreements"]:
            amber.append("%d must-check item(s) differ between the two views" % c12["summary"]["disagreements"])
        items = list(c12["items"])
        wob = english_wobble(run1, run2)
        out["english_wobble"] = wob
        if wob:
            amber.append("%d English sentence(s) changed between the two views" % len(wob))
        terms = english_term_differences(run1, run2)
        out["english_term_differences"] = terms
        for t in terms:
            amber.append("English %ss that differ between the views: %s" % (t["kind"], "; ".join(
                ["view 1 only: " + ", ".join(t["only_in_view_1"][:6])] * bool(t["only_in_view_1"]) + ["view 2 only: " + ", ".join(t["only_in_view_2"][:6])] * bool(t["only_in_view_2"]))))
        marks = doubtful_marks(run1) + doubtful_marks(run2)
        if marks:
            amber.append("the reader marked %d doubtful word(s) as [unclear] or (?)" % marks)
        seen = []
        for r in (run1, run2):
            eng = r.split("TRANSLATION")[-1] if "TRANSLATION" in r else None
            for f in redundancy.page_flags(r, eng, known):
                if f not in seen:
                    seen.append(f)
        out["redundancy_flags"] = seen
        amber += ["page check: " + f for f in seen]
        _glossary_note(out, amber, [("view 1", run1.split("TRANSLATION")[0], run1.split("TRANSLATION")[-1] if "TRANSLATION" in run1 else ""),
                                    ("view 2", run2.split("TRANSLATION")[0], run2.split("TRANSLATION")[-1] if "TRANSLATION" in run2 else "")])
        if run3 is not None:
            out["agreement_view3_vs_view1"] = agreement(run3, run1); out["agreement_view3_vs_view2"] = agreement(run3, run2)
            out["third_view_on_disagreements"] = tiebreak(items, run3)
            contra = third_view_contradictions(items, run3)
            out["third_view_contradicts"] = contra
            eng3 = run3.split("TRANSLATION")[-1] if "TRANSLATION" in run3 else None
            for f in redundancy.page_flags(run3, eng3, known):                   # the same no-model checks on view 3: a numbering that skips, an impossible date
                if f not in seen:
                    out["redundancy_flags"].append("view 3 reads: " + f); amber.append("page check, third view only: " + f)
            if contra:
                amber.append("the third view (ultra-high detail) reads %d agreed value(s) differently from both views: %s: look at these first" % (
                    len(contra), "; ".join("%s %s against %s" % (c["type"], c["views_1_and_2"], c["third_view"] or "nothing") for c in contra[:4])))
    else:
        out["agreement_view1_vs_view2"] = None
        if not red:
            red.append("fewer than two readings: run the second view")
    reads = [("view 1", run1), ("view 2", run2)] + ([("view 3", run3)] if run3 is not None else [])
    cm = [m for m in merge_marks([(n, t) for n, t in reads if t and t.strip()])]
    out["corrections"] = cm
    seen_c = {(m["kind"], _flat(m["text"])) for m in cm if m["kind"] in CORRECTION_KINDS}
    if seen_c:
        amber.append("the reader marked %d correction(s) on the page (crossed-out or inserted words, or a stamp over writing): look at each on the image" % len(seen_c))
        some = [m for m in cm if m["kind"] in CORRECTION_KINDS and m["where"] == "original" and not m["in_all"]]
        if some:
            amber.append("%d correction mark(s) are in only some of the readings (a crossed-out word that one reading kept or dropped without a mark): %s" % (
                len(some), "; ".join("%s '%s'" % (m["kind"], m["text"]) if m["text"] else m["kind"] for m in some[:4])))
    dbt = {_flat(m["text"]) for m in cm if m["kind"] == "doubtful reading, explained"}
    if dbt:
        amber.append("the reader explained %d doubtful reading(s) (a word that did not make sense as written): look at each on the image" % len(dbt))
    if page_type == "handwritten":
        amber.append("handwriting has no independent machine check: a person must look at every date, number and name")
    light = "red" if red else "amber" if amber else "green"
    out["light"] = light
    out["reasons_red"], out["reasons_amber"], out["notes"] = red, amber, notes
    # a third image view can only settle a difference in what the page says; it cannot settle a difference in English wording
    agr_pct = (out.get("agreement_view1_vs_view2") or {}).get("percent")
    out["third_view_reason"] = third_view_reason(items, agr_pct) if (run1 and run2) else None
    out["needs_third_view"] = out["third_view_reason"] is not None
    n_check = sum(1 for i in items if i["status"] in ("CONFIRM", "DISAGREE"))
    out["person_task"] = {
        "green": "Tick the must-check list (%d item(s)) against the page image. Nothing was flagged. Green means spot-check, not correct." % n_check,
        "amber": "Look at every flagged item and line against the page image, then tick the must-check list (%d item(s))." % n_check,
        "red": "Read the whole page. Use the machine English only as a help, and do not rely on it.",
    }[light]
    out["must_check"] = items
    out["stamp"] = "Machine draft. Not a certified translation."
    return out


def check_text_page(text, english1, english2, known=None):
    """The check for a PDF page whose own text layer is used (step 2): the source is exact, so only the two English drafts and the
    redundancy checks are in question. text: the text layer; english1, english2: two blind translations (each with a TRANSLATION heading)."""
    import redundancy
    amber, red = [], []
    for n, e in (("English draft 1", english1), ("English draft 2", english2)):
        if not e or "TRANSLATION" not in e or not english_sentences(e):
            red.append("%s: no translation" % n)
    items = [dict(i, status="CONFIRM", A=i["value"], B=i["value"], source="text layer") for i in extract_items(transcription_lines("TRANSCRIPTION\n" + text))]
    wob = english_wobble(english1, english2) if not red else []
    if wob:
        amber.append("%d English sentence(s) changed between the two drafts" % len(wob))
    flags = redundancy.page_flags("TRANSCRIPTION\n" + text, None, known)
    for e in (english1, english2):
        for w, dg, wd in redundancy.english_amount_check(e.split("TRANSLATION")[-1] if e else ""):
            f = "English amount '%s': digits say %s, words say %s" % (w, dg, wd)
            if f not in flags:
                flags.append(f)
        for f in redundancy.designation_flags(e.split("TRANSLATION")[-1] if e else ""):
            if "designation: " + f not in flags:
                flags.append("designation: " + f)
    amber += ["page check: " + f for f in flags]
    gl = {}
    _glossary_note(gl, amber, [("draft 1", text, english1.split("TRANSLATION")[-1] if english1 else ""), ("draft 2", text, english2.split("TRANSLATION")[-1] if english2 else "")])
    light = "red" if red else "amber" if amber else "green"
    return {"glossary_notes": gl.get("glossary_notes", []), "page_type": "text_layer", "light": light, "reasons_red": red, "reasons_amber": amber, "english_wobble": wob, "redundancy_flags": flags,
            "must_check": items,
            "person_task": {"green": "The source text is the PDF's own text. Check the English draft against it and tick the must-check list (%d item(s))." % len(items),
                            "amber": "Check the flagged English sentences and items against the source text, then tick the must-check list (%d item(s))." % len(items),
                            "red": "The translation failed: translate this page by hand."}[light],
            "stamp": "Machine draft. Not a certified translation."}


def check_document(source, english1, english2, known=None, finish1="STOP", finish2="STOP", joins=None, page_items=None, page_corrections=None):
    """The check for a WHOLE document translated twice from its joined text (stitch.py). source: the joined original text; english1, english2: the two
    translations (with or without a TRANSLATION heading). Flags only; nothing is marked correct and nothing is corrected.
    Amber for: sentences that changed between the two translations, a name or number that only one translation has, a clause / rule / article /
    section number that the two translations count differently, a printed reference that disagrees with itself (redundancy.reference_flags),
    [sic], (?), (spelling unsure) and [unclear] marks the model put in, and the redundancy checks. Red: a translation that is missing, cut off, or much shorter."""
    import redundancy
    body = lambda e: e.split("TRANSLATION", 1)[1].lstrip("*:# \n-") if e and "TRANSLATION" in e else (e or "")
    e1, e2 = body(english1), body(english2)
    red, amber = [], []
    for n, e, f in (("Translation 1", e1, finish1), ("Translation 2", e2, finish2)):
        if not e.strip():
            red.append("%s: no translation" % n)
        elif f not in (None, "STOP"):
            red.append("%s: cut off (%s)" % (n, f))
    if e1.strip() and e2.strip() and min(len(e1), len(e2)) < DROP_RATIO * max(len(e1), len(e2)):
        red.append("one translation is much shorter than the other (%d against %d characters)" % (len(e1), len(e2)))
    a1, a2 = "TRANSLATION\n" + e1, "TRANSLATION\n" + e2
    wob = english_wobble(a1, a2) if not red else []
    if wob:
        amber.append("%d sentence(s) changed between the two translations" % len(wob))
    diffs = english_term_differences(a1, a2) if not red else []
    names = next((d for d in diffs if d["kind"] == "name"), None)
    nums = next((d for d in diffs if d["kind"] == "number"), None)
    if names:
        amber.append("%d name(s) or title(s) that only one translation has" % (len(names["only_in_view_1"]) + len(names["only_in_view_2"])))
    if nums:
        amber.append("number(s) that only one translation has: %s" % ", ".join(nums["only_in_view_1"] + nums["only_in_view_2"]))
    r1, r2 = redundancy.legal_references(e1), redundancy.legal_references(e2)
    ref_diff = sorted("%s %s: %d against %d" % (k[0], k[1], r1[k], r2[k]) for k in set(r1) | set(r2) if r1[k] != r2[k])
    if ref_diff:
        amber.append("clause, rule, article or section reference(s) counted differently by the two translations: " + "; ".join(ref_diff))
    rflags = []
    for e in (e1, e2):
        for f in redundancy.reference_flags(e):
            if f not in rflags:
                rflags.append(f)
    amber += ["reference check: " + f for f in rflags]
    dflags = []
    for e in (e1, e2):
        for f in redundancy.designation_flags(e):
            if f not in dflags:
                dflags.append(f)
    amber += ["designation check: " + f for f in dflags]
    gl = {}
    _glossary_note(gl, amber, [("translation 1", source, e1), ("translation 2", source, e2)])
    marks = {m: sum(e.count(m) for e in (e1, e2)) for m in ("[sic]", "(?)", "(spelling unsure)", "[unclear]", "<doubtful:", "~~")}
    for m, n in marks.items():
        if n:
            amber.append("%d '%s' mark(s) put in by the model: look at each" % (n, m))
    flags = redundancy.page_flags("TRANSCRIPTION\n" + source, None, known)
    for e in (e1, e2):
        for w, dg, wd in redundancy.english_amount_check(e):
            f = "English amount '%s': digits say %s, words say %s" % (w, dg, wd)
            if f not in flags:
                flags.append(f)
    amber += ["document check: " + f for f in flags]
    items = [dict(i, status="CONFIRM", A=i["value"], B=i["value"], source="joined text") for i in extract_items(transcription_lines("TRANSCRIPTION\n" + source))]
    # A value that the readings of a PAGE disagree on is not confirmed because the two translations of the joined text agree: the translations are made from one
    # reading, so their agreement says nothing about the page (10ak: a date under a stamp showed as confirmed in the document list while the page list had a disagreement).
    page_dis = []
    for it in (page_items or []):
        if it.get("status") != "DISAGREE" or not (it.get("A") and it.get("B")):
            continue
        fa, fb = _flat(it["A"]), _flat(it["B"])
        hit = [i for i in items if i["type"] == it["type"] and _flat(i["value"]) in (fa, fb)]
        for i in hit:
            i.update(status="DISAGREE", A=it["A"], B=it["B"], source="page %s readings" % it.get("page", "?"), page=it.get("page"), third_view=it.get("third_view"))
        if not hit:
            items.append({"status": "DISAGREE", "type": it["type"], "value": it["A"], "A": it["A"], "B": it["B"], "line": None, "source": "page %s readings" % it.get("page", "?"), "page": it.get("page"), "third_view": it.get("third_view")})
        page_dis.append({"page": it.get("page"), "type": it["type"], "A": it["A"], "B": it["B"], "third_view": it.get("third_view")})
    if page_dis:
        amber.append("%d value(s) that the readings of a page disagree on stay unconfirmed here, even where the two translations agree: %s" % (
            len(page_dis), "; ".join("%s %s against %s (page %s%s)" % (d["type"], d["A"], d["B"], d["page"], ", third view: " + d["third_view"] if d.get("third_view") else "") for d in page_dis[:4])))
    if page_corrections:
        kinds = {(c["kind"], _flat(c["text"])) for c in page_corrections if c["kind"] in CORRECTION_KINDS}
        if kinds:
            amber.append("%d correction(s) marked on the pages (crossed-out or inserted words, stamps over writing): check that the translation shows each one" % len(kinds))
    light = "red" if red else "amber" if amber else "green"
    return {"page_type": "document", "light": light, "reasons_red": red, "reasons_amber": amber, "english_wobble": wob, "name_differences": names,
            "number_differences": nums, "reference_counts_differ": ref_diff, "reference_flags": rflags, "designation_flags": dflags, "glossary_notes": gl.get("glossary_notes", []), "references": {"%s %s" % k: r1[k] for k in sorted(r1)},
            "model_marks": marks, "redundancy_flags": flags, "must_check": items, "page_joins": joins or [], "page_disagreements": page_dis, "corrections": page_corrections or [],
            "person_task": {"green": "Read the whole translation against the original, then tick the must-check list (%d item(s))." % len(items),
                            "amber": "Read the whole translation against the original. Look first at the flags above: every name, every clause / rule / section number, every changed sentence. %d must-check item(s)." % len(items),
                            "red": "The translation failed or is incomplete: do not use it."}[light],
            "stamp": "Machine draft. Not a certified translation."}


def _cli_page(argv):
    ap = argparse.ArgumentParser(prog="checker.py --page")
    ap.add_argument("--page", choices=PAGE_TYPES, required=True)
    ap.add_argument("--a", required=True, help="view 1: the image as given (harness output file)")
    ap.add_argument("--b", required=True, help="view 2: the padded copy (harness output file)")
    ap.add_argument("--c", help="view 3: ultra-high detail (optional)")
    ap.add_argument("--finish-a", dest="finish_a"); ap.add_argument("--finish-b", dest="finish_b"); ap.add_argument("--finish-c", dest="finish_c")
    ap.add_argument("--known", help="JSON list of names a reviewer has confirmed (case data: keep outside the repository)")
    ns = ap.parse_args(argv)
    rd = lambda p: open(p, encoding="utf8").read() if p else None
    known = json.loads(rd(ns.known)) if ns.known else None
    print(json.dumps(check_page(ns.page, rd(ns.a), rd(ns.b), rd(ns.c), ns.finish_a, ns.finish_b, ns.finish_c, known), ensure_ascii=False, indent=1))


def selftest():
    A = "TRANSCRIPTION\n[COLUMN 1]\n1. Order dated 15-02-2020 under Section 302 of the code.\n2. Land 2 বিঘা 0 কঠা 0 held by Shri Ramesh Kumar.\n3. Amount ₹20,000/- paid; phone 98599-79979.\n4. Closing line present.\nTRANSLATION\nignored"
    B = "TRANSCRIPTION\n1. Order dated 15-02-2020 under Section 302 of the code.\n2. Land 2 বিঘা 0 কথা 0 held by Shri Ramesh Kumar.\n3. Amount ₹20,000/- paid; phone 98659-79979.\nTRANSLATION\nignored"
    r = compare(A, B)
    dis = {(i["type"], i["A"], i["B"]) for i in r["items"] if i["status"] == "DISAGREE"}
    assert ("number", "98599-79979", "98659-79979") in dis, dis                      # near-miss phone digits flagged as ONE disagreement
    assert any(t == "unit" and a == "কঠা" and b is None for t, a, b in dis), dis        # the land unit misread as another word
    conf = {(i["type"], i["A"]) for i in r["items"] if i["status"] == "CONFIRM"}
    assert ("date", "15-02-2020") in conf and ("section", "Section 302") in conf and ("amount", "₹20,000") in conf, conf
    assert any(t == "name" and a == "Ramesh Kumar" for t, a in conf), conf              # agreement still goes on the list to confirm
    assert r["summary"]["lines_A"] == 4 and r["summary"]["lines_B"] == 3 and any(d["B"] is None for d in r["line_diffs"])   # the dropped last line
    assert norm("২০২৫ ৰ") == norm("2025 র"), "Assamese digits and ra must match their ASCII and Bengali forms"
    # a full stop after an abbreviation or an initial does not end a sentence
    assert english_sentences("TRANSLATION\nIn Maru Ram vs. Union of India [1981 (1) S.C.C. 106], it was held. Bench: S. N. Phukan. Next one.") == [
        "In Maru Ram vs. Union of India [1981 (1) S.C.C. 106], it was held.", "Bench: S. N. Phukan.", "Next one."], english_sentences("TRANSLATION\nIn Maru Ram vs. Union of India [1981 (1) S.C.C. 106], it was held. Bench: S. N. Phukan. Next one.")
    assert english_wobble("TRANSLATION\nSee Maru Ram vs. Union of India. Next one.", "TRANSLATION\nSee Maru Ram vs.\nUnion of India. Next one.") == []
    # names the two English drafts spell differently, although the sentence is nearly the same
    ta = "TRANSLATION\nIn Maru Ram vs Union Government of India [1981 (1) SCC 106] it was held."; tb = "TRANSLATION\nIn Maru Ram vs. Union of India [1981 (1) S.C.C. 106] it was held."
    d = english_term_differences(ta, tb)
    assert d and "union government of india" in d[0]["only_in_view_1"] and "union of india" in d[0]["only_in_view_2"], d
    assert english_term_differences("TRANSLATION\nOn the 20th and 21st of May.", "TRANSLATION\nOn 20 and 21 May.") == [], "ordinals are not different numbers"
    assert extract_items(["a line -000- and 00 and 150"])[0]["value"] == "150", "zero-only numbers are separators"
    assert english_term_differences(ta, ta) == [] and english_term_differences("TRANSLATION\nThe first line is here.", "TRANSLATION\nThe first line is here.") == []
    assert english_term_differences("TRANSLATION\nSection 433A applies.", "TRANSLATION\nSection 433B applies.")[0]["kind"] == "number"
    # page check, invented text: two identical views of a typed page are green; a handwritten page never is
    R = "TRANSCRIPTION\n1. aaaa bbbb cccc dddd eeee ffff gggg hhhh\nTRANSLATION\nThe first line is here. The second line follows."
    assert agreement(R, R)["percent"] == 100.0
    assert check_page("typed", R, R, None, "STOP", "STOP")["light"] == "green"
    assert check_page("handwritten", R, R, None, "STOP", "STOP")["light"] == "amber"
    assert check_page("typed", R, R, None, "MAX_TOKENS", "STOP")["light"] == "red"                                  # a cut-off view
    assert check_page("typed", R, None, None, "STOP", None)["light"] == "red"                                       # no second view
    assert check_page("typed", R, R.replace("cccc", "zzzz"), None, "STOP", "STOP")["light"] == "red"                # 87.5% agreement
    assert len(english_wobble(R, R.replace("The second line follows.", "A different sentence entirely."))) == 1
    assert check_page("typed", R, R.replace("The second line follows.", "A different sentence entirely."), None, "STOP", "STOP")["light"] == "amber"
    bad = R.replace("aaaa", "45/1/90")                                                                              # the same impossible date in both views
    r = check_page("typed", bad, bad, None, "STOP", "STOP")
    assert r["light"] == "amber" and any("impossible date" in x for x in r["reasons_amber"]), r
    assert extract_items(["a note dated ১১।৮।৯৩ here"])[0]["type"] == "date"                                         # Assamese dates with the danda
    # a third view sides with one of two disagreeing readings
    V1 = "TRANSCRIPTION\n1. dated 15/8/92 end\nTRANSLATION\nx."; V2 = V1.replace("15/8/92", "16/8/92"); V3 = V1.replace("15/8/92", "16/8/92")
    r = check_page("typed", V1, V2, V3, "STOP", "STOP", "STOP")
    assert r["needs_third_view"] and r["third_view_on_disagreements"] == [{"type": "date", "view1": "15/8/92", "view2": "16/8/92", "third_view": "view 2"}], r
    assert [i["norm"] for i in extract_items(transcription_lines("TRANSCRIPTION\n1950. March 14. The judgment was delivered")) if i["type"] == "date"] == ["1950-03-14"]
    ks = extract_items(["1940ರ ಆಗಸ್ಟ್ 21ರಂದು ಅಂತಿಮ ಐತೀರ್ಪನ್ನು, 1941ರ ಡಿಸೆಂಬರ್\u200c 22ರಂದು"])             # dates written with a month name are dates
    assert [(i["type"], i["norm"]) for i in ks] == [("date", "1940-08-21"), ("date", "1941-12-22")], ks
    assert not any(i["type"] == "date" for i in extract_items(["ಮೇಲ್ಮನವಿ 1940 ಮೇ"])) and extract_items(["On the 21st August, 1940, a decree"])[0]["norm"] == "1940-08-21"
    K1 = "TRANSCRIPTION\n1940ರ ಆಗಸ್ಟ್ 21ರಂದು ಐತೀರ್ಪು\nTRANSLATION\nx."; K2 = K1.replace("21ರಂದು", "27ರಂದು")
    assert [(i["status"], i["type"]) for i in compare(K1, K2)["items"]] == [("DISAGREE", "date")]
    assert check_page("typed", K1, K1, K2, "STOP", "STOP", "STOP")["third_view_contradicts"][0]["third_view"].endswith("27")
    # the 50-number page (10y): the writer numbered one line 88 instead of 48; views 1 and 2 silently wrote 48, view 3 wrote 88 as printed
    L = "TRANSCRIPTION\n১. a\n২. b\n৩. c\n৪. d\nTRANSLATION\nx."
    r = check_page("typed", L, L, L.replace("৪.", "৮৮."), "STOP", "STOP", "STOP")
    assert any("third view only" in x and "skips from 3 to 88" in x for x in r["reasons_amber"]) and r["light"] == "amber", r
    assert check_page("typed", L, L, L, "STOP", "STOP", "STOP")["light"] == "green"
    N1 = "TRANSCRIPTION\n১. khatian no 123/47 end\nTRANSLATION\nx."
    assert check_page("typed", N1, N1, N1.replace("123/47", "123/87"), "STOP", "STOP", "STOP")["third_view_contradicts"][0]["type"] == "number"       # not only dates and amounts
    # the first fresh document (10w): both views read a year wrongly, only the third view read it right
    Y1 = "TRANSCRIPTION\n1. meeting held on 18-08-2023 and order no. 154549/239\nTRANSLATION\nThe meeting was held on 18-08-2023."; Y3 = Y1.replace("2023", "2026")
    r = check_page("typed", Y1, Y1, None, "STOP", "STOP")
    assert r["needs_third_view"] and "date or an amount" in r["third_view_reason"], r                      # a page with a date always gets a third look
    r = check_page("typed", Y1, Y1, Y3, "STOP", "STOP", "STOP")
    assert r["third_view_contradicts"] == [{"type": "date", "views_1_and_2": "18-08-2023", "third_view": "18-08-2026"}] and any("third view" in x and "18-08-2026" in x for x in r["reasons_amber"]), r
    assert check_page("typed", Y1, Y1, Y1, "STOP", "STOP", "STOP")["third_view_contradicts"] == []
    assert not check_page("typed", R, R, None, "STOP", "STOP")["needs_third_view"]                           # no date or amount, views agree: no third look
    # a PDF page whose own text is used
    E1 = "TRANSLATION\nThe first line is here. The second line follows."
    t = check_text_page("order dated 15-02-2020 here", E1, E1)
    assert t["light"] == "green" and any(i["type"] == "date" for i in t["must_check"]), t
    assert check_text_page("order here", E1, E1.replace("second line follows.", "other thing entirely."))["light"] == "amber"
    assert check_text_page("order here", E1, "")["light"] == "red"
    assert english_sentences("TRANSLATION\nAll Addl. Chief Secretaries to the Govt. of Assam, Dispur. The Hon'ble Dept. of Health. P.S. to All Ministers.") == [
        "All Addl. Chief Secretaries to the Govt. of Assam, Dispur.", "The Hon'ble Dept. of Health.", "P.S. to All Ministers."]          # Indian-English abbreviations do not end a sentence
    # a whole document translated twice from its joined text
    D1 = "TRANSLATION\nShri Ramesh Kumar [original] came on 15-02-2020. The Order IX, rule 9 application failed. The words \"where there has been an appeal\" in clause 3 are read with the column. It falls under clause 2 because the words \"where there has been an appeal\" are wide."
    D2 = D1.replace("Ramesh Kumar", "Ramesh Kumer")
    d = check_document("order dated 15-02-2020 here", D1, D1)
    assert d["light"] == "amber" and any("tied to clause 3" in f for f in d["reference_flags"]) and d["references"]["clause 2"] == 1, d
    d = check_document("order here", D1, D2)
    assert any("name(s) or title(s) that only one translation has" in r for r in d["reasons_amber"]) and d["name_differences"]["only_in_view_1"] == ["shri ramesh kumar"], d
    clean = "TRANSLATION\nThe appeal is dismissed. The costs follow the event."
    assert check_document("order here", clean, clean)["light"] == "green"
    dd = check_document("order here", "TRANSLATION\nAll Co-District Commissioners, Assam are asked to attend now.", "TRANSLATION\nAll Sub-District Commissioners, Assam are asked to attend now.")
    assert any(r.startswith("designation check:") and "co-district commissioner" in r for r in dd["reasons_amber"]), dd
    assert any("designation:" in f for f in check_text_page("order here", "TRANSLATION\nThe Sub-District Commissioner came.", "TRANSLATION\nThe Sub-District Commissioner came.")["redundancy_flags"])
    pg = check_page("typed", "TRANSCRIPTION\n1. x\nTRANSLATION\nThe Sub-District Commissioner came.", "TRANSCRIPTION\n1. x\nTRANSLATION\nThe Sub-District Commissioner came.", None, "STOP", "STOP")
    assert any("designation:" in f for f in pg["redundancy_flags"]) and pg["light"] == "amber", pg
    assert check_document("order here", clean, clean + " (?)")["light"] == "amber"
    assert check_document("order here", clean, "")["light"] == "red" and check_document("order here", clean, clean, finish2="MAX_TOKENS")["light"] == "red"
    assert check_document("order here", clean * 3, clean)["light"] == "red"                       # one translation much shorter
    # 10ak: corrections marked by the reader, and page disagreements carried into the document view
    M1 = "TRANSCRIPTION\nwitness\nThe ~~victim~~ ^witness^ is escorted\n[stamp over text] 4/25\nTRANSLATION\nThe ~~victim~~ ^witness^ is escorted. Sometimes <doubtful: written 'when', likely meant 'sometimes'> he came."
    cmk = correction_marks(M1)
    assert [(m["kind"], m["text"], m["where"]) for m in cmk if m["where"] == "original"] == [("struck out", "victim", "original"), ("inserted above the line", "witness", "original"), ("stamp or seal over text", "", "original")], cmk
    assert any(m["kind"] == "doubtful reading, explained" and m["where"] == "English" and "sometimes" in m["text"] for m in cmk) and correction_marks("") == [] and correction_marks("plain text") == []
    M2 = M1.replace("~~victim~~ ", "")                                                          # one reading drops the crossed-out word with no mark
    mm = merge_marks([("view 1", M1), ("view 2", M2)])
    assert [m["in_all"] for m in mm if m["kind"] == "struck out"] == [False, False] and all(m["in_all"] for m in mm if m["kind"] == "stamp or seal over text"), mm
    P1 = "TRANSCRIPTION\n1. x\nThe ~~victim~~ ^witness^ is escorted\nTRANSLATION\nThe ~~victim~~ ^witness^ is escorted."
    P2 = "TRANSCRIPTION\n1. x\nThe witness is escorted\nTRANSLATION\nThe witness is escorted."
    pgc = check_page("handwritten", P1, P2)
    assert any("correction(s) on the page" in r for r in pgc["reasons_amber"]) and any("only some of the readings" in r for r in pgc["reasons_amber"]) and pgc["corrections"], pgc["reasons_amber"]
    assert not any("correction" in r for r in check_page("typed", "TRANSCRIPTION\n1. x\nTRANSLATION\nA.", "TRANSCRIPTION\n1. x\nTRANSLATION\nA.")["reasons_amber"]), "a page with no marks raises no correction note"
    src = "1. dated ০২/৪/২৫ end\n2. total ২,০০,০০০/- paid"
    en = "TRANSLATION\nDated 02/4/25. Total 2,00,000/- paid."
    dd = check_document(src, en, en, page_items=[{"page": 2, "status": "DISAGREE", "type": "date", "A": "02/4/25", "B": "9/4/25", "third_view": "view 2"}], page_corrections=[{"kind": "struck out", "text": "victim", "where": "original"}])
    assert dd["light"] == "amber" and dd["page_disagreements"] and any(i["status"] == "DISAGREE" and i["type"] == "date" for i in dd["must_check"]), dd["must_check"]
    assert any("stay unconfirmed" in r for r in dd["reasons_amber"]) and any("correction(s) marked on the pages" in r for r in dd["reasons_amber"])
    assert check_document(src, en, en)["page_disagreements"] == [], "nothing carried over when the pages had no disagreement"
    assert doubtful_marks("TRANSCRIPTION\na [struck: ?] b [unclear] c\nTRANSLATION\nx") == 2
    # 10ak: the same text with a block read in a different place is amber, different text is still red
    B1 = "TRANSCRIPTION\n1. aaaa bbbb cccc dddd eeee\n2. ffff gggg hhhh iiii jjjj\n3. kkkk llll mmmm nnnn oooo\n4. pppp qqqq rrrr ssss tttt\n5. uuuu vvvv wwww xxxx yyyy\n6. zzzz aaab bbbc cccd ddde\nTRANSLATION\nx."
    B2 = "TRANSCRIPTION\n1. aaaa bbbb cccc dddd eeee\n5. uuuu vvvv wwww xxxx yyyy\n6. zzzz aaab bbbc cccd ddde\n2. ffff gggg hhhh iiii jjjj\n3. kkkk llll mmmm nnnn oooo\n4. pppp qqqq rrrr ssss tttt\nTRANSLATION\nx."
    assert agreement(B1, B2)["percent"] < RED_AGREE <= agreement_unordered(B1, B2)["percent"] and check_page("handwritten", B1, B2)["light"] == "amber", check_page("handwritten", B1, B2)["reasons_red"]
    B3 = B1.replace("ffff gggg hhhh iiii jjjj", "qqqq rrrr ssss tttt uuuu").replace("kkkk llll mmmm nnnn oooo", "wwww xxxx yyyy zzzz aaaa").replace("pppp qqqq rrrr ssss tttt", "bbbb cccc dddd eeee ffff")
    assert check_page("handwritten", B1, B3)["light"] == "red", "really different text is still red"
    assert [i["status"] for i in compare("TRANSCRIPTION\n1. dated 09/4/25 end", "TRANSCRIPTION\n1. dated 9/4/25 end")["items"]] == ["CONFIRM"], "a leading zero is not a different date"
    assert [i["status"] for i in compare("TRANSCRIPTION\n1. dated 02/4/25 end", "TRANSCRIPTION\n1. dated 9/4/25 end")["items"]] == ["DISAGREE"]
    assert english_term_differences("TRANSLATION\nDated 09/4/25 here.", "TRANSLATION\nDated 9/4/25 here.") == [] and english_term_differences("TRANSLATION\nDated 02/4/25 here.", "TRANSLATION\nDated 9/4/25 here.")[0]["kind"] == "number"
    # 10al: the sense check: findings are kept only when the quote is in the text; amber, never red
    sn = parse_sense('```json\n[{"quote": "the urgent necessity for has been realized", "problem": "missing object", "severity": "high"}, {"quote": "never said this", "problem": "invented", "severity": "low"}, {"quote": "x", "problem": "short", "severity": "low"}]\n```')
    assert len(sn) == 3 and parse_sense("[]") == [] and parse_sense("no list here") is None and parse_sense("[{bad json") is None
    kept, dropped = match_sense(sn, "In such   circumstances, the urgent necessity for has been realized. Next.")
    assert [k["quote"] for k in kept] == ["the urgent necessity for has been realized"] and dropped == 2, (kept, dropped)
    G = check_page("typed", "TRANSCRIPTION\n1. x\nTRANSLATION\nA b.", "TRANSCRIPTION\n1. x\nTRANSLATION\nA b.")
    assert G["light"] == "green" and apply_sense(dict(G), [], 0)["light"] == "green"
    G2 = apply_sense(dict(G, reasons_amber=list(G["reasons_amber"])), kept, dropped)
    assert G2["light"] == "amber" and G2["sense_flags"] and any("sense check found 1" in r for r in G2["reasons_amber"]) and "Look at every flagged item" in G2["person_task"]
    assert apply_sense({"light": "red", "reasons_amber": [], "must_check": []}, kept)["light"] == "red", "a sense finding never turns red into anything else, and never makes red"
    # 10an: where the readings disagree the English shows both values
    I1 = [{"A": "02/4/25", "B": "9/4/25", "third_view": "view 2"}]
    mk, n, un = mark_disagreements("Dated 02/4/25 and again 02/4/25. Next 102/4/25 is another number.", I1)
    assert n == 1 and un == [] and mk.count("[02/4/25 or 9/4/25 (third look: 9/4/25): check]") == 2 and "Next 102/4/25" in mk, mk
    mk2, n2, un2 = mark_disagreements("Paid on 9/4/25 only.", I1)
    assert n2 == 1 and "[02/4/25 or 9/4/25 (third look: 9/4/25): check]" in mk2, mk2
    mk3, n3, un3 = mark_disagreements("No date here.", I1)
    assert n3 == 0 and un3 == I1 and mk3 == "No date here."
    mk4, n4, _ = mark_disagreements("Amount 2,00,000/- paid.", [{"A": "2,00,000/-", "B": None, "third_view": None}])
    assert "[2,00,000/-: found in one reading only: check]" in mk4 and n4 == 1
    assert mark_disagreements(mk, I1)[1] == 0, "a value already marked is not marked again"
    assert mark_disagreements("x 1/1/90", [{"A": "1/1/90", "B": "1/1/91", "third_view": "neither"}])[0] == "x [1/1/90 or 1/1/91: check]"
    print("selftest OK (invented text only)")


if __name__ == "__main__":
    if "--selftest" in sys.argv: selftest()
    elif "--page" in sys.argv: _cli_page(sys.argv[1:])
    elif len(sys.argv) == 3: print(json.dumps(compare(open(sys.argv[1]).read(), open(sys.argv[2]).read()), ensure_ascii=False, indent=1))
    else: sys.exit(__doc__)
