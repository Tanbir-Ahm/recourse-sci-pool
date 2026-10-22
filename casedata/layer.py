"""The layer the product talks to: five calls over any adapter, with a saved copy, a spending cap and a ledger.

    layer = CaseDataLayer(adapter, daily_cap_rs=20, store_dir="casedata_store")      # store_dir=None keeps everything in memory (tests)
    layer.track("DLND020047882015", "Sharma bail")
    layer.get_case(id)                       # the standard record, from our saved copy if it is recent enough, else bought; always FRESH, STALE or FAILED, never an exception for a
                                             #   source that is down or a cap that is reached (the record says so in `note`)
    layer.check_listings(ids, "2026-10-23")  # LISTED, NOT_LISTED or UNKNOWN per case (UNKNOWN: the source does not cover it, which is not the same as not listed)
    layer.refresh(ids)                       # ask the source to re-collect, then save the new copy; per-case REFRESHED or FAILED; a failure flags the case STALE
    layer.get_order(id, order_ref)           # the text of one order, bought once and kept
    layer.what_changed(since)                # events found since then (date changed, new order, listed, disposed, update failed ...)
    layer.plan_night(for_date) / run_night(for_date, plan_id)       # a dry run, then the same plan run for real

Guards (the pattern of goodlaw/ik.py, smaller):
  * every call that spends is checked against `daily_cap_rs` BEFORE it is sent, and the ledger line is written before the call and its outcome after; a call with no recorded result
    counts as spent; only a call that never left (`AdapterDown`) or an adapter error marked `charged=False` counts nothing; a batch that partly fails counts in full
  * a file named CASEDATA_STOP in `store_dir` refuses every spending call (reads of the saved copy still work)
  * a case whose update failed is not retried by a read for RETRY_AFTER_MINUTES, so a broken case cannot drain the cap
  * an adapter exception that is not an `AdapterError` is a bug: it is recorded as "unknown" (counted as spent) and raised, never swallowed
  * the ledger, the events and every message carry a case only as nickname and last four digits; the saved state holds full case numbers and order text, so `store_dir` must be a private,
    git-ignored folder
FRESH means "we fetched it within max_age_hours", not "the court's latest entry is in it": a source may itself hold an old copy until it is refreshed.
"""
import dataclasses
import hashlib
import json
import math
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import date as _date, datetime, timedelta, timezone

from . import adapter as A
from . import events as E
from .record import CaseRecord, Listing, FRESH, STALE, FAILED, is_cnr, iso_date, last4

STOP_FILE = "CASEDATA_STOP"
RETRY_AFTER_MINUTES = 60
LISTED, NOT_LISTED, UNKNOWN = "LISTED", "NOT_LISTED", A.UNKNOWN
COUNTED = ("pending", "ok", "error", "unknown")        # ledger outcomes that count as money spent


class LayerError(Exception):
    pass


class BudgetError(LayerError):
    """The call would take today's spending past the cap; nothing was sent."""


class StoppedError(LayerError):
    """The stop file is present; nothing was sent."""


class PlanError(LayerError):
    """run_night was given a plan id that is not today's plan."""


@dataclass(frozen=True)
class ListingResult:
    case_id: str
    status: str                    # LISTED, NOT_LISTED or UNKNOWN
    listing: object
    on_date: str
    checked_at: str
    source: str


@dataclass(frozen=True)
class OrderText:
    case_id: str
    ref: str
    date: str
    text: str
    source: str
    fetched_at: str
    paid_rs: float


@dataclass(frozen=True)
class Plan:
    for_date: str
    horizon_days: int
    steps: tuple                   # (call kind, number of cases)
    est_cost: float                # from the saved copies: which cases look due
    max_cost: float                # every tracked case listed, refreshed and fetched
    plan_id: str


def _parse(s):
    return datetime.fromisoformat(s)


class CaseDataLayer:
    def __init__(self, adapter, daily_cap_rs, store_dir=None, clock=None, max_age_hours=24):
        if isinstance(daily_cap_rs, bool) or not isinstance(daily_cap_rs, (int, float)) or not math.isfinite(daily_cap_rs) or daily_cap_rs < 0:
            raise ValueError("daily_cap_rs must be a finite number of rupees, 0 or more")
        self.adapter = adapter
        self.daily_cap_rs = float(daily_cap_rs)
        self.max_age_hours = max_age_hours
        self.store_dir = store_dir
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._state = {"tracked": {}, "cases": {}, "listings": {}, "failed": {}, "events": [], "orders": {}}
        self._ledger = []
        if store_dir:
            os.makedirs(store_dir, exist_ok=True)
            self._load()

    # ---- time, saving, ledger -------------------------------------------------------------------------------------------------------------------------------------------------------
    def _now(self):
        t = self._clock()
        if t.tzinfo is None:
            raise ValueError("the clock must return an aware datetime")
        return t.astimezone(timezone.utc)

    def _stamp(self):
        return self._now().isoformat(timespec="seconds")

    def _path(self, name):
        return os.path.join(self.store_dir, name)

    def _load(self):
        if os.path.exists(self._path("state.json")):
            with open(self._path("state.json"), encoding="utf-8") as f:
                self._state.update(json.load(f))
        if os.path.exists(self._path("ledger.jsonl")):
            with open(self._path("ledger.jsonl"), encoding="utf-8") as f:
                self._ledger = [json.loads(line) for line in f if line.strip()]

    def _save(self):
        if not self.store_dir:
            return
        fd, tmp = tempfile.mkstemp(dir=self.store_dir, prefix=".tmp-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=1, sort_keys=True)
        os.replace(tmp, self._path("state.json"))

    def _log(self, row):
        self._ledger.append(row)
        if self.store_dir:
            with open(self._path("ledger.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(row, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())

    def spent_today(self):
        today = self._now().date().isoformat()
        rows = {}
        for r in self._ledger:
            rows.setdefault(r["id"], {}).update(r)
        return round(sum(r["cost"] for r in rows.values() if r.get("day") == today and r.get("outcome") in COUNTED), 4)

    def _guard(self, cost):
        if self.store_dir and os.path.exists(self._path(STOP_FILE)):
            raise StoppedError(f"{STOP_FILE} is present: nothing is bought")
        if self.spent_today() + cost > self.daily_cap_rs + 1e-9:
            raise BudgetError(f"today's cap of Rs {self.daily_cap_rs:g} would be passed (spent Rs {self.spent_today():g}, this call Rs {cost:g})")

    def _spend(self, kind, n, call):
        """Check the cap, write the attempt, make the call, write its outcome. Returns (what the call returned, rupees counted)."""
        cost = round(self.adapter.price(kind, n), 4)
        self._guard(cost)
        row_id = uuid.uuid4().hex
        self._log({"id": row_id, "at": self._stamp(), "day": self._now().date().isoformat(), "call": kind, "n": n, "cost": cost, "outcome": "pending"})
        try:
            out = call()
        except A.AdapterError as e:
            self._log({"id": row_id, "at": self._stamp(), "outcome": "error" if e.charged else "notsent"})
            raise
        except BaseException:
            self._log({"id": row_id, "at": self._stamp(), "outcome": "unknown"})
            raise
        self._log({"id": row_id, "at": self._stamp(), "outcome": "ok"})
        return out, cost

    # ---- which cases --------------------------------------------------------------------------------------------------------------------------------------------------------------
    def track(self, case_id, nickname):
        if not is_cnr(case_id):
            raise ValueError("not a case number record (4 capital letters then 12 digits)")
        nickname = (nickname or "").strip()
        if not nickname:
            raise ValueError("a nickname is needed")
        self._state["tracked"][case_id] = nickname
        self._save()

    def untrack(self, case_id):
        """Forget the case: its saved copy, listing, failure flag, order texts and events go with it."""
        self._need(case_id)
        s = self._state
        for k in ("tracked", "cases", "listings", "failed"):
            s[k].pop(case_id, None)
        s["orders"] = {k: v for k, v in s["orders"].items() if not k.startswith(case_id + "|")}
        s["events"] = [e for e in s["events"] if e["case_id"] != case_id]
        self._save()

    def tracked(self):
        return dict(self._state["tracked"])

    def _need(self, case_id):
        if case_id not in self._state["tracked"]:
            raise KeyError(f"the case ending {str(case_id)[-4:]} is not tracked")

    def label(self, case_id):
        self._need(case_id)
        return f"{self._state['tracked'][case_id]} · …{last4(case_id)}"

    def _scrub(self, text):
        """Replace any tracked full case number in a message from outside with its short form."""
        text = str(text)
        for cid in self._state["tracked"]:
            text = text.replace(cid, "…" + last4(cid))
        return text[:200]

    # ---- reading the saved copy -----------------------------------------------------------------------------------------------------------------------------------------------------
    def _saved(self, case_id):
        d = self._state["cases"].get(case_id)
        return CaseRecord.from_dict(d) if d else None

    def _listing(self, case_id):
        d = self._state["listings"].get(case_id)
        return Listing(**d) if d else None

    def _age_hours(self, rec):
        return (self._now() - _parse(rec.fetched_at)).total_seconds() / 3600

    def _view(self, case_id, extra_note="", limit=None):
        """The record as the product sees it: nickname, listing, and an honest freshness (judged against `limit` hours, default the layer's)."""
        limit = self.max_age_hours if limit is None else limit
        nick = self._state["tracked"][case_id]
        rec = self._saved(case_id)
        failed = self._state["failed"].get(case_id)
        failure = f"The last update failed ({failed['at']}): {failed['note']}" if failed else ""
        if rec is None:
            return CaseRecord(case_id, nickname=nick, freshness=FAILED, note=" ".join(n for n in (extra_note, failure) if n) or "Nothing has been fetched for this case yet.")
        freshness, note = FRESH, ""
        age = self._age_hours(rec)
        if failed:
            freshness, note = STALE, failure
        elif age > limit:
            freshness, note = STALE, f"Last updated {int(age)} hours ago."
        if extra_note:
            freshness, note = STALE, (extra_note + " " + note).strip()
        return dataclasses.replace(rec, nickname=nick, listing=self._listing(case_id) or rec.listing, freshness=freshness, note=note)

    # ---- the five calls -------------------------------------------------------------------------------------------------------------------------------------------------------------
    def get_case(self, case_id, max_age_hours=None):
        self._need(case_id)
        limit = self.max_age_hours if max_age_hours is None else max_age_hours
        rec, failed = self._saved(case_id), self._state["failed"].get(case_id)
        if rec is not None and not failed and self._age_hours(rec) <= limit:
            return self._view(case_id, limit=limit)
        if failed and (self._now() - _parse(failed["at"])) < timedelta(minutes=RETRY_AFTER_MINUTES):
            return self._view(case_id, limit=limit)
        try:
            self._fetch_and_save(case_id)
        except A.AdapterError as e:
            self._mark_failed(case_id, str(e))
        except LayerError as e:
            return self._view(case_id, extra_note=f"Not updated: {e}", limit=limit)
        return self._view(case_id, limit=limit)

    def check_listings(self, case_ids, on_date):
        on_date = iso_date(on_date)
        ids = list(dict.fromkeys(case_ids))
        for i in ids:
            self._need(i)
        if not ids:
            return {}
        raw, _ = self._spend("listing", len(ids), lambda: self.adapter.check_listings(ids, on_date))
        at, out = self._stamp(), {}
        for i in ids:
            v = raw.get(i, UNKNOWN)
            if v is None or isinstance(v, Listing) and v.date == on_date:
                new, status = (v, LISTED) if v is not None else (None, NOT_LISTED)
                old = self._listing(i)
                for ev in E.listing_events(old, new, on_date, i, self.label(i), at):
                    self._state["events"].append(ev.to_dict())
                if new is not None:
                    self._state["listings"][i] = dataclasses.asdict(new)
                elif old is not None and old.date == on_date:
                    self._state["listings"].pop(i)
                out[i] = ListingResult(i, status, new, on_date, at, self.adapter.name)
            else:                                           # UNKNOWN, or an answer for another day: we learned nothing
                out[i] = ListingResult(i, UNKNOWN, None, on_date, at, self.adapter.name)
        self._save()
        return out

    def refresh(self, case_ids):
        ids = list(dict.fromkeys(case_ids))
        for i in ids:
            self._need(i)
        if not ids:
            return {}
        self._guard(self.adapter.price("refresh", len(ids)) + self.adapter.price("case", len(ids)))       # the whole batch must fit before anything is sent
        status = {}
        try:
            reasons, _ = self._spend("refresh", len(ids), lambda: self.adapter.refresh(ids))
        except A.AdapterError as e:                         # the source is down or refused the batch: flag every case and stop
            for i in ids:
                self._mark_failed(i, str(e))
                status[i] = "FAILED"
            return status
        for n, i in enumerate(ids):
            if reasons.get(i):
                self._mark_failed(i, str(reasons[i]))
                status[i] = "FAILED"
                continue
            try:
                self._fetch_and_save(i)
                status[i] = "REFRESHED"
            except A.AdapterDown as e:                      # stop on the first outage: the rest are not tried
                for j in ids[n:]:
                    self._mark_failed(j, str(e))
                    status[j] = "FAILED"
                break
            except A.AdapterError as e:
                self._mark_failed(i, str(e))
                status[i] = "FAILED"
        return status

    def get_order(self, case_id, order_ref):
        self._need(case_id)
        rec = self._saved(case_id)
        ref = next((o for o in (rec.orders if rec else ()) if o.ref == order_ref), None)
        if ref is None:
            raise KeyError(f"no order {order_ref!r} on the saved copy of {self.label(case_id)}")
        key = f"{case_id}|{order_ref}"
        hit = self._state["orders"].get(key)
        if hit:
            return OrderText(**hit)

        def fetch():
            text = self.adapter.get_order_text(case_id, order_ref)
            if not isinstance(text, str) or not text.strip():
                raise A.AdapterError("the source returned an empty order")
            return text
        text, cost = self._spend("order", 1, fetch)
        ot = OrderText(case_id, order_ref, ref.date, text, self.adapter.name, self._stamp(), cost)
        self._state["orders"][key] = dataclasses.asdict(ot)
        self._save()
        return ot

    def what_changed(self, since=None):
        if isinstance(since, str):
            since = _parse(since)
        evs = [E.Event.from_dict(d) for d in self._state["events"]]
        return [e for e in evs if since is None or _parse(e.at) > since]

    # ---- fetching and flagging ------------------------------------------------------------------------------------------------------------------------------------------------
    def _fetch_and_save(self, case_id):
        def fetch():
            raw = self.adapter.get_case(case_id)
            if not isinstance(raw, CaseRecord) or raw.case_id != case_id:
                raise A.AdapterError("the source returned a different case")
            return raw
        raw, cost = self._spend("case", 1, fetch)
        old, at = self._saved(case_id), self._stamp()
        rec = dataclasses.replace(raw, nickname="", listing=None, source=self.adapter.name, fetched_at=at, freshness=FRESH, note="", paid_rs=cost)
        for ev in E.diff(old, rec, self.label(case_id), at):
            self._state["events"].append(ev.to_dict())
        self._state["cases"][case_id] = rec.to_dict()
        self._state["failed"].pop(case_id, None)
        self._save()

    def _mark_failed(self, case_id, note):
        at, note = self._stamp(), self._scrub(note)
        self._state["failed"][case_id] = {"at": at, "note": note}
        self._state["events"].append(E.Event(E.UPDATE_FAILED, case_id, self.label(case_id), at, {}, f"Could not update. {note}").to_dict())
        self._save()

    # ---- the nightly run ------------------------------------------------------------------------------------------------------------------------------------------------------------
    def _due(self, case_id, for_date, horizon_days):
        """Does the saved copy of this case need refreshing for that day: nothing held, or the next hearing falls within the horizon or has already passed."""
        rec = self._saved(case_id)
        if rec is None:
            return True
        if rec.status.upper() == "DISPOSED" or not rec.next_hearing:
            return False
        return _date.fromisoformat(rec.next_hearing) <= _date.fromisoformat(for_date) + timedelta(days=horizon_days - 1)

    def plan_night(self, for_date, horizon_days=2):
        """A dry run: what a night would do and cost. Spends nothing and calls no source."""
        for_date = iso_date(for_date)
        ids = sorted(self._state["tracked"])
        n, m = len(ids), sum(1 for i in ids if self._due(i, for_date, horizon_days))
        steps = tuple((k, c) for k, c in (("listing", n), ("refresh", m), ("case", m)) if c)
        est = round(sum(self.adapter.price(k, c) for k, c in steps), 4)
        worst = round(sum(self.adapter.price(k, n) for k in ("listing", "refresh", "case")), 4) if n else 0.0
        pid = hashlib.sha1(json.dumps([for_date, horizon_days, ids, steps]).encode()).hexdigest()[:12]
        return Plan(for_date, horizon_days, steps, est, worst, pid)

    def run_night(self, for_date, plan_id, horizon_days=2):
        """Run the plan that was shown: check the day's listings for every tracked case, then refresh the ones listed or due. A changed set of cases means a new plan id."""
        plan = self.plan_night(for_date, horizon_days)
        if plan_id != plan.plan_id:
            raise PlanError("that plan id is not the current plan: look at plan_night again")
        ids, before = sorted(self._state["tracked"]), self.spent_today()
        result = {"plan_id": plan.plan_id, "listings": {}, "refreshed": [], "failed": [], "spent_rs": 0.0}
        if not ids:
            return result
        self._guard(plan.max_cost)                          # the cap must cover the worst night (every case listed and refreshed) before the first call is sent
        try:
            listings = self.check_listings(ids, plan.for_date)
        except A.AdapterError as e:                         # the source is unreachable at the first step: flag everything and stop
            for i in ids:
                self._mark_failed(i, str(e))
            result["failed"] = list(ids)
            return result
        targets = [i for i in ids if listings[i].status == LISTED or self._due(i, plan.for_date, horizon_days)]
        status = self.refresh(targets) if targets else {}
        result.update(listings=listings, refreshed=[i for i, s in status.items() if s == "REFRESHED"], failed=[i for i, s in status.items() if s == "FAILED"],
                      spent_rs=round(self.spent_today() - before, 4))
        return result
