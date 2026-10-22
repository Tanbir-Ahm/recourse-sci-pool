"""Word rejoin for the open bucket's Guwahati text (set C).

The bucket's Guwahati PDFs are typed on an 80-column grid. A line break falls anywhere: inside a word ("popular|ly"), or at a word end where the space was lost ("months|of June"). The old
`unwrap_fixed` glued every full-width line to the next without a space, which is right for the first kind and wrong for the second. This module decides each break with a lexicon built
from CLEAN text (Supreme Court newer archive + Guwahati court files; the bucket text itself is never used to build it) and joins with or without a space.

Decision for a break whose two sides are letters, L = the word-piece ending the line, R = the piece starting the next line:
  - R starts with a capital and L ends with a lowercase letter: a new word (space).
  - only L+R is a word: join. Only L and R are both words (and L+R is not): space.
  - both readings are words ("any|one"): join if count(LR) > KAPPA * count("L R" as two adjacent words) in the clean text.
  - neither is a word (names, numbers, damage): join (a break inside a word is about three times as common as a break at a word end).
Usage as a module: lex = build_lexicon([dirs]); out = rejoin(text, lex)."""
import collections, glob, gzip, json, os, re

T = 20                 # a word needs at least this many occurrences in the clean text
KAPPA = 1.0
SHORT_OK = set("a i an as at be by do go he if in is it me my no of on or so to up us we am ah oh".split())
SENT_END = ".:;?!"
_ALPHA_TAIL = re.compile(r"([A-Za-z]+)$")
_ALPHA_HEAD = re.compile(r"^([A-Za-z]+)")
_PAIR = re.compile(r"([A-Za-z]+)(?= ([A-Za-z]+))")
_TOK = re.compile(r"[A-Za-z]+")


class Lexicon:
    def __init__(self, uni, pair):
        self.uni, self.pair = uni, pair

    def is_word(self, w):
        w = w.lower()
        if len(w) <= 2:
            return w in SHORT_OK
        return self.uni.get(w, 0) >= T

    def count(self, w):
        return self.uni.get(w.lower(), 0)


def _texts(dirs):
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "shards", "*.jsonl.gz"))):
            for line in gzip.open(f, "rt", encoding="utf-8"):
                r = json.loads(line)
                if "in_bucket" in r or r.get("text_source") == "court":     # Supreme Court newer archive, or a Guwahati court file: normal layout
                    yield r["text"]


def build_lexicon(dirs):
    uni = collections.Counter()
    texts = list(_texts(dirs))
    for t in texts:
        uni.update(w.lower() for w in _TOK.findall(t))
    words = {w for w, c in uni.items() if c >= T}
    pair = collections.Counter()
    for t in texts:
        for x, y in _PAIR.findall(t):
            xy = (x + y).lower()
            if xy in words:
                pair[(x.lower(), y.lower())] += 1
    return Lexicon(dict(uni), dict(pair))


def decide(L, R, lex, kappa=KAPPA):
    """'join' (no separator) or 'space' for a break between the word pieces L and R."""
    if L[-1].islower() and R[0].isupper():
        return "space"
    lw, rw = lex.is_word(L), lex.is_word(R)
    c_lr = lex.count(L + R)
    j = (c_lr >= T) and (len(L + R) > 2 or (L + R).lower() in SHORT_OK)
    if j and not (lw and rw):
        return "join"
    if lw and rw and not j:
        return "space"
    if j and lw and rw:
        return "join" if c_lr > kappa * lex.pair.get((L.lower(), R.lower()), 0) else "space"
    return "join"


def _width(lines):
    lens = collections.Counter(len(x) for x in lines[:-1] if len(x) >= 60)
    if not lens:
        return 0
    w, n = lens.most_common(1)[0]
    return w if n >= 5 else 0


def rejoin(text, lex, slack=12, kappa=KAPPA, stats=None):
    """Joins the hard-wrapped lines of every page. A line is a candidate when it is within `slack` characters of the page's width and does not end a sentence."""
    out_pages = []
    for pg in text.split("\f"):
        lines = pg.split("\n")
        w = _width(lines)
        if not w:
            out_pages.append(pg)
            continue
        res, cur, a = [], lines[0], lines[0]              # cur: text built so far; a: the last physical line
        for nxt in lines[1:]:
            glue = None
            if len(a) >= w - slack and nxt and a and a[-1] not in SENT_END:
                if a.endswith(" ") or nxt.startswith(" "):
                    glue = ""
                elif not a[-1].isalnum():
                    glue = " " if nxt[0].isalnum() or nxt[0] in "(\"“‘'[" else ""
                elif nxt[0] in ",.;:)]?!%/-":
                    glue = ""
                elif _ALPHA_TAIL.search(a) and _ALPHA_HEAD.search(nxt):
                    L = _ALPHA_TAIL.search(a).group(1)
                    R = _ALPHA_HEAD.search(nxt).group(1)
                    glue = "" if decide(L, R, lex, kappa) == "join" else " "
                    if stats is not None:
                        stats[glue == ""] += 1
                elif nxt[0].isdigit() and a[-1].isdigit():
                    glue = ""
                else:
                    glue = " "
            if glue is None:
                res.append(cur)
                cur = nxt
            else:
                cur = cur + glue + nxt
            a = nxt
        res.append(cur)
        out_pages.append("\n".join(res))
    return "\f".join(out_pages)
