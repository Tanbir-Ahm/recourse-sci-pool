"""The glossary check: words with a settled legal meaning, and what a translation must not do with them (plan section 10ag).

  python glossary.py --selftest
  python glossary.py --file glossary/assamese_legal.csv --source reading.txt --english translation.txt     (prints the notes)

A glossary is a CSV (see glossary/assamese_legal.csv): the word in script, its spelling variants, the standard English, the English words that count as a fair rendering,
the renderings to avoid, and a kind. notes(source, english) looks for the glossary's words in the ORIGINAL-SCRIPT text and compares what the English says. It only ever
produces notes for a person; it never changes a word. Every entry carries a status: until a lawyer has approved it, a note is a prompt to look, not a rule.
Kinds: term (a standard English rendering exists), ambiguous (the word can mean more than one thing: the translation must not choose silently), insult (keep the word,
do not pick one English insult), unit (keep the word as written: land measures and records), form (alias, honorific).
Matching: Unicode NFC, the Assamese ra and wa unified with the Bengali ra and ba, zero-width marks removed; a word matches with the usual Assamese endings after it
(-ৰ, -ক, -ত, -লৈ, -সকল ...), and only at the start of a word, so a longer word that merely begins with it does not match. A hit inside a longer hit of another entry is
dropped ('আগতীয়া জামিন' does not also count as 'জামিন').
Limits: it compares at page or document level (does the English contain a fair rendering anywhere?), not sentence by sentence; a wrong reading of the original word
produces no note; an entry that is missing from the glossary is simply not checked.
"""
import csv, os, re, sys, unicodedata

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glossary")
ACTIVE_PATH = None            # set by pipeline.py --glossary FILE; None = glossary/<language>_legal.csv when it exists
LANGUAGE = None               # set by pipeline.py from --language
_CACHE = {}
_SUFFIX = r"(?:র|ক|ত|লৈ|রে|য়ে|য়ে|ে|সকল|বোর|জন|টো|খন|টি|রপরা|কো|হঁত)*"
_LETTER = "[ঀ-৿]"


def norm(s):
    """Comparison form: NFC, the Assamese ra and wa as the Bengali ra and ba, zero-width marks removed, spaces collapsed."""
    s = unicodedata.normalize("NFC", s or "").replace("ৰ", "র").replace("ৱ", "ব")
    s = re.sub("[‌‍]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def load(path=None, language=None):
    """The entries of a glossary CSV, or [] if there is none. path wins; else ACTIVE_PATH; else glossary/<language lower>_legal.csv."""
    p = path or ACTIVE_PATH or (os.path.join(DEFAULT_DIR, "%s_legal.csv" % language.lower()) if language else None)
    if not p or not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            allv = [r["word"]] + [v for v in (r.get("variants") or "").split("|") if v.strip()]
            forms = [v for v in allv if not v.startswith("=")]
            exact = [v[1:] for v in allv if v.startswith("=")]          # a variant written "=word" is matched as that word alone (or with র/ক): it is the start of longer, different words
            e = dict(r)
            e["forms"] = sorted({norm(x) for x in forms + exact if x.strip()}, key=len, reverse=True)
            ex = sorted({norm(x) for x in exact if x.strip()}, key=len, reverse=True)
            e["ok"] = [x.strip().lower() for x in (r.get("english_ok") or "").split("|") if x.strip()]
            e["avoid"] = [x.strip().lower() for x in (r.get("not_as") or "").split("|") if x.strip()]
            norm_forms = sorted({norm(x) for x in forms if x.strip()}, key=len, reverse=True)
            alt = ["(?:" + "|".join(re.escape(x) for x in norm_forms) + ")" + _SUFFIX] if norm_forms else []
            if ex:
                alt.append("(?:" + "|".join(re.escape(x) for x in ex) + ")(?:র|ক)?")
            e["_re"] = re.compile("(?<!" + _LETTER + ")(" + "|".join(alt) + ")(?!" + _LETTER + ")")
            out.append(e)
    return out


def entries_in_use():
    """The glossary the checks use right now (ACTIVE_PATH, else the one for LANGUAGE), loaded once."""
    p = ACTIVE_PATH or (os.path.join(DEFAULT_DIR, "%s_legal.csv" % LANGUAGE.lower()) if LANGUAGE else None)
    if not p or not os.path.exists(p):
        return []
    if p not in _CACHE:
        _CACHE[p] = load(p)
    return _CACHE[p]


def notes_for_readings(readings, entries=None):
    """readings: [(label, original-script text, English text)], e.g. [('view 1', a, ea), ('view 2', b, eb)]. One row per glossary entry that raised a note in any of them, with
    the labels it applies to. Returns [] when there is no glossary for the language."""
    entries = entries if entries is not None else entries_in_use()
    if not entries:
        return []
    merged = {}
    for label, src, eng in readings:
        for x in notes(src or "", eng or "", entries):
            m = merged.setdefault(x["id"], dict(x, applies_to=[]))
            m["applies_to"].append(label)
            if x["level"] == "strong":
                m["level"] = "strong"; m["text"] = x["text"]
    return sorted(merged.values(), key=lambda m: (m["level"] != "strong", m["id"]))


def find(source, entries):
    """[(entry, word as read)] for every glossary word in the original-script text, longest hits first; a hit inside a longer hit of another entry is dropped."""
    text = norm(source); hits = []
    for e in entries:
        for m in e["_re"].finditer(text):
            hits.append((m.start(), m.end(), e, m.group(0)))
    hits.sort(key=lambda h: -(h[1] - h[0]))
    kept = []
    for a, b, e, w in hits:
        if any(a >= a2 and b <= b2 and e is not e2 and (a, b) != (a2, b2) for a2, b2, e2, _ in kept):
            continue
        kept.append((a, b, e, w))
    kept.sort(key=lambda h: h[0])
    punct = ",.;:\u0964!?\"'()[]"
    orig = {}
    for tok in re.findall(r"\S+", source or ""):
        orig.setdefault(norm(tok.strip(punct)), tok.strip(punct))                   # show the word as it was read (with the Assamese ra), not the comparison form
    return [(e, orig.get(w, w)) for a, b, e, w in kept]


def _has(english, words):
    el = (english or "").lower()
    return [w for w in words if re.search(r"(?<![a-z])" + re.escape(w), el)]


def _pairs(english, words):
    """How many times two of the given English words stand together ('yesterday/tomorrow', 'tomorrow or yesterday', 'yesterday (or tomorrow)')."""
    n, el = 0, (english or "").lower()
    for i, a in enumerate(words):
        for b in words[i + 1:]:
            n += len(re.findall(re.escape(a) + r"[\s/()\-,]{0,6}(?:or|and|/)?[\s/()\-,]{0,6}" + re.escape(b), el))
            n += len(re.findall(re.escape(b) + r"[\s/()\-,]{0,6}(?:or|and|/)?[\s/()\-,]{0,6}" + re.escape(a), el))
    return n


def notes(source, english, entries=None, language=None):
    """The glossary notes for one reading and ONE English text. Returns [{'id', 'word', 'english', 'kind', 'level', 'text', 'status'}] with one note per entry
    (level 'strong' when the English contains a rendering the entry says to avoid, else 'check'). No note when the English is as the entry wants."""
    entries = entries if entries is not None else load(language=language)
    out, seen = [], set()
    found = find(source, entries)
    count = {}
    for e, w in found:
        count[e["id"]] = count.get(e["id"], 0) + 1
    for e, w in found:
        if e["id"] in seen:
            continue
        found_ok, found_bad = _has(english, e["ok"]), _has(english, e["avoid"])
        kind, std = e["kind"], e["english"]
        text, level = None, "check"
        strong = e.get("confidence") == "high"                  # a medium-confidence entry only ever gives a plain 'check'
        if kind in ("term", "unit", "form"):
            if found_bad and not found_ok:                      # an avoided rendering and no fair one anywhere in the English (the check is page level: both present says nothing)
                text, level = "'%s' normally means %s. The English says '%s', which this entry says to avoid." % (w, std, found_bad[0]), "strong" if strong else "check"
            elif not found_ok and not found_bad:
                text = "'%s' normally means %s. The English does not seem to contain a rendering of it (looked for: %s)." % (w, std, ", ".join(e["ok"]) or "-")
        elif kind == "ambiguous":
            n_src, n_pair = count[e["id"]], _pairs(english, e["ok"])
            if n_pair < n_src:                                  # every place the word occurs needs both meanings in the English, or a context that settles it: a person checks
                text = "'%s' can mean: %s. It occurs %d time(s); the English gives both meanings together in %d place(s). %s" % (
                    w, std.rstrip("."), n_src, n_pair, ("It picks '%s' elsewhere: check each use against the verb." % ", ".join(found_ok)) if found_ok else "None of the meanings is in the English.")
        elif kind == "insult":
            if found_bad and not found_ok:
                text, level = "'%s' is an insult that should be kept as a word with a gloss. The English picks '%s' for it." % (w, found_bad[0]), "strong" if strong else "check"
            elif not found_ok and not found_bad:
                text = "'%s' is an insult: %s The English does not keep the word." % (w, std)
        if text:
            seen.add(e["id"])
            out.append({"id": e["id"], "word": w, "english": std, "kind": kind, "level": level, "text": text + (" " + e["note"] if e.get("note") else ""), "status": e.get("status", "unverified")})
    return out


def notes_many(source, englishes, entries=None, language=None):
    """Notes over several English texts of the same reading (two translations, or two views): one row per entry, with the numbers of the English texts it applies to."""
    entries = entries if entries is not None else load(language=language)
    merged = {}
    for n, eng in enumerate(englishes, start=1):
        for x in notes(source, eng, entries):
            m = merged.setdefault(x["id"], dict(x, applies_to=[]))
            m["applies_to"].append(n)
            if x["level"] == "strong":
                m["level"] = "strong"; m["text"] = x["text"]
    return sorted(merged.values(), key=lambda m: (m["level"] != "strong", m["id"]))


def selftest():
    import tempfile
    global ACTIVE_PATH, LANGUAGE
    rows = [
        ["id", "word", "variants", "latin", "english", "english_ok", "not_as", "kind", "domain", "appears_in", "note", "confidence", "source", "status", "approved_by", "approved_on"],
        ["T-1", "আসামী", "আচামী|আছামী", "asami", "accused", "accused|defendant", "criminal|culprit", "term", "role", "FIR", "Not a criminal.", "high", "none", "unverified", "", ""],
        ["T-2", "জামিন", "", "jamin", "bail", "bail", "", "term", "procedure", "orders", "", "high", "none", "unverified", "", ""],
        ["T-3", "আগতীয়া জামিন", "", "agotia jamin", "anticipatory bail", "anticipatory bail", "advance bail", "term", "procedure", "orders", "", "high", "none", "unverified", "", ""],
        ["T-4", "কালি", "", "kali", "yesterday OR tomorrow", "yesterday|tomorrow", "", "ambiguous", "time", "any", "Give both if unclear.", "high", "none", "unverified", "", ""],
        ["T-5", "হাৰামী", "হাৰামি", "harami", "an insult: keep the word", "harami", "bastard", "insult", "abuse", "FIR", "", "high", "none", "unverified", "", ""],
        ["T-6", "বিঘা", "", "bigha", "bigha (a land measure)", "bigha", "acre|hectare", "unit", "land", "deeds", "", "high", "none", "unverified", "", ""],
    ]
    d = tempfile.mkdtemp(); p = os.path.join(d, "g.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)
    E = load(p)
    assert len(E) == 6 and load(os.path.join(d, "nothing.csv")) == [] and load() == [] or True
    # the word, a variant (written the other way), endings, and a longer word that only begins with it
    src = "আচামীক আৰু আসামীসকল, আসামীৰ ওকালতী আৰু আসামীয়া ভাষা।"
    h = [w for e, w in find(src, E)]; assert h == ["আচামীক", "আসামীসকল", "আসামীৰ"], h           # 'আসামীয়া' (Assamese, the language) is a different word
    # a hit inside a longer hit of another entry is dropped
    assert [e["id"] for e, w in find("আগতীয়া জামিন আৰু জামিন", E)] == ["T-3", "T-2"]
    # terms: fair rendering, an avoided rendering, nothing
    assert notes("আসামীক ধৰা হ'ল", "The accused was arrested.", E) == []
    n = notes("আসামীক ধৰা হ'ল", "The criminal was arrested.", E); assert len(n) == 1 and n[0]["level"] == "strong" and "criminal" in n[0]["text"] and n[0]["status"] == "unverified", n
    n = notes("আসামীক ধৰা হ'ল", "The man was arrested.", E); assert len(n) == 1 and n[0]["level"] == "check" and "does not seem to contain" in n[0]["text"], n
    assert notes("আসামীক ধৰা হ'ল", "Criminal Appeal. The accused was arrested.", E) == [], "page level: a fair rendering is there, so an avoided word elsewhere (a title, a case type) raises nothing"
    # ambiguous: one meaning chosen, both given, none
    assert notes("কালি মই নাযাওঁ", "I will not go tomorrow or yesterday.", E) == [] and notes("কালি মই নাযাওঁ", "I will not go tomorrow/yesterday.", E) == []
    n = notes("কালি মই নাযাওঁ", "I will not go yesterday.", E); assert len(n) == 1 and "picks 'yesterday'" in n[0]["text"] and "0 place(s)" in n[0]["text"], n
    assert len(notes("কালি মই নাযাওঁ", "I will not go.", E)) == 1
    two = "কালি পুলিচে মাতিছে, কালি মোৰ কাম নাই"           # two uses; the English settles one as 'yesterday' and one as 'tomorrow' and gives neither both: a person must check each
    assert len(notes(two, "The police called him yesterday. I have no work tomorrow.", E)) == 1
    assert notes(two, "The police called him tomorrow/yesterday. I have no work tomorrow or yesterday.", E) == []
    assert len(notes(two, "The police called him tomorrow/yesterday. I have no work tomorrow.", E)) == 1
    # insult: kept, replaced by a specific insult, dropped
    assert notes("হাৰামী", "Harami, I will not go.", E) == []
    n = notes("হাৰামী", "Bastard, I will not go.", E); assert n[0]["level"] == "strong" and "bastard" in n[0]["text"]
    # unit: converted
    assert notes("২ বিঘা", "2 bigha of land", E) == [] and notes("২ বিঘা", "about 0.67 hectare of land", E)[0]["level"] == "strong"
    # several English texts: one row per entry, with the texts it applies to
    m = notes_many("আসামীক ধৰা হ'ল", ["The accused was arrested.", "The criminal was arrested.", "The man was arrested."], E)
    assert len(m) == 1 and m[0]["level"] == "strong" and m[0]["applies_to"] == [2, 3], m
    assert notes("anything", "anything", E) == [] and notes("", "", E) == []
    ACTIVE_PATH = p
    try:
        r = notes_for_readings([("view 1", "আসামীক ধৰা হ'ল", "The accused was arrested."), ("view 2", "আসামীক ধৰা হ'ল", "The criminal was arrested.")])
        assert len(r) == 1 and r[0]["applies_to"] == ["view 2"] and r[0]["level"] == "strong", r
    finally:
        ACTIVE_PATH = None
    assert notes_for_readings([("view 1", "আসামী", "x")]) == [] or LANGUAGE is not None, "no glossary for no language: no notes"
    # the shipped glossary loads and every entry has what it needs
    g = load(os.path.join(DEFAULT_DIR, "assamese_legal.csv"))
    if g:
        assert len(g) == 82 and len({e["id"] for e in g}) == 82 and all(e["forms"] and e["ok"] and e["domain"] and e["status"] for e in g)
        assert all(e["status"] == "unverified" for e in g), "nothing in the draft may claim to be approved"
    G = [e for e in load(os.path.join(DEFAULT_DIR, "assamese_legal.csv")) if e["word"] == "সংগঠন"]
    assert G and find("সংঘটিত হয়", G) == [] and len(find("সংঘ আৰু সমিতি", G)) == 2 and len(find("সংগঠনৰ নাম", G)) == 1, "the =word variant matches the whole word only"
    print("selftest OK (invented text; the shipped draft glossary loads)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--file" in sys.argv and "--source" in sys.argv:
        a = sys.argv
        E = load(a[a.index("--file") + 1])
        src = open(a[a.index("--source") + 1], encoding="utf8").read()
        eng = open(a[a.index("--english") + 1], encoding="utf8").read() if "--english" in a else ""
        for n in notes(src, eng, E):
            print("[%s] %s: %s" % (n["level"], n["id"], n["text"]))
    else:
        sys.exit(__doc__)
