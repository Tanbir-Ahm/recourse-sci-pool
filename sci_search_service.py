"""sci-search: recipe B over the Supreme Court index as a small private HTTP service (Phase 1 step 10 of DEPLOYMENT_PLAN.md).

Recipe B (the stage F baseline, kept by the owner on 2026-10-12): 100 passages by meaning (voyage-law-2) + 50 by keyword (BM25) + up to 30 per "section N" in the question, merged by reciprocal
rank (K = 60) into 60 candidates, re-ranked by rerank-3-lite, multiplied by the passage-type weights (and 1.10 when the passage names a section the question names), top 10. The side indexes
(review_data/side_index/*) are searched with the main index. The ranking code mirrors review_tools/pool_runner.Engine; test_sci_search_service.py checks the two give the same list.

    python sci_search_service.py serve [--host ::] [--port $PORT]     # the service; needs VOYAGE_API_KEY and SCI_SEARCH_TOKEN
    python sci_search_service.py report [--json OUT]                       # sizes, load time and memory, no network, no key needed
    python sci_search_service.py ask "question text"                       # one real search from the command line (costs about a tenth of a cent of Voyage credit)

Endpoints: GET /health (no secret, no question text); POST /search {"question": "...", "k": 10} with header X-Search-Token. Every answer says what it is: tier "wider_pool_not_independently_verified",
the index commit, and the date the index ends. Nothing in it says a case is good law; the website puts the Overruled Register and the cards overlay on top (REGISTER_SITE_PATCH.md).
Safety: SCI_SEARCH_ENABLED=0 turns /search off at once (503); a daily cap on re-rank tokens (SCI_DAILY_RERANK_TOKENS, default 5,000,000: about 230 questions a day at the measured 21,700 tokens each, about a quarter of a dollar) answers 429 when spent; one search
at a time (a lock); questions over 2,000 characters are refused; the caller is expected to fail open (answer as it does today) on anything but 200.
Names and links: names_table/names_table.json.gz (built by names_table/build_names_table.py for the same index commit; the service refuses to start on a table built for another commit) gives each result a readable case_name, date, citations and a link to the judgment's PDF.
Environment: SCI_NAMES_TABLE (default names_table/names_table.json.gz), SCI_INDEX_DIR (default ../recourse-sci-index), SCI_SIDE_INDEXES (comma-separated folders; default the three in review_data/side_index), SCI_INDEX_COMMIT (when the index folder is not a git checkout),
SCI_QUOTES (on|off, default off: passages numbered outside their judgment's own paragraph sequence get a "quote" field; sci_quotes.py), SCI_RERANK_MODEL (default rerank-3-lite), SCI_MAX_TEXT (characters of passage text returned, default 1500), VOYAGE_API_KEY, SCI_SEARCH_TOKEN, PORT.
SCI_AUTHORITY (on|off, default off): authority-aware ranking (authority_search.py, 2026-10-29): the judgments that the retrieved judgments themselves name are fetched and favoured, so that a landmark is not outranked by the
restatements of it. Needs the table authority_graph.py builds for the same index (SCI_AUTHORITY_TABLE, default authority_table/authority_<index commit>.json.gz; the service refuses to start on a missing table or one made for
another commit). Tuning: SCI_AUTH_PRIOR, SCI_AUTH_CONSENSUS, SCI_AUTH_MIN_FRAC, SCI_AUTH_MAX, SCI_AUTH_PASSAGES, SCI_AUTH_MIN_COUNT. Off, the service ranks exactly as before and the results carry no extra field.
"""
import collections
import datetime
import glob
import gzip
import hashlib
import json
import os
import re
import resource
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sci_index as si  # noqa: E402

EMBED_MODEL = si.MODEL
RERANK_MODEL = "rerank-3-lite"
PRICE_RERANK, PRICE_EMBED = 0.05, 0.12          # dollars per million tokens, as in review_tools/pool_runner.py (estimates; the service's own counts are what is billed)
DEFAULT_SIDE_INDEXES = ("review_data/side_index/2026-10-09_correcting_judgments", "review_data/side_index/2026-10-09_fetched_documents", "review_data/side_index/2026-10-09_fetched_shivangi_bansal")
TIER = "wider_pool_not_independently_verified"
COURT_DEFAULT = "Supreme Court of India"       # every document of the first index, and any result row of a names table made before the table had a court column
COURT_UNKNOWN = "Court not recorded"           # a document the names table does not know: never labelled as the Supreme Court
DISCLAIMER = ("These passages come from a search of a much wider judgment database. Nobody at Recourse has read and confirmed them. Read the real judgment yourself, or with a lawyer, before relying on it. "
              "This search does not say whether a decision is still good law.")
MAX_QUESTION = 2000
RETRYABLE = {"RateLimitError", "ServiceUnavailableError", "APIConnectionError", "Timeout", "TryAgain", "APIError"}


class Refused(Exception):
    """A request the service will not run; `status` is the HTTP code."""

    def __init__(self, status, reason):
        super().__init__(reason)
        self.status, self.reason = status, reason


KEEP = ("doc", "i", "pn", "page", "section", "h", "text")


def _slim(m):
    """Only the fields the service uses (the index rows carry four more that cost memory)."""
    return {k: m[k] for k in KEEP if k in m}


def _call(fn, *args, tries=4, pause=2.0, sleep=time.sleep, **kw):
    for i in range(tries):
        try:
            return fn(*args, **kw)
        except Exception as e:                      # noqa: BLE001
            if type(e).__name__ in RETRYABLE and i < tries - 1:
                sleep(pause * 2 ** i)
                continue
            raise


def build_fts(metas):
    """The keyword index. Contentless (the text is not stored a second time; the passage text stays in `metas`): the same rows in the same bm25 order as the stored-text table the experiments used, about 340 MB less memory."""
    fts = sqlite3.connect(":memory:", check_same_thread=False)
    fts.execute("create virtual table f using fts5(text, content='', tokenize='porter unicode61')")
    fts.executemany("insert into f(rowid, text) values(?,?)", ((i, m["text"]) for i, m in enumerate(metas)))
    return fts


def _title_table(index_dirs):
    """doc -> 'Petitioner v. Respondent (date)' from the index's case records (crawl judgments) or the title and date the bucket judgment arrived with. As review_tools/pool_runner.titles."""
    case_meta, src_title = {}, {}
    for d in index_dirs:
        for f in glob.glob(os.path.join(d, "index", "*.docs.jsonl.gz")):
            with gzip.open(f, "rt", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        r = json.loads(line)
                        if r.get("case"):
                            case_meta[r["doc"]] = r["case"]
                        src = r.get("src")
                        if isinstance(src, dict) and src.get("title"):
                            src_title[r["doc"]] = (src["title"], src.get("date"))
    return case_meta, src_title


def _src_courts(index_dirs):
    """doc -> the court its own source record names (only the newer documents carry one), so that a High Court document is never taken for a Supreme Court one even when no names table is loaded."""
    out = {}
    for d in index_dirs:
        for f in glob.glob(os.path.join(d, "index", "*.docs.jsonl.gz")):
            with gzip.open(f, "rt", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        r = json.loads(line)
                        src = r.get("src")
                        if isinstance(src, dict) and src.get("court"):
                            out[r["doc"]] = str(src["court"]).strip()
    return out


def _make_title(case_meta, src_title, extra=None, header=None):
    def title(doc):
        c = case_meta.get(doc)
        if c and (c.get("pet") or c.get("resp")):
            return (f"{c.get('pet', '?')} v. {c.get('resp', '?')}" + (f" ({c['date']})" if c.get("date") else ""))[:200]
        if doc in src_title:
            name, date = src_title[doc]
            return (re.sub(r"\s+", " ", name) + (f" ({date})" if date else ""))[:200]
        if extra and doc in extra:
            return extra[doc][:200]
        return (header or {}).get(doc)
    return title


def _latest_date(title_strings):
    best = None
    for t in title_strings:
        m = re.search(r"\((\d{1,2})[-/.](\d{1,2})[-/.]((?:19|20)\d\d)\)", t or "")
        if m:
            try:
                d = datetime.date(int(m[3]), int(m[2]), int(m[1]))
            except ValueError:
                continue
            best = d if best is None or d > best else best
    return best.isoformat() if best else None


def quotes_on():
    """SCI_QUOTES=on|off, default off: whether passages numbered outside their judgment's own paragraph sequence are marked (sci_quotes.py)."""
    return (os.environ.get("SCI_QUOTES") or "off").strip().strip("\"'").strip().lower() in ("on", "1", "true", "yes")


def court_of(doc, names, src_courts):
    """The court of one document: the names table's court column, else the court the document's own source record names, else (a names table that has no court column, or none at all) the Supreme Court,
    which is what every document of the first index was. A document that a loaded table does not know has an unknown court."""
    nm = names.get(doc) if names else None
    if nm and nm.get("court"):
        return nm["court"]
    if doc in src_courts:
        return src_courts[doc]
    return COURT_UNKNOWN if (names and nm is None) else COURT_DEFAULT


def court_summary(docs, names, src_courts, today=None):
    """({court: judgments}, {court: latest decision date}, latest date overall). The dates come from the names table (ISO dates; a date after today is a typing error in the source and is ignored)."""
    today = (today or datetime.date.today()).isoformat()
    count, latest = collections.Counter(), {}
    for d in docs:
        court = court_of(d, names, src_courts)
        count[court] += 1
        dt = ((names or {}).get(d) or {}).get("date")
        if dt and dt <= today and dt > latest.get(court, ""):
            latest[court] = dt
    return dict(count), latest, (max(latest.values()) if latest else None)


def git_head(path):
    f = os.path.join(path, "INDEX_COMMIT")
    if os.path.exists(f):
        return open(f).read().strip() or None
    try:
        return subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


class SearchService:
    def __init__(self, metas, M, client, title, fts=None, info=None, rerank_model=RERANK_MODEL, daily_rerank_tokens=5_000_000, max_text=1500, clock=time.time, sleep=time.sleep, enabled=True):
        self.metas, self.M, self.client, self.title = metas, M, client, title
        self.fts = fts or build_fts(metas)
        self.info = info or {}
        self.rerank_model, self.daily_cap, self.max_text, self.clock, self.sleep, self.enabled = rerank_model, daily_rerank_tokens, max_text, clock, sleep, enabled
        self.header_docs = set()
        self.src_courts = {}
        self.names = {}
        self.quotes = {}                                 # "<doc>:<i>" -> sci_quotes record, when SCI_QUOTES=on
        self.authority = None                            # authority_search.AuthorityTable when SCI_AUTHORITY=on
        self.auth_params = None
        self._rows_by_doc = None
        self.lock = threading.Lock()
        self.day, self.rerank_today, self.embed_today, self.searches_today = None, 0, 0, 0
        self.started = clock()

    # ------------------------------------------------------------ loading
    @classmethod
    def load(cls, index_dir, side_dirs=(), client=None, **kw):
        t0 = time.time()
        wrong = si.check_model(index_dir, EMBED_MODEL)
        if wrong:
            raise ValueError(wrong)
        head = os.environ.get("SCI_INDEX_COMMIT") or git_head(index_dir)
        metas, M, _ = si._load_index(index_dir)
        metas = [_slim(m) for m in metas]
        n_main = len(metas)
        extra, sides = {}, []
        for d in side_dirs:
            metas, M, info, ex = _add_side_index(d, metas, M, head)
            extra.update(ex)
            sides.append(info)
        case_meta, src_title = _title_table([index_dir])
        src_courts = _src_courts([index_dir] + [d for d in side_dirs])
        header = {}
        for m in metas:
            if m["doc"] not in header and (m["section"] == "header" or str(m["pn"]).startswith("preamble")):
                header[m["doc"]] = re.sub(r"\s+", " ", m["text"])[:260]            # a document with no case record: its opening lines, as in the experiments
        title = _make_title(case_meta, src_title, extra, header)
        docs = sorted({m["doc"] for m in metas})
        as_of = _latest_date(title(d) for d in docs)
        fts = build_fts(metas)
        info = {"index_commit": head, "passages": len(metas), "passages_main": n_main, "documents": len(docs), "side_indexes": sides, "as_of": as_of, "embed_model": EMBED_MODEL,
                "documents_without_title": sum(1 for d in docs if not title(d)), "vector_dtype": str(M.dtype), "vector_dim": int(M.shape[1]), "load_seconds": round(time.time() - t0, 1)}
        svc = cls(metas, M, client or si.make_client(), title, fts, info, **kw)
        names_path = os.environ.get("SCI_NAMES_TABLE") or os.path.join(HERE, "names_table", "names_table.json.gz")
        if os.path.exists(names_path):
            with gzip.open(names_path, "rt", encoding="utf-8") as fh:
                nd = json.load(fh)
            svc.names = {r["doc"]: r for r in nd["rows"]}
            info["names_table"] = {"rows": len(svc.names), "named": nd.get("named"), "built": nd.get("built"), "index_commit": nd.get("index_commit")}
            if nd.get("index_commit") and head and nd["index_commit"] != head:
                raise ValueError(f"the names table was built for index {nd['index_commit'][:7]}, not {head[:7]}; rebuild it (names_table/build_names_table.py)")
        svc.src_courts = src_courts
        courts, as_of_by_court, newest = court_summary(docs, svc.names, src_courts)
        info["courts"], info["as_of_by_court"] = courts, as_of_by_court
        if newest:
            info["as_of"] = newest                     # the latest decision date among all the judgments (the title-based date above only reads dd-mm-yyyy titles, which the newer documents do not have)
        svc.header_docs = {d for d in docs if not ((case_meta.get(d) or {}).get("pet") or (case_meta.get(d) or {}).get("resp")) and d not in src_title and d not in extra}
        info["documents_named_from_opening_lines"] = len(svc.header_docs) - info["documents_without_title"]
        if quotes_on():                                # SCI_QUOTES=on (default off): passages numbered outside their judgment's own sequence get a "quote" field (sci_quotes.py)
            import sci_quotes
            svc.quotes, qstats = sci_quotes.build(metas)
            info["quotes"] = qstats
        import authority_search as AS
        if AS.enabled():                               # SCI_AUTHORITY=on (default off): the judgments the retrieved judgments name are fetched and favoured (authority_search.py)
            apath = os.environ.get("SCI_AUTHORITY_TABLE") or os.path.join(HERE, "authority_table", f"authority_{(head or 'unknown')[:7]}.json.gz")
            if not os.path.exists(apath):
                raise ValueError(f"SCI_AUTHORITY is on but the authority table {apath} is missing (python authority_graph.py build ...; SCI_AUTHORITY_TABLE names another file)")
            svc.authority = AS.AuthorityTable.load(apath, head)
            svc.auth_params = AS.params_from_env()
            info["authority"] = {"table": os.path.basename(apath), "judgments_named": len(svc.authority.cited_by), "judgments_that_name_others": len(svc.authority.cites), "params": svc.auth_params}
        return svc

    # ------------------------------------------------------------ the recipe
    def _embed(self, q):
        resp = _call(self.client.embed, [q], model=EMBED_MODEL, input_type="query", sleep=self.sleep)
        self.embed_today += getattr(resp, "total_tokens", 0) or 0
        qv = np.asarray(resp.embeddings[0], dtype=np.float32)
        return qv / (np.linalg.norm(qv) or 1.0)

    def retrieve(self, q, pool=60):
        qv = self._embed(q)
        sims = np.concatenate([self.M[i:i + 50000].astype(np.float32) @ qv for i in range(0, len(self.M), 50000)])
        sem = [int(i) for i in np.argsort(-sims)[:100]]
        toks = list(dict.fromkeys(t for t in re.findall(r"[A-Za-z0-9]{4,}", q.lower()) if t not in si.STOP))[:12]
        kw = [r[0] for r in self.fts.execute("select rowid from f where f match ? order by bm25(f) limit 50", (" OR ".join(f'"{t}"' for t in toks),))] if toks else []
        nums = si.section_numbers(q)
        sc = []
        for n in nums:
            sc += [r[0] for r in self.fts.execute("select rowid from f where f match ? order by bm25(f) limit 30", (f'"section {n}"',))]
        rr = {}
        for lst in (sem, kw, sc):
            for rank, rid in enumerate(lst):
                rr[rid] = rr.get(rid, 0.0) + 1.0 / (60 + rank)
        ranked = [r for r, _ in sorted(rr.items(), key=lambda x: -x[1])]
        return {"cand": ranked[:pool], "nums": nums, "sims": sims}

    def _rerank(self, q, cand):
        texts = [self.metas[r]["text"][:3500] for r in cand]
        resp = _call(self.client.rerank, q, texts, model=self.rerank_model, top_k=len(texts), sleep=self.sleep)
        self.rerank_today += getattr(resp, "total_tokens", 0) or 0
        return {cand[x.index]: x.relevance_score for x in resp.results}

    def _weight(self, rid, nums):
        return si.W.get(self.metas[rid]["section"], 1.0) * (1.10 if nums and si.has_section(self.metas[rid]["text"], nums) else 1.0)

    def ranked(self, q, k=10):
        """[(index row id, score)] best first: recipe B (with the authority step when SCI_AUTHORITY is on)."""
        return self.ranked_ex(q, k)[0]

    def rows_by_doc(self):
        if self._rows_by_doc is None:
            d = collections.defaultdict(list)
            for i, m in enumerate(self.metas):
                d[m["doc"]].append(i)
            self._rows_by_doc = dict(d)
        return self._rows_by_doc

    def ranked_ex(self, q, k=10):
        """([(row id, score)], annotation or None). Without the authority table: recipe B exactly. With it: the court's own pointers (authority_search.py)."""
        a = self.retrieve(q)
        if self.authority is None:
            rs = self._rerank(q, a["cand"])
            final = {r: s * self._weight(r, a["nums"]) for r, s in rs.items()}
            return sorted(final.items(), key=lambda x: -x[1])[:k], None
        import authority_search as AS
        prm, tab = self.auth_params, self.authority
        pl = AS.plan(tab, [self.metas[r]["doc"] for r in a["cand"][:prm["pool"]]], prm)
        named = {}                                                    # judgment -> how many retrieved judgments name it (only for the judgments the retrieved ones rely on)
        for c, n in pl["chosen"]:
            for d in tab.docs_of(c):
                named[d] = max(named.get(d, 0), n)
        extra = AS.extra_rows(tab, pl["chosen"], self.rows_by_doc(), a["sims"], a["cand"], prm)
        rs = self._rerank(q, list(a["cand"]) + extra)
        final = {r: s * self._weight(r, a["nums"]) * AS.boost(tab, self.metas[r]["doc"], named.get(self.metas[r]["doc"], 0), pl["pool_size"], prm) for r, s in rs.items()}
        top = sorted(final.items(), key=lambda x: -x[1])
        if prm.get("per_doc"):                                        # a judgment may take at most this many places in the list (the website keeps one passage of each judgment, so more only crowd the others out)
            kept, per = [], collections.Counter()
            for r, s_ in top:
                c = tab.cluster_of(self.metas[r]["doc"])
                if per[c] < prm["per_doc"]:
                    per[c] += 1
                    kept.append((r, s_))
            top = kept
        top = top[:k]
        return top, {"pool_size": pl["pool_size"], "counts": pl["counts"], "named": named, "raw": {r: rs[r] for r, _s in top}, "added": len(extra), "chosen": len(pl["chosen"]), "chosen_set": {c for c, _n in pl["chosen"]}}

    # ------------------------------------------------------------ the request
    def _new_day(self):
        today = datetime.datetime.fromtimestamp(self.clock(), datetime.timezone.utc).date()
        if today != self.day:
            self.day, self.rerank_today, self.embed_today, self.searches_today = today, 0, 0, 0

    def search(self, question, k=10):
        """The /search answer for one question. Raises Refused for anything the service will not run."""
        if not self.enabled:
            raise Refused(503, "the search tier is switched off (SCI_SEARCH_ENABLED=0)")
        q = re.sub(r"\s+", " ", question or "").strip() if isinstance(question, str) else ""
        if not q:
            raise Refused(400, "question is empty")
        if len(q) > MAX_QUESTION:
            raise Refused(400, f"question is longer than {MAX_QUESTION} characters")
        try:
            k = max(1, min(int(k), 20))
        except (TypeError, ValueError):
            raise Refused(400, "k must be a number from 1 to 20")
        with self.lock:
            self._new_day()
            if self.rerank_today >= self.daily_cap:
                raise Refused(429, "the daily re-rank allowance is spent; try again tomorrow")
            t0 = time.time()
            e0, r0 = self.embed_today, self.rerank_today
            top, auth = self.ranked_ex(q, k)
            usage = {"embed_model": EMBED_MODEL, "embed_tokens": self.embed_today - e0, "rerank_model": self.rerank_model, "rerank_tokens": self.rerank_today - r0}      # what this one search used (one search runs at a time, so the difference is exact)
            self.searches_today += 1
            results = []
            for rank, (rid, score) in enumerate(top, 1):
                m = self.metas[rid]
                text = re.sub(r"[ \t]+", " ", m["text"]).strip()
                nm = self.names.get(m["doc"])
                results.append({"rank": rank, "doc": m["doc"], "court": court_of(m["doc"], self.names, self.src_courts), "case_name": (nm or {}).get("name") or self.title(m["doc"]), "date": (nm or {}).get("date"), "citations": (nm or {}).get("citations") or {},
                                "link": (nm or {}).get("link"), "link_kind": (nm or {}).get("link_kind"), "name_to_review": bool(nm["review"]) if nm else None, "paragraph": m["pn"], "page": m.get("page"), "name_is_opening_lines": (m["doc"] in self.header_docs) if not nm else (nm["name"] is None), "passage_type": m["section"], "score": round(float(score), 4),
                                "text": text[: self.max_text] + ("..." if len(text) > self.max_text else ""), "passage_id": m["h"]})
                q = self.quotes.get(f"{m['doc']}:{m['i']}") if self.quotes else None
                if q:
                    results[-1]["quote"] = dict(q)       # the number in "paragraph" is NOT the judgment's own: the passage sits inside paragraph q["within"]
                if auth is not None:                     # SCI_AUTHORITY=on: why this judgment is here, as facts (counts of text matches; not a statement that it is good law)
                    import authority_search as AS
                    cl = self.authority.cluster_of(m["doc"])
                    results[-1]["authority"] = dict(AS.annotate(self.authority, m["doc"], auth["counts"].get(cl, 0), auth["pool_size"], cl in auth["chosen_set"]), raw_score=round(float(auth["raw"][rid]), 4))
            return {"ok": True, "tier": TIER, "recipe": "B" + ("+authority" if auth is not None else ""), "index_commit": self.info.get("index_commit"), "as_of": self.info.get("as_of"), "as_of_by_court": self.info.get("as_of_by_court") or {}, "disclaimer": DISCLAIMER,
                    "seconds": round(time.time() - t0, 2), "usage": usage, "results": results}

    def health(self):
        self._new_day()
        return {"ok": True, "enabled": self.enabled, "tier": TIER, "uptime_seconds": int(self.clock() - self.started), "index": self.info,
                "rerank_model": self.rerank_model, "today": {"date": str(self.day), "searches": self.searches_today, "rerank_tokens": self.rerank_today, "daily_cap": self.daily_cap,
                                                              "dollars_estimate": round(self.rerank_today * PRICE_RERANK / 1e6 + self.embed_today * PRICE_EMBED / 1e6, 4)},
                "memory_mb": rss_mb()}


def _add_side_index(supp_dir, metas, M, head):
    """Main index + one side index, with the checks of review_tools/pool_runner.load_supplement (same model, made for this main index, same width, no document twice)."""
    mp = os.path.join(supp_dir, "SUPPLEMENT.json")
    if not os.path.exists(mp):
        raise ValueError(f"{supp_dir} has no SUPPLEMENT.json")
    raw = open(mp, "rb").read()
    man = json.loads(raw)
    wrong = si.check_model(supp_dir, EMBED_MODEL)
    if wrong:
        raise ValueError(wrong)
    if head and man.get("main_index_commit") != head:
        raise ValueError(f"the side index was made for main index {str(man.get('main_index_commit'))[:7]}, not {head[:7]}")
    smetas, SM, _ = si._load_index(supp_dir)
    smetas = [_slim(m) for m in smetas]
    if len(smetas) != len(SM) or not len(SM):
        raise ValueError(f"the side index in {supp_dir} is empty or inconsistent")
    if SM.shape[1] != M.shape[1]:
        raise ValueError(f"vector width differs: main {M.shape[1]}, side index {SM.shape[1]}")
    clash = {m["doc"] for m in metas} & {m["doc"] for m in smetas}
    if clash:
        raise ValueError(f"the main index already has passages for {len(clash)} document(s) of the side index")
    extra = {d["doc"]: d["title"] for d in man.get("documents_detail", [])}
    lp = os.path.join(HERE, man["docs_list"]) if man.get("docs_list") else None
    if lp and os.path.exists(lp):
        for e in json.load(open(lp, encoding="utf-8"))["docs"]:
            extra[int(e["index_doc"])] = re.sub(r"\s+", " ", e["title"]) + (f" ({e['date']})" if e.get("date") else "")
    info = {"dir": os.path.basename(supp_dir.rstrip("/")), "manifest_sha256": hashlib.sha256(raw).hexdigest(), "documents": man.get("documents"), "passages": man.get("passages")}
    return metas + smetas, np.vstack([M, SM]), info, extra


# ================================================================ getting the index onto the volume
class FetchError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _get(url, token=None, accept=None, timeout=120):
    """GET with the token sent only to the URL it was given for; a redirect is returned, not followed (the signed download address needs no token)."""
    headers = {"User-Agent": "recourse-sci-search/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if accept:
        headers["Accept"] = accept
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        return opener.open(urllib.request.Request(url, headers=headers), timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
            return e
        raise FetchError(f"GET {url.split('?')[0]} answered HTTP {e.code}") from None


def has_index(index_dir):
    return bool(glob.glob(os.path.join(index_dir, "index", "*.meta.jsonl.gz"))) and bool(glob.glob(os.path.join(index_dir, "index", "*.vec.npy")))


DEFAULT_INDEX_REPO = "Tanbir-Ahm/recourse-sci-pool"
DEFAULT_INDEX_SHA = "3c80a26e42bea75e5858be6ed44a2649ec701355"      # the frozen index (claude/sci-index, ends 13 July 2026); change with SCI_INDEX_SHA when a new index is built


def fetch_index(index_dir, repo, branch, token, api="https://api.github.com", log=print, sha=None, codeload="https://codeload.github.com"):
    """Downloads the index folder into index_dir/index and records the commit in index_dir/INDEX_COMMIT. Two routes, standard library only:
    - with `sha` and no token: the public archive of exactly that commit (codeload, no API call, so no anonymous API limit -- Railway's shared address hit that limit on 2026-10-13);
    - otherwise: the API (needs `token` for a private repository or to avoid the anonymous limit), looking up the branch's commit first.
    The token goes to the API address only, never to the download address, never into a message. A half-finished download is removed. Needs about the size of the index (540 MB) free once."""
    import shutil
    import tarfile
    if sha and not token:
        log(f"downloading the archive of commit {sha[:10]} (public, no API call)")
        try:
            stream = urllib.request.urlopen(urllib.request.Request(f"{codeload}/{repo}/tar.gz/{sha}", headers={"User-Agent": "recourse-sci-search/1.0"}), timeout=600)
        except urllib.error.HTTPError as e:
            raise FetchError(f"the archive download answered HTTP {e.code}") from None
    else:
        if not token:
            log("no GITHUB_TOKEN: trying the API without one (works only while the repository is public and under GitHub's anonymous limit)")
        r = _get(f"{api}/repos/{repo}/commits/{urllib.parse.quote(branch, safe='')}", token, "application/vnd.github+json")
        sha = json.loads(r.read().decode("utf-8")).get("sha")
        if not sha:
            raise FetchError("could not read the commit of the index branch")
        log(f"index branch {branch} is at {sha[:10]}; downloading")
        r = _get(f"{api}/repos/{repo}/tarball/{sha}", token, "application/vnd.github+json")
        loc = r.headers.get("Location")
        stream = urllib.request.urlopen(urllib.request.Request(loc, headers={"User-Agent": "recourse-sci-search/1.0"}), timeout=600) if loc else r
    tmp = os.path.join(index_dir, ".incoming")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    n = 0
    try:
        with tarfile.open(fileobj=stream, mode="r|gz") as tf:
            for m in tf:
                parts = m.name.split("/", 2)
                if len(parts) < 3 or parts[1] != "index" or not m.isfile() or ".." in parts[2]:
                    continue
                dest = os.path.join(tmp, "index", *parts[2].split("/"))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as out:
                    shutil.copyfileobj(tf.extractfile(m), out)
                n += 1
        if not has_index(tmp):
            raise FetchError("the download held no index files")
        old = os.path.join(index_dir, "index")
        shutil.rmtree(old, ignore_errors=True)
        os.rename(os.path.join(tmp, "index"), old)
        open(os.path.join(index_dir, "INDEX_COMMIT"), "w").write(sha + "\n")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    log(f"{n} index files in {index_dir} (commit {sha[:10]})")
    return sha


def ensure_index(index_dir, log=print):
    """Called before serving: nothing to do when the index is already on the volume; otherwise fetch it (SCI_INDEX_REPO, SCI_INDEX_SHA or the built-in frozen commit, optional GITHUB_TOKEN, SCI_INDEX_BRANCH)."""
    if has_index(index_dir):
        return None
    repo = os.environ.get("SCI_INDEX_REPO") or DEFAULT_INDEX_REPO
    sha = os.environ.get("SCI_INDEX_SHA") or (DEFAULT_INDEX_SHA if repo == DEFAULT_INDEX_REPO else None)
    token = os.environ.get("GITHUB_TOKEN")
    if not sha and not token and repo != DEFAULT_INDEX_REPO:
        log("no SCI_INDEX_SHA and no GITHUB_TOKEN: using the API anonymously, which may be refused")
    os.makedirs(index_dir, exist_ok=True)
    return fetch_index(index_dir, repo, os.environ.get("SCI_INDEX_BRANCH", "claude/sci-index"), token, os.environ.get("SCI_GITHUB_API", "https://api.github.com"), log, sha=sha,
                       codeload=os.environ.get("SCI_GITHUB_CODELOAD", "https://codeload.github.com"))


def rss_mb():
    ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss          # kilobytes on Linux
    return round(ru / 1024, 0)


def current_rss_mb():
    try:
        for line in open("/proc/self/status"):
            if line.startswith("VmRSS:"):
                return round(int(line.split()[1]) / 1024, 0)
    except OSError:
        pass
    return rss_mb()


# ================================================================ HTTP
def make_handler(service, token):
    class Handler(BaseHTTPRequestHandler):
        server_version = "sci-search"

        def log_message(self, fmt, *args):          # never log the question
            sys.stderr.write("%s %s\n" % (self.command, self.path.split("?")[0]))

        def _send(self, status, body):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.split("?")[0] in ("/health", "/"):
                self._send(200, service.health())
            else:
                self._send(404, {"ok": False, "reason": "not found"})

        def do_POST(self):
            if self.path.split("?")[0] != "/search":
                return self._send(404, {"ok": False, "reason": "not found"})
            if token and self.headers.get("X-Search-Token") != token:
                return self._send(401, {"ok": False, "reason": "bad or missing X-Search-Token"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if n > 20000:
                    raise Refused(400, "request too large")
                body = json.loads(self.rfile.read(n) or b"{}")
                if not isinstance(body, dict):
                    raise Refused(400, "body must be a JSON object")
                self._send(200, service.search(body.get("question"), body.get("k", 10)))
            except Refused as r:
                self._send(r.status, {"ok": False, "reason": r.reason})
            except (ValueError, UnicodeDecodeError):
                self._send(400, {"ok": False, "reason": "body is not valid JSON"})
            except Exception as exc:  # noqa: BLE001
                sys.stderr.write(f"search failed: {type(exc).__name__}\n")
                self._send(502, {"ok": False, "reason": "the search failed; answer without it"})
    return Handler


class DualStackServer(ThreadingHTTPServer):
    """Listens on IPv6 and IPv4 together (host '::'). Railway's private network between services is IPv6 in older environments, so a server bound only to 0.0.0.0 cannot be reached there."""
    address_family = socket.AF_INET6

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            pass
        super().server_bind()


def make_server(service, host, port, token):
    """A dual-stack server for '::' (or ''), an ordinary one for a given IPv4 address; falls back to IPv4 when the machine has no IPv6."""
    handler = make_handler(service, token)
    if host in ("::", ""):
        try:
            return DualStackServer(("::", port), handler)
        except OSError:
            host = "0.0.0.0"
    return ThreadingHTTPServer((host, port), handler)


def startup_line(service, host, port):
    info = service.info
    q = info.get("quotes")
    return (f"sci-search listening on {host}:{port}; index {info.get('index_commit', '?')[:10] if info.get('index_commit') else '?'}, {info.get('passages'):,} passages; "
            f"{info.get('documents'):,} judgments ({', '.join(f'{k} {v:,}' for k, v in (info.get('courts') or {}).items())}); ends {info.get('as_of')}"
            + (f"; SCI_QUOTES on: {q['flagged']:,} passages marked in {q['documents_with_flagged']:,} judgments (numbered outside their judgment's own sequence)" if q else "")
            + (f"; SCI_AUTHORITY on: {info['authority']['judgments_named']:,} judgments named by others, {info['authority']['judgments_that_name_others']:,} that name others" if info.get("authority") else ""))


def serve(service, host, port, token):
    srv = make_server(service, host, port, token)
    print(startup_line(service, host, port), flush=True)
    srv.serve_forever()


# ================================================================ command line
def _paths():
    index_dir = os.environ.get("SCI_INDEX_DIR") or os.path.normpath(os.path.join(HERE, "..", "recourse-sci-index"))
    side = os.environ.get("SCI_SIDE_INDEXES")
    sides = [s.strip() for s in side.split(",") if s.strip()] if side is not None else [os.path.join(HERE, p) for p in DEFAULT_SIDE_INDEXES]
    return index_dir, sides


def report(index_dir, sides):
    """Sizes, load time and memory with no network and no key (a stand-in client is never called)."""
    t0 = time.time()
    disk = sum(os.path.getsize(f) for d in [index_dir] + sides for f in glob.glob(os.path.join(d, "index", "*")) if os.path.isfile(f))
    before = current_rss_mb()
    svc = SearchService.load(index_dir, sides, client=object())
    after = current_rss_mb()
    text_mb = sum(len(m["text"]) for m in svc.metas) / 1e6
    out = {"index": svc.info, "disk_mb_index_files": round(disk / 1e6, 1), "vectors_mb_in_memory": round(svc.M.nbytes / 1e6, 1), "passage_text_mb_chars": round(text_mb, 1),
           "rss_mb_before_load": before, "rss_mb_after_load": after, "rss_mb_peak": rss_mb(), "load_seconds_total": round(time.time() - t0, 1)}
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--host", default="::", help='"::" = IPv6 and IPv4 together (needed on Railway\'s private network); 127.0.0.1 for local tests')
    s.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    s.add_argument("--no-auth", action="store_true", help="only with --host 127.0.0.1: no X-Search-Token")
    r = sub.add_parser("report")
    r.add_argument("--json")
    sub.add_parser("fetch-index")
    k = sub.add_parser("ask")
    k.add_argument("question")
    a = ap.parse_args(argv)
    index_dir, sides = _paths()
    if a.cmd in ("fetch-index", "serve", "ask"):
        try:
            sha = ensure_index(index_dir)
        except FetchError as e:
            print(f"cannot get the index: {e}", file=sys.stderr)
            return 3
        if a.cmd == "fetch-index":
            print("index already present" if sha is None else f"index fetched ({sha[:10]})")
            return 0
    if a.cmd == "report":
        out = report(index_dir, sides)
        print(json.dumps(out, indent=1))
        if a.json:
            json.dump(out, open(a.json, "w"), indent=1)
        return 0
    svc = SearchService.load(index_dir, sides, rerank_model=os.environ.get("SCI_RERANK_MODEL", RERANK_MODEL),
                             daily_rerank_tokens=int(os.environ.get("SCI_DAILY_RERANK_TOKENS", "5000000")), max_text=int(os.environ.get("SCI_MAX_TEXT", "1500")),
                             enabled=os.environ.get("SCI_SEARCH_ENABLED", "1").strip().lower() not in ("0", "off", "false", "no"))
    if a.cmd == "ask":
        res = svc.search(a.question)
        for r_ in res["results"]:
            print(f'{r_["rank"]:2}. {r_["case_name"]}  para {r_["paragraph"]}  [{r_["passage_type"]}] {r_["score"]}')
        print(f'index {str(res["index_commit"])[:10]}, ends {res["as_of"]}, {res["seconds"]}s; spend today {json.dumps(svc.health()["today"])}')
        return 0
    token = os.environ.get("SCI_SEARCH_TOKEN")
    if not token and not (a.no_auth and a.host == "127.0.0.1"):
        print("refusing to start: set SCI_SEARCH_TOKEN (or --no-auth with --host 127.0.0.1 for local tests)", file=sys.stderr)
        return 2
    serve(svc, a.host, a.port, token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
