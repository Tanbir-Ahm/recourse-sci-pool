"""From a search hit to the passage the chat formatter takes (goodlaw/chat_format.py): who the judgment is, which paragraph and page, and the text, word for word.

Offline: it reads rows the search already returned and records the checker's corpus (or the index's own document records) already hold. It searches nothing, fetches nothing and sends nothing.

    docs = IndexDocs.load("path/to/sci-index-checkout")             # the index's document records (only those that carry a title)
    who = ChainIdentity(CorpusIdentity(Corpus("corpus.sqlite"), docs), IndexRowIdentity(docs))
    passage = passage_from_hit(hit, who)                            # hit: an index passage row {doc, i, pn, page, section, h, text}
    message = formatter.format(passage, intro=True)

Why the identity comes from the corpus and not from the index: the index keeps a title only for bucket judgments (2017 onwards) and for the old CASE NO / PETITIONER / RESPONDENT layout. Checked on the
real index on 2026-10-22: the crawl judgments (most of it) carry no title, no date and no citation in their document records. The checker's corpus (goodlaw/corpus.py) has all of them, and is what the
register and the cards were built against, so a hit is matched to a case the same way they are: doc `c<id>` for a crawl judgment, `b<path>` for a bucket one (the path is in the index's record).

What it will not do:
  * It never guesses a title. A judgment it cannot name comes out as `identified: False`, and the formatter then says "Not checked by us ... we could not identify which judgment this passage comes from"
    instead of "no register entry", which would be untrue because nothing was looked up. (pool_runner.titles falls back to the opening header text; that is not a case name and is not used here.)
  * It never changes the passage, apart from replacing stray control characters (form feeds and the like, which PDF text carries) with a space. `source_info.text_changed` says when that happened.
  * It states a year only as the corpus gives it, and says in `source_info.notes` when the corpus estimated it (neighbouring judgments) instead of reading it from the judgment.
  * A passage's tag from the index ("facts", "argument", "order", "header", "statute_text") becomes a cautious plain-words label ("Appears to record counsel's arguments, not the Court's view");
    "reasoning" gets no label, because the tag is a heuristic and the label must not suggest that the passage is the Court's own holding. A passage tagged reasoning can still recite a lower court.
  * No link is built unless the caller gives `link_for` (the court's PDF link has not been tested from a user's side); `doc_id` is added only with `open_action=True`.
"""
import glob
import gzip
import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from . import cites as C
from . import corpus as K

BUCKET_BASE = 1_000_000_000          # sci_index.BUCKET_BASE: an index doc id at or above it is a bucket judgment, below it a crawl judgment
MAX_CITES = 4                        # reported citations passed on from a corpus row

KIND_LABELS = {
    "facts": "Appears to recite the facts, or what a lower court held",
    "argument": "Appears to record counsel's arguments, not the Court's view",
    "order": "Appears to be part of the operative order",
    "header": "Case header, not reasoning",
    "statute_text": "Appears to quote a statute",
}
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_PN = re.compile(r"^(\d+[A-Za-z]?)(?:-(\d+[A-Za-z]?))?(?:/\d+)?$")
_VERSUS = re.compile(r"\s+(?:versus|vs\.?)\s+", re.I)


@dataclass(frozen=True)
class Identity:
    name: str                        # "Petitioner v. Respondent"
    year: Optional[int]
    citation: str                    # reported citations as text the register and the cards can read ("(2018) 17 SCC 627 ; 2019 INSC 5"); may be empty
    date: Optional[str] = None       # ISO
    name_source: str = ""            # corpus, index_bucket_title or index_case_header
    date_source: Optional[str] = None
    doc_key: Optional[str] = None
    notes: tuple = ()


# ---- small readers --------------------------------------------------------------------------------------------------------------------------------------------------------------
def para_label(pn):
    """'14' -> '14'; '1-3' (a merged run of short paragraphs) -> '1-3'; '14/2' (a long paragraph split in pieces) -> '14'; 'preamble' or nothing -> None."""
    if pn is None:
        return None
    m = _PN.match(str(pn).strip())
    return (m.group(1) + (f"-{m.group(2)}" if m.group(2) else "")) if m else None


def page_label(page):
    try:
        n = int(page)
    except (TypeError, ValueError):
        return None
    return n if n >= 1 and not isinstance(page, bool) else None


def clean_text(text):
    """The passage with stray control characters turned into spaces and the ends trimmed; nothing else is touched (no whitespace is collapsed, no word changed)."""
    return _CONTROL.sub(" ", text or "").strip()


def clean_name(s):
    """Whitespace collapsed and 'versus' / 'vs' written as 'v.', which is how the register and the cards write a case."""
    return _VERSUS.sub(" v. ", re.sub(r"\s+", " ", s or "").strip())[:300]


def date_parts(text):
    """(ISO date or None, year or None) from '2026-01-05', '05-01-2026', '05/01/2026'; a bare four-digit year gives only the year."""
    s = str(text or "")
    m = re.search(r"\b((?:18|19|20)\d\d)-(\d{2})-(\d{2})\b", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", int(m.group(1))
    m = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.]((?:18|19|20)\d\d)\b", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            return f"{y:04d}-{mo:02d}-{d:02d}", y
    m = re.search(r"\b((?:18|19|20)\d\d)\b", s)
    return (None, int(m.group(1))) if m else (None, None)


def key_text(key):
    """A citation key written back as text that goodlaw/cites.py reads as the same key ('scc:2018:17:627' -> '(2018) 17 SCC 627'); None for a kind it does not write."""
    p = key.split(":")
    kind = p[0]
    try:
        if kind == "scc":
            y, ser, pg = p[1:4]
            return f"({y}) {ser} SCC {pg}" if ser.isdigit() else (f"({y}) Supp {ser[1:]} SCC {pg}" if ser.startswith("s") and ser[1:].isdigit() else f"{y} (Supp.) SCC {pg}")
        if kind == "air":
            return f"AIR {p[1]} SC {p[2]}"
        if kind == "scr":
            y, ser, pg = p[1:4]
            return f"[{y}] {ser} S.C.R. {pg}" if ser.isdigit() else (f"[{y}] Supp ({ser[1:]}) SCR {pg}" if ser.startswith("s") and ser[1:].isdigit()
                                                                       else (f"[{y}] Suppl. SCR {pg}" if ser == "s" else f"[{y}] S.C.R. {pg}"))
        if kind == "insc":
            return f"{p[1]} INSC {p[2]}"
        if kind == "scale":
            return f"({p[1]}) {p[2]} SCALE {p[3]}"
        if kind == "jt":
            return f"JT {p[1]} ({p[2]}) SC {p[3]}"
        if kind == "scccri":
            return f"({p[1]}) {p[2]} SCC (Cri) {p[3]}" if p[2] else f"{p[1]} SCC (Cri) {p[3]}"
        if kind == "sconline":
            return f"{p[1]} SCC OnLine SC {p[2]}"
    except (IndexError, ValueError):
        return None
    return None


def citation_text(keys=(), texts=()):
    """Reported citations as one string, each written once: the keys first (written back as text), then any given texts whose key is not already there."""
    out, seen = [], set()
    for k in list(keys or [])[:MAX_CITES]:
        t = key_text(k)
        if t and k not in seen:
            seen.add(k)
            out.append(t)
    for t in texts or ():
        if not t:
            continue
        ks = C.cite_keys(t)
        if ks and all(k in seen for k in ks):
            continue
        seen.update(ks)
        out.append(re.sub(r"\s+", " ", t).strip())
    return " ; ".join(out)


# ---- who a judgment is ----------------------------------------------------------------------------------------------------------------------------------------------------------
class IndexDocs:
    """The index's own document records, kept only where they say something about who the judgment is ('src' for a bucket judgment, 'case' for the old header layout)."""

    def __init__(self, rows=()):
        self.by_doc = {}
        for r in rows:
            self.add(r)

    def add(self, row):
        if "skip" in row:                                   # a judgment the index did not embed has no passages to hit
            return
        keep = {k: row[k] for k in ("src", "case") if row.get(k)}
        if keep:
            self.by_doc[int(row["doc"])] = keep

    @classmethod
    def load(cls, index_dir):
        """Reads `index/*.docs.jsonl.gz` in a checkout of the index branch (or a list of them)."""
        docs = cls()
        for d in ([index_dir] if isinstance(index_dir, str) else list(index_dir)):
            for f in sorted(glob.glob(os.path.join(d, "index", "*.docs.jsonl.gz"))):
                with gzip.open(f, "rt", encoding="utf-8") as fh:
                    for line in fh:
                        if line.strip():
                            docs.add(json.loads(line))
        return docs

    def get(self, doc):
        return self.by_doc.get(int(doc))


class IndexRowIdentity:
    """Identity from the index's own record: the bucket title (with its date and citations) or the old-layout petitioner and respondent. None where the record has neither."""

    def __init__(self, docs):
        self.docs = docs

    def __call__(self, doc):
        row = self.docs.get(doc)
        if not row:
            return None
        src, case = row.get("src") or {}, row.get("case") or {}
        if src.get("title"):
            date, year = date_parts(src.get("date"))
            return Identity(clean_name(src["title"]), year, citation_text((), (src.get("citation"), src.get("case_id"))), date, "index_bucket_title", "bucket" if date else None, None)
        if case.get("pet") and case.get("resp"):
            date, year = date_parts(case.get("date"))
            return Identity(clean_name(f"{case['pet']} v. {case['resp']}"), year, "", date, "index_case_header", "header" if date else None, None)
        return None


class CorpusIdentity:
    """Identity from the checker's corpus (goodlaw/corpus.py `Corpus`, or anything with `get(doc_key, with_text=False)`), which is what the register and the cards were built against."""

    def __init__(self, corpus, docs=None, bucket_base=BUCKET_BASE):
        self.corpus, self.docs, self.bucket_base = corpus, docs, bucket_base

    def __call__(self, doc):
        doc = int(doc)
        if doc >= self.bucket_base:
            path = (((self.docs.get(doc) if self.docs else None) or {}).get("src") or {}).get("path")
            if not path:
                return None
            key = "b" + path
        else:
            key = f"c{doc}"
        d = self.corpus.get(key, with_text=False)
        if not d:
            return None
        name = d.get("title") or (f"{d['pet']} v. {d['resp']}" if d.get("pet") and d.get("resp") else None)
        if not name:
            return None
        notes = []
        if not d.get("date") or d.get("date_source") not in K.RELIABLE:
            notes.append(f"year taken from '{d.get('date_source') or 'unknown'}', not read from the judgment")
        return Identity(clean_name(name), d.get("year"), citation_text(d.get("cites"), (d.get("scr_cite"), d.get("insc"))), d.get("date"), "corpus", d.get("date_source"), key, tuple(notes))


class ChainIdentity:
    """The first provider that knows the judgment."""

    def __init__(self, *providers):
        self.providers = providers

    def __call__(self, doc):
        for p in self.providers:
            ident = p(doc)
            if ident:
                return ident
        return None


# ---- the connector ---------------------------------------------------------------------------------------------------------------------------------------------------------------
def passage_from_hit(hit, identity=None, *, court="Supreme Court", link_for=None, open_action=False):
    """The formatter's passage dict for one index passage row. `identity` is a provider (doc id -> Identity or None); without one, nothing can be identified.
    `link_for(doc, identity)` may return a URL (nothing is built by default); `open_action=True` adds the index doc id as `doc_id`."""
    raw = hit.get("text")
    text = clean_text(raw)
    if not text:
        raise ValueError("a hit needs its passage text")
    if hit.get("doc") is None:
        raise ValueError("a hit needs its index doc id")
    doc = int(hit["doc"])
    ident = identity(doc) if identity else None
    info = {"index_doc": doc, "index_passage": hit.get("i"), "hash": hit.get("h"), "section": hit.get("section"), "text_changed": text != (raw or "").strip(),
            "name_source": ident.name_source if ident else None, "date_source": ident.date_source if ident else None, "doc_key": ident.doc_key if ident else None,
            "notes": list(ident.notes) if ident else ["judgment not identified"]}
    out = {"case_name": ident.name if ident else f"Judgment no. {doc} (title not available)", "year": ident.year if ident else None, "citation": (ident.citation or None) if ident else None,
           "court": court, "para": para_label(hit.get("pn")), "page": page_label(hit.get("page")), "text": text, "kind_label": KIND_LABELS.get(hit.get("section")),
           "identified": ident is not None, "source_info": info}
    url = link_for(doc, ident) if link_for else None
    if url:
        out["url"] = url
    elif open_action:
        out["doc_id"] = doc
    return out


def format_hit(formatter, hit, identity, intro=False, max_chars=3500, **kw):
    """One message for one hit."""
    return formatter.format(passage_from_hit(hit, identity, **kw), intro=intro, max_chars=max_chars)


def format_hits(formatter, hits, identity, shown=None, max_chars=3500, **kw):
    """A header message, then one per hit shown (see Formatter.format_batch)."""
    return formatter.format_batch([passage_from_hit(h, identity, **kw) for h in hits], shown=shown, max_chars=max_chars)
