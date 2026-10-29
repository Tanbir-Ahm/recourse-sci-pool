"""authority_graph.py -- which judgments of the index do the OTHER judgments of the index name? (the court's own signal of a landmark)

WHY. A search by wording finds the judgments that SAY something like the question. It does not find the judgment the others rely on: the landmark that states the rule in long, mixed passages is outranked by
hundreds of later judgments that restate it in one tidy sentence each. On 2026-10-29 a question about conviction on circumstantial evidence returned eight such restatements and never *Sharad Birdhichand Sarda*,
named by 446 other judgments of the same index. The signal that was missing is the one the courts themselves leave behind: who names whom.

WHAT. This module reads every passage of an index, finds the case names it mentions ("X v. Y", with a year or a reporter citation when one follows, and the bare name of a case that is demonstrably cited by its
full name), matches each mention to a judgment of the same index by its party names, and writes a table:

    cited_by   judgment -> how many OTHER judgments of the index name it (one count for the whole cluster of a case held twice)
    cluster    judgment -> the first judgment of its cluster (only where they differ)
    cites      judgment -> the clusters it names

A search then asks the court's own question of the judgments it has just retrieved: "which earlier judgment do most of you name?" (authority_search.py). Nothing here says that a case is good law: a case can be named
because it was criticised, and a count is not a holding.

    python authority_graph.py build --index-dir DIR --names names_table/names_table_d8811a9.json.gz [--side DIR ...] --out authority_table/authority_<index commit>.json.gz
    python authority_graph.py show  authority_table/authority_<index commit>.json.gz [--names ...] [--top 40]

Rebuild the table whenever the index changes (the service refuses to start on a table made for another commit).

HOW MATCHING WORKS, and why it is strict. A wrong link would make an ordinary case look like a landmark; a missed link only makes a landmark look slightly less cited.
- "X v. Y": the squashed first party (letters only; honorifics, "& Ors", "(Dead) by LRs", "@ alias", "S/O ..." dropped; the leading words of the sentence trimmed off) AND the first three words of the second party.
  A distinctive first party (12 letters or more, not a State, the Union or another body that many cases share) belonging to one case only is also matched without the second party.
- One pair of names can belong to cases decades apart ("Tofan Singh v. State of Tamil Nadu": the 2013 reference order and the 2020 Constitution Bench decision). A year or citation beside the mention picks the case within
  two years of it; without one, the latest case not later than the citing judgment is taken.
- A case held twice in the index (the same distinctive name, the same second party, decided within two years of each other) is one cluster.
- The bare name ("in Tofan Singh the Court held") is used only for a case already named in full by at least three judgments, only if it is distinctive (nine letters and two words, or ten letters), only in the way a case
  is cited ("in X", "the decision in X", "X (supra)", "X's case", "X (2021)"), never when "J." follows (a judge of that name), and never by an earlier judgment than the one named.
Measured on 2026-10-29 on the index of 19,236 judgments: 94,143 "X v. Y" mentions, 38,264 matched, plus 31,033 bare mentions; the most named judgments are the classics of Indian criminal law. The table is NOT
checked by a lawyer; it counts text matches. Known gaps: names that a judgment abbreviates or misspells, and cases the index does not hold (a mention of "Virsa Singh v. State of Punjab" with no year is credited to the only
Virsa Singh v. State of Punjab the index holds, which is a different case of 2008).
"""
import argparse
import collections
import glob
import gzip
import json
import os
import re
import sys
import time

_HON = r"(?:shri|smt|sri|sh|dr|mr|mrs|ms|m/s|messrs|late|lt|col|capt|major|justice|hon'ble|prof|kumari|km|master|baby)"
_DROPW = frozenset("ors anr anrs etc others another dead lrs lr thr through by alias the rep represented its his her".split())
_CONNECT = r"(?:of|and|the|for|&|ors\.?|anr\.?|etc\.?|others|another|in|re|m/s|dead|lrs?)"
_ABBR = re.compile(r"^(?:Dr|Mr|Mrs|Ms|Smt|Shri|Sri|Sh|Col|Lt|Capt|Prof|Hon|St|Vs|M/s|Mt|Md|Mohd|[A-Z])\.?$")
_INITIALS = re.compile(r"^(?:[A-Z]\.){1,5}[A-Z]?\.?$")
_VS = re.compile(r"(?<=[\s,(])(?:v|vs|versus)\.?(?=\s)", re.I)
_YEAR_AFTER = re.compile(r"^[^A-Za-z0-9]{0,6}(?:\(\s*((?:19|20)\d\d)\s*\)|(?:AIR|SCC|SCR|INSC)?\s*((?:19|20)\d\d)\b|\[\s*((?:19|20)\d\d)\s*\])")
_LEAD_STOP = frozenset("in see also vide and compare cf following per thus hence held case cases of the like court judgment decision observed said view relied reference reported".split())


def party_tokens(s):
    s = re.sub(r"\([^)]*\)?", " ", s or "")
    s = re.split(r"@|\balias\b|\bthrough\b|\bthr\.?\b|\brepresented\b|\bs/o\b|\bd/o\b|\bw/o\b|\bson of\b", s, flags=re.I)[0]
    s = s.lower().replace("’", "'")
    s = re.sub(r"\b" + _HON + r"\b\.?", " ", s)
    return [t for t in re.findall(r"[a-z]+", s) if t not in _DROPW]


def _is_name_tok(t):
    core = t.strip(",;:()[]\"'‘’“”")
    if not core or core.isdigit() or re.match(r"^[\(\[]\s*\d", t):                       # "(1984)" and "[2010]" after a name are a year, not part of the name
        return False
    return bool(re.match(r"^" + _CONNECT + r"$", core, re.I) or re.match(r"^[A-Z@(\[]", t) or re.match(r"^[A-Z]", core))


def _left(text, pos):
    toks = text[max(0, pos - 160):pos].rstrip().split()
    out = []
    for t in reversed(toks):
        if not _is_name_tok(t):
            break
        core = t.strip(",;:()[]\"'‘’“”")
        out.append(t)
        if re.search(r"[;:]$", t) or (t.endswith(".") and len(core) > 3 and not _INITIALS.match(core) and not _ABBR.match(core)):
            out.pop()
            break
        if len(out) >= 9:
            break
    return list(reversed(out))


def _right(text, pos):
    toks = text[pos:pos + 160].lstrip().split()
    out = []
    for t in toks:
        if not _is_name_tok(t):
            break
        core = t.strip(",;:()[]\"'‘’“”")
        out.append(t)
        if re.search(r"[,;:)]$", t) or (t.endswith(".") and len(core) > 3 and not _INITIALS.match(core) and not _ABBR.match(core)):
            break
        if len(out) >= 8:
            break
    return out


def mentions(text):
    """[(first-party tokens, second-party key, year or None)] for every 'X v. Y' in `text`."""
    res = []
    for m in _VS.finditer(text or ""):
        left, right = _left(text, m.start()), _right(text, m.end())
        if not left or not right:
            continue
        t1 = party_tokens(" ".join(left))
        t2 = party_tokens(" ".join(right))
        if not t1 or not t2:
            continue
        ym = _YEAR_AFTER.match(text[m.end() + len(" ".join(right)) + 1:m.end() + len(" ".join(right)) + 40])
        year = int(next(g for g in ym.groups() if g)) if ym else None
        res.append((t1, "".join(t2[:3]), year))
    return res


def doc_keys(name):
    """The keys a judgment is known by: [(squashed first party, first three words of the second party)] from its 'X v. Y' name (also with only the first of several petitioners)."""
    if not name or not re.search(r"\sv\.?\s", name, re.I):
        return []
    p1, p2 = re.split(r"\sv\.?\s", name, maxsplit=1, flags=re.I)
    t2 = party_tokens(p2)
    if not t2:
        return []
    ks, seen = [], set()
    firsts = [p1] + [x for x in re.split(r",|\band\b|&", p1) if len(x.strip()) > 3]
    for f in firsts:
        t1 = party_tokens(f)
        if t1 and "".join(t1) not in seen:
            seen.add("".join(t1))
            ks.append(("".join(t1), "".join(t2[:3])))
    return ks


class Resolver:
    def __init__(self, names):
        """names: {doc: {'name':..., 'year':..., 'date':...}}"""
        self.year = {d: (r.get("year") or (int(r["date"][:4]) if r.get("date") else None)) for d, r in names.items()}
        self.by_pair = collections.defaultdict(set)
        self.by_first = collections.defaultdict(set)
        for d, r in names.items():
            for k1, k2 in doc_keys(r.get("name")):
                self.by_pair[(k1, k2)].add(d)
                self.by_first[k1].add(d)

    def _pick(self, docs, year, citing_year=None):
        """Which judgments of one pair of names a mention means. A mention with a year (or a citation) is matched to a case decided within a year of it. Without one: cases of the same name decades apart are told apart
        by taking the latest not later than the citing judgment (the usual meaning of "Tofan Singh v. State of Tamil Nadu" in a 2022 judgment is the 2020 decision, not the 2013 reference order); a lone case is taken
        as it stands."""
        docs = set(docs)
        ys = {d: self.year.get(d) for d in docs}
        if year:
            return {d for d in docs if ys[d] is None or abs(ys[d] - year) <= 2}
        known = [y for y in ys.values() if y]
        if len(docs) > 1 and known and max(known) - min(known) > 2:
            ok = [d for d in docs if ys[d] and (not citing_year or ys[d] <= citing_year)]
            if not ok:
                return set()
            best = max(ys[d] for d in ok)
            return {d for d in ok if abs(ys[d] - best) <= 2}
        return docs

    def resolve(self, t1, k2, year=None, citing_year=None):
        """The judgments a mention stands for ({} when unsure)."""
        for j in range(min(len(t1), 8)):
            k1 = "".join(t1[j:])
            if len(k1) < 5:
                break
            hit = self.by_pair.get((k1, k2))
            if hit:
                return self._pick(hit, year, citing_year)
        for j in range(min(len(t1), 8)):
            k1 = "".join(t1[j:])
            if len(k1) >= 12 and k1 in self.by_first and t1[j] not in _GENERIC_WORDS:
                docs = self.by_first[k1]                          # a distinctive first party named without its second party: only if it belongs to one case (the same case held twice is one case)
                ys = [self.year.get(d) for d in docs if self.year.get(d)]
                if len(docs) <= 4 and (not ys or max(ys) - min(ys) <= 2):
                    return self._pick(docs, year, citing_year)
                return set()
        return set()


_GENERIC_WORDS = frozenset("""state union central govt government commissioner collector director directorate superintendent inspector bureau enforcement national registrar station public police cbi home ministry secretary
chief district sessions magistrate bank municipal corporation board authority committee commission tribunal university institute company assistant deputy additional joint senior principal high supreme emperor crown king
queen india amicus curiae food income customs excise narcotics delhi punjab bihar uttar madhya andhra tamil west kerala gujarat maharashtra karnataka rajasthan haryana assam orissa odisha bengal himachal jharkhand
chhattisgarh uttarakhand telangana goa manipur tripura meghalaya mizoram nagaland sikkim jammu kashmir bombay madras calcutta mumbai chennai kolkata officer official administration railway railways insurance
revenue municipality panchayat council society trust committee commissioner collectorate general advocate attorney solicitor prosecutor court judge""".split())
_JUDGE_AFTER = re.compile(r"^\s*,?\s*(?:J{1,2}\.?|C\.J\.?|CJI|JJ\.)(?![A-Za-z])")
_WORD = re.compile(r"[A-Za-z]+")
_BEFORE_OK = re.compile(r"(?:\bin|\bby|\bof|\bvide|\bsee|\bcf\.?|\bcase|\bdecision|\bjudgment|\bruling|\bheld|\bobserved|\bfollowed|\bapproved|\bdistinguished|\bunlike|\blike|\bin the)\s+(?:the\s+|case\s+of\s+)?$", re.I)
_AFTER_OK = re.compile(r"^\s*(?:\(\s*supra\s*\)|supra\b|['\u2019]s\s+case|\bcase\b|\(\s*(?:19|20)\d\d\s*\)|(?:19|20)\d\d\b|\[\s*(?:19|20)\d\d|AIR\b|SCC\b|SCR\b|\(\s*[IVX]+\s*\)|\bdecision\b|\bjudgment\b|\bruling\b)", re.I)


def doc_signature_keys(name):
    """The squashed names a judgment is known by in running text: its distinctive party (the second party when the first is a State, the Union or another body that many cases share; no name at all when both
    are), at least seven letters. [(squashed name, number of words)]"""
    if not name or not re.search(r"\sv\.?\s", name, re.I):
        return []
    p1, p2 = re.split(r"\sv\.?\s", name, maxsplit=1, flags=re.I)
    t1 = party_tokens(re.split(r",| and |&", p1)[0])
    t2 = party_tokens(re.split(r",| and |&", p2)[0])
    if t1 and t1[0] not in _GENERIC_WORDS:
        toks = t1
    elif t2 and t2[0] not in _GENERIC_WORDS:
        toks = t2
    else:
        return []
    out = []
    for n in (len(toks), min(len(toks), 4)):
        sq = "".join(toks[:n])
        if len(sq) >= 7 and n <= 5 and (sq, n) not in out:
            out.append((sq, n))
    return out


def clusters(names):
    """doc -> cluster id: the same case held twice (same distinctive name and same second party, decided within two years of each other) is one case."""
    byk = collections.defaultdict(list)
    for d, r in names.items():
        keys = doc_signature_keys(r.get("name"))
        if not keys:
            continue
        p2 = re.split(r"\sv\.?\s", r["name"], maxsplit=1, flags=re.I)[1]
        byk[(keys[0][0], "".join(party_tokens(p2)[:3]), r.get("court"))].append(d)
    cid = {}
    year = lambda d: (names[d].get("year") or (int(names[d]["date"][:4]) if names[d].get("date") else None))
    for key, docs in byk.items():
        docs = sorted(docs, key=lambda d: (year(d) or 0, d))
        cur = []
        groups = []
        for d in docs:
            if cur and year(d) and year(cur[-1]) and abs(year(d) - year(cur[-1])) > 2:
                groups.append(cur); cur = []
            cur.append(d)
        if cur:
            groups.append(cur)
        for g in groups:
            for d in g:
                cid.setdefault(d, g[0])
    for d in names:
        cid.setdefault(d, d)
    return cid


def scan(metas, names, strict_min=3, bare=True):
    """Everything in one pass over the passages. Returns ({citing doc: {cited cluster ids}}, cluster map, stats)."""
    res = Resolver(names)
    cid = clusters(names)
    year = lambda d: (names[d].get("year") or (int(names[d]["date"][:4]) if names[d].get("date") else None)) if d in names else None
    cites = collections.defaultdict(set)
    strict_citers = collections.defaultdict(set)
    n_men = n_res = 0
    t0 = time.time()
    for m in metas:
        for t1, k2, y in mentions(m["text"]):
            n_men += 1
            docs = res.resolve(t1, k2, y, year(m['doc']))
            if docs:
                n_res += 1
                for d in docs:
                    if d != m["doc"] and cid[d] != cid.get(m["doc"]):
                        cites[m["doc"]].add(cid[d])
                        strict_citers[cid[d]].add(m["doc"])
    stats = {"mentions": n_men, "resolved": n_res, "strict_seconds": round(time.time() - t0, 1)}
    if bare:
        sig = collections.defaultdict(set)                # squashed name -> cluster ids, only for cases cited by full name at least `strict_min` times
        for d, r in names.items():
            if len(strict_citers.get(cid[d], ())) < strict_min:
                continue
            for sq, n in doc_signature_keys(r.get("name")):
                if (n >= 2 and len(sq) >= 9) or len(sq) >= 10:
                    sig[sq].add(cid[d])
        sig = {k: v for k, v in sig.items() if len(v) == 1}          # a name that belongs to two different cases is not used bare
        sig_n = {}
        for d, r in names.items():
            for sq, n in doc_signature_keys(r.get("name")):
                if sq in sig:
                    sig_n[sq] = n
        pref = {sq[:4] for sq in sig}                       # a window of words can only be a name if its first four letters are the first four letters of a name
        maxn = min(max(sig_n.values()) if sig_n else 0, 5)
        t1_ = time.time()
        n_bare = 0
        for m in metas:
            text = m["text"]
            ws = [(w.group(0).lower(), w.end(), w.start()) for w in _WORD.finditer(text)]
            citing = m["doc"]
            cy = year(citing)
            ccl = cid.get(citing)
            for i in range(len(ws)):
                head = "".join(w[0] for w in ws[i:i + 3])
                if head[:4] not in pref:
                    continue
                acc = ""
                for n in range(1, maxn + 1):
                    if i + n > len(ws):
                        break
                    acc += ws[i + n - 1][0]
                    if len(acc) > 40:
                        break
                    cl = sig.get(acc)
                    if not cl:
                        continue
                    c = next(iter(cl))
                    if c == ccl:
                        continue
                    cyr = year(c)
                    if cyr and cy and cyr > cy:
                        continue                               # a case cannot be cited by an earlier judgment
                    end_pos = ws[i + n - 1][1]
                    if _JUDGE_AFTER.match(text[end_pos:end_pos + 12]):
                        continue
                    if not (_AFTER_OK.match(text[end_pos:end_pos + 24]) or _BEFORE_OK.search(text[max(0, ws[i][2] - 24):ws[i][2]])):
                        continue                               # a bare name counts only in the way a case is cited ("in X (supra)", "the decision in X"), not as a party's name in the facts
                    cites[citing].add(c)
                    n_bare += 1
        stats.update({"bare_mentions": n_bare, "bare_signatures": len(sig), "bare_seconds": round(time.time() - t1_, 1)})
    return cites, cid, stats


def build_table(cites, cid, names, index_commit, stats):
    """The table the search service loads (schema authority-table-2). Counts are per cluster; a judgment of a cluster carries the cluster's count."""
    counts = collections.Counter()
    for citing, cl in cites.items():
        for c in cl:
            counts[c] += 1
    members = collections.defaultdict(list)
    for d, c in cid.items():
        members[c].append(d)
    cited_by = {str(d): counts[c] for c, docs in members.items() for d in docs if counts[c]}
    return {"schema": "authority-table-2", "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "index_commit": index_commit, "documents_with_citations": len(cited_by), "citing_documents": len(cites),
            "method": "case names found in passage text, matched to judgments of the index by party names (strict); counts are distinct OTHER judgments of the index; not a statement that a case is good law; see authority_graph.py",
            "stats": stats, "cited_by": cited_by, "cluster": {str(d): c for d, c in cid.items() if c != d}, "cites": {str(d): sorted(v) for d, v in cites.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--index-dir", required=True)
    b.add_argument("--names", required=True)
    b.add_argument("--side", action="append", default=[])
    b.add_argument("--out", required=True)
    s_ = sub.add_parser("show")
    s_.add_argument("table")
    s_.add_argument("--names")
    s_.add_argument("--top", type=int, default=40)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import sci_index as si
        nm = json.load(gzip.open(a.names, "rt", encoding="utf-8"))
        names = {r["doc"]: r for r in nm["rows"] if r.get("name")}
        metas = []
        for d in [a.index_dir] + a.side:
            mm, _M, _ = si._load_index(d)
            metas += [{"doc": m["doc"], "text": m["text"]} for m in mm]
        cites, cid, stats = scan(metas, names)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with gzip.open(a.out, "wt", encoding="utf-8") as fh:
            json.dump(build_table(cites, cid, names, nm.get("index_commit"), stats), fh, separators=(",", ":"))
        print(stats, "->", a.out, f"({os.path.getsize(a.out) / 1e6:.1f} MB)")
        return 0
    t = json.load(gzip.open(a.table, "rt", encoding="utf-8"))
    names = {}
    if a.names:
        names = {r["doc"]: r for r in json.load(gzip.open(a.names, "rt", encoding="utf-8"))["rows"]}
    print(f"table for index {str(t.get('index_commit'))[:10]}: {t['documents_with_citations']:,} judgments named at least once by {t['citing_documents']:,} judgments that name others")
    for d, n in sorted(t["cited_by"].items(), key=lambda x: -x[1])[:a.top]:
        print(f"{n:>5}  {d:>12}  {(names.get(int(d)) or {}).get('name', '')[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
