"""The fix test's final question set (FIX_TEST_RULES_v1.md and v2): the sealed question file, the private key, the check, and the one-time hand-out guard.

    python review_tools/fix_test_set.py build --workbook FINAL.xlsx --authorities AUTHORITIES.json --soft-overlap N04,N06,N07,N13 --index-commit SHA [--drop N12] [--writer-hash-confirmed SHA256 --writer-hash-confirmed-by TEXT] [--out-dir review_data/ruler]
    python review_tools/fix_test_set.py check [--set fix_test_f_v1.json] [--key fix_test_f_key_v1.json]

The writer's workbook (Questions, Key, Declaration sheets; rules in question_rules/New_Test_Questions_Rules_and_Guidelines.docx) becomes two files:
  fix_test_f_v1.json       PUBLIC part: ids, texts and the tags the scorer needs (domain, kind, code tag, trap flag, era, language, control type, Acts concerned, look-alike, twin, soft overlap).
                           No answer, no authority, no neighbour regime. Carries the freeze hashes (questions; the key's hash) and the index snapshot.
  fix_test_f_key_v1.json   PRIVATE key: the writer's key rows next to what is in the index (document numbers of every authority), the key and stale documents, answerable or not.
--drop removes scored questions from the sealed set before sealing (question rules section 11: at least 24 usable questions must remain; controls cannot be dropped). The dropped ids are recorded in the public file's provenance and in
its freeze hash; the writer's own hash still covers every row of the workbook as received, dropped rows included. Nothing about a dropped question is handed out or scored.
Sealing = both files committed with their hashes BEFORE any search. `select` hands the questions out once and logs the hand-out; a second hand-out is refused. PRIVATE, like the rest of review_data/.
The authorities table is a JSON list of {"qid", "role" (primary | acceptable | trap_old | note), "label", "status" (IN | LEFT_OUT | ABSENT), "docs": [index document numbers], "stale": {"kind", "counts_as_stale"} (older rulings only)};
it is made by hand from the index check (review_results/2026-10-12_new_questions_intake/) and is part of what Mr. Advocate reviews.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import check_new_questions as CNQ

DATA = os.path.join(ROOT, "review_data", "ruler")
DEFAULT_SET = os.path.join(DATA, "fix_test_f_v1.json")
DEFAULT_KEY = os.path.join(DATA, "fix_test_f_key_v1.json")
DEFAULT_RUNS = os.path.join(DATA, "fix_test_f_runs.jsonl")
SCHEMA = "fix-test-questions-1"
KIND = {"E": "everyday", "L": "legal", "N": "narrative"}
NUMBERING = {"NEW": "BNS/BNSS", "OLD": "IPC/CrPC", "NONE": "none"}
PUBLIC_FIELDS = ("id", "domain", "kind", "numbering", "text", "trap", "best_law_era", "language", "control_type", "acts", "acts_named", "look_alike", "twin_of", "soft_overlap")
KEY_FIELDS_IN_PUBLIC = ("trap_note", "expected", "expected_answer", "authority", "authorities", "source_urls", "primary_authority", "neighbour_regime", "neighbour", "key_docs", "stale_docs")
ROLES = ("primary", "acceptable", "trap_old", "note")


class SealedError(RuntimeError):
    pass


def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def freeze_digest(public):
    """Hash of everything the questions are: id, text and every tag, in id order."""
    body = [{k: q.get(k) for k in PUBLIC_FIELDS} for q in sorted(public["questions"], key=lambda q: q["id"])]
    dropped = sorted((public.get("provenance") or {}).get("dropped") or [])
    return sha(canon({"questions": body, "dropped": dropped}) if dropped else canon(body))        # a set with nothing dropped keeps the hash it always had


def key_digest(key):
    return sha(canon(key["questions"]))


def writer_hash(rows):
    """The writer's own freeze hash: SHA-256 of 'Id<TAB>question text' lines, one per row of the Questions sheet (reserves included), joined by a newline (reproduced 2026-10-12 for the first file)."""
    return sha("\n".join(f"{r['Id']}\t{r['Question text']}" for r in rows))


def declared_hash(declaration):
    for _, value in declaration or []:
        m = re.findall(r"\b[0-9a-f]{64}\b", value or "")
        if m:
            return m[-1]
    return None


def key_entry(k, q, auths, soft):
    docs_in = lambda role: [d for a in auths if a["role"] == role and a["status"] == "IN" for d in a["docs"]]
    primary, acceptable = docs_in("primary"), docs_in("acceptable")
    stale = []
    for a in auths:
        if a["role"] in ("trap_old", "note") and a["status"] == "IN":
            for d in a["docs"]:
                stale.append({"doc": d, "label": a["label"], "kind": (a.get("stale") or {}).get("kind", "narrower or contested"), "counts_as_stale": bool((a.get("stale") or {}).get("counts_as_stale", False))})
    key_docs = sorted(set(primary + acceptable))
    scored = q["domain"] != "K"
    reachable = (True if key_docs else False) if scored and any(a["role"] in ("primary", "acceptable") for a in auths) else (False if scored else None)
    return {"id": q["id"], "expected_answer": k["Expected answer"], "primary_authority": k["Primary authority"], "other_acceptable": k["Other acceptable authorities"], "older_ruling": k["Older ruling a search may wrongly show (traps) with what changed and the current authority"],
            "code": k["Code that applies and why"], "source_urls": k["Source URLs"], "how_verified": k["How verified"], "conf": k["Conf"], "to_verify": k["To verify"], "neighbour_regime": q.get("neighbour"),
            "authorities": [{"label": a["label"], "role": a["role"], "where": {"IN": "in_index", "LEFT_OUT": "left_out", "ABSENT": "absent"}[a["status"]], "index_docs": a["docs"]} for a in auths],
            "key_docs": key_docs, "primary_key_docs": sorted(set(primary)), "stale_docs": stale, "reachable": reachable, "soft_overlap": soft}


def build(workbook, authorities, soft_overlap=(), index_commit=None, today=None, drop=(), confirmed_hash=None, confirmed_by=None):
    """(public, key) from the writer's final workbook and the authorities table. Raises ValueError listing every problem.
    drop: scored questions removed before sealing. confirmed_hash / confirmed_by: a freeze hash over the workbook's rows that the writer's declaration does not carry (for example because the file was revised after the declaration),
    confirmed by a named person; it is recorded next to the declared one."""
    data = CNQ.read(workbook)
    drop = tuple(sorted(set(drop or ())))
    problems = [f"{r['id']}: {r['rule']} [{r['detail']}]" for r in CNQ.check(data, drop) if not r["ok"] and r["id"].startswith(("F", "R", "S", "U"))]
    if problems:
        raise ValueError("the workbook fails the recount: " + "; ".join(problems))
    Q = {r["Id"]: r for r in data["Questions"]["rows"]}
    K = {r["Id"]: r for r in data["Key"]["rows"]}
    ids = [f"N{i:02d}" for i in range(1, 31) if f"N{i:02d}" not in drop]
    by_q = {}
    for a in authorities:
        if a["role"] not in ROLES or a["status"] not in ("IN", "LEFT_OUT", "ABSENT"):
            raise ValueError(f"authorities table: bad role or status in {a}")
        by_q.setdefault(a["qid"], []).append(a)
    named_dropped = sorted(set(by_q) & set(drop))
    if named_dropped:
        raise ValueError(f"authorities table names dropped questions {named_dropped}")
    unknown = sorted(set(by_q) - set(ids) - {i for i in Q if i.startswith("NR")})
    if unknown:
        raise ValueError(f"authorities table names unknown questions {unknown}")
    soft = set(soft_overlap)
    if not soft <= set(ids):
        raise ValueError(f"soft-overlap ids not in the set: {sorted(soft - set(ids))}")
    qs, keyq = [], {}
    for i in ids:
        r = Q[i]
        q = {"id": i, "domain": r["Domain (A to K)"], "kind": KIND[r["Phr (E/L/N)"]], "numbering": NUMBERING[r["Sec (NEW/OLD/NONE)"]], "text": r["Question text"], "trap": r["CT (Y/N)"] == "Y",
             "best_law_era": "2017 or later" if r["Era 2017+ (Y/N)"] == "Y" else "before 2017", "language": "Hinglish" if r["Hinglish (Y/N)"] == "Y" else "English",
             "control_type": r["Control type (K1/K2/K3, domain K only)"] or None, "acts": sorted(CNQ.tags_of(r['Act(s) concerned (from the 13, or "none")'])),
             "acts_named": r["Act, section or acronym named in the question text (Y/N)"] == "Y", "look_alike": r["Look-alike (Y/N)"] == "Y", "twin_of": r["Twin of (Id or blank)"] or None, "soft_overlap": i in soft}
        q["neighbour"] = r["Neighbour regime"]
        qs.append(q)
    for q in qs:
        auths = by_q.get(q["id"], [])
        if q["domain"] != "K" and not any(a["role"] == "primary" for a in auths):
            raise ValueError(f"{q['id']}: no primary authority in the authorities table")
        keyq[q["id"]] = key_entry(K[q["id"]], q, auths, q["soft_overlap"])
        del q["neighbour"]
    wh = writer_hash(data["Questions"]["rows"])                                  # every row as received, dropped rows included
    declared = declared_hash(data["Declaration"])
    prov = {"workbook_sha256": hashlib.sha256(open(workbook, "rb").read()).hexdigest(), "writer_text_sha256": wh, "writer_declared_sha256": declared, "writer_hash_matches": declared == wh or (confirmed_hash is not None and confirmed_hash == wh),
            "unused_reserves": sorted(i for i in Q if i.startswith("NR"))}
    if confirmed_hash is not None:
        prov["writer_confirmed_sha256"], prov["writer_confirmed_by"] = confirmed_hash, confirmed_by or ""
    if drop:
        prov["dropped"] = list(drop)
    public = {"schema": SCHEMA, "built": today or datetime.date.today().isoformat(), "questions": qs, "index_snapshot": {"commit": index_commit}, "provenance": prov}
    key = {"schema": SCHEMA + "-key", "built": public["built"], "questions": keyq}
    public["freeze"] = {"sha256": freeze_digest(public), "key_sha256": key_digest(key), "questions": ids,
                        "note": "Written before any search was run on these questions. Handed out once, with `select`; the hand-out is logged."}
    return public, key


def check(public, key=None):
    """Problems found in a built question file (and its key): structure, counts, hashes, no key fields in the public file."""
    bad = []
    ids = [q["id"] for q in public["questions"]]
    dropped = sorted((public.get("provenance") or {}).get("dropped") or [])
    if len(ids) != len(set(ids)):
        bad.append("duplicate ids")
    if ids != [f"N{i:02d}" for i in range(1, 31) if f"N{i:02d}" not in dropped]:
        bad.append("ids are not N01 to N30 in order" + (f" less the dropped {dropped}" if dropped else ""))
    if dropped and (30 - len(dropped) < CNQ.USABLE_FLOOR or any(not re.fullmatch(r"N(0[1-9]|[12]\d|30)", d) for d in dropped)):
        bad.append(f"dropped {dropped}: fewer than {CNQ.USABLE_FLOOR} usable questions remain, or an id is not N01 to N30")
    counts = {}
    for q in public["questions"]:
        counts[q["domain"]] = counts.get(q["domain"], 0) + 1
        if q["kind"] not in KIND.values() or q["numbering"] not in NUMBERING.values():
            bad.append(f"{q['id']}: bad kind or numbering")
    short = {d: CNQ.DOMAINS[d] - counts.get(d, 0) for d in CNQ.DOMAINS}
    if any(counts.get(d, 0) > CNQ.DOMAINS[d] for d in counts if d in CNQ.DOMAINS) or set(counts) - set(CNQ.DOMAINS) or sum(short.values()) != len(dropped) or short.get("K", 0) != 0 or any(v < 0 for v in short.values()):
        bad.append(f"domain counts {counts} differ from the plan {CNQ.DOMAINS}" + (f" less the {len(dropped)} dropped scored question(s)" if dropped else ""))
    leaked = sorted({k for q in public["questions"] for k in q if k in KEY_FIELDS_IN_PUBLIC})
    if leaked:
        bad.append("the question file holds key fields: " + ", ".join(leaked))
    if public["freeze"]["sha256"] != freeze_digest(public):
        bad.append("the questions have changed since the freeze (hash differs)")
    if public["freeze"]["questions"] != ids:
        bad.append("freeze list differs from the questions")
    if not (public.get("index_snapshot") or {}).get("commit"):
        bad.append("no index snapshot recorded")
    if key is not None:
        if key_digest(key) != public["freeze"]["key_sha256"]:
            bad.append("the key has changed since the freeze (hash differs)")
        if sorted(key["questions"]) != sorted(ids):
            bad.append("the key does not cover exactly the questions")
    return bad


def load(path=DEFAULT_SET):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_runs(path=DEFAULT_RUNS):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def select(public, final=False, label="", runs_path=DEFAULT_RUNS, allow_repeat=False, now=None):
    """Hands the questions out ONCE (for the single Stage F search) and logs it. Returns the questions with half = 'final' (the pool runner's field)."""
    if not final:
        raise SealedError("the final questions are run once: ask for them with final=True and a label")
    if not label.strip():
        raise SealedError("a final run needs a label saying what is being judged")
    if freeze_digest(public) != public["freeze"]["sha256"]:
        raise SealedError("the questions have changed since the freeze; do not run them")
    prior = read_runs(runs_path)
    if prior and not allow_repeat:
        raise SealedError(f"the questions were already handed out on {prior[0]['ts']} ({prior[0]['label']}); a repeat needs allow_repeat=True and is logged as a repeat")
    stamp = (now or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(os.path.dirname(runs_path) or ".", exist_ok=True)
    with open(runs_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": stamp, "label": label, "repeat": bool(prior), "qids": [q["id"] for q in public["questions"]], "freeze_sha256": public["freeze"]["sha256"], "key_sha256": public["freeze"]["key_sha256"]}) + "\n")
    return [dict(q, half="final") for q in public["questions"]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--workbook", required=True)
    b.add_argument("--authorities", required=True)
    b.add_argument("--soft-overlap", default="")
    b.add_argument("--index-commit", required=True)
    b.add_argument("--drop", default="", help="comma-separated ids of scored questions dropped before sealing")
    b.add_argument("--writer-hash-confirmed", default=None, help="freeze hash over the workbook's rows confirmed by a person (when the declaration carries an older one)")
    b.add_argument("--writer-hash-confirmed-by", default="")
    b.add_argument("--out-dir", default=DATA)
    c = sub.add_parser("check")
    c.add_argument("--set", default=DEFAULT_SET)
    c.add_argument("--key", default=DEFAULT_KEY)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        public, key = build(a.workbook, json.load(open(a.authorities, encoding="utf-8")), [x for x in a.soft_overlap.split(",") if x], a.index_commit,
                            drop=[x.strip() for x in a.drop.split(",") if x.strip()], confirmed_hash=a.writer_hash_confirmed, confirmed_by=a.writer_hash_confirmed_by)
        os.makedirs(a.out_dir, exist_ok=True)
        for name, obj in (("fix_test_f_v1.json", public), ("fix_test_f_key_v1.json", key)):
            with open(os.path.join(a.out_dir, name), "w", encoding="utf-8") as fh:
                json.dump(obj, fh, ensure_ascii=False, indent=1, sort_keys=True)
                fh.write("\n")
        print(f"built {a.out_dir}: {len(public['questions'])} questions" + (f" (dropped {public['provenance']['dropped']})" if public['provenance'].get('dropped') else "") + f", questions hash {public['freeze']['sha256']}, key hash {public['freeze']['key_sha256']}; writer's own hash {'matches' if public['provenance']['writer_hash_matches'] else 'DOES NOT MATCH'}")
        return 0
    bad = check(load(a.set), json.load(open(a.key, encoding="utf-8")) if os.path.exists(a.key) else None)
    print("OK" if not bad else "PROBLEMS: " + "; ".join(bad))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
