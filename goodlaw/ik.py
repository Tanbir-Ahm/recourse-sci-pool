"""Indian Kanoon (IK) API client with guard rails. Every call costs real money, so nothing here spends without a plan, a cap and an explicit approval.

What it enforces (IK_PLAN.md, Phase 1):

    key         read from the environment only (INDIANKANOON_API_KEY); held in a wrapper that prints as <IK key>; sent only to api.indiankanoon.org, as the
                Authorization header; scrubbed from every message, ledger line and cache file; redirects are never followed
    dry run     `plan` lists every call with its price and says which are already cached; `run` spends nothing unless the approved amount equals the plan's cost
    caps        a hard rupee cap for this run, and TOTAL_CAP_RS across all runs (the ledger is the memory); checked again before every call
    cache       each raw response is saved the first time and read from disk afterwards, so nothing is fetched twice
    stop        the first auth, balance, rate-limit, server, redirect or bad-response error ends the run; no retry; the error is never cached
    probe first a kind of call (a "shape") that has no successful call in the ledger can only be planned as a single call, so its real response is read before more are made
    throttle    calls are serial, with a gap between their starts
    stop file   a file named IK_STOP in the working folder refuses every call

The ledger (goodlaw/data/ik_ledger.jsonl) holds one line per call that reached the server: when, what, the price assumed, the outcome. It holds no key and no text and is
committed. The cache (ik_cache/, git-ignored) holds raw responses, which may be IK text, and is never committed; where fetched text may be kept is a Phase 4 decision.

Money rules: an "ok" call counts at its listed price; a call that may have been processed without a readable answer (a timeout, a dropped connection) counts too, because it may
have been charged; an HTTP error answer counts nothing (not verified; the caps leave room). Prices are those IK published on 2026-10-06 and may change on a week's notice; only
'meta' has been confirmed on the dashboard (Rs 391.16 to 391.14).

Not built, on purpose: parallel calls, retries, the Original Document call, anything that reads the key from a file.
"""
import dataclasses
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

HOST = "api.indiankanoon.org"
BASE_URL = "https://" + HOST
KEY_ENV = "INDIANKANOON_API_KEY"
STOP_FILE = "IK_STOP"
TOTAL_CAP_RS = 150.0               # the checker's total across all runs (IK_PLAN.md budget rule); raising it is a deliberate edit, visible in git
MIN_GAP_SECONDS = 0.5              # between the starts of two calls
TIMEOUT_SECONDS = 30

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEDGER = os.path.join(HERE, "data", "ik_ledger.jsonl")
DEFAULT_CACHE = os.path.join(os.path.dirname(HERE), "ik_cache")

# kind -> endpoint, price in rupees per call, what the call needs, and the extra parameters it may carry. All calls are POST with the parameters in the query string, as
# Recourse's own client does (that client worked against the live API). 'meta' is confirmed against the real API (Phase 0). 'doc' and 'search' follow Recourse's client and IK's
# price page. 'fragment' and the extra parameters of 'doc' are NOT verified: their paths and parameter names come from memory of IK's documentation, which is why a first call of
# each runs alone.
KINDS = {
    "meta":     {"path": "/docmeta/{tid}/",     "price": 0.02, "needs": "tid",       "extras": ()},
    "doc":      {"path": "/doc/{tid}/",         "price": 0.20, "needs": "tid",       "extras": ("maxcites", "maxcitedby")},
    "fragment": {"path": "/docfragment/{tid}/", "price": 0.05, "needs": "tid+query", "extras": ()},
    "search":   {"path": "/search/",            "price": 0.50, "needs": "query",     "extras": ()},
}
TID_RE = re.compile(r"\d{1,12}")
MAX_QUERY = 500


class IKError(Exception):
    """Anything that ends a run. The message never holds the key."""


class IKPlanError(IKError):
    """Refused before any call was made."""


class IKAuthError(IKError):
    """401 or 403."""


class IKBalanceError(IKError):
    """402, or an answer that talks of balance or credit."""


class IKRateLimited(IKError):
    """429. Not retried."""


class IKBadResponse(IKError):
    """A redirect, a server error, an answer that is not JSON, or JSON that reports an error."""


class _Secret:
    """Holds the key so that printing, logging or a traceback shows <IK key>, never the value."""
    __slots__ = ("_v",)

    def __init__(self, v):
        self._v = v

    def reveal(self):
        return self._v

    def __repr__(self):
        return "<IK key>"

    __str__ = __repr__


@dataclasses.dataclass(frozen=True)
class Call:
    """One API call. Validated on construction so that a bad id or an unlisted parameter cannot reach the network or a file name."""
    kind: str
    tid: str = ""
    query: str = ""
    page: int = 0
    extra: tuple = ()                  # ((name, int), ...) sorted

    def __post_init__(self):
        spec = KINDS.get(self.kind)
        if spec is None:
            raise ValueError(f"unknown kind {self.kind!r}; known: {', '.join(KINDS)}")
        needs = spec["needs"]
        object.__setattr__(self, "tid", str(self.tid or ""))
        if "tid" in needs and not TID_RE.fullmatch(self.tid):
            raise ValueError(f"{self.kind} needs a numeric tid (up to 12 digits), got {self.tid!r}")
        if "tid" not in needs and self.tid:
            raise ValueError(f"{self.kind} takes no tid")
        if "query" in needs and not (isinstance(self.query, str) and self.query.strip() and len(self.query) <= MAX_QUERY and "\n" not in self.query):
            raise ValueError(f"{self.kind} needs a one-line query of at most {MAX_QUERY} characters")
        if "query" not in needs and self.query:
            raise ValueError(f"{self.kind} takes no query")
        if not (isinstance(self.page, int) and 0 <= self.page <= 1000):
            raise ValueError("page must be an integer from 0 to 1000")
        if self.page and self.kind != "search":
            raise ValueError("only search takes a page")
        pairs = self.extra.items() if isinstance(self.extra, dict) else self.extra
        extra = tuple(sorted((str(k), v) for k, v in pairs))
        for k, v in extra:
            if k not in spec["extras"]:
                raise ValueError(f"{self.kind} may not carry parameter {k!r}; allowed: {spec['extras'] or 'none'}")
            if not (isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 50):
                raise ValueError(f"parameter {k} must be an integer from 0 to 50")
        object.__setattr__(self, "extra", extra)

    @property
    def price(self):
        return KINDS[self.kind]["price"]

    def shape(self):
        """The kind plus the names of its extra parameters: what has to have worked once before it is repeated."""
        return self.kind + "".join("+" + k for k, _ in self.extra)

    def path(self):
        return KINDS[self.kind]["path"].format(tid=self.tid)

    def params(self):
        p = {}
        if self.query:
            p["formInput"] = self.query
        if self.kind == "search":
            p["pagenum"] = self.page
        p.update(dict(self.extra))
        return p

    def request(self):
        return {"kind": self.kind, "tid": self.tid, "query": self.query, "page": self.page, "extra": dict(self.extra)}

    def key(self):
        return json.dumps(self.request(), sort_keys=True, ensure_ascii=True)

    def label(self):
        bits = [self.kind, self.tid or None, repr(self.query) if self.query else None, f"page {self.page}" if self.page else None,
                ",".join(f"{k}={v}" for k, v in self.extra) or None]
        return " ".join(b for b in bits if b)


def meta(tid):
    return Call("meta", tid=tid)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_meta(resp):
    """The fields of a /docmeta/ answer, as seen in the real Phase 0 response (tid 151036912, 2026-10-06). Raises IKBadResponse if the shape differs, so a change at IK is
    noticed rather than read as zeros."""
    need = ("tid", "publishdate", "doctype", "title", "numcites", "numcitedby")
    if not isinstance(resp, dict) or any(k not in resp for k in need):
        raise IKBadResponse(f"a /docmeta/ answer without the fields {need}: got {sorted(resp) if isinstance(resp, dict) else type(resp).__name__}")
    return {"tid": str(resp["tid"]), "date": resp["publishdate"], "doctype": resp["doctype"], "title": resp["title"], "caseno": resp.get("caseno"),
            "numcites": int(resp["numcites"]), "numcitedby": int(resp["numcitedby"]), "relurl": resp.get("relurl")}


# ---------------------------------------------------------------------------------------------------------------------------- the plan
@dataclasses.dataclass
class PlanItem:
    call: Call
    cached: bool

    @property
    def price(self):
        return 0.0 if self.cached else self.call.price


@dataclasses.dataclass
class Plan:
    items: list
    run_cap_rs: float
    spent_before_rs: float
    problems: list

    @property
    def cost(self):
        return round(sum(i.price for i in self.items), 2)

    @property
    def n_calls(self):
        return sum(1 for i in self.items if not i.cached)

    @property
    def n_cached(self):
        return sum(1 for i in self.items if i.cached)

    def text(self):
        out = [f"DRY RUN: {len(self.items)} distinct calls, {self.n_cached} already cached (free), {self.n_calls} to make"]
        for i in self.items:
            out.append(f"  {'cached  ' if i.cached else 'CALL    '} Rs {i.price:5.2f}  {i.call.label()}")
        out.append(f"COST OF THIS PLAN: Rs {self.cost:.2f}   (run cap Rs {self.run_cap_rs:.2f}; spent so far by this client Rs {self.spent_before_rs:.2f} of Rs {TOTAL_CAP_RS:.2f})")
        for p in self.problems:
            out.append("REFUSED: " + p)
        if not self.problems and self.n_calls:
            out.append(f"To spend it, run with --approved-rs {self.cost:.2f}")
        return "\n".join(out)


class Client:
    def __init__(self, env=None, cache_dir=DEFAULT_CACHE, ledger_path=DEFAULT_LEDGER, base_url=BASE_URL, allow_test_base=False, transport=None,
                 clock=time.monotonic, sleep=time.sleep, min_gap=MIN_GAP_SECONDS, stop_file=STOP_FILE, log=None):
        env = os.environ if env is None else env
        raw = env.get(KEY_ENV)
        self._key_problem = None
        if raw and not re.fullmatch(r"[\x21-\x7e]{8,200}", raw):
            raw, self._key_problem = None, f"{KEY_ENV} is set but is not a single printable token of 8 to 200 characters (the value is not shown)"
        self._key = _Secret(raw) if raw else None
        host = re.sub(r"^https?://([^/:]+).*$", r"\1", base_url)
        if base_url != BASE_URL and not (allow_test_base and host in ("127.0.0.1", "localhost") and base_url.startswith("http://")):
            raise IKError(f"the key is only ever sent to {BASE_URL}")
        self.base_url = base_url.rstrip("/")
        self.cache_dir, self.ledger_path = cache_dir, ledger_path
        self._transport = transport or _requests_transport
        self._clock, self._sleep, self.min_gap = clock, sleep, min_gap
        self._last_start = None
        self.stop_file = stop_file
        self.log = log or (lambda m: print(m, file=sys.stderr))

    def __repr__(self):
        return f"<ik.Client {self.base_url} key={'set' if self._key else 'NOT set'}>"

    # ------------------------------------------------------------------------------------------------------------------------ ledger and cache
    def ledger(self):
        rows = []
        if os.path.exists(self.ledger_path):
            with open(self.ledger_path, encoding="utf-8") as fh:
                for n, line in enumerate(fh, 1):
                    if line.strip():
                        try:
                            rows.append(json.loads(line))
                        except ValueError:
                            raise IKError(f"{self.ledger_path} line {n} is not JSON; refusing to spend with a damaged ledger")
        return rows

    @staticmethod
    def _spent(row):
        return row["price_rs"] if row.get("outcome") in ("ok", "unknown") else 0.0

    def spent_total(self):
        return round(float(sum(self._spent(r) for r in self.ledger())), 2)

    def confirmed_shapes(self):
        return {r["shape"] for r in self.ledger() if r.get("outcome") == "ok"}

    def _append_ledger(self, call, outcome, http, note=""):
        row = {"ts": _now(), "kind": call.kind, "shape": call.shape(), "tid": call.tid, "query": call.query, "page": call.page, "extra": dict(call.extra),
               "price_rs": call.price, "outcome": outcome, "http": http, "note": self._scrub(note)[:300]}
        os.makedirs(os.path.dirname(os.path.abspath(self.ledger_path)), exist_ok=True)
        with open(self.ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def _cache_path(self, call):
        h = hashlib.sha256(call.key().encode()).hexdigest()[:10]
        plain = call.tid and not call.query and not call.extra
        return os.path.join(self.cache_dir, call.kind, f"{call.tid}.json" if plain else f"{call.tid or 'q'}_{h}.json")

    def cached(self, call):
        p = self._cache_path(call)
        if not os.path.exists(p):
            return None
        try:
            with open(p, encoding="utf-8") as fh:
                rec = json.load(fh)
            if rec["request"] == call.request() and "response" in rec:
                return rec
        except (ValueError, KeyError, OSError):
            pass
        self.log(f"cache file {p} is unreadable or does not match its request; treated as not cached")
        return None

    def _write_cache(self, call, response, http, price):
        p = self._cache_path(call)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = os.path.join(os.path.dirname(p), ".tmp-" + os.path.basename(p))
        rec = {"request": call.request(), "fetched_at": _now(), "http": http, "price_rs": price, "response": response}
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, p)
        return rec

    def _scrub(self, s):
        s = str(s)
        return s.replace(self._key.reveal(), "<IK key>") if self._key else s

    # ------------------------------------------------------------------------------------------------------------------------ planning
    def plan(self, calls, run_cap_rs):
        seen, items = set(), []
        for c in calls:
            if c.key() not in seen:
                seen.add(c.key())
                items.append(PlanItem(c, self.cached(c) is not None))
        spent = self.spent_total()
        pl = Plan(items, float(run_cap_rs), spent, [])
        if os.path.exists(self.stop_file):
            pl.problems.append(f"the file {self.stop_file} exists; remove it to allow calls")
        if pl.cost > pl.run_cap_rs + 1e-9:
            pl.problems.append(f"the plan costs Rs {pl.cost:.2f}, over the run cap of Rs {pl.run_cap_rs:.2f}")
        if spent + pl.cost > TOTAL_CAP_RS + 1e-9:
            pl.problems.append(f"Rs {spent:.2f} already spent plus Rs {pl.cost:.2f} would pass the total cap of Rs {TOTAL_CAP_RS:.2f}")
        confirmed = self.confirmed_shapes()
        per_shape = {}
        for i in items:
            if not i.cached:
                per_shape[i.call.shape()] = per_shape.get(i.call.shape(), 0) + 1
        for shape, n in sorted(per_shape.items()):
            if shape not in confirmed and n > 1:
                pl.problems.append(f"'{shape}' has no successful call in the ledger yet; plan one call of it first, read its real answer, then plan the rest ({n} planned)")
        return pl

    # ------------------------------------------------------------------------------------------------------------------------ running
    def run(self, calls, run_cap_rs, approved_rs):
        """Make the planned calls that are not cached. Raises IKPlanError (nothing sent) unless the plan is clean and approved_rs equals its cost. Returns {call.key(): cache record}.
        The first error of any kind stops the run; what was fetched before it is already saved."""
        pl = self.plan(calls, run_cap_rs)
        if pl.problems:
            raise IKPlanError("; ".join(pl.problems))
        if pl.cost > 0 and (approved_rs is None or round(float(approved_rs), 2) != pl.cost):
            raise IKPlanError(f"the plan costs Rs {pl.cost:.2f} and the approved amount is {approved_rs!r}; run `plan`, read it, and pass its cost as the approval")
        if pl.n_calls and not self._key:
            raise IKError(self._key_problem or f"{KEY_ENV} is not set in the environment")
        out, run_spent, made = {}, 0.0, 0
        for item in pl.items:
            c = item.call
            if item.cached:
                out[c.key()] = self.cached(c)
                if out[c.key()] is None:
                    raise IKPlanError(f"the cache entry for {c.label()} disappeared after the plan was made; plan again")
                continue
            if os.path.exists(self.stop_file):
                raise IKPlanError(f"the file {self.stop_file} appeared; stopped after {made} calls (Rs {run_spent:.2f})")
            if run_spent + c.price > float(run_cap_rs) + 1e-9 or self.spent_total() + c.price > TOTAL_CAP_RS + 1e-9:
                raise IKPlanError(f"a cap would be passed by the next call; stopped after {made} calls (Rs {run_spent:.2f})")
            try:
                out[c.key()] = self._fetch(c)
            except IKError as e:
                self.log(f"STOPPED after {made} calls (Rs {run_spent:.2f} this run): {e}")
                raise
            made += 1
            run_spent += c.price
        self.log(f"done: {made} calls made, Rs {run_spent:.2f} this run, Rs {self.spent_total():.2f} in total, {pl.n_cached} served from the cache")
        return out

    def _throttle(self):
        if self._last_start is not None:
            wait = self.min_gap - (self._clock() - self._last_start)
            if wait > 0:
                self._sleep(wait)
        self._last_start = self._clock()

    def _fetch(self, call):
        self._throttle()
        headers = {"Authorization": "Token " + self._key.reveal(), "Accept": "application/json"}
        url = self.base_url + call.path()
        try:
            status, text = self._transport("POST", url, headers, call.params(), TIMEOUT_SECONDS)
        except Exception as e:                                                # may have been processed; counted as spent
            self._append_ledger(call, "unknown", None, f"{type(e).__name__}: {e}")
            raise IKBadResponse(f"no readable answer to {call.label()} ({type(e).__name__}); it may have been charged and is counted as spent") from None
        text = text if isinstance(text, str) else str(text)
        if status in (401, 403):
            self._append_ledger(call, "error", status, "auth")
            raise IKAuthError(f"authentication refused (HTTP {status}) on {call.label()}")
        if status == 429:
            self._append_ledger(call, "error", status, "rate limited")
            raise IKRateLimited(f"rate limited (HTTP 429) on {call.label()}; not retried")
        low = text.lower()
        if status == 402 or (status != 200 and ("balance" in low or "insufficient" in low or "credit" in low)):
            self._append_ledger(call, "error", status, "balance")
            raise IKBalanceError(f"balance problem (HTTP {status}) on {call.label()}: {self._scrub(text[:200])!r}")
        if status != 200:
            self._append_ledger(call, "error", status, "unexpected status")
            raise IKBadResponse(f"HTTP {status} on {call.label()}: {self._scrub(text[:200])!r}")
        try:
            resp = json.loads(self._scrub(text))
        except ValueError:
            self._append_ledger(call, "unknown", status, "200 but not JSON")
            raise IKBadResponse(f"HTTP 200 but not JSON on {call.label()}; counted as spent: {self._scrub(text[:200])!r}") from None
        if isinstance(resp, dict) and resp.get("errmsg"):
            self._append_ledger(call, "error", status, "errmsg: " + str(resp["errmsg"]))
            raise IKBadResponse(f"IK reported an error on {call.label()}: {self._scrub(str(resp['errmsg'])[:200])!r}")
        self._append_ledger(call, "ok", status)
        return self._write_cache(call, resp, status, call.price)

    def record_manual(self, call, response, note, http=200):
        """Put a call that was made by hand (Phase 0) into the ledger and the cache, so it is counted and not repeated."""
        self._append_ledger(call, "ok", http, note)
        self._write_cache(call, response, http, call.price)

    def status(self):
        rows = self.ledger()
        by = {}
        for r in rows:
            d = by.setdefault(r["shape"], {"calls": 0, "ok": 0, "rs": 0.0})
            d["calls"] += 1
            d["ok"] += r.get("outcome") == "ok"
            d["rs"] = round(d["rs"] + self._spent(r), 2)
        return {"spent_rs": self.spent_total(), "total_cap_rs": TOTAL_CAP_RS, "left_under_cap_rs": round(TOTAL_CAP_RS - self.spent_total(), 2), "calls": len(rows),
                "by_shape": by, "confirmed_shapes": sorted(self.confirmed_shapes()), "key": "set" if self._key else (self._key_problem or "NOT set"),
                "stop_file": os.path.exists(self.stop_file)}


def _requests_transport(method, url, headers, params, timeout):
    """The one place that touches the network. Redirects are not followed: a redirect would resend the key somewhere else."""
    import requests
    r = requests.request(method, url, headers=headers, params=params, timeout=timeout, allow_redirects=False)
    return r.status_code, r.text
