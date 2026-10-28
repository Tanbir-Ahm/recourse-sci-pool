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
        out.append(re.sub(r"^\d+\.\s+", "", l))
    return out


def extract_items(lines):
    items = []
    for ln, raw in enumerate(lines, 1):
        s = norm(raw); used = []
        def add(kind, m, value=None):
            items.append({"type": kind, "value": (value or m.group(0)).strip(" ,;:.|"), "norm": norm(value or m.group(0)).strip(" ,;:.|").lower(), "line": ln})
            used.append(m.span())
        for m in re.finditer(r"\b\d{1,2}\s*[/\-.।৷]\s*\d{1,2}\s*[/\-.।৷]\s*\d{2,4}\b", s): add("date", m)
        for m in re.finditer(r"(?:₹|Rs\.?|रु(?:पये|\.)?|টকা|ರೂ)\s*[0-9][0-9,.]*|[0-9][0-9,.]*\s*(?:/-|টকা|रुपये|ರೂಪಾಯಿ|rupees)", s, re.I): add("amount", m)
        for m in re.finditer(r"(?:section|sec\.?|धारा|ধাৰা|ধারা|ಕಲಂ)\s*\d+[A-Za-z]?", s, re.I): add("section", m)
        for u in UNITS:
            for m in re.finditer(re.escape(norm(u)), s, re.I): add("unit", m)
        for m in re.finditer(HONOR + r"\s*([^\s,;:()\[\]]+(?:\s+[^\s,;:()\[\]]+)?)", s): add("name", m, m.group(1))
        for m in re.finditer(r"\b(?:[A-Z][a-z]+\.?\s+){1,3}[A-Z][a-z]+\b|\b(?:[A-Z]{2,}\s+){1,3}[A-Z]{2,}\b", s):
            if not re.match(HONOR + r"\b", m.group(0)):        # "Shri Ramesh Kumar" is already caught after its honorific
                add("name", m)
        for m in re.finditer(r"\d+(?:[.,]\d+)*(?:-\d+(?:[.,]\d+)*)*", s):
            if len(re.sub(r"\D", "", m.group(0))) >= 2 and not any(a <= m.start() < b for a, b in used):
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


def english_sentences(text):
    """The English part of a harness output as sentences (the harness uses the LAST TRANSLATION heading)."""
    i = text.rfind("TRANSLATION")
    if i < 0:
        return []
    tail = re.sub(r"\s+", " ", text[i + len("TRANSLATION"):].lstrip("*:# \n-")).strip()
    return [s for s in re.split(r"(?<=[.?!])\s+", tail) if s]


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
    return head.count("[unclear]") + head.count("(?)")


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
        if run3 is not None:
            out["agreement_view3_vs_view1"] = agreement(run3, run1); out["agreement_view3_vs_view2"] = agreement(run3, run2)
            out["third_view_on_disagreements"] = tiebreak(items, run3)
    else:
        out["agreement_view1_vs_view2"] = None
        if not red:
            red.append("fewer than two readings: run the second view")
    if page_type == "handwritten":
        amber.append("handwriting has no independent machine check: a person must look at every date, number and name")
    light = "red" if red else "amber" if amber else "green"
    out["light"] = light
    out["reasons_red"], out["reasons_amber"], out["notes"] = red, amber, notes
    out["needs_third_view"] = light != "green" or any(i["status"] == "DISAGREE" for i in items)
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
    items = [dict(i, status="CONFIRM", source="text layer") for i in extract_items(transcription_lines("TRANSCRIPTION\n" + text))]
    wob = english_wobble(english1, english2) if not red else []
    if wob:
        amber.append("%d English sentence(s) changed between the two drafts" % len(wob))
    flags = redundancy.page_flags("TRANSCRIPTION\n" + text, None, known)
    for e in (english1, english2):
        for w, dg, wd in redundancy.english_amount_check(e.split("TRANSLATION")[-1] if e else ""):
            f = "English amount '%s': digits say %s, words say %s" % (w, dg, wd)
            if f not in flags:
                flags.append(f)
    amber += ["page check: " + f for f in flags]
    light = "red" if red else "amber" if amber else "green"
    return {"page_type": "text_layer", "light": light, "reasons_red": red, "reasons_amber": amber, "english_wobble": wob, "redundancy_flags": flags,
            "must_check": items,
            "person_task": {"green": "The source text is the PDF's own text. Check the English draft against it and tick the must-check list (%d item(s))." % len(items),
                            "amber": "Check the flagged English sentences and items against the source text, then tick the must-check list (%d item(s))." % len(items),
                            "red": "The translation failed: translate this page by hand."}[light],
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
    # a PDF page whose own text is used
    E1 = "TRANSLATION\nThe first line is here. The second line follows."
    t = check_text_page("order dated 15-02-2020 here", E1, E1)
    assert t["light"] == "green" and any(i["type"] == "date" for i in t["must_check"]), t
    assert check_text_page("order here", E1, E1.replace("second line follows.", "other thing entirely."))["light"] == "amber"
    assert check_text_page("order here", E1, "")["light"] == "red"
    print("selftest OK (invented text only)")


if __name__ == "__main__":
    if "--selftest" in sys.argv: selftest()
    elif "--page" in sys.argv: _cli_page(sys.argv[1:])
    elif len(sys.argv) == 3: print(json.dumps(compare(open(sys.argv[1]).read(), open(sys.argv[2]).read()), ensure_ascii=False, indent=1))
    else: sys.exit(__doc__)
