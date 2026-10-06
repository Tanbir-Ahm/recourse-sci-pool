"""Indian Kanoon (IK) API client with guard rails. Every call costs real money, so nothing here spends without a plan, a cap and an explicit approval.

What it enforces (IK_PLAN.md, Phase 1; hardened after an adversarial review the same day):

    key         read from the environment only (INDIANKANOON_API_KEY, letters, digits, '.', '_' and '-' only); held in a wrapper that prints as <IK key>; sent only to
                api.indiankanoon.org, as the Authorization header; scrubbed (before any shortening) from every message, ledger line and cache file; redirects are never followed
    dry run     `plan` lists every call with its price and a plan id; `run` spends nothing unless the approved amount equals the plan's cost AND the plan id matches
                (so an approval cannot be reused for a different list of the same cost)
    caps        a hard rupee cap for this run (finite, checked again before every call) and TOTAL_CAP_RS across all runs; the ledger is the memory; a missing ledger refuses (CLI)
    ledger      the attempt is written BEFORE the call is sent and its result after, so a crash, an interrupt or a failed write never leaves a charged call unrecorded; a call
                with no recorded result counts as spent. Folders are checked writable before the first call
    cache       each raw response is saved the first time and read from disk afterwards; the rejected answers are kept in ik_cache/_rejected/ so IK's real error shapes can be learned.
                The cache folder does not survive a new session, so the plan REFUSES a call the ledger says was paid for but the cache lacks, unless refetch is asked for
    stop        the first auth, balance, rate-limit, server, redirect, unreadable or invalid answer ends the run; no retry. A call that failed before, or a kind of call whose
                probe failed, is refused again unless retry_failed is asked for
    valid       a 200 answer counts as a success only if it is a non-empty JSON object with none of the fields errmsg, error, errors, message, detail, and (meta) the fields seen in
                the real answer, (search) a 'docs' list
    probe first a kind of call (a "shape": the kind plus its extra parameters and their values) can be planned as a single call until the OWNER has read the dashboard price and
                recorded it (`confirm_price`); only then may it be planned in batches. A price that later changes in the table lapses the confirmation
    lock        one run at a time (a lock file next to the ledger); the cache is checked again before every call
    throttle    calls are serial, with a gap between their starts
    stop file   a file named IK_STOP in the repository folder or the working folder refuses every call

The ledger (goodlaw/data/ik_ledger.jsonl) holds attempts, their results and the owner's price confirmations. It holds no key and no IK text (notes are fixed words) and is committed. The
cache (ik_cache/, git-ignored) holds raw responses, which may be IK text, and is never committed; where fetched text may be kept is a Phase 4 decision. Results worth keeping across
sessions (counts, ids) must be written to a committed file by the caller, since the cache is lost.

Money rules: an "ok" call counts at its listed price; so does a call whose result is missing or unreadable (it may have been charged), and an HTTP error other than 401, 402, 403 and 429
(a 404 or 500 may still be charged; not verified). Only a call that never left (a failed connection or TLS handshake) and the refusals 401, 402, 403 and 429 count nothing. Prices are
those IK published on 2026-10-06 and may change on a week's notice; only 'meta' has been confirmed on the dashboard (Rs 391.16 to 391.14).

Not built, on purpose: parallel calls, retries, the Original Document call, anything that reads the key from a file. The key cannot be hidden from code that inspects this process
(the wrapper only stops it being printed or logged).
"""
import contextlib
import dataclasses
import hashlib
import json
import math
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

HOST = "api.indiankanoon.org"
BASE_URL = "https://" + HOST
KEY_ENV = "INDIANKANOON_API_KEY"
STOP_FILE = "IK_STOP"
TOTAL_CAP_RS = 150.0               # the checker's total across all runs (IK_PLAN.md budget rule); raising it is a deliberate edit, visible in git
MIN_GAP_SECONDS = 0.5              # between the starts of two calls
CONNECT_SECONDS, READ_SECONDS, TOTAL_SECONDS = 10, 30, 60
MAX_BYTES = 8_000_000
KEY_RE = re.compile(r"[A-Za-z0-9._-]{8,200}")
ERROR_KEYS = ("errmsg", "error", "errors", "message", "detail")
NOT_CHARGED_HTTP = (401, 402, 403, 429)            # refusals: nothing was processed
OUTCOMES = ("pending", "ok", "error", "unknown", "notsent")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
DEFAULT_LEDGER = os.path.join(HERE, "data", "ik_ledger.jsonl")
DEFAULT_CACHE = os.path.join(REPO_ROOT, "ik_cache")
SAMPLE_DIR = os.path.join(HERE, "data")             # committed real answers (metadata only) that stand in for a lost cache, named ik_sample_docmeta_<tid>.json

# kind -> endpoint, price in rupees per call, what the call needs, and the extra parameters it may carry. All calls are POST with the parameters in the query string, as
# Recourse's own client does (that client worked against the live API). 'meta' is confirmed against the real API (Phase 0). 'doc' and 'search' follow Recourse's client and IK's
# price page. 'fragment' and the extra parameters of 'doc' are NOT verified: their paths and parameter names come from memory of IK's documentation, which is why a first call of
# each runs alone and its price must be confirmed by the owner before more are planned.
KINDS = {
    "meta":     {"path": "/docmeta/{tid}/",     "price": 0.02, "needs": "tid",       "extras": ()},
    "doc":      {"path": "/doc/{tid}/",         "price": 0.20, "needs": "tid",       "extras": ("maxcites", "maxcitedby")},
    "fragment": {"path": "/docfragment/{tid}/", "price": 0.05, "needs": "tid+query", "extras": ()},
    "search":   {"path": "/search/",            "price": 0.50, "needs": "query",     "extras": ()},
}
TID_RE = re.compile(r"[1-9][0-9]{0,11}")          # ASCII digits only, no leading zero: one document, one spelling
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
    """A redirect, a server error, an answer that is not JSON or not a valid answer, or a call with no readable answer."""


class NotSent(Exception):
    """Raised by a transport when the request certainly never left (a failed connection or TLS handshake)."""


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
        tid = self.tid if isinstance(self.tid, str) else ("" if self.tid in (None, "") else str(self.tid))
        object.__setattr__(self, "tid", tid)
        if "tid" in needs and not TID_RE.fullmatch(tid):
            raise ValueError(f"{self.kind} needs a numeric tid of 1 to 12 ASCII digits without a leading zero, got {tid!r}")
        if "tid" not in needs and tid:
            raise ValueError(f"{self.kind} takes no tid")
        query = " ".join(self.query.split()) if isinstance(self.query, str) else self.query      # one spelling per query
        object.__setattr__(self, "query", query)
        if "query" in needs and not (isinstance(query, str) and query and len(query) <= MAX_QUERY):
            raise ValueError(f"{self.kind} needs a query of at most {MAX_QUERY} characters")
        if "query" not in needs and query:
            raise ValueError(f"{self.kind} takes no query")
        if not (isinstance(self.page, int) and not isinstance(self.page, bool) and 0 <= self.page <= 1000):
            raise ValueError("page must be an integer from 0 to 1000")
        if self.page and self.kind != "search":
            raise ValueError("only search takes a page")
        pairs = self.extra.items() if isinstance(self.extra, dict) else self.extra
        extra = tuple(sorted((str(k), v) for k, v in pairs))
        if len({k for k, _ in extra}) != len(extra):
            raise ValueError("a parameter is given twice")
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
        """The kind plus its extra parameters and their values: what has to have worked, and had its price confirmed, before it is repeated."""
        return self.kind + "".join(f"+{k}={v}" for k, v in self.extra)

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


def _count(v, name, top=10 ** 7):
    """A count or an id from an answer: an int, or digits, between 0 and top; anything else is IKBadResponse."""
    if isinstance(v, bool) or not (isinstance(v, int) or (isinstance(v, str) and v.isascii() and v.isdigit() and len(v) <= 13)) or not 0 <= int(v) <= top:
        raise IKBadResponse(f"a /docmeta/ answer whose {name} is {str(v)[:30]!r}, not a count")
    return int(v)


def parse_meta(resp):
    """The fields of a /docmeta/ answer, as seen in the real Phase 0 response (tid 151036912, 2026-10-06). Raises IKBadResponse (never another error) if the shape differs, so a change
    at IK is noticed rather than read as zeros."""
    need = ("tid", "publishdate", "doctype", "title", "numcites", "numcitedby")
    if not isinstance(resp, dict) or any(k not in resp for k in need):
        raise IKBadResponse(f"a /docmeta/ answer without the fields {need}: got {sorted(resp) if isinstance(resp, dict) else type(resp).__name__}")
    for k in ("publishdate", "doctype", "title"):
        if not isinstance(resp[k], str):
            raise IKBadResponse(f"a /docmeta/ answer whose {k} is not text")
    return {"tid": str(_count(resp["tid"], "tid", 10 ** 12)), "date": resp["publishdate"], "doctype": resp["doctype"], "title": resp["title"], "caseno": resp.get("caseno"),
            "numcites": _count(resp["numcites"], "numcites"), "numcitedby": _count(resp["numcitedby"], "numcitedby"), "relurl": resp.get("relurl")}


def _answer_problem(call, resp):
    """Why a parsed 200 answer is not a success, or None. Unknown error shapes are the reason for the field list; the real shapes of doc, fragment and search are learned from the
    first call of each, which a person reads."""
    if not isinstance(resp, dict) or not resp:
        return "the answer is not a non-empty JSON object"
    bad = [k for k in ERROR_KEYS if k in resp]
    if bad:
        return "the answer carries an error field (" + ", ".join(bad) + ")"
    if call.kind == "meta":
        try:
            parse_meta(resp)
        except IKBadResponse as e:
            return str(e)
    if call.kind == "search" and not isinstance(resp.get("docs"), list):
        return "a search answer without a 'docs' list"
    return None


def _finite_rs(x, what):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0:
        raise IKPlanError(f"{what} must be a finite, non-negative number of rupees, got {x!r}")
    return float(x)


# ---------------------------------------------------------------------------------------------------------------------------- the plan
@dataclasses.dataclass
class PlanItem:
    call: Call
    cached: bool
    note: str = ""

    @property
    def price(self):
        return 0.0 if self.cached else self.call.price


@dataclasses.dataclass
class Plan:
    items: list
    run_cap_rs: float
    spent_before_rs: float
    problems: list
    confirmed: frozenset = frozenset()

    @property
    def cost(self):
        return round(sum(i.price for i in self.items), 2)

    @property
    def n_calls(self):
        return sum(1 for i in self.items if not i.cached)

    @property
    def n_cached(self):
        return sum(1 for i in self.items if i.cached)

    @property
    def plan_id(self):
        """Names exactly these calls at this cost; `run` must be given it back, so an approval cannot be used for another list."""
        keys = sorted(i.call.key() for i in self.items if not i.cached)
        return hashlib.sha256(("\n".join(keys) + f"|{self.cost:.2f}").encode()).hexdigest()[:8]

    def text(self):
        out = [f"DRY RUN: {len(self.items)} distinct calls, {self.n_cached} already cached (free), {self.n_calls} to make"]
        for i in self.items:
            mark = "" if i.cached or i.call.shape() in self.confirmed else "   [price NOT confirmed on the dashboard]"
            out.append(f"  {'cached  ' if i.cached else 'CALL    '} Rs {i.price:5.2f}  {i.call.label()}{mark}{('   [' + i.note + ']') if i.note else ''}")
        out.append(f"COST OF THIS PLAN: Rs {self.cost:.2f}   plan id {self.plan_id}   (run cap Rs {self.run_cap_rs:.2f}; spent so far by this client Rs {self.spent_before_rs:.2f} of Rs {TOTAL_CAP_RS:.2f})")
        for p in self.problems:
            out.append("REFUSED: " + p)
        if not self.problems and self.n_calls:
            out.append(f"To spend it, run with --approved-rs {self.cost:.2f} --plan-id {self.plan_id}")
        return "\n".join(out)


class Client:
    def __init__(self, env=None, cache_dir=DEFAULT_CACHE, ledger_path=DEFAULT_LEDGER, base_url=BASE_URL, allow_test_base=False, transport=None, clock=time.monotonic,
                 sleep=time.sleep, min_gap=MIN_GAP_SECONDS, stop_file=None, log=None, require_ledger=False, sample_dir=SAMPLE_DIR):
        env = os.environ if env is None else env
        raw = env.get(KEY_ENV)
        self._key_problem = None
        if raw and not KEY_RE.fullmatch(raw):
            raw, self._key_problem = None, f"{KEY_ENV} is set but is not 8 to 200 letters, digits, '.', '_' or '-' (the value is not shown)"
        self._key = _Secret(raw) if raw else None
        if base_url != BASE_URL:
            u = urlsplit(base_url)
            if not (allow_test_base and u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost") and u.username is None and u.password is None):
                raise IKError(f"the key is only ever sent to {BASE_URL}")
        self.base_url = base_url.rstrip("/")
        self.cache_dir, self.ledger_path, self.sample_dir = cache_dir, ledger_path, sample_dir
        self.require_ledger = require_ledger
        self._transport = transport or _requests_transport
        self._clock, self._sleep, self.min_gap = clock, sleep, min_gap
        self._last_start = None
        self._stop_files = [stop_file] if stop_file else [os.path.join(REPO_ROOT, STOP_FILE), os.path.join(os.getcwd(), STOP_FILE)]
        self.log = log or (lambda m: print(m, file=sys.stderr))

    def __repr__(self):
        return f"<ik.Client {self.base_url} key={'set' if self._key else 'NOT set'}>"

    def _stopped(self):
        return next((f for f in self._stop_files if os.path.exists(f)), None)

    # ------------------------------------------------------------------------------------------------------------------------ ledger
    def ledger(self):
        rows = []
        if os.path.exists(self.ledger_path):
            with open(self.ledger_path, encoding="utf-8") as fh:
                for n, line in enumerate(fh, 1):
                    if not line.strip():
                        continue
                    try:
                        r = json.loads(line)
                        t = r["type"]
                        if t == "attempt":
                            ok = (isinstance(r["id"], str) and r["kind"] in KINDS and isinstance(r["key"], str) and isinstance(r["shape"], str) and r.get("outcome") == "pending"
                                  and isinstance(r["price_rs"], (int, float)) and math.isfinite(r["price_rs"]) and 0 <= r["price_rs"] <= 10)
                        elif t == "result":
                            ok = isinstance(r["id"], str) and r["outcome"] in OUTCOMES and r["outcome"] != "pending"
                        elif t == "price_confirmed":
                            ok = isinstance(r["shape"], str) and isinstance(r["price_rs"], (int, float)) and math.isfinite(r["price_rs"])
                        else:
                            ok = False
                    except (ValueError, KeyError, TypeError):
                        ok = False
                    if not ok:
                        raise IKError(f"{self.ledger_path} line {n} is not a valid ledger row; refusing to spend with a damaged ledger")
                    rows.append(r)
        return rows

    def attempts(self, rows=None):
        by = {}
        for r in (self.ledger() if rows is None else rows):
            if r["type"] == "attempt":
                by[r["id"]] = dict(r, http=None, note="")
            elif r["type"] == "result":
                if r["id"] not in by:
                    raise IKError(f"{self.ledger_path} has a result for an attempt it does not list; refusing to spend with a damaged ledger")
                by[r["id"]].update(outcome=r["outcome"], http=r.get("http"), note=r.get("note", ""))
        return list(by.values())

    @staticmethod
    def _spent(a):
        if a["outcome"] in ("pending", "ok", "unknown"):
            return a["price_rs"]
        if a["outcome"] == "error":
            return 0.0 if a.get("http") in NOT_CHARGED_HTTP else a["price_rs"]
        return 0.0

    def spent_total(self):
        return round(float(sum(self._spent(a) for a in self.attempts())), 2)

    def confirmed_shapes(self, rows=None):
        rows = self.ledger() if rows is None else rows
        answered = {a["shape"] for a in self.attempts(rows) if a["outcome"] == "ok"}
        conf = {r["shape"]: r["price_rs"] for r in rows if r["type"] == "price_confirmed"}
        return {s for s in answered if s in conf and s.split("+")[0] in KINDS and abs(conf[s] - KINDS[s.split("+")[0]]["price"]) < 1e-9}

    def _append(self, row):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.ledger_path)), exist_ok=True)
            with open(self.ledger_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        except OSError as e:
            raise IKError(f"cannot write the ledger ({type(e).__name__}); stopping") from None

    def _attempt(self, call):
        aid = uuid.uuid4().hex[:12]
        self._append({"type": "attempt", "id": aid, "ts": _now(), "kind": call.kind, "shape": call.shape(), "key": call.key(), "tid": call.tid, "query": call.query,
                      "page": call.page, "extra": dict(call.extra), "price_rs": call.price, "outcome": "pending"})
        return aid

    def _result(self, aid, outcome, http, note):
        self._append({"type": "result", "id": aid, "ts": _now(), "outcome": outcome, "http": http, "note": note})

    def confirm_price(self, shape, price_rs, note):
        """The owner's record that a call of this shape was answered and that the dashboard showed this price per call. The price must equal the table's, so a different real price has
        to be put into KINDS first, where it shows in git."""
        kind = shape.split("+")[0]
        if kind not in KINDS:
            raise IKError(f"unknown shape {shape!r}")
        if shape not in {a["shape"] for a in self.attempts() if a["outcome"] == "ok"}:
            raise IKError(f"no answered call of shape {shape!r} in the ledger; make the single probe call first")
        if abs(float(price_rs) - KINDS[kind]["price"]) > 1e-9:
            raise IKError(f"the dashboard price Rs {float(price_rs):.2f} differs from the table's Rs {KINDS[kind]['price']:.2f}; correct KINDS['{kind}']['price'] first")
        self._append({"type": "price_confirmed", "ts": _now(), "shape": shape, "price_rs": float(price_rs), "note": note})

    def record_manual(self, call, response, note, confirm_price=False):
        """Put a call that was made by hand (Phase 0) into the ledger and the cache, so it is counted and not repeated."""
        aid = self._attempt(call)
        self._write_cache(call, response, 200, call.price)
        self._result(aid, "ok", 200, note)
        if confirm_price:
            self.confirm_price(call.shape(), call.price, note)

    # ------------------------------------------------------------------------------------------------------------------------ cache
    def _cache_path(self, call):
        h = hashlib.sha256(call.key().encode()).hexdigest()[:10]
        plain = call.tid and not call.query and not call.extra
        return os.path.join(self.cache_dir, call.kind, f"{call.tid}.json" if plain else f"{call.tid or 'q'}_{h}.json")

    def _sample(self, call):
        if call.kind == "meta" and not call.query and not call.extra and self.sample_dir:
            p = os.path.join(self.sample_dir, f"ik_sample_docmeta_{call.tid}.json")
            if os.path.exists(p):
                try:
                    with open(p, encoding="utf-8") as fh:
                        resp = json.load(fh)
                    if _answer_problem(call, resp) is None and str(resp.get("tid")) == call.tid:
                        return {"request": call.request(), "fetched_at": "committed sample", "http": 200, "price_rs": call.price, "response": resp}
                except (ValueError, OSError):
                    pass
        return None

    def cached(self, call):
        p = self._cache_path(call)
        if not os.path.exists(p):
            return self._sample(call)
        try:
            with open(p, encoding="utf-8") as fh:
                rec = json.load(fh)
            if rec["request"] == call.request() and "response" in rec:
                return rec
        except (ValueError, KeyError, TypeError, OSError):
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

    def _reject(self, aid, call, http, text):
        """Keep an answer that was refused, so that IK's real error shapes can be read later. Never stops the run if it cannot be written."""
        try:
            d = os.path.join(self.cache_dir, "_rejected")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, aid + ".json"), "w", encoding="utf-8") as fh:
                json.dump({"request": call.request(), "http": http, "text": self._scrub(text)[:20000]}, fh, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def _scrub(self, s):
        s = str(s)
        return s.replace(self._key.reveal(), "<IK key>") if self._key else s

    def _preflight(self):
        """Both folders must be writable before the first call: a charged answer that cannot be recorded is the worst case."""
        for d in (self.cache_dir, os.path.dirname(os.path.abspath(self.ledger_path))):
            try:
                os.makedirs(d, exist_ok=True)
                t = os.path.join(d, ".tmp-preflight")
                with open(t, "w") as fh:
                    fh.write("x")
                os.remove(t)
            except OSError as e:
                raise IKPlanError(f"{d} is not writable ({type(e).__name__}); nothing was sent") from None

    @contextlib.contextmanager
    def _lock(self):
        path = self.ledger_path + ".lock"
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as e:
            if os.path.exists(path):
                raise IKPlanError(f"another run is in progress, or one crashed and left {path}; check, then delete that file") from None
            raise IKPlanError(f"the ledger folder {os.path.dirname(path)} cannot be used ({type(e).__name__}); nothing was sent") from None
        except OSError as e:
            raise IKPlanError(f"the ledger folder {os.path.dirname(path)} is not writable ({type(e).__name__}); nothing was sent") from None
        try:
            os.write(fd, f"{os.getpid()} {_now()}\n".encode())
            os.close(fd)
            yield
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

    # ------------------------------------------------------------------------------------------------------------------------ planning
    def plan(self, calls, run_cap_rs, retry_failed=False, refetch=False):
        cap = _finite_rs(run_cap_rs, "the run cap")
        rows = self.ledger()
        attempts = self.attempts(rows)
        ok_keys = {a["key"] for a in attempts if a["outcome"] == "ok"}
        failed_keys = {a["key"] for a in attempts if a["outcome"] in ("error", "unknown", "pending")} - ok_keys
        ok_shapes = {a["shape"] for a in attempts if a["outcome"] == "ok"}
        failed_shapes = {a["shape"] for a in attempts if a["outcome"] in ("error", "unknown", "pending")} - ok_shapes
        confirmed = self.confirmed_shapes(rows)
        seen, items = set(), []
        for c in calls:
            if c.key() not in seen:
                seen.add(c.key())
                items.append(PlanItem(c, self.cached(c) is not None))
        spent = round(float(sum(self._spent(a) for a in attempts)), 2)
        pl = Plan(items, cap, spent, [], frozenset(confirmed))
        stop = self._stopped()
        if stop:
            pl.problems.append(f"the file {stop} exists; remove it to allow calls")
        if not (pl.cost <= cap + 1e-9):
            pl.problems.append(f"the plan costs Rs {pl.cost:.2f}, over the run cap of Rs {cap:.2f}")
        if not (spent + pl.cost <= TOTAL_CAP_RS + 1e-9):
            pl.problems.append(f"Rs {spent:.2f} already spent plus Rs {pl.cost:.2f} would pass the total cap of Rs {TOTAL_CAP_RS:.2f}")
        per_shape = {}
        for i in items:
            if not i.cached:
                per_shape[i.call.shape()] = per_shape.get(i.call.shape(), 0) + 1
        answered_before = {s: sum(1 for a in attempts if a["outcome"] == "ok" and a["shape"] == s) for s in per_shape}
        for shape, n in sorted(per_shape.items()):
            if shape not in confirmed and answered_before[shape] + n > 1:
                pl.problems.append(f"'{shape}' has no confirmed price: one call may be made ({answered_before[shape]} answered so far, {n} planned); read its answer and the dashboard, "
                                   f"then record the price (confirm_price) before planning more")
        refetch_n = [i for i in items if not i.cached and i.call.key() in ok_keys]
        for i in refetch_n:
            i.note = "paid before; not in the cache"
        if refetch_n and not refetch:
            pl.problems.append(f"{len(refetch_n)} planned call(s) were paid for before but their answers are not in the cache (it does not survive a new session): "
                               f"{', '.join(i.call.label() for i in refetch_n[:3])}{'...' if len(refetch_n) > 3 else ''}; pay again only with refetch")
        redo = [i for i in items if not i.cached and (i.call.key() in failed_keys or (i.call.shape() in failed_shapes and i.call.shape() not in confirmed))]
        for i in redo:
            i.note = "failed before"
        if redo and not retry_failed:
            pl.problems.append(f"{len(redo)} planned call(s) (or their first-of-a-kind probe) failed before and were never answered: "
                               f"{', '.join(i.call.label() for i in redo[:3])}{'...' if len(redo) > 3 else ''}; read the rejected answer in the cache, then retry only with retry_failed")
        return pl

    # ------------------------------------------------------------------------------------------------------------------------ running
    def run(self, calls, run_cap_rs, approved_rs, plan_id=None, retry_failed=False, refetch=False):
        """Make the planned calls that are not cached. Raises IKPlanError (nothing sent) unless the plan is clean and approved_rs equals its cost and plan_id is its id. Returns
        {call.key(): cache record}. The first error of any kind stops the run; what was fetched before it is already saved."""
        with self._lock():
            pl = self.plan(calls, run_cap_rs, retry_failed, refetch)
            if pl.problems:
                raise IKPlanError("; ".join(pl.problems))
            if pl.cost > 0:
                good = (not isinstance(approved_rs, bool) and isinstance(approved_rs, (int, float)) and math.isfinite(approved_rs) and round(float(approved_rs), 2) == pl.cost)
                if not good:
                    raise IKPlanError(f"the plan costs Rs {pl.cost:.2f} and the approved amount is {approved_rs!r}; run `plan`, read it, and pass its cost")
                if plan_id != pl.plan_id:
                    raise IKPlanError(f"the plan id is {pl.plan_id}, not {plan_id!r}: the approval was not given for this list of calls; run `plan` again")
            if pl.n_calls and not self._key:
                raise IKError(self._key_problem or f"{KEY_ENV} is not set in the environment")
            if self.require_ledger and not os.path.exists(self.ledger_path):
                raise IKPlanError(f"the ledger {self.ledger_path} is missing; without it the total cap and the confirmed prices are forgotten, so nothing is spent")
            if pl.n_calls:
                self._preflight()
            cap = _finite_rs(run_cap_rs, "the run cap")
            out, run_spent, made = {}, 0.0, 0
            for item in pl.items:
                c = item.call
                if self.cached(c) is not None:                        # also covers an answer that appeared since the plan was made
                    out[c.key()] = self.cached(c)
                    continue
                if item.cached:
                    raise IKPlanError(f"the cache entry for {c.label()} disappeared after the plan was made; plan again")
                stop = self._stopped()
                if stop:
                    raise IKPlanError(f"the file {stop} appeared; stopped after {made} calls (Rs {run_spent:.2f})")
                if not (run_spent + c.price <= cap + 1e-9) or not (self.spent_total() + c.price <= TOTAL_CAP_RS + 1e-9):      # defence in depth: the plan already checked both
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
        aid = self._attempt(call)                                      # written before anything is sent; no result means 'counted as spent'
        headers = {"Authorization": "Token " + self._key.reveal(), "Accept": "application/json"}
        url = self.base_url + call.path()
        try:
            status, text = self._transport("POST", url, headers, call.params(), READ_SECONDS)
        except NotSent as e:
            self._result(aid, "notsent", None, "not sent: " + type(e.__cause__ or e).__name__)
            raise IKBadResponse(f"{call.label()} was not sent ({type(e.__cause__ or e).__name__}); nothing was charged") from None
        except Exception as e:                                         # may have been processed; counted as spent
            self._result(aid, "unknown", None, "no readable answer: " + type(e).__name__)
            raise IKBadResponse(f"no readable answer to {call.label()} ({type(e).__name__}); it may have been charged and is counted as spent") from None
        text = self._scrub(text if isinstance(text, str) else str(text))
        short = text[:200]                                             # scrubbed before it is shortened
        if status in (401, 403):
            self._result(aid, "error", status, "auth")
            self._reject(aid, call, status, text)
            raise IKAuthError(f"authentication refused (HTTP {status}) on {call.label()}")
        if status == 429:
            self._result(aid, "error", status, "rate limited")
            raise IKRateLimited(f"rate limited (HTTP 429) on {call.label()}; not retried")
        low = text.lower()
        balance = "balance" in low or "insufficient" in low or "credit" in low
        if status == 402 or (status != 200 and balance):
            self._result(aid, "error", status, "balance")
            self._reject(aid, call, status, text)
            raise IKBalanceError(f"balance problem (HTTP {status}) on {call.label()}: {short!r}")
        if status != 200:
            self._result(aid, "error", status, "unexpected status")
            self._reject(aid, call, status, text)
            raise IKBadResponse(f"HTTP {status} on {call.label()}: {short!r}")
        try:
            resp = json.loads(text)
        except ValueError:
            self._result(aid, "unknown", status, "200 but not JSON")
            self._reject(aid, call, status, text)
            raise IKBadResponse(f"HTTP 200 but not JSON on {call.label()}; counted as spent: {short!r}") from None
        why = _answer_problem(call, resp)
        if why:
            self._result(aid, "error", status, "invalid answer")
            self._reject(aid, call, status, text)
            if balance:
                raise IKBalanceError(f"an answer that talks of balance on {call.label()}: {short!r}")
            raise IKBadResponse(f"IK answered 200 on {call.label()} but {why}; kept in {os.path.join(self.cache_dir, '_rejected', aid + '.json')}; counted as spent")
        try:
            rec = self._write_cache(call, resp, status, call.price)    # the answer is saved before its 'ok' is recorded: if the ledger write then fails, the attempt still counts
        except OSError as e:
            raise IKError(f"the answer to {call.label()} could not be saved ({type(e).__name__}); counted as spent") from None
        self._result(aid, "ok", status, "")
        return rec

    def status(self):
        rows = self.ledger()
        att = self.attempts(rows)
        by = {}
        for a in att:
            d = by.setdefault(a["shape"], {"calls": 0, "ok": 0, "rs": 0.0})
            d["calls"] += 1
            d["ok"] += a["outcome"] == "ok"
            d["rs"] = round(d["rs"] + self._spent(a), 2)
        spent = round(float(sum(self._spent(a) for a in att)), 2)
        conf = self.confirmed_shapes(rows)
        return {"spent_rs": spent, "total_cap_rs": TOTAL_CAP_RS, "left_under_cap_rs": round(TOTAL_CAP_RS - spent, 2), "calls": len(att), "by_shape": by,
                "confirmed_shapes": sorted(conf), "answered_but_price_not_confirmed": sorted({a["shape"] for a in att if a["outcome"] == "ok"} - conf),
                "failed_or_unrecorded_calls": sum(1 for a in att if a["outcome"] in ("error", "unknown", "pending")),
                "key": "set" if self._key else (self._key_problem or "NOT set"), "stop_file": self._stopped()}


def _requests_transport(method, url, headers, params, timeout):
    """The one place that touches the network. Redirects are not followed (a redirect would resend the key somewhere else); the body is read in pieces with a size limit and an overall
    deadline and decoded strictly as UTF-8; a failure before the request left (connection, proxy refusal, TLS) is NotSent."""
    import requests
    deadline = time.monotonic() + TOTAL_SECONDS
    try:
        with requests.request(method, url, headers=headers, params=params, timeout=(CONNECT_SECONDS, timeout), allow_redirects=False, stream=True) as r:
            body, n = [], 0
            for chunk in r.iter_content(65536):
                n += len(chunk)
                if n > MAX_BYTES:
                    raise ValueError(f"answer longer than {MAX_BYTES} bytes")
                if time.monotonic() > deadline:
                    raise TimeoutError(f"answer not complete after {TOTAL_SECONDS} seconds")
                body.append(chunk)
            status = r.status_code
    except (requests.exceptions.ConnectTimeout, requests.exceptions.SSLError, requests.exceptions.ProxyError) as e:
        raise NotSent(type(e).__name__) from e
    return status, b"".join(body).decode("utf-8-sig")
