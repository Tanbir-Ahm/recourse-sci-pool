#!/usr/bin/env python3
"""Finds and removes duplicate and mislabelled judgments in a finished index. No embedding, no API calls, no spending.

sci_index.py already skips judgments whose text is byte-for-byte the same. This tool catches the rest: the same case crawled twice
with a different header, an OCR variant, or a different layout (official report versus court website).

  scan   reads every kept judgment from the crawl and lists pairs whose text overlaps by 80% or more
  plan   decides which pairs are the SAME case (same parties, no conflicting case number), groups them, picks one copy to keep
         (--keep-landmarks makes sure the verified landmark cases in landmarks.json are never the copy that is removed;
          --save-to-index also commits and pushes the plan under state/fixes/plans/ on the index branch so a person can review it there)
  apply  removes the other copies' passages and vectors from the index files and marks them in the docs files
         (--commit commits on the index branch; --push also pushes it; both refuse if the index folder has uncommitted changes or a STOP file)

A judgment decided together with others (different case numbers or different parties) is a different case even when its text is
identical, so it is never removed here. Anything the rules cannot decide goes in the plan's "review" list.
The rules cannot tell every same-case pair (a differently spelled name, another layout), so a person reviews a plan before it is applied.
"""
import argparse, collections, gzip, heapq, itertools, json, os, re, shutil, sys, time

import numpy as np

import sci_index as si

SKETCH_K, SKETCH_MAX_DF, SKETCH_MIN_SHARED = 128, 30, 3     # cheap candidate search: smallest 128 hashes of each judgment's 5-word shingles
MIN_OVERLAP = 0.80                                          # each judgment must contain 80% of the other's 8-word shingles
MAX_LEN_RATIO = 1.30
MIN_PARTY_SIM = 0.60
HEAD_CHARS = 900
DEFAULT_LANDMARKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "landmarks.json")

BOILER = set("""supreme court of india criminal appellate jurisdiction appeal crl petition special leave civil reportable non judgment
petitioner respondent respondents appellant appellants versus vs date bench page case state states arising out slp the and others anr ors
with http judis nic original writ miscellaneous revision order corrected copy act headnote madhya pradesh uttar delhi punjab haryana
rajasthan bihar kerala gujarat karnataka maharashtra bengal west tamil nadu andhra assam orissa union""".split())


def norm_head(text):
    return re.sub(r"\s+", " ", text)[:HEAD_CHARS]


def party_tokens(head):
    """Words of the party names from a header (court-website layout, or the first caption-like stretch of the others)."""
    m = re.search(r"PETITIONER:\s*(.*?)\s*DATE OF JUDGMENT", head)
    if m:
        region = m.group(1)
    else:
        m = re.search(r"(.{3,200}?)\s*\((?:Criminal|Crl|Contempt|SLP|S\.L\.P|Writ)", head)
        if m and re.search(r"\sv\.?\s", m.group(1)):
            region = m.group(1)
        else:
            m = re.search(r"(?:NO\.?\s*[\d\-_ ]*OF\s*\d{4}|\d{4})\)?\s*(.{3,300}?)\s*(?:J\s?U\s?D\s?G\s?M\s?E\s?N\s?T|O\s?R\s?D\s?E\s?R)\b", head)
            region = m.group(1) if m else head[:250]
    return {t for t in re.findall(r"[a-z]{3,}", region.lower()) if t not in BOILER}


def party_sim(a, b):
    ta, tb = party_tokens(a), party_tokens(b)
    return len(ta & tb) / len(ta | tb) if (ta or tb) else 0.0


_NUM = re.compile(r"(\d{1,5}(?:\s*-\s*\d{1,5})?)\s*(?:of|OF)\s*(\d{4})|\bNO\.?\s*(\d{1,5}(?:\s*-\s*\d{1,5})?)\s+(\d{4})\b", re.I)
_SLP = re.compile(r"(?:S\.?L\.?P\.?|Special Leave Petition|Crl\.?\s*M\.?P\.?|I\.?A\.?|Interlocutory Application)[^0-9]{0,30}\d[\d,\s\-/()a-zA-Z.]{0,40}?\s*(?:of|OF)\s*\d{4}", re.I)


def case_numbers(head):
    """(number, year) pairs of the appeal or petition itself, in order of appearance, leaving out SLP / application numbers and dates."""
    h = _SLP.sub(" ", head[:600])
    return [((a or c).replace(" ", ""), y or d) for a, y, c, d in _NUM.findall(h)]


def _covered(number):
    """'1156-57' -> {1156, 1157}; '1174' -> {1174}."""
    lo, _, hi = number.partition("-")
    if not hi:
        return {int(lo)}
    if len(hi) < len(lo):
        hi = lo[: len(lo) - len(hi)] + hi
    return set(range(int(lo), int(hi) + 1)) if int(hi) >= int(lo) and int(hi) - int(lo) < 500 else {int(lo), int(hi)}


def numbers_conflict(a, b):
    """True when both headers give a case number and the first ones (the appeal itself) cover no number in common, or are from different years."""
    na, nb = case_numbers(a), case_numbers(b)
    if not na or not nb:
        return False
    (x, ya), (y, yb) = na[0], nb[0]
    return ya != yb or not (_covered(x) & _covered(y))


# ---------------------------------------------------------------- reading the index
def kept_docs(index_dir):
    out = {}
    for start, v in si.ledger(index_dir).items():
        with gzip.open(os.path.join(si._idx_dir(index_dir), v["base"] + ".docs.jsonl.gz"), "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if "skip" not in r:
                    out[r["doc"]] = {"block": start, "hash": r.get("hash")}
    return out


def doc_stats(index_dir, ids):
    """Passages per judgment and how many carry a paragraph number."""
    ids, stats = set(ids), collections.defaultdict(lambda: {"passages": 0, "numbered": 0})
    for start, v in si.ledger(index_dir).items():
        if not v["passages"]:
            continue
        with gzip.open(os.path.join(si._idx_dir(index_dir), v["base"] + ".meta.jsonl.gz"), "rt", encoding="utf-8") as fh:
            for line in fh:
                m = json.loads(line)
                if m["doc"] in ids:
                    stats[m["doc"]]["passages"] += 1
                    stats[m["doc"]]["numbered"] += m.get("pn") is not None
    return stats


# ---------------------------------------------------------------- scan
def scan(pool_dir, index_dir, out=print):
    """Pairs of kept judgments whose text overlaps by MIN_OVERLAP or more both ways. Returns {"pairs": [...], "heads": {id: head}, "lens": {id: chars}}."""
    t0 = time.time()
    led, kept = si.ledger(index_dir), kept_docs(index_dir)
    blocks = si.pool_blocks(pool_dir)
    texts, sketch = {}, {}
    for start in sorted(led):
        if start not in blocks:
            continue
        for r in si._read_pool_block(blocks[start]["path"]):
            if r.get("id") in kept and r.get("text"):
                texts[r["id"]] = r["text"]
                w = re.findall(r"[a-z0-9]+", r["text"].lower())
                sketch[r["id"]] = heapq.nsmallest(SKETCH_K, {hash(" ".join(w[i:i + 5])) for i in range(max(len(w) - 4, 1))})
    out(f"read {len(texts):,} of {len(kept):,} kept judgments in {time.time() - t0:.0f}s")
    inv = collections.defaultdict(list)
    for d, sk in sketch.items():
        for h in sk:
            inv[h].append(d)
    shared = collections.Counter()
    for ds in inv.values():
        if 2 <= len(ds) <= SKETCH_MAX_DF:
            for p in itertools.combinations(sorted(ds), 2):
                shared[p] += 1
    cand = [p for p, c in shared.items() if c >= SKETCH_MIN_SHARED]
    sh, pairs = {}, []
    for a, b in cand:
        for d in (a, b):
            if d not in sh:
                sh[d] = si.shingles(texts[d])
        inter = len(sh[a] & sh[b])
        a_in_b, b_in_a = inter / len(sh[a]), inter / len(sh[b])
        if min(a_in_b, b_in_a) >= MIN_OVERLAP:
            pairs.append({"a": a, "b": b, "a_in_b": round(a_in_b, 4), "b_in_a": round(b_in_a, 4), "len_a": len(texts[a]), "len_b": len(texts[b])})
    ids = {d for p in pairs for d in (p["a"], p["b"])}
    out(f"{len(cand):,} candidate pairs, {len(pairs)} with at least {MIN_OVERLAP:.0%} overlap both ways, in {time.time() - t0:.0f}s")
    return {"pairs": sorted(pairs, key=lambda p: (p["a"], p["b"])), "heads": {d: norm_head(texts[d]) for d in ids}, "lens": {d: len(texts[d]) for d in ids}}


# ---------------------------------------------------------------- plan
def classify(pair, heads):
    """'same_case', or 'different_case' with the reason."""
    a, b = pair["a"], pair["b"]
    ratio = max(pair["len_a"], pair["len_b"]) / max(min(pair["len_a"], pair["len_b"]), 1)
    if ratio > MAX_LEN_RATIO:
        return "different_case", f"lengths differ by {ratio:.2f}x"
    sim = party_sim(heads[a], heads[b])
    if sim < MIN_PARTY_SIM:
        return "different_case", f"party names differ (similarity {sim:.2f})"
    if numbers_conflict(heads[a], heads[b]):
        return "different_case", "same parties but different case numbers"
    return "same_case", f"party names match ({sim:.2f}), no conflicting case number"


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def plan(scan_result, stats, keep=(), force=(), never=(), merge=()):
    """keep: ids to prefer as the surviving copy (verified landmarks, anything cited elsewhere).
    force: [[a, b], ...] pairs that are the same case although the header rules cannot show it.
    never: [[a, b], ...] pairs that must stay apart.
    merge: [{"keep": id, "remove": [ids], "reason": text}] explicit decisions (for example a body under the wrong header)."""
    heads, lens, keep = scan_result["heads"], scan_result["lens"], set(keep)
    never = {frozenset(map(int, p)) for p in never}
    force = {frozenset(map(int, p)) for p in force}
    uf, why, review = _UF(), {}, []
    for p in scan_result["pairs"]:
        a, b = p["a"], p["b"]
        if frozenset((a, b)) in never:
            review.append({"pair": [a, b], "why": "kept apart by decision"})
            continue
        verdict, reason = ("same_case", "forced by decision") if frozenset((a, b)) in force else classify(p, heads)
        if verdict == "same_case":
            uf.union(a, b)
            why[(a, b)] = reason
        else:
            review.append({"pair": [a, b], "overlap": min(p["a_in_b"], p["b_in_a"]), "why": reason})
    groups = collections.defaultdict(set)
    for a, b in why:
        groups[uf.find(a)] |= {a, b}
    out_groups, fixed = [], {}
    for m in merge:
        members = [m["keep"], *m["remove"]]
        out_groups.append({"keep": m["keep"], "remove": sorted(m["remove"]), "reason": m["reason"], "members": members})
        for d in m["remove"]:
            fixed[d] = m["keep"]
    for g in groups.values():
        g = {d for d in g if d not in fixed}
        if len(g) < 2:
            continue
        if any(d in m["remove"] or d == m["keep"] for m in merge for d in g):
            continue
        longest = max(lens.get(d, 0) for d in g) or 1       # lengths within about 10% count as equal: OCR noise must not decide
        key = lambda d: (d not in keep, -round(stats[d]["numbered"] / max(stats[d]["passages"], 1), 1), -round(lens.get(d, 0) / longest, 1), d)
        ordered = sorted(g, key=key)
        out_groups.append({"keep": ordered[0], "remove": sorted(ordered[1:]), "reason": "same case: matching parties, no conflicting case number", "members": sorted(g)})
    for d in keep:
        for g in out_groups:
            if d in g["remove"]:
                raise ValueError(f"judgment {d} is on the keep list but the plan removes it (group {g['members']})")
    return {"groups": sorted(out_groups, key=lambda g: g["keep"]), "review": review,
            "rules": {"min_overlap": MIN_OVERLAP, "max_len_ratio": MAX_LEN_RATIO, "min_party_sim": MIN_PARTY_SIM}}


# ---------------------------------------------------------------- apply
def apply_plan(index_dir, the_plan, out=print):
    """Removes the planned copies from the index files. Returns the totals. The removed judgments stay in the docs files, marked
    skip=near_duplicate with dup_of=<kept id> and with their content hash, so a later run still recognises them and nothing is re-embedded."""
    removed = {d: g["keep"] for g in the_plan["groups"] for d in g["remove"]}
    led_before = si.ledger(index_dir)
    spent_before = si.tokens_spent(index_dir)
    where = kept_docs(index_dir)
    missing = [d for d in removed if d not in where]
    if missing:
        raise ValueError(f"not kept judgments of this index (already removed, or wrong index?): {missing[:10]}")
    if any(k not in where for k in removed.values()):
        raise ValueError("a copy chosen to be kept is not in the index")
    by_block = collections.defaultdict(set)
    for d in removed:
        by_block[where[d]["block"]].add(d)
    totals = {"blocks_rewritten": 0, "docs_removed": len(removed), "passages_removed": 0, "tokens_unchanged": spent_before}
    d_idx = si._idx_dir(index_dir)
    for start in sorted(by_block):
        v = led_before[start]
        with gzip.open(os.path.join(d_idx, v["base"] + ".docs.jsonl.gz"), "rt", encoding="utf-8") as fh:
            docs = [json.loads(line) for line in fh]
        metas, vecs = [], None
        if v["passages"]:
            with gzip.open(os.path.join(d_idx, v["base"] + ".meta.jsonl.gz"), "rt", encoding="utf-8") as fh:
                metas = [json.loads(line) for line in fh]
            vecs = np.load(os.path.join(d_idx, v["base"] + ".vec.npy"))
            assert len(metas) == vecs.shape[0]
        drop = by_block[start]
        mask = np.array([m["doc"] not in drop for m in metas], dtype=bool)
        new_metas = [m for m, k in zip(metas, mask) if k]
        new_vecs = vecs[mask] if vecs is not None else np.zeros((0, 0), dtype=np.float16)
        for r in docs:
            if r["doc"] in drop:
                r.pop("case", None)
                r.update(skip="near_duplicate", dup_of=removed[r["doc"]], was_passages=r.get("passages", 0), passages=0, noise=0)
        old_base = v["base"]
        new_base = si.write_block_files(index_dir, start, v["end"] - start + 1, docs, new_metas, new_vecs, v["tokens"])
        if new_base != old_base:
            for suffix in (".docs.jsonl.gz", ".meta.jsonl.gz", ".vec.npy"):
                p = os.path.join(d_idx, old_base + suffix)
                if os.path.exists(p):
                    os.remove(p)
        totals["blocks_rewritten"] += 1
        totals["passages_removed"] += len(metas) - len(new_metas)
        out(f"block {start:06d}: removed {len(drop)} judgments, {len(metas) - len(new_metas)} passages")
    led_after = si.ledger(index_dir)
    if set(led_after) != set(led_before):
        raise RuntimeError("the set of valid blocks changed during the rewrite; check the index folder before doing anything else")
    if si.tokens_spent(index_dir) != spent_before:
        raise RuntimeError("tokens_spent changed during the rewrite")
    return totals


def landmark_ids(path=None):
    """The judgment ids of the verified landmark cases (landmarks.json). They must never be the copy a plan removes."""
    with open(path or DEFAULT_LANDMARKS, encoding="utf-8") as fh:
        return [int(L["doc"]) for L in json.load(fh)["landmarks"]]


def check_ready_to_commit(index_dir):
    """Refusal text if the index folder must not be changed and committed right now, else None: a STOP file, uncommitted changes, or not in step with the remote."""
    if os.path.exists(os.path.join(index_dir, "STOP")):
        return "STOP file present in the index folder"
    dirty = si._git(index_dir, "status", "--porcelain")
    if dirty.returncode != 0:
        return f"{index_dir} is not a git repository"
    if dirty.stdout.strip():
        return "the index folder has uncommitted changes; commit or discard them first"
    ok, msg = si._sync(index_dir)
    if not ok:
        return f"could not update from the remote: {msg}"
    return None


def write_record(index_dir, the_plan, totals, previous_commit, note=""):
    rel = os.path.join("state", "fixes", f"{time.strftime('%Y%m%dT%H%M%S', time.gmtime())}-duplicates.json")
    os.makedirs(os.path.join(index_dir, "state", "fixes"), exist_ok=True)
    with open(os.path.join(index_dir, rel), "w", encoding="utf-8") as fh:
        json.dump({"previous_commit": previous_commit, "note": note, "totals": totals, **the_plan}, fh, indent=1)
    return rel


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan"); p.add_argument("--pool-dir", required=True); p.add_argument("--index-dir", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("plan"); p.add_argument("--index-dir", required=True); p.add_argument("--scan", required=True); p.add_argument("--out", required=True)
    p.add_argument("--decisions", help="JSON with keys keep, force, never, merge (see plan())")
    p.add_argument("--keep-landmarks", action="store_true", help="never remove the verified landmark cases (adds them to the keep list)")
    p.add_argument("--landmarks", default=DEFAULT_LANDMARKS, help="landmarks.json to read for --keep-landmarks")
    p.add_argument("--show", type=int, default=10, help="print the first N groups (keep id, removed ids)")
    p.add_argument("--save-to-index", action="store_true", help="also commit and push the plan on the index branch (state/fixes/plans/); changes no index data")
    p = sub.add_parser("apply"); p.add_argument("--index-dir", required=True); p.add_argument("--plan", required=True)
    p.add_argument("--commit", action="store_true", help="commit the change on the index branch")
    p.add_argument("--push", action="store_true", help="commit and push the index branch (implies --commit)")
    a = ap.parse_args(argv)
    if a.cmd == "scan":
        res = scan(a.pool_dir, a.index_dir)
        res["heads"] = {str(k): v for k, v in res["heads"].items()}; res["lens"] = {str(k): v for k, v in res["lens"].items()}
        json.dump(res, open(a.out, "w"))
    elif a.cmd == "plan":
        s = json.load(open(a.scan))
        s["heads"] = {int(k): v for k, v in s["heads"].items()}; s["lens"] = {int(k): v for k, v in s["lens"].items()}
        dec = json.load(open(a.decisions)) if a.decisions else {}
        ids = {d for p in s["pairs"] for d in (p["a"], p["b"])}
        keep = list(dec.get("keep", [])) + (landmark_ids(a.landmarks) if a.keep_landmarks else [])
        pl = plan(s, doc_stats(a.index_dir, ids), keep=keep, force=dec.get("force", []), never=dec.get("never", []), merge=dec.get("merge", []))
        json.dump(pl, open(a.out, "w"), indent=1)
        print(f"{len(pl['groups'])} groups, {sum(len(g['remove']) for g in pl['groups'])} judgments to remove, {len(pl['review'])} pairs left in place")
        for g in pl["groups"][:a.show]:
            print(f"  keep {g['keep']}, remove {', '.join(map(str, g['remove']))}  ({g['reason'][:60]})")
        if a.save_to_index:
            why_not = check_ready_to_commit(a.index_dir)
            if why_not:
                sys.exit(f"refused: {why_not}")
            rel = os.path.join("state", "fixes", "plans", f"{time.strftime('%Y%m%dT%H%M%S', time.gmtime())}-plan.json")
            os.makedirs(os.path.join(a.index_dir, "state", "fixes", "plans"), exist_ok=True)
            shutil.copy(a.out, os.path.join(a.index_dir, rel))
            si._commit(a.index_dir, [rel], f"dedupe plan (not applied): {len(pl['groups'])} groups")
            ok, msg = si._push(a.index_dir)
            print(f"plan saved on the index branch as {rel}" + (" (pushed)" if ok else f" (push failed: {msg})"))
            if not ok:
                sys.exit(1)
    else:
        commit = a.commit or a.push
        if os.path.exists(os.path.join(a.index_dir, "STOP")):
            sys.exit("refused: STOP file present in the index folder")
        if commit:
            why_not = check_ready_to_commit(a.index_dir)
            if why_not:
                sys.exit(f"refused: {why_not}")
        pl = json.load(open(a.plan))
        prev = si._git(a.index_dir, "rev-parse", "HEAD").stdout.strip()
        totals = apply_plan(a.index_dir, pl)
        rel = write_record(a.index_dir, pl, totals, prev)
        print(json.dumps(totals))
        if commit:
            si._commit(a.index_dir, ["index", rel], f"index fix: remove {totals['docs_removed']} duplicate judgments ({totals['passages_removed']} passages)")
            print("committed")
            if a.push:
                ok, msg = si._push(a.index_dir)
                print("pushed" if ok else f"push failed: {msg}")
                if not ok:
                    sys.exit(1)
            else:
                print("(not pushed)")


if __name__ == "__main__":
    main()
