"""The watchlist: cases a lawyer saved, re-checked against the Overruled Register and the currency cards, with DRAFT alerts that a person approves before anything goes out.

Offline: it calls goodlaw/chat_format.py's `Formatter.currency` (so it says exactly what a result message says), keeps a small JSON file, and writes draft texts. It schedules nothing, sends nothing, and
creates no routine; whoever runs `run()` (a person, or a routine the owner has approved) decides when. Nothing is connected to the site or to any chat service.

    wl = Watchlist(formatter, path="watchlist_store/alice.json", owner="Alice's chamber")
    key, current = wl.add("Mohan Lal v State of Punjab", 2018, "(2018) 17 SCC 627")      # shows what is known today; this is the baseline, not an alert
    result = wl.run()                                 # after the monthly refresh: compares each saved case with its last snapshot -> draft alerts
    for a in wl.pending(): ...                        # a person reads the draft; wl.approve(a["id"], "Mr. Advocate") or wl.reject(...)
    for a in wl.outbox(): ...                         # approved drafts, ready for a sender that does not exist yet; wl.mark_sent(a["id"]) afterwards

What counts as a change worth a message (warnings only; the line keys come from chat_format.Line.key):
    NEW_WARNING        a warning or caution that was not there before (a register row, the checker's card, a person's confirmation of a card)
    WARNING_CONFIRMED  the same warning, now confirmed by a person (a candidate register row confirmed; a card flag confirmed in review)
    WARNING_CHANGED    a warning of the same kind with different grounds (a caution that became adverse, a register row set that changed)
    WARNING_WITHDRAWN  a warning we showed has gone (a flag a person cleared, a register row rejected): worded as a correction, "not an all-clear"
What never produces a message: a case that became "quiet" or "not checked" without having had a warning, a card that appeared with nothing adverse, a rewording of the same warning, or an older card.
Silence is not news, and we never say a case is fine: there is no "all clear" alert, and every draft ends by saying that silence is not one.

Rules this keeps (test_goodlaw_watchlist.py checks each): the first look at a saved case is a baseline, not an alert; an alert is created once (its id comes from the case, the kind, the lines involved
and the day); a draft carries no "good law" claim (the formatter's wording guard runs on it); only a draft can be approved or rejected, only an approved one marked sent, and approving needs a
reviewer's name. The file holds the case names a lawyer saved (public names, but a private interest list) and no client information: keep it in a private, git-ignored folder.
"""
import hashlib
import json
import os
import re
import tempfile
from datetime import date

from . import chat_format as CF
from . import cites as C

NEW_WARNING, WARNING_CONFIRMED, WARNING_CHANGED, WARNING_WITHDRAWN = "NEW_WARNING", "WARNING_CONFIRMED", "WARNING_CHANGED", "WARNING_WITHDRAWN"
KINDS = (NEW_WARNING, WARNING_CONFIRMED, WARNING_CHANGED, WARNING_WITHDRAWN)
STATUSES = ("draft", "approved", "rejected", "sent")
HEADLINES = {
    NEW_WARNING: "New warning on a case you saved",
    WARNING_CONFIRMED: "A warning on a case you saved has been confirmed by our reviewer",
    WARNING_CHANGED: "The warning on a case you saved has changed",
    WARNING_WITHDRAWN: "A warning we gave on a case you saved no longer applies (a correction, not an all-clear)",
}
FOOTER = "We only message you when something changes against a case you saved. Silence is not an all-clear."
WITHDRAWN_NOTE = "That warning no longer applies after a review or a change in our records. This is a correction, not an all-clear: it says nothing about whether the case is still reliable."


def _today(today):
    return str(today)[:10] if today else date.today().isoformat()


def _squash(s):
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\b(?:versus|vs\.?|v\.?)\b", " v ", (s or "").lower()))


def watch_key(name, year=None, citation=None):
    """A stable key for a saved case: its first reported citation if it has one, else its squashed name and year."""
    keys = C.cite_keys(citation or "")
    return keys[0] if keys else f"name:{_squash(name)}:{year or ''}"


def _lines(currency):
    """The warning and caution lines of a Currency, by key."""
    return {l.key: {"level": l.level, "headline": l.headline, "body": l.body, "firm": l.firm, "as_of": l.as_of, "rule": l.rule}
            for l in currency.lines if l.level in (CF.RED, CF.AMBER) and l.key}


def _firmer(old_key, new_key):
    """The same grounds, now confirmed by a person (candidate -> firm, checker -> human)."""
    return old_key.rsplit(":", 1)[0] == new_key.rsplit(":", 1)[0] and old_key.endswith((":candidate", ":checker")) and new_key.endswith((":firm", ":human"))


def diff_warnings(old, new):
    """[(kind, new line or None, old line or None, added key, removed key)] between two {key: line} snapshots of one case."""
    added = [k for k in new if k not in old]
    removed = [k for k in old if k not in new]
    out = []
    for a in added:
        fam = a.split(":")[0]
        match = next((r for r in removed if r.split(":")[0] == fam), None)
        if match:
            removed.remove(match)
            out.append((WARNING_CONFIRMED if _firmer(match, a) else WARNING_CHANGED, new[a], old[match], a, match))
        else:
            out.append((NEW_WARNING, new[a], None, a, None))
    out += [(WARNING_WITHDRAWN, None, old[r], None, r) for r in removed]
    return out


def _line_text(line):
    body = line["body"] + (f" As of {CF.fmt_date(line['as_of'])}." if line.get("as_of") else "")
    return f"{line['headline'].upper()}\n{body}"


class WatchlistError(Exception):
    pass


class Watchlist:
    def __init__(self, formatter, path=None, owner=""):
        self.formatter, self.path = formatter, path
        self.state = {"owner": owner, "cases": {}, "alerts": []}
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

    def _snapshot(self, currency, today):
        return {"taken": today, "lines": _lines(currency)}

    # ---- the saved cases ---------------------------------------------------------------------------------------------------------------------------------------------------
    def add(self, name, year=None, citation=None, label=None, today=None):
        """Save a case. Returns (key, the Currency as it stands now). What is known today is the baseline: it is shown to the lawyer now and is not an alert."""
        if not (name or "").strip():
            raise WatchlistError("a case needs a name")
        today = _today(today if today else self.formatter.today)
        key = watch_key(name, year, citation)
        current = self.formatter.currency(name, year, citation)
        if key not in self.state["cases"]:
            self.state["cases"][key] = {"name": name, "year": year, "citation": citation, "label": label or name, "added": today, "snapshot": self._snapshot(current, today)}
            self._save()
        return key, current

    def remove(self, key):
        if key not in self.state["cases"]:
            raise WatchlistError("that case is not on the watchlist")
        del self.state["cases"][key]
        self._save()

    def cases(self):
        return dict(self.state["cases"])

    # ---- the check ---------------------------------------------------------------------------------------------------------------------------------------------------------
    def run(self, today=None):
        """Compare every saved case with its last snapshot and write draft alerts for what changed. Safe to run twice: the second run finds nothing new."""
        today = _today(today if today else self.formatter.today)
        res = {"date": today, "checked": 0, "unchanged": 0, "baselined": 0, "alerts": [], "cards_older_than_limit": 0}
        for key, c in self.state["cases"].items():
            cur = self.formatter.currency(c["name"], c["year"], c["citation"])
            res["checked"] += 1
            res["cards_older_than_limit"] += 1 if any(CF.STALE_SENTENCE.split("{")[0].strip() in l.body for l in cur.lines) else 0
            new, old = self._snapshot(cur, today), c.get("snapshot")
            c["snapshot"] = new
            if old is None:
                res["baselined"] += 1
                continue
            events = diff_warnings(old["lines"], new["lines"])
            if not events:
                res["unchanged"] += 1
            for kind, nl, ol, added, removed in events:
                alert = self._draft(key, c, kind, nl, ol, added, removed, today)
                if alert:
                    res["alerts"].append(alert)
        self._save()
        return res

    def _draft(self, key, case, kind, new_line, old_line, added, removed, today):
        aid = hashlib.sha1("|".join([key, kind, added or "", removed or "", today]).encode()).hexdigest()[:12]
        if any(a["id"] == aid for a in self.state["alerts"]):
            return None
        parts = [f"WATCHLIST ALERT: {HEADLINES[kind]}", case["label"]]
        if kind == WARNING_WITHDRAWN:
            parts.append("We previously warned:\n" + _line_text(old_line) + "\n\n" + WITHDRAWN_NOTE)
        else:
            parts.append(_line_text(new_line))
            if kind == WARNING_CHANGED:
                parts.append("This replaces an earlier warning:\n" + _line_text(old_line))
        parts.append(FOOTER)
        text = "\n\n".join(parts)
        bad = CF.wording_violations(text)
        if bad:
            raise CF.WordingError(f"the draft alert contains {bad}: nothing was written")
        alert = {"id": aid, "case_key": key, "label": case["label"], "kind": kind, "created": today, "status": "draft", "text": text, "keys": {"added": added, "removed": removed},
                 "reviewer": None, "decided_on": None, "note": None}
        self.state["alerts"].append(alert)
        return alert

    # ---- a person decides ------------------------------------------------------------------------------------------------------------------------------------------------
    def _find(self, alert_id):
        for a in self.state["alerts"]:
            if a["id"] == alert_id:
                return a
        raise WatchlistError("no such alert")

    def pending(self):
        return [a for a in self.state["alerts"] if a["status"] == "draft"]

    def outbox(self):
        return [a for a in self.state["alerts"] if a["status"] == "approved"]

    def approve(self, alert_id, reviewer, on=None):
        if not (reviewer or "").strip():
            raise WatchlistError("approving needs the reviewer's name")
        a = self._find(alert_id)
        if a["status"] != "draft":
            raise WatchlistError(f"only a draft can be approved (this one is {a['status']})")
        a.update(status="approved", reviewer=reviewer.strip(), decided_on=_today(on))
        self._save()
        return a

    def reject(self, alert_id, reviewer, note=None, on=None):
        if not (reviewer or "").strip():
            raise WatchlistError("rejecting needs the reviewer's name")
        a = self._find(alert_id)
        if a["status"] != "draft":
            raise WatchlistError(f"only a draft can be rejected (this one is {a['status']})")
        a.update(status="rejected", reviewer=reviewer.strip(), decided_on=_today(on), note=note)
        self._save()
        return a

    def mark_sent(self, alert_id, on=None):
        a = self._find(alert_id)
        if a["status"] != "approved":
            raise WatchlistError(f"only an approved alert can be marked sent (this one is {a['status']})")
        a.update(status="sent", note=f"sent {_today(on)}")
        self._save()
        return a
