"""The private pilot's own bookkeeping: who may take part, that they accepted the three rules, and what they mark on each passage. Offline and independent of any chat service.

The pilot exists to get what the project does not have yet: real lawyers' marks on the passages the search shows (so far there are only AI-reviewer marks, no lawyer). This module holds only the part that
is the same on any channel; a sender, an account and a bot would sit on top of it and are not built.

    pilot = Pilot("pilot_store/pilot.json", keep_question_text=False)
    pilot.add_user("123456", "Adv. A", added_by="the owner")          # the owner decides who is on the list; a user starts with the rules not yet accepted
    ok, reason, text = pilot.gate("123456")                           # not on the list / switched off / rules not accepted -> the message to send instead of an answer
    pilot.accept("123456")                                            # after the user replies "I understand"
    qid = pilot.start_question("123456", text="...")                  # only a test question; the text is kept only if keep_question_text=True
    msg = with_feedback(message, qid, passage_hash)                   # adds Relevant / Not relevant / Misleading buttons to a formatted message
    pilot.record_tap("123456", callback_data)                         # a tap comes back as a short string (at most 64 bytes, the smallest limit among the chat services)
    pilot.summary(); pilot.export_marks_csv("marks.csv")              # for the owner and the reviewer

Rules (test_goodlaw_pilot.py checks each): nobody gets an answer unless they are on the list, switched on and have accepted the current rules; a user can mark only a passage from a question they asked; a
mark is one of three words, and a second mark on the same passage replaces the first; a tap is decoded strictly (a changed or unknown callback is refused, not guessed at); the mark sheet shows labels,
never chat ids, and no question text unless the owner turned that on; nothing here says a case is good law. The file holds chat ids and marks: keep it in a private, git-ignored folder (`pilot_store/`).
A user typing a client's name into a test question cannot be detected here: the first message says not to, and `keep_question_text` is off by default so that such text is not kept.
"""
import csv
import dataclasses
import json
import os
import re
import tempfile
from datetime import date

from . import chat_format as CF

RULES_VERSION = "v1"
MARKS = ("relevant", "not_relevant", "misleading")
_CODE = {"relevant": "r", "not_relevant": "n", "misleading": "m"}
_DECODE = {v: k for k, v in _CODE.items()}
MAX_CALLBACK_BYTES = 64                     # Telegram's limit for a button's data; the other services allow more
FEEDBACK_LABELS = {"relevant": "Relevant", "not_relevant": "Not relevant", "misleading": "Misleading"}

ONBOARDING = ("Welcome to the Recourse test.\n\n"
              "Three rules before you start:\n"
              "1. Test questions only. Do not type client names or facts.\n"
              "2. This chat is not end-to-end encrypted. Treat it as a public place.\n"
              "3. Nothing here is independently verified. Check every case yourself before you cite it.\n\n"
              "Reply \"I understand\" to start.")
NOT_ON_LIST = "This is a private test. Ask the person who invited you to add you."
SWITCHED_OFF = "Your access to this test has been switched off. Ask the person who invited you."
FEEDBACK_PROMPT = "Was this passage useful?"


class PilotError(Exception):
    pass


def _today(on):
    return str(on)[:10] if on else date.today().isoformat()


def callback_data(question_id, passage_hash, mark):
    """The short string a feedback button carries: 'm|<question id>|<passage hash>|<r, n or m>'. Raises if it would not fit in 64 bytes."""
    if mark not in MARKS:
        raise PilotError(f"unknown mark {mark!r}")
    if not re.fullmatch(r"q\d{1,9}", str(question_id)) or not re.fullmatch(r"[0-9a-f]{8,40}", str(passage_hash)):
        raise PilotError("a question id looks like q12 and a passage hash is lowercase hex")
    data = f"m|{question_id}|{passage_hash}|{_CODE[mark]}"
    if len(data.encode()) > MAX_CALLBACK_BYTES:
        raise PilotError(f"the button data is {len(data.encode())} bytes; the limit is {MAX_CALLBACK_BYTES}")
    return data


def parse_callback(data):
    """(question id, passage hash, mark) from a button's data, or PilotError for anything that is not exactly what callback_data writes."""
    if not isinstance(data, str) or len(data.encode()) > MAX_CALLBACK_BYTES:
        raise PilotError("not a feedback tap")
    m = re.fullmatch(r"m\|(q\d{1,9})\|([0-9a-f]{8,40})\|([rnm])", data)
    if not m:
        raise PilotError("not a feedback tap")
    return m.group(1), m.group(2), _DECODE[m.group(3)]


def with_feedback(message, question_id, passage_hash):
    """The message with the three feedback buttons added after its own buttons."""
    extra = tuple(CF.Button(FEEDBACK_LABELS[mk], "mark", callback_data(question_id, passage_hash, mk)) for mk in MARKS)
    return dataclasses.replace(message, buttons=tuple(message.buttons) + extra)


class Pilot:
    def __init__(self, path=None, keep_question_text=False, rules_version=RULES_VERSION):
        self.path, self.keep_question_text, self.rules_version = path, bool(keep_question_text), rules_version
        self.state = {"users": {}, "questions": [], "marks": [], "next_question": 1}
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.state.update(json.load(f))

    def _save(self):
        if not self.path:
            return
        d = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=1, sort_keys=True, ensure_ascii=False)
        os.replace(tmp, self.path)

    # ---- who may take part -------------------------------------------------------------------------------------------------------------------------------------------------
    def add_user(self, user_id, label, added_by, on=None):
        user_id, label = str(user_id).strip(), (label or "").strip()
        if not user_id or not label or not (added_by or "").strip():
            raise PilotError("a user needs an id, a label (not a real name is fine) and who added them")
        if user_id in self.state["users"]:
            raise PilotError("that user is already on the list")
        if any(u["label"] == label for u in self.state["users"].values()):
            raise PilotError("that label is already used")
        self.state["users"][user_id] = {"label": label, "added_by": added_by.strip(), "added_on": _today(on), "active": True, "accepted_on": None, "accepted_version": None}
        self._save()

    def set_active(self, user_id, active, by, on=None):
        if not (by or "").strip():
            raise PilotError("switching a user on or off needs the name of who did it")
        u = self._user(user_id)
        u["active"] = bool(active)
        u.setdefault("history", []).append({"on": _today(on), "by": by.strip(), "active": bool(active)})
        self._save()

    def _user(self, user_id):
        u = self.state["users"].get(str(user_id))
        if not u:
            raise PilotError("that user is not on the list")
        return u

    def users(self):
        return {uid: dict(u) for uid, u in self.state["users"].items()}

    def gate(self, user_id):
        """(allowed, reason, text to send instead of an answer). reason: ok, not_on_list, switched_off or rules_not_accepted."""
        u = self.state["users"].get(str(user_id))
        if not u:
            return False, "not_on_list", NOT_ON_LIST
        if not u["active"]:
            return False, "switched_off", SWITCHED_OFF
        if u["accepted_version"] != self.rules_version:
            return False, "rules_not_accepted", ONBOARDING
        return True, "ok", ""

    def accept(self, user_id, on=None):
        u = self._user(user_id)
        if not u["active"]:
            raise PilotError("a switched-off user cannot accept the rules")
        u.update(accepted_on=_today(on), accepted_version=self.rules_version)
        self._save()

    # ---- questions and marks -----------------------------------------------------------------------------------------------------------------------------------------------
    def start_question(self, user_id, text=None, on=None):
        ok, reason, _ = self.gate(user_id)
        if not ok:
            raise PilotError(f"this user cannot ask a question ({reason})")
        qid = f"q{self.state['next_question']}"
        self.state["next_question"] += 1
        self.state["questions"].append({"id": qid, "user": str(user_id), "on": _today(on), "text": text if (self.keep_question_text and text) else None})
        self._save()
        return qid

    def set_shown(self, question_id, items):
        """Record which passages were shown for a question: [(passage hash, index doc)]. From then on only these can be marked, and a tap finds its doc here."""
        q = next((q for q in self.state["questions"] if q["id"] == question_id), None)
        if q is None:
            raise PilotError("no such question")
        q["shown"] = [[h, d] for h, d in items]
        self._save()

    def drop_question(self, question_id, user_id):
        """Forget a question that was started but could not be answered (the search was unavailable), so it does not count towards a daily limit. Refused once anything was marked."""
        q = next((q for q in self.state["questions"] if q["id"] == question_id), None)
        if q is None or q["user"] != str(user_id):
            raise PilotError("no such question for this user")
        if any(m["question"] == question_id for m in self.state["marks"]):
            raise PilotError("a question with marks cannot be dropped")
        self.state["questions"].remove(q)
        self._save()

    def questions_on(self, day, user_id=None):
        return sum(1 for q in self.state["questions"] if q["on"] == _today(day) and (user_id is None or q["user"] == str(user_id)))

    def mark(self, user_id, question_id, passage_hash, mark, doc=None, note=None, on=None):
        if mark not in MARKS:
            raise PilotError(f"unknown mark {mark!r}; use one of {MARKS}")
        ok, reason, _ = self.gate(user_id)
        if not ok:
            raise PilotError(f"this user cannot mark a passage ({reason})")
        q = next((q for q in self.state["questions"] if q["id"] == question_id), None)
        if q is None or q["user"] != str(user_id):
            raise PilotError("a user can mark only a passage from a question they asked")
        if q.get("shown") is not None:
            shown = {h: d for h, d in q["shown"]}
            if passage_hash not in shown:
                raise PilotError("that passage was not shown for this question")
            doc = shown[passage_hash] if doc is None else doc
        existing = next((m for m in self.state["marks"] if m["question"] == question_id and m["passage"] == passage_hash), None)
        if existing:
            existing.update(mark=mark, note=note, on=_today(on), revised=existing.get("revised", 0) + 1)
        else:
            self.state["marks"].append({"question": question_id, "user": str(user_id), "passage": passage_hash, "doc": doc, "mark": mark, "note": note, "on": _today(on), "revised": 0})
        self._save()

    def record_tap(self, user_id, data, doc=None, on=None):
        """A feedback button tap -> a mark. Refuses anything that is not a tap this module wrote."""
        qid, h, mk = parse_callback(data)
        self.mark(user_id, qid, h, mk, doc=doc, on=on)
        return qid, h, mk

    # ---- for the owner and the reviewer ----------------------------------------------------------------------------------------------------------------------------
    def summary(self):
        marks, label = self.state["marks"], {uid: u["label"] for uid, u in self.state["users"].items()}
        by_mark = {mk: sum(1 for m in marks if m["mark"] == mk) for mk in MARKS}
        by_user = {}
        for m in marks:
            by_user.setdefault(label.get(m["user"], "?"), {mk: 0 for mk in MARKS})[m["mark"]] += 1
        n = len(marks)
        return {"users": len(label), "accepted_rules": sum(1 for u in self.state["users"].values() if u["accepted_version"] == self.rules_version), "questions": len(self.state["questions"]),
                "marks": n, "by_mark": by_mark, "share_misleading": round(by_mark["misleading"] / n, 4) if n else None, "by_user": by_user,
                "misleading_to_review": sorted({(m["passage"], m["doc"]) for m in marks if m["mark"] == "misleading"}, key=lambda x: (str(x[1]), x[0]))}

    def export_marks_csv(self, path):
        """One row per mark: the question id, the user's label (never the chat id), the passage hash, the index doc, the mark and its date. No question text unless it was kept on purpose."""
        label = {uid: u["label"] for uid, u in self.state["users"].items()}
        text = {q["id"]: q["text"] for q in self.state["questions"]}
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["question", "user", "passage_hash", "index_doc", "mark", "marked_on", "revised", "note"] + (["question_text"] if self.keep_question_text else []))
            for m in self.state["marks"]:
                w.writerow([m["question"], label.get(m["user"], "?"), m["passage"], m["doc"] if m["doc"] is not None else "", m["mark"], m["on"], m.get("revised", 0), m.get("note") or ""]
                           + ([text.get(m["question"]) or ""] if self.keep_question_text else []))
        return len(self.state["marks"])
