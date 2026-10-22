"""A made-up source for tests: invented cases, no network, no key, no money.

It models the one thing about a real source that matters here: it keeps its OWN copy of each case (`held`), which only catches up with the court (`truth`) when `refresh` is called. A
test can change the court's side (`move_hearing`, `add_order`, `dispose`, `set_court`) and see that `get_case` still returns the old copy until a refresh. The prices are invented, chosen only
so that spending caps are easy to test; they are not any vendor's.
"""
import dataclasses

from . import adapter as A
from .record import CaseRecord, OrderRef

PRICES = {"case": 0.50, "listing": 0.10, "refresh": 0.05, "order": 1.25}


def sample_cases():
    """Four invented cases (case numbers start TEST, so they can never be real ones)."""
    def orders(*dates):
        return tuple(OrderRef(d, f"order-{i}.pdf", "COPY OF ORDER") for i, d in enumerate(dates, 1))
    return [
        CaseRecord("TEST010000004821", court="District Court, [City], Court 5", status="PENDING", stage="Bail application", purpose="Arguments", next_hearing="2026-10-23",
                   orders=orders("2026-09-03", "2026-09-17", "2026-10-01", "2026-10-15")),
        CaseRecord("TEST010000007713", court="District Court, [City], Court 5", status="PENDING", stage="Civil suit", purpose="Evidence of plaintiff", next_hearing="2026-10-23",
                   orders=orders("2026-10-08")),
        CaseRecord("TEST010000002290", court="High Court, [Bench], Court 12", status="PENDING", stage="Admission", purpose="Admission hearing", next_hearing="2026-10-23",
                   orders=orders("2026-10-12")),
        CaseRecord("TEST010000009035", court="High Court, [Bench], Court 12", status="PENDING", stage="Writ petition", purpose="Final hearing", next_hearing="2026-10-27"),
    ]


class FakeAdapter(A.Adapter):
    name = "fake"

    def __init__(self, cases=None, prices=None):
        self.truth = {c.case_id: c for c in (cases if cases is not None else sample_cases())}
        self.held = dict(self.truth)               # the source's own copy: stale until refresh
        self.listings = {}                         # (case_id, date) -> Listing
        self.order_texts = {}                      # (case_id, order ref) -> text
        self.uncovered = set()                     # case ids whose listings this source cannot see
        self.fail = {}                             # case id -> reason: that case fails on get_case and refresh
        self.down = False                          # the whole source is unreachable
        self.calls = []                            # (kind, case ids) for every call that reached the source
        self.prices = dict(PRICES, **(prices or {}))

    def _enter(self, kind, ids):
        if self.down:
            raise A.AdapterDown()
        self.calls.append((kind, tuple(ids)))

    def calls_of(self, kind):
        return [c for c in self.calls if c[0] == kind]

    def price(self, kind, n=1):
        return round(self.prices[kind] * n, 4)

    def get_case(self, case_id):
        self._enter("case", [case_id])
        if case_id in self.fail:
            raise A.AdapterError(self.fail[case_id])
        if case_id not in self.held:
            raise A.AdapterError("case not found")
        return self.held[case_id]

    def check_listings(self, case_ids, on_date):
        self._enter("listing", case_ids)
        return {i: (A.UNKNOWN if i in self.uncovered else self.listings.get((i, on_date))) for i in case_ids}

    def refresh(self, case_ids):
        self._enter("refresh", case_ids)
        out = {}
        for i in case_ids:
            if i in self.fail:
                out[i] = self.fail[i]
            elif i in self.truth:
                self.held[i] = self.truth[i]
                out[i] = None
            else:
                out[i] = "case not found"
        return out

    def get_order_text(self, case_id, order_ref):
        self._enter("order", [case_id])
        if (case_id, order_ref) not in self.order_texts:
            raise A.AdapterError("order not found")
        return self.order_texts[(case_id, order_ref)]

    # the court's side: changes here reach `held` only through refresh
    def move_hearing(self, case_id, new_date):
        self.truth[case_id] = dataclasses.replace(self.truth[case_id], next_hearing=new_date)

    def add_order(self, case_id, order, text=None):
        rec = self.truth[case_id]
        self.truth[case_id] = dataclasses.replace(rec, orders=rec.orders + (order,))
        if text is not None:
            self.order_texts[(case_id, order.ref)] = text

    def dispose(self, case_id):
        self.truth[case_id] = dataclasses.replace(self.truth[case_id], status="DISPOSED", next_hearing=None)

    def set_court(self, case_id, court):
        self.truth[case_id] = dataclasses.replace(self.truth[case_id], court=court)
