"""Tests for goodlaw/chat_format.py: the offline message formatter (a retrieved passage, the Overruled Register and the currency cards in; one chat message out, warning first).
Run: python test_goodlaw_chat_format.py

Part 1 uses a small register and a few cards written here, one for each rule. Part 2 runs the formatter over the real register (1,765 rows) and the real 76 cards and checks what must always hold.
"""
import os

from goodlaw import cardreader as CR
from goodlaw import chat_format as CF
from goodlaw import register as R

FAILURES = []
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = "2026-10-22"
PLACEHOLDER = "[Matched paragraph, word for word from the judgment. Placeholder text in this test.]"


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc:
        return True
    except BaseException:
        return False
    return False


def row(rid, a, ayear, b, byear, trust="verified", treatment="overruled", cites=(), scope=None):
    return {"id": rid, "source": "t", "trust": trust,
            "overruled": {"name": a, "alt_names": [], "court": "SC", "cites": list(cites), "keys": R.key_set(" : ".join(cites)), "year": ayear, "years": [ayear]},
            "overruling": {"name": b, "court": "SC", "cites": [], "keys": [], "year": byear, "date": None, "bench": None},
            "treatment": treatment, "scope": scope, "court_words": None, "same_parties": False, "flags": [], "evidence": {"basis": "B"}, "verification": None, "history": []}


ROWS = [
    row("V1", "Ratanlal Industries v. Sethi Traders", 1965, "State of Mysore v. Syed Mahmood", 1968, cites=["(1965) 2 SCR 120"]),
    row("C1", "Mohan Lal v. State of Punjab", 2018, "Mukesh Singh v. State (Narcotic Branch of Delhi)", 2020, trust="candidate", cites=["(2018) 17 SCC 627"]),
    row("N1", "Gamma Industries v. Delta Traders", 1990, "Epsilon Bank v. Zeta Mills", 1995, treatment="not_good_law"),
    row("U1", "Foo Brothers v. Bar Works", 2001, "Baz Corp v. Qux Ltd", 2010, trust="unchecked"),
]
REG = R.Register(ROWS, {"built_on": "2026-10-07"})


def card(name, status, note=None, generated="2026-10-06", statute_note=None, review=None, keys=()):
    return {"case": {"name": name, "citation_keys": list(keys)}, "status": status, "user_facing_note": note, "statute_note": statute_note, "internal_note": "", "review": review,
            "provenance": {"generated": generated}}


ADV = "A later five-judge bench of the Supreme Court (2020) appears to overrule or reject this case, in whole or in part, so check it before relying on this case."
CAU = "Later judgments doubt or limit this case, so check them before relying on it."
CARDS = CR.load({"cards": [
    card("Alpha v Beta", "ADVERSE_SIGNAL", ADV),
    card("Human v Review", "ADVERSE_SIGNAL", ADV, review={"current": True, "verdict": "CONFIRMED_ADVERSE", "reviewer": "Mr. Advocate", "date": "2026-10-10"}),
    card("Cleared v Case", "ADVERSE_SIGNAL", ADV, review={"current": True, "verdict": "FALSE_ALARM", "reviewer": "Mr. Advocate", "date": "2026-10-10"}),
    card("Research v Case", "QUESTIONED", CAU, review={"current": True, "verdict": "NEEDS_RESEARCH", "reviewer": "Mr. Advocate", "date": "2026-10-10"}),
    card("Gamma Corp v Delta Ltd", "QUESTIONED", CAU),
    card("Quiet v Case", "NO_ADVERSE_FOUND"),
    card("Few v Cites", "INSUFFICIENT"),
    card("High v Court", "NOT_CHECKABLE_HIGH_COURT"),
    card("Absent v Collection", "NOT_IN_COLLECTION"),
    card("Statute v Case", "NO_ADVERSE_FOUND", statute_note="This judgment discusses a section whose number changed under the 2023 codes."),
    card("Questioned Statute v Case", "QUESTIONED", CAU, statute_note="This judgment discusses a section whose number changed under the 2023 codes."),
    card("Old v Card", "ADVERSE_SIGNAL", ADV, generated="2026-01-01"),
    card("Bad v Note", "QUESTIONED", "This case is still valid in most respects."),
    card("Mohan Lal v State of Punjab", "ADVERSE_SIGNAL", ADV, keys=["scc:2018:17:627"]),
]})
F = CF.Formatter(REG, CARDS, quiet_policy="coverage_note", today=TODAY)
FS = CF.Formatter(REG, CARDS, quiet_policy="silent", today=TODAY)


def cur(name, year=None, citation=None, fmt=F):
    return fmt.currency(name, year, citation)


def one(name, year=None, citation=None, fmt=F):
    c = cur(name, year, citation, fmt)
    return c.lines


def passage(name, year=None, citation=None, **kw):
    p = {"case_name": name, "year": year, "citation": citation, "court": "Supreme Court", "para": 14, "page": 9, "text": PLACEHOLDER}
    p.update(kw)
    return p


# ---- what the formatter refuses ------------------------------------------------------------------------------------------------------------------------------------------------
print("setup")
check(raises(ValueError, CF.Formatter, None, CARDS, quiet_policy="silent") and raises(ValueError, CF.Formatter, REG, None, quiet_policy="silent"), "a missing register or card index is refused, so 'no entry' is never said about nothing")
check(raises(TypeError, CF.Formatter, REG, CARDS), "quiet_policy has no default: the owner's open decision cannot be inherited by accident")
check(raises(ValueError, CF.Formatter, REG, CARDS, quiet_policy="whatever"), "and an unknown policy is refused")

# ---- the six rules -------------------------------------------------------------------------------------------------------------------------------------------------------------
print("rule 1 and 2: the register")
l = one("Ratanlal Industries v. Sethi Traders", 1965)
check(len(l) == 1 and l[0].level == CF.RED and l[0].rule == 1 and l[0].firm and l[0].headline == "On the Overruled Register", "a row a person confirmed gives a firm RED line")
check("was overruled by State of Mysore v. Syed Mahmood (1968)" in l[0].body and l[0].as_of == "2026-10-07", "in the register's own wording, as of the date the register was built")
l = one("Mohan Lal v State of Punjab", 2018, "(2018) 17 SCC 627")
check(l[0].level == CF.RED and l[0].rule == 2 and not l[0].firm and l[0].headline == "Reported on the Overruled Register" and "not yet confirmed by our reviewer" in l[0].body, "a candidate row is RED but hedged: 'reported ... not yet confirmed by our reviewer'")
check(len(l) == 2 and l[1].rule == 3, "and when the checker's card also flags the case, its line follows the register's")

print("rule 3 and 4: the card")
l = one("Alpha v Beta")
check(len(l) == 1 and l[0].level == CF.RED and l[0].rule == 3 and l[0].headline == "Reported adverse" and l[0].body == ADV and not l[0].firm and l[0].as_of == "2026-10-06", "an ADVERSE_SIGNAL card gives 'Reported adverse', in the card's own sentence, not firm")
l = one("Human v Review")
check(l[0].headline == "Adverse, confirmed by our reviewer" and l[0].firm and l[0].level == CF.RED, "a person's confirmation makes it firm and says so")
l = one("Gamma Corp v Delta Ltd")
check(len(l) == 1 and l[0].level == CF.AMBER and l[0].headline == "Questioned" and l[0].rule == 4 and l[0].body == CAU, "a QUESTIONED card gives an AMBER line")
check("looking at this case" in one("Research v Case")[0].body, "a case a person marked as needing research says our reviewer is looking at it")
l = one("Old v Card")
check("may be out of date" in l[0].body and "1 Jan 2026" in l[0].body, "a card older than 45 days says when it was run and that it may be out of date")
l = cur("Bad v Note")
check(l.lines[0].level == CF.AMBER and l.lines[0].body == CF.ADVERSE_FALLBACK and any("withheld" in n for n in l.internal), "a card note the wording guard withheld is replaced by a plain fallback, never by nothing, and the reviewer is told")

print("rule 5: a quiet card (the open decision)")
l = one("Quiet v Case")
check(len(l) == 1 and l[0].level == CF.GREY and l[0].rule == 5 and l[0].headline == CF.QUIET_HEAD and l[0].body == CF.QUIET_BODY, "with coverage_note a quiet card gets the grey 'no warning found in what we hold' line")
check("good law" in l[0].body and "not a finding" in l[0].body, "which says in the same breath that it is not a finding")
c = cur("Quiet v Case", fmt=FS)
check(c.lines == () and any("quiet card" in n for n in c.internal), "with silent a quiet card gets no line, and a note for the reviewer")
check(one("Cleared v Case")[0].rule == 5 and cur("Cleared v Case", fmt=FS).lines == (), "a flagged card a person cleared is treated as quiet")

print("rule 6: not checked by us")
for name, why in (("Nobody v Nowhere", "no card"), ("Few v Cites", "too few later judgments"), ("High v Court", "a High Court case"), ("Absent v Collection", "a judgment we do not hold")):
    l = one(name)
    check(len(l) == 1 and l[0].level == CF.OUTLINE and l[0].headline == CF.NOT_CHECKED and l[0].rule == 6, f"{why}: 'Not checked by us'")
    check("verify it before you cite it" in l[0].body.lower(), f"{why}: and it says to verify the case")
check("High Court" in one("High v Court")[0].body and "Too few later judgments" in one("Few v Cites")[0].body, "the High Court and too-few cases say why")
check(one("Few v Cites", fmt=FS)[0].level == CF.OUTLINE, "the silent policy does not silence 'not checked'")

print("other rules")
l = one("Statute v Case")
check([x.level for x in l] == [CF.GREY, CF.INFO] and "2023 codes" in l[1].body, "a statute note is added as its own line, last")
check([x.level for x in one("Questioned Statute v Case")] == [CF.AMBER, CF.INFO], "also after a caution")
l = cur("Foo Brothers v Bar Works")
check(l.lines[0].rule == 6 and any("weak register match" in n for n in l.internal), "a bare name matches an unchecked row only weakly: not worded, 'not checked', and kept for the weekly review")
l = cur("Foo Brothers v. Bar Works", 2001)
check(l.lines[0].rule == 6 and any("without wording" in n for n in l.internal), "a strong match to an unchecked row is never worded either")
c = cur("Mohan Lal v State of Punjab")
check([x.rule for x in c.lines] == [3] and any("weak register match to C1" in n for n in c.internal), "a bare name with no year or citation is a weak register match: not worded as a register fact, and only the card speaks")
l = one("Gamma Industries v. Delta Traders", 1990)
check("held not to be good law in Epsilon Bank v. Zeta Mills" in l[0].body, "a court's holding is worded as the register words it")
m = F.format(passage("Gamma Industries v. Delta Traders", 1990))
check("HELD NOT TO BE GOOD LAW" not in m.text and "held not to be good law in" in m.text, "and that phrase passes the wording guard")

# ---- the wording guard ---------------------------------------------------------------------------------------------------------------------------------------------------------
print("wording")
check(CF.wording_violations("This case is good law.") == ["good law"] and CF.wording_violations("It is still valid.") == ["still valid"], "a claim of good law, or a phrase like 'still valid', is caught")
check(CF.wording_violations(CF.QUIET_BODY) == [] and CF.wording_violations("It was held not to be good law in X.") == [], "the fixed 'not a finding' sentence and a court's holding are allowed")
bad = CF.Currency((CF.Line(CF.GREY, "Fine", "This case is good law.", "", 5),))
check(raises(CF.WordingError, CF.render, passage("X v Y"), bad), "a message whose own wording claims good law is not built")
ok = True
for name in ("Alpha v Beta", "Human v Review", "Gamma Corp v Delta Ltd", "Quiet v Case", "Few v Cites", "High v Court", "Statute v Case", "Old v Card", "Bad v Note", "Nobody v Nowhere"):
    for fmt in (F, FS):
        ok = ok and not CF.wording_violations(fmt.format(passage(name), intro=True).text.replace(PLACEHOLDER, ""))
check(ok, "no message in the set claims good law, with either policy")

# ---- the message ---------------------------------------------------------------------------------------------------------------------------------------------------------------
print("the message")
m = F.format(passage("Alpha v Beta", url="https://example.invalid/judgment"), intro=True)
t = m.text
check(t.index("REPORTED ADVERSE") < t.index("Alpha v Beta") < t.index(PLACEHOLDER), "the warning comes first, then the case, then the passage")
check("Supreme Court · para 14 · page 9" in t and "As of 6 Oct 2026." in t and f"“{PLACEHOLDER}”" in t, "the case line, the as-of date and the passage in quotes, word for word")
check(t.rstrip().endswith(CF.INTRO_FOOTER) and CF.INTRO_FOOTER not in F.format(passage("Alpha v Beta")).text, "the not-verified line closes the first message only")
check([(b.label, b.action) for b in m.buttons] == [("Read full judgment", "open_url")], "a link gives a 'Read full judgment' button")
check([b.action for b in F.format(passage("Alpha v Beta", doc_id=7), with_watch=True).buttons] == ["open_judgment", "watch"] and F.format(passage("Alpha v Beta")).buttons == (), "a document id gives an open action; the watch button is only on request; none otherwise")
check(not any(n in t for n in ("V1", "C1", "U1", "weak register")) and m.internal == (), "internal notes and row ids never reach the text")
m = F.format(passage("Foo Brothers v Bar Works"))
check(m.internal and not any(n in m.text for n in m.internal), "even when there are internal notes")
check(raises(ValueError, F.format, {"case_name": "X v Y", "text": ""}) and raises(ValueError, F.format, {"case_name": "", "text": "x"}), "a passage with no text or no case name is refused")

print("a long passage")
LONG = " ".join(f"word{i}" for i in range(900))
m = F.format(passage("Alpha v Beta", text=LONG), max_chars=800)
body = m.text.split("“", 1)[1].rsplit("”", 1)[0]
check(len(m.text) <= 800 and m.truncated and not m.over_limit and body.endswith(" […]"), "only the passage is shortened, to fit, and the message says so")
check(LONG.startswith(body[:-len(" […]")]) and LONG[len(body) - 4:len(body) - 3] == " ", "at a word boundary, from the start of the original, with nothing changed")
check(all(CF._line_text(x) in m.text for x in m.lines) and "REPORTED ADVERSE" in m.text, "the warning is whole")
m = F.format(passage("Alpha v Beta", text=PLACEHOLDER), max_chars=800)
check(not m.truncated and PLACEHOLDER in m.text, "a short passage is left alone")
big = CF.Currency((CF.Line(CF.RED, "Reported adverse", "x " * 600, "2026-10-06", 3),))
m = CF.render(passage("Alpha v Beta", text=LONG), big, max_chars=300)
check(m.over_limit and all(CF._line_text(x) in m.text for x in m.lines) and len(m.text.split("“", 1)[1]) >= CF.MIN_PASSAGE, "if the warnings alone are longer than the limit, nothing is cut and the message says it is over the limit")

print("a passage nobody could identify, and a passage-type line")
m = F.format(passage("Judgment no. 555 (title not available)", identified=False))
check(m.lines[0].rule == 6 and m.lines[0].level == CF.OUTLINE and "could not identify" in m.text and "No register entry" not in m.text and "NOT CHECKED BY US" in m.text, "an unidentified passage says it could not be identified, never 'no register entry'")
check(any("not identified" in n for n in m.internal), "and the reviewer's note says the register and cards were not consulted")
m = F.format(passage("Alpha v Beta", kind_label="Appears to record counsel's arguments, not the Court's view."))
check("Passage: Appears to record counsel's arguments, not the Court's view." in m.text and m.text.index("Passage:") < m.text.index(PLACEHOLDER) and m.text.index("Alpha v Beta") < m.text.index("Passage:"), "a passage-type line sits under the case line, before the passage")
check("Passage:" not in F.format(passage("Alpha v Beta")).text and "Passage:" not in F.format(passage("Alpha v Beta", kind_label="  ")).text, "no label, no line")
check(raises(CF.WordingError, F.format, passage("Alpha v Beta", kind_label="This is good law.")), "a label that claims good law is refused like any other wording of ours")

print("a batch")
msgs = F.format_batch([passage("Alpha v Beta"), passage("Quiet v Case"), passage("Nobody v Nowhere")], shown=2)
check(len(msgs) == 3 and "Found 3 passages" in msgs[0].text and "Showing 2" in msgs[0].text and CF.INTRO_FOOTER in msgs[0].text, "a header, then one message per passage shown")
check(not CF.wording_violations(msgs[0].text) and msgs[1].lines[0].rule == 3 and msgs[2].lines[0].rule == 5, "the header makes no claim, and each message keeps its own line")

# ---- the real register and the real cards --------------------------------------------------------------------------------------------------------------------------------------
print("the real register and cards")
REAL_REG = R.Register.load()
REAL_CARDS = CR.load(os.path.join(HERE, "cards", "currency_cards.json"))
RF = CF.Formatter(REAL_REG, REAL_CARDS, quiet_policy="coverage_note", today="2026-10-22")
RFS = CF.Formatter(REAL_REG, REAL_CARDS, quiet_policy="silent", today="2026-10-22")
m = RF.format(passage("Mohan Lal v State of Punjab", 2018, "(2018) 17 SCC 627"))
check(m.lines[0].rule == 2 and m.lines[1].rule == 3 and "Mukesh Singh" in m.text and "REPORTED ON THE OVERRULED REGISTER" in m.text and "REPORTED ADVERSE" in m.text, "Mohan Lal (2018): the register's candidate row and the checker's card both warn, register first")
m = RF.format(passage("Siddharam Satlingappa Mhetre v State of Maharashtra", 2011, "(2011) 1 SCC 694"))
check(m.lines[0].level == CF.RED and "Sushila Aggarwal" in m.text, "Mhetre (2011): warned, with the overruling case named")
m = RF.format(passage("National Building Material Supply v. Jai Jai Ram Manohar Lal", 1965))
check(m.lines[0].rule == 1 and m.lines[0].firm and "ON THE OVERRULED REGISTER" in m.text, "a verified list-1 case gets the firm line")
check(RF.format(passage("Nobody v Nowhere")).lines[0].rule == 6 and RF.format(passage("Deepa v S. Vijayalakshmi")).lines[0].headline == CF.NOT_CHECKED, "an unknown case and a High Court case are 'not checked by us'")

names = [c["case"]["name"] for c in REAL_CARDS["cards"]]
by_status = {}
bad = []
for c in REAL_CARDS["cards"]:
    for fmt in (RF, RFS):
        try:
            msg = fmt.format(passage(c["case"]["name"], c["case"].get("year"), c["case"].get("citation")))
        except Exception as e:
            bad.append((c["case"]["name"], repr(e)))
            continue
        if fmt is RF:
            by_status.setdefault(c["status"], []).append(msg)
        if CF.wording_violations("\n\n".join(CF._line_text(x) for x in msg.lines)):
            bad.append((c["case"]["name"], "wording"))
check(len(names) == 76 and not bad, f"all 76 real cards format with both policies and none breaks the wording guard ({bad[:2]})")
check(all(any(x.level == CF.RED for x in m.lines) for m in by_status["ADVERSE_SIGNAL"]), "every ADVERSE_SIGNAL card comes out with a RED line")
quiet_ok = all(m.lines and m.lines[0].level in (CF.GREY, CF.RED, CF.AMBER) for m in by_status["NO_ADVERSE_FOUND"])
check(quiet_ok and all(any(x.level == CF.OUTLINE for x in m.lines) or any(x.level == CF.RED for x in m.lines)
                       for s in ("INSUFFICIENT", "NOT_CHECKABLE_HIGH_COURT") for m in by_status.get(s, [])), "quiet cards get a grey line (or a register warning), and unchecked ones 'not checked' (or a register warning)")

rows_bad, n_red, n_firm = [], 0, 0
for r in REAL_REG.rows:
    if r["trust"] in R.NO_WORDING:
        continue
    o = r["overruled"]
    try:
        msg = RF.format(passage(o["name"], o.get("year"), (o.get("cites") or [None])[0]))
    except Exception as e:
        rows_bad.append((r["id"], repr(e)))
        continue
    if msg.lines and msg.lines[0].level == CF.RED:
        n_red += 1
        n_firm += 1 if msg.lines[0].firm else 0
check(not rows_bad, f"every register row with wording formats without an error ({rows_bad[:2]})")
check(n_red >= 1500 and n_firm >= 1400, f"and almost all of them come out with a RED register line ({n_red} red, {n_firm} firm of {sum(1 for r in REAL_REG.rows if r['trust'] not in R.NO_WORDING)})")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
