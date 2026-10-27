"""Compare readings of the same page and build the list a person must confirm.

  python checker.py A_reading.txt B_reading.txt > checks.json              (two readings: items and line differences)
  python checker.py --page typed --a run1.txt --b run2.txt \\
         [--vision vision.txt --vision-stats vision_stats.json] [--finish-a STOP --finish-b STOP] > page_check.json
                                                                           (the whole page check: traffic light, section 11 of the plan)
  python checker.py --selftest

Each reading is a harness output (TRANSCRIPTION then TRANSLATION). The transcription is compared letter by letter;
the English is compared only between the two argon runs, sentence by sentence.
Two kinds of item are produced:
  DISAGREE      the two readers differ (a number, a date, a name, a unit, or a whole line): look at the page.
  CONFIRM       the readers agree, but it is a date, amount, number, unit, section number or name: still confirm it.
                Agreement is not correctness; three readers once agreed on a wrong age.
The tool never marks anything as correct. A person closes every item. Green means "spot-check", never "right".

Languages: the structure does not depend on the language, but the thresholds were taken from Assamese pages only, and the
patterns for units, honorifics and names were written for Assamese/Bengali script, Devanagari (Hindi, Marathi) and Kannada.
Digits are folded for nine Indian scripts. Units and honorifics for Telugu, Tamil, Malayalam and Gujarati are UNVERIFIED
additions (not checked by a reader of those languages). Kannada and Hindi pages have not been run through this file.
No case data belongs in this folder; the selftest uses invented text.
"""
import argparse, difflib, json, re, sys, unicodedata

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
        for m in re.finditer(r"\b\d{1,2}\s*[/\-.]\s*\d{1,2}\s*[/\-.]\s*\d{2,4}\b", s): add("date", m)
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
# These numbers are a FIRST GUESS taken from three Assamese comparisons (argon against Cloud Vision on the clean half, the
# scanned half and the whole page of one dictionary page: 97.9, 87.7 and 91.0 percent). Tune them on the 30-page test.
GREEN_AGREE = 97.0       # letter agreement needed for green
RED_AGREE = 90.0         # below this the page is red
VISION_MIN_CONF = 80.0   # Cloud Vision mean word confidence (percent) under which the page is red
DROP_RATIO = 0.85        # a reading with less than this share of the other's letters has probably dropped text
ENGLISH_WOBBLE = 0.85    # an English sentence more different than this between the two runs is flagged
PAGE_TYPES = ("typed", "scan", "handwritten")


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


def check_page(page_type, run1, run2, vision=None, vision_stats=None, finish1=None, finish2=None):
    """The traffic light for one page. page_type: typed, scan (a typed or printed page that is a poor scan) or handwritten.
    run1, run2: two argon readings (harness output). vision: Cloud Vision's text, vision_stats: its stats dict with mean_conf.
    Returns a dict; 'light' is green, amber or red. It never says a page is correct."""
    if page_type not in PAGE_TYPES:
        raise ValueError("page_type must be one of %s" % (PAGE_TYPES,))
    red, amber, notes = [], [], []
    out = {"page_type": page_type, "thresholds": {"green_agree": GREEN_AGREE, "red_agree": RED_AGREE, "vision_min_conf": VISION_MIN_CONF,
                                                  "drop_ratio": DROP_RATIO, "english_wobble": ENGLISH_WOBBLE,
                                                  "status": "first guess, tune on the 30-page test"}}

    for name, text, fin in (("argon run 1", run1, finish1), ("argon run 2", run2, finish2)):
        p = reading_problem(text, fin)
        if p:
            red.append("%s: %s" % (name, p))
    have_both = bool(run1 and run1.strip() and run2 and run2.strip())

    items = []
    if have_both:
        agr = agreement(run1, run2)
        out["agreement_run1_vs_run2"] = agr
        if agr["percent"] < RED_AGREE:
            red.append("the two argon runs agree on only %.1f%% of letters (red below %.0f%%)" % (agr["percent"], RED_AGREE))
        elif agr["percent"] < GREEN_AGREE:
            amber.append("the two argon runs agree on %.1f%% of letters (green needs %.0f%% or more)" % (agr["percent"], GREEN_AGREE))
        if agr.get("share", 1) < DROP_RATIO:
            red.append("one argon run has much less text than the other (%.0f%% of the letters): possible dropped text" % (100 * agr["share"]))
        c12 = compare(run1, run2)
        out["line_differences_run1_vs_run2"] = c12["line_diffs"]
        d = c12["summary"]["disagreements"]
        if d:
            amber.append("%d must-check item(s) differ between the two argon runs" % d)
        items += [dict(i, source="argon run 1 vs run 2") for i in c12["items"]]
        wob = english_wobble(run1, run2)
        out["english_wobble"] = wob
        if wob:
            amber.append("%d English sentence(s) changed between the two runs" % len(wob))
        marks = doubtful_marks(run1) + doubtful_marks(run2)
        if marks:
            amber.append("the reader marked %d doubtful word(s) as [unclear] or (?)" % marks)
    else:
        out["agreement_run1_vs_run2"] = None
        if not red:
            red.append("fewer than two readings: run the second argon reading")

    vis_ok = bool(vision and vision.strip())
    conf = (vision_stats or {}).get("mean_conf")
    if page_type == "handwritten":
        amber.append("handwriting has no independent machine check: a person must look at every date, number and name")
        if vis_ok:
            out["cloud_vision"] = {"use": "warning only", "mean_conf": conf}
            if conf is not None and conf < VISION_MIN_CONF:
                notes.append("Cloud Vision is unsure of this handwriting (mean confidence %.1f%%); this does not change the colour" % conf)
    elif vis_ok and run1 and run1.strip():
        av = agreement(run1, vision)
        out["agreement_argon_vs_vision"] = av
        out["cloud_vision"] = {"use": "second reader", "mean_conf": conf}
        if av["percent"] < RED_AGREE:
            red.append("argon and Cloud Vision agree on only %.1f%% of letters (red below %.0f%%)" % (av["percent"], RED_AGREE))
        elif av["percent"] < GREEN_AGREE:
            amber.append("argon and Cloud Vision agree on %.1f%% of letters (green needs %.0f%% or more)" % (av["percent"], GREEN_AGREE))
        if av.get("share", 1) < DROP_RATIO:
            red.append("argon and Cloud Vision differ a lot in how much text they found (%.0f%% of the letters): possible dropped text" % (100 * av["share"]))
        if conf is not None and conf < VISION_MIN_CONF:
            red.append("Cloud Vision is unsure of this page (mean confidence %.1f%%, red below %.0f%%): likely a poor scan" % (conf, VISION_MIN_CONF))
        cv = compare(run1, vision)
        dv = cv["summary"]["disagreements"]
        if dv:
            amber.append("%d must-check item(s) differ between argon and Cloud Vision" % dv)
        items += [dict(i, source="argon run 1 vs Cloud Vision") for i in cv["items"] if i["status"] == "DISAGREE"]
    else:
        amber.append("no independent second reader was available for this page")

    light = "red" if red else "amber" if amber else "green"
    out["light"] = light
    out["reasons_red"], out["reasons_amber"], out["notes"] = red, amber, notes
    n_check = sum(1 for i in items if i["status"] == "CONFIRM") + sum(1 for i in items if i["status"] == "DISAGREE")
    out["person_task"] = {
        "green": "Tick the must-check list (%d item(s)) against the page image. Nothing was flagged. Green means spot-check, not correct." % n_check,
        "amber": "Look at every flagged item and line against the page image, then tick the must-check list (%d item(s))." % n_check,
        "red": "Read the whole page. Use the machine English only as a help, and do not rely on it.",
    }[light]
    out["must_check"] = items
    out["stamp"] = "Machine draft. Not a certified translation."
    return out


def _cli_page(argv):
    ap = argparse.ArgumentParser(prog="checker.py --page")
    ap.add_argument("--page", choices=PAGE_TYPES, required=True)
    ap.add_argument("--a", required=True, help="argon run 1 (harness output file)")
    ap.add_argument("--b", required=True, help="argon run 2 (harness output file)")
    ap.add_argument("--vision", help="Cloud Vision text file (typed and scan pages)")
    ap.add_argument("--vision-stats", dest="vision_stats", help="JSON with mean_conf for the Cloud Vision reading")
    ap.add_argument("--finish-a", dest="finish_a")
    ap.add_argument("--finish-b", dest="finish_b")
    ns = ap.parse_args(argv)
    rd = lambda p: open(p, encoding="utf8").read() if p else None
    stats = json.loads(rd(ns.vision_stats)) if ns.vision_stats else None
    print(json.dumps(check_page(ns.page, rd(ns.a), rd(ns.b), rd(ns.vision), stats, ns.finish_a, ns.finish_b), ensure_ascii=False, indent=1))


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
    # page check, invented text: identical runs and a matching Vision text on a typed page are green; a handwritten page never is
    R = "TRANSCRIPTION\n1. aaaa bbbb cccc dddd eeee ffff gggg hhhh\nTRANSLATION\nThe first line is here. The second line follows."
    V = "aaaa bbbb cccc dddd eeee ffff gggg hhhh"
    assert agreement(R, R)["percent"] == 100.0
    assert check_page("typed", R, R, V, {"mean_conf": 95.0}, "STOP", "STOP")["light"] == "green"
    assert check_page("handwritten", R, R, None, None, "STOP", "STOP")["light"] == "amber"
    assert check_page("typed", R, R, V, {"mean_conf": 95.0}, "MAX_TOKENS", "STOP")["light"] == "red"               # a cut-off run
    assert check_page("typed", R, R, V, {"mean_conf": 60.0}, "STOP", "STOP")["light"] == "red"                    # Vision unsure of the scan
    assert check_page("typed", R, R.replace("cccc", "zzzz"), V, {"mean_conf": 95.0}, "STOP", "STOP")["light"] == "red"   # 87.5% agreement
    assert len(english_wobble(R, R.replace("The second line follows.", "A different sentence entirely."))) == 1
    assert check_page("typed", R, R, None, None, "STOP", "STOP")["light"] == "amber"                              # no second reader
    print("selftest OK (invented text only)")


if __name__ == "__main__":
    if "--selftest" in sys.argv: selftest()
    elif "--page" in sys.argv: _cli_page(sys.argv[1:])
    elif len(sys.argv) == 3: print(json.dumps(compare(open(sys.argv[1]).read(), open(sys.argv[2]).read()), ensure_ascii=False, indent=1))
    else: sys.exit(__doc__)
