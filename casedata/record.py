"""The standard case record: one shape for a case, whatever source it came from.

Dates are ISO strings (YYYY-MM-DD); times are ISO strings in UTC. `source`, `fetched_at` and `freshness` are never dropped: they are what lets a brief say how old a fact is.
`freshness` is about OUR copy (fetched recently enough, or not); it does not prove the source itself had the court's latest entry.
"""
import dataclasses
import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

FRESH, STALE, FAILED = "FRESH", "STALE", "FAILED"          # FAILED: we hold nothing at all for the case
CNR_RE = re.compile(r"[A-Z]{4}[0-9]{12}")                  # the court's 16-character case number record: 4 letters, 12 digits


def is_cnr(value):
    return isinstance(value, str) and CNR_RE.fullmatch(value) is not None


def iso_date(value):
    """The same date as a YYYY-MM-DD string; ValueError for anything else."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return date.fromisoformat(value).isoformat()
    raise ValueError(f"not a YYYY-MM-DD date: {value!r}")


def last4(case_id):
    return case_id[-4:]


@dataclass(frozen=True)
class Listing:
    date: str
    court_name: str = ""
    court_no: str = ""
    item_no: Optional[int] = None


@dataclass(frozen=True)
class OrderRef:
    date: str
    ref: str                       # the source's name for the order, used to fetch its text
    description: str = ""


@dataclass(frozen=True)
class CaseRecord:
    case_id: str                   # the full case number: private, never printed in a label, event or ledger line
    nickname: str = ""             # set by the lawyer, held by the layer
    court: str = ""
    status: str = ""               # PENDING, DISPOSED, or the source's own word
    stage: str = ""
    purpose: str = ""
    next_hearing: Optional[str] = None
    listing: Optional[Listing] = None      # filled by the layer from a listing check, not by adapters
    orders: tuple = ()
    source: str = ""
    fetched_at: str = ""
    freshness: str = FRESH
    note: str = ""                 # why a record is STALE or FAILED, in plain words
    paid_rs: float = 0.0

    def label(self):
        return f"{self.nickname} · …{last4(self.case_id)}" if self.nickname else f"…{last4(self.case_id)}"

    def to_dict(self):
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d["listing"] = Listing(**d["listing"]) if d.get("listing") else None
        d["orders"] = tuple(OrderRef(**o) for o in d.get("orders") or ())
        return cls(**d)
