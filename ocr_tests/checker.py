"""Compare two readings of the same page and build the list a person must confirm.

  python checker.py A_reading.txt B_reading.txt > checks.json
  python checker.py --selftest

Each input is a harness output (TRANSCRIPTION then TRANSLATION). Only the transcription is compared here.
Two kinds of item are produced:
  DISAGREE      the two readers differ (a number, a date, a name, a unit, or a whole line): look at the page.
  CONFIRM       the readers agree, but it is a date, amount, number, unit, section number or name: still confirm it.
                Agreement is not correctness; three readers once agreed on a wrong age.
The tool never marks anything as correct. A person closes every item.
No case data belongs in this folder; the selftest uses invented text.
"""
import difflib, json, re, sys, unicodedata

_DIGITS = {}
for base in (0x09E6, 0x0966, 0x0CE6):            # Assamese/Bengali, Devanagari, Kannada digits
    for i in range(10):
        _DIGITS[base + i] = ord("0") + i
UNITS = ["বিঘা", "কঠা", "লেছা", "লেচা", "बीघा", "बिस्वा", "ಎಕರೆ", "ಗುಂಟೆ", "bigha", "katha", "lessa", "acre", "guntha"]
HONOR = r"(?:শ্ৰীমতী|শ্ৰী|শ্রী|ড°|ডঃ|श्रीमती|श्री|ಶ್ರೀಮತಿ|ಶ್ರೀ|Smt\.?|Sri|Shri|Mr\.?|Mrs\.?|Dr\.?)"


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
    print("selftest OK (invented text only)")


if __name__ == "__main__":
    if "--selftest" in sys.argv: selftest()
    elif len(sys.argv) == 3: print(json.dumps(compare(open(sys.argv[1]).read(), open(sys.argv[2]).read()), ensure_ascii=False, indent=1))
    else: sys.exit(__doc__)
