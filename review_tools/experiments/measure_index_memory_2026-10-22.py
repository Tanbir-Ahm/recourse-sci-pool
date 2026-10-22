"""How much memory does the passage index need, and how long does the local part of a search take? Reads the index files only: no network, no spend, no real search (the query embedding is a fake random vector;
the re-ranker is never called). Sealed questions are never touched: the test questions below are ten plain ones written for this measurement.

    python review_tools/experiments/measure_index_memory_2026-10-22.py --index-dir <checkout of branch claude/sci-index> --out review_results/2026-10-22_index_memory

What it measures, in this order, each in the same process so that the numbers add up: the resident memory after the interpreter and libraries are loaded; after the passages (text and numbers) are loaded; after the keyword index (SQLite FTS5, in memory) is built;
then the time of `Engine.retrieve` (the semantic matrix product, the keyword search and the merge, as the pilot's search does it) over ten questions; and the peak resident memory (`VmHWM`) at the end. The re-rank call is the only part not measured (a network call).
"""
import argparse
import json
import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "review_tools"), HERE]

import numpy as np  # noqa: E402
import pool_runner as PR  # noqa: E402
import sci_index as si  # noqa: E402

QUESTIONS = ["Can bail be refused only because the accused is alleged to be part of a conspiracy?",
             "When is police custody remand for more than fifteen days not allowed?",
             "What must the police tell an accused at the time of arrest under section 50 CrPC?",
             "Does a delay in lodging the FIR by itself make the prosecution case doubtful?",
             "Can a High Court quash proceedings under section 482 when the complaint discloses no offence?",
             "What are the conditions for anticipatory bail under section 438?",
             "Is a confession made to a police officer admissible as evidence?",
             "When can a court summon an additional accused under section 319 of the Code?",
             "How is the right to speedy trial balanced against the rigours of bail under special statutes?",
             "What is the standard of proof for circumstantial evidence in a murder trial?"]


def mb(kb):
    return round(kb / 1024, 1)


def status():
    out = {}
    for line in open("/proc/self/status", encoding="utf-8"):
        if line.startswith(("VmRSS:", "VmHWM:")):
            out[line.split(":")[0]] = int(line.split()[1])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    res = {"note": "measured on the machine named below; a different machine's numbers will differ, memory far less than time"}
    res["machine"] = {"cpus": os.cpu_count(), "python": sys.version.split()[0], "numpy": np.__version__}
    res["rss_mb_after_imports"] = mb(status()["VmRSS"])

    t = time.time()
    metas, M, _ = si._load_index(a.index_dir)
    res["load_seconds"] = round(time.time() - t, 1)
    res["passages"], res["vector_dtype"], res["vector_dim"] = len(metas), str(M.dtype), int(M.shape[1])
    res["matrix_mb"] = round(M.nbytes / 1e6, 1)
    res["text_mb"] = round(sum(len(m["text"].encode("utf-8")) for m in metas) / 1e6, 1)
    res["rss_mb_after_load"] = mb(status()["VmRSS"])

    t = time.time()
    fts = PR.build_fts(metas)
    res["fts_build_seconds"] = round(time.time() - t, 1)
    res["rss_mb_after_fts"] = mb(status()["VmRSS"])

    rng = np.random.default_rng(0)

    class FakeClient:
        def embed(self, texts, model=None, input_type=None):
            v = rng.normal(size=M.shape[1]).astype(np.float32)
            return types.SimpleNamespace(embeddings=[v.tolist()], total_tokens=0)

    eng = PR.Engine(metas, M, FakeClient(), PR.Spend(0), fts)
    times = []
    for q in QUESTIONS:
        t = time.time()
        r = eng.retrieve(q)
        times.append(time.time() - t)
        assert len(r["cand"]) == 60
    res["retrieve_seconds"] = {"first": round(times[0], 2), "median": round(sorted(times)[len(times) // 2], 2), "max": round(max(times), 2), "questions": len(times)}
    st = status()
    res["rss_mb_after_searches"], res["peak_rss_mb"] = mb(st["VmRSS"]), mb(st["VmHWM"])
    res["not_measured"] = ["the re-rank call (network)", "the serving framework, the chat library and several users at once", "another machine's memory behaviour"]
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "numbers.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
