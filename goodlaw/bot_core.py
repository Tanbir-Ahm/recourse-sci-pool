"""The pilot bot's core, with no chat service attached: a message (or a button tap) from a user goes in, a list of replies comes out.

It joins the pieces built so far and adds nothing of its own to what is said about a case:
    the allow-list, the three rules and the marks     goodlaw/pilot.py
    a search for the question                         `search_fn` (given; the real one costs Voyage credit and is not wired)
    a search hit -> a named passage                   goodlaw/passage_input.py
    a passage -> a message, warning first             goodlaw/chat_format.py
    saved cases and their alerts                      goodlaw/watchlist.py
    the list as a spreadsheet                         goodlaw/authority_export.py

    core = BotCore(pilot, formatter, search_fn, identity, store_dir="pilot_store", export_dir="pilot_store/exports", daily_question_cap=10)
    replies = core.handle("123456", text="What does the Court say about ...?")      # [Outbound(text, buttons, attachment)]
    replies = core.handle("123456", tap="m|q7|3c1126abebc40570|m")                   # a feedback button
A sender (WhatsApp, Telegram) would pass each incoming message in, send each Outbound out, and attach `attachment` as a file. None exists; nothing here touches a network.

What a user can do: reply "I understand" to the three rules; ask a test question; /watch Name v Name (2018) ; (2018) 17 SCC 627 ; /watchlist ; /export ; /help.
What it will not do (test_goodlaw_bot_core.py checks each): answer anyone who is not on the list, switched on and has accepted the current rules (a stranger gets one neutral line and nothing is recorded);
run a search past a daily limit per user or in all (every search costs money); count a question whose search was unavailable; show a passage's feedback buttons for a passage that was not shown;
put a chat id in anything it sends; say a case is good law in any wording of its own; promise an alert (nothing sends alerts yet).
`search_fn(question)` returns index passage rows ({doc, i, pn, page, section, h, text}); it may raise `SearchUnavailable`, which is answered politely, and any other exception is a bug and is raised.
"""
import dataclasses
import hashlib
import os
import re
from dataclasses import dataclass
from datetime import date

from . import authority_export as AE
from . import chat_format as CF
from . import passage_input as PI
from . import pilot as P
from . import watchlist as W

HELP = ("You can:\n"
        "- ask a test question in plain English (no client names or facts);\n"
        "- /watch Name v Name (2018) ; (2018) 17 SCC 627   to save a case (the year and the citation are optional);\n"
        "- /watchlist   to see your saved cases;\n"
        "- /export   to get your saved cases as a spreadsheet;\n"
        "- tap Relevant, Not relevant or Misleading under a passage to tell us how it did.\n"
        "Nothing here is independently verified. Check every case before you cite it.")
ACCEPTED = "Thank you. Ask your first test question. After each passage, tell us whether it was useful."
THANKS = "Thanks, noted."
NO_PASSAGES = "We found no passages for that question. Try asking it as a plain-English legal question."
SEARCH_DOWN = "The search is not available right now. Nothing was recorded for this question; please try again later."
LIMIT_USER = "You have reached today's limit for the test. Please try again tomorrow."
LIMIT_ALL = "The test has reached its limit for today. Please try again tomorrow."
STALE_TAP = "That button is no longer valid."
EMPTY_WATCHLIST = "Your watchlist is empty. Save a case with /watch Name v Name (2018)."
NO_EXPORT = "Export is not available in this test."
SAVED = "Saved to your watchlist. This is what we know today:"
_WATCH = re.compile(r"^/watch(?:@\w+)?\s+(?P<name>.+?)(?:\s*\((?P<year>(?:18|19|20)\d\d)\))?(?:\s*;\s*(?P<cite>.+))?\s*$", re.S)


class SearchUnavailable(Exception):
    """The search could not be run (no credit left, the service is down). The question is not counted."""


@dataclass(frozen=True)
class Outbound:
    text: str
    buttons: tuple = ()
    attachment: str = None


def _says_understood(text):
    return re.sub(r"[^a-z]", "", (text or "").lower()) == "iunderstand"


class BotCore:
    def __init__(self, pilot, formatter, search_fn, identity, store_dir=None, export_dir=None, daily_question_cap=10, global_daily_cap=100, shown=3, today=None):
        self.pilot, self.formatter, self.search_fn, self.identity = pilot, formatter, search_fn, identity
        self.store_dir, self.export_dir, self.shown, self.today = store_dir, export_dir, shown, today
        self.daily_question_cap, self.global_daily_cap = daily_question_cap, global_daily_cap
        self._watch = {}

    def _day(self, on):
        return str(on or self.today or date.today().isoformat())[:10]

    def _watchlist(self, uid):
        if uid not in self._watch:
            label = self.pilot.users()[uid]["label"]
            path = None
            if self.store_dir:
                slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "user"
                path = os.path.join(self.store_dir, f"watch_{slug}-{hashlib.sha1(uid.encode()).hexdigest()[:6]}.json")
            self._watch[uid] = W.Watchlist(self.formatter, path=path, owner=label)
        return self._watch[uid]

    # ---- one incoming event ----------------------------------------------------------------------------------------------------------------------------------------------
    def handle(self, user_id, text=None, tap=None, on=None):
        uid, day = str(user_id), self._day(on)
        ok, reason, gate_text = self.pilot.gate(uid)
        if not ok:
            if reason == "rules_not_accepted" and tap is None and _says_understood(text):
                self.pilot.accept(uid, day)
                return [Outbound(ACCEPTED)]
            return [Outbound(gate_text)]
        if tap is not None:
            return self._tap(uid, tap, day)
        text = (text or "").strip()
        if not text:
            return [Outbound(HELP)]
        if text.startswith("/"):
            return self._command(uid, text, day)
        return self._question(uid, text, day)

    def _tap(self, uid, data, day):
        try:
            self.pilot.record_tap(uid, data, on=day)
        except P.PilotError:
            return [Outbound(STALE_TAP)]
        return [Outbound(THANKS)]

    # ---- a question ------------------------------------------------------------------------------------------------------------------------------------------------------------
    def _question(self, uid, text, day):
        if self.pilot.questions_on(day, uid) >= self.daily_question_cap:
            return [Outbound(LIMIT_USER)]
        if self.pilot.questions_on(day) >= self.global_daily_cap:
            return [Outbound(LIMIT_ALL)]
        qid = self.pilot.start_question(uid, text, day)
        try:
            hits = list(self.search_fn(text))
        except SearchUnavailable:
            self.pilot.drop_question(qid, uid)
            return [Outbound(SEARCH_DOWN)]
        if not hits:
            return [Outbound(NO_PASSAGES)]
        passages = [PI.passage_from_hit(h, self.identity) for h in hits]
        batch = self.formatter.format_batch(passages, shown=self.shown, max_chars=3400)
        out = [Outbound(batch[0].text)]
        shown = []
        for h, msg in zip(hits[:self.shown], batch[1:]):
            ph = h.get("h") if re.fullmatch(r"[0-9a-f]{8,40}", str(h.get("h") or "")) else hashlib.sha1((h.get("text") or "").encode()).hexdigest()[:16]
            shown.append((ph, int(h["doc"])))
            msg = P.with_feedback(dataclasses.replace(msg, text=msg.text + "\n\n" + P.FEEDBACK_PROMPT), qid, ph)
            out.append(Outbound(msg.text, tuple((b.label, b.action, b.target) for b in msg.buttons)))
        self.pilot.set_shown(qid, shown)
        return out

    # ---- commands --------------------------------------------------------------------------------------------------------------------------------------------------------------
    def _command(self, uid, text, day):
        cmd = text.split(None, 1)[0].lower().split("@")[0]
        if cmd == "/watch":
            return self._cmd_watch(uid, text, day)
        if cmd == "/watchlist":
            return self._cmd_watchlist(uid)
        if cmd == "/export":
            return self._cmd_export(uid, day)
        return [Outbound(HELP)]

    def _cmd_watch(self, uid, text, day):
        m = _WATCH.match(text)
        if not m or len(m.group("name").strip()) < 3:
            return [Outbound("To save a case, write /watch Name v Name (2018) ; (2018) 17 SCC 627 (the year and the citation are optional).")]
        name, year, cite = m.group("name").strip(), (int(m.group("year")) if m.group("year") else None), (m.group("cite") or "").strip() or None
        _, cur = self._watchlist(uid).add(name, year, cite, today=day)
        body = "\n\n".join(CF._line_text(l) for l in cur.lines) or "Nothing to report."
        return [Outbound(f"{SAVED}\n\n{name}\n\n{body}\n\nSilence is not an all-clear.")]

    def _cmd_watchlist(self, uid):
        cases = self._watchlist(uid).cases()
        if not cases:
            return [Outbound(EMPTY_WATCHLIST)]
        rows = []
        for c in cases.values():
            cur = self.formatter.currency(c["name"], c["year"], c["citation"])
            rows.append(f"- {c['label']}: {cur.lines[0].headline if cur.lines else 'No line'}")
        return [Outbound("Your saved cases:\n" + "\n".join(rows) + "\n\nSilence is not an all-clear. Check every case before you cite it.")]

    def _cmd_export(self, uid, day):
        wl = self._watchlist(uid)
        if not wl.cases():
            return [Outbound(EMPTY_WATCHLIST)]
        if not self.export_dir:
            return [Outbound(NO_EXPORT)]
        os.makedirs(self.export_dir, exist_ok=True)
        label = self.pilot.users()[uid]["label"]
        path = os.path.join(self.export_dir, f"authorities_{re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-') or 'user'}_{day}.csv")
        n = AE.export_watchlist(wl, path, exported_on=day)
        return [Outbound(f"Your {n} saved case{'s' if n != 1 else ''} as a spreadsheet. Every row carries its own note about how it was checked.", attachment=path)]
