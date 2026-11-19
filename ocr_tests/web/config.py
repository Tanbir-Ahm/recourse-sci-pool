"""Settings of the Reading Desk site. Everything comes from environment variables (RD_*) or the command line; no key and no access code is ever read from, or written to, a file in the repository.

  RD_USERS            "name:code,name2:code2"   who may sign in (a code is at least 10 characters). Without any user the server refuses to start, unless --dev (local use only).
  RD_DATA_DIR         where jobs live (default ~/.reading_desk, outside the repository: it holds case documents)
  RD_PIPELINE         real (default) or stub (invented text, no model, no cost: for tests and the demo)
  RD_JOB_BUDGET_INR   most one job may be allowed to spend, by the pipeline's own estimate (default 40)
  RD_DAILY_BUDGET_INR most one user may spend per UTC day (default 150)
  RD_MONTHLY_BUDGET_INR most the whole site may spend per UTC month (default 600)
  RD_MAX_PAGES        pages in one job (default 30)         RD_MAX_FILE_MB  one file (default 25)       RD_MAX_JOB_MB  one job (default 120)
  RD_RETENTION_HOURS  a job and its files are deleted this long after it finishes (default 72)
  RD_WORKERS          jobs run at the same time (default 1)  RD_JOB_TIMEOUT_MIN  a job is stopped after this long (default 60)
  RD_PDF_REPORTS      auto (default), on, off: print the reports to PDF too (needs Node and Playwright)
  RD_COOKIE_SECURE    1 when the site is served over HTTPS (set it behind a TLS proxy)
  RD_COOKIE_SAMESITE  Strict (default), Lax or None (None needs Secure; only for a page shown inside another site)
  RD_TRUST_PROXY      1 when a reverse proxy in front of the server sets X-Forwarded-Host and X-Forwarded-Proto
  RD_ALLOWED_ORIGINS  extra "host:port" values accepted in the Origin header of a write request (comma separated); "*" skips that comparison (every write still needs the site's own header)
  RD_ALLOW_FRAMING    1 lets another site show this one in a frame (off by default)
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OCR_DIR = os.path.dirname(HERE)
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$")
LANGUAGES = {"Assamese": "asm+eng", "Kannada": "kan+eng", "Hindi": "hin+eng"}      # language -> Tesseract languages for a PDF's text check
MIN_CODE = 10


def _num(name, default, cast=float, low=0):
    raw = os.environ.get("RD_" + name)
    if raw in (None, ""):
        return default
    try:
        v = cast(raw)
    except ValueError:
        sys.exit("RD_%s must be a number" % name)
    if v < low:
        sys.exit("RD_%s must be at least %s" % (name, low))
    return v


def parse_users(text):
    """'name:code,name2:code2' -> {name: code}. A name is letters, digits, dot, dash or underscore; a code has at least MIN_CODE characters and no comma."""
    users = {}
    for part in (text or "").split(","):
        part = part.strip()
        if not part:
            continue
        name, sep, code = part.partition(":")
        name = name.strip().lower()
        if not sep or not NAME_RE.match(name):
            raise ValueError("a user must look like name:code, with a name of letters, digits, dot, dash or underscore")
        if len(code) < MIN_CODE:
            raise ValueError("the access code of %s is shorter than %d characters" % (name, MIN_CODE))
        users[name] = code
    return users


class Config:
    def __init__(self, dev=False, data_dir=None, host="127.0.0.1", port=8080):
        self.dev = dev
        self.host, self.port = host, port
        try:
            self.users = parse_users(os.environ.get("RD_USERS", ""))
        except ValueError as e:
            sys.exit("RD_USERS: %s" % e)
        if not self.users:
            if not dev:
                sys.exit("No user is set. Set RD_USERS=\"name:code\" (a code of at least %d characters), or start with --dev to use the site on this computer only." % MIN_CODE)
            if host not in ("127.0.0.1", "localhost", "::1"):
                sys.exit("--dev without RD_USERS signs everybody in: it is only allowed on 127.0.0.1")
            self.users = {"dev": ""}
        self.data_dir = os.path.abspath(os.path.expanduser(data_dir or os.environ.get("RD_DATA_DIR") or "~/.reading_desk"))
        self.pipeline = os.environ.get("RD_PIPELINE", "real")
        if self.pipeline not in ("real", "stub"):
            sys.exit("RD_PIPELINE must be real or stub")
        self.job_budget = _num("JOB_BUDGET_INR", 40.0)
        self.daily_budget = _num("DAILY_BUDGET_INR", 150.0)
        self.monthly_budget = _num("MONTHLY_BUDGET_INR", 600.0)
        self.max_pages = _num("MAX_PAGES", 30, int, 1)
        self.max_file = int(_num("MAX_FILE_MB", 25.0) * 1024 * 1024)
        self.max_job = int(_num("MAX_JOB_MB", 120.0) * 1024 * 1024)
        self.retention_hours = _num("RETENTION_HOURS", 72.0)
        self.workers = _num("WORKERS", 1, int, 1)
        self.job_timeout = _num("JOB_TIMEOUT_MIN", 60.0) * 60
        self.pdf_reports = os.environ.get("RD_PDF_REPORTS", "auto")
        self.cookie_secure = os.environ.get("RD_COOKIE_SECURE") == "1"
        self.samesite = os.environ.get("RD_COOKIE_SAMESITE", "Strict")
        if self.samesite not in ("Strict", "Lax", "None"):
            sys.exit("RD_COOKIE_SAMESITE must be Strict, Lax or None")
        if self.samesite == "None" and not self.cookie_secure:
            sys.exit("RD_COOKIE_SAMESITE=None needs RD_COOKIE_SECURE=1")
        self.trust_proxy = os.environ.get("RD_TRUST_PROXY") == "1"
        self.allowed_origins = {x.strip().lower() for x in os.environ.get("RD_ALLOWED_ORIGINS", "").split(",") if x.strip()}
        self.allow_framing = os.environ.get("RD_ALLOW_FRAMING") == "1"
        self.session_ttl = 12 * 3600
