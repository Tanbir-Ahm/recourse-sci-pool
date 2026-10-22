"""Turns a retrieved passage and what we know about its case into one chat-sized message, with the warning first.

Offline: it reads the Overruled Register (goodlaw/register.py) and the currency cards (goodlaw/cardreader.py) that are already loaded, and writes text. It searches nothing, fetches nothing,
sends nothing and decides nothing about a case: it only words what the register and the cards already say. Nothing is connected to the live site or to any chat service.

    f = Formatter(Register.load(), cardreader.load("cards/currency_cards.json"), quiet_policy="coverage_note")
    msg = f.format({"case_name": "Mohan Lal v State of Punjab", "year": 2018, "citation": "(2018) 17 SCC 627", "court": "Supreme Court", "para": 14, "page": 9, "text": "..."}, intro=True)
    msg.text        # the message; msg.buttons the actions; msg.lines what was said about the case; msg.internal notes for a reviewer, never shown to a user

Which line a case gets (first match decides the main line; a card's warning or caution is added after a register line; a statute note is added last):
  1. a register row confirmed by a person (trust verified or reviewer_confirmed)   RED      "On the Overruled Register", in the register's firm wording
  2. a register row not yet confirmed (candidate)                                  RED      "Reported on the Overruled Register ... not yet confirmed by our reviewer"
  3. the checker's card is ADVERSE_SIGNAL (or a person confirmed it)               RED      "Reported adverse" (or "Adverse, confirmed by our reviewer")
  4. the card is QUESTIONED                                                        AMBER    "Questioned"
  5. the card is quiet (nothing adverse in what we hold)                           GREY     a coverage note, or no line at all, by `quiet_policy`
  6. anything else: no card, too few later judgments, a High Court case, a judgment we do not hold, a case the matcher could not place     OUTLINE  "Not checked by us"
  +  the card says a section it cites was renumbered under the 2023 codes         INFO     one more line
A passage the connector could not attach to a judgment (`identified: False`, see passage_input.py) gets "Not checked by us" with its own body: nothing was looked up, so it must not say "no register entry".
An optional `kind_label` (for example "Appears to record counsel's arguments, not the Court's view") adds one "Passage: ..." line under the case line; it is our wording and goes through the wording guard.

Rules this keeps (test_goodlaw_chat_format.py checks each):
  * a case with a warning never comes out without it, and shortening a long passage never cuts a warning: only the passage is shortened, at a word boundary, and the message says so
  * no line of ours calls a case "good law" or any phrase in cardreader.FORBIDDEN, except the fixed "not a finding" sentence and the register's own "held not to be good law in" (a court's words);
    the passage itself is the judgment's text, shown word for word, and is not checked
  * a weak register match (a bare name) is never worded; it is kept in `internal` for the weekly review. A register row with no wording (unchecked, rejected) is never worded either
  * firm wording only for a row a person confirmed; every other reading says "reported" or "appears" (the register's and the cards' own sentences are used as they are)
  * a missing register or card index is refused, because "no register entry" must not be said about a register that was never loaded

`quiet_policy` has no default on purpose: whether a quiet card gets a grey "no warning found in what we hold" line or no line at all is the owner's open decision (see FOLLOW_UPS.md).
Plain text only: no markup, so the same text goes to WhatsApp or Telegram, and a channel can add its own formatting later.
"""
import datetime
from dataclasses import dataclass, field

from . import cardreader as CR
from .register import TRUST_FIRM

RED, AMBER, GREY, OUTLINE, INFO = "RED", "AMBER", "GREY", "OUTLINE", "INFO"
QUIET_POLICIES = ("coverage_note", "silent")

NOT_CHECKED = "Not checked by us"
NOT_CHECKED_BODY = {
    "default": "No register entry and no check on file for this case. Verify it before you cite it.",
    "NOT_CHECKABLE_HIGH_COURT": "No register entry. This is a High Court decision, and we do not check High Court cases for later treatment. Verify it before you cite it.",
    "INSUFFICIENT": "No register entry. Too few later judgments in our collection cite this case to check it. Verify it before you cite it.",
}
QUIET_HEAD = "No warning found in what we hold"
QUIET_BODY = "This is not a finding that the case is good law."
INTRO_FOOTER = "Results are not independently verified. Check any case before you cite it."
NOT_IDENTIFIED_BODY = ("We could not identify which judgment this passage comes from, so we have not checked it against the register or for later treatment. "
                       "Verify it before you cite it.")
ADVERSE_FALLBACK = "A later judgment may be adverse to this case. Check it before relying on it."
STALE_SENTENCE = "This check was run on {date} and may be out of date."
ALLOWED_FRAGMENTS = (QUIET_BODY, "held not to be good law in")        # the only places our own wording may contain "good law": a refusal to claim it, and a court's holding
QUIET_STATUSES = ("NO_ADVERSE_FOUND", "ADVERSE_SIGNAL", "QUESTIONED")  # a card that checked the case; the last two only when a person cleared them (level 'none')
MIN_PASSAGE = 160
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class WordingError(Exception):
    """Our own wording contained a phrase that claims a case is good law: the message is not built."""


@dataclass(frozen=True)
class Line:
    level: str                         # RED, AMBER, GREY, OUTLINE or INFO
    headline: str
    body: str
    as_of: str = ""                    # ISO date the evidence is as of
    rule: int = 0                      # which rule above produced it
    firm: bool = False                 # True only for a fact a person confirmed


@dataclass(frozen=True)
class Currency:
    lines: tuple = ()
    internal: tuple = ()               # notes for a reviewer: weak matches, rows without wording, withheld notes


@dataclass(frozen=True)
class Button:
    label: str
    action: str                        # open_url, open_judgment or watch
    target: str


@dataclass(frozen=True)
class Message:
    text: str
    lines: tuple = ()
    buttons: tuple = ()
    truncated: bool = False            # the passage was shortened to fit
    over_limit: bool = False           # the warnings and header alone are longer than the limit; nothing was cut
    internal: tuple = ()


def fmt_date(iso):
    d = datetime.date.fromisoformat(str(iso)[:10])
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


def wording_violations(text):
    """Phrases in OUR wording that claim a case is good law (an empty list is fine). Two fixed fragments are allowed."""
    low = (text or "").lower()
    for frag in ALLOWED_FRAGMENTS:
        low = low.replace(frag.lower(), " ")
    return [p for p in CR.FORBIDDEN if p in low]


def _line_text(line):
    body = line.body + (f" As of {fmt_date(line.as_of)}." if line.as_of and line.level != OUTLINE else "")
    return f"{line.headline.upper()}\n{body}"


def _shorten(text, budget):
    """The passage cut at a word boundary within `budget` characters, with a marker; the start of the text is never changed."""
    if len(text) <= budget:
        return text, False
    cut = text[:max(budget - 2, 1)]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-") + " […]", True


def render(passage, currency, intro=False, max_chars=3500, with_watch=False):
    """One message from a passage and a Currency. The passage is {case_name, text, and optionally court, year, para, page, url, doc_id}."""
    name, text = (passage.get("case_name") or "").strip(), (passage.get("text") or "").strip()
    if not name or not text:
        raise ValueError("a passage needs a case_name and its text")
    kind = (passage.get("kind_label") or "").strip().rstrip(".")
    own = "\n\n".join(_line_text(l) for l in currency.lines)
    if intro:
        own = (own + "\n\n" if own else "") + INTRO_FOOTER
    bad = wording_violations(own + " " + kind)
    if bad:
        raise WordingError(f"our wording contains {bad}: nothing was built")
    meta = " · ".join(str(x) for x in (passage.get("court"), passage.get("year"), f"para {passage['para']}" if passage.get("para") else None,
                                        f"page {passage['page']}" if passage.get("page") else None) if x)
    title = name + ("\n" + meta if meta else "") + (f"\nPassage: {kind}." if kind else "")
    head = "\n\n".join(p for p in ("\n\n".join(_line_text(l) for l in currency.lines), title) if p)
    tail = ("\n\n" + INTRO_FOOTER) if intro else ""
    budget = max_chars - len(head) - len(tail) - 6                    # 6: the blank line and the two quote marks
    quoted, truncated = _shorten(text, max(budget, MIN_PASSAGE))
    out = f"{head}\n\n“{quoted}”{tail}"
    buttons = []
    if passage.get("url"):
        buttons.append(Button("Read full judgment", "open_url", passage["url"]))
    elif passage.get("doc_id"):
        buttons.append(Button("Read full judgment", "open_judgment", str(passage["doc_id"])))
    if with_watch:
        buttons.append(Button("Save to watchlist", "watch", name))
    return Message(out, currency.lines, tuple(buttons), truncated, len(out) > max_chars, currency.internal)


class Formatter:
    def __init__(self, register, cards, *, quiet_policy, today=None):
        if register is None or cards is None:
            raise ValueError("a register and a card index are required: 'no register entry' must not be said about a register that was never loaded")
        if quiet_policy not in QUIET_POLICIES:
            raise ValueError(f"quiet_policy must be one of {QUIET_POLICIES}; this is the owner's open decision, so it has no default")
        self.register, self.cards, self.quiet_policy, self.today = register, cards, quiet_policy, today

    def currency(self, case_name, year=None, citation=None):
        reg, lines, internal = self.register, [], []
        matches = reg.lookup_case(case_name, year, citation)
        rows = list({m["row"]["id"]: m["row"] for m in matches if m["strength"] == "strong"}.values())
        for m in matches:
            if m["strength"] != "strong":
                internal.append(f"weak register match to {m['row']['id']} ({m['how']}): listed for review, not worded")
        clause = reg.clause_group(rows) if rows else None
        if rows and not clause:
            internal.append("register row(s) without wording (unchecked or rejected): " + ", ".join(r["id"] for r in rows))
        if clause:
            firm = any(r["trust"] in TRUST_FIRM for r in rows)
            lines.append(Line(RED, "On the Overruled Register" if firm else "Reported on the Overruled Register", clause, reg.meta.get("built_on") or "", 1 if firm else 2, firm))

        card = CR.find(self.cards, case_name=case_name, citation=citation)
        res = CR.for_answer(card, today=self.today)
        status, as_of = res["status"], res["card_generated"] or ""
        stale = (" " + STALE_SENTENCE.format(date=fmt_date(as_of))) if res["stale"] and as_of else ""
        if res["level"] in ("warning", "caution"):
            note = res["user_facing_note"]
            if not note:
                note = ADVERSE_FALLBACK
                internal.append("the card's note was missing or withheld by the wording guard; the fallback sentence was used")
            if res["under_review"]:
                note += " Our reviewer is looking at this case."
            if res["level"] == "warning":
                human = res["decided_by"] != "checker"
                lines.append(Line(RED, "Adverse, confirmed by our reviewer" if human else "Reported adverse", note + stale, as_of, 3, human))
            else:
                lines.append(Line(AMBER, "Questioned", note + stale, as_of, 4))
        elif not lines:
            if status in QUIET_STATUSES:
                if self.quiet_policy == "coverage_note":
                    lines.append(Line(GREY, QUIET_HEAD, QUIET_BODY, as_of, 5))
                else:
                    internal.append("quiet card: no line, by quiet_policy")
            else:
                lines.append(Line(OUTLINE, NOT_CHECKED, NOT_CHECKED_BODY.get(status, NOT_CHECKED_BODY["default"]), "", 6))
        if res["statute_note"]:
            lines.append(Line(INFO, "Section numbers", res["statute_note"], as_of, 7))
        return Currency(tuple(lines), tuple(internal))

    def format(self, passage, intro=False, max_chars=3500, with_watch=False):
        if passage.get("identified") is False:               # the connector could not tell which judgment this is: the register and the cards were never consulted, and the message says so
            cur = Currency((Line(OUTLINE, NOT_CHECKED, NOT_IDENTIFIED_BODY, "", 6),), ("judgment not identified: register and cards not consulted",))
        else:
            cur = self.currency(passage.get("case_name"), passage.get("year"), passage.get("citation"))
        return render(passage, cur, intro=intro, max_chars=max_chars, with_watch=with_watch)

    def format_batch(self, passages, shown=None, max_chars=3500, with_watch=False):
        """A header message, then one message per passage. The header says how many were found and that nothing is independently verified."""
        shown = passages if shown is None else passages[:shown]
        head = (f"Found {len(passages)} passage{'s' if len(passages) != 1 else ''} from Supreme Court judgments. Showing {len(shown)}. "
                "What we know about a case's later treatment comes before its passage. " + INTRO_FOOTER)
        return [Message(head)] + [self.format(p, max_chars=max_chars, with_watch=with_watch) for p in shown]
