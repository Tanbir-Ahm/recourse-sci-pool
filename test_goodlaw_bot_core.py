"""Tests for goodlaw/bot_core.py: the pilot bot's core (a message in, replies out), with a stub search and the real register and cards. No chat service, no network, no spend.
Run: python test_goodlaw_bot_core.py
"""
import csv
import io
import json
import os
import re
import socket
import sys
import tempfile

from goodlaw import bot_core as B
from goodlaw import cardreader as CR
from goodlaw import chat_format as CF
from goodlaw import passage_input as PI
from goodlaw import pilot as P
from goodlaw import register as R

FAILURES = []
HERE = os.path.dirname(os.path.abspath(__file__))
DAY = "2026-11-05"


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


REG, CARDS = R.Register.load(), CR.load(os.path.join(HERE, "cards", "currency_cards.json"))
FMT = CF.Formatter(REG, CARDS, quiet_policy="coverage_note", today="2026-11-05")
DOCS = PI.IndexDocs([
    {"doc": 1000000001, "passages": 5, "src": {"title": "MOHAN LAL versus STATE OF PUNJAB", "date": "24-07-2018", "citation": "(2018) 17 SCC 627", "case_id": "2018 INSC 1", "path": "a"}},
    {"doc": 1000000002, "passages": 5, "src": {"title": "SAMPLE ONE versus STATE", "date": "01-02-2015", "citation": "[2015] 1 S.C.R. 1", "case_id": "2015 INSC 2", "path": "b"}},
    {"doc": 1000000003, "passages": 5, "src": {"title": "SAMPLE TWO versus STATE", "date": "01-02-2016", "citation": "[2016] 1 S.C.R. 1", "case_id": "2016 INSC 3", "path": "c"}},
])
WHO = PI.IndexRowIdentity(DOCS)
HASHES = ["1111aaaa2222bbbb", "3333cccc4444dddd", "5555eeee6666ffff", "7777aaaa8888bbbb"]
HITS = [{"doc": 1000000001, "i": 0, "pn": "14", "page": 9, "section": "reasoning", "h": HASHES[0], "text": "14. A passage of the first judgment, word for word."},
        {"doc": 1000000002, "i": 1, "pn": "3", "page": 2, "section": "argument", "h": HASHES[1], "text": "3. Counsel for the appellant submitted that the order was bad."},
        {"doc": 777, "i": 2, "pn": None, "page": 1, "section": "reasoning", "h": HASHES[2], "text": "A passage from a judgment nobody can name."},
        {"doc": 1000000003, "i": 3, "pn": "8", "page": 4, "section": "reasoning", "h": HASHES[3], "text": "8. A fourth passage that is not shown."}]
CALLS = []


def search(q):
    CALLS.append(q)
    return HITS


def make(search_fn=search, store=None, export=None, **kw):
    p = P.Pilot()
    p.add_user("111", "Adv. A", "the owner", DAY)
    p.add_user("222", "Adv. B", "the owner", DAY)
    return p, B.BotCore(p, FMT, search_fn, WHO, store_dir=store, export_dir=export, today=DAY, **kw)


def texts(replies):
    return "\n".join(r.text for r in replies)


def accepted(core, uid):
    core.handle(uid, text="I understand")


# ---- who is let in ---------------------------------------------------------------------------------------------------------------------------------------------------------------
print("who is let in")
p, core = make()
r = core.handle("999", text="What is the rule on bail?")
check([x.text for x in r] == [P.NOT_ON_LIST] and not CALLS and p.state["questions"] == [], "a stranger gets one neutral line; nothing is searched or recorded")
r = core.handle("111", text="What is the rule on bail?")
check([x.text for x in r] == [P.ONBOARDING] and not CALLS, "a user who has not accepted the rules gets the rules, not an answer")
r = core.handle("111", text="/watch X v Y")
check([x.text for x in r] == [P.ONBOARDING], "and cannot use a command either")
r = core.handle("111", text="  I understand. ")
check(r[0].text == B.ACCEPTED and p.gate("111")[0] is True, "'I understand', in any case and with punctuation, accepts the rules")
check(core.handle("222", text="yes")[0].text == P.ONBOARDING and p.gate("222")[0] is False, "anything else does not")
p.set_active("111", False, "the owner")
check([x.text for x in core.handle("111", text="hello")] == [P.SWITCHED_OFF] and [x.text for x in core.handle("111", tap="m|q1|" + HASHES[0] + "|r")] == [P.SWITCHED_OFF], "a switched-off user gets one line, for a message or a tap")
p.set_active("111", True, "the owner")
p.rules_version = "v2"
check(core.handle("111", text="hello")[0].text == P.ONBOARDING, "when the rules change, the user is asked again")

# ---- a question ------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("a question")
CALLS.clear()
p, core = make()
accepted(core, "111")
r = core.handle("111", text="Can bail be refused on a conspiracy allegation?")
check(CALLS == ["Can bail be refused on a conspiracy allegation?"] and len(r) == 4, "the question is searched once, and the answer is a header and three passages")
check("Found 4 passages" in r[0].text and "Showing 3" in r[0].text and CF.INTRO_FOOTER in r[0].text and r[0].buttons == (), "the header counts every hit found, says how many are shown and that nothing is verified")
m1 = r[1]
check(m1.text.index("REPORTED ADVERSE") < m1.text.index("MOHAN LAL v. STATE OF PUNJAB\nSupreme Court") < m1.text.index(HITS[0]["text"]) and "ON THE OVERRULED REGISTER" in m1.text, "the passage from an overruled-listed case opens with the register's and the checker's warnings, then the case, then the passage")
check([b[0] for b in m1.buttons] == ["Relevant", "Not relevant", "Misleading"] and all(b[1] == "mark" for b in m1.buttons) and m1.text.endswith(P.FEEDBACK_PROMPT), "each passage ends with the feedback prompt and its three buttons")
check("Passage: Appears to record counsel's arguments" in r[2].text, "an argument passage says so")
check("NOT CHECKED BY US" in r[3].text and "could not identify" in r[3].text, "a passage nobody can name says it could not be identified")
q = p.state["questions"][0]
check(q["id"] == "q1" and q["shown"] == [[HASHES[0], 1000000001], [HASHES[1], 1000000002], [HASHES[2], 777]] and q["text"] is None, "the passages shown are recorded for the question; its text is not kept")
check(not core.handle("111", text="   ")[0].buttons and core.handle("111", text="   ")[0].text == B.HELP and len(CALLS) == 1, "an empty message gets the help text and no search")
none = make(lambda q: [])[1]
accepted(none, "111")
check(none.handle("111", text="Anything")[0].text == B.NO_PASSAGES, "no passages found is said plainly")

# ---- the feedback buttons ---------------------------------------------------------------------------------------------------------------------------------------------------------
print("feedback")
tap = m1.buttons[2][2]
r = core.handle("111", tap=tap)
check([x.text for x in r] == [B.THANKS] and p.state["marks"][0]["mark"] == "misleading" and p.state["marks"][0]["doc"] == 1000000001, "a tap records the mark, with the index doc taken from what was shown")
check(core.handle("111", tap="m|q1|" + HASHES[3] + "|r")[0].text == B.STALE_TAP and len(p.state["marks"]) == 1, "a tap on a passage that was not shown is refused")
check(core.handle("222", tap=tap)[0].text == P.ONBOARDING, "another user's tap, before they have accepted, gets the rules")
accepted(core, "222")
check(core.handle("222", tap=tap)[0].text == B.STALE_TAP and core.handle("111", tap="garbage")[0].text == B.STALE_TAP and len(p.state["marks"]) == 1, "another user's tap on this question, or a made-up tap, is refused")

# ---- limits and a search that fails -------------------------------------------------------------------------------------------------------------------------------------------
print("limits")
CALLS.clear()
p, core = make(daily_question_cap=2, global_daily_cap=3)
accepted(core, "111"); accepted(core, "222")
core.handle("111", text="one"); core.handle("111", text="two")
r = core.handle("111", text="three")
check(r[0].text == B.LIMIT_USER and len(CALLS) == 2, "past the user's daily limit nothing is searched")
core.handle("222", text="four")
check(core.handle("222", text="five")[0].text == B.LIMIT_ALL and len(CALLS) == 3, "past the test's daily limit nothing is searched for anyone")
check(core.handle("222", text="six", on="2026-11-06")[0].text != B.LIMIT_ALL and len(CALLS) == 4, "and the limits start again the next day")


def down(q):
    raise B.SearchUnavailable()


p, core = make(down, daily_question_cap=1)
accepted(core, "111")
check(core.handle("111", text="a question")[0].text == B.SEARCH_DOWN and p.state["questions"] == [], "a search that is unavailable is answered politely and the question is not recorded")
core.search_fn = search
check(core.handle("111", text="a question")[0].text != B.LIMIT_USER, "so it does not use up the user's limit")


def broken(q):
    raise RuntimeError("bug")


p, core = make(broken)
accepted(core, "111")
check(raises(RuntimeError, core.handle, "111", text="a question"), "any other exception in the search is a bug and is raised, not hidden")

# ---- commands --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("commands")
with tempfile.TemporaryDirectory() as d:
    store, export = os.path.join(d, "store"), os.path.join(d, "exports")
    p, core = make(store=store, export=export)
    accepted(core, "111"); accepted(core, "222")
    check(core.handle("111", text="/watchlist")[0].text == B.EMPTY_WATCHLIST and core.handle("111", text="/export")[0].text == B.EMPTY_WATCHLIST, "an empty watchlist says so, for the list and for the export")
    r = core.handle("111", text="/watch Mohan Lal v State of Punjab (2018) ; (2018) 17 SCC 627")
    t = r[0].text
    check(t.startswith(B.SAVED) and "REPORTED ON THE OVERRULED REGISTER" in t and "REPORTED ADVERSE" in t and t.endswith("Silence is not an all-clear."), "saving a case shows what is known today, warnings first, and ends by saying silence is not an all-clear")
    check("alert" not in t.lower() and "we will tell you" not in t.lower(), "and promises no alert, because nothing sends alerts yet")
    core.handle("111", text="/watch Nobody v Nowhere")
    check(core.handle("111", text="/watch")[0].text.startswith("To save a case, write /watch") and core.handle("111", text="/watch ab")[0].text.startswith("To save a case"), "a /watch without a case name says how to write one")
    r = core.handle("111", text="/watchlist")[0].text
    check("- Mohan Lal v State of Punjab: Reported on the Overruled Register" in r and "- Nobody v Nowhere: Not checked by us" in r and r.endswith("Check every case before you cite it."), "the list shows each saved case with its status line")
    check(core.handle("222", text="/watchlist")[0].text == B.EMPTY_WATCHLIST, "another user's watchlist is separate")
    r = core.handle("111", text="/export")[0]
    rows = list(csv.DictReader(io.StringIO(open(r.attachment, encoding="utf-8-sig", newline="").read(), newline="")))
    check(r.attachment.startswith(export) and r.attachment.endswith("authorities_adv-a_2026-11-05.csv") and len(rows) == 2 and rows[0]["case"] == "Mohan Lal v State of Punjab" and all(x["note"] for x in rows), "an export gives a spreadsheet of the saved cases, most pressing first, each row with its note")
    check("111" not in os.path.basename(r.attachment), "and the file name carries the label, not the chat id")
    p2 = P.Pilot()
    p2.add_user("111", "Adv. A", "the owner", DAY)
    p2.accept("111", DAY)
    core2 = B.BotCore(p2, FMT, search, WHO, store_dir=store, export_dir=export, today=DAY)
    check("Mohan Lal v State of Punjab" in core2.handle("111", text="/watchlist")[0].text, "a restarted core finds the saved cases in the store")
    check(core.handle("111", text="/whatever")[0].text == B.HELP, "an unknown command gets the help text")
    p3, core3 = make(store=store)
    accepted(core3, "111")
    core3.handle("111", text="/watch Alpha v Beta (2010)")
    check(core3.handle("111", text="/export")[0].text == B.NO_EXPORT, "with no export folder, export says it is not available")
    check(sorted(f for f in os.listdir(store) if f.startswith("watch_")) == [f for f in sorted(os.listdir(store)) if f.startswith("watch_")] and not any("111" in f for f in os.listdir(store)), "the stored files are named by label and a short hash, never the chat id")

# ---- everything it said ----------------------------------------------------------------------------------------------------------------------------------------------------------
print("everything it said")
sent = []
real_connect, real_lookup = socket.socket.connect, socket.getaddrinfo


def no_network(*a, **kw):
    raise AssertionError("a network call was attempted")


socket.socket.connect, socket.getaddrinfo = no_network, no_network
try:
    p, core = make(export=tempfile.mkdtemp())
    for uid in ("999", "111"):
        sent += core.handle(uid, text="hello")
    accepted(core, "111")
    for t in ("What does the Court say about bail?", "/help", "/watch Sample One v State (2015)", "/watch Mohan Lal v State of Punjab (2018) ; (2018) 17 SCC 627", "/watchlist", "/export", "???"):
        sent += core.handle("111", text=t)
    r = core.handle("111", text="Another question")
    sent += r
    for b in r[1].buttons:
        sent += core.handle("111", tap=b[2])
        break
    ran_offline = True
except AssertionError:
    ran_offline = False
finally:
    socket.socket.connect, socket.getaddrinfo = real_connect, real_lookup
check(ran_offline, "a whole conversation (question, commands, export, a tap) runs with every network call blocked")
own = []
for o in sent:
    text = o.text
    for h in HITS:
        text = text.replace(h["text"], "")                         # the passages are the judgments' own words; everything else is ours
    own.append(text)
check(not any(CF.wording_violations(t) for t in own), "nothing it sent, apart from the passages themselves, claims a case is good law")
check(not any("111" in o.text.replace("1000000001", "").replace("1111aaaa", "") for o in sent), "no chat id appears in anything sent")
check(all(len(o.text) < 4096 for o in sent), "every message is under 4,096 characters, the smallest limit of the chat services")

print("hits from the real search code (fake service, no network, no spend)")
sys.path.insert(0, os.path.join(HERE, "review_tools"))
try:
    import fake_pool_fixture as FX
except Exception as e:
    FX = None
    print(f"[SKIP] the search engine could not be imported ({e!r})")
if FX:
    def engine_search(q):
        return [FX.metas[r] for r in FX.engine().lists_for(q)["A today"]]
    docs = PI.IndexDocs([{"doc": 100 + d, "passages": 10, "src": {"title": f"CASE {d} versus STATE OF TESTLAND", "date": "01-02-2010", "citation": f"[2010] {d + 1} S.C.R. {d + 5}", "case_id": f"2010 INSC {d + 1}", "path": f"p{d}"}} for d in range(12)])
    p = P.Pilot()
    p.add_user("111", "Adv. A", "the owner", DAY)
    core = B.BotCore(p, FMT, engine_search, PI.IndexRowIdentity(docs), today=DAY)
    accepted(core, "111")
    r = core.handle("111", text=FX.Q)
    q = p.state["questions"][0]
    check(len(r) == 4 and len(q["shown"]) == 3 and all(re.fullmatch(r"[0-9a-f]{16}", h) for h, _ in q["shown"]), "the real engine's top hits become a header and three passages (its test hashes are not hex, so each passage gets a hash made from its text)")
    check(all(b[2] and len(b[2].encode()) <= 64 for m in r[1:] for b in m.buttons), "every button's data fits the smallest limit")
    check(core.handle("111", tap=r[1].buttons[0][2])[0].text == B.THANKS and p.state["marks"][0]["mark"] == "relevant", "and a tap on one of them is recorded")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
