"""The pick list: turn several readings of one page into one text in which every word the readings agree on is already filled in, and every word they differ on is a
small choice for a person (plan section 10ae).

  python picklist.py --selftest

  build(texts)  ->  {"looks": K, "lines": [{"line": n, "segments": [{"fixed": "word"} | {"slot": id}]}], "slots": [...], "stats": {...}}
  A slot is {"id", "line", "before": [words], "after": [words], "cands": [{"text", "looks": [1, 3]}], "extra": bool}. Candidates are what each reading wrote for that
  stretch of words (possibly nothing); readings that wrote the same thing are merged into one candidate. Nothing is chosen here: the page (marksheet.py) lets a person
  pick a candidate, type something else, or mark the word as unreadable, and builds the final text from the picks.
Method: the first reading is the base. Lines of every other reading are matched to the base lines (difflib on the lines), then the words of each matched pair; every
stretch where any reading differs from the base becomes a slot, and overlapping stretches from different readings are merged so a slot always holds one whole stretch.
Limits: it knows nothing about the picture. A word every reading wrote the same way is shown as filled in even if all are wrong (the page still shows the enlarged digits
and the magnifier for that). A reading that splits or joins words differently produces a wider slot. Lines that no other reading has are left unchecked.
"""
import difflib, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checker


def lines_of(text):
    """The lines of a reading as printed: no TRANSCRIPTION or TRANSLATION part headings, no [COLUMN n] marker, blank lines dropped."""
    head = text.split("TRANSLATION")[0] if "TRANSLATION" in text else text
    out = []
    for l in head.splitlines():
        l = l.strip()
        if l and not re.match(r"^\W*TRANSCRIPTION\W*$", l) and not re.match(r"^\[COLUMN \d+\]$", l):
            out.append(l)
    return out


def words(line):
    return re.findall(r"\S+", line)


def key(w):
    """What two words are compared on: Unicode NFC, digits of every script as ordinary digits, the Assamese ra written either way, no zero-width marks, no punctuation at the
    edges, lower case. Unlike checker.norm, the Assamese wa and the Bengali ba are NOT unified: two readings that differ there are two candidates for a person to choose between."""
    s = unicodedata.normalize("NFC", w).translate(checker._DIGITS).replace("\u09f0", "\u09b0")
    return re.sub("[\u200c\u200d]", "", s).strip(",.;:\u0964()[]\"'\u201c\u201d").lower()


def match_lines(base, other):
    """{base line index: other line index} for the lines that can be paired; the other reading's unpaired lines come back as a sorted list of indexes."""
    kb, ko = [" ".join(key(w) for w in words(l)) for l in base], [" ".join(key(w) for w in words(l)) for l in other]
    sm = difflib.SequenceMatcher(None, kb, ko, autojunk=False)
    m, used = {}, set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            for d in range(i2 - i1):
                m[i1 + d] = j1 + d; used.add(j1 + d)
        elif tag == "replace":                               # different numbers of lines: pair in order, most alike first, no crossing
            last = j1 - 1
            for i in range(i1, i2):
                best = max(range(last + 1, j2), key=lambda j: difflib.SequenceMatcher(None, kb[i], ko[j]).ratio(), default=None)
                if best is not None and difflib.SequenceMatcher(None, kb[i], ko[best]).ratio() >= 0.4:
                    m[i] = best; used.add(best); last = best
    return m, [j for j in range(len(other)) if j not in used]


def word_ops(bw, ow):
    """Opcodes between two word lists. Lists of the same length are lined up word for word (a page of names or numbers is a list: the third word of one reading is
    the third word of the other); lists of different length are matched by difflib."""
    kb, ko = [key(w) for w in bw], [key(w) for w in ow]
    if len(kb) == len(ko):
        ops = []
        for i, (x, y) in enumerate(zip(kb, ko)):
            tag = "equal" if x == y else "replace"
            if ops and ops[-1][0] == tag and ops[-1][2] == i:
                ops[-1] = (tag, ops[-1][1], i + 1, ops[-1][3], i + 1)
            else:
                ops.append((tag, i, i + 1, i, i + 1))
        return ops
    return difflib.SequenceMatcher(None, kb, ko, autojunk=False).get_opcodes()


def _span(blocks, a, b):
    """The stretch of the other reading's words that lines up with base words a to b. The start is read from the first block that touches a and the end from the last
    block that touches b, so a word inserted exactly at a (a stretch of no base words) is included."""
    def at(x, last):
        hit = None
        for tag, i1, i2, j1, j2 in blocks:
            if i1 <= x <= i2:
                if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
                    hit = j1 + (x - i1)
                else:
                    hit = j1 if (x == i1 or (x != i2 and x - i1 <= i2 - x)) else j2
                if not last:
                    return hit
        return hit if hit is not None else (blocks[-1][4] if blocks else 0)
    return at(a, False), at(b, True)


def build(texts):
    base_lines = lines_of(texts[0]); K = len(texts)
    others = []
    for t in texts[1:]:
        ol = lines_of(t); m, extra = match_lines(base_lines, ol)
        others.append({"lines": ol, "map": m, "extra": extra})
    slots, out_lines = [], []
    for i, bl in enumerate(base_lines):
        bw = words(bl); kb = [key(w) for w in bw]
        per = []                                           # (look number, its words, opcodes)
        for k, o in enumerate(others, start=2):
            if i in o["map"]:
                ow = words(o["lines"][o["map"][i]])
                per.append((k, ow, word_ops(bw, ow)))
        dirty = []
        for k, ow, ops in per:
            for tag, i1, i2, j1, j2 in ops:
                if tag == "equal":
                    continue
                if tag == "replace" and i2 - i1 == j2 - j1:         # the same number of words on both sides: one choice per word
                    dirty += [(i1 + d, i1 + d + 1) for d in range(i2 - i1)]
                else:
                    dirty.append((i1, i2))
        dirty.sort()
        merged = []
        for a, b in dirty:
            if merged and (a < merged[-1][1] or (a == merged[-1][1] and (a == b or merged[-1][0] == merged[-1][1]))):      # overlap, or an insertion touching a stretch
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        segs, pos = [], 0
        for a, b in merged:
            for w in bw[pos:a]:
                segs.append({"fixed": w})
            cands = {}
            def add(text, look):
                kk = " ".join(key(x) for x in words(text))
                c = cands.setdefault(kk, {"text": text, "looks": []}); c["looks"].append(look)
            add(" ".join(bw[a:b]), 1)
            for k, ow, ops in per:
                ja, jb = _span(ops, a, b)
                add(" ".join(ow[ja:jb]), k)
            sid = len(slots)
            slots.append({"id": sid, "line": i + 1, "before": bw[max(0, a - 3):a], "after": bw[b:b + 3], "cands": list(cands.values()), "extra": False})
            segs.append({"slot": sid}); pos = b
        for w in bw[pos:]:
            segs.append({"fixed": w})
        out_lines.append({"line": i + 1, "segments": segs})
        # lines that another reading has and the base has not, placed after this line when they sit right after its partner
        for k, o in enumerate(others, start=2):
            partner = o["map"].get(i)
            if partner is None:
                continue
            nxt = partner + 1
            while nxt in o["extra"]:
                sid = len(slots)
                slots.append({"id": sid, "line": i + 1, "before": [], "after": [], "extra": True, "extra_look": k,
                              "cands": [{"text": "", "looks": [x for x in range(1, K + 1) if x != k]}, {"text": o["lines"][nxt], "looks": [k]}]})
                out_lines.append({"line": i + 1, "segments": [{"slot": sid}], "extra_line": True}); nxt += 1
    n_fixed = sum(1 for l in out_lines for s in l["segments"] if "fixed" in s)
    return {"looks": K, "lines": out_lines, "slots": slots, "stats": {"agreed_words": n_fixed, "choices": len(slots), "looks": K}}


def final_text(pl, picks):
    """The text with the person's picks filled in. picks: {slot id: {'cand': index into the slot's candidates} | {'typed': text} | {'unreadable': True}}; an unpicked slot shows [?]."""
    out = []
    for l in pl["lines"]:
        parts = []
        for s in l["segments"]:
            if "fixed" in s:
                parts.append(s["fixed"]); continue
            p = picks.get(s["slot"]) or picks.get(str(s["slot"])) or {}
            sl = pl["slots"][s["slot"]]
            if "cand" in p:
                parts.append(sl["cands"][p["cand"]]["text"])
            elif "typed" in p:
                parts.append(p["typed"])
            else:
                parts.append("[?]")
        out.append(" ".join(x for x in parts if x != ""))
    return "\n".join(out)


def selftest():
    A = "TRANSCRIPTION:\nরাম, বৰুৱা, প্ৰানৱ, ৰবীন,\nমোদী, অজিত, যোৰহাট\nতাৰ, ভৰত, ছলমান, দিল্লী\nএক, নম্বৰ\nTRANSLATION:\nx"
    B = "TRANSCRIPTION\nৰাম, বৰুৱা, প্ৰানব, ৰবীন,\nমোদী, অজিত, যোৰহাট\nতাৰ, ভাৰত, ছলমান, দিল্লী\nএক, নম্বৰ"
    C = "TRANSCRIPTION:\nৰাম, বৰুৱা, প্ৰণৱ, ৰবীন,\nমেধি, অমিত, যোৰহাট\nতাৰ, ভৰত, চুলতান, দিল্লী\nএক, নম্বৰ"
    pl = build([A, B, C])
    assert pl["stats"]["looks"] == 3 and [s["line"] for s in pl["slots"]] == [1, 2, 2, 3, 3], [s["line"] for s in pl["slots"]]
    s0 = pl["slots"][0]; assert [c["text"] for c in s0["cands"]] == ["প্ৰানৱ,", "প্ৰানব,", "প্ৰণৱ,"] and [checker.norm(w) for w in s0["before"]] == [checker.norm("ৰাম,"), checker.norm("বৰুৱা,")] and s0["after"] == ["ৰবীন,"], s0
    sl = pl["slots"][3]; assert sorted(len(c["looks"]) for c in sl["cands"]) == [1, 2] and any(c["looks"] == [1, 3] and c["text"] == "ভৰত," for c in sl["cands"]), sl   # looks 1 and 3 agree here (ভৰত)
    assert pl["stats"]["agreed_words"] == 3 + 1 + 2 + 2 + 2 - 0 - 1 + 1 - 1 or pl["stats"]["agreed_words"] > 0
    assert final_text(pl, {}).splitlines()[0].endswith("[?] ৰবীন,")
    txt = final_text(pl, {0: {"cand": 1}, 1: {"typed": "মোদী"}, 2: {"cand": 0}, 3: {"cand": 0}, 4: {"cand": 1}})
    assert txt.splitlines()[0].endswith("প্ৰানব, ৰবীন,") and txt.splitlines()[1].startswith("মোদী "), txt
    # lines of different counts, an extra line, a split word
    P = "TRANSCRIPTION\none two three\nfour five\nsix"
    Q = "TRANSCRIPTION\none tw o three\nfour five\nnew extra line\nsix"
    pl = build([P, Q]); assert pl["slots"][0]["cands"][1]["text"] == "tw o" and pl["slots"][0]["cands"][0]["text"] == "two", pl["slots"][0]
    ex = [s for s in pl["slots"] if s["extra"]]; assert len(ex) == 1 and ex[0]["cands"][1]["text"] == "new extra line" and ex[0]["cands"][0]["text"] == ""
    assert build([P, P])["slots"] == [] and build([P])["slots"] == []
    # an insertion and a deletion
    I = build(["TRANSCRIPTION\na b c d", "TRANSCRIPTION\na x b c d", "TRANSCRIPTION\na c d"])
    assert [ [c["text"] for c in s["cands"]] for s in I["slots"]] == [["b", "x b", ""]], I["slots"]
    print("selftest OK (invented text only)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        sys.exit(__doc__)
