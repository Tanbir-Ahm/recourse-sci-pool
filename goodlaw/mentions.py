"""Finds the later judgments that cite a target case, and where.

A target is a case (parties, year, known reporter citations). Three kinds of evidence say a later judgment is talking about it, strongest first:

  cite    the text contains one of the target's reporter citations (its AIR page, its SCR page, its SCC page, its neutral citation)
  pair    the text names both parties together ("Rangappa v. Sri Mohan"); dropped if a citation follows that belongs to a different case
  short   the text uses a distinctive party name alone ("Rangappa", "Bhajan Lal's case"); medium confidence in a text that also has a cite or
          pair hit, low confidence in a text that does not

Citations the target is not yet known by are learned: when the pair is followed by a citation of a compatible year in two or more texts, that
citation is added to the target (and reported), and texts that cite it without naming the parties are found too.

Every mention carries the sentence it is in (and its neighbours), who is speaking (the court, counsel, a lower court, the law report's headnote),
and the citing judgment's date and bench. The target's own text and second copies are never counted.
"""
import collections
import re

from . import cites as C
from .textutil import flatten, paragraph_number, sentence_index, sentences

_NOISE_TAIL = re.compile(r"\(\s*(?:dead|deceased|since deceased)[^)]*\)|\bthrough\b.*$|\bby (?:his |her |their )?(?:l\.?rs?\.?|legal representatives?)\b.*$|"
                         r"\b(?:and|&)\s+(?:ors|anr|another|others|anrs)\b\.?.*$|\b(?:ors|anr|anrs)\b\.?.*$|\betc\.?.*$|\(.*?\)", re.I)
_PREFIX = re.compile(r"^(?:m/s\.?|messrs\.?|shri|sri|smt\.?|dr\.?|mr\.?|mrs\.?|the)\s+", re.I)
_COMMON = {"state", "union", "india", "of", "the", "and", "company", "corporation", "limited", "ltd", "pvt", "private", "commissioner", "collector", "board",
           "municipal", "committee", "government", "authority", "department", "bank", "singh", "kumar", "sharma", "gupta", "devi", "lal", "ram", "chand", "das", "rao",
           "reddy", "khan", "ali", "shah", "prasad", "nath", "pradesh", "bihar", "punjab", "haryana", "gujarat", "maharashtra", "kerala", "delhi"}


_LEADING_NUMBER = re.compile(r"^(?:[A-Za-z. ]{0,20}\bNo\.?\s*[\d/-]+\s*\)\s*|[\d/-]{3,}\s*\)\s*)", re.I)   # a case number left on the front of a title: "No. 6290/2007) American Hotel ..."


def clean_party(name):
    s = _LEADING_NUMBER.sub("", name or "")
    s = _NOISE_TAIL.sub(" ", s)
    s = _PREFIX.sub("", s.strip())
    return re.sub(r"\s+", " ", s).strip(" .,;:-&")


def party_words(name, limit=6):
    return re.findall(r"[A-Za-z0-9]+", clean_party(name))[:limit]


def _words_regex(words):
    return r"\W+".join(re.escape(w) for w in words)


class Target:
    def __init__(self, pet, resp, year, cites=(), date=None, doc_key=None, bench_size=None, name=None, aliases=(), bench_source=None):
        self.pet, self.resp, self.year, self.date = pet, resp, year, date
        self.bench_source = bench_source
        self.cites = list(cites)
        self.doc_key, self.bench_size = doc_key, bench_size
        self.name = name or f"{pet} v. {resp}"
        self.aliases = list(aliases)         # extra short names to search for, e.g. ["Koushal"]
        self.learned_cites = []

    @classmethod
    def from_doc(cls, doc):
        pet, resp = doc.get("pet"), doc.get("resp")
        if (not pet or not resp) and doc.get("title") and re.search(r"\s(?:v\.?|vs\.?|versus)\s", doc["title"], re.I):
            pet, resp = re.split(r"\s(?:v\.?|vs\.?|versus)\s", doc["title"], maxsplit=1, flags=re.I)
        return cls(pet or "", resp or "", doc.get("year"), doc.get("cites") or [], doc.get("date"), doc.get("doc_key"), doc.get("bench_size"), doc.get("title"), bench_source=doc.get("bench_source"))

    def all_cites(self):
        return self.cites + [c for c in self.learned_cites if c not in self.cites]

    def pair_regex(self):
        pw, rw = party_words(self.pet), party_words(self.resp)
        if not pw or not rw:
            return None
        honorific = r"(?:(?:m/s|messrs|shri|sri|smt|dr|mr|mrs|the)\W{0,3})?"
        return re.compile(rf"{_words_regex(pw)}\W{{1,6}}(?:v|vs|versus)\W{{1,4}}{honorific}{_words_regex(rw)}", re.I)

    def party_case_patterns(self, corpus=None, max_df=600):
        """Patterns for a party's name followed by 'case', 'decision', 'judgment', 'ruling' or '(supra)', e.g. "University of Delhi case" or "Chhotabhai
        Jethabhai's case". Used only when the party's phrase is unusual enough in the corpus (not "State of Punjab")."""
        out = []
        for party in (self.pet, self.resp):
            words = party_words(party, limit=5)
            if not words:
                continue
            if len(words) == 1 and (len(words[0]) < 5 or words[0].lower() in _COMMON):
                continue
            if corpus is not None and corpus.phrase_df(" ".join(words)) > max_df:
                continue
            out.append((" ".join(words), re.compile(rf"\b{_words_regex(words)}(?:['’]s)?\W{{0,3}}(?:case|decision|judgment|ruling|\(supra\)|\(\d\))", re.I)))
            # a later reference often drops the end of a long name: "Assam Small Scale Industries (supra)" for "Assam Small Scale Ind. Dev. Corp. Ltd."; only the explicit "(supra)" counts for these shorter forms
            for n in (3, 2):
                if len(words) > n:
                    head = words[:n]
                    if len(" ".join(head)) < 9 or head[0].lower() in _COMMON:
                        continue
                    if corpus is not None and corpus.phrase_df(" ".join(head)) > max_df:
                        continue
                    out.append((" ".join(head), re.compile(rf"\b{_words_regex(head)}(?:\W+[A-Za-z.&]+){{0,3}}?\W{{0,3}}\(supra\)", re.I)))
        return out

    def short_names(self, corpus=None, max_df=300):
        """Distinctive single names to look for alone: a party's first or last word that is rare in the corpus and not a stock name."""
        out = []
        for a in self.aliases:
            if a not in out:
                out.append(a)
        for party in (self.pet, self.resp):
            words = party_words(party)
            for w in words:
                lw = w.lower()
                if len(w) < 5 or lw in _COMMON or not w.isalpha():
                    continue
                if corpus is not None and corpus.doc_frequency(lw) > max_df:
                    continue
                if w not in out:
                    out.append(w)
        return out


# ---------------------------------------------------------------- who is speaking
_COUNSEL = re.compile(r"\b(?:(?:reliance|stand|plea|grievance|contention|argument|submission|case) (?:placed )?(?:of|by|taken by) (?:Mr|Ms|Mrs|Shri|Dr)\.? [A-Z]\w*|(?:stand|plea|case|contention|submission|argument) of the (?:State|appellants?|respondents?|petitioners?|Union|Government|Revenue|Department)\b|learned (?:senior )?(?:counsel|advocate|amicus|Additional Solicitor General|Solicitor General|Attorney General)|(?:the )?(?:Attorney|Solicitor|Advocate)[- ]General (?:referred|submitted|contended|urged|argued|relied|pointed|placed|wanted)|"
                      r"(?:Mr|Ms|Mrs|Dr|Shri|Sri)\.? [A-Z][\w.]*(?: [A-Z][\w.]*)*,? (?:learned )?(?:senior )?(?:counsel|advocate)|"
                      r"(?:arguments?|submissions?|contentions?) (?:in support of|advanced|addressed)|in support of the (?:submission|contention)|addressed (?:elaborate |lengthy |detailed )?arguments|appearing (?:also )?for the|"
                      r"submitted that|submits that|contended that|contends that|argued that|argues that|urged that|urges that|placed (?:strong )?reliance|"
                      r"relied (?:heavily )?upon by|on behalf of the (?:appellant|respondent|petitioner|State|accused|complainant)|according to the (?:appellant|respondent|petitioner|learned)|"
                      r"it was (?:submitted|contended|argued|urged|pleaded)|it is (?:submitted|contended|argued|urged)|the (?:appellant|respondent|petitioner)s? (?:also )?(?:submitted|contended|argued|urged|relied|placed reliance))\b", re.I)
_LOWER = re.compile(r"\b(?:the )?(?:High Court|Trial Court|trial court|Sessions Court|Sessions Judge|learned (?:Single )?Judge|Division Bench of the High Court|Tribunal|impugned (?:judgment|order)|Magistrate)\b[^.]{0,80}\b(?:held|observed|relied|noted|took the view|has held|opined|concluded|found|dismissed|allowed|rejected|negatived|repelled)\b", re.I)
_COURT_VOICE = re.compile(r"\b(?:we|this Court|our (?:view|opinion|considered)|in our|we are|we hold|we find|we may|we have|having regard|therefore|thus|accordingly|It is settled|it is well settled)\b", re.I)


def speaker(sent, prev_sent, in_headnote):
    """('headnote' | 'counsel' | 'lower_court' | 'court', cue). The court is the default; counsel and lower courts are recognised by their usual phrases in the
    sentence (or, for counsel, in the sentence before when this one has no court-voice phrase)."""
    if in_headnote:
        return "headnote", "before the court's own judgment begins"
    m = _COUNSEL.search(sent)
    if m:
        return "counsel", m.group(0)
    m = _LOWER.search(sent)
    if m:
        return "lower_court", m.group(0)[:60]
    m = _COUNSEL.search(prev_sent or "")
    if m and not _COURT_VOICE.search(sent):
        return "counsel", f"(previous sentence) {m.group(0)}"
    return "court", None


# ---------------------------------------------------------------- mentions in one text
_RANK = {"cite": 0, "pair": 1, "short": 2}


def _merge(raw):
    """Overlapping hits are one mention: the union of their spans, labelled with the strongest kind (cite, then pair)."""
    out = []
    for s, e, tier, detail in sorted(raw):
        if out and s <= out[-1][1]:
            ps, pe, ptier, pdetail = out[-1]
            best_tier, best_detail = (ptier, pdetail) if _RANK[ptier] <= _RANK[tier] else (tier, detail)
            out[-1] = (ps, max(pe, e), best_tier, best_detail if best_detail else (pdetail or detail))
        else:
            out.append((s, e, tier, detail))
    return out


SERIES_OK = ("scc", "air", "scr", "scale", "jt", "sconline", "insc", "scccri")


def _compatible_year(key, year):
    """A citation after the parties' names can belong to the target if its reporter year is the decision year or up to three years later
    (an SCC volume can come out a year or two after the decision: Bhajan Lal, decided in 1990, is 1992 Supp (1) SCC 335)."""
    try:
        y = C.parse_key(key)[1]
    except Exception:
        return False
    return year is None or -1 <= y - int(year) <= 3


_NAME_BEFORE_CITE = re.compile(r"((?:[A-Z][\w.&'()/-]*,?\s+){1,8}(?:v\.?|vs\.?|versus)\s+(?:[A-Z][\w.&'()/-]*,?\s+){1,10})$")


def _name_start(flat, s):
    """Where a citation's mention begins: at the case name just before it ("Town Municipal Council, Athani v. Presiding Officer, Labour Court, [1970] 1 SCR 51"),
    so that the cue reading sees the name and the citation as one reference and not as a name followed by a comma and a separate citation."""
    window = flat[max(0, s - 160):s]
    hit = _NAME_BEFORE_CITE.search(window)
    return s - (len(window) - hit.start(1)) if hit else s


def extract(text, target, short_names=(), body_start=None, known_cites=None, party_cases=()):
    """Mentions of the target in one text -> (list of mention dicts, {citation key: votes} for citations seen right after the pair)."""
    flat = flatten(text)
    spans = sentences(flat)
    cites = C.find_cites(flat)
    known = set(known_cites if known_cites is not None else target.all_cites())
    raw = []          # (start, end, tier, detail)
    conflict = []     # spans where the parties' names are followed by another case's citation
    votes = collections.Counter()
    for key, s, e in cites:
        if any(C.keys_match(key, k) for k in known):
            raw.append((_name_start(flat, s), e, "cite", key))
    pair = target.pair_regex()
    if pair:
        for m in pair.finditer(flat):
            s, e = m.start(), m.end()
            after = [(k, a, b) for k, a, b in cites if 0 <= a - e <= 90]
            if after:
                k = after[0][0]
                if any(C.keys_match(k, kk) for kk in known):
                    raw.append((s, after[0][2], "pair", k))
                    continue
                if not _compatible_year(k, target.year):
                    conflict.append((s, after[0][2]))
                    continue              # same names, a different case: someone else's citation follows
                if k.split(":")[0] in SERIES_OK:
                    votes[k] += 1
            raw.append((s, e, "pair", None))
    # parallel citations: "(1976) 2 SCC 521 : [1976] Suppl. SCR 172" next to a citation the target is known by is the same case, whatever the name says
    for key, s_, e_ in cites:
        if not any(C.keys_match(key, k) for k in known):
            continue
        for key2, s2, e2 in cites:
            if key2 == key or any(C.keys_match(key2, k) for k in known):
                continue
            gap = flat[e_:s2] if s2 >= e_ else (flat[e2:s_] if e2 <= s_ else None)
            if gap is not None and len(gap) <= 12 and re.fullmatch(r"[\s:;,=/]*(?:and|or)?[\s:;,=/]*", gap) and _compatible_year(key2, target.year) and key2.split(":")[0] in SERIES_OK:
                votes[key2] += 1
    votes = collections.Counter({k: 1 for k in votes})          # one vote per text, so a long judgment cannot outvote the rest
    raw = _merge(raw)
    shorts = []
    for name in short_names:
        for m in re.finditer(rf"\b{re.escape(name)}(?:['’]s)?\b", flat, re.I):
            shorts.append((m.start(), m.end(), "short", name))
    for phrase, rx in party_cases:
        for m in rx.finditer(flat):
            shorts.append((m.start(), m.end(), "short", phrase))
    # an explicit pair or cite hit can swallow a short-name hit at the same place
    covered = [(s, e) for s, e, _, _ in raw]
    shorts = [x for x in shorts if not any(s <= x[0] and x[1] <= e + 3 for s, e in covered + conflict)]
    has_strong = bool(raw)
    raw += shorts
    raw.sort()
    flat_body_start = len(flatten(text[:body_start])) if body_start else None
    out, last_sent_span = [], set()
    for s, e, tier, detail in raw:
        i = sentence_index(spans, s)
        if (i, tier) in last_sent_span and tier == "short":
            continue
        last_sent_span.add((i, tier))
        a, b = spans[i]
        prev = flat[spans[i - 1][0]:spans[i - 1][1]] if i > 0 else ""
        nxt = flat[spans[i + 1][0]:spans[i + 1][1]] if i + 1 < len(spans) else ""
        in_head = flat_body_start is not None and s < flat_body_start
        who, cue = speaker(flat[a:b], prev, in_head)
        confidence = "high" if tier in ("cite", "pair") else ("medium" if has_strong else "low")
        out.append({"tier": tier, "confidence": confidence, "detail": detail, "start": s, "end": e, "sentence": flat[a:b], "target_in_sentence": (max(0, s - a), min(b - a, e - a)),
                    "prev": prev, "next": nxt, "speaker": who, "speaker_cue": cue, "in_headnote": in_head, "matched": flat[s:e]})
    return out, votes


# ---------------------------------------------------------------- across the corpus
def _later(doc, target):
    """True if the citing doc is later than the target. Same year with no exact dates is not later (unknown order); same year with both dates is."""
    if doc.get("doc_key") == target.doc_key:
        return False
    if target.date and doc.get("date") and doc.get("date_source") in ("header", "tail_place", "bucket"):
        return doc["date"] > target.date
    if target.year and doc.get("year"):
        return doc["year"] > target.year
    return False


def find_mentions(corpus, target, learn=True, min_votes=2, log=None):
    """-> dict(mentions=[...], citing_docs=n, learned_cites=[...], by_tier={...}). Mentions come sorted by date of the citing judgment."""
    short = target.short_names(corpus)
    pcases = target.party_case_patterns(corpus)
    cand = {}

    def add(docs, why):
        for d in docs:
            if _later(d, target) and d["doc_key"] not in cand:
                cand[d["doc_key"]] = (d, why)

    if target.all_cites() and corpus.has_cite_index:
        add(corpus.docs_citing(target.all_cites()), "cite")
    pw, rw = party_words(target.pet), party_words(target.resp)
    if pw and rw:
        def rare(words):
            ws = [w.lower() for w in words if len(w) > 2 and w.isalnum()]
            return min(ws, key=lambda w: corpus.doc_frequency(w) or 10**9) if ws else None
        a, b = rare(pw), rare(rw)
        if a and b and a != b:
            add(corpus.search(f'NEAR("{a}" "{b}", 14)'), "pair")
        elif a:
            add(corpus.search(f'"{a}"'), "pair")
    for name in short:
        add(corpus.search(f'"{name.lower()}"'), "short")
    for phrase, _ in pcases:
        add(corpus.search(f'"{phrase.lower()}"'), "short")
    for key in [k for k, (d, _) in cand.items() if d.get("maybe_dup_of") and d["maybe_dup_of"] in cand]:
        del cand[key]          # a bucket text that may be a second copy of a crawl text already among the candidates is not counted twice
    if log:
        log(f"{len(cand)} candidate texts")
    mentions, votes_total = [], collections.Counter()
    texts = {}
    for key, (d, why) in cand.items():
        text = corpus.text_of(d["id"])
        texts[key] = text
        found, votes = extract(text, target, short, d.get("body_start"), party_cases=pcases)
        votes_total.update(votes)
        for m in found:
            m["doc_key"], m["doc_id"] = d["doc_key"], d["id"]
            m["date"], m["year"], m["date_source"] = d["date"], d["year"], d["date_source"]
            m["bench_size"], m["bench_source"], m["source"], m["title"] = d["bench_size"], d["bench_source"], d["source"], d["title"]
            m["citing_cites"] = d["cites"]
            mentions.append(m)
    learned = []
    if learn:
        learned = [k for k, v in votes_total.most_common() if v >= min_votes and k not in target.all_cites()]
        if learned:
            target.learned_cites = learned
            if corpus.has_cite_index:
                extra = [d for d in corpus.docs_citing(learned) if _later(d, target) and d["doc_key"] not in cand and d.get("maybe_dup_of") not in cand]
                for d in extra:
                    text = corpus.text_of(d["id"])
                    found, _ = extract(text, target, short, d.get("body_start"), party_cases=pcases)
                    for m in found:
                        m["doc_key"], m["doc_id"] = d["doc_key"], d["id"]
                        m["date"], m["year"], m["date_source"] = d["date"], d["year"], d["date_source"]
                        m["bench_size"], m["bench_source"], m["source"], m["title"] = d["bench_size"], d["bench_source"], d["source"], d["title"]
                        m["citing_cites"] = d["cites"]
                        mentions.append(m)
    mentions.sort(key=lambda m: (m["date"] or f"{m['year']}-12-31", m["doc_key"], m["start"]))
    docs = {m["doc_key"] for m in mentions}
    by_tier = collections.Counter(m["tier"] for m in mentions)
    confident_docs = {m["doc_key"] for m in mentions if m["confidence"] == "high"}
    for m in mentions:
        if m["tier"] == "short" and m["doc_key"] in confident_docs:
            m["confidence"] = "medium"
    return {"mentions": mentions, "citing_docs": len(docs), "citing_docs_high": len(confident_docs), "learned_cites": learned, "by_tier": dict(by_tier)}
