"""Is the site up, and is it set up safely? A check you can run against the live address yourself, without trusting anyone's word.

  python smoke_remote.py https://desk.example.com                  # the checks that need no sign-in
  python smoke_remote.py https://desk.example.com NAME CODE        # and the demo end to end (invented pages, no model, no cost; the demo job is deleted)
  python smoke_remote.py http://127.0.0.1:8080 NAME CODE --local   # a server on this computer (skips the checks that only make sense over HTTPS)

It exits 1 if anything fails. The wrong-code check makes one wrong try, which counts towards the limit of 8 an address gets in ten minutes.
"""
import http.client, json, ssl, sys, time, urllib.parse


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    local = "--local" in argv
    if not args:
        sys.exit(__doc__)
    base = urllib.parse.urlsplit(args[0])
    name, code = (args[1], args[2]) if len(args) >= 3 else (None, None)
    https = base.scheme == "https"
    fails = []

    def check(ok, what):
        print(("ok    " if ok else "FAIL  ") + what)
        if not ok:
            fails.append(what)

    def conn(scheme=None, host=None):
        scheme, host = scheme or base.scheme, host or base.netloc
        return (http.client.HTTPSConnection(host, timeout=30, context=ssl.create_default_context()) if scheme == "https" else http.client.HTTPConnection(host, timeout=30))

    cookie = [None]

    def req(method, path, body=None, headers=None):
        c = conn()
        h = {"X-RD": "1"} if method != "GET" else {}
        if cookie[0]:
            h["Cookie"] = cookie[0]
        if body is not None:
            body = json.dumps(body); h["Content-Type"] = "application/json"
        h.update(headers or {})
        c.request(method, path, body=body, headers=h)
        r = c.getresponse(); data = r.read(); hd = {k.lower(): v for k, v in r.getheaders()}; c.close()
        try:
            data = json.loads(data) if hd.get("content-type", "").startswith("application/json") else data
        except ValueError:
            pass
        return r.status, hd, data

    s, h, body = req("GET", "/")
    check(s == 200 and b"<title>" in body, "the front page loads")
    check("frame-ancestors 'none'" in h.get("content-security-policy", "") and h.get("x-content-type-options") == "nosniff" and h.get("x-frame-options") == "DENY", "security headers are set (CSP, nosniff, no framing)")
    check("noindex" in h.get("x-robots-tag", ""), "search engines are told not to index it")
    check(req("GET", "/healthz")[0] == 200, "the health check answers")
    if https and not local:
        check("max-age" in h.get("strict-transport-security", ""), "HTTPS is pinned (Strict-Transport-Security)")
        try:
            c = conn("http", base.netloc.split(":")[0]); c.request("GET", "/"); r = c.getresponse(); r.read()
            check(r.status in (301, 302, 307, 308) and r.getheader("Location", "").startswith("https://"), "plain HTTP is sent to HTTPS")
        except OSError as e:
            check(False, "plain HTTP answers with a redirect (%s)" % type(e).__name__)
    for path in ("/api/jobs", "/api/me", "/api/glossary", "/api/usage"):
        check(req("GET", path)[0] == 401, "%s needs a sign-in" % path)
    check(req("GET", "/static/../config.py")[0] in (400, 404) and req("GET", "/config.py")[0] == 404, "server files are not reachable by path")
    s, h, d = req("POST", "/api/login", {"name": "nobody", "code": "wrong-code-for-a-check"})
    check(s == 401 and "set-cookie" not in h, "a wrong access code is refused and sets no cookie")
    s, h, d = req("GET", "/api/public")
    check(s == 200 and "retention_hours" in d, "the public page says how long papers are kept (%s hours)" % (d.get("retention_hours") if isinstance(d, dict) else "?"))
    if name:
        s, h, d = req("POST", "/api/login", {"name": name, "code": code})
        check(s == 200, "sign-in works")
        if s == 200:
            sc = h.get("set-cookie", "")
            cookie[0] = sc.split(";")[0]
            check("HttpOnly" in sc and (("Secure" in sc) or not https or local), "the cookie is HttpOnly%s" % (" and Secure" if https else ""))
            s, h, d = req("POST", "/api/demo", {})
            check(s == 201, "the demo job starts")
            jid = d["job"]["id"] if s == 201 else None
            end = time.time() + 180
            while jid and time.time() < end:
                st = req("GET", "/api/jobs/" + jid)[2]["job"]["status"]
                if st in ("done", "failed", "cancelled"):
                    break
                time.sleep(2)
            if jid:
                s, h, d = req("GET", "/api/jobs/%s/result" % jid)
                res = d.get("result") if isinstance(d, dict) else None
                check(bool(res) and len(res["pages"]) == 3 and res["stamp"].startswith("Machine draft"), "the demo reads three pages and carries the stamp")
                s, h, img = req("GET", "/api/jobs/%s/image/doc_p1" % jid)
                check(s == 200 and img[:3] == b"\xff\xd8\xff", "a page picture is served")
                check(req("DELETE", "/api/jobs/" + jid)[0] == 200 and req("GET", "/api/jobs/" + jid)[0] == 404, "the job and its files can be deleted")
            old = cookie[0]
            req("POST", "/api/logout", {})
            cookie[0] = old
            check(req("GET", "/api/jobs")[0] == 401, "signing out ends the session on the server")
    print("\n%s" % ("all checks passed" if not fails else "%d check(s) FAILED" % len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
