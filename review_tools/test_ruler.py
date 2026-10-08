"""Tests for the ruler (review_tools/ruler.py): matching of key paragraphs, the frozen/dev split, the freeze hash, the one-run guard, and gates on the saved
ruler. Run: python review_tools/test_ruler.py   (needs nothing but the repository; gates that need the sibling index checkout say SKIP when it is absent)."""
import copy
import datetime
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ruler as R

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


def raises(fn, exc):
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


# ---- matching ---------------------------------------------------------------------------------------------------------------------------------------

WORDS = " ".join(f"word{i}" for i in range(60))
KEY = WORDS
p1 = {"h": "a", "pn": "1", "section": "reasoning", "text": " ".join(f"word{i}" for i in range(0, 35)) + " alpha beta gamma delta"}
p2 = {"h": "b", "pn": "2", "section": "reasoning", "text": " ".join(f"word{i}" for i in range(30, 60)) + " epsilon zeta eta"}
p3 = {"h": "c", "pn": "3", "section": "facts", "text": "completely different words about something else entirely that never appears in the key text at all today"}
m, cov = R.match_key(KEY, [p1, p2, p3])
check("a key paragraph cut across two passages is covered by both", {x["h"] for x in m} == {"a", "b"} and cov > 0.95, (m, cov))
check("an unrelated passage is not listed", all(x["h"] != "c" for x in m))
check("no passages gives no matches and zero coverage", R.match_key(KEY, []) == ([], 0.0))
rec = R.key_record("X v Y", 1, "30", "recourse_curated", KEY, "curated_excerpt", [p1, p2, p3])
check("key_record marks a covered key as resolved", rec["resolved"] and rec["coverage"] > 0.95)
rec2 = R.key_record("X v Y", 1, "30", "recourse_curated", KEY, "curated_excerpt", [p3])
check("key_record marks an absent key as not resolved", not rec2["resolved"] and rec2["matches"] == [])
check("a missing excerpt (None) is not resolved and does not raise", not R.key_record("X", 1, "9", "recourse_curated", None, None, [p1])["resolved"])
share_only = {"h": "s", "pn": "9", "section": "reasoning", "text": " ".join(f"word{i}" for i in range(10, 30))}
m2, _ = R.match_key(KEY + " " + " ".join(f"tail{i}" for i in range(300)), [share_only])
check("a passage that is mostly the key counts even when it is a small part of a long key", [x["h"] for x in m2] == ["s"], m2)
try:
    import sci_index as si
    t = "The Court held, in Section 50 (NDPS)  that the accused's right  must be told clearly to him at the time of the search."
    check("shingles are the same runs as sci_index.shingles", R.shingles(t) == si.shingles(t))
except Exception as e:                                                         # sci_index needs numpy and friends
    print("SKIP shingles vs sci_index:", type(e).__name__)

# ---- the split ----------------------------------------------------------------------------------------------------------------------------------------


def T(tid, group, area, exposed=False, half=None, docs=(1,)):
    return {"id": tid, "group": group, "area": area, "exposed": exposed, "half": half, "expected": [{"doc": d} for d in docs], "also_acceptable": [],
            "key_passages": [], "questions": [tid + "a", tid + "b"], "era": "x", "title": tid}


ts = [T("A", "g1", "ndps", exposed=True), T("B", "g1", "ndps"), T("C", "g2", "ndps"), T("D", "g3", "ndps"), T("E", "g4", "cheque"), T("F", "g5", "cheque"), T("G", "g6", "cheque", exposed=True)]
h1 = R.assign_halves(ts, "seed-1")
check("a group with an exposed topic is dev", h1["g1"] == "dev" and h1["g6"] == "dev")
check("same input and seed give the same split", R.assign_halves(ts, "seed-1") == h1)
free_ndps = ["g2", "g3"]
check("two free groups in one area split one frozen, one dev", sorted(h1[g] for g in free_ndps) == ["dev", "frozen"], h1)
check("two free groups in another area also split", sorted(h1[g] for g in ("g4", "g5")) == ["dev", "frozen"], h1)
order = sorted(free_ndps, key=lambda g: __import__("hashlib").sha256(f"seed-1|{g}".encode()).hexdigest())
check("the first group by hash is the frozen one", h1[order[0]] == "frozen" and h1[order[1]] == "dev")
lone = R.assign_halves([T("X", "gx", "solo")], "s")
check("a single free group in an area is frozen", lone["gx"] == "frozen")
check("a group that spans two areas is refused", raises(lambda: R.assign_halves([T("X", "g", "a"), T("Y", "g", "b")], "s"), ValueError))

# ---- check() and the freeze ---------------------------------------------------------------------------------------------------------------------------


def mini():
    topics = [dict(T("T1", "g1", "ndps", exposed=True, half="dev", docs=(10,)), key_passages=[]),
              dict(T("T2", "g2", "ndps", half="frozen", docs=(20,)), key_passages=[{"doc": 20, "slug": "5", "source": "recourse_curated", "resolved": True, "matches": [{"h": "zz"}]}]),
              ]
    qs = []
    for t in topics:
        qs.append({"id": t["id"] + "a", "topic": t["id"], "kind": "lay", "text": "lay " + t["id"], "status": "new", "active": True, "half": t["half"], "marks": {"state": "none"}})
        qs.append({"id": t["id"] + "b", "topic": t["id"], "kind": "legal", "text": "legal " + t["id"], "status": "new", "active": True, "half": t["half"], "marks": {"state": "none"}})
    r = {"schema": R.SCHEMA, "topics": topics, "questions": qs}
    r["freeze"] = {"half": "frozen", "sha256": R.freeze_digest(r), "topics": ["T2"], "questions": ["T2a", "T2b"]}
    return r


base = mini()
check("a consistent mini ruler passes check()", R.check(base) == [], R.check(base))
b = copy.deepcopy(base)
b["questions"][2]["text"] = "edited after the freeze"
check("editing a frozen question breaks the freeze hash", any("frozen half has changed" in p for p in R.check(b)))
b = copy.deepcopy(base)
b["questions"][0]["text"] = "edited a dev question"
check("editing a dev question does not touch the freeze", R.check(b) == [])
b = copy.deepcopy(base)
b["topics"][1]["expected"][0]["doc"] = 10
check("a judgment acceptable on both sides of the split is reported", any("both sides" in p for p in R.check(b)))
b = copy.deepcopy(base)
b["topics"][0]["half"] = "frozen"
b["topics"][0]["exposed"] = True
check("an exposed topic in the frozen half is reported", any("exposed topic in the frozen half" in p for p in R.check(b)))
b = copy.deepcopy(base)
b["questions"][3]["active"] = False
check("a topic without an active legal question is reported", any("needs exactly one active lay and one active legal" in p for p in R.check(b)))
b = copy.deepcopy(base)
b["questions"][0]["half"] = "frozen"
check("a question whose half differs from its topic is reported", any("half differs" in p for p in R.check(b)))

# ---- the guard ----------------------------------------------------------------------------------------------------------------------------------------

with tempfile.TemporaryDirectory() as tmp:
    log = os.path.join(tmp, "runs.jsonl")
    check("dev questions are free and leave no log", [q["id"] for q in R.select(base, "dev", runs_path=log)] == ["T1a", "T1b"] and not os.path.exists(log))
    check("the frozen half is refused without final", raises(lambda: R.select(base, "frozen", runs_path=log, label="x"), R.FrozenHalfError))
    check("a final run needs a label", raises(lambda: R.select(base, "frozen", final=True, runs_path=log, label="  "), R.FrozenHalfError))
    check("nothing is logged by a refusal", not os.path.exists(log))
    bad = copy.deepcopy(base)
    bad["questions"][2]["text"] = "tampered"
    check("a changed frozen half is refused", raises(lambda: R.select(bad, "frozen", final=True, runs_path=log, label="x"), R.FrozenHalfError))
    now = datetime.datetime(2026, 10, 8, 12, 0, 0, tzinfo=datetime.timezone.utc)
    got = R.select(base, "frozen", final=True, runs_path=log, label="end of step 3", now=now)
    check("the first final run hands out the frozen questions", [q["id"] for q in got] == ["T2a", "T2b"])
    runs = R.read_runs(log)
    check("and logs it with time, label, questions and hash", len(runs) == 1 and runs[0]["ts"] == "2026-10-08T12:00:00Z" and runs[0]["label"] == "end of step 3"
          and runs[0]["qids"] == ["T2a", "T2b"] and runs[0]["freeze_sha256"] == base["freeze"]["sha256"] and runs[0]["repeat"] is False, runs)
    check("a second final run is refused", raises(lambda: R.select(base, "frozen", final=True, runs_path=log, label="again"), R.FrozenHalfError))
    R.select(base, "frozen", final=True, runs_path=log, label="again", allow_repeat=True, now=now)
    runs = R.read_runs(log)
    check("a deliberate repeat is allowed and logged as a repeat", len(runs) == 2 and runs[1]["repeat"] is True)
    check("superseded questions are never handed out", all(q["active"] for q in R.select(base, "dev", runs_path=log)))

# ---- gates on the saved ruler -------------------------------------------------------------------------------------------------------------------------

if not os.path.exists(R.DEFAULT_RULER):
    print("SKIP gates: no saved ruler")
else:
    ruler = R.load()
    topics = {t["id"]: t for t in ruler["topics"]}
    qs = {q["id"]: q for q in ruler["questions"]}
    check("the saved ruler passes check()", R.check(ruler) == [], R.check(ruler))
    check("sixteen topics: the six scored ones and ten new", len(topics) == 16 and sum(1 for t in topics.values() if t["origin"] == "v1") == 6)
    check("every active question belongs to a topic with one lay and one legal", all(len([q for q in qs.values() if q["topic"] == t and q["active"]]) == 2 for t in topics))
    check("the six first topics are all exposed and all dev", all(topics[t]["exposed"] and topics[t]["half"] == "dev" for t in ("T01", "T02", "T03", "T04", "T05", "T06")))
    check("every frozen topic is a new topic nobody has seen results for", all(t["origin"] == "new" and not t["exposed"] for t in topics.values() if t["half"] == "frozen"))
    check("the frozen half is not empty and is under half of the active questions", 0 < len(ruler["freeze"]["questions"]) < sum(1 for q in qs.values() if q["active"]) / 2)
    check("topics sharing a doctrine group are on the same side", all(len({t["half"] for t in topics.values() if t["group"] == g}) == 1 for g in {t["group"] for t in topics.values()}))
    check("every key paragraph was found in the index", all(k["resolved"] for t in topics.values() for k in t["key_passages"]), [(t["id"], k["slug"]) for t in topics.values() for k in t["key_passages"] if not k["resolved"]])
    check("every topic has at least one key paragraph", all(t["key_passages"] for t in topics.values()))
    check("the first six topics carry both the project's own picks and Recourse's", all({"claude_selected", "recourse_curated"} <= {k["source"] for k in topics[t]["key_passages"]} for t in ("T01", "T02", "T04", "T05", "T06")))
    check("new topics rest on Recourse's curated excerpts only", all({k["source"] for k in t["key_passages"]} == {"recourse_curated"} for t in topics.values() if t["origin"] == "new"))
    check("Q06 is superseded and Q06v2 asks about Section 326", qs["Q06"]["status"] == "superseded" and not qs["Q06"]["active"] and qs["Q06v2"]["active"]
          and "Section 326" in qs["Q06v2"]["text"] and "325" not in qs["Q06v2"]["text"] and qs["Q06v2"]["supersedes"] == "Q06")
    check("Q06v2 has no marks and says it needs a new pool", qs["Q06v2"]["marks"]["state"] == "none" and "new pool" in qs["Q06v2"]["marks"]["note"])
    check("Q05's rewrite now names Section 326 and the old one is kept", "326" in qs["Q05"]["rewrite"] and "325" not in qs["Q05"]["rewrite"] and qs["Q05"]["rewrite_v1"] and "326" not in qs["Q05"]["rewrite_v1"])
    check("Q05's own text is unchanged, so its marks stand", qs["Q05"]["status"] == "v1" and qs["Q05"]["text"].startswith("Both parties have settled a case of grievous hurt."))
    check("new questions have no marks", all(q["marks"]["state"] == "none" for q in qs.values() if q["status"] == "new"))
    check("Q09 is recorded as marked by one reader only", set(qs["Q09"]["marks"]["readers_per_passage"]) == {"1"})
    frozen_texts = [q["text"] for q in qs.values() if q["half"] == "frozen"]
    pool_text = open(R.DEFAULT_POOL, encoding="utf-8").read()
    check("no frozen question appears in the review pool", not any(t in pool_text for t in frozen_texts))
    tool_text = "".join(open(os.path.join(R.HERE, f), encoding="utf-8").read() for f in os.listdir(R.HERE) if f.endswith(".py") and f not in ("ruler.py", "test_ruler.py"))
    check("no frozen question appears in any other review tool", not any(t in tool_text for t in frozen_texts))
    check("the lay questions carry no section numbers (as in the first six)", all(not __import__("re").search(r"\bsection\s+\d|\bs\.\s*\d", q["text"], __import__("re").I) for q in qs.values() if q["kind"] == "lay"))
    check("the freeze note says it was written before any search", "before any search" in ruler["freeze"]["note"])
    if os.path.isdir(os.path.join(R.DEFAULT_INDEX, "index")):
        docs = {e["doc"] for t in topics.values() for e in t["expected"] + t.get("also_acceptable", [])}
        have = set()
        import glob
        import gzip
        for f in glob.glob(os.path.join(R.DEFAULT_INDEX, "index", "*.docs.jsonl.gz")):
            for line in gzip.open(f, "rt", encoding="utf-8"):
                r = json.loads(line)
                if r["doc"] in docs and not r.get("skip"):
                    have.add(r["doc"])
        check("every acceptable judgment is embedded in the index", docs <= have, sorted(docs - have))
    else:
        print("SKIP index gate: no sibling index checkout")

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
