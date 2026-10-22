"""Tests for goodlaw/pilot.py: the private pilot's allow-list, the three rules, and the lawyers' marks on passages.
Run: python test_goodlaw_pilot.py
"""
import csv
import json
import os
import tempfile

from goodlaw import cardreader as CR
from goodlaw import chat_format as CF
from goodlaw import pilot as P
from goodlaw import register as R

FAILURES = []
H1, H2 = "3c1126abebc40570", "7aca799ec25ca0c7"


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


def ready(keep=False, path=None):
    p = P.Pilot(path, keep_question_text=keep)
    p.add_user("111", "Adv. A", "the owner", "2026-11-01")
    p.add_user("222", "Adv. B", "the owner", "2026-11-01")
    p.accept("111", "2026-11-02")
    p.accept("222", "2026-11-02")
    return p


# ---- the rules shown to a new user -----------------------------------------------------------------------------------------------------------------------------------------
print("the rules")
check(not CF.wording_violations(P.ONBOARDING + P.NOT_ON_LIST + P.SWITCHED_OFF + P.FEEDBACK_PROMPT), "none of the pilot's own messages claims a case is good law")
check("client names or facts" in P.ONBOARDING and "not end-to-end encrypted" in P.ONBOARDING and "independently verified" in P.ONBOARDING and P.ONBOARDING.rstrip().endswith("\"I understand\" to start."), "the first message carries the three rules and asks for a reply")

# ---- who may take part -----------------------------------------------------------------------------------------------------------------------------------------------------------
print("the allow-list")
p = P.Pilot()
check(p.gate("111") == (False, "not_on_list", P.NOT_ON_LIST), "a stranger is told it is a private test, and nothing more")
check(raises(P.PilotError, p.add_user, "", "x", "o") and raises(P.PilotError, p.add_user, "9", "", "o") and raises(P.PilotError, p.add_user, "9", "x", " "), "a user needs an id, a label and the name of who added them")
p.add_user("111", "Adv. A", "the owner", "2026-11-01")
check(raises(P.PilotError, p.add_user, "111", "Adv. Z", "the owner") and raises(P.PilotError, p.add_user, "222", "Adv. A", "the owner"), "an id or a label cannot be used twice")
ok, reason, text = p.gate("111")
check((ok, reason) == (False, "rules_not_accepted") and text == P.ONBOARDING, "a user on the list who has not accepted the rules gets the rules, not an answer")
check(raises(P.PilotError, p.start_question, "111", "a question"), "and cannot ask a question yet")
p.accept("111", "2026-11-02")
check(p.gate("111") == (True, "ok", ""), "after accepting, the gate opens")
p.set_active("111", False, "the owner", "2026-11-03")
check(p.gate("111")[:2] == (False, "switched_off") and raises(P.PilotError, p.accept, "111") and raises(P.PilotError, p.set_active, "111", True, " "), "switching a user off closes it, and switching needs a name")
p.set_active("111", True, "the owner", "2026-11-04")
check(p.gate("111")[:2] == (True, "ok") and len(p.users()["111"]["history"]) == 2, "switching back on restores it, and the history is kept")
p.rules_version = "v2"
check(p.gate("111")[:2] == (False, "rules_not_accepted"), "when the rules change, everyone accepts again")

# ---- the buttons ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("the buttons")
d = P.callback_data("q12", H1, "misleading")
check(d == f"m|q12|{H1}|m" and len(d.encode()) <= 64 and P.parse_callback(d) == ("q12", H1, "misleading"), "a button's data is short and decodes to what it was made from")
check(all(len(P.callback_data("q999999999", "a" * 40, mk).encode()) <= P.MAX_CALLBACK_BYTES for mk in P.MARKS) and raises(P.PilotError, P.callback_data, "q9999999999", H1, "relevant") and raises(P.PilotError, P.callback_data, "q1", "a" * 41, "relevant"),
      "even the longest id and hash fit in 64 bytes, and an id or hash longer than the format allows is refused")
bad = [None, 5, "", "m|q1|" + H1 + "|x", "m|q1|" + H1 + "|rr", "x|q1|" + H1 + "|r", "m|1|" + H1 + "|r", "m|q1|ZZZZ|r", "m|q1|" + H1 + "|r|extra", "m|q1|" + H1.upper() + "|r", "m|q1|" + H1 + "|r" + "0" * 80]
check(all(raises(P.PilotError, P.parse_callback, b) for b in bad), "anything that is not exactly what callback_data writes is refused, not guessed at")
check(raises(P.PilotError, P.callback_data, "q1", H1, "great") and raises(P.PilotError, P.callback_data, "1", H1, "relevant"), "an unknown mark or a malformed id is refused when making the data")
msg = CF.Message("text", buttons=(CF.Button("Read full judgment", "open_url", "https://example.invalid/j"),))
m2 = P.with_feedback(msg, "q5", H1)
check([b.label for b in m2.buttons] == ["Read full judgment", "Relevant", "Not relevant", "Misleading"] and [b.action for b in m2.buttons][1:] == ["mark"] * 3 and msg.buttons[0].label == "Read full judgment" and len(msg.buttons) == 1,
      "the three feedback buttons come after the message's own, and the original message is not changed")
check([P.parse_callback(b.target)[2] for b in m2.buttons[1:]] == list(P.MARKS), "and each carries its own mark")

# ---- questions and marks ---------------------------------------------------------------------------------------------------------------------------------------------------------
print("marking")
p = ready()
q1, q2 = p.start_question("111", "a test question", "2026-11-05"), p.start_question("222", "another", "2026-11-05")
check((q1, q2) == ("q1", "q2") and all(q["text"] is None for q in p.state["questions"]), "questions get short ids, and their text is not kept by default")
p.mark("111", q1, H1, "relevant", doc=100, on="2026-11-06")
check(raises(P.PilotError, p.mark, "222", q1, H1, "relevant"), "a user cannot mark a passage from someone else's question")
check(raises(P.PilotError, p.mark, "111", "q99", H1, "relevant") and raises(P.PilotError, p.mark, "111", q1, H1, "great") and raises(P.PilotError, p.mark, "999", q1, H1, "relevant"), "nor from a question that does not exist, with an unknown mark, or as someone not on the list")
p.mark("111", q1, H1, "misleading", doc=100, note="recites the trial court", on="2026-11-07")
check(len(p.state["marks"]) == 1 and p.state["marks"][0]["mark"] == "misleading" and p.state["marks"][0]["revised"] == 1 and p.state["marks"][0]["note"] == "recites the trial court", "a second mark on the same passage replaces the first and is counted as a revision")
p.mark("111", q1, H2, "not_relevant", doc=101)
p.mark("222", q2, H1, "relevant", doc=100)
qid, h, mk = p.record_tap("222", P.callback_data(q2, H2, "misleading"), doc=102)
check((qid, h, mk) == (q2, H2, "misleading") and len(p.state["marks"]) == 4, "a button tap becomes a mark")
check(raises(P.PilotError, p.record_tap, "222", "m|q1|" + H1 + "|r") and raises(P.PilotError, p.record_tap, "222", "garbage"), "a tap on someone else's question, or a made-up tap, is refused")
p.set_active("222", False, "the owner")
check(raises(P.PilotError, p.mark, "222", q2, H1, "relevant") and len(p.state["marks"]) == 4, "a switched-off user can no longer mark, and what they marked stays")

print("the summary and the sheet")
s = p.summary()
check(s["users"] == 2 and s["accepted_rules"] == 2 and s["questions"] == 2 and s["marks"] == 4 and s["by_mark"] == {"relevant": 1, "not_relevant": 1, "misleading": 2} and s["share_misleading"] == 0.5, "the summary counts users, questions and marks, and the share marked misleading")
check(s["by_user"] == {"Adv. A": {"relevant": 0, "not_relevant": 1, "misleading": 1}, "Adv. B": {"relevant": 1, "not_relevant": 0, "misleading": 1}} and (H1, 100) in s["misleading_to_review"] and (H2, 102) in s["misleading_to_review"],
      "by user, with the misleading passages listed for the reviewer")
check(P.Pilot().summary()["share_misleading"] is None, "with no marks there is no share to report")
with tempfile.TemporaryDirectory() as d:
    out = os.path.join(d, "marks.csv")
    n = p.export_marks_csv(out)
    rows = list(csv.reader(open(out, encoding="utf-8")))
    check(n == 4 and rows[0] == ["question", "user", "passage_hash", "index_doc", "mark", "marked_on", "revised", "note"] and len(rows) == 5, "the sheet has a row per mark")
    text = open(out, encoding="utf-8").read()
    check("111" not in text.replace(H1, "").replace(H2, "") and "Adv. A" in text and "a test question" not in text, "it shows labels, never chat ids, and no question text")
    pk = ready(keep=True)
    qk = pk.start_question("111", "what is the rule on anticipatory bail")
    pk.mark("111", qk, H1, "relevant")
    out2 = os.path.join(d, "marks2.csv")
    pk.export_marks_csv(out2)
    check("question_text" in open(out2, encoding="utf-8").read() and "anticipatory bail" in open(out2, encoding="utf-8").read(), "question text appears only when the owner turned keeping it on")

# ---- the file -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("the file")
with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "store", "pilot.json")
    a = ready(path=path)
    qa = a.start_question("111", "x")
    a.mark("111", qa, H1, "relevant", doc=7)
    b = P.Pilot(path)
    check(b.users().keys() == a.users().keys() and b.gate("111") == (True, "ok", "") and b.summary()["marks"] == 1 and b.start_question("222") == "q2", "a new object reads the same users, acceptances and marks, and carries on numbering questions")
    check(sorted(os.listdir(os.path.dirname(path))) == ["pilot.json"], "and leaves no stray files")

# ---- from a result message to a mark -----------------------------------------------------------------------------------------------------------------------------------------
print("from a result message to a mark")
reg = R.Register([], {"built_on": "2026-10-07"})
cards = CR.load({"cards": []})
f = CF.Formatter(reg, cards, quiet_policy="coverage_note", today="2026-10-22")
p = ready()
qid = p.start_question("111")
msg = P.with_feedback(f.format({"case_name": "Sample v State", "text": "A passage, word for word.", "year": 2015, "para": 4, "page": 2}), qid, H1)
tap = next(b.target for b in msg.buttons if b.label == "Misleading")
check(msg.lines[0].rule == 6 and p.record_tap("111", tap, doc=555) == (qid, H1, "misleading") and p.summary()["misleading_to_review"] == [(H1, 555)], "a formatted message gets its buttons; a tap on Misleading is recorded against the passage and its index doc")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
