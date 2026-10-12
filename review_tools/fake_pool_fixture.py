"""An invented index and a fake service for tests (copied from test_pool_runner.py; no network, no spend)."""
import collections
import os
import re
import sys
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pool_runner as P

DIM = 32


def vec(text):
    v = np.zeros(DIM, dtype=np.float32)
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        v[hash(w) % DIM] += 1.0
    return v / (np.linalg.norm(v) or 1.0)


class FakeClient:
    """embed: hashed bag of words; rerank: share of the question's words found in the passage, with fixed overrides. Counts calls and bills tokens as the real service does."""

    def __init__(self, overrides=None):
        self.overrides, self.embed_calls, self.rerank_calls = overrides or {}, 0, 0

    def embed(self, texts, model, input_type):
        self.embed_calls += 1
        return SimpleNamespace(embeddings=[vec(texts[0]).tolist()], total_tokens=len(texts[0]) // 4)

    def rerank(self, query, docs, model, top_k):
        self.rerank_calls += 1
        qw = set(re.findall(r"[a-z0-9]+", query.lower()))
        res = []
        for i, d in enumerate(docs):
            score = len(qw & set(re.findall(r"[a-z0-9]+", d.lower()))) / (len(qw) or 1)
            for frag, val in self.overrides.items():
                if frag in d:
                    score = val
            res.append(SimpleNamespace(index=i, relevance_score=score))
        res.sort(key=lambda r: -r.relevance_score)
        return SimpleNamespace(results=res[:top_k], total_tokens=sum(len(d) // 4 + len(query) // 4 for d in docs))


TOPICS = ["bail anticipatory arrest", "cheque dishonour compounding", "murder sentence death", "default bail chargesheet", "quash fir settlement", "ndps statement confession"]
metas = []
for d in range(12):
    for i in range(10):
        topic = TOPICS[(d + i) % len(TOPICS)]
        text = f"{i + 1}. In case {d} paragraph {i} the court considered {topic} and section {400 + (d % 4)} as it arose on the record."
        metas.append({"doc": 100 + d, "i": i, "pn": str(i + 1), "page": i // 3 + 1, "section": ["reasoning", "facts", "header", "argument"][i % 4], "h": f"h{d}-{i}", "text": text})
# an identical passage in two judgments (a copy), strongly relevant to the first topic
metas.append({"doc": 200, "i": 0, "pn": "1", "page": 1, "section": "reasoning", "h": "hdup", "text": "1. Anticipatory bail and arrest: the court held that bail anticipatory arrest must be decided on the facts. COPY"})
metas.append({"doc": 201, "i": 0, "pn": "1", "page": 1, "section": "reasoning", "h": "hdup", "text": "1. Anticipatory bail and arrest: the court held that bail anticipatory arrest must be decided on the facts. COPY"})
M = np.stack([vec(m["text"]) for m in metas]).astype(np.float16)
hdocs = collections.defaultdict(set)
for m in metas:
    hdocs[m["h"]].add(m["doc"])
fts = P.build_fts(metas)
title = lambda doc: f"Case {doc} v. State"
Q = "Can anticipatory bail and arrest be decided on the facts under section 400?"


def engine(client=None, cap=10**9, site=None):
    return P.Engine(metas, M, client or FakeClient(), P.Spend(cap), fts, site, sleep=lambda s: None)
