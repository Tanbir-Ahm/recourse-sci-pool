"""authority_search.py -- authority-aware ranking for the sci-search service (switch SCI_AUTHORITY=on; default off, nothing changes while it is off).

THE PROBLEM IT SOLVES. Recipe B ranks passages by how well their words fit the question. The landmark of a topic is rarely the best fit: later judgments restate its rule in one tidy sentence each, and there are
hundreds of them. On 2026-10-29 the question "Can a person be convicted on circumstantial evidence alone? What must the prosecution prove?" returned eight such restatements and not *Sharad Birdhichand Sarda*, which
446 other judgments of the same index name. On 104 test questions with a known landmark in the index, recipe B put the landmark among the first 8 judgments for 51 percent (review_results/2026-10-29_landmark_miss/).

WHAT IT DOES, in three steps, all from the table authority_graph.py builds (who names whom):
1. THE COURT'S OWN POINTERS. Take the judgments of the 60 candidates recipe B retrieved (the "pool"). Count, for every judgment, how many pool judgments NAME it. A judgment that a good share of the pool names
   (at least 3 and at least 8 percent of the pool) is the authority the retrieved judgments rely on. Its best passages for the question are added to the passages that are re-ranked.
2. A SMALL BOOST for what the pool names (up to +60 percent of the re-ranker's score, reaching its maximum when half of the pool names the judgment) and for a judgment many judgments of the whole index name (up to +10
   percent, reaching its maximum at 100 judgments). The boost multiplies the score; a passage that the re-ranker finds irrelevant stays irrelevant (0.5 x 1.7 = 0.85 is still below the 0.9 of a good fit).
3. THE FACTS ARE SHOWN. Each result says how many judgments of the collection name it and how many of the retrieved judgments do, so that the website can tell the reader and the answer model why this judgment is here.

NOTHING HERE SAYS A CASE IS GOOD LAW. A judgment can be named because it was criticised or overruled; the Overruled Register and the cards (website side) are what warn about that.
Parameters (environment, with clamps): SCI_AUTH_PRIOR 0.1, SCI_AUTH_CONSENSUS 0.6, SCI_AUTH_MIN_FRAC 0.08, SCI_AUTH_MAX 10 (judgments added at most), SCI_AUTH_PASSAGES 3 (passages of each), SCI_AUTH_MIN_COUNT 3,
SCI_AUTH_PER_DOC 1 (the most passages one judgment may take in the returned list: the website keeps one passage of each judgment, so a landmark's other passages would only push other judgments out; 0 = no limit).
The numbers were chosen on the 'dev' half of the test questions only; the 'frozen' half was run once afterwards.
"""
import collections
import gzip
import json
import math
import os

SCHEMA = "authority-table-2"
DEFAULTS = {"prior": 0.1, "consensus": 0.6, "min_frac": 0.08, "max_clusters": 10, "passages": 3, "min_count": 3, "per_doc": 1, "prior_cap": 100, "consensus_cap": 0.5, "pool": 60}


def _num(env, default, lo, hi, cast=float):
    raw = os.environ.get(env)
    if raw is None or not raw.strip():
        return default
    try:
        v = cast(raw.strip().strip("\"'"))
    except ValueError:
        return default
    return max(lo, min(hi, v))


def params_from_env():
    return {"prior": _num("SCI_AUTH_PRIOR", DEFAULTS["prior"], 0.0, 1.0), "consensus": _num("SCI_AUTH_CONSENSUS", DEFAULTS["consensus"], 0.0, 2.0), "min_frac": _num("SCI_AUTH_MIN_FRAC", DEFAULTS["min_frac"], 0.02, 0.9),
            "max_clusters": _num("SCI_AUTH_MAX", DEFAULTS["max_clusters"], 0, 30, int), "passages": _num("SCI_AUTH_PASSAGES", DEFAULTS["passages"], 1, 8, int), "min_count": _num("SCI_AUTH_MIN_COUNT", DEFAULTS["min_count"], 2, 50, int),
            "per_doc": _num("SCI_AUTH_PER_DOC", DEFAULTS["per_doc"], 0, 10, int),
            "prior_cap": DEFAULTS["prior_cap"], "consensus_cap": DEFAULTS["consensus_cap"], "pool": DEFAULTS["pool"]}


def enabled():
    return (os.environ.get("SCI_AUTHORITY") or "off").strip().strip("\"'").strip().lower() in ("on", "1", "true", "yes")


class AuthorityTable:
    """The table authority_graph.py builds: who names whom, in one index."""

    def __init__(self, table):
        if table.get("schema") != SCHEMA:
            raise ValueError(f"the authority table has schema {table.get('schema')!r}, not {SCHEMA!r}")
        self.info = {k: table.get(k) for k in ("index_commit", "built", "documents_with_citations", "citing_documents", "stats")}
        self.cited_by = {int(d): n for d, n in table["cited_by"].items()}
        self.cluster = {int(d): int(c) for d, c in table.get("cluster", {}).items()}
        self.cites = {int(d): tuple(int(c) for c in v) for d, v in table["cites"].items()}
        self.members = collections.defaultdict(list)
        for d, c in self.cluster.items():
            self.members[c].append(d)
        for c in list(self.members):
            self.members[c].append(c)

    @classmethod
    def load(cls, path, index_commit=None):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            table = json.load(fh)
        t = cls(table)
        if index_commit and t.info.get("index_commit") and t.info["index_commit"] != index_commit:
            raise ValueError(f"the authority table was built for index {str(t.info['index_commit'])[:7]}, not {str(index_commit)[:7]}; rebuild it (authority_graph.py build)")
        return t

    def cluster_of(self, doc):
        return self.cluster.get(doc, doc)

    def docs_of(self, cluster):
        return self.members.get(cluster) or [cluster]

    def named_by(self, doc):
        return self.cited_by.get(doc, 0)

    def prior_factor(self, doc, cap=DEFAULTS["prior_cap"]):
        n = self.named_by(doc)
        return min(1.0, math.log1p(n) / math.log1p(cap)) if n else 0.0


def plan(table, pool_docs, prm):
    """The court's own pointers among a pool of judgments: {'pool_size', 'threshold', 'chosen': [(cluster, number of pool judgments naming it)], 'counts': {cluster: number}}, most named first."""
    pool = list(dict.fromkeys(pool_docs))
    cons = collections.Counter()
    for d in pool:
        for c in table.cites.get(d, ()):
            cons[c] += 1
    thr = max(prm["min_count"], math.ceil(prm["min_frac"] * len(pool)))
    chosen = [(c, n) for c, n in cons.most_common(prm["max_clusters"] * 3) if n >= thr][:prm["max_clusters"]]
    return {"pool_size": len(pool), "threshold": thr, "chosen": chosen, "counts": cons}


def boost(table, doc, named_by_pool, pool_size, prm):
    """The factor a passage's score is multiplied by (>= 1)."""
    pf = table.prior_factor(doc, prm["prior_cap"])
    cf = min(1.0, (named_by_pool / pool_size) / prm["consensus_cap"]) if pool_size and named_by_pool else 0.0
    return 1.0 + prm["prior"] * pf + prm["consensus"] * cf


def extra_rows(table, chosen, doc_rows, sims, have, prm):
    """The best passages (by meaning) of each chosen judgment's cluster that are not yet candidates: row numbers."""
    out, seen = [], set(have)
    for c, _n in chosen:
        rows = [i for d in table.docs_of(c) for i in doc_rows.get(d, ())]
        for i in sorted(rows, key=lambda i: -float(sims[i]))[:prm["passages"]]:
            if i not in seen:
                out.append(i)
                seen.add(i)
    return out


def annotate(table, doc, named_by_pool, pool_size, pointer=False):
    """The facts shown with a result. `pointer`: this is one of the court's own pointers, i.e. enough of the retrieved judgments name it for it to have been fetched and favoured."""
    return {"named_by_collection": table.named_by(doc), "named_by_retrieved": int(named_by_pool or 0), "retrieved": pool_size, "pointer": bool(pointer)}
