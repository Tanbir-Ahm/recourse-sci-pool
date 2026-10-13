"""Tests for the index loader of sci_search_service.py (fetch_index / ensure_index) against a local stand-in for the GitHub API. No network beyond localhost. Run: python test_sci_search_fetch.py"""
import io, json, os, sys, tarfile, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sci_search_service as S

F = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond: F.append(name)

SHA = "ab12cd34ef56ab12cd34ef56ab12cd34ef56ab12"
def make_tar(with_index=True):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        def add(name, data):
            ti = tarfile.TarInfo(name); ti.size = len(data); tf.addfile(ti, io.BytesIO(data))
        add("Owner-repo-ab12cd3/README.md", b"readme")
        add("Owner-repo-ab12cd3/review_data/x.json", b"{}")
        if with_index:
            add("Owner-repo-ab12cd3/index/000000.meta.jsonl.gz", b"meta")
            add("Owner-repo-ab12cd3/index/000000.vec.npy", b"vec")
            add("Owner-repo-ab12cd3/index/sub/000000.docs.jsonl.gz", b"docs")
        add("Owner-repo-ab12cd3/index/../evil.txt", b"x")
    return buf.getvalue()

SEEN = {"auth": [], "paths": []}
STATE = {"tar": make_tar(), "code": 200}
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        SEEN["paths"].append(self.path); SEEN["auth"].append((self.path, self.headers.get("Authorization")))
        if STATE["code"] != 200 and self.path.startswith("/repos/Owner/repo/commits"):
            self.send_response(STATE["code"]); self.end_headers(); return
        if self.path.startswith("/repos/Owner/repo/commits/"):
            body = json.dumps({"sha": SHA}).encode(); self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif self.path == f"/repos/Owner/repo/tarball/{SHA}":
            self.send_response(302); self.send_header("Location", f"http://127.0.0.1:{self.server.server_address[1]}/signed/download?sig=1"); self.end_headers()
        elif self.path.startswith("/signed/download"):
            self.send_response(200); self.send_header("Content-Length", str(len(STATE["tar"]))); self.end_headers(); self.wfile.write(STATE["tar"])
        else:
            self.send_response(404); self.end_headers()
srv = ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
api = f"http://127.0.0.1:{srv.server_address[1]}"

d = tempfile.mkdtemp()
msgs = []
sha = S.fetch_index(d, "Owner/repo", "claude/sci-index", "TOKEN123", api, log=msgs.append)
check("the index folder and the commit are written", sha == SHA and S.has_index(d) and open(os.path.join(d, "INDEX_COMMIT")).read().strip() == SHA)
check("nested files are kept, other folders are not, a path with .. is refused", os.path.exists(os.path.join(d, "index", "sub", "000000.docs.jsonl.gz")) and not os.path.exists(os.path.join(d, "README.md")) and not os.path.exists(os.path.join(d, "evil.txt")) and not os.path.exists(os.path.join(d, "review_data")))
check("the token went to the API address only, not to the signed download address", any(a == "Bearer TOKEN123" for p, a in SEEN["auth"] if p.startswith("/repos/")) and all(a is None for p, a in SEEN["auth"] if p.startswith("/signed/")), SEEN["auth"])
check("the token is in no message", all("TOKEN123" not in m for m in msgs))
check("git_head reads the recorded commit when there is no .git", S.git_head(d) == SHA)
check("nothing is left over from the download", not os.path.exists(os.path.join(d, ".incoming")))
check("ensure_index does nothing when the index is already there", S.ensure_index(d, log=lambda *_: None) is None)

d2 = tempfile.mkdtemp()
m2 = []
d3 = tempfile.mkdtemp()
S.fetch_index(d3, "Owner/repo", "b", None, api, log=m2.append)
check("no token: it tries anonymously (a public repository) and says so", S.has_index(d3) and any("without one" in m for m in m2) and SEEN["auth"][-1][1] is None)
STATE["code"] = 404
try:
    S.fetch_index(d2, "Owner/repo", "b", "TOKEN123", api, log=lambda *_: None); ok = False
except S.FetchError as e:
    ok = "404" in str(e) and "TOKEN123" not in str(e)
check("a refused request is reported without the token", ok)
STATE["code"] = 200
STATE["tar"] = make_tar(with_index=False)
try:
    S.fetch_index(d2, "Owner/repo", "b", "TOKEN123", api, log=lambda *_: None); ok = False
except S.FetchError as e:
    ok = "no index files" in str(e)
check("a download without index files fails and leaves nothing half-written", ok and not S.has_index(d2) and not os.path.exists(os.path.join(d2, ".incoming")))
os.environ.pop("SCI_INDEX_REPO", None)
try:
    S.ensure_index(tempfile.mkdtemp(), log=lambda *_: None); ok = False
except S.FetchError as e:
    ok = "SCI_INDEX_REPO" in str(e)
check("ensure_index says what is missing when nothing is configured", ok)
print("\nALL PASSED" if not F else f"\n{len(F)} FAILED: {F}")
sys.exit(1 if F else 0)
