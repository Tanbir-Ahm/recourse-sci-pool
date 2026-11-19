#!/usr/bin/env python3
"""The Reading Desk: a small website around the checked-reading pipeline (plan section 11).

  export GEMINI_API_KEY=...            # the model key: only here, never in a file, never printed
  export RD_USERS="name:an-access-code-of-10-or-more-characters"
  python server.py --port 8080         # then open http://127.0.0.1:8080
  python server.py --dev               # this computer only, no sign-in (needs no RD_USERS)

A person signs in, uploads page photos or a PDF, says the language and whether the pages are typed or handwritten, confirms that nothing in them identifies a minor or the victim of a
sexual offence, sees an estimate, and starts the reading. The pipeline (pipeline.py, unchanged) runs in a child process; the page shows its progress and then the result: the English
to read beside the page, a 'Read these first' list, the traffic light and why, the glossary notes, a Word file, the full report and a marking sheet. It is a reading aid: every output
carries "Machine draft. Not a certified translation.", the light is a reading order, and nothing here says a page is correct.

What this is not (read README.md before real client papers): no password reset, no payment, no encryption at rest, no virus scan, no audit of who opened what. Page images go to Google's
Gemini API for reading. Files are deleted RD_RETENTION_HOURS after a job finishes.
"""
import argparse, json, os, re, secrets, shutil, subprocess, sys, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import auth, config, demo, docx_out, results, store as storemod
import harness
from runner import Runner
from store import ACTIVE, day_start, month_start, now_iso

STATIC = os.path.join(HERE, "static")
STATIC_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml"}
PER_PAGE_LOW_INR = 2.0                # the pipeline's own estimate for a sparse page (a short handwritten page: Rs 0.7 a reading, 3 readings and a check; plan 10ao)
PER_PAGE_HIGH_INR = 12.0              # and for a dense one (a full printed page of small type: Rs 3.75 a reading, 3 readings and a check; plan 10i and the first run through this site)
BUDGET_PER_PAGE_INR = 14.0            # the ceiling given to the pipeline per page, so that a dense page can finish
COST_NOTE = "These figures are the pipeline's own estimates. The real bill has run 1.5 to 2 times higher (plan section 10k). A page costs more the more is written on it."
MAX_PIXELS = 80000000
GATE_TEXT = "I confirm that nothing in these pages identifies a minor or the victim of a sexual offence, and that the pages may be sent to Google's Gemini service for reading."
ROUTES = []


class ApiError(Exception):
    def __init__(self, code, msg, close=False):
        Exception.__init__(self, msg)
        self.code, self.msg, self.close = code, msg, close


def route(method, pattern, auth_required=True):
    def deco(fn):
        ROUTES.append((method, re.compile("^" + pattern + "$"), fn, auth_required))
        return fn
    return deco


class App:
    def __init__(self, cfg, start_workers=True):
        self.cfg = cfg
        os.makedirs(cfg.data_dir, mode=0o700, exist_ok=True)
        self.store = storemod.Store(cfg.data_dir)
        self.secret = auth.load_secret(cfg.data_dir)
        self.runner = Runner(cfg, self.store, start_workers)
        self.limiter = auth.LoginLimiter()                               # per address: 8 wrong codes in 10 minutes
        self.name_limiter = auth.LoginLimiter(limit=30)                  # per name: looser, so a stranger cannot lock a real user out by guessing at the name
        self.revoked = {}                                                # signed-out cookies that would otherwise stay valid until they expire: token -> time to forget it
        self.pdf_tools = all(shutil.which(t) for t in ("pdfinfo", "pdftotext", "pdffonts", "pdfimages", "pdftoppm"))
        self.glossary = None

    def key_ready(self):
        return self.cfg.pipeline == "real" and bool(os.environ.get("GEMINI_API_KEY"))

    @staticmethod
    def estimate(pages):
        """The range a job may cost by the pipeline's own estimate: a sparse page to a dense one. The real bill has run 1.5 to 2 times higher."""
        return {"low": round(pages * PER_PAGE_LOW_INR + 1.0, 1), "high": round(pages * PER_PAGE_HIGH_INR + 2.0, 1)}

    def room(self, user, now=None):
        """Rupees this user may still start today and the site may still start this month, after what is spent and what running jobs hold back."""
        c, s = self.cfg, self.store
        day = c.daily_budget - s.spent(user, day_start(now)) - s.reserved(user)
        month = c.monthly_budget - s.spent(None, month_start(now)) - s.reserved(None)
        return {"day": round(day, 2), "month": round(month, 2), "allowed": round(max(0.0, min(c.job_budget, day, month)), 2)}


def clean_name(name):
    name = os.path.basename((name or "").replace("\\", "/"))
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name[:120] or "file"


def safe_filename(label, suffix):
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", label or "").strip("._")[:40] or "reading_desk"
    return base + suffix


def pdf_pages(path):
    try:
        r = subprocess.run(["pdfinfo", path], capture_output=True, text=True, timeout=40)
    except (OSError, subprocess.SubprocessError):
        raise ApiError(415, "This PDF could not be opened.")
    m = re.search(r"^Pages:\s+(\d+)", r.stdout, re.M)
    if r.returncode != 0 or not m or int(m.group(1)) < 1:
        raise ApiError(415, "This PDF could not be opened (it may be damaged or locked).")
    return int(m.group(1))


def check_image(path):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            w, h = im.size
    except Exception:
        raise ApiError(415, "This image could not be read.")
    if w * h > MAX_PIXELS:
        raise ApiError(413, "This image is too large (more than %d million pixels)." % (MAX_PIXELS // 1000000))


def public_meta(app, m):
    keys = ("id", "label", "status", "language", "page_type", "created", "started", "finished", "n_pages", "spent_inr", "budget_inr", "error", "stopped_by_budget", "sense_unrun", "demo", "light_counts", "reviews", "grouped", "gate_at")
    d = {k: m.get(k) for k in keys}
    d["files"] = [{"name": f["original"], "kind": f["kind"], "size": f["size"], "pages": f["pages"]} for f in m.get("files", [])]
    d["estimate"] = app.estimate(m.get("n_pages") or 0)
    base = m.get("finished_epoch") or m.get("created_epoch") or time.time()
    d["delete_after"] = storemod.now_iso(base + (app.cfg.retention_hours if m.get("status") != "draft" else 6) * 3600)
    return d


class Handler(BaseHTTPRequestHandler):
    server_version = "ReadingDesk"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    timeout = 60
    app = None

    # ---- plumbing
    def log_message(self, fmt, *args):
        pass

    def log_request(self, code="-", size="-"):
        sys.stderr.write("%s %s %s %s\n" % (time.strftime("%H:%M:%S"), self.command, urllib.parse.urlsplit(self.path).path, code))

    def do_GET(self): self.dispatch("GET")
    def do_POST(self): self.dispatch("POST")
    def do_PUT(self): self.dispatch("PUT")
    def do_DELETE(self): self.dispatch("DELETE")

    def dispatch(self, method):
        self.body_read = int(self.headers.get("Content-Length") or 0) == 0
        try:
            parts = urllib.parse.urlsplit(self.path)
            path, q = parts.path, urllib.parse.parse_qs(parts.query, keep_blank_values=True)
            self.check_host()
            if method == "GET" and not path.startswith("/api/"):
                return self.static(path)
            for mth, rx, fn, needs in ROUTES:
                mo = rx.match(path) if mth == method else None
                if not mo:
                    continue
                user = self.current_user()
                if needs and not user:
                    raise ApiError(401, "Sign in first.")
                if method != "GET":
                    self.check_origin()
                fn(self, user, mo.groupdict(), q)
                if not self.body_read:                                   # a body the handler did not read would be taken for the start of the next request on this connection
                    self.discard_body()
                return
            raise ApiError(404, "Not found.")
        except ApiError as e:
            try:
                self.send_json({"error": e.msg}, e.code, close=e.close or not self.body_read)
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                self.close_connection = True
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            self.close_connection = True
        except Exception as e:                                           # the person sees a plain message; the operator sees only the kind of error and the path
            sys.stderr.write("error %s on %s\n" % (type(e).__name__, urllib.parse.urlsplit(self.path).path))
            try:
                self.send_json({"error": "Something went wrong on the server."}, 500, close=True)
            except Exception:
                self.close_connection = True

    def discard_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 1048576:
            self.close_connection = True
            return
        while n > 0:
            chunk = self.rfile.read(min(65536, n))
            if not chunk:
                break
            n -= len(chunk)
        self.body_read = True

    def check_host(self):
        if self.app.cfg.dev:                                             # dev mode has no sign-in: only the local names count (a page from another site cannot rebind its name to this port)
            ok = {"127.0.0.1:%d" % self.app.cfg.port, "localhost:%d" % self.app.cfg.port, "[::1]:%d" % self.app.cfg.port}
            if (self.headers.get("Host") or "").lower() not in ok:
                raise ApiError(403, "Use http://127.0.0.1:%d in dev mode." % self.app.cfg.port, close=True)

    def check_origin(self):
        if self.headers.get("X-RD") != "1":
            raise ApiError(403, "This request did not come from the site.", close=True)
        origin = self.headers.get("Origin")
        if origin and "*" not in self.app.cfg.allowed_origins:          # '*' (RD_ALLOWED_ORIGINS=*) skips this comparison; the X-RD header above is the real guard, since another site cannot send it without a CORS pre-flight this server never allows
            host = urllib.parse.urlsplit(origin).netloc.lower()
            ok = {(self.headers.get("Host") or "").lower()} | self.app.cfg.allowed_origins
            if self.app.cfg.trust_proxy and self.headers.get("X-Forwarded-Host"):
                ok.add(self.headers["X-Forwarded-Host"].split(",")[0].strip().lower())
            if host not in ok:
                raise ApiError(403, "This request came from another site.", close=True)

    def current_user(self):
        cfg = self.app.cfg
        if cfg.dev and list(cfg.users) == ["dev"] and cfg.users["dev"] == "":
            return "dev"
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "rd_session":
                if v in self.app.revoked:
                    return None
                u = auth.read_session(self.app.secret, v)
                return u if u in cfg.users else None
        return None

    def cookie_token(self):
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "rd_session":
                return v
        return ""

    def client_ip(self):
        if self.app.cfg.trust_proxy and self.headers.get("X-Forwarded-For"):
            return self.headers["X-Forwarded-For"].split(",")[0].strip()
        return self.client_address[0]

    def owned(self, jid, user):
        m = self.app.store.get(jid)
        if not m or m.get("user") != user:
            raise ApiError(404, "No such job.")
        return m

    def content_length(self, required=False, limit=None):
        raw = self.headers.get("Content-Length")
        if raw is None:
            if required or self.headers.get("Transfer-Encoding"):
                raise ApiError(411, "A length is needed.", close=True)
            return 0
        try:
            n = int(raw)
        except ValueError:
            raise ApiError(400, "Bad length.", close=True)
        if n < 0 or (limit is not None and n > limit):
            raise ApiError(413, "That request is too large.", close=True)
        return n

    def read_json(self, limit=65536):
        n = self.content_length(required=True, limit=limit)
        raw = self.rfile.read(n)
        self.body_read = True
        try:
            d = json.loads(raw.decode("utf8") or "{}")
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "That was not valid JSON.")
        if not isinstance(d, dict):
            raise ApiError(400, "Expected a JSON object.")
        return d

    # ---- responses
    def security_headers(self, kind):
        c = self.app.cfg
        h = [("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "no-referrer"), ("Cache-Control", "no-store" if kind != "static" else "no-cache")]
        csp = {"app": "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; object-src 'none'; frame-ancestors %s" % ("*" if c.allow_framing else "'none'"),
               "api": "default-src 'none'; frame-ancestors 'none'",
               "doc": "sandbox; default-src 'none'; img-src data:; style-src 'unsafe-inline'",
               "sheet": "sandbox allow-scripts allow-downloads; default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; script-src 'unsafe-inline'"}
        h.append(("Content-Security-Policy", csp["app" if kind == "static" else kind]))
        h.append(("X-Robots-Tag", "noindex, nofollow"))
        if c.cookie_secure:                                              # served over HTTPS: the browser must not go back to plain HTTP
            h.append(("Strict-Transport-Security", "max-age=31536000"))
        if not c.allow_framing:
            h.append(("X-Frame-Options", "DENY"))
        return h

    def respond(self, code, body, ctype, kind="api", close=False, headers=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in self.security_headers(kind) + list(headers):
            self.send_header(k, v)
        if close:
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj, code=200, close=False, headers=()):
        self.respond(code, json.dumps(obj, ensure_ascii=False).encode("utf8"), "application/json; charset=utf-8", "api", close, headers)

    def send_file(self, path, ctype, kind, name=None, attachment=False):
        try:
            size = os.path.getsize(path)
            f = open(path, "rb")
        except OSError:
            raise ApiError(404, "That file is not there.")
        with f:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(size))
            for k, v in self.security_headers(kind):
                self.send_header(k, v)
            if name:
                self.send_header("Content-Disposition", '%s; filename="%s"' % ("attachment" if attachment else "inline", name))
            self.end_headers()
            shutil.copyfileobj(f, self.wfile)

    def static(self, path):
        if path == "/healthz":
            return self.respond(200, b"ok", "text/plain; charset=utf-8", "static")
        if path in ("/", "/index.html"):
            path = "/static/index.html"
        mo = re.match(r"^/static/([A-Za-z0-9_.-]+)$", path)
        if not mo or os.path.splitext(mo.group(1))[1] not in STATIC_TYPES:
            raise ApiError(404, "Not found.")
        f = os.path.join(STATIC, mo.group(1))
        self.send_file(f, STATIC_TYPES[os.path.splitext(f)[1]], "static")

    def set_cookie(self, token, max_age):
        c = self.app.cfg
        return [("Set-Cookie", "rd_session=%s; HttpOnly; Path=/; Max-Age=%d; SameSite=%s%s" % (token, max_age, c.samesite, "; Secure" if c.cookie_secure else ""))]


# ---------------------------------------------------------------- session
@route("POST", r"/api/login", auth_required=False)
def api_login(h, user, m, q):
    app, cfg = h.app, h.app.cfg
    d = h.read_json()
    name, code = str(d.get("name", "")).strip().lower(), str(d.get("code", ""))
    ip = h.client_ip()
    if not app.limiter.allowed("ip:" + ip) or not app.name_limiter.allowed("name:" + name):
        sys.stderr.write("login refused (too many wrong codes) from %s\n" % ip)
        raise ApiError(429, "Too many wrong tries. Wait ten minutes.")
    if not auth.check_code(cfg.users, name, code):
        app.limiter.fail("ip:" + ip); app.name_limiter.fail("name:" + name)
        sys.stderr.write("login failed from %s\n" % ip)
        time.sleep(0.4)
        raise ApiError(401, "The name or the access code is not right.")
    app.limiter.ok("ip:" + ip); app.name_limiter.ok("name:" + name)
    h.send_json({"user": name}, headers=h.set_cookie(auth.make_session(app.secret, name, cfg.session_ttl), cfg.session_ttl))


@route("GET", r"/api/public", auth_required=False)
def api_public(h, user, m, q):
    """What anyone may know before signing in: the site's name and how long papers are kept (for the 'How your papers are handled' page)."""
    c = h.app.cfg
    h.send_json({"site_name": c.site_name, "retention_hours": c.retention_hours, "contact": c.contact, "gate_text": GATE_TEXT,
                 "reading": "the model service named on the upload screen" if c.pipeline == "real" else "invented text (test mode)"})


@route("POST", r"/api/logout", auth_required=False)
def api_logout(h, user, m, q):
    tok, now = h.cookie_token(), time.time()
    if tok:
        h.app.revoked = {t: x for t, x in h.app.revoked.items() if x > now}
        h.app.revoked[tok] = now + h.app.cfg.session_ttl + 60
    h.send_json({"ok": True}, headers=h.set_cookie("", 0))


@route("GET", r"/api/me", auth_required=False)
def api_me(h, user, m, q):
    app, cfg = h.app, h.app.cfg
    if not user:
        raise ApiError(401, "Sign in first.")
    room = app.room(user)
    h.send_json({"user": user, "dev": cfg.dev, "site_name": cfg.site_name,
                 "caps": {"pdf": app.pdf_tools, "word": docx_out.available(), "pdf_reports": bool(app.runner.pdf_reports), "real": app.key_ready(), "stub": cfg.pipeline == "stub", "languages": list(config.LANGUAGES)},
                 "limits": {"max_pages": cfg.max_pages, "max_file_mb": cfg.max_file // (1024 * 1024), "retention_hours": cfg.retention_hours, "job_budget_inr": cfg.job_budget, "per_page_low_inr": PER_PAGE_LOW_INR, "per_page_high_inr": PER_PAGE_HIGH_INR},
                 "room": room, "gate_text": GATE_TEXT, "cost_note": COST_NOTE})


# ---------------------------------------------------------------- jobs
@route("GET", r"/api/jobs")
def api_jobs(h, user, m, q):
    h.send_json({"jobs": [public_meta(h.app, j) for j in h.app.store.list(user)]})


@route("POST", r"/api/jobs")
def api_create(h, user, m, q):
    app = h.app
    d = h.read_json()
    if d.get("gate_confirmed") is not True:
        raise ApiError(400, "Please tick the confirmation that nothing in the pages identifies a minor or the victim of a sexual offence.")
    language, ptype = d.get("language"), d.get("page_type")
    if language not in config.LANGUAGES:
        raise ApiError(400, "Choose the language of the document.")
    if ptype not in ("typed", "handwritten", "unsure"):
        raise ApiError(400, "Say whether the pages are typed or handwritten.")
    label = re.sub(r"[\x00-\x1f\x7f]", "", str(d.get("label") or "")).strip()[:80]
    known = [re.sub(r"[\x00-\x1f\x7f]", "", str(x)).strip()[:80] for x in (d.get("known_names") or []) if str(x).strip()][:50] if isinstance(d.get("known_names"), list) else []
    meta = app.store.create(user, label=label, language=language, page_type=ptype, grouped=bool(d.get("grouped", True)), n_pages=0, gate_at=now_iso(), gate_text=GATE_TEXT)
    if known:
        with open(app.store.path(meta["id"], "known.json"), "w", encoding="utf8") as f:
            json.dump(known, f, ensure_ascii=False)
    h.send_json({"job": public_meta(app, meta)}, 201)


@route("PUT", r"/api/jobs/(?P<jid>[0-9a-f]{24})/files")
def api_put_file(h, user, m, q):
    app, cfg, st = h.app, h.app.cfg, h.app.store
    meta = h.owned(m["jid"], user)
    if meta["status"] != "draft":
        raise ApiError(409, "Files can only be added before the reading starts.", close=True)
    length = h.content_length(required=True)
    if length == 0:
        raise ApiError(400, "That file is empty.", close=True)
    if length > cfg.max_file:
        raise ApiError(413, "That file is larger than %d MB." % (cfg.max_file // (1024 * 1024)), close=True)
    if sum(f["size"] for f in meta["files"]) + length > cfg.max_job:
        raise ApiError(413, "These files together are larger than %d MB." % (cfg.max_job // (1024 * 1024)), close=True)
    if meta["n_pages"] >= cfg.max_pages:
        raise ApiError(409, "A job can hold at most %d pages." % cfg.max_pages, close=True)
    shown = clean_name((q.get("name") or [""])[0])
    tmp = os.path.join(st.path(m["jid"], "in"), ".upload-" + secrets.token_hex(6))
    try:
        left = length
        with open(tmp, "wb") as f:
            while left:
                chunk = h.rfile.read(min(65536, left))
                if not chunk:
                    raise ConnectionResetError()
                f.write(chunk); left -= len(chunk)
        h.body_read = True
        kind = harness.sniff(tmp)
        if kind is None:
            raise ApiError(415, "Only PDF, JPEG, PNG or WebP files can be read (checked by content, not by name).")
        if kind == "pdf":
            if not app.pdf_tools:
                raise ApiError(415, "This server cannot read PDFs (the poppler tools are not installed). Upload the pages as photos instead.")
            pages = pdf_pages(tmp)
        else:
            check_image(tmp)
            pages = 1
        with st.lock:
            meta = st.get(m["jid"])
            if meta["n_pages"] + pages > cfg.max_pages:
                raise ApiError(413, "That would make more than %d pages." % cfg.max_pages)
            idx = len(meta["files"]) + 1
            if kind == "pdf":
                entry = {"stem": "d%d" % idx, "ext": ".pdf"}
            elif meta.get("grouped", True):
                n = sum(1 for f in meta["files"] if f.get("group") == "doc") + 1
                entry = {"stem": "doc_p%d" % n, "group": "doc", "ext": {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[kind]}
            else:
                entry = {"stem": "img%d" % idx, "ext": {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[kind]}
            stored = entry["stem"] + entry.pop("ext")
            os.replace(tmp, st.path(m["jid"], "in", stored))
            entry.update(stored=stored, original=shown, kind=kind, size=length, pages=pages)
            files = meta["files"] + [entry]
            st.update(m["jid"], files=files, n_pages=meta["n_pages"] + pages, label=meta.get("label") or shown)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    h.send_json({"file": {"name": shown, "kind": kind, "pages": pages, "size": length}, "n_pages": meta["n_pages"] + pages}, 201)


def begin(app, user, meta, demo_job=False):
    """Check the caps, set the budget and queue the job. Raises ApiError with the reason when it may not start."""
    cfg = app.cfg
    pages = meta["n_pages"]
    if not meta["files"] or pages < 1:
        raise ApiError(400, "Add at least one page first.")
    if not demo_job and cfg.pipeline == "real" and not app.key_ready():
        raise ApiError(503, "Reading is switched off: this server has no model key (GEMINI_API_KEY). The demo still works.")
    est = app.estimate(pages)
    room = app.room(user)
    budget = 5.0 if demo_job else min(round(pages * BUDGET_PER_PAGE_INR + 4.0, 1), room["allowed"])
    if not demo_job and budget < est["low"]:
        which = "your daily limit" if room["day"] <= room["month"] else "the site's monthly limit"
        if room["allowed"] >= cfg.job_budget and cfg.job_budget < est["low"]:
            which = "the limit for one job (Rs %.0f)" % cfg.job_budget
        raise ApiError(402, "Even the lowest estimate for this job, about Rs %.1f, is more than %s allows right now (Rs %.1f left)." % (est["low"], which, room["allowed"]))
    app.store.update(meta["id"], budget_inr=budget)
    app.runner.submit(meta["id"])


@route("POST", r"/api/jobs/(?P<jid>[0-9a-f]{24})/start")
def api_start(h, user, m, q):
    h.read_json()
    meta = h.owned(m["jid"], user)
    if meta["status"] != "draft":
        raise ApiError(409, "This job has already been started.")
    begin(h.app, user, meta)
    h.send_json({"job": public_meta(h.app, h.app.store.get(m["jid"]))})


@route("POST", r"/api/demo")
def api_demo(h, user, m, q):
    app = h.app
    h.read_json()
    assets = os.path.join(app.cfg.data_dir, "demo_assets")
    paths = demo.make_pages(assets)
    meta = app.store.create(user, label=demo.DEMO_NAME, language="Assamese", page_type="handwritten", grouped=True, n_pages=3, demo=True, gate_at=now_iso(), gate_text="demo: invented pages")
    files = []
    for i, p in enumerate(paths, 1):
        stored = "doc_p%d.png" % i
        shutil.copyfile(p, app.store.path(meta["id"], "in", stored))
        files.append({"stem": "doc_p%d" % i, "group": "doc", "stored": stored, "original": "demo page %d.png" % i, "kind": "image/png", "size": os.path.getsize(p), "pages": 1})
    app.store.update(meta["id"], files=files)
    begin(app, user, app.store.get(meta["id"]), demo_job=True)
    h.send_json({"job": public_meta(app, app.store.get(meta["id"]))}, 201)


@route("GET", r"/api/jobs/(?P<jid>[0-9a-f]{24})")
def api_job(h, user, m, q):
    meta = h.owned(m["jid"], user)
    prog = results.progress(meta, h.app.store.path(m["jid"])) if meta["status"] in ("queued", "running", "done", "failed", "cancelled") else None
    h.send_json({"job": public_meta(h.app, meta), "progress": prog})


@route("GET", r"/api/jobs/(?P<jid>[0-9a-f]{24})/result")
def api_result(h, user, m, q):
    meta = h.owned(m["jid"], user)
    r = results.build(meta, h.app.store.path(m["jid"])) if meta["status"] in ("done", "failed", "cancelled") else None
    h.send_json({"job": public_meta(h.app, meta), "result": r, "caps": {"word": docx_out.available()}})


@route("POST", r"/api/jobs/(?P<jid>[0-9a-f]{24})/cancel")
def api_cancel(h, user, m, q):
    h.read_json()
    meta = h.owned(m["jid"], user)
    if meta["status"] not in ACTIVE:
        raise ApiError(409, "This job is not waiting or running.")
    h.app.runner.cancel(m["jid"])
    h.send_json({"ok": True})


@route("POST", r"/api/jobs/(?P<jid>[0-9a-f]{24})/resume")
def api_resume(h, user, m, q):
    h.read_json()
    app, meta = h.app, h.owned(m["jid"], user)
    if not (meta["status"] in ("failed", "cancelled") or (meta["status"] == "done" and (meta.get("stopped_by_budget") or meta.get("sense_unrun")))):
        raise ApiError(409, "Only a job that stopped early, or whose sense check did not run, can be continued.")
    if not app.key_ready() and not meta.get("demo") and app.cfg.pipeline == "real":
        raise ApiError(503, "Reading is switched off: this server has no model key.")
    room = app.room(user)
    spent = meta.get("spent_inr", 0.0)
    budget = min(round(spent + meta["n_pages"] * BUDGET_PER_PAGE_INR + 4.0, 1), spent + room["allowed"])
    if not meta.get("demo") and budget - spent < PER_PAGE_LOW_INR:
        raise ApiError(402, "There is not enough budget left to continue (Rs %.1f left). Finished readings are kept." % room["allowed"])
    app.store.update(m["jid"], budget_inr=budget if not meta.get("demo") else 5.0, stopped_by_budget=False, sense_unrun=False)
    app.runner.submit(m["jid"])
    h.send_json({"job": public_meta(app, app.store.get(m["jid"]))})


@route("DELETE", r"/api/jobs/(?P<jid>[0-9a-f]{24})")
def api_delete(h, user, m, q):
    meta = h.owned(m["jid"], user)
    if meta["status"] in ACTIVE:
        raise ApiError(409, "Stop the job first.")
    h.app.store.delete(m["jid"])
    h.send_json({"ok": True})


def known_targets(app, jid):
    s = results._json(os.path.join(app.store.path(jid), "run", "summary.json"), {})
    pages = {p["page"] for p in s.get("pages", [])}
    docs = {d["document"] for d in s.get("documents", []) if "light" in d}
    return pages, docs


@route("POST", r"/api/jobs/(?P<jid>[0-9a-f]{24})/review")
def api_review(h, user, m, q):
    d = h.read_json()
    meta = h.owned(m["jid"], user)
    pages, docs = known_targets(h.app, m["jid"])
    target = str(d.get("target", ""))
    if target not in pages | docs:
        raise ApiError(404, "No such page.")
    note = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(d.get("note") or ""))[:300]

    def fn(mm):
        rv = mm.setdefault("reviews", {})
        if d.get("read"):
            rv[target] = {"by": user, "at": now_iso(), "note": note}
        else:
            rv.pop(target, None)
    out = h.app.store.mutate(m["jid"], fn)
    h.send_json({"reviews": out["reviews"]})


@route("GET", r"/api/jobs/(?P<jid>[0-9a-f]{24})/image/(?P<pid>[A-Za-z0-9_\-]{1,80})")
def api_image(h, user, m, q):
    h.owned(m["jid"], user)
    if m["pid"] not in known_targets(h.app, m["jid"])[0]:
        raise ApiError(404, "No picture of that page.")
    p = results.preview_jpeg(os.path.join(h.app.store.path(m["jid"]), "run"), m["pid"])
    if not p:
        raise ApiError(404, "No picture of that page.")
    h.send_file(p, "image/jpeg", "api")


@route("GET", r"/api/jobs/(?P<jid>[0-9a-f]{24})/report/(?P<target>[A-Za-z0-9_\-]{1,80})")
def api_report(h, user, m, q):
    meta = h.owned(m["jid"], user)
    pages, docs = known_targets(h.app, m["jid"])
    run = os.path.join(h.app.store.path(m["jid"]), "run")
    base = os.path.join(run, "report", m["target"]) if m["target"] in pages else (os.path.join(run, "document", m["target"] + "_document") if m["target"] in docs else None)
    if not base:
        raise ApiError(404, "No such report.")
    want_pdf = (q.get("format") or ["html"])[0] == "pdf"
    if want_pdf and os.path.exists(base + ".pdf"):
        return h.send_file(base + ".pdf", "application/pdf", "doc", safe_filename(meta.get("label"), "_%s.pdf" % m["target"]), attachment=True)
    if not os.path.exists(base + ".html"):
        raise ApiError(404, "No such report.")
    h.send_file(base + ".html", "text/html; charset=utf-8", "doc", None)


@route("GET", r"/api/jobs/(?P<jid>[0-9a-f]{24})/marksheet/(?P<pid>[A-Za-z0-9_\-]{1,80})")
def api_marksheet(h, user, m, q):
    h.owned(m["jid"], user)
    if m["pid"] not in known_targets(h.app, m["jid"])[0]:
        raise ApiError(404, "No such marking sheet.")
    h.send_file(os.path.join(h.app.store.path(m["jid"]), "run", "marksheets", m["pid"] + "_marksheet.html"), "text/html; charset=utf-8", "sheet")


@route("GET", r"/api/jobs/(?P<jid>[0-9a-f]{24})/word/(?P<target>[A-Za-z0-9_\-]{1,80})")
def api_word(h, user, m, q):
    meta = h.owned(m["jid"], user)
    if not docx_out.available():
        raise ApiError(501, "The Word file is switched off: python-docx is not installed on the server.")
    r = results.build(meta, h.app.store.path(m["jid"]))
    if not r:
        raise ApiError(404, "There is no result yet.")
    doc = next((d for d in r["documents"] if d["id"] == m["target"] and d.get("light")), None)
    page = next((p for p in r["pages"] if p["id"] == m["target"]), None)
    src = doc or page
    if not src:
        raise ApiError(404, "No such page.")
    title = ("%s (whole document)" % doc["display"]) if doc else ("%s, page %d" % (page["label"], page["n"]) if page["label"] != page["id"] else page["id"])
    note = "Translation 1 is the one to read; it was fixed in advance, never chosen by the tool." if doc else ""
    data = docx_out.make_docx(title, meta["language"], src["light"], src["read_first"], src["paras"], src["glossary"], [x for x in src["must_check"] if x["status"] == "CONFIRM"], note)
    body_name = safe_filename(meta.get("label"), "_%s.docx" % m["target"])
    h.respond(200, data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "doc", headers=[("Content-Disposition", 'attachment; filename="%s"' % body_name)])


# ---------------------------------------------------------------- reference pages
@route("GET", r"/api/glossary")
def api_glossary(h, user, m, q):
    app = h.app
    if app.glossary is None:
        app.glossary = results.glossary_rows()
    h.send_json({"rows": app.glossary, "count": len(app.glossary), "note": "Notes only: they never change the translation. Every row states that a lawyer approved it on the owner's say-so; that approval has not been seen by the people who built the tool."})


@route("GET", r"/api/usage")
def api_usage(h, user, m, q):
    app, cfg, st = h.app, h.app.cfg, h.app.store
    room = app.room(user)
    mine = [j for j in st.list(user)]
    month = month_start()
    h.send_json({"today_inr": round(st.spent(user, day_start()), 2), "month_inr": round(st.spent(user, month), 2), "site_month_inr": round(st.spent(None, month), 2),
                 "caps": {"daily": cfg.daily_budget, "monthly": cfg.monthly_budget, "job": cfg.job_budget}, "room": room, "note": COST_NOTE,
                 "pages_month": sum(r.get("pages", 0) for r in st.usage_rows() if r.get("user") == user and r.get("epoch", 0) >= month and not r.get("demo") and r.get("spent_inr", 0) > 0),
                 "jobs": [{"id": j["id"], "label": j.get("label"), "created": j.get("created"), "status": j["status"], "pages": j.get("n_pages"), "spent_inr": j.get("spent_inr"), "demo": bool(j.get("demo"))} for j in mine[:50]]})


# ---------------------------------------------------------------- start up
def janitor(app):
    while True:
        try:
            for jid in app.store.expired(app.cfg.retention_hours):
                app.store.delete(jid)
        except Exception as e:
            sys.stderr.write("clean-up error: %s\n" % type(e).__name__)
        time.sleep(600)


class QuietServer(ThreadingHTTPServer):
    request_queue_size = 64
    daemon_threads = True

    def handle_error(self, request, client_address):
        if issubclass(sys.exc_info()[0] or Exception, (BrokenPipeError, ConnectionResetError, TimeoutError)):
            return                                                       # a browser that went away mid-request is not an error worth a traceback
        sys.stderr.write("server error from %s: %s\n" % (client_address[0], (sys.exc_info()[0] or Exception).__name__))


def make_server(cfg, start_workers=True):
    app = App(cfg, start_workers)
    srv = QuietServer((cfg.host, cfg.port), type("BoundHandler", (Handler,), {"app": app}))        # one handler class per server, so two servers in one process do not share an app
    cfg.port = srv.server_address[1]
    return srv, app


def main(argv=None):
    ap = argparse.ArgumentParser(description="The Reading Desk site (see the top of this file).")
    ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=int(os.environ.get("PORT") or 8080))
    ap.add_argument("--new-code", action="store_true", help="print a random access code and exit (put it in RD_USERS as name:code)")
    ap.add_argument("--data", help="where jobs are kept (default ~/.reading_desk)")
    ap.add_argument("--dev", action="store_true", help="this computer only: no sign-in")
    a = ap.parse_args(argv)
    if a.new_code:
        print(secrets.token_urlsafe(15))
        return
    cfg = config.Config(dev=a.dev, data_dir=a.data, host=a.host, port=a.port)
    srv, app = make_server(cfg)
    app.runner.recover()
    threading.Thread(target=janitor, args=(app,), daemon=True).start()
    print("Reading Desk on http://%s:%d" % (cfg.host, cfg.port))
    print("  data folder      %s" % cfg.data_dir)
    print("  readings         %s" % ("real (the model key is set)" if app.key_ready() else ("STUB: invented text, no model" if cfg.pipeline == "stub" else "OFF: GEMINI_API_KEY is not set, only the demo works")))
    print("  signed-in users  %s" % (", ".join(sorted(cfg.users)) if not (cfg.dev and cfg.users == {"dev": ""}) else "none (dev mode: this computer only)"))
    print("  PDF files        %s    Word file  %s    PDF reports  %s" % ("yes" if app.pdf_tools else "no (poppler missing)", "yes" if docx_out.available() else "no (python-docx missing)", "yes" if app.runner.pdf_reports else "no"))
    print("  limits           %d pages, %d MB a file, Rs %.0f a job, Rs %.0f a day each, Rs %.0f a month; files deleted %.0f h after a job ends" % (
        cfg.max_pages, cfg.max_file // 1048576, cfg.job_budget, cfg.daily_budget, cfg.monthly_budget, cfg.retention_hours))
    sys.stdout.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
