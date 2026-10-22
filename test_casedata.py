"""Tests for casedata/: the standard record, events, the layer's five calls, its saved copy, spending cap, ledger and nightly plan, all against the made-up FakeAdapter. No network, no key,
no money. Run: python test_casedata.py"""
import dataclasses
import json
import os
import tempfile
from datetime import datetime, timedelta

from casedata import adapter as A
from casedata import events as E
from casedata import fake as F
from casedata import layer as L
from casedata.record import CaseRecord, Listing, OrderRef, FRESH, STALE, FAILED, is_cnr, iso_date

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc as e:
        return e
    except BaseException as e:
        return None if not isinstance(e, exc) else e
    return None


SHARMA, RAO, GUPTA, KHAN = [c.case_id for c in F.sample_cases()]
NICKS = ["Sharma bail", "Rao partition", "Gupta cheque", "Khan writ"]
START = "2026-10-22T12:00:00+00:00"
DAY = "2026-10-23"


class Clock:
    def __init__(self, start=START):
        self.t = datetime.fromisoformat(start)

    def __call__(self):
        return self.t

    def advance(self, **kw):
        self.t += timedelta(**kw)


def make(cap=50.0, store=None, adapter=None, track=True, **kw):
    ad = adapter or F.FakeAdapter()
    clock = Clock()
    layer = L.CaseDataLayer(ad, cap, store_dir=store, clock=clock, **kw)
    if track:
        for rec, nick in zip(F.sample_cases(), NICKS):
            layer.track(rec.case_id, nick)
    return ad, clock, layer


def total(layer):
    """Everything counted as spent on any day (the ledger rows that are not 'notsent')."""
    rows = {}
    for r in layer._ledger:
        rows.setdefault(r["id"], {}).update(r)
    return round(sum(r["cost"] for r in rows.values() if r.get("outcome") in L.COUNTED), 4)


def no_cnr(text):
    return not any(c in text for c in (SHARMA, RAO, GUPTA, KHAN))


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("record")
check(is_cnr("TEST010000004821") and not is_cnr("test010000004821") and not is_cnr("TEST01000000482") and not is_cnr("") and not is_cnr(None) and not is_cnr("TEST0100000048211"), "a case number is 4 capital letters and 12 digits, nothing else")
check(iso_date("2026-10-23") == "2026-10-23" and iso_date(datetime(2026, 10, 23).date()) == "2026-10-23", "dates are accepted as ISO strings or date objects")
check(raises(ValueError, iso_date, "23/10/2026") is not None and raises(ValueError, iso_date, "2026-13-40") is not None, "any other date spelling, and an impossible date, is refused")
rec = dataclasses.replace(F.sample_cases()[0], nickname="Sharma bail")
check(rec.label() == "Sharma bail · …4821" and SHARMA not in rec.label(), "a label is the nickname and the last four digits, never the full case number")
check(CaseRecord.from_dict(json.loads(json.dumps(rec.to_dict()))) == rec, "a record survives a round trip through JSON unchanged")
with_listing = dataclasses.replace(rec, listing=Listing(DAY, "Court 5", "5", 14))
check(CaseRecord.from_dict(json.loads(json.dumps(with_listing.to_dict()))) == with_listing, "so does a record with a listing")

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("events")
base = F.sample_cases()[0]
check(E.diff(None, base, "x", "t") == [], "a first look at a case is not a change")
moved = dataclasses.replace(base, next_hearing="2026-10-27")
ev = E.diff(base, moved, "Sharma bail · …4821", "t")
check([e.kind for e in ev] == [E.DATE_CHANGED] and ev[0].detail == {"from": "2026-10-23", "to": "2026-10-27"}, "a moved next date is one DATE_CHANGED event with both dates")
two_new = dataclasses.replace(base, orders=base.orders + (OrderRef("2026-10-22", "order-6.pdf"), OrderRef("2026-10-20", "order-5.pdf")))
ev = E.diff(base, two_new, "x", "t")
check([e.detail["date"] for e in ev] == ["2026-10-20", "2026-10-22"] and all(e.kind == E.NEW_ORDER for e in ev), "each new order is its own event, oldest first")
ev = E.diff(base, dataclasses.replace(base, status="DISPOSED", next_hearing=None), "x", "t")
check(sorted(e.kind for e in ev) == [E.DATE_CHANGED, E.DISPOSED], "disposal is reported, and the cleared date with it")
ev = E.diff(base, dataclasses.replace(base, court="High Court, Court 7"), "x", "t")
check([e.kind for e in ev] == [E.COURT_CHANGED], "a changed court is reported")
check(E.diff(base, base, "x", "t") == [], "an unchanged case gives no events")
lst = Listing(DAY, "", "5", 14)
check(E.listing_events(None, lst, DAY, SHARMA, "x", "t")[0].kind == E.LISTED, "a newly listed case gives LISTED")
check(E.listing_events(lst, lst, DAY, SHARMA, "x", "t") == [], "the same listing again gives nothing")
check(E.listing_events(lst, dataclasses.replace(lst, item_no=15), DAY, SHARMA, "x", "t")[0].kind == E.LISTING_CHANGED, "a new item number gives LISTING_CHANGED")
gone = E.listing_events(lst, None, DAY, SHARMA, "x", "t")
check(len(gone) == 1 and "No longer listed" in gone[0].text, "a case that drops off the list is reported")
check(E.listing_events(Listing("2026-10-22", "", "5", 3), None, DAY, SHARMA, "x", "t") == [], "yesterday's listing says nothing about today")
check(all(no_cnr(e.text + e.label) for e in E.diff(base, dataclasses.replace(base, next_hearing=None, status="DISPOSED"), "Sharma bail · …4821", "t")), "event text and labels carry no full case number")

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("the made-up source")
ad = F.FakeAdapter()
ad.move_hearing(SHARMA, "2026-10-27")
check(ad.get_case(SHARMA).next_hearing == "2026-10-23", "the source keeps its own copy: a change at the court does not show before a refresh")
check(ad.refresh([SHARMA]) == {SHARMA: None} and ad.get_case(SHARMA).next_hearing == "2026-10-27", "a refresh brings the source's copy up to the court's")
ad.down = True
check(raises(A.AdapterDown, ad.get_case, SHARMA) is not None and len(ad.calls) == 3, "a source that is down raises AdapterDown and the call never counts as made")
check(A.AdapterDown().charged is False and A.AdapterError("x").charged is True, "an outage is never charged; any other failure is counted as charged by default")

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("the layer: reading and the saved copy")
ad, clock, layer = make()
r = layer.get_case(SHARMA)
check(r.freshness == FRESH and r.source == "fake" and r.fetched_at == START and r.nickname == "Sharma bail" and r.paid_rs == 0.5, "a first read buys the case and stamps its source, time, nickname and price")
check(layer.spent_today() == 0.5 and len(ad.calls_of("case")) == 1, "and the spending is on the ledger")
layer.get_case(SHARMA)
check(len(ad.calls_of("case")) == 1 and layer.spent_today() == 0.5, "a second read within the age limit is served from the saved copy for free")
clock.advance(hours=25)
r = layer.get_case(SHARMA)
check(len(ad.calls_of("case")) == 2 and r.freshness == FRESH and total(layer) == 1.0, "after the age limit a read buys the case again")
clock.advance(hours=25)
check(layer.get_case(SHARMA, max_age_hours=100).freshness == FRESH and len(ad.calls_of("case")) == 2, "a caller that accepts older data gets the saved copy")
check(layer.get_case(RAO).fetched_at == "2026-10-24T14:00:00+00:00" and layer.label(RAO) == "Rao partition · …7713", "labels use the nickname and last four digits")
check(raises(KeyError, layer.get_case, "TEST999999999999") is not None and "TEST999999999999" not in str(raises(KeyError, layer.get_case, "TEST999999999999")), "an untracked case is refused without printing its number")

print("the layer: a source that fails")
ad, clock, layer = make()
layer.get_case(SHARMA)
clock.advance(hours=25)
ad.down = True
rows = len(layer._ledger)
r = layer.get_case(SHARMA)
check(r.freshness == STALE and "failed" in r.note and r.next_hearing == "2026-10-23", "an outage gives the saved copy marked STALE with a reason, not an exception and not FRESH")
check(total(layer) == 0.5 and layer._ledger[-1]["outcome"] == "notsent", "an outage costs nothing: the attempt is recorded as not sent")
layer.get_case(SHARMA)
check(len(layer._ledger) == rows + 2, "a failed case is not tried again straight away (one attempt, one outcome)")
check(any(e.kind == E.UPDATE_FAILED for e in layer.what_changed()), "the failure is an event")
clock.advance(minutes=61)
ad.down = False
r = layer.get_case(SHARMA)
check(r.freshness == FRESH and r.note == "" and len(ad.calls_of("case")) == 2, "after the wait it tries again, recovers, and the flag clears")
ad.down = True
r = layer.get_case(RAO)
check(r.freshness == FAILED and r.nickname == "Rao partition" and r.note and r.next_hearing is None, "a case never fetched, with the source down, is FAILED and says so")
ad, clock, layer = make()
ad.fail[SHARMA] = f"case {SHARMA} blocked by the court site"
r = layer.get_case(SHARMA)
check(r.freshness == FAILED and "…4821" in r.note and no_cnr(r.note) and layer.spent_today() == 0.5, "a source error is counted as spent, and a case number in its message is cut down to four digits")


class Buggy(F.FakeAdapter):
    def get_case(self, case_id):
        raise RuntimeError("bug in the adapter")


ad, clock, layer = make(adapter=Buggy())
check(raises(RuntimeError, layer.get_case, SHARMA) is not None, "an unexpected exception is a bug: it is raised, not swallowed")
check(layer.spent_today() == 0.5 and layer._ledger[-1]["outcome"] == "unknown", "and the call is recorded as unknown and counted as spent")


class WrongCase(F.FakeAdapter):
    def get_case(self, case_id):
        return dataclasses.replace(super().get_case(case_id), case_id=RAO)


ad, clock, layer = make(adapter=WrongCase())
check(layer.get_case(SHARMA).freshness == FAILED and layer._state["cases"] == {}, "a source answering with a different case is refused and nothing is saved")

print("the layer: the spending cap")
ad, clock, layer = make(cap=0.4)
r = layer.get_case(SHARMA)
check(r.freshness == FAILED and "Not updated" in r.note and not ad.calls and not layer._ledger, "a read that would pass the cap sends nothing, writes nothing and says so")
ad, clock, layer = make(cap=0.3)
check(raises(L.BudgetError, layer.check_listings, [SHARMA, RAO, GUPTA, KHAN], DAY) is not None and not ad.calls, "a listing check past the cap is refused before it is sent")
ad, clock, layer = make(cap=1.0)
layer.get_case(SHARMA)
layer.get_case(RAO)
r = layer.get_case(GUPTA)
check(len(ad.calls_of("case")) == 2 and "Not updated" in r.note and layer.spent_today() == 1.0, "the cap holds across calls: two cases bought, the third refused")
clock.t = datetime.fromisoformat("2026-10-22T23:30:00+00:00")
ad, clock2, layer = make(cap=1.0)
layer._clock = lambda: clock.t
layer.get_case(SHARMA)
clock.advance(hours=1)
check(layer.spent_today() == 0.0 and layer.get_case(RAO).freshness == FRESH, "the cap is per day: it starts again at midnight UTC")
check(all(raises(ValueError, L.CaseDataLayer, F.FakeAdapter(), c) is not None for c in (-1, float("nan"), float("inf"), True, "5", None)), "a cap that is negative, not a number, infinite or a boolean is refused")
check(raises(ValueError, L.CaseDataLayer(F.FakeAdapter(), 5, clock=lambda: datetime(2026, 10, 22)).spent_today) is not None, "a clock without a time zone is refused")
check(raises(ValueError, L.CaseDataLayer(F.FakeAdapter(), 5).track, "bad", "x") is not None and raises(ValueError, L.CaseDataLayer(F.FakeAdapter(), 5).track, SHARMA, "  ") is not None, "a bad case number or a blank nickname is refused")

print("the layer: listings")
ad, clock, layer = make()
ad.listings[(SHARMA, DAY)] = Listing(DAY, "Court 5", "5", 14)
ad.listings[(RAO, DAY)] = Listing("2026-10-24", "Court 5", "5", 31)        # an answer for another day
ad.uncovered = {KHAN}
res = layer.check_listings([SHARMA, GUPTA, KHAN, RAO, SHARMA], DAY)
check(len(res) == 4 and res[SHARMA].status == L.LISTED and res[GUPTA].status == L.NOT_LISTED and res[KHAN].status == L.UNKNOWN and res[RAO].status == L.UNKNOWN, "listing answers: LISTED, NOT_LISTED, UNKNOWN for not covered, UNKNOWN for another day's answer")
check(layer.spent_today() == 0.4 and ad.calls_of("listing") == [("listing", (SHARMA, GUPTA, KHAN, RAO))], "duplicates are collapsed, and the batch is paid once per distinct case")
check([e.kind for e in layer.what_changed()] == [E.LISTED], "a first listing is an event, an unknown is not")
layer.check_listings([SHARMA], DAY)
check([e.kind for e in layer.what_changed()] == [E.LISTED], "asking again changes nothing")
layer.get_case(SHARMA)
check(layer.get_case(SHARMA).listing == Listing(DAY, "Court 5", "5", 14), "the record shows the listing the layer holds")
ad.listings[(SHARMA, DAY)] = Listing(DAY, "Court 5", "5", 15)
layer.check_listings([SHARMA], DAY)
del ad.listings[(SHARMA, DAY)]
layer.check_listings([SHARMA], DAY)
check([e.kind for e in layer.what_changed()] == [E.LISTED, E.LISTING_CHANGED, E.LISTING_CHANGED] and layer.get_case(SHARMA).listing is None, "a changed item and then a dropped listing are both reported, and the held listing goes")
check(raises(A.AdapterDown, L.CaseDataLayer(F.FakeAdapter(), 5).check_listings, [], DAY) is None, "an empty request is answered without calling the source")

print("the layer: refresh and what changed")
ad, clock, layer = make()
for c in (SHARMA, RAO, GUPTA, KHAN):
    layer.get_case(c)
t0 = clock.t
clock.advance(minutes=5)
ad.move_hearing(SHARMA, "2026-10-27")
ad.add_order(RAO, OrderRef("2026-10-22", "order-2.pdf"), "text")
ad.dispose(GUPTA)
ad.set_court(KHAN, "High Court, [Bench], Court 7")
check(layer.get_case(SHARMA).next_hearing == "2026-10-23", "before a refresh the held copy is still the old one")
before = layer.spent_today()
res = layer.refresh([SHARMA, RAO, GUPTA, KHAN])
check(set(res.values()) == {"REFRESHED"} and round(layer.spent_today() - before, 4) == 2.2, "a refresh of four cases is paid as four refreshes and four fetches")
kinds = sorted(e.kind for e in layer.what_changed(t0))
check(kinds == sorted([E.DATE_CHANGED, E.NEW_ORDER, E.DISPOSED, E.DATE_CHANGED, E.COURT_CHANGED]), "the changes are found: new date, new order, disposal (with its cleared date), new court")
check(layer.what_changed(clock.t) == [] and len(layer.what_changed(t0 - timedelta(days=1))) == 5, "what_changed filters by time")
check(layer.get_case(SHARMA).next_hearing == "2026-10-27", "the saved copy has the new date")
check(all(no_cnr(e.text + e.label) for e in layer.what_changed()), "no event text or label carries a full case number")
clock.advance(minutes=5)
ad.fail[RAO] = "page did not load"
ad.calls.clear()
res = layer.refresh([SHARMA, RAO])
check(res == {SHARMA: "REFRESHED", RAO: "FAILED"} and [c for c in ad.calls_of("case")] == [("case", (SHARMA,))], "one case failing does not stop the others, and the failed case is not fetched")
r = layer.get_case(RAO)
check(r.freshness == STALE and "page did not load" in r.note and any(e.kind == E.UPDATE_FAILED and "page did not load" in e.text for e in layer.what_changed()), "the failed case is STALE, with the reason, and the failure is an event")
ad, clock, layer = make()
ad.down = True
check(layer.refresh([SHARMA, RAO]) == {SHARMA: "FAILED", RAO: "FAILED"} and layer.spent_today() == 0 and not ad.calls, "a source that is down: every case is flagged, nothing is spent")


class DownAfterRefresh(F.FakeAdapter):
    def refresh(self, case_ids):
        out = super().refresh(case_ids)
        self.down = True
        return out


ad, clock, layer = make(adapter=DownAfterRefresh())
res = layer.refresh([SHARMA, RAO, GUPTA])
check(set(res.values()) == {"FAILED"} and not ad.calls_of("case") and layer.spent_today() == 0.15, "an outage after the refresh stops the run: the rest are flagged and not tried, and only the refresh was paid")
ad, clock, layer = make(cap=0.5)
check(raises(L.BudgetError, layer.refresh, [SHARMA, RAO]) is not None and not ad.calls and not layer._ledger, "a batch that does not fit under the cap sends nothing at all")

print("the layer: orders")
ad, clock, layer = make()
check(raises(KeyError, layer.get_order, SHARMA, "order-4.pdf") is not None, "an order cannot be asked for before the case has been fetched")
layer.get_case(SHARMA)
ad.order_texts[(SHARMA, "order-4.pdf")] = "ORDER TEXT"
spent = layer.spent_today()
o = layer.get_order(SHARMA, "order-4.pdf")
check(o.text == "ORDER TEXT" and o.date == "2026-10-15" and o.source == "fake" and o.paid_rs == 1.25 and round(layer.spent_today() - spent, 4) == 1.25, "an order is bought once, with its date, source and price")
layer.get_order(SHARMA, "order-4.pdf")
check(len(ad.calls_of("order")) == 1, "and kept: asking again is free")
check(raises(KeyError, layer.get_order, SHARMA, "order-99.pdf") is not None, "an order the case does not have is refused")
ad.order_texts[(SHARMA, "order-3.pdf")] = "   "
check(raises(A.AdapterError, layer.get_order, SHARMA, "order-3.pdf") is not None and (SHARMA + "|order-3.pdf") not in layer._state["orders"], "an empty order is an error and is not kept")
ad.down = True
check(raises(A.AdapterDown, layer.get_order, SHARMA, "order-1.pdf") is not None, "an order cannot be bought while the source is down, and the caller is told")

print("the layer: saving, restarting, the stop file")
with tempfile.TemporaryDirectory() as store:
    ad, clock, layer = make(cap=2.0, store=store)
    layer.get_case(SHARMA)
    ad.listings[(SHARMA, DAY)] = Listing(DAY, "Court 5", "5", 14)
    layer.check_listings([SHARMA], DAY)
    check(sorted(os.listdir(store)) == ["ledger.jsonl", "state.json"], "the store holds the state and the ledger, and no stray files")
    ledger_text = open(os.path.join(store, "ledger.jsonl"), encoding="utf-8").read()
    check(no_cnr(ledger_text) and "pending" in ledger_text and '"ok"' in ledger_text, "the ledger shows the attempt and its result, and holds no case number")
    ad2 = F.FakeAdapter()
    layer2 = L.CaseDataLayer(ad2, 2.0, store_dir=store, clock=clock)
    r = layer2.get_case(SHARMA)
    check(r.freshness == FRESH and r.listing is not None and not ad2.calls, "a restarted layer reads the saved copy and listing without calling the source")
    check(layer2.spent_today() == 0.6 and len(layer2.what_changed()) == 1 and layer2.tracked() == layer.tracked(), "and keeps today's spending, the events and the tracked cases")
    check(raises(L.BudgetError, layer2.refresh, [SHARMA, RAO, GUPTA, KHAN]) is not None and not ad2.calls, "so the cap holds across a restart")
    open(os.path.join(store, L.STOP_FILE), "w").close()
    r = layer2.get_case(RAO)
    check(r.freshness == FAILED and "Not updated" in r.note and not ad2.calls, "with the stop file present nothing is bought, and a read says so")
    check(layer2.get_case(SHARMA).freshness == FRESH and raises(L.StoppedError, layer2.refresh, [SHARMA]) is not None, "the saved copy can still be read, and a spending call is refused")
    os.remove(os.path.join(store, L.STOP_FILE))
    check(layer2.get_case(RAO).freshness == FRESH and ad2.calls_of("case") == [("case", (RAO,))], "when the stop file goes, buying works again")
    layer2.untrack(SHARMA)
    check(SHARMA not in layer2.tracked() and no_cnr(json.dumps(layer2._state["events"]).replace(RAO, "")) and not [k for k in layer2._state["orders"] if k.startswith(SHARMA)]
          and SHARMA not in json.dumps(layer2._state), "untracking forgets the case's copy, listing, orders and events")
    check(raises(KeyError, layer2.get_case, SHARMA) is not None, "an untracked case cannot be read")

print("the nightly plan")
ad, clock, layer = make()
plan = layer.plan_night(DAY)
check(plan.steps == (("listing", 4), ("refresh", 4), ("case", 4)) and plan.est_cost == 2.6 and plan.max_cost == 2.6 and not ad.calls and layer.spent_today() == 0, "a plan for cases never fetched lists every step, with its cost, and spends and calls nothing")
check(layer.plan_night(DAY).plan_id == plan.plan_id and layer.plan_night("2026-10-24").plan_id != plan.plan_id, "the plan id is the same for the same plan and different for another day")
check(raises(L.PlanError, layer.run_night, DAY, "wrongid") is not None and not ad.calls, "a night does not run against a plan id that was not shown")
res = layer.run_night(DAY, plan.plan_id)
check(len(res["refreshed"]) == 4 and not res["failed"] and res["spent_rs"] == 2.6 and len(res["listings"]) == 4, "the first night checks every listing and fetches every case")
check(layer.plan_night(DAY).plan_id != plan.plan_id, "once the copies exist the plan has changed, so the old id no longer runs")
plan = layer.plan_night(DAY)
check(plan.steps == (("listing", 4), ("refresh", 3), ("case", 3)) and plan.est_cost == 2.05, "later nights refresh only the cases due within the horizon (Khan's hearing is days away)")
ad.listings[(KHAN, DAY)] = Listing(DAY, "Court 12", "12", 42)
res = layer.run_night(DAY, plan.plan_id)
check(sorted(res["refreshed"]) == sorted([SHARMA, RAO, GUPTA, KHAN]) and res["spent_rs"] == 2.6, "a case found listed that day is refreshed even when its saved date said otherwise")
ad.dispose(GUPTA)
layer.refresh([GUPTA])
check(layer.plan_night(DAY).steps[1] == ("refresh", 2), "a disposed case is no longer refreshed")
ad.down = True
plan = layer.plan_night(DAY)
res = layer.run_night(DAY, plan.plan_id)
check(sorted(res["failed"]) == sorted(layer.tracked()) and not res["refreshed"] and all(layer.get_case(c).freshness == STALE for c in layer.tracked()), "a source that is down on the night: every case is flagged STALE and nothing else is tried")
ad, clock, layer = make(cap=1.0)
plan = layer.plan_night(DAY)
check(raises(L.BudgetError, layer.run_night, DAY, plan.plan_id) is not None and not ad.calls and not layer._ledger, "a cap that cannot cover the worst night stops it before the first call")

print("privacy")
ad, clock, layer = make()
ad.fail[GUPTA] = f"{GUPTA} and {KHAN} not reachable"
layer.get_case(GUPTA)
layer.refresh([SHARMA, KHAN])
check(no_cnr(json.dumps(layer._ledger)) and all(no_cnr(e.text + e.label) for e in layer.what_changed()) and no_cnr(layer.get_case(GUPTA).note), "ledger, events and notes stay free of full case numbers even when a source puts them in its messages")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
