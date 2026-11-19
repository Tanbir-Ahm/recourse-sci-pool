"""Jobs on disk for the Reading Desk site. One folder per job: meta.json, in/ (the uploaded files under neutral names), run/ (the pipeline's output), log.txt.
A job id is 24 hex characters and is checked before it is used in any path. Writes of meta.json are atomic. The usage log (usage.jsonl) outlives the jobs: it holds counts and
estimated rupees, never text, so the budgets still hold after a job is deleted."""
import datetime, json, os, re, secrets, shutil, tempfile, threading, time

ID_RE = re.compile(r"^[0-9a-f]{24}$")
ACTIVE = ("queued", "running")


def now_iso(t=None):
    return datetime.datetime.fromtimestamp(t or time.time(), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Store:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.jobs = os.path.join(self.root, "jobs")
        os.makedirs(self.jobs, mode=0o700, exist_ok=True)
        try:
            os.chmod(self.root, 0o700)
        except OSError:
            pass
        self.lock = threading.RLock()
        self.usage_path = os.path.join(self.root, "usage.jsonl")

    # ---- paths
    def valid(self, jid):
        return isinstance(jid, str) and bool(ID_RE.match(jid))

    def path(self, jid, *parts):
        if not self.valid(jid):
            raise ValueError("bad job id")
        return os.path.join(self.jobs, jid, *parts)

    # ---- jobs
    def create(self, user, **fields):
        with self.lock:
            jid = secrets.token_hex(12)
            os.makedirs(self.path(jid, "in"), mode=0o700)
            meta = {"id": jid, "user": user, "created": now_iso(), "created_epoch": time.time(), "status": "draft", "files": [], "reviews": {}, "spent_inr": 0.0}
            meta.update(fields)
            self._write(meta)
            return meta

    def _write(self, meta):
        p = self.path(meta["id"], "meta.json")
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix=".meta-")
        with os.fdopen(fd, "w", encoding="utf8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
        os.replace(tmp, p)

    def get(self, jid):
        if not self.valid(jid):
            return None
        try:
            with open(self.path(jid, "meta.json"), encoding="utf8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def update(self, jid, **kw):
        """Read, change and write meta.json under the lock. Returns the new meta, or None when the job is gone."""
        with self.lock:
            m = self.get(jid)
            if m is None:
                return None
            m.update(kw)
            self._write(m)
            return m

    def mutate(self, jid, fn):
        with self.lock:
            m = self.get(jid)
            if m is None:
                return None
            fn(m)
            self._write(m)
            return m

    def list(self, user=None):
        out = []
        try:
            names = os.listdir(self.jobs)
        except OSError:
            return out
        for n in names:
            m = self.get(n)
            if m and (user is None or m.get("user") == user):
                out.append(m)
        out.sort(key=lambda m: m.get("created_epoch", 0), reverse=True)
        return out

    def delete(self, jid):
        with self.lock:
            if not self.valid(jid) or not os.path.isdir(self.path(jid)):
                return False
            shutil.rmtree(self.path(jid), ignore_errors=True)
            return True

    def size(self, jid):
        total = 0
        for dp, _, fs in os.walk(self.path(jid)):
            for f in fs:
                try:
                    total += os.path.getsize(os.path.join(dp, f))
                except OSError:
                    pass
        return total

    # ---- usage
    def add_usage(self, row):
        with self.lock:
            with open(self.usage_path, "a", encoding="utf8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def usage_rows(self):
        rows = []
        try:
            with open(self.usage_path, encoding="utf8") as f:
                for line in f:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        pass
        except OSError:
            pass
        return rows

    def spent(self, user=None, since=None):
        """Estimated rupees spent (from the usage log) by a user, or by everybody, since an epoch time."""
        return sum(r.get("spent_inr", 0.0) for r in self.usage_rows() if (user is None or r.get("user") == user) and r.get("epoch", 0) >= (since or 0))

    def reserved(self, user=None):
        """Rupees held back for jobs that are queued or running (their budget), so that two jobs started together cannot pass a cap."""
        return sum(m.get("budget_inr", 0.0) for m in self.list(user) if m.get("status") in ACTIVE)

    # ---- clean-up
    def expired(self, retention_hours, draft_hours=6.0, now=None):
        """Job ids to delete: finished jobs older than the retention time, and drafts that were never started."""
        now = now or time.time()
        out = []
        for m in self.list():
            st = m.get("status")
            if st in ACTIVE:
                continue
            age = (now - (m.get("finished_epoch") or m.get("created_epoch") or now)) / 3600.0
            if (st == "draft" and age > draft_hours) or (st != "draft" and age > retention_hours):
                out.append(m["id"])
        return out


def month_start(now=None):
    d = datetime.datetime.fromtimestamp(now or time.time(), datetime.timezone.utc)
    return datetime.datetime(d.year, d.month, 1, tzinfo=datetime.timezone.utc).timestamp()


def day_start(now=None):
    d = datetime.datetime.fromtimestamp(now or time.time(), datetime.timezone.utc)
    return datetime.datetime(d.year, d.month, d.day, tzinfo=datetime.timezone.utc).timestamp()


def selftest():
    root = tempfile.mkdtemp()
    s = Store(root)
    m = s.create("alice", label="x")
    assert s.valid(m["id"]) and s.get(m["id"])["user"] == "alice"
    for bad in ("../x", "", "g" * 24, "a" * 23, None, "a" * 24 + "/"):
        assert not s.valid(bad) and s.get(bad) is None, bad
    try:
        s.path("../..")
        raise AssertionError("a bad id must not give a path")
    except ValueError:
        pass
    s.update(m["id"], status="queued", budget_inr=12.0)
    assert s.reserved("alice") == 12.0 and s.reserved("other") == 0
    s.update(m["id"], status="done", finished_epoch=time.time() - 100 * 3600)
    assert s.expired(72.0) == [m["id"]] and s.expired(200.0) == []
    d = s.create("alice")
    assert s.expired(72.0, draft_hours=6.0, now=time.time() + 7 * 3600).count(d["id"]) == 1
    s.add_usage({"user": "alice", "spent_inr": 3.5, "epoch": 1000.0}); s.add_usage({"user": "x", "spent_inr": 1.0, "epoch": 2000.0})
    assert s.spent("alice") == 3.5 and s.spent(since=1500.0) == 1.0 and s.spent() == 4.5
    assert s.delete(m["id"]) and not s.delete(m["id"]) and s.get(m["id"]) is None
    shutil.rmtree(root)
    print("store selftest OK")


if __name__ == "__main__":
    selftest()
