"""Pools the search versions over the index for the 30 questions (the tuning half by default) and writes what the reviewers and the scorer need. Read-only on the index.

    python review_tools/pool_runner.py --half dev --max-rerank-tokens 15000000 --out review_results/DATE_real30_pool_dev [--no-site] [--only R01,R02] [--dry-run]
    python review_tools/pool_runner.py --half sealed --final --label "end of step 6" ...        # the sealed half, once (real_questions.select hands it out and logs it)

Versions (the same as the first pack, see review_tools/experiments/VERSIONS.md): A today, B no repeats, E no multiplier, S site shown (the Recourse site's own search code run over this index,
no hand pins, no topic routing), and for the questions that have a blind rewrite in `real30_rewrites_v1.json`: C rewrite and F merged. All but S share one retrieval (100 by meaning, 50 by keyword,
up to 30 by "section N", merged by reciprocal rank into 60 candidates) and one re-ranker (Voyage rerank-2).
Guards: the index head must be the one recorded in the question file (`index_snapshot`); the re-rank tokens billed stay under --max-rerank-tokens (the run stops before the call that would
cross it, saving what it has); a sealed question is run only with --final and a label. The private key is never read here.
--safety-net adds two arms that cost no extra call: "N merged order (no re-ranker)" (the merged order before the re-ranker, top 10) and "M safety net" (the merged top 5 that version A's ten do not show),
so that nothing the three searches agreed on is lost to the re-ranker: the list to show is A's ten followed by the net (at most 15). Off by default; the arms are labelled in the run record.
--supplement DIR (repeatable) searches "main index + side index(es)" (see build_supplement.py): a side index holds judgments the main index left out; the main index is not touched and the run says so.
Writes OUT/questions.jsonl as it goes (a re-run skips the questions already there), then OUT/pool.json (per question: rows to be marked, shuffled with a fixed seed and numbered, and the ordered top
results of every version for the scorer) and OUT/spend.json. PRIVATE: the pool names which version found what.
"""
import argparse
import collections
import datetime
import glob
import gzip
import hashlib
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import real_questions as RQ                # noqa: E402
import sci_index as si                     # noqa: E402

DATA = os.path.join(ROOT, "review_data", "ruler")
DEFAULT_REAL = os.path.join(DATA, "real30_v1.json")
DEFAULT_REWRITES = os.path.join(DATA, "real30_rewrites_v1.json")
DEFAULT_INDEX = os.path.normpath(os.path.join(ROOT, "..", "recourse-sci-index"))
DEFAULT_RECOURSE = "/home/user/tanbir-ahm/recourse"
RERANK_MODEL, EMBED_MODEL = "rerank-2", si.MODEL
PRICE_RERANK, PRICE_EMBED = 0.05, 0.12          # dollars per million tokens (rerank-2 from third-party price lists; voyage-law-2); checked against the first billed call
VERSIONS = ("A today", "B no repeats", "E no multiplier", "C rewrite", "F merged", "S site shown")
SAFETY_VERSIONS = ("N merged order (no re-ranker)", "M safety net")
SAFETY_NET_DEPTH = 5                  # the merged (pre-re-ranker) top 5 must come up somewhere in the list shown
SHUFFLE_SEED = "real30-pool-v1"
RETRYABLE = {"RateLimitError", "ServiceUnavailableError", "APIConnectionError", "Timeout", "TryAgain", "APIError"}


def safety_net(fused, shown, depth=SAFETY_NET_DEPTH, ident=lambda x: x):
    """The safety net: the passages of the merged top `depth` (the order the three searches agreed on, before the re-ranker) that the list `shown` does not hold, in merged order. `ident` maps an item to the
    identity that decides 'already shown' (the passage hash, so that a copy of the same text counts as shown). Nothing is added when the re-ranker's list already holds them all."""
    seen = {ident(x) for x in shown}
    out = []
    for x in fused[:depth]:
        i = ident(x)
        if i in seen:
            continue
        seen.add(i)
        out.append(x)
    return out


class SpendCapReached(RuntimeError):
    pass


class Spend:
    """Re-rank and embedding tokens billed (from the service's own counts) against a cap on re-ranking."""

    def __init__(self, cap_rerank_tokens):
        self.cap = cap_rerank_tokens
        self.rerank = self.embed = self.rerank_calls = self.embed_calls = 0

    def room_for(self, estimate):
        if self.rerank + estimate > self.cap:
            raise SpendCapReached(f"the next re-rank call (about {estimate:,} tokens) would take the total from {self.rerank:,} past the cap of {self.cap:,}")

    def dollars(self):
        return self.rerank * PRICE_RERANK / 1e6 + self.embed * PRICE_EMBED / 1e6

    def as_dict(self):
        return {"rerank_tokens": self.rerank, "rerank_calls": self.rerank_calls, "embed_tokens": self.embed, "embed_calls": self.embed_calls, "cap_rerank_tokens": self.cap,
                "dollars_estimate": round(self.dollars(), 4), "prices_per_million": {"rerank-2": PRICE_RERANK, "voyage-law-2": PRICE_EMBED}}


def call(fn, *args, tries=4, pause=2.0, sleep=time.sleep, **kw):
    """One service call with a few patient retries for rate limits and brief outages; anything else is raised."""
    for i in range(tries):
        try:
            return fn(*args, **kw)
        except Exception as e:                      # noqa: BLE001
            if type(e).__name__ in RETRYABLE and i < tries - 1:
                sleep(pause * 2 ** i)
                continue
            raise


def build_fts(metas):
    fts = sqlite3.connect(":memory:")
    fts.execute("create virtual table f using fts5(text, tokenize='porter unicode61')")
    fts.executemany("insert into f(rowid, text) values(?,?)", ((i, m["text"]) for i, m in enumerate(metas)))
    return fts


class Engine:
    """The pipeline of experiments/pool.py, parameterised so that it can be tested with a fake service."""

    def __init__(self, metas, M, client, spend, fts, site=None, sleep=time.sleep, safety=False):
        self.metas, self.M, self.client, self.spend, self.fts, self.site, self.sleep, self.safety = metas, M, client, spend, fts, site, sleep, safety

    def embed(self, q):
        resp = call(self.client.embed, [q], model=EMBED_MODEL, input_type="query", sleep=self.sleep)
        self.spend.embed += getattr(resp, "total_tokens", 0) or 0
        self.spend.embed_calls += 1
        qv = np.asarray(resp.embeddings[0], dtype=np.float32)
        return qv / (np.linalg.norm(qv) or 1.0)

    def retrieve(self, q, dedupe=False, pool=60):
        qv = self.embed(q)
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
        if dedupe:
            seen, cand = set(), []
            for r in ranked:
                if self.metas[r]["h"] in seen:
                    continue
                seen.add(self.metas[r]["h"])
                cand.append(r)
                if len(cand) == pool:
                    break
        else:
            cand = ranked[:pool]
        return {"q": q, "cand": cand, "nums": nums}

    def rerank(self, q, cand):
        texts = [self.metas[r]["text"][:3500] for r in cand]
        self.spend.room_for(int(len(texts) * (len(q) / 3.5) + sum(len(t) for t in texts) / 3.5 * 1.1))
        resp = call(self.client.rerank, q, texts, model=RERANK_MODEL, top_k=len(texts), sleep=self.sleep)
        self.spend.rerank += getattr(resp, "total_tokens", 0) or 0
        self.spend.rerank_calls += 1
        return {cand[x.index]: x.relevance_score for x in resp.results}

    def weight(self, rid, nums):
        return si.W.get(self.metas[rid]["section"], 1.0) * (1.10 if nums and si.has_section(self.metas[rid]["text"], nums) else 1.0)

    @staticmethod
    def order_by(scores):
        return [r for r, _ in sorted(scores.items(), key=lambda x: -x[1])]

    def lists_for(self, q, rewrite=None):
        """{version: [index row ids, best first]} for one question (top 10 each; S whole)."""
        out = {}
        a = self.retrieve(q)
        rs_a = self.rerank(q, a["cand"])
        out["A today"] = self.order_by({r: s * self.weight(r, a["nums"]) for r, s in rs_a.items()})[:10]
        out["E no multiplier"] = self.order_by(rs_a)[:10]
        if self.safety:                                      # no extra call: the merged order is what the re-ranker was given
            out["N merged order (no re-ranker)"] = list(a["cand"][:10])
            out["M safety net"] = safety_net(a["cand"], out["A today"], SAFETY_NET_DEPTH, lambda r: self.metas[r]["h"])
        b = self.retrieve(q, dedupe=True)
        rs_b = self.rerank(q, b["cand"])
        out["B no repeats"] = self.order_by({r: s * self.weight(r, b["nums"]) for r, s in rs_b.items()})[:10]
        if rewrite:
            c = self.retrieve(rewrite)
            rs_c = self.rerank(rewrite, c["cand"])
            out["C rewrite"] = self.order_by({r: s * self.weight(r, c["nums"]) for r, s in rs_c.items()})[:10]
            union = list(dict.fromkeys(a["cand"] + c["cand"]))
            ro, rw = self.rerank(q, union), self.rerank(rewrite, union)
            out["F merged"] = self.order_by({r: max(ro[r] * self.weight(r, a["nums"]), rw[r] * self.weight(r, c["nums"])) for r in union})[:10]
        if self.site:
            out["S site shown"] = list(self.site(q))
        return out


def make_site(metas, M, recourse_dir):
    """The Recourse site's own judgment search (semantic_retrieval, unmodified) over this index: statute lookups off, no pins, no routing. Returns q -> [index row ids]."""
    sys.path.insert(0, recourse_dir)
    import semantic_retrieval as sr
    where = {(m["doc"], m["i"]): k for k, m in enumerate(metas)}
    records = [{"chunk_id": f"{m['doc']}:{m['i']}", "text": m["text"], "type": "judgment", "case_name": str(m["doc"]), "paragraph_number": m["pn"], "section_number": None, "doc": m["doc"], "h": m["h"],
                "tag": m["section"]} for m in metas]
    sr._corpus_cache = {"records": records, "matrix": M.astype(np.float32), "model": EMBED_MODEL}
    sr._named_section_exact_match = lambda q: None
    sr._section_tables = lambda: {}
    sr._build_lexical_index()

    def site(q):
        shown = sr.find_relevant_sections(q).get("judgment_matches", [])
        return [where[(r["doc"], int(r["chunk_id"].split(":")[1]))] for r in shown]
    return site


def titles(index_dir, metas=(), extra=None):
    """doc -> the title shown with a passage: 'Petitioner v. Respondent (date)' from the index's case record (crawl judgments), else the title and date the bucket judgment arrived with, else a title
    given in `extra` ({doc: title}, e.g. a side index's list), else the opening header text (as the first pack did). None when none of these exists. `index_dir` may be a list of index folders."""
    case_meta, src_title, header = {}, {}, {}
    dirs = [index_dir] if isinstance(index_dir, str) else list(index_dir)
    for d in dirs:
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
    for m in metas:
        if m["doc"] not in header and (m["section"] == "header" or str(m["pn"]).startswith("preamble")):
            header[m["doc"]] = re.sub(r"\s+", " ", m["text"])[:260]

    def title(doc):
        c = case_meta.get(doc)
        if c and (c.get("pet") or c.get("resp")):
            return (f"{c.get('pet', '?')} v. {c.get('resp', '?')}" + (f" ({c['date']})" if c.get("date") else ""))[:200]
        if doc in src_title:
            name, date = src_title[doc]
            return (re.sub(r"\s+", " ", name) + (f" ({date})" if date else ""))[:200]
        if extra and doc in extra:
            return extra[doc][:200]
        return header.get(doc)
    return title


def retitle(pool_path, index_dir, extra=None):
    """Fills the titles a run left empty (a first run took titles from crawl records and header text only), in pool.json and nothing else. Returns (rows filled, rows still without a title)."""
    with open(pool_path, encoding="utf-8") as fh:
        doc = json.load(fh)
    title = titles(index_dir, extra=extra)
    filled = left = 0
    for q in doc["questions"]:
        for r in q["rows"]:
            if not r["title"]:
                t = title(r["doc"])
                if t:
                    r["title"], filled = t, filled + 1
                else:
                    left += 1
    doc["run"]["titles_filled_afterwards"] = {"rows": filled, "still_without": left, "from": "the index's document records (src.title, src.date)"}
    with open(pool_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return filled, left


def supplement_titles(supp_dir):
    """{doc: title (date)} for the documents of a side index, from its manifest and from the list it was built from (which carries the dates)."""
    with open(os.path.join(supp_dir, "SUPPLEMENT.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    extra = {d["doc"]: d["title"] for d in man.get("documents_detail", [])}
    lp = os.path.join(ROOT, man["docs_list"]) if man.get("docs_list") else None
    if lp and os.path.exists(lp):
        with open(lp, encoding="utf-8") as fh:
            for e in json.load(fh)["docs"]:
                extra[int(e["index_doc"])] = re.sub(r"\s+", " ", e["title"]) + (f" ({e['date']})" if e.get("date") else "")
    return extra


def load_supplement(supp_dir, metas, M, head, allow_other=False):
    """Main index + side index as one searchable set. Refuses a side index made with another model, for another main-index commit (unless allowed), with another vector width, or one that holds
    a document the main index already has passages for. Returns (metas, M, info for the run record, {doc: title}). The main index's own arrays are not modified."""
    mp = os.path.join(supp_dir, "SUPPLEMENT.json")
    if not os.path.exists(mp):
        raise ValueError(f"{supp_dir} has no SUPPLEMENT.json")
    with open(mp, "rb") as fh:
        raw = fh.read()
    man = json.loads(raw)
    refusal = si.check_model(supp_dir, EMBED_MODEL)
    if refusal:
        raise ValueError(refusal)
    if man.get("main_index_commit") != head and not allow_other:
        raise ValueError(f"the side index was made for main index {str(man.get('main_index_commit'))[:7]}, not {head[:7]}")
    smetas, SM, _ = si._load_index(supp_dir)
    if len(smetas) != len(SM) or not len(SM):
        raise ValueError(f"the side index in {supp_dir} is empty or inconsistent")
    if SM.shape[1] != M.shape[1]:
        raise ValueError(f"vector width differs: main {M.shape[1]}, side index {SM.shape[1]}")
    clash = {m["doc"] for m in metas} & {m["doc"] for m in smetas}
    if clash:
        raise ValueError(f"the main index already has passages for {len(clash)} document(s) of the side index, e.g. {sorted(clash)[:3]}")
    extra = supplement_titles(supp_dir)
    info = {"dir": os.path.relpath(supp_dir, ROOT) if os.path.abspath(supp_dir).startswith(ROOT) else supp_dir, "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "documents": man.get("documents"), "passages": man.get("passages"), "built": man.get("built"), "made_for_main_index": man.get("main_index_commit")}
    return metas + smetas, np.vstack([M, SM]), info, extra


def build_question(q, lists, metas, hdocs, title, rewrite=None, top_k=5):
    """One question's record: the rows to be marked (the top k of every version, all of S, collapsed by identical text, shuffled with a fixed seed, numbered) and each version's ordered results."""
    groups = collections.OrderedDict()
    for version, lst in lists.items():
        whole = version.startswith(("S", "M "))                # S site shown and M safety net are sets, pooled whole
        for rank, rid in enumerate(lst, 1):
            if not whole and rank > top_k:
                continue
            g = groups.setdefault(metas[rid]["h"], {"primary": rid, "variants": {}})
            g["variants"][version] = min(rank, g["variants"].get(version, 99))
    for version, lst in lists.items():                      # ranks beyond the top k of a passage that is in the pool anyway
        for rank, rid in enumerate(lst, 1):
            g = groups.get(metas[rid]["h"])
            if g is not None:
                g["variants"][version] = min(rank, g["variants"].get(version, 99))
    rows = []
    for h, g in groups.items():
        m = metas[g["primary"]]
        rows.append({"h": h, "doc": m["doc"], "pn": m["pn"], "page": m["page"], "title": title(m["doc"]), "text": m["text"], "also": sorted(hdocs[h] - {m["doc"]}), "variants": g["variants"]})
    random.Random(f"{SHUFFLE_SEED}|{q['id']}").shuffle(rows)
    for i, row in enumerate(rows, 1):
        row["n"] = i
    return {"qid": q["id"], "domain": q["domain"], "kind": q["kind"], "question": q["text"], "rewrite": rewrite, "half": q["half"], "rows": rows,
            "lists": {v: [{"doc": metas[r]["doc"], "h": metas[r]["h"], "also": sorted(hdocs[metas[r]["h"]] - {metas[r]["doc"]})} for r in lst] for v, lst in lists.items()}}


def ruler_questions(ruler_path, half="dev", final=False, label=""):
    """The ruler's questions of a half as runner questions (the ruler's own guard decides whether the frozen half may be handed out). Everyday = the ruler's 'lay'."""
    import ruler as RU
    R = RU.load(ruler_path)
    topics = {t["id"]: t for t in R["topics"]}
    return [{"id": q["id"], "domain": topics[q["topic"]]["area"], "kind": "everyday" if q["kind"] == "lay" else q["kind"], "text": q["text"], "half": q["half"], "topic": q["topic"]}
            for q in RU.select(R, "frozen" if half == "sealed" else "dev", final=final, label=label)]


def index_head(index_dir):
    return subprocess.run(["git", "-C", index_dir, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()


def read_done(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return {r["qid"]: r for r in map(json.loads, (l for l in fh if l.strip()))}


def run(real, questions, rewrites, engine, hdocs, title, out_dir, log=print):
    """Runs the questions one by one, saving each as it finishes. Returns the compiled pool and whether the cap stopped it."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "questions.jsonl")
    done = read_done(path)
    stopped = None
    for q in questions:
        if q["id"] in done:
            log(f"{q['id']} already done")
            continue
        before = (engine.spend.rerank, engine.spend.embed)
        rw = (rewrites or {}).get(q["id"])
        try:
            lists = engine.lists_for(q["text"], rw)
        except SpendCapReached as e:
            stopped = f"stopped before {q['id']}: {e}"
            log(stopped)
            break
        rec = build_question(q, lists, engine.metas, hdocs, title, rw)
        rec["spend"] = {"rerank_tokens": engine.spend.rerank - before[0], "embed_tokens": engine.spend.embed - before[1]}
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        done[q["id"]] = rec
        log(f"{q['id']} {q['kind']:9} versions {len(lists)} rows {len(rec['rows']):>2} rerank tokens {rec['spend']['rerank_tokens']:>8,} (total {engine.spend.rerank:,}, about ${engine.spend.dollars():.3f})")
    ordered = [done[q["id"]] for q in questions if q["id"] in done]
    return ordered, stopped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--real", default=DEFAULT_REAL)
    ap.add_argument("--source", choices=["real30", "ruler"], default="real30", help="the 30 real questions, or the ruler's 32 (the ruler's own guard keeps its frozen half back; no rewrites are used for it)")
    ap.add_argument("--ruler", default=os.path.join(DATA, "ruler_v2.json"))
    ap.add_argument("--half", choices=["dev", "sealed"], default="dev")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--label", default="")
    ap.add_argument("--rewrites", default=DEFAULT_REWRITES)
    ap.add_argument("--index-dir", default=DEFAULT_INDEX)
    ap.add_argument("--recourse-dir", default=DEFAULT_RECOURSE)
    ap.add_argument("--out")
    ap.add_argument("--max-rerank-tokens", type=int, help="stop before the call that would take the re-rank tokens billed past this (required for a run)")
    ap.add_argument("--retitle", metavar="POOL_JSON", help="only fill the titles a finished run left empty, from the index's document records; searches nothing, spends nothing")
    ap.add_argument("--supplement", action="append", default=[], help="a side index (build_supplement.py): search main + side index; may be given more than once; the run is labelled with each")
    ap.add_argument("--no-site", action="store_true")
    ap.add_argument("--safety-net", action="store_true", help="also record the merged order before the re-ranker (N) and the safety net (M); no extra API call")
    ap.add_argument("--only", default="", help="comma-separated question ids")
    ap.add_argument("--allow-other-index", action="store_true", help="run on an index head other than the recorded one (the run says so)")
    ap.add_argument("--dry-run", action="store_true", help="show the plan and call nothing")
    a = ap.parse_args(argv)
    if a.retitle:
        extra = {}
        for d in a.supplement:
            extra.update(supplement_titles(d))
        filled, left = retitle(a.retitle, [a.index_dir] + a.supplement, extra or None)
        print(f"titles filled: {filled}; still without a title: {left}")
        return 0
    if not a.out or a.max_rerank_tokens is None:
        ap.error("--out and --max-rerank-tokens are required for a run")
    real = RQ.load(a.real)
    bad = RQ.check(real, os.path.join(DATA, "ruler_v2.json"))
    if bad:
        print("the question file fails its check:", bad)
        return 1
    head, want = index_head(a.index_dir), real["index_snapshot"]["commit"]
    if head != want and not a.allow_other_index:
        print(f"refused: the index head is {head[:7]}, the experiment is recorded on {want[:7]}")
        return 1
    try:
        if a.source == "ruler":
            qs = ruler_questions(a.ruler, a.half, final=a.final, label=a.label)
        else:
            qs = RQ.select(real, a.half, final=a.final, label=a.label)
    except Exception as e:                       # noqa: BLE001  (RQ.SealedError, ruler.FrozenHalfError)
        if type(e).__name__ not in ("SealedError", "FrozenHalfError"):
            raise
        print("refused:", e)
        return 3
    if a.only:
        keep = set(a.only.split(","))
        qs = [q for q in qs if q["id"] in keep]
    rewrites = {}
    if a.source == "real30" and os.path.exists(a.rewrites):
        with open(a.rewrites, encoding="utf-8") as fh:
            rewrites = json.load(fh)["rewrites"]
    if a.dry_run:
        n_rw = sum(1 for q in qs if q["id"] in rewrites)
        print(f"{len(qs)} questions ({a.half}); {n_rw} with a blind rewrite (versions C and F); site arm {'off' if a.no_site else 'on'}; cap {a.max_rerank_tokens:,} re-rank tokens"
              + "".join(f"; side index {d}" for d in a.supplement))
        print("planned re-rank calls: %d (A/E: 1, B: 1, C: 1, F: 2 per rewritten question)" % (len(qs) * 2 + n_rw * 3))
        return 0
    t0 = time.time()
    metas, M, _ = si._load_index(a.index_dir)
    print(f"index loaded: {len(metas):,} passages in {time.time() - t0:.0f}s", flush=True)
    supp_infos, extra_titles = [], {}
    for d in a.supplement:
        try:
            metas, M, info, extra = load_supplement(d, metas, M, head, a.allow_other_index)
        except ValueError as e:
            print("refused:", e)
            return 1
        supp_infos.append(info)
        extra_titles.update(extra)
        print(f"side index added: {info['documents']} judgments, {info['passages']:,} passages (made {info['built']})", flush=True)
    hdocs = collections.defaultdict(set)
    for m in metas:
        hdocs[m["h"]].add(m["doc"])
    fts = build_fts(metas)
    site = None if a.no_site else make_site(metas, M, a.recourse_dir)
    spend = Spend(a.max_rerank_tokens)
    engine = Engine(metas, M, si.make_client(), spend, fts, site, safety=a.safety_net)
    ordered, stopped = run(real, qs, rewrites, engine, hdocs, titles([a.index_dir] + a.supplement, metas, extra_titles or None), a.out)
    run_info = {"when": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "half": a.half, "index_commit": head, "index_matches_record": head == want, "versions": list(VERSIONS) + (list(SAFETY_VERSIONS) if a.safety_net else []),
                "source": a.source, "site_arm": not a.no_site, "rewrites_file": os.path.relpath(a.rewrites, ROOT) if rewrites else None, "stopped": stopped, "spend": spend.as_dict(),
                "question_file_split_sha256": real["freeze"]["split_sha256"], "models": {"embed": EMBED_MODEL, "rerank": RERANK_MODEL}, "side_index": supp_infos[0] if supp_infos else None, "side_indexes": supp_infos}
    with open(os.path.join(a.out, "pool.json"), "w", encoding="utf-8") as fh:
        json.dump({"run": run_info, "questions": ordered}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    with open(os.path.join(a.out, "spend.json"), "w", encoding="utf-8") as fh:
        json.dump({"run": run_info, "per_question": {q["qid"]: q["spend"] for q in ordered}}, fh, indent=1)
        fh.write("\n")
    print(f"done: {len(ordered)} of {len(qs)} questions; re-rank tokens billed {spend.rerank:,}; about ${spend.dollars():.3f}" + (f"; {stopped}" if stopped else ""))
    return 0 if not stopped else 4


if __name__ == "__main__":
    sys.exit(main())
