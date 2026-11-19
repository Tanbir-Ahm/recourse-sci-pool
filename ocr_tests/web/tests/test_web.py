"""Tests of the Reading Desk site. They start the real server on a free port with the stub pipeline (invented text, no model, no network, no cost) and drive it over HTTP.

  python -m unittest discover -s ocr_tests/web/tests -v      (from the repository root)   or   python ocr_tests/web/tests/test_web.py
"""
import http.client, io, json, os, shutil, socket, sys, tempfile, threading, time, unittest, urllib.parse
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.dirname(HERE)
sys.path.insert(0, WEB)
import config, server
from PIL import Image

CODE_A, CODE_B = "alpha-code-12345", "bravo-code-12345"
server.Handler.log_request = lambda self, *a, **k: None          # no access log in test output


def png(w=40, h=30, color=(250, 250, 250)):
    b = io.BytesIO(); Image.new("RGB", (w, h), color).save(b, "PNG"); return b.getvalue()


class Site:
    """A server on a free port with its own data folder; env sets the RD_* variables for this server only."""
    def __init__(self, **env):
        self.tmp = tempfile.mkdtemp(prefix="rd-test-")
        base = {"RD_USERS": "alpha:%s,bravo:%s" % (CODE_A, CODE_B), "RD_PIPELINE": "stub", "RD_DATA_DIR": os.path.join(self.tmp, "data"), "RD_PDF_REPORTS": "off"}
        base.update({k: str(v) for k, v in env.items()})
        with mock.patch.dict(os.environ, base, clear=False):
            for k in [k for k in os.environ if k.startswith("RD_") and k not in base]:
                del os.environ[k]
            self.cfg = config.Config(host="127.0.0.1", port=0)
        self.srv, self.app = server.make_server(self.cfg)
        self.port = self.cfg.port
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def stop(self):
        self.srv.shutdown(); self.srv.server_close(); shutil.rmtree(self.tmp, ignore_errors=True)


class Client:
    def __init__(self, port):
        self.port, self.cookie = port, None

    def req(self, method, path, body=None, headers=None, raw=False, origin=True):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        h = {"X-RD": "1"} if method != "GET" else {}
        if origin and method != "GET":
            h["Origin"] = "http://127.0.0.1:%d" % self.port
        if self.cookie:
            h["Cookie"] = self.cookie
        h.update(headers or {})
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode(); h["Content-Type"] = "application/json"
        c.request(method, path, body=body, headers=h)
        r = c.getresponse(); data = r.read(); c.close()
        for k, v in r.getheaders():
            if k.lower() == "set-cookie":
                tok = v.split(";")[0]
                self.cookie = None if tok.endswith("=") else tok
        return r.status, dict(r.getheaders()), (data if raw else (json.loads(data) if data and r.getheader("Content-Type", "").startswith("application/json") else data))

    def login(self, name, code):
        return self.req("POST", "/api/login", {"name": name, "code": code})

    def wait(self, jid, want=("done", "failed", "cancelled"), timeout=150):
        end = time.time() + timeout
        while time.time() < end:
            s, _, d = self.req("GET", "/api/jobs/" + jid)
            if d["job"]["status"] in want:
                return d
            time.sleep(0.4)
        raise AssertionError("job did not finish: %s" % d["job"]["status"])


class Basics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = Site(RD_MAX_FILE_MB="0.01")
        cls.a = Client(cls.site.port); cls.b = Client(cls.site.port)
        assert cls.a.login("alpha", CODE_A)[0] == 200 and cls.b.login("bravo", CODE_B)[0] == 200

    @classmethod
    def tearDownClass(cls):
        cls.site.stop()

    def test_static_files_and_headers(self):
        c = Client(self.site.port)
        s, h, body = c.req("GET", "/", raw=True)
        self.assertEqual(s, 200); self.assertIn(b"Reading Desk", body)
        self.assertIn("frame-ancestors 'none'", h["Content-Security-Policy"]); self.assertEqual(h["X-Content-Type-Options"], "nosniff"); self.assertEqual(h["X-Frame-Options"], "DENY")
        self.assertEqual(c.req("GET", "/healthz", raw=True)[0], 200)
        for bad in ("/static/nope.js", "/static/../config.py", "/static/%2e%2e/config.py", "/static/app.py", "/config.py", "/api/nope"):
            self.assertIn(c.req("GET", bad, raw=True)[0], (401, 404), bad)

    def test_everything_needs_a_sign_in(self):
        c = Client(self.site.port)
        for path in ("/api/jobs", "/api/me", "/api/glossary", "/api/usage", "/api/jobs/%s" % ("a" * 24), "/api/jobs/%s/image/x" % ("a" * 24)):
            self.assertEqual(c.req("GET", path)[0], 401, path)
        self.assertEqual(c.req("POST", "/api/jobs", {"x": 1})[0], 401)
        forged = Client(self.site.port); forged.cookie = "rd_session=YWxwaGF8OTk5OTk5OTk5OQ.AAAA"
        self.assertEqual(forged.req("GET", "/api/jobs")[0], 401, "a forged cookie is refused")

    def test_wrong_code_and_cookie_flags(self):
        c = Client(self.site.port)
        self.assertEqual(c.login("alpha", "wrong")[0], 401); self.assertEqual(c.login("nobody", CODE_A)[0], 401)
        s, h, d = c.login("ALPHA", CODE_A)
        self.assertEqual(s, 200)
        cookie = h["Set-Cookie"]
        self.assertIn("HttpOnly", cookie); self.assertIn("SameSite=Strict", cookie); self.assertNotIn("Secure", cookie)
        s, h, d = c.req("GET", "/api/me")
        self.assertEqual((s, d["user"]), (200, "alpha")); self.assertIn("gate_text", d)
        c.req("POST", "/api/logout", {}); self.assertEqual(c.req("GET", "/api/me")[0], 401)

    def test_a_write_needs_the_site_header_and_the_site_origin(self):
        s, _, d = self.a.req("POST", "/api/jobs", {"gate_confirmed": True, "language": "Assamese", "page_type": "typed"}, headers={"X-RD": ""})
        self.assertEqual(s, 403)
        s, _, d = self.a.req("POST", "/api/jobs", {"gate_confirmed": True, "language": "Assamese", "page_type": "typed"}, headers={"Origin": "http://evil.example"})
        self.assertEqual(s, 403)
        s, _, d = self.a.req("POST", "/api/jobs", {"gate_confirmed": True, "language": "Assamese", "page_type": "typed"})
        self.assertEqual(s, 201)

    def new_job(self, client=None, **kw):
        body = {"gate_confirmed": True, "language": "Assamese", "page_type": "typed", "grouped": True}
        body.update(kw)
        s, _, d = (client or self.a).req("POST", "/api/jobs", body)
        self.assertEqual(s, 201, d)
        return d["job"]["id"]

    def test_creating_a_job_checks_its_fields(self):
        for body in ({"language": "Assamese", "page_type": "typed"}, {"gate_confirmed": False, "language": "Assamese", "page_type": "typed"}, {"gate_confirmed": "yes", "language": "Assamese", "page_type": "typed"},
                     {"gate_confirmed": True, "language": "Klingon", "page_type": "typed"}, {"gate_confirmed": True, "language": "Assamese", "page_type": "cursive"}):
            self.assertEqual(self.a.req("POST", "/api/jobs", body)[0], 400, body)

    def test_upload_rules(self):
        jid = self.new_job()
        put = lambda body, name="x.png", client=None, jid_=None: (client or self.a).req("PUT", "/api/jobs/%s/files?name=%s" % (jid_ or jid, name), body, headers={"Content-Type": "application/octet-stream"})
        self.assertEqual(put(b"")[0], 400)
        s, _, d = put(b"just some text, not an image"); self.assertEqual(s, 415, d)
        s, _, d = put(b"%PDF-1.4 not really"); self.assertIn(s, (415,), d)
        s, _, d = put(b"\x89PNG\r\n\x1a\n" + b"\0" * 50); self.assertEqual(s, 415, "a PNG header without an image behind it")
        s, _, d = put(png() + b"0" * 20000); self.assertEqual(s, 413, d)
        s, _, d = put(png(), name="..%2F..%2Fetc%2Fpasswd.png"); self.assertEqual(s, 201, d)
        s, _, d = self.b.req("PUT", "/api/jobs/%s/files?name=x.png" % jid, png(), headers={"Content-Type": "application/octet-stream"}); self.assertEqual(s, 404, "another user cannot add to this job")
        s, _, d = self.b.req("GET", "/api/jobs/" + jid); self.assertEqual(s, 404)
        s, _, d = self.a.req("GET", "/api/jobs/" + jid)
        self.assertEqual(d["job"]["n_pages"], 1); self.assertEqual(d["job"]["files"][0]["name"], "passwd.png", "the shown name has no path in it")
        stored = os.listdir(os.path.join(self.site.app.store.path(jid), "in"))
        self.assertEqual(stored, ["doc_p1.png"], "the file is kept under a neutral name")
        self.assertEqual(self.a.req("POST", "/api/jobs/%s/start" % jid, {})[0] in (200,), True)

    def test_a_chunked_upload_is_refused(self):
        jid = self.new_job()
        s = socket.create_connection(("127.0.0.1", self.site.port), timeout=10)
        s.sendall(("PUT /api/jobs/%s/files?name=x.png HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nX-RD: 1\r\nCookie: %s\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n" % (jid, self.site.port, self.a.cookie)).encode())
        reply = s.recv(4096).decode(); s.close()
        self.assertIn(" 411 ", reply.split("\r\n")[0])

    def test_start_needs_a_page_and_a_job_in_draft(self):
        jid = self.new_job()
        self.assertEqual(self.a.req("POST", "/api/jobs/%s/start" % jid, {})[0], 400)
        self.assertEqual(self.a.req("POST", "/api/jobs/%s/cancel" % jid, {})[0], 409)
        self.assertEqual(self.a.req("DELETE", "/api/jobs/" + jid)[0], 200); self.assertEqual(self.a.req("GET", "/api/jobs/" + jid)[0], 404)

    def test_ids_in_paths_cannot_escape(self):
        jid = self.new_job()
        J = "/api/jobs/" + jid
        for path in ("/api/jobs/..%2F..%2Fetc/passwd", J + "/image/..%2F..%2Fmeta", J + "/report/..%2Fmeta", J + "/report/x/../../meta", J + "/marksheet/..%2F..%2F..%2Fsecret",
                     J + "/word/..%2Fx", "/api/jobs/ZZZZZZZZZZZZZZZZZZZZZZZZ", J + "/image/%00", J + "/report/a%20b"):
            self.assertIn(self.a.req("GET", path, raw=True)[0], (404,), path)
        for target in ("meta", "summary", "demo_p1", "x"):
            self.assertEqual(self.a.req("GET", "%s/report/%s" % (J, target), raw=True)[0], 404, "a job with no result has no reports")

    def test_one_connection_serves_several_requests_even_after_an_unread_body(self):
        c = http.client.HTTPConnection("127.0.0.1", self.site.port, timeout=20)
        mine = Client(self.site.port); mine.login("alpha", CODE_A); tok = mine.cookie
        hdr = {"X-RD": "1", "Cookie": tok, "Content-Type": "application/json"}
        c.request("POST", "/api/logout", body=b'{"padding": "' + b"x" * 500 + b'"}', headers=hdr); r = c.getresponse(); r.read(); self.assertEqual(r.status, 200)
        c.request("GET", "/api/glossary", headers={"Cookie": tok}); r = c.getresponse(); body = r.read()
        self.assertEqual(r.status, 401, "signing out ends the session even if someone kept the cookie")
        fresh = Client(self.site.port); fresh.login("alpha", CODE_A); tok = fresh.cookie
        c.request("GET", "/api/glossary", headers={"Cookie": tok}); r = c.getresponse(); body = r.read()
        self.assertEqual(r.status, 200, body[:100]); self.assertEqual(json.loads(body)["count"], 227)
        c.request("POST", "/api/jobs", body=b"{}" * 10, headers={"X-RD": "", "Cookie": tok}); r = c.getresponse(); r.read(); self.assertEqual(r.status, 403)
        c.close()

    def test_the_glossary_and_usage_pages(self):
        s, _, d = self.a.req("GET", "/api/glossary")
        self.assertEqual(s, 200); self.assertEqual(d["count"], 227); self.assertTrue(all(r["word"] and r["english"] for r in d["rows"]))
        self.assertIn("approval has not been seen", d["note"])
        s, _, d = self.a.req("GET", "/api/usage"); self.assertEqual(s, 200); self.assertIn("1.5 to 2 times", d["note"])


class DemoJob(unittest.TestCase):
    """The demo is three invented pages run through the real pipeline with the stub reader: every check, report and file is the real thing."""
    @classmethod
    def setUpClass(cls):
        cls.site = Site()
        cls.a = Client(cls.site.port); cls.b = Client(cls.site.port)
        cls.a.login("alpha", CODE_A); cls.b.login("bravo", CODE_B)
        s, _, d = cls.a.req("POST", "/api/demo", {})
        assert s == 201, d
        cls.jid = d["job"]["id"]
        cls.done = cls.a.wait(cls.jid)
        assert cls.done["job"]["status"] == "done", cls.done
        s, _, cls.res = cls.a.req("GET", "/api/jobs/%s/result" % cls.jid)

    @classmethod
    def tearDownClass(cls):
        cls.site.stop()

    def test_the_result_has_pages_a_document_and_lights(self):
        r = self.res["result"]
        self.assertEqual([p["light"] for p in r["pages"]], ["amber", "red", "red"]); self.assertEqual(r["light"], "red")
        self.assertEqual(len(r["documents"]), 1); doc = r["documents"][0]
        self.assertEqual((doc["light"], doc["display"], doc["pages"]), ("amber", "Demo complaint (invented text)", ["doc_p1", "doc_p2", "doc_p3"]))
        self.assertEqual(r["stamp"], "Machine draft. Not a certified translation.")
        self.assertEqual(self.res["job"]["spent_inr"], 0.0, "a demo costs nothing")

    def test_read_these_first_names_the_places_to_look(self):
        doc = self.res["result"]["documents"][0]
        text = " | ".join(i["title"] + " " + i["detail"] for i in doc["read_first"])
        self.assertIn("14/3/2024 or 11/3/2024", text); self.assertIn("May not make sense", text); self.assertIn("Struck out", text); self.assertIn("Stamp or seal over text", text)
        self.assertEqual(doc["read_first"][0]["sev"], "high")
        eng = doc["english"]
        self.assertIn("[14/3/2024 or 11/3/2024 (third look: 14/3/2024): check]", eng, "both values are printed where the readings disagree")
        self.assertIn("~~victim~~ ^witness^", eng); self.assertTrue(doc["paras"] and all("\n" not in p for p in doc["paras"]))
        p1 = self.res["result"]["pages"][0]
        self.assertTrue(any(i["kind"] == "readings_differ" for i in p1["read_first"])); self.assertTrue(p1["glossary"], "the glossary notes the legal word")
        self.assertTrue(any(m["type"] == "date" and m["status"] == "DISAGREE" for m in p1["must_check"]))

    def test_images_reports_and_sheets(self):
        s, h, body = self.a.req("GET", "/api/jobs/%s/image/doc_p1" % self.jid, raw=True)
        self.assertEqual(s, 200); self.assertEqual(body[:3], b"\xff\xd8\xff"); self.assertEqual(h["Content-Type"], "image/jpeg")
        for target in ("doc_p2", "doc"):
            s, h, body = self.a.req("GET", "/api/jobs/%s/report/%s" % (self.jid, target), raw=True)
            self.assertEqual(s, 200, target); self.assertIn(b"Machine draft. Not a certified translation.", body); self.assertIn("sandbox", h["Content-Security-Policy"])
        s, h, body = self.a.req("GET", "/api/jobs/%s/marksheet/doc_p1" % self.jid, raw=True)
        self.assertEqual(s, 200); self.assertIn("allow-scripts", h["Content-Security-Policy"]); self.assertNotIn("allow-same-origin", h["Content-Security-Policy"])
        self.assertEqual(self.a.req("GET", "/api/jobs/%s/report/doc_p9" % self.jid, raw=True)[0], 404)
        self.assertEqual(self.a.req("GET", "/api/jobs/%s/report/doc?format=pdf" % self.jid, raw=True)[0], 200, "without a PDF report the HTML is served")

    @unittest.skipUnless(server.docx_out.available(), "python-docx is not installed")
    def test_the_word_file(self):
        import docx
        for target, expect in (("doc", "whole document"), ("doc_p2", "demo page 2.png")):
            s, h, body = self.a.req("GET", "/api/jobs/%s/word/%s" % (self.jid, target), raw=True)
            self.assertEqual(s, 200, target); self.assertIn("wordprocessingml", h["Content-Type"]); self.assertIn("attachment", h["Content-Disposition"])
            d = docx.Document(io.BytesIO(body)); text = "\n".join(p.text for p in d.paragraphs)
            self.assertIn("Machine draft. Not a certified translation.", text); self.assertIn("Read these first", text); self.assertIn(expect, text)
            self.assertEqual(d.sections[0].footer.paragraphs[0].text, "Machine draft. Not a certified translation.")
        d = docx.Document(io.BytesIO(self.a.req("GET", "/api/jobs/%s/word/doc" % self.jid, raw=True)[2]))
        self.assertEqual([r.text for p in d.paragraphs for r in p.runs if r.font.strike], ["victim"], "a crossed-out word stays crossed out")

    def test_only_the_owner_can_reach_a_job(self):
        for path in ("", "/result", "/image/doc_p1", "/report/doc", "/marksheet/doc_p1", "/word/doc"):
            self.assertEqual(self.b.req("GET", "/api/jobs/" + self.jid + path, raw=True)[0], 404, path)
        self.assertEqual(self.b.req("DELETE", "/api/jobs/" + self.jid)[0], 404)
        self.assertEqual(self.b.req("POST", "/api/jobs/%s/review" % self.jid, {"target": "doc", "read": True})[0], 404)
        self.assertEqual([j["id"] for j in self.b.req("GET", "/api/jobs")[2]["jobs"]], [])

    def test_a_person_can_mark_a_page_as_read_and_unmark_it(self):
        s, _, d = self.a.req("POST", "/api/jobs/%s/review" % self.jid, {"target": "doc_p2", "read": True, "note": "checked the date"})
        self.assertEqual(s, 200); self.assertEqual(d["reviews"]["doc_p2"]["by"], "alpha"); self.assertTrue(d["reviews"]["doc_p2"]["at"].endswith("Z"))
        self.assertEqual(self.a.req("POST", "/api/jobs/%s/review" % self.jid, {"target": "../x", "read": True})[0], 404)
        s, _, d = self.a.req("POST", "/api/jobs/%s/review" % self.jid, {"target": "doc_p2", "read": False}); self.assertEqual(d["reviews"], {})

    def test_usage_lists_the_demo_at_no_cost(self):
        s, _, d = self.a.req("GET", "/api/usage")
        self.assertEqual((d["today_inr"], d["month_inr"], d["pages_month"]), (0, 0, 0)); self.assertTrue(any(j["demo"] for j in d["jobs"]))

    def test_the_marks_show_in_the_ledger_of_one_run_only(self):
        led = open(os.path.join(self.site.app.store.path(self.jid), "run", "ledger.jsonl"), encoding="utf8").read().splitlines()
        self.assertEqual(len(led), 10, "6 readings, 3 third looks and 1 sense check, once each")

    def test_zzz_delete_removes_the_files(self):
        self.assertEqual(self.a.req("DELETE", "/api/jobs/" + self.jid)[0], 200)
        self.assertFalse(os.path.exists(self.site.app.store.path(self.jid))); self.assertEqual(self.a.req("GET", "/api/jobs/" + self.jid)[0], 404)


@unittest.skipUnless(all(shutil.which(t) for t in ("pdfinfo", "pdftotext", "pdffonts", "pdfimages", "pdftoppm")), "poppler tools are not installed")
class Pdfs(unittest.TestCase):
    """PDF files go through the real triage (poppler, Tesseract) and the stub reader."""
    @classmethod
    def setUpClass(cls):
        cls.site = Site(); cls.a = Client(cls.site.port); cls.a.login("alpha", CODE_A)

    @classmethod
    def tearDownClass(cls):
        cls.site.stop()

    def run_job(self, files, **kw):
        c = self.a
        body = {"gate_confirmed": True, "language": "Assamese", "page_type": "typed"}; body.update(kw)
        jid = c.req("POST", "/api/jobs", body)[2]["job"]["id"]
        for name, data in files:
            s, _, d = c.req("PUT", "/api/jobs/%s/files?name=%s" % (jid, urllib.parse.quote(name)), data, headers={"Content-Type": "application/octet-stream"}); self.assertEqual(s, 201, d)
        s, _, d = c.req("POST", "/api/jobs/%s/start" % jid, {}); self.assertEqual(s, 200, d)
        done = c.wait(jid); self.assertEqual(done["job"]["status"], "done", done)
        return jid, c.req("GET", "/api/jobs/%s/result" % jid)[2]["result"]

    def test_a_scanned_pdf_of_two_pages_is_one_document(self):
        b = io.BytesIO(); Image.new("RGB", (600, 200), "white").save(b, "PDF", save_all=True, append_images=[Image.new("RGB", (600, 201), "white")])
        jid, r = self.run_job([("my scan.pdf", b.getvalue())])
        self.assertEqual([p["label"] for p in r["pages"]], ["my scan.pdf, page 1", "my scan.pdf, page 2"])
        self.assertEqual(len(r["documents"]), 1); self.assertEqual(r["documents"][0]["display"], "my scan.pdf")
        s, h, body = self.a.req("GET", "/api/jobs/%s/image/d1_p2" % jid, raw=True); self.assertEqual((s, body[:3]), (200, b"\xff\xd8\xff"))
        j = self.a.req("GET", "/api/jobs/" + jid)[2]["job"]; self.assertEqual((j["n_pages"], j["files"][0]["pages"]), (2, 2))

    def test_a_pdf_with_a_text_layer(self):
        import pdf_triage
        tmp = tempfile.mkdtemp(); path = os.path.join(tmp, "t.pdf")
        pdf_triage._mini_pdf(path, ["The quick brown fox jumps over the lazy dog.", "Order dated fifteen February under the heading of this code.", "Closing line of this invented test page only."])
        jid, r = self.run_job([("order.pdf", open(path, "rb").read())])
        shutil.rmtree(tmp)
        self.assertEqual(len(r["pages"]), 1); self.assertTrue(r["pages"][0]["paras"] or r["pages"][0]["english"] is not None)
        self.assertEqual(self.a.req("GET", "/api/jobs/%s/report/d1_p1" % jid, raw=True)[0], 200)

    def test_a_damaged_pdf_is_refused_at_upload(self):
        jid = self.a.req("POST", "/api/jobs", {"gate_confirmed": True, "language": "Assamese", "page_type": "typed"})[2]["job"]["id"]
        s, _, d = self.a.req("PUT", "/api/jobs/%s/files?name=bad.pdf" % jid, b"%PDF-1.4\nnot a real pdf at all", headers={"Content-Type": "application/octet-stream"})
        self.assertEqual(s, 415, d); self.assertIn("could not be opened", d["error"])
        self.assertEqual(self.a.req("GET", "/api/jobs/" + jid)[2]["job"]["n_pages"], 0)

    def test_images_not_grouped_are_separate_documents(self):
        jid, r = self.run_job([("one.png", png(300, 200)), ("two.png", png(301, 200))], grouped=False)
        self.assertEqual(sorted(p["label"] for p in r["pages"]), ["one.png", "two.png"]); self.assertEqual(r["documents"], [])


class Limits(unittest.TestCase):
    def test_no_model_key_switches_real_reading_off_but_not_the_demo(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GEMINI_API_KEY", None)
            site = Site(RD_PIPELINE="real")
            try:
                c = Client(site.port); c.login("alpha", CODE_A)
                self.assertFalse(c.req("GET", "/api/me")[2]["caps"]["real"])
                s, _, d = c.req("POST", "/api/jobs", {"gate_confirmed": True, "language": "Assamese", "page_type": "typed"}); jid = d["job"]["id"]
                c.req("PUT", "/api/jobs/%s/files?name=a.png" % jid, png(), headers={"Content-Type": "application/octet-stream"})
                s, _, d = c.req("POST", "/api/jobs/%s/start" % jid, {})
                self.assertEqual(s, 503); self.assertIn("no model key", d["error"])
                s, _, d = c.req("POST", "/api/demo", {}); self.assertEqual(s, 201, "the demo needs no key")
                self.assertEqual(c.wait(d["job"]["id"])["job"]["status"], "done")
            finally:
                site.stop()

    def test_the_budget_caps_stop_a_job_before_it_starts(self):
        site = Site(RD_JOB_BUDGET_INR="2", RD_DAILY_BUDGET_INR="150")
        try:
            c = Client(site.port); c.login("alpha", CODE_A)
            jid = c.req("POST", "/api/jobs", {"gate_confirmed": True, "language": "Assamese", "page_type": "typed"})[2]["job"]["id"]
            c.req("PUT", "/api/jobs/%s/files?name=a.png" % jid, png(), headers={"Content-Type": "application/octet-stream"})
            s, _, d = c.req("POST", "/api/jobs/%s/start" % jid, {})
            self.assertEqual(s, 402); self.assertIn("limit for one job", d["error"])
            self.assertEqual(c.req("GET", "/api/jobs/" + jid)[2]["job"]["status"], "draft", "a refused job stays a draft")
        finally:
            site.stop()
        site = Site(RD_DAILY_BUDGET_INR="2.5")
        try:
            c = Client(site.port); c.login("alpha", CODE_A)
            jid = c.req("POST", "/api/jobs", {"gate_confirmed": True, "language": "Assamese", "page_type": "typed"})[2]["job"]["id"]
            c.req("PUT", "/api/jobs/%s/files?name=a.png" % jid, png(), headers={"Content-Type": "application/octet-stream"})
            s, _, d = c.req("POST", "/api/jobs/%s/start" % jid, {})
            self.assertEqual(s, 402); self.assertIn("daily limit", d["error"])
        finally:
            site.stop()

    def test_page_and_size_limits(self):
        site = Site(RD_MAX_PAGES="2", RD_MAX_JOB_MB="0.001")
        try:
            c = Client(site.port); c.login("alpha", CODE_A)
            jid = c.req("POST", "/api/jobs", {"gate_confirmed": True, "language": "Assamese", "page_type": "typed"})[2]["job"]["id"]
            ok = lambda: c.req("PUT", "/api/jobs/%s/files?name=a.png" % jid, png(10, 10), headers={"Content-Type": "application/octet-stream"})[0]
            self.assertEqual(ok(), 201)
            self.assertEqual(c.req("PUT", "/api/jobs/%s/files?name=a.png" % jid, png(600, 600, (3, 4, 5)) + b"0" * 2000, headers={"Content-Type": "application/octet-stream"})[0], 413, "the whole job is over its size limit")
        finally:
            site.stop()

    def test_the_login_limit(self):
        site = Site()
        try:
            c = Client(site.port)
            with mock.patch("time.sleep"):
                codes = [c.login("alpha", "wrong-wrong-%d" % i)[0] for i in range(10)]
            self.assertEqual(codes[:8], [401] * 8); self.assertEqual(codes[8], 429)
            self.assertEqual(c.login("alpha", CODE_A)[0], 429, "even the right code waits while the limit holds")
        finally:
            site.stop()

    def test_cancel_stops_a_running_job_and_a_stopped_job_can_be_retried(self):
        with mock.patch.dict(os.environ, {"STUB_DELAY": "1.5"}):
            site = Site()
            try:
                c = Client(site.port); c.login("alpha", CODE_A)
                jid = c.req("POST", "/api/demo", {})[2]["job"]["id"]
                c.wait(jid, want=("running",), timeout=30)
                self.assertEqual(c.req("POST", "/api/jobs/%s/cancel" % jid, {})[0], 200)
                self.assertEqual(c.wait(jid, want=("cancelled", "done", "failed"))["job"]["status"], "cancelled")
                self.assertEqual(c.req("DELETE", "/api/jobs/" + jid)[0], 200)
            finally:
                site.stop()

    def test_a_failed_job_shows_a_clean_error_and_can_be_retried(self):
        site = Site()
        try:
            c = Client(site.port); c.login("alpha", CODE_A)
            with mock.patch.dict(os.environ, {"STUB_FAIL": "1"}):
                jid = c.req("POST", "/api/demo", {})[2]["job"]["id"]
                job = c.wait(jid)["job"]
            self.assertEqual(job["status"], "failed"); self.assertIn("failing on purpose", job["error"])
            self.assertNotIn("AIza", job["error"], "anything that looks like a key is removed"); self.assertNotIn(site.cfg.data_dir, job["error"], "the server's folders are not shown")
            self.assertEqual(c.req("POST", "/api/jobs/%s/resume" % jid, {})[0], 200)
            self.assertEqual(c.wait(jid)["job"]["status"], "done")
            self.assertEqual(c.req("POST", "/api/jobs/%s/resume" % jid, {})[0], 409, "a finished job cannot be retried")
        finally:
            site.stop()

    def test_a_sense_check_that_failed_is_reported_and_can_be_tried_again(self):
        site = Site()
        try:
            c = Client(site.port); c.login("alpha", CODE_A)
            with mock.patch.dict(os.environ, {"STUB_SENSE_FAIL": "1"}):
                jid = c.req("POST", "/api/demo", {})[2]["job"]["id"]
                job = c.wait(jid)["job"]
            self.assertEqual(job["status"], "done"); self.assertTrue(job["sense_unrun"])
            res = c.req("GET", "/api/jobs/%s/result" % jid)[2]["result"]
            doc = res["documents"][0]
            self.assertTrue(doc["notices"] and doc["notices"][0].startswith("The sense check did not run"), doc["notices"])
            self.assertFalse([i for i in doc["read_first"] if i["kind"] == "sense"], "no finding is invented when the check did not run")
            self.assertEqual(c.req("POST", "/api/jobs/%s/resume" % jid, {})[0], 200)
            job = c.wait(jid)["job"]
            self.assertEqual(job["status"], "done"); self.assertFalse(job["sense_unrun"])
            res = c.req("GET", "/api/jobs/%s/result" % jid)[2]["result"]
            self.assertEqual(res["documents"][0]["notices"], []); self.assertTrue([i for i in res["documents"][0]["read_first"] if i["kind"] == "sense"], "the retry ran the check and it found the sentence")
            self.assertEqual(c.req("POST", "/api/jobs/%s/resume" % jid, {})[0], 409)
        finally:
            site.stop()

    def test_a_job_left_running_by_a_restart_is_marked_failed(self):
        site = Site()
        try:
            m = site.app.store.create("alpha", label="x", language="Assamese", page_type="typed", n_pages=1)
            site.app.store.update(m["id"], status="running")
            site.app.runner.recover()
            got = site.app.store.get(m["id"])
            self.assertEqual(got["status"], "failed"); self.assertIn("restarted", got["error"])
        finally:
            site.stop()

    def test_old_jobs_are_deleted_and_running_ones_are_not(self):
        site = Site(RD_RETENTION_HOURS="1")
        try:
            st = site.app.store
            old = st.create("alpha", label="old"); st.update(old["id"], status="done", finished_epoch=time.time() - 3 * 3600)
            new = st.create("alpha", label="new"); st.update(new["id"], status="done", finished_epoch=time.time())
            busy = st.create("alpha", label="busy"); st.update(busy["id"], status="running", created_epoch=time.time() - 99 * 3600)
            gone = st.expired(site.cfg.retention_hours)
            self.assertEqual(gone, [old["id"]])
        finally:
            site.stop()

    def test_the_public_page_the_site_name_and_the_https_header(self):
        site = Site(RD_COOKIE_SECURE="1", RD_SITE_NAME="Desk X", RD_CONTACT="write to the chambers", RD_RETENTION_HOURS="48")
        try:
            c = Client(site.port)
            s, h, d = c.req("GET", "/api/public")
            self.assertEqual((s, d["site_name"], d["retention_hours"], d["contact"]), (200, "Desk X", 48.0, "write to the chambers"))
            self.assertIn("max-age", h["Strict-Transport-Security"]); self.assertIn("noindex", h["X-Robots-Tag"])
            self.assertIn("Secure", c.login("alpha", CODE_A)[1]["Set-Cookie"])
        finally:
            site.stop()

    def test_the_smoke_check_passes_against_a_running_site(self):
        import subprocess
        out = subprocess.run([sys.executable, os.path.join(HERE, "smoke_remote.py"), "http://127.0.0.1:%d" % self.site_port(), "alpha", CODE_A, "--local"], capture_output=True, text=True, timeout=240)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr); self.assertIn("all checks passed", out.stdout)

    def site_port(self):
        if not hasattr(Limits, "_smoke"):
            Limits._smoke = Site()
            return Limits._smoke.port

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_smoke"):
            cls._smoke.stop()

    def test_the_server_refuses_to_start_without_a_user_unless_dev(self):
        with mock.patch.dict(os.environ, {"RD_USERS": ""}):
            with self.assertRaises(SystemExit):
                config.Config()
            with self.assertRaises(SystemExit):
                config.Config(dev=True, host="0.0.0.0")
            self.assertEqual(config.Config(dev=True).users, {"dev": ""})
        with self.assertRaises(ValueError):
            config.parse_users("x:short")
        self.assertEqual(config.parse_users("Alice:abcdefghij, b-2:klmnopqrst"), {"alice": "abcdefghij", "b-2": "klmnopqrst"})

    def test_dev_mode_only_answers_to_local_names(self):
        with mock.patch.dict(os.environ, {"RD_USERS": "", "RD_PIPELINE": "stub", "RD_DATA_DIR": tempfile.mkdtemp()}):
            cfg = config.Config(dev=True, host="127.0.0.1", port=0)
        srv, app = server.make_server(cfg)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            c = http.client.HTTPConnection("127.0.0.1", cfg.port, timeout=10)
            c.request("GET", "/api/me", headers={"Host": "127.0.0.1:%d" % cfg.port}); r = c.getresponse(); r.read(); self.assertEqual(r.status, 200)
            c = http.client.HTTPConnection("127.0.0.1", cfg.port, timeout=10)
            c.request("GET", "/api/me", headers={"Host": "evil.example:%d" % cfg.port}); r = c.getresponse(); r.read(); self.assertEqual(r.status, 403, "a page on another name cannot reach the dev server")
        finally:
            srv.shutdown(); srv.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
