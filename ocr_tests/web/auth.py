"""Sign-in for the Reading Desk site: a signed, expiring cookie and a limit on wrong codes. Nothing here stores a password: the access codes are held in the environment."""
import base64, hashlib, hmac, os, threading, time


def _b64(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def load_secret(data_dir):
    """The cookie-signing secret: made once, kept in the data directory (mode 0600), never in the repository."""
    path = os.path.join(data_dir, "secret.key")
    if os.path.exists(path):
        s = open(path, "rb").read()
        if len(s) >= 32:
            return s
    s = os.urandom(48)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(s)
    return s


def _sig(secret, payload):
    return _b64(hmac.new(secret, payload.encode(), hashlib.sha256).digest())


def make_session(secret, user, ttl, now=None):
    exp = int((now or time.time()) + ttl)
    payload = "%s|%d|%s" % (user, exp, os.urandom(6).hex())            # the random part makes every sign-in a different cookie, so signing out ends only that one
    return _b64(payload.encode()) + "." + _sig(secret, payload)


def read_session(secret, token, now=None):
    """The user name in a valid, unexpired cookie, else None."""
    try:
        body, sig = token.split(".", 1)
        payload = _unb64(body).decode()
        if not hmac.compare_digest(sig, _sig(secret, payload)):
            return None
        user, exp, _nonce = payload.split("|")
        return user if int(exp) > (now or time.time()) else None
    except Exception:
        return None


def check_code(users, name, code):
    """True when name and code match. The comparison takes the same time whatever is wrong, and an unknown name is compared against a dummy."""
    expected = users.get((name or "").strip().lower())
    dummy = "x" * 16
    ok = hmac.compare_digest((code or "").encode(), (expected if expected is not None else dummy).encode())
    return bool(ok and expected is not None)


class LoginLimiter:
    """At most `limit` wrong codes per key (address or name) in `window` seconds."""
    def __init__(self, limit=8, window=600):
        self.limit, self.window, self.fails, self.lock = limit, window, {}, threading.Lock()

    def _recent(self, key, now):
        v = [t for t in self.fails.get(key, []) if now - t < self.window]
        self.fails[key] = v
        return v

    def allowed(self, *keys, now=None):
        now = now or time.time()
        with self.lock:
            return all(len(self._recent(k, now)) < self.limit for k in keys)

    def fail(self, *keys, now=None):
        now = now or time.time()
        with self.lock:
            for k in keys:
                self._recent(k, now).append(now)

    def ok(self, *keys):
        with self.lock:
            for k in keys:
                self.fails.pop(k, None)


def selftest():
    s = os.urandom(32)
    t = make_session(s, "alice", 60)
    assert read_session(s, t) == "alice"
    assert read_session(s, t, now=time.time() + 120) is None, "an expired cookie is refused"
    assert read_session(s, t[:-2] + ("AA" if not t.endswith("AA") else "BB")) is None, "a changed signature is refused"
    assert read_session(os.urandom(32), t) is None, "another secret is refused"
    assert read_session(s, "garbage") is None and read_session(s, "") is None
    assert make_session(s, "alice", 60) != make_session(s, "alice", 60), "two sign-ins in one second are two cookies"
    users = {"alice": "correct-horse-1"}
    assert check_code(users, "Alice", "correct-horse-1") and not check_code(users, "alice", "wrong") and not check_code(users, "nobody", "x" * 16)
    lim = LoginLimiter(limit=3, window=100)
    for _ in range(3):
        assert lim.allowed("a", now=1000.0)
        lim.fail("a", now=1000.0)
    assert not lim.allowed("a", now=1001.0) and lim.allowed("a", now=1200.0), "the limit lifts after the window"
    print("auth selftest OK")


if __name__ == "__main__":
    selftest()
