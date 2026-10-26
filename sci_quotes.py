"""
sci_quotes.py -- passages whose paragraph number is not the judgment's own (FOLLOW_UPS 2cm; prototype, owner's go 2026-10-26).

THE PROBLEM. The index cuts a judgment into passages at every line that starts "N. " (chunk_judgments.PARAGRAPH_PATTERN) and calls the number the passage's "paragraph". Inside one paragraph of the judgment that is wrong in three
ways, all seen in the real index (Sadhwi Pragyna Singh Thakur v. State of Maharashtra (2011), document 38684):
  * a QUOTATION of an earlier decision keeps that decision's own paragraph numbers ("3. A similar case came before this Court...", "6. The petitioner then filed...", "8. From the order-sheets..."), all inside the
    judgment's own paragraph 25, which says "In Saptawna vs. The State of Assam AIR (1971) SC 813, this Court has observed as under ... :". The passage numbered 8 was shown, and credited, as "Sadhwi, paragraph 8".
  * a citation wrapped at the end of a line ("... (1966) 3 SCR" / "830. Only the spirit ...", or "... SCC 718 para" / "4. It may be mentioned ...") is read as a new paragraph numbered 830 or 4;
  * a numbered list inside a paragraph (the court's own directions "1. ... 2. ...") is read as paragraphs 1 and 2.
A prompt cannot repair that: the number printed beside the passage is simply wrong, and the model has no way to see that the words belong to another decision.

WHAT THIS DOES. It reads only the passages' numbering and the words at the end of the paragraph before (no model, no network, no re-embedding): in each judgment the numbers that form the longest run in file order
(strictly increasing, except that the pieces of one long paragraph, "7/1", "7/2", share a number) are the judgment's own; a passage numbered off that run, in a place where the run picks up again straight afterwards (the next
own number is at most 3 above the one before), sits INSIDE the own paragraph before it. Such a passage gets {"within": "25", "kind": ..., "intro": ...}. The paragraph a reader should be sent to is "25"; the number the passage
carries ("8") is not a paragraph of this judgment. Code can say THAT the number is not the judgment's own; it cannot say what the words are, so there are only two kinds:
  kind "introduced": the own paragraph before the block ends with a colon ("... has observed as under :-"), or with an opening mark, or a quotation mark opened in it is closed in the block. "intro" holds up to 320 characters
                     of the judgment's own words that end there, copied word for word. A colon also introduces a list ("... on the following decisions:"), so this says "probably a quotation", not "a quotation".
  kind "off_sequence": the numbering is off and nothing introduces it. It may be a quotation whose introduction is not at the end of the paragraph, a wrapped citation ("... (1966) 3 SCR" / "830. Only the spirit ..."), a
                     footnote, a statute section or an affidavit set out with its own numbers, or the court's own numbered list. The words can be the court's own.
  "ends_at": a joined passage ("8-24") that starts off the run and ends on it: its last part is the judgment's own paragraph.
A passage that nothing introduces and whose number fits between the own paragraph before it and the own paragraph after it ("46." before an own "46.", a judgment that repeats a number) is left alone: code cannot tell it from the
court's own numbering. A passage whose number is far from the slot (a quoted "8" inside 25) or that something introduces is flagged. Not touched: a judgment with fewer than 6 numbered passages or more than 2,500 (sentence-window judgments have no numbers at all), off-run passages at the start or end of a judgment (a caption list, a second opinion that
restarts the numbering, an annexure), and a block where the run does not pick up within 3.

WHAT IT CANNOT DO (measured in review_results/2026-10-26_quote_provenance/RESULTS.md). It misses a quoted block whose numbers fall inside the judgment's own run (a quoted "8" between own 7 and own 8 is resolved by taking
the later one as the own), and a quotation that carries no paragraph numbers (then the passage is not numbered off at all: this is probably the larger share of quoted text). It cannot name the quoted decision: "intro" gives the
judgment's own words and a reader or the model reads the name from them. Nothing here says a quoted passage is good or bad law.

Used by sci_search_service.SearchService.load (SCI_QUOTES=on, default off), which adds "quote" to a result, and by Recourse's sci_search_tier.feed_block, which words the head of the passage, the note under it and the page.
CLI: python sci_quotes.py report INDEX_DIR [SIDE_INDEX_DIR ...] [--samples N]
"""
import gzip
import itertools
import json
import os
import random
import re
import sys

VERSION = "q1"
MIN_NUMBERED = 6                    # fewer numbered passages than this: the judgment is not read
MAX_NUMBERED = 2500                 # the longest run is found by an O(n^2) pass
MAX_GAP = 3                         # the own run must pick up again within this many numbers after the passage before the block
MAX_BLOCK = 80                      # a block of more consecutive off-run passages than this is not read as a quotation
INTRO_CHARS = 320

_PN = re.compile(r"^(\d{1,4})(/\d+)?(?:-(\d{1,4})(/\d+)?)?$")


def parse_pn(pn):
    """(start, end, piece) from a passage's paragraph label: "25" -> (25, 25, False); "7/2" -> (7, 7, True); "5-6" -> (5, 6, False); "preamble", None, anything else -> None."""
    m = _PN.match(str(pn).strip()) if pn is not None else None
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(3)) if m.group(3) else start
    return start, end, bool(m.group(2) or m.group(4))


def own_run(items):
    """`items`: [(start, piece)] in file order. The indexes (into items) of the longest run in which each number is above the one before it, or equal to it when both are pieces of one paragraph. Among runs of the
    same length the one with the smaller total of steps wins; among equal ones the one that uses the LATER passage of two with the same number (a quotation comes before the own paragraph that follows it)."""
    n = len(items)
    best = [(1, 0)] * n                  # (length, -total step) of the best run ending here
    pred = [-1] * n
    for i in range(n):
        a_i, p_i = items[i]
        top, who = (1, 0), -1
        for j in range(i):
            a_j, p_j = items[j]
            if a_j < a_i or (a_j == a_i and p_j and p_i):
                cand = (best[j][0] + 1, best[j][1] - (a_i - a_j))
                if cand > top or (cand == top and who != -1):       # a tie goes to the later j
                    top, who = cand, j
        best[i], pred[i] = top, who
    end = max(range(n), key=lambda i: (best[i][0], best[i][1], i))
    run = []
    while end != -1:
        run.append(end)
        end = pred[end]
    return set(run)


_COLON_END = re.compile(r"(?:[:\uff1a]\s*[-\u2013\u2014]*|[\u201c\"])\s*$")


def _open_quote(text):
    """Position of an opening quotation mark with no closing one after it, or -1. Curly marks first; straight marks only when there are no curly ones and their number is odd."""
    opens, closes = text.count("\u201c"), text.count("\u201d")
    if opens or closes:
        if opens > closes:
            return text.rfind("\u201c")
        return -1
    if text.count('"') % 2 == 1:
        return text.rfind('"')
    return -1


def _tail_words(before):
    """Up to INTRO_CHARS of the judgment's own words at the end of `before`, starting at a sentence start when there is one."""
    before = re.sub(r"\s+", " ", before).strip()
    before = re.sub(r"^\d{1,4}\.\s+", "", before)                       # the own paragraph's number
    if len(before) > INTRO_CHARS:
        before = before[-INTRO_CHARS:]
        cut = re.search(r"[.;:]\s+(?=[A-Z0-9(])", before)
        before = before[cut.end():] if cut and cut.end() < len(before) - 40 else "..." + before[before.find(" ") + 1:]
    return before


def introduced(host, block):
    """(True, the judgment's own words that introduce the block) when the block follows something that introduces a quotation: the own paragraph ends with a colon ("... has observed as under :-"), or with an opening mark, or
    a quotation mark opened in it is closed in the block. (False, "") otherwise. This is a cue, not a finding: a colon also introduces a list ("... on the following decisions:").
    `host`: the text of the own paragraph (all its pieces) before the block; `block`: the text of the off-run passages."""
    h = re.sub(r"\s+", " ", host or "").strip()
    if _COLON_END.search(h):
        return True, _tail_words(h)
    q = _open_quote(h)
    if q >= 0 and ("\u201d" in block or '"' in block):
        return True, _tail_words(h[:q])
    if re.match(r"\s*\d{1,4}\.\s*[\u201c\"]", block or ""):                  # "17. \u201c...The identification parades belong to the stage of investigation": the passage itself opens with a quotation mark
        return True, _tail_words(h)
    return False, ""


def read_doc(passages):
    """`passages`: the judgment's passages in file order, each {"pn": ..., "text": ...}. Returns {position in `passages`: {"within": "25", "kind": "quotation"|"off_sequence", "intro"?: "...", "block": n}} for every
    passage found inside an own paragraph (see the module docstring); {} when the judgment is not read."""
    parsed = [parse_pn(p.get("pn")) for p in passages]
    idx = [i for i, x in enumerate(parsed) if x]
    if not (MIN_NUMBERED <= len(idx) <= MAX_NUMBERED):
        return {}
    run = {idx[k] for k in own_run([(parsed[i][0], parsed[i][2]) for i in idx])}
    out = {}
    i = 0
    n = len(passages)
    while i < n:
        if i in run or not parsed[i]:
            i += 1
            continue
        j = i
        while j < n and j not in run and parsed[j]:
            j += 1
        before, after = i - 1, j
        if before >= 0 and after < n and before in run and after in run and j - i <= MAX_BLOCK and 0 <= parsed[after][0] - parsed[before][0] <= MAX_GAP:
            base = parsed[before][0]
            k = before                                                   # the own paragraph before the block, with the other pieces of it
            while k - 1 >= 0 and k - 1 in run and parsed[k - 1][0] == base and parsed[k - 1][2]:
                k -= 1
            host = " ".join(re.sub(r"\s+", " ", passages[x]["text"] or "") for x in range(k, before + 1))
            block = " ".join(re.sub(r"\s+", " ", passages[x]["text"] or "") for x in range(i, j))
            cue, intro = introduced(host, block)
            rec = {"within": str(base), "kind": "introduced" if cue else "off_sequence", "block": j - i}
            if cue:
                rec["intro"] = intro
            for x in range(i, j):
                if not cue and parsed[before][0] <= parsed[x][0] <= parsed[after][0]:
                    continue                                              # its number fits the slot of an own paragraph (the judgment may repeat a number: "46." twice) and nothing introduces it: not enough to say it is not the judgment's own
                one = dict(rec)
                if parsed[x][1] != parsed[x][0] and parsed[before][0] <= parsed[x][1] <= parsed[after][0]:
                    one["ends_at"] = str(parsed[x][1])                       # a joined passage ("8-24"): it starts off the run and ends on it, so its last part is the judgment's own paragraph
                out[x] = one
        i = j
    return out


def build(metas):
    """`metas`: the index's passage rows (doc, i, pn, text), the passages of one judgment next to each other and in file order (as the index stores them). Returns ({"<doc>:<i>": record}, statistics).
    `metas` may be a generator: only one judgment is held at a time."""
    found = {}
    stats = {"version": VERSION, "documents": 0, "passages": 0, "documents_read": 0, "documents_with_flagged": 0, "flagged": 0, "introduced": 0, "off_sequence": 0, "joined_with_own": 0, "blocks": 0, "split_documents": 0}
    seen_docs = set()
    for doc, group in itertools.groupby(metas, key=lambda m: m["doc"]):
        ps = list(group)
        stats["documents"] += 1
        stats["passages"] += len(ps)
        if doc in seen_docs:
            stats["split_documents"] += 1                                  # a document whose passages are not next to each other: its later part is read as a document of its own
        seen_docs.add(doc)
        recs = read_doc(ps)
        if MIN_NUMBERED <= sum(1 for p in ps if parse_pn(p.get("pn"))) <= MAX_NUMBERED:
            stats["documents_read"] += 1
        if recs:
            stats["documents_with_flagged"] += 1
        for pos, rec in recs.items():
            found[f"{doc}:{ps[pos]['i']}"] = rec
            stats["flagged"] += 1
            stats[rec["kind"]] += 1
            stats["joined_with_own"] += 1 if rec.get("ends_at") else 0
    stats["blocks"] = sum(1 for _ in _blocks(found))
    return found, stats


def _blocks(found):
    """One item per block of flagged passages (consecutive passages of one judgment with the same 'within' and block size)."""
    last = None
    for k in sorted(found, key=lambda x: tuple(int(v) for v in x.split(":"))):
        doc, i = (int(v) for v in k.split(":"))
        rec = found[k]
        if last and last[0] == doc and last[1] == i - 1 and last[2] == rec["within"] and last[3] == rec["block"] and last[4] < rec["block"]:
            last = (doc, i, rec["within"], rec["block"], last[4] + 1)
            continue
        last = (doc, i, rec["within"], rec["block"], 1)
        yield k


def key(doc, i):
    return f"{doc}:{i}"


# ------------------------------------------------------------------ command line: a report on an index
def _read_metas(index_dir):
    """The passage rows of one index folder, in block order (only the fields used here)."""
    d = os.path.join(index_dir, "index")
    names = sorted(f for f in os.listdir(d) if f.endswith(".meta.jsonl.gz"))
    for f in names:
        with gzip.open(os.path.join(d, f), "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                yield {"doc": int(r["doc"]), "i": r["i"], "pn": r.get("pn"), "text": r.get("text") or ""}


def report(dirs, samples=0, seed=7, out=print):
    found, st = build(m for d in dirs for m in _read_metas(d))
    out(json.dumps(st, indent=1))
    if samples:
        rows = sorted(found.items())
        random.Random(seed).shuffle(rows)
        want = {tuple(int(v) for v in k.split(":")): rec for k, rec in rows[:samples]}
        for m in (m for d in dirs for m in _read_metas(d)):
            rec = want.get((m["doc"], m["i"]))
            if rec:
                out("-" * 78)
                out(f"doc {m['doc']} passage {m['i']} number {m['pn']} -> within {rec['within']} [{rec['kind']}] block of {rec['block']}")
                if rec.get("intro"):
                    out("  intro: " + rec["intro"])
                out("  text : " + re.sub(r"\s+", " ", m["text"])[:260])
    return found, st


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] != "report":
        print(__doc__)
        return 2
    samples = 0
    if "--samples" in argv:
        k = argv.index("--samples")
        samples = int(argv[k + 1])
        del argv[k:k + 2]
    report(argv[1:], samples)
    return 0


if __name__ == "__main__":
    sys.exit(main())
