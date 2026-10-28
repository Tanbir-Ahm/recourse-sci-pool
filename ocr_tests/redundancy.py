"""Checks that use a page's own redundancy, with no model: things that must hold on any honest page, so a reading that breaks them is wrong somewhere.

  python redundancy.py --selftest

Built here (all work on text a reader produced; none of them says anything is correct, they only flag):
  impossible_dates      a day over 31, a month over 12, 31 April, 30 February, a four-digit year outside 1800 to 2100
  numbering_gaps        a numbered list that skips a number or goes backwards: (1) (2) (4)
  english_amount_check  an amount written in digits AND words in the English draft that do not agree: Rs 750.00 (seven hundred)
  name_variants         the same name spelled two ways across the pages of a bundle (near-misses, not exact matches)
  known_name_flags      a name close to, but not the same as, a name a reviewer already confirmed: "did you mean ...?"  Never auto-corrects.
NOT built: amounts in words against digits in the ORIGINAL script (needs a reliable Assamese number-word parser, which has not been written
or checked by a reader of the language), weekday against date, and section numbers against a statute list.
The known-names list is case data: keep it outside the repository. The selftest uses invented text.
"""
import csv, difflib, json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checker

_DATE = re.compile(r"(?<!\d)(\d{1,2})\s*[/\-.।৷|]\s*(\d{1,2})\s*[/\-.।৷|]\s*(\d{2,4})(?!\d)")


def impossible_dates(text):
    """Dates in a reading that cannot exist. Returns a list of (date as written, why)."""
    out = []
    for m in _DATE.finditer(checker.norm(text)):
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        why = None
        if not 1 <= mo <= 12:
            why = "month %d" % mo
        elif not 1 <= d <= 31:
            why = "day %d" % d
        elif d == 31 and mo in (4, 6, 9, 11):
            why = "31 in a 30-day month"
        elif mo == 2 and d > 29:
            why = "%d February" % d
        elif len(y) == 4 and not 1800 <= int(y) <= 2100:
            why = "year %s" % y
        elif len(y) == 3:
            why = "three-digit year %s" % y
        if why:
            out.append((m.group(0), why))
    return out


def numbering_gaps(text):
    """A numbered list that skips or goes backwards. Several lines with the same number in a row (sub-items) are fine."""
    nums = []
    for l in checker.transcription_lines(text):
        m = re.match(r"^\(?\s*(\d{1,2})\s*[)।৷.]", checker.norm(l))
        if m:
            nums.append(int(m.group(1)))
    out = []
    for a, b in zip(nums, nums[1:]):
        if b == a:
            continue
        if b < a:
            out.append("goes back from %d to %d" % (a, b))
        elif b > a + 1:
            out.append("skips from %d to %d" % (a, b))
    return out


_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * i for i, w in enumerate("x x twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "x"}
_SCALE = {"hundred": 100, "thousand": 1000, "lakh": 100000, "lakhs": 100000, "crore": 10000000, "crores": 10000000}


def words_to_int(s):
    """English number words to an integer ('seven hundred fifty' is 750; 'thirty thousand' is 30000), or None if any word is not understood."""
    toks = [t for t in re.split(r"[\s,\-]+", s.lower().strip()) if t and t not in ("and", "only", "rupees", "rupee", "rs", "inr")]
    if not toks:
        return None
    total, cur = 0, 0
    for t in toks:
        if t in _UNITS:
            cur += _UNITS[t]
        elif t in _TENS:
            cur += _TENS[t]
        elif t == "hundred":
            cur = max(cur, 1) * 100
        elif t in _SCALE:
            total += max(cur, 1) * _SCALE[t]; cur = 0
        else:
            return None
    return total + cur


_AMOUNT = re.compile(r"(?:₹|Rs\.?|INR)?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:/-)?\s*\(\s*([A-Za-z][A-Za-z\- ,]*?)\s*\)\s*(thousand|hundred|lakhs?|crores?)?", re.I)


def english_amount_check(english):
    """In an English draft, an amount given in digits and in words that disagree. Returns a list of (what was written, digits, words)."""
    out = []
    for m in _AMOUNT.finditer(english):
        digits = float(m.group(1).replace(",", ""))
        words = words_to_int(m.group(2) + (" " + m.group(3) if m.group(3) else ""))
        if words is not None and abs(digits - words) > 0.5:
            out.append((m.group(0).strip(), int(digits) if digits == int(digits) else digits, words))
    return out


def name_variants(pages, low=0.80):
    """pages: {page id: reading text}. Names (as the checker finds them) that look like the same name spelled two ways. Returns tuples
    (name 1, page 1, name 2, page 2, similarity). Different people with close names also appear: it is a list to look at, not a verdict."""
    seen = {}
    for pid, text in pages.items():
        for it in checker.extract_items(checker.transcription_lines(text)):
            if it["type"] == "name" and len(it["norm"]) >= 4:
                seen.setdefault(it["norm"], (it["value"], pid))
    names = sorted(seen)
    out = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            r = difflib.SequenceMatcher(None, a, b).ratio()
            if low <= r < 1.0:
                out.append((seen[a][0], seen[a][1], seen[b][0], seen[b][1], round(r, 2)))
    return out


def known_name_flags(text, known, low=0.75):
    """Names in a reading that are close to, but not the same as, a confirmed name. known: list of confirmed names. Returns (as read, close to)."""
    kn = {checker.norm(k).lower(): k for k in known}
    out = []
    for it in checker.extract_items(checker.transcription_lines(text)):
        if it["type"] != "name" or it["norm"] in kn or len(it["norm"]) < 4:
            continue
        best = max(kn, key=lambda k: difflib.SequenceMatcher(None, it["norm"], k).ratio(), default=None)
        if best and low <= difflib.SequenceMatcher(None, it["norm"], best).ratio() < 1.0:
            out.append((it["value"], kn[best]))
    return out


def known_names_from_csv(paths):
    """Names a reviewer typed in 'Value on the page' on marking sheets (the Check list part of the downloaded CSV), as a sorted list."""
    names = set()
    for p in paths:
        for row in csv.reader(open(p, encoding="utf8")):
            if len(row) >= 8 and row[0] == "" and row[2] == "name" and row[6].strip():
                names.add(row[6].strip())
    return sorted(names)


def page_flags(reading, english=None, known=None):
    """All the checks for one reading, as a list of plain-words flags."""
    flags = []
    for d, why in impossible_dates(reading):
        flags.append("impossible date '%s' (%s)" % (d, why))
    for g in numbering_gaps(reading):
        flags.append("numbered list %s" % g)
    if english:
        for w, dg, wd in english_amount_check(english):
            flags.append("English amount '%s': digits say %s, words say %s" % (w, dg, wd))
    if known:
        for a, b in known_name_flags(reading, known):
            flags.append("name '%s' is close to the confirmed name '%s'" % (a, b))
    return flags


def selftest():
    assert impossible_dates("TRANSCRIPTION\n1. dated 15-02-2020 and 31/4/93 and 1/8/92 and 45/1/90 and 3/13/91 and 30/2/90") == [
        ("31/4/93", "31 in a 30-day month"), ("45/1/90", "day 45"), ("3/13/91", "month 13"), ("30/2/90", "30 February")], impossible_dates("31/4/93 45/1/90 3/13/91 30/2/90")
    assert impossible_dates("১১।৮।৯৩ and ৯৷৮৷৯৩") == []                                  # Assamese dates with the danda are read
    assert impossible_dates("১১।১৫।৯৩") == [("11।15।93", "month 15")]
    assert numbering_gaps("TRANSCRIPTION\n(১) a\n(২) b\n(৩) c") == []
    assert numbering_gaps("TRANSCRIPTION\n(1) a\n(2) b\n(4) c") == ["skips from 2 to 4"]
    assert numbering_gaps("TRANSCRIPTION\n(5) a\n(5) sub\n(6) c\n(3) d") == ["goes back from 6 to 3"]
    assert [words_to_int(x) for x in ("seven hundred fifty", "five hundred", "one hundred", "thirty thousand", "twenty-five thousand six hundred", "one lakh", "twelve")] == [750, 500, 100, 30000, 25600, 100000, 12]
    assert words_to_int("seven hundred banana") is None and words_to_int("") is None
    assert english_amount_check("pension from Rs. 500.00 (Five hundred) to Rs. 750.00 (Seven hundred fifty).") == []
    assert english_amount_check("an amount of Rs. 750.00 (Seven hundred) was paid") == [("Rs. 750.00 (Seven hundred)", 750, 700)]
    assert english_amount_check("one-time assistance of Rs. 30,000 (thirty) thousand") == []        # the digits followed by '(thirty) thousand'
    assert english_amount_check("Rs. 30,000 (unknownword)") == []                                      # not understood: no flag
    p = {"A": "TRANSCRIPTION\n1. Shri Ramesh Kumar was present.", "B": "TRANSCRIPTION\n1. Shri Ramesh Kumer was present and Shri Dinesh Mardi."}
    nv = name_variants(p)
    assert any({a, c} == {"Ramesh Kumar", "Ramesh Kumer"} for a, _, c, _, _ in nv), nv
    assert known_name_flags("TRANSCRIPTION\n1. Shri Ramesh Kumer came.", ["Ramesh Kumar"]) == [("Ramesh Kumer", "Ramesh Kumar")]
    assert known_name_flags("TRANSCRIPTION\n1. Shri Ramesh Kumar came.", ["Ramesh Kumar"]) == []
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "m.csv")
        open(f, "w", encoding="utf8").write('"Page","Tool"\n\n"Check list","Status","Type","Reader A","Reader B","Line A/B","Value on the page","Result"\n"","DISAGREE","name","X","Y","1 / 1","Ramesh Kumar","A wrong"\n"","CONFIRM","number","15","15","1 / 1","15","right in both"\n')
        assert known_names_from_csv([f]) == ["Ramesh Kumar"]
    fl = page_flags("TRANSCRIPTION\n(1) a 45/1/90\n(3) b", "Rs. 750.00 (Seven hundred)")
    assert len(fl) == 3, fl
    print("selftest OK (invented text only)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        sys.exit(__doc__)
