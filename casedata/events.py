"""What changed between two looks at a case: the events the urgent pings and the briefs are built from.

Event text is plain and carries the case only by its label (nickname and last four digits), never the full case number. Whether a missing listing means "not listed" or "not
covered by the source" is the adapter's call; this module only compares what it is given.
"""
from dataclasses import dataclass, field, asdict

DATE_CHANGED, NEW_ORDER, DISPOSED, COURT_CHANGED = "DATE_CHANGED", "NEW_ORDER", "DISPOSED", "COURT_CHANGED"
LISTED, LISTING_CHANGED, UPDATE_FAILED = "LISTED", "LISTING_CHANGED", "UPDATE_FAILED"
KINDS = (DATE_CHANGED, NEW_ORDER, DISPOSED, COURT_CHANGED, LISTED, LISTING_CHANGED, UPDATE_FAILED)


@dataclass(frozen=True)
class Event:
    kind: str
    case_id: str
    label: str
    at: str
    detail: dict = field(default_factory=dict)
    text: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


def diff(old, new, label, at):
    """Events between two saved records of one case. A first look (old is None) is not a change."""
    if old is None:
        return []
    out = []
    if old.next_hearing != new.next_hearing:
        out.append(Event(DATE_CHANGED, new.case_id, label, at, {"from": old.next_hearing, "to": new.next_hearing},
                         f"Date changed: {old.next_hearing or 'no date'} to {new.next_hearing or 'no date'}."))
    seen = {o.ref for o in old.orders}
    for o in sorted((o for o in new.orders if o.ref not in seen), key=lambda o: (o.date, o.ref)):
        out.append(Event(NEW_ORDER, new.case_id, label, at, {"date": o.date, "ref": o.ref}, f"New order dated {o.date}."))
    if new.status.upper() == "DISPOSED" and old.status.upper() != "DISPOSED":
        out.append(Event(DISPOSED, new.case_id, label, at, {}, "The case now shows as disposed."))
    if old.court and new.court and old.court != new.court:
        out.append(Event(COURT_CHANGED, new.case_id, label, at, {"from": old.court, "to": new.court}, f"Court changed: {old.court} to {new.court}."))
    return out


def _where(listing):
    return f"court {listing.court_no or '?'}, item {listing.item_no if listing.item_no is not None else '?'}"


def listing_events(old, new, on_date, case_id, label, at):
    """Events when a listing check for `on_date` differs from what we held for that date (old and new are Listing or None)."""
    if old is not None and old.date != on_date:
        old = None                                  # a listing for another day says nothing about this one
    if new is None and old is None:
        return []
    if new is not None and old is None:
        return [Event(LISTED, case_id, label, at, {"date": on_date}, f"Listed on {on_date}: {_where(new)}.")]
    if new is None:
        return [Event(LISTING_CHANGED, case_id, label, at, {"date": on_date, "was": _where(old)}, f"No longer listed on {on_date} (was {_where(old)}).")]
    if (new.court_name, new.court_no, new.item_no) != (old.court_name, old.court_no, old.item_no):
        return [Event(LISTING_CHANGED, case_id, label, at, {"date": on_date, "was": _where(old), "now": _where(new)},
                      f"Listing changed on {on_date}: now {_where(new)} (was {_where(old)}).")]
    return []
