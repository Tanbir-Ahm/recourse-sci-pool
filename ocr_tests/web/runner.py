"""Runs a job's pipeline in a child process, one command per job. The child's output goes to the job's log.txt; its cost is read back from the pipeline's own ledger (an ESTIMATE:
the real bill has run 1.5 to 2 times higher); a job is stopped when the owner cancels it or when it runs past the time limit. The model key stays in the server's environment and
is passed to the child there; nothing in this module prints it, and the error text shown to a person is stripped of anything that looks like a key or a path of the server.
"""
import os, queue, re, shutil, signal, subprocess, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
OCR_DIR = os.path.dirname(HERE)
sys.path.insert(0, OCR_DIR); sys.path.insert(0, HERE)
import config, harness
from store import ACTIVE, now_iso

KEY_RE = re.compile(r"AIza[0-9A-Za-z_\-]{20,}|sk-[0-9A-Za-z_\-]{20,}|[0-9a-f]{32,}")


def redact(text, *paths):
    text = KEY_RE.sub("[removed]", text or "")
    for p in paths:
        if p:
            text = text.replace(p, "…")
    return text


def friendly_error(log_tail, data_dir):
    if "is not set in this environment" in log_tail:
        return "This server has no model key set (GEMINI_API_KEY), so it cannot read pages. Ask the person who runs it."
    lines = [l.strip() for l in log_tail.splitlines() if l.strip() and not l.startswith(("Traceback", '  File "', "    "))]
    return redact(" / ".join(lines[-3:]) or "The reading stopped without a message.", data_dir)[:400]


def detect_pdf_reports():
    node = shutil.which("node")
    if not node:
        return False
    try:
        npm = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, timeout=30).stdout.strip()
        r = subprocess.run([node, "-e", "require('playwright')"], capture_output=True, timeout=30, env=dict(os.environ, NODE_PATH=npm))
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def kill(proc):
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.terminate()
    except (OSError, ProcessLookupError):
        pass
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            else:
                proc.kill()
        except (OSError, ProcessLookupError):
            pass


class Runner:
    def __init__(self, cfg, store, start_workers=True):
        self.cfg, self.store = cfg, store
        self.q, self.procs, self.cancelled, self.lock = queue.Queue(), {}, set(), threading.Lock()
        self._pdf = None
        if start_workers:
            for i in range(cfg.workers):
                threading.Thread(target=self._worker, daemon=True, name="rd-worker-%d" % i).start()

    @property
    def pdf_reports(self):
        if self._pdf is None:
            self._pdf = {"on": True, "off": False}.get(self.cfg.pdf_reports) if self.cfg.pdf_reports in ("on", "off") else detect_pdf_reports()
        return self._pdf

    def recover(self):
        """Jobs that were queued or running when the server last stopped cannot continue: say so, so a person can retry them."""
        for m in self.store.list():
            if m.get("status") in ACTIVE:
                self.store.update(m["id"], status="failed", error="The server restarted while this job was waiting or running. Use Retry: finished readings are not paid for twice.", finished=now_iso(), finished_epoch=time.time())

    def submit(self, jid):
        self.store.update(jid, status="queued", queued_epoch=time.time(), error=None)
        self.q.put(jid)

    def cancel(self, jid):
        with self.lock:
            self.cancelled.add(jid)
            p = self.procs.get(jid)
        m = self.store.get(jid)
        if m and m.get("status") == "queued":
            self.store.update(jid, status="cancelled", finished=now_iso(), finished_epoch=time.time())
        elif p is not None:
            kill(p)

    # ---- the command
    def command(self, meta, in_dir, out_dir):
        stub = self.cfg.pipeline == "stub" or meta.get("demo")
        script = os.path.join(HERE, "stub_pipeline.py") if stub else os.path.join(OCR_DIR, "pipeline.py")
        cmd = [sys.executable, script, "--input", in_dir, "--out", out_dir, "--language", meta["language"],
               "--page-type", "typed" if meta["page_type"] == "typed" else "handwritten", "--budget-inr", "%.2f" % meta["budget_inr"],
               "--third-view", "auto", "--orient", "auto", "--stitch", "auto", "--sense", "auto", "--marks", "auto", "--pdf-lang", config.LANGUAGES[meta["language"]]]
        if os.path.exists(os.path.join(os.path.dirname(in_dir), "known.json")):
            cmd += ["--known", os.path.join(os.path.dirname(in_dir), "known.json")]
        if self.pdf_reports and not stub:
            cmd.append("--pdf")
        return cmd

    def _env(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("RD_")}
        env.update(PYTHONUNBUFFERED="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        return env

    # ---- the workers
    def _worker(self):
        while True:
            jid = self.q.get()
            try:
                self._run(jid)
            except Exception as e:                                          # a worker must never die; the person sees a plain message, the operator sees the type
                sys.stderr.write("worker error on a job: %s\n" % type(e).__name__)
                self.store.update(jid, status="failed", error="The job could not be run (%s)." % type(e).__name__, finished=now_iso(), finished_epoch=time.time())
            finally:
                with self.lock:
                    self.procs.pop(jid, None)
                    self.cancelled.discard(jid)

    def _run(self, jid):
        meta = self.store.get(jid)
        if not meta or meta.get("status") != "queued":
            return
        job_dir = self.store.path(jid)
        in_dir, out_dir, log = os.path.join(job_dir, "in"), os.path.join(job_dir, "run"), os.path.join(job_dir, "log.txt")
        self.store.update(jid, status="running", started=now_iso(), started_epoch=time.time())
        kw = {"start_new_session": True} if os.name == "posix" else {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
        reason = None
        with open(log, "ab") as lf:
            proc = subprocess.Popen(self.command(meta, in_dir, out_dir), stdin=subprocess.DEVNULL, stdout=lf, stderr=subprocess.STDOUT, cwd=job_dir, env=self._env(), **kw)
            with self.lock:
                self.procs[jid] = proc
            deadline = time.time() + self.cfg.job_timeout
            while True:
                try:
                    rc = proc.wait(timeout=0.4)
                    break
                except subprocess.TimeoutExpired:
                    pass
                if jid in self.cancelled:
                    reason = "cancelled"; kill(proc); rc = proc.returncode; break
                if time.time() > deadline:
                    reason = "timeout"; kill(proc); rc = proc.returncode; break
        if reason is None and jid in self.cancelled:                       # cancel() may have stopped the process itself
            reason = "cancelled"
        self.finish(jid, rc, reason)

    @staticmethod
    def sense_unrun(run, summary):
        """True when a page or a document of this run was amber because its sense check did not run (pipeline.SENSE_UNRUN), so the site can offer to try it again."""
        import json
        paths = [os.path.join(run, "checks", p["page"] + ".json") for p in summary.get("pages", [])] + [os.path.join(run, "document", d["document"] + "_check.json") for d in summary.get("documents", []) if "light" in d]
        for path in paths:
            try:
                with open(path, encoding="utf8") as f:
                    if any(str(r).startswith("the sense check did not run") for r in json.load(f).get("reasons_amber", [])):
                        return True
            except (OSError, ValueError):
                pass
        return False

    def finish(self, jid, rc, reason):
        meta = self.store.get(jid) or {}
        job_dir = self.store.path(jid)
        run = os.path.join(job_dir, "run")
        led = harness.read_ledger(os.path.join(run, "ledger.jsonl"))
        spent = 0.0 if meta.get("demo") else round(harness.spent_inr(led), 2)
        try:
            with open(os.path.join(job_dir, "log.txt"), encoding="utf8", errors="replace") as f:
                log = f.read()
        except OSError:
            log = ""
        tail = "\n".join(log.splitlines()[-12:])
        summary_ok = os.path.exists(os.path.join(run, "summary.json"))
        fields = {"spent_inr": spent, "finished": now_iso(), "finished_epoch": time.time(), "stopped_by_budget": "STOP: the budget" in log}
        if reason == "cancelled":
            fields.update(status="cancelled", error=None)
        elif reason == "timeout":
            fields.update(status="failed", error="The job ran for more than %d minutes and was stopped. Use Retry: finished readings are not paid for twice." % int(self.cfg.job_timeout // 60))
        elif rc != 0:
            fields.update(status="failed", error=friendly_error(tail, self.cfg.data_dir))
        elif not summary_ok:
            fields.update(status="failed", error="The reading finished without a result. " + friendly_error(tail, self.cfg.data_dir))
        else:
            fields.update(status="done", error=None)
            try:
                import json
                with open(os.path.join(run, "summary.json"), encoding="utf8") as f:
                    s = json.load(f)
                lights = [p["light"] for p in s.get("pages", [])]
                fields["light_counts"] = {k: lights.count(k) for k in ("red", "amber", "green")}
                fields["sense_unrun"] = self.sense_unrun(run, s)
            except (OSError, ValueError, KeyError):
                pass
        recorded = meta.get("spent_inr_recorded", 0.0)
        fields["spent_inr_recorded"] = spent
        self.store.update(jid, **fields)
        if spent - recorded > 0 or not recorded:
            self.store.add_usage({"epoch": time.time(), "at": now_iso(), "user": meta.get("user"), "job": jid, "pages": meta.get("n_pages", 0), "spent_inr": round(max(0.0, spent - recorded), 2),
                                  "demo": bool(meta.get("demo")), "status": fields["status"]})
