"""Tests for sci_quotes.py (passages whose paragraph number is not the judgment's own) and its use in sci_search_service.py (SCI_QUOTES). Offline; invented passages shaped like the real ones, plus the real
shape of Sadhwi Pragyna Singh Thakur (2011) when review_results/2026-10-26_quote_provenance/sadhwi_passages.json is present. Run: python test_sci_quotes.py"""
import json, os, re, sys
from types import SimpleNamespace
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sci_quotes as Q
import sci_search_service as S

FAILS = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)

def P(pn, text="Some words of the court. " * 6):
    return {"pn": pn, "text": text}

def seq(*pns):
    return [P(p) for p in pns]

# ---- parse_pn
check("parse_pn: plain, piece, range, joined piece range", Q.parse_pn("25") == (25, 25, False) and Q.parse_pn("7/2") == (7, 7, True) and Q.parse_pn("5-6") == (5, 6, False) and Q.parse_pn("3/1-4") == (3, 4, True))
check("parse_pn: preamble, None, junk", Q.parse_pn("preamble") is None and Q.parse_pn(None) is None and Q.parse_pn("fallback_2") is None and Q.parse_pn("") is None)

# ---- own_run
check("own_run: a clean sequence is all own", Q.own_run([(i, False) for i in (1, 2, 3, 4, 5, 6)]) == set(range(6)))
check("own_run: pieces of one paragraph share a number", Q.own_run([(1, False), (2, True), (2, True), (2, True), (3, False), (4, False)]) == set(range(6)))
r = Q.own_run([(23, False), (24, False), (25, False), (3, False), (6, False), (8, False), (830, False), (26, False), (27, False)])
check("own_run: the numbers of a quoted decision (3, 6, 8, 830) between 25 and 26 are off the run", r == {0, 1, 2, 7, 8}, r)
r = Q.own_run([(7, False), (8, False), (8, False), (9, False)])           # a quoted 8 and the own 8: the later one is the own
check("own_run: two plain 8s -> the later one is the own paragraph", r == {0, 2, 3}, r)

# ---- read_doc
base = seq("preamble", "1", "2", "3", "4", "5", "6", "7", "8")
check("read_doc: a clean judgment flags nothing", Q.read_doc(base) == {})
check("read_doc: a judgment with sentence windows (no numbers) is not read", Q.read_doc(seq(None, None, None, None, None, None, None)) == {})
check("read_doc: fewer than 6 numbered passages is not read", Q.read_doc(seq("1", "2", "3", "3", "4")) == {})

doc = seq("1", "2", "3", "4", "5", "6", "7", "8", "3", "6", "9", "10", "11", "12")             # 3 and 6 sit between 8 and 9
out = Q.read_doc(doc)
check("read_doc: the block between own 8 and own 9 is found, nothing else", sorted(out) == [8, 9], out)
check("read_doc: it sits inside paragraph 8, kind off_sequence when nothing introduces it", out[8]["within"] == "8" and out[8]["kind"] == "off_sequence" and out[8]["block"] == 2 and "intro" not in out[8], out[8])

d2 = [P(p) for p in ("1", "2", "3", "4", "5", "6")] + [P("7", "7. In Saptawna v. State of Assam AIR 1971 SC 813 this Court observed as under :-")] + [P("3"), P("4")] + [P(p) for p in ("8", "9", "10")]
out2 = Q.read_doc(d2)
check("read_doc: a paragraph that ends with ':-' introduces the block, and the words are copied", out2[7]["kind"] == "introduced" and out2[7]["intro"] == "In Saptawna v. State of Assam AIR 1971 SC 813 this Court observed as under :-", out2.get(7))
d3 = [P(p) for p in ("1", "2", "3", "4", "5", "6")] + [P("7", "7. The counsel relied on the following decisions:")] + [P("1"), P("2")] + [P("8"), P("9"), P("10")]
check("read_doc: a colon also introduces a list; the kind says 'introduced', the words say which", Q.read_doc(d3)[7]["kind"] == "introduced" and Q.read_doc(d3)[7]["intro"] == "The counsel relied on the following decisions:")
d4 = [P(p) for p in ("1", "2", "3", "4", "5", "6")] + [P("7", "7. The court said “2. The learned counsel says that the petitioner")] + [P("2", "2. is entitled to be released.”")] + [P("8"), P("9"), P("10")]
o4 = Q.read_doc(d4)
check("read_doc: a quotation mark opened in the paragraph and closed in the block introduces it (intro = the words before the mark)", o4[7]["kind"] == "introduced" and o4[7]["intro"] == "The court said", o4.get(7))
d5 = [P(p) for p in ("1", "2", "3", "4", "5", "6")] + [P("7", "7. The court said “2. The learned counsel says that the petitioner is a person")] + [P("2")] + [P("8"), P("9"), P("10")]
check("read_doc: an opened mark that the block does not close is no cue (an unrelated stray mark)", Q.read_doc(d5)[7]["kind"] == "off_sequence")
d6 = [P(p) for p in ("1", "2", "3", "4", "5", "6")] + [P("7/1", "7. A long paragraph that begins: “2. The learned counsel")] + [P("7/2", "continues and goes on and on")] + [P("2", "the end of the quote.”")] + [P("8"), P("9"), P("10")]
o6 = Q.read_doc(d6)
check("read_doc: the pieces of the own paragraph are read together before the block (the mark opens in piece 7/1, the block follows 7/2)", sorted(o6) == [8] and o6[8]["kind"] == "introduced" and o6[8]["within"] == "7", o6)

# a judgment that repeats one of its own numbers, and a passage that opens with a quotation mark
dup = seq("1", "2", "3", "4", "5", "6", "45", "46", "46", "47", "48", "49")
check("read_doc: a number repeated in the judgment's own sequence (46, 46) is left alone: code cannot tell it from the court's numbering", Q.read_doc(dup) == {}, Q.read_doc(dup))
dupq = [P(p) for p in ("1", "2", "3", "4", "5", "6", "15")] + [P("16", "16. \u201c...The expression has sometimes been employed to convey the restricted idea of facts")] + [P("16"), P("17"), P("18")]
oq = Q.read_doc(dupq)
check("read_doc: ...unless the passage itself opens with a quotation mark (then it is introduced, whatever its number)", sorted(oq) == [7] and oq[7]["kind"] == "introduced" and oq[7]["within"] == "15", oq)
far = seq("20", "21", "22", "23", "24", "25", "3", "26", "27", "28")
check("read_doc: a number far from the slot (8 inside 25) is flagged even though nothing introduces it", sorted(Q.read_doc(far)) == [6] and Q.read_doc(far)[6]["kind"] == "off_sequence" and Q.read_doc(far)[6]["within"] == "25", Q.read_doc(far))

# edges
tail = seq("1", "2", "3", "4", "5", "6", "7", "1", "2", "3")
check("read_doc: numbering that restarts and never returns (a second opinion) is not flagged", Q.read_doc(tail) == {})
head = seq("6", "7", "8", "1", "2", "3", "4", "5", "6", "7")
check("read_doc: a numbered caption before the judgment is not flagged", Q.read_doc(head) == {}, Q.read_doc(head))
jump = seq("1", "2", "3", "4", "5", "6", "40", "11", "12")
check("read_doc: a block after which the own run is not within 3 numbers is not flagged", Q.read_doc(jump) == {}, Q.read_doc(jump))
jj = Q.read_doc(seq("20", "21", "22", "23", "8-24", "25", "26", "27"))
check("read_doc: '8-24' between own 23 and 25: flagged inside 23, and it says it ends on own paragraph 24", jj.get(4, {}).get("within") == "23" and jj[4].get("ends_at") == "24", jj)

# ---- the real shape (Sadhwi), when the file is there
real = os.path.join(HERE, "review_results", "2026-10-26_quote_provenance", "sadhwi_passages.json")
if os.path.exists(real):
    rows = json.load(open(real, encoding="utf-8"))
    res = Q.read_doc(rows)
    pos = {i: rows[i]["pn"] for i in res}
    check("Sadhwi (real index rows): the four passages numbered 3, 6, 8, 830 are found inside paragraph 25, with the words that introduce them",
          sorted(pos.values()) == ["3", "4", "6", "8", "830"] and all(res[i]["within"] == "25" and res[i]["kind"] == "introduced" for i in res if rows[i]["pn"] in ("3", "6", "8", "830")), pos)
    check("Sadhwi: the introduction names Saptawna, as the judgment does", all("Saptawna vs. The State of Assam AIR (1971) SC 813" in res[i]["intro"] for i in res if res[i]["kind"] == "introduced"))
    check("Sadhwi: the '4' that is a wrapped 'para 4.' inside paragraph 21 is found too, as off_sequence", [res[i] for i in res if rows[i]["pn"] == "4"][0]["within"] == "21")
    check("Sadhwi: no real paragraph (2 to 31) is flagged", all(rows[i]["pn"] in ("3", "4", "6", "8", "830") for i in res))
else:
    print("(Sadhwi file not present: skipped)")

# ---- build()
metas = []
for d in (1, 2):
    for i, p in enumerate(doc):
        metas.append({"doc": d, "i": i, "pn": p["pn"], "text": p["text"]})
found, st = Q.build(iter(metas))
check("build: keys are '<doc>:<i>', both documents", sorted(found) == ["1:8", "1:9", "2:8", "2:9"], sorted(found))
check("build: statistics", st["documents"] == 2 and st["documents_read"] == 2 and st["documents_with_flagged"] == 2 and st["flagged"] == 4 and st["off_sequence"] == 4 and st["blocks"] == 2 and st["passages"] == 28, st)
found2, st2 = Q.build(iter(metas[:14] + metas[14:20] + metas[:3]))
check("build: a document that comes back after another is counted as split", st2["split_documents"] == 1, st2)

# ---- the service
DIM = 32
def vec(text):
    v = np.zeros(DIM, dtype=np.float32)
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        v[sum(map(ord, w)) % DIM] += 1.0
    return v / (np.linalg.norm(v) or 1.0)

class FakeClient:
    def embed(self, texts, model, input_type):
        return SimpleNamespace(embeddings=[vec(texts[0]).tolist()], total_tokens=len(texts[0]) // 4)
    def rerank(self, query, docs, model, top_k):
        qw = set(re.findall(r"[a-z0-9]+", query.lower()))
        res = [SimpleNamespace(index=i, relevance_score=len(qw & set(re.findall(r"[a-z0-9]+", d.lower()))) / (len(qw) or 1)) for i, d in enumerate(docs)]
        res.sort(key=lambda r: -r.relevance_score)
        return SimpleNamespace(results=res[:top_k], total_tokens=sum(len(d) // 4 for d in docs))

sm = []
for i, p in enumerate(d2):
    txt = p["text"] if i == 6 else (f"{p['pn']}. Quoted decision text about detention and remand and production before the magistrate." if i in (7, 8) else f"{p['pn']}. The court considered bail and arrest at paragraph {i}.")
    sm.append({"doc": 500, "i": i, "pn": p["pn"], "page": 1, "section": "reasoning", "h": f"h{i}", "text": txt})
M = np.stack([vec(m["text"]) for m in sm]).astype(np.float16)
def make(on):
    old = os.environ.get("SCI_QUOTES")
    os.environ["SCI_QUOTES"] = on
    try:
        svc = S.SearchService([S._slim(m) for m in sm], M, FakeClient(), lambda doc: f"Case {doc} v. State (01/02/2020)", info={"index_commit": "abc", "as_of": "2026-07-13"}, sleep=lambda s: None)
        if S.quotes_on():
            svc.quotes, _ = Q.build(svc.metas)
        return svc
    finally:
        if old is None:
            os.environ.pop("SCI_QUOTES", None)
        else:
            os.environ["SCI_QUOTES"] = old

check("SCI_QUOTES: off by default, on only for on/1/true/yes", not (os.environ.pop("SCI_QUOTES", None) or S.quotes_on()))
for v, want in (("on", True), ("ON", True), (' "on" ', True), ("1", True), ("off", False), ("", False), ("maybe", False)):
    os.environ["SCI_QUOTES"] = v
    check(f"SCI_QUOTES={v!r} -> {want}", S.quotes_on() == want)
os.environ.pop("SCI_QUOTES", None)

res_off = make("off").search("detention remand production before the magistrate", k=12)["results"]
check("service, switch off: no result has a 'quote' field (the answer is what it was)", all("quote" not in r for r in res_off) and len(res_off) == 12)
res_on = make("on").search("detention remand production before the magistrate", k=12)["results"]
flagged = [r for r in res_on if "quote" in r]
check("service, switch on: the passages numbered outside the sequence carry 'quote', the others do not", len(flagged) == 2 and {r["paragraph"] for r in flagged} == {"3", "4"} and all(r["quote"]["within"] == "7" for r in flagged), [(r["paragraph"], r.get("quote")) for r in res_on])
check("service, switch on: the paragraph label itself is not changed (clients decide)", all(r["paragraph"] in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10") for r in res_on) and sorted(r["paragraph"] for r in res_on) == sorted(r["paragraph"] for r in res_off))
svc_on = make("on")
r1 = svc_on.search("detention remand production before the magistrate", k=12)["results"]
for r in r1:
    if "quote" in r:
        r["quote"]["within"] = "CHANGED"
check("service, switch on: the result holds a copy of the record, so changing it does not change the service's table", all(v["within"] == "7" for v in svc_on.quotes.values()))
check("service, switch on: same passages, same order as with the switch off", [r["passage_id"] for r in res_on] == [r["passage_id"] for r in res_off])

# ---- the start-up line
base_info = {"index_commit": "d8811a910c73b0159bea7bcf3183ea258120db5b", "passages": 420893, "documents": 19255, "courts": {"Supreme Court of India": 11702, "Gauhati High Court": 7553}, "as_of": "2026-10-16"}
class _Svc:
    def __init__(self, info): self.info = info
line_off = S.startup_line(_Svc(dict(base_info)), "::", 8080)
line_on = S.startup_line(_Svc(dict(base_info, quotes={"flagged": 21524, "documents_with_flagged": 4550})), "::", 8080)
check("start-up line: unchanged when SCI_QUOTES is off", line_off == "sci-search listening on :::8080; index d8811a910c, 420,893 passages; 19,255 judgments (Supreme Court of India 11,702, Gauhati High Court 7,553); ends 2026-10-16", line_off)
check("start-up line: says how many passages are marked when SCI_QUOTES is on", line_on.startswith(line_off) and line_on.endswith("; SCI_QUOTES on: 21,524 passages marked in 4,550 judgments (numbered outside their judgment's own sequence)"), line_on)

print()
print("ALL PASSED" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
