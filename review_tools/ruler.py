"""The ruler: the fixed test every search version is measured on, with a frozen half that is run once.

What it holds (review_data/ruler/ruler_v2.json, PRIVATE like pool_all.json): topics (a lay and a legal question each), the judgments that are acceptable
answers, the key paragraphs (where the Court itself states the rule), a half for each topic ('dev' or 'frozen'), and what is known about the marks.

Where the ground truth comes from, per key paragraph:
  recourse_curated  a verbatim excerpt the Recourse repository already holds and lists as hand-verified (read-only checkout). Chosen by Recourse's
                    curation, not by this project's search. Nothing in Recourse says a lawyer checked it.
  claude_selected   a paragraph picked by this project for the first six topics (landmarks.json 'pinned'). Not lawyer-checked.
Each key paragraph is matched to the index's own passages by shared 8-word runs (containment), so a search result can be compared with it.

Halves: a topic is 'frozen' only if nobody has seen search results for it ('exposed' false) and no topic in the same group is exposed or dev. Groups join
topics that share an expected judgment or that Recourse files under one doctrine, so a case cannot sit on both sides of the split. Free groups are split
inside each area by SHA-256(seed|group), alternating frozen, dev, frozen, ... One seed, used once. The frozen half's content is hashed; `select` refuses to
hand out the frozen questions unless asked for a final run, refuses a second run unless told to repeat, and writes every hand-out to a log.

    python review_tools/ruler.py build            # topics_v2.json + pool + landmarks + index + Recourse chunks -> ruler_v2.json
    python review_tools/ruler.py check            # structure, split rules, freeze hash
    python review_tools/ruler.py list --half dev
    python review_tools/ruler.py select --half frozen --final --label "end of step 3"
"""
import argparse
import csv
import datetime
import glob
import gzip
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "review_data", "ruler")
DEFAULT_TOPICS = os.path.join(DATA, "topics_v2.json")
DEFAULT_RULER = os.path.join(DATA, "ruler_v2.json")
DEFAULT_RUNS = os.path.join(DATA, "frozen_runs.jsonl")
DEFAULT_POOL = os.path.join(ROOT, "review_data", "pool_all.json")
DEFAULT_LANDMARKS = os.path.join(ROOT, "landmarks.json")
DEFAULT_MARKS = os.path.join(ROOT, "review_results", "2026-10-07_full_read", "llm_marks.csv")
DEFAULT_INDEX = os.path.normpath(os.path.join(ROOT, "..", "recourse-sci-index"))
DEFAULT_RECOURSE = os.path.normpath(os.path.join(ROOT, "..", "tanbir-ahm", "recourse"))
SCHEMA = "ruler-2"
MIN_CONTAIN = 0.5            # a key paragraph counts as found when this share of its 8-word runs is in the index passages that hold it
SHOW_CONTAIN = 0.3           # weaker overlaps are kept in the record, marked unresolved


class FrozenHalfError(RuntimeError):
    pass


def shingles(t, n=8):
    """Same runs of n words as sci_index.shingles, so containment here agrees with the pinned-passage test there."""
    w = re.sub(r"[^a-z0-9 ]", " ", (t or "").lower()).split()
    return {" ".join(w[i:i + n]) for i in range(max(len(w) - n + 1, 1))}


def containment(key_sh, text):
    """Share of the key paragraph's runs that are also in the passage."""
    return len(key_sh & shingles(text)) / max(len(key_sh), 1)


# ---- the index's passages and Recourse's excerpts -------------------------------------------------------------------------------------------------------

def index_passages(index_dir, docs):
    """{doc: [ {h, pn, section, text} ]} for the wanted judgments, streamed from the index's meta files."""
    want = set(docs)
    out = {d: [] for d in want}
    for f in sorted(glob.glob(os.path.join(index_dir, "index", "*.meta.jsonl.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if r["doc"] in want:
                    out[r["doc"]].append({"h": r["h"], "pn": r.get("pn"), "section": r.get("section"), "text": r["text"]})
    return out


def recourse_excerpt(recourse_dir, fname, slug, cache):
    """The verbatim text Recourse holds for one paragraph slug, or None."""
    path = os.path.join(recourse_dir, "chunks", fname)
    if path not in cache:
        with open(path, encoding="utf-8") as fh:
            cache[path] = json.load(fh)
    for c in cache[path]:
        if str(c.get("paragraph_number")) == slug:
            return c["text"], c.get("chunk_method")
    return None, None


def match_key(text, passages):
    """How a key paragraph sits in the index. Returns (matches, coverage). A long paragraph can be cut across several passages, so a passage counts as
    part of the key paragraph when it holds SHOW_CONTAIN of the key's 8-word runs ('containment') or when half of the passage's own runs come from the key
    ('share'). 'coverage' is the share of the key's runs found anywhere in those passages."""
    ksh = shingles(text)
    found, covered = [], set()
    for p in passages:
        psh = shingles(p["text"])
        inter = ksh & psh
        if not inter:
            continue
        c, sh = len(inter) / max(len(ksh), 1), len(inter) / max(len(psh), 1)
        if c >= SHOW_CONTAIN or sh >= 0.5:
            found.append({"h": p["h"], "pn": p["pn"], "section": p["section"], "containment": round(c, 3), "share": round(sh, 3)})
            covered |= inter
    found.sort(key=lambda m: -max(m["containment"], m["share"]))
    return found[:6], round(len(covered) / max(len(ksh), 1), 3)


def key_record(case, doc, slug, source, text, method, passages):
    m, cov = match_key(text, passages) if text else ([], 0.0)
    return {"doc": doc, "case": case, "slug": slug, "source": source, "chunk_method": method, "chars": len(text or ""),
            "resolved": cov >= MIN_CONTAIN, "coverage": cov, "matches": m}


# ---- marks already held ---------------------------------------------------------------------------------------------------------------------------

def marking_summary(marks_csv):
    """{qid: {passages, readers_per_passage: {n: how many passages}}} from the first full read; {} if the file is missing."""
    if not marks_csv or not os.path.exists(marks_csv):
        return {}
    with open(marks_csv, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return {}
    run_cols = [c for c in rows[0] if c not in ("Q", "No", "judgment_id", "consensus", "agreement_share", "n_votes", "any_Misleading", "source")]
    out = {}
    for r in rows:
        s = out.setdefault(r["Q"], {"passages": 0, "readers_per_passage": {}})
        n = sum(1 for c in run_cols if (r.get(c) or "").strip())
        s["passages"] += 1
        s["readers_per_passage"][str(n)] = s["readers_per_passage"].get(str(n), 0) + 1
    return out


# ---- the split ------------------------------------------------------------------------------------------------------------------------------------

def assign_halves(topics, seed):
    """{group: 'dev'|'frozen'}. A group with any exposed topic is dev. The other groups are split inside each area, alternating frozen, dev, ..."""
    groups = {}
    for t in topics:
        groups.setdefault(t["group"], []).append(t)
    for g, ts in groups.items():
        if len({t["area"] for t in ts}) != 1:
            raise ValueError(f"group {g} spans more than one area")
    out = {g: "dev" for g, ts in groups.items() if any(t["exposed"] for t in ts)}
    free = {}
    for g, ts in groups.items():
        if g not in out:
            free.setdefault(ts[0]["area"], []).append(g)
    for area, gs in free.items():
        gs.sort(key=lambda g: hashlib.sha256(f"{seed}|{g}".encode("utf-8")).hexdigest())
        for i, g in enumerate(gs):
            out[g] = "frozen" if i % 2 == 0 else "dev"
    return out


def freeze_digest(ruler):
    """SHA-256 of everything about the frozen half that a later edit could change: questions, expected judgments, key paragraphs."""
    tids = sorted(t["id"] for t in ruler["topics"] if t["half"] == "frozen")
    body = []
    for tid in tids:
        t = next(x for x in ruler["topics"] if x["id"] == tid)
        qs = [q for q in ruler["questions"] if q["topic"] == tid]
        body.append({"id": tid, "group": t["group"], "area": t["area"], "expected": t["expected"], "also_acceptable": t.get("also_acceptable", []),
                     "key_passages": [{"doc": k["doc"], "slug": k["slug"], "source": k["source"], "resolved": k["resolved"], "h": [m["h"] for m in k["matches"]]}
                                      for k in t["key_passages"]],
                     "questions": [{"id": q["id"], "kind": q["kind"], "text": q["text"], "rewrite": q.get("rewrite")} for q in sorted(qs, key=lambda q: q["id"])]})
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


# ---- build ----------------------------------------------------------------------------------------------------------------------------------------

def build(topics_path=DEFAULT_TOPICS, pool_path=DEFAULT_POOL, landmarks_path=DEFAULT_LANDMARKS, marks_path=DEFAULT_MARKS,
          index_dir=DEFAULT_INDEX, recourse_dir=DEFAULT_RECOURSE, today=None):
    with open(topics_path, encoding="utf-8") as fh:
        src = json.load(fh)
    with open(pool_path, encoding="utf-8") as fh:
        pool = json.load(fh)
    with open(landmarks_path, encoding="utf-8") as fh:
        landmarks = json.load(fh)["landmarks"]
    marking = marking_summary(marks_path)
    today = today or datetime.date.today().isoformat()
    cache = {}

    plan = []                     # (topic dict without key_passages, [key specs])
    questions = []
    for tid, spec in src["old_topics"].items():
        lm = landmarks[spec["landmark_index"]]
        lm_doc = int(lm["doc"])
        qa, qb = pool[2 * spec["landmark_index"]], pool[2 * spec["landmark_index"] + 1]
        topic = {"id": tid, "title": lm["name"], "origin": "v1", "area": spec["area"], "group": spec["group"], "era": spec["era"], "exposed": True,
                 "expected": [{"doc": lm_doc, "name": lm["name"], "role": "landmark", "source": "landmarks.json"}],
                 "also_acceptable": spec.get("also_acceptable", []), "questions": [qa["qid"], qb["qid"]]}
        keys = [{"doc": lm_doc, "case": lm["name"], "slug": f"pinned {i + 1}", "source": "claude_selected", "text": p["text"], "method": "landmarks.json"}
                for i, p in enumerate(lm["pinned"])]
        for rk in spec["recourse_keys"]:
            for slug in rk["slugs"]:
                text, method = recourse_excerpt(recourse_dir, rk["file"], slug, cache)
                keys.append({"doc": rk["doc"], "case": rk["name"], "slug": slug, "source": "recourse_curated", "text": text, "method": method})
        plan.append((topic, keys))
        for q in (qa, qb):
            marks = {"state": "llm-judged", **marking.get(q["qid"], {})}
            rec = {"id": q["qid"], "topic": tid, "kind": q["kind"], "text": q["question"], "status": "v1", "active": True, "marks": marks}
            if q.get("rewrite"):
                rec["rewrite"] = q["rewrite"]
            questions.append(rec)
    for t in src["new_topics"]:
        topic = {"id": t["id"], "title": t["title"], "origin": "new", "area": t["area"], "group": t["group"], "era": t["era"], "exposed": False,
                 "expected": [dict(e, source="recourse_curated_case") for e in t["expected"]], "also_acceptable": t.get("also_acceptable", []),
                 "questions": [q["id"] for q in t["questions"]]}
        if t.get("notes"):
            topic["notes"] = t["notes"]
        keys = []
        for rk in t["recourse_keys"]:
            for slug in rk["slugs"]:
                text, method = recourse_excerpt(recourse_dir, rk["file"], slug, cache)
                keys.append({"doc": rk["doc"], "case": rk["name"], "slug": slug, "source": "recourse_curated", "text": text, "method": method})
        plan.append((topic, keys))
        for q in t["questions"]:
            questions.append({"id": q["id"], "topic": t["id"], "kind": q["kind"], "text": q["text"], "status": "new", "active": True,
                              "marks": {"state": "none", "note": "no search has been run on this question and no passage has been marked"}})

    by_id = {q["id"]: q for q in questions}
    for c in src["corrections"]:
        if c.get("supersedes"):
            old = by_id[c["supersedes"]]
            old["status"], old["active"], old["superseded_by"] = "superseded", False, c["id"]
            old["marks"]["note"] = "these marks answer the old wording; kept as a record"
            new = {"id": c["id"], "topic": c["topic"], "kind": c["kind"], "text": c["text"], "status": "corrected", "active": True, "supersedes": c["supersedes"],
                   "correction_reason": c["reason"],
                   "marks": {"state": "none", "note": "needs a new pool (the old one came from a section search on 325) and new marks"}}
            questions.append(new)
            by_id[c["id"]] = new
            for t, _ in plan:
                if t["id"] == c["topic"]:
                    t["questions"].append(c["id"])
        elif c.get("rewrite_v2"):
            q = by_id[c["id"]]
            q["rewrite_v1"], q["rewrite"] = q.get("rewrite"), c["rewrite_v2"]
            q["rewrite_note"] = c["reason"]

    docs = {k["doc"] for _, ks in plan for k in ks}
    passages = index_passages(index_dir, docs)
    topics = []
    for topic, keys in plan:
        topic["key_passages"] = [key_record(k["case"], k["doc"], k["slug"], k["source"], k["text"], k["method"], passages.get(k["doc"], [])) for k in keys]
        topics.append(topic)
    halves = assign_halves(topics, src["seed"])
    for t in topics:
        t["half"] = halves[t["group"]]
    for q in questions:
        q["half"] = next(t["half"] for t in topics if t["id"] == q["topic"])
    ruler = {"schema": SCHEMA, "built": today, "seed": src["seed"],
             "sources": {"topics": os.path.basename(topics_path), "pool": "review_data/pool_all.json", "landmarks": "landmarks.json", "marks": "review_results/2026-10-07_full_read/llm_marks.csv",
                         "recourse_commit": src["recourse_commit"], "recourse_note": src["recourse_source_note"]},
             "rules": {"match": f"a key paragraph is found when {MIN_CONTAIN:.0%} of its 8-word runs are in the passages that hold it (a passage holds it if it has {SHOW_CONTAIN:.0%} of the key's runs or half of its own runs are the key's)",
                       "split": "frozen only if unexposed and the whole group is unexposed; free groups split inside each area by SHA-256(seed|group), alternating frozen, dev",
                       "exposed": "a topic is exposed once search results for it have been seen; the first six topics were scored, rewritten and discussed before this file existed"},
             "topics": topics, "questions": sorted(questions, key=lambda q: (int(re.match(r"Q(\d+)", q["id"]).group(1)), q["id"])),
             "index_gaps": src["index_gaps"]}
    ruler["freeze"] = {"half": "frozen", "sha256": freeze_digest(ruler),
                       "topics": sorted(t["id"] for t in topics if t["half"] == "frozen"),
                       "questions": sorted(q["id"] for q in ruler["questions"] if q["half"] == "frozen" and q["active"]),
                       "note": "Written before any search was run on these questions. Run once, at the end, with `select --half frozen --final`."}
    return ruler


# ---- checks ---------------------------------------------------------------------------------------------------------------------------------------

def check(ruler):
    """A list of problems; empty means the ruler is consistent."""
    bad = []
    tids = {t["id"] for t in ruler["topics"]}
    qids = [q["id"] for q in ruler["questions"]]
    if len(qids) != len(set(qids)):
        bad.append("duplicate question ids")
    if len(tids) != len(ruler["topics"]):
        bad.append("duplicate topic ids")
    for q in ruler["questions"]:
        if q["topic"] not in tids:
            bad.append(f"{q['id']}: unknown topic {q['topic']}")
        if q["kind"] not in ("lay", "legal"):
            bad.append(f"{q['id']}: kind {q['kind']}")
        if q["active"] and q["status"] == "superseded":
            bad.append(f"{q['id']}: superseded but active")
        if not q["text"].strip():
            bad.append(f"{q['id']}: empty text")
    for t in ruler["topics"]:
        act = [q for q in ruler["questions"] if q["topic"] == t["id"] and q["active"]]
        if sorted(q["kind"] for q in act) != ["lay", "legal"]:
            bad.append(f"{t['id']}: needs exactly one active lay and one active legal question, has {[q['kind'] for q in act]}")
        if not t["expected"]:
            bad.append(f"{t['id']}: no expected judgment")
        if t["half"] == "frozen" and t["exposed"]:
            bad.append(f"{t['id']}: exposed topic in the frozen half")
        for q in ruler["questions"]:
            if q["topic"] == t["id"] and q["half"] != t["half"]:
                bad.append(f"{q['id']}: half differs from its topic")
    docs_by_half = {}
    for t in ruler["topics"]:
        for d in [e["doc"] for e in t["expected"]] + [e["doc"] for e in t.get("also_acceptable", [])]:
            docs_by_half.setdefault(d, {})[t["half"]] = t["id"]
    for d, h in docs_by_half.items():
        if len(h) > 1:
            bad.append(f"judgment {d} is an acceptable answer on both sides of the split: {h}")
    groups = {}
    for t in ruler["topics"]:
        groups.setdefault(t["group"], set()).add(t["half"])
    for g, hs in groups.items():
        if len(hs) > 1:
            bad.append(f"group {g} is split across halves")
    if ruler["freeze"]["sha256"] != freeze_digest(ruler):
        bad.append("the frozen half has changed since the freeze (hash differs)")
    if sorted(q["id"] for q in ruler["questions"] if q["half"] == "frozen" and q["active"]) != ruler["freeze"]["questions"]:
        bad.append("freeze question list differs from the questions marked frozen")
    return bad


# ---- the guard ------------------------------------------------------------------------------------------------------------------------------------

def read_runs(runs_path):
    if not os.path.exists(runs_path):
        return []
    with open(runs_path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def select(ruler, half, final=False, runs_path=DEFAULT_RUNS, label="", allow_repeat=False, now=None):
    """The active questions of a half. 'dev' is free. 'frozen' needs final=True, a label, an unchanged freeze hash, and (unless allow_repeat) no earlier
    hand-out; every hand-out is appended to the log, a repeat marked as such."""
    qs = [q for q in ruler["questions"] if q["active"] and q["half"] == half]
    if half != "frozen":
        return qs
    if not final:
        raise FrozenHalfError("the frozen half is run once, at the end: ask for it with final=True and a label")
    if not label.strip():
        raise FrozenHalfError("a final run needs a label saying what is being judged")
    if freeze_digest(ruler) != ruler["freeze"]["sha256"]:
        raise FrozenHalfError("the frozen half has changed since the freeze; do not run it")
    prior = read_runs(runs_path)
    if prior and not allow_repeat:
        raise FrozenHalfError(f"the frozen half was already handed out on {prior[0]['ts']} ({prior[0]['label']}); a repeat needs allow_repeat=True and is logged as a repeat")
    stamp = (now or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(os.path.dirname(runs_path) or ".", exist_ok=True)
    with open(runs_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": stamp, "label": label, "repeat": bool(prior), "qids": [q["id"] for q in qs], "freeze_sha256": ruler["freeze"]["sha256"]}) + "\n")
    return qs


# ---- command line ---------------------------------------------------------------------------------------------------------------------------------

def load(path=DEFAULT_RULER):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def summary(ruler):
    lines = []
    for half in ("dev", "frozen"):
        ts = [t for t in ruler["topics"] if t["half"] == half]
        qs = [q for q in ruler["questions"] if q["half"] == half and q["active"]]
        lines.append(f"{half}: {len(ts)} topics, {len(qs)} active questions ({', '.join(t['id'] for t in ts)})")
    kp = [k for t in ruler["topics"] for k in t["key_passages"]]
    lines.append(f"key paragraphs: {len(kp)}, found in the index: {sum(1 for k in kp if k['resolved'])}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--topics", default=DEFAULT_TOPICS)
    b.add_argument("--out", default=DEFAULT_RULER)
    b.add_argument("--index", default=DEFAULT_INDEX)
    b.add_argument("--recourse", default=DEFAULT_RECOURSE)
    b.add_argument("--force", action="store_true", help="overwrite an existing ruler (this changes the freeze; the old hash is lost)")
    c = sub.add_parser("check")
    c.add_argument("--ruler", default=DEFAULT_RULER)
    ls = sub.add_parser("list")
    ls.add_argument("--ruler", default=DEFAULT_RULER)
    ls.add_argument("--half", choices=["dev", "frozen", "all"], default="all")
    s = sub.add_parser("select")
    s.add_argument("--ruler", default=DEFAULT_RULER)
    s.add_argument("--half", choices=["dev", "frozen"], required=True)
    s.add_argument("--final", action="store_true")
    s.add_argument("--label", default="")
    s.add_argument("--allow-repeat", action="store_true")
    s.add_argument("--runs", default=DEFAULT_RUNS)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        if os.path.exists(a.out) and not a.force:
            print(f"{a.out} exists; a rebuild changes the freeze. Use --force only on purpose.")
            return 2
        ruler = build(a.topics, index_dir=a.index, recourse_dir=a.recourse)
        problems = check(ruler)
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(ruler, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print(summary(ruler))
        print("freeze sha256:", ruler["freeze"]["sha256"])
        print("problems:", problems or "none")
        return 1 if problems else 0
    ruler = load(a.ruler)
    if a.cmd == "check":
        problems = check(ruler)
        print(summary(ruler))
        print("problems:", problems or "none")
        return 1 if problems else 0
    if a.cmd == "list":
        for q in ruler["questions"]:
            if q["active"] and (a.half == "all" or q["half"] == a.half):
                print(q["id"], q["half"], q["topic"], q["kind"], q["text"][:90])
        return 0
    try:
        qs = select(ruler, a.half, final=a.final, runs_path=a.runs, label=a.label, allow_repeat=a.allow_repeat)
    except FrozenHalfError as e:
        print("refused:", e)
        return 3
    print(" ".join(q["id"] for q in qs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
