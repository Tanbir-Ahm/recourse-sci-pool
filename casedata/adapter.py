"""What a source of case data must offer. One adapter per source; the layer talks only to this interface.

Prices are per call kind: "case" (one case's details), "listing" (one case checked against a day's cause list), "refresh" (one case re-collected at the source), "order" (one order's
text). An adapter says what it charges; the layer decides whether to pay.

Failures: `AdapterDown` means the source could not be reached (nothing was sent, nothing is charged). `AdapterError` is anything else the source refused or broke on; it is counted
as charged unless `charged=False`, because a source may bill for a call that failed. Any other exception is a bug: the layer does not catch it.
"""

UNKNOWN = "UNKNOWN"                       # a listing answer meaning "this source does not cover that case or day", which is not the same as "not listed"
KINDS = ("case", "listing", "refresh", "order")


class AdapterError(Exception):
    def __init__(self, message, charged=True):
        super().__init__(message)
        self.charged = charged


class AdapterDown(AdapterError):
    def __init__(self, message="source unreachable"):
        super().__init__(message, charged=False)


class Adapter:
    name = "adapter"                       # stamped on every record as its source

    def price(self, kind, n=1):
        """Rupees for n calls of this kind."""
        raise NotImplementedError

    def get_case(self, case_id):
        """The source's current copy of the case as a CaseRecord (no nickname, no listing, no stamps: the layer adds those)."""
        raise NotImplementedError

    def check_listings(self, case_ids, on_date):
        """{case_id: Listing, None (no listing found) or UNKNOWN (not covered)} for that day."""
        raise NotImplementedError

    def refresh(self, case_ids):
        """Ask the source to re-collect these cases now. Returns {case_id: None (ok) or a plain-words reason it failed}."""
        raise NotImplementedError

    def get_order_text(self, case_id, order_ref):
        """The text of one order."""
        raise NotImplementedError
