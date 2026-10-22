"""Tests for goodlaw/passage_input.py: the connector from a search hit (an index passage row) to the passage the chat formatter takes.
Run: python test_goodlaw_passage_input.py

Part 1 tests the small readers and the identity providers on rows shaped like the real index's and on a real (temporary) corpus file. Part 2 feeds the connector the hits that the real search code
(review_tools/pool_runner.py's Engine, with the repository's fake service: no network, no spend) returns, and checks that every one becomes a message. Part 3 runs a hit through the formatter with the real
register and cards.
"""
import copy
import gzip
import json
import os
import sqlite3
import sys
import tempfile

from goodlaw import cardreader as CR
from goodlaw import chat_format as CF
from goodlaw import cites as C
from goodlaw import corpus as K
from goodlaw import passage_input as PI
from goodlaw import register as R

FAILURES = []
HERE = os.path.dirname(os.path.abspath(__file__))


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc:
        return True
    except BaseException:
        return False
    return False


# ---- the small readers --------------------------------------------------------------------------------------------------------------------------------------------------------
print("readers")
check([PI.para_label(x) for x in ("14", "1-3", "14/2", " 7 ", "12A", None, "", "preamble-1", "x")] == ["14", "1-3", "14", "7", "12A", None, None, None, None], "paragraph labels: a number, a merged run, a split piece; a preamble or nothing gives none")
check([PI.page_label(x) for x in (9, "9", 0, -1, None, "x", True)] == [9, 9, None, None, None, None, None], "page labels: a positive whole number or nothing")
raw = "  First\x0csecond\x08 third\n\nfourth  fifth \x00 "
check(PI.clean_text(raw) == "First second  third\n\nfourth  fifth", "stray control characters become a space; nothing else changes, not even double spaces")
check(PI.clean_name("MOTILAL OSWAL  LTD.  versus  SANTOSH CORDEIRO") == "MOTILAL OSWAL LTD. v. SANTOSH CORDEIRO" and PI.clean_name("A vs. B") == "A v. B", "'versus' and 'vs' are written as 'v.'")
check(PI.date_parts("05-01-2026") == ("2026-01-05", 2026) and PI.date_parts("2026-08-12") == ("2026-08-12", 2026) and PI.date_parts("12/05/1975") == ("1975-05-12", 1975), "dates: DD-MM-YYYY, ISO, DD/MM/YYYY")
check(PI.date_parts("in the year 1983") == (None, 1983) and PI.date_parts("32-13-2020") == (None, 2020) and PI.date_parts(None) == (None, None) and PI.date_parts("n/a") == (None, None), "a bare year gives the year only; an impossible date is not read as one; nothing gives nothing")

keys = set()
for r in R.Register.load().rows:
    for side in ("overruled", "overruling"):
        keys.update(r[side].get("keys") or [])
keys.update(k for c in CR.load(os.path.join(HERE, "cards", "currency_cards.json"))["cards"] for k in (c["case"].get("citation_keys") or []))
supported = [k for k in keys if not k.startswith("airx:")]
bad = [k for k in supported if C.cite_keys(PI.key_text(k) or "") != [k]]
check(len(supported) > 3000 and not bad, f"every Supreme Court citation key in the register and the cards is written back as text that reads as the same key ({len(supported)} keys; failures {bad[:3]})")
check(PI.key_text("airx:1965:all:586") is None and PI.key_text("nonsense") is None, "a kind it does not write gives None, not a guess")
check(PI.citation_text(["scr:2026:1:1"], ["[2026] 1 S.C.R. 1", "2026 INSC 5"]) == "[2026] 1 S.C.R. 1 ; 2026 INSC 5" and PI.citation_text([], [None, ""]) == "", "citations are written once each, in order; none gives an empty string")
check(PI.citation_text(["scc:2018:17:627"] * 3) == "(2018) 17 SCC 627", "and a repeated key is not repeated")

# ---- identity from the index's own records --------------------------------------------------------------------------------------------------------------------------------------
print("identity from the index's document records")
BUCKET_ROW = {"doc": 1003962500, "hash": "ce29", "pages": 23, "v": "p2", "passages": 12, "noise": 0,
              "src": {"source": "bucket", "scope": "refresh_20261005", "path": "2026_1_1_23", "title": "MOTILAL OSWAL FINANCIAL SERVICES LIMITED versus SANTOSH CORDEIRO AND ANOTHER",
                      "date": "05-01-2026", "citation": "[2026] 1 S.C.R. 1", "case_id": "2026 INSC 5", "headnote_cut": True}}
SKIPPED_ROW = dict(BUCKET_ROW, doc=1003962501, skip="not_criminal")
CRAWL_ROW = {"doc": 14750, "hash": "8c7f", "pages": 15, "v": "p2", "density": 40.9, "passages": 10, "noise": 0}
OLD_ROW = {"doc": 7, "hash": "x", "pages": 3, "passages": 4, "case": {"caseno": "Appeal (crl.) 3 of 1975", "pet": "Foo", "resp": "State of Bar", "date": "12/05/1975", "bench": "A, B"}}
DOCS = PI.IndexDocs([BUCKET_ROW, SKIPPED_ROW, CRAWL_ROW, OLD_ROW])
check(sorted(DOCS.by_doc) == [7, 1003962500], "only records that say who a judgment is are kept, and a judgment the index did not embed is left out")
# judgments from the extra sources (ids from 2,000,000,000): the court's newer archive (a Supreme Court judgment) and the Gauhati High Court
SCI_URL = "https://api.sci.gov.in/supremecourt/2015/480/480_2015_Judgement_20-Jul-2017.pdf"
SCI_ROW = {"doc": 2000250160, "hash": "aa", "pages": 9, "v": "p2", "passages": 6, "noise": 0,
           "src": {"source": "sci_newer", "scope": "sci_newer", "path": SCI_URL, "title": "STATE OF X versus Y", "date": "2017-07-20", "citation": "2017 INSC 640", "case_id": "480/2015", "url": SCI_URL,
                   "court": "Supreme Court of India"}}
SCI_COPY_ROW = {"doc": 2000250161, "hash": "ab", "pages": 9, "v": "p2", "passages": 9, "noise": 0,
                "src": {"source": "sci_newer", "scope": "sci_newer", "path": "https://api.sci.gov.in/supremecourt/2010/1075/1075_2010_Judgement_16-Aug-2018.pdf", "title": "MOHAN LAL versus THE STATE OF PUNJAB",
                        "date": "2018-08-16", "citation": None, "case_id": "1075/2010", "court": "Supreme Court of India"}}
SCI_NOID_ROW = {"doc": 2000250162, "hash": "ac", "pages": 3, "v": "p2", "passages": 2, "noise": 0,
                "src": {"source": "sci_newer", "scope": "sci_newer", "path": "https://api.sci.gov.in/supremecourt/x.pdf", "title": "NO ID versus NOBODY", "date": "2017-08-01", "citation": None, "case_id": None, "court": "Supreme Court of India"}}
GHC_ROW = {"doc": 2000000010, "hash": "ad", "pages": 5, "v": "p2", "passages": 7, "noise": 0,
           "src": {"source": "ghc_court", "scope": "ghc_court", "path": "https://example.invalid/ghc/x.pdf", "title": "STATE OF ASSAM versus RAM DAS", "date": "2019-03-04", "citation": "Crl.A(J)/12/2018",
                   "case_id": "Crl.A(J)/12/2018", "court": "Gauhati High Court"}}
DOCS_X = PI.IndexDocs([BUCKET_ROW, CRAWL_ROW, OLD_ROW, SCI_ROW, SCI_COPY_ROW, SCI_NOID_ROW, GHC_ROW])
who = PI.IndexRowIdentity(DOCS)
i = who(1003962500)
check(i.name == "MOTILAL OSWAL FINANCIAL SERVICES LIMITED v. SANTOSH CORDEIRO AND ANOTHER" and i.year == 2026 and i.date == "2026-01-05" and i.citation == "[2026] 1 S.C.R. 1 ; 2026 INSC 5" and i.name_source == "index_bucket_title",
      "a bucket judgment: its title, its date, and both its citations")
i = who(7)
check(i.name == "Foo v. State of Bar" and i.year == 1975 and i.name_source == "index_case_header" and i.citation == "", "an old-layout judgment: petitioner and respondent from its header, no citation invented")
check(who(14750) is None and who(999) is None, "a crawl judgment with no record of who it is, and an unknown one, are not identified")
whox = PI.IndexRowIdentity(DOCS_X)
i = whox(2000250160)
check(i.name == "STATE OF X v. Y" and i.year == 2017 and i.date == "2017-07-20" and i.date_source == "court" and i.citation == "2017 INSC 640" and i.name_source == "index_extra_title" and i.court == "Supreme Court",
      "a judgment from the court's newer archive is named from its recorded title, with its date, its neutral citation and the court written as 'Supreme Court'")
i = whox(2000000010)
check(i.name == "STATE OF ASSAM v. RAM DAS" and i.year == 2019 and i.court == "Gauhati High Court" and i.citation == "" and i.doc_key is None, "a High Court judgment is named from its title and keeps its court; a case number is not taken for a reported citation")
check(whox(1003962500).court is None and whox(7).court is None, "a bucket or crawl judgment's record names no court (the Supreme Court is assumed)")
with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, "index"))
    with gzip.open(os.path.join(d, "index", "000000-000249.docs3.pass1.tok1.docs.jsonl.gz"), "wt", encoding="utf-8") as fh:
        for r in (BUCKET_ROW, SKIPPED_ROW, CRAWL_ROW, OLD_ROW):
            fh.write(json.dumps(r) + "\n")
    loaded = PI.IndexDocs.load(d)
check(sorted(loaded.by_doc) == [7, 1003962500], "the records load from an index checkout's files")

# ---- identity from the corpus ------------------------------------------------------------------------------------------------------------------------------------------------------
print("identity from the corpus (a real temporary corpus file)")
tmp = tempfile.TemporaryDirectory()
CORPUS_PATH = os.path.join(tmp.name, "corpus.sqlite")
con = sqlite3.connect(CORPUS_PATH)
con.executescript(K.SCHEMA)
ROWS = [
    ("c101", "crawl", "101", "Mohan Lal v. State of Punjab", "Mohan Lal", "State of Punjab", "2018-07-24", "header", 2018, ["scc:2018:17:627"], None, None),
    ("c102", "crawl", "102", None, None, None, None, None, None, [], None, None),
    ("c103", "crawl", "103", None, "Sample", "State", None, "neighbours", 2005, [], None, None),
    ("b2026_1_1_23", "bucket", "2026_1_1_23", "MOTILAL OSWAL FINANCIAL SERVICES LIMITED versus SANTOSH CORDEIRO AND ANOTHER", None, None, "2026-01-05", "bucket", 2026,
     ["scr:2026:1:1", "insc:2026:5"], "[2026] 1 S.C.R. 1", "2026 INSC 5"),
]
for n, (key, src, sid, title, pet, resp, date, dsrc, year, cites, scr, insc) in enumerate(ROWS, 1):
    con.execute("INSERT INTO docs(id,doc_key,source,src_id,title,pet,resp,date,date_source,year,cites,citator,insc,scr_cite) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (n, key, src, sid, title, pet, resp, date, dsrc, year, json.dumps(cites), "[]", insc, scr))
    con.execute("INSERT INTO texts(id,text) VALUES (?,?)", (n, "text"))
EXTRA_CORPUS = [("n480_2015_2017-07-20", "court", SCI_URL, "STATE OF X versus Y", "2017-07-20", "court", 2017, ["insc:2017:640"], "2017 INSC 640", None),
                ("n1075_2010_2018-08-16", "court", "https://api.sci.gov.in/supremecourt/2010/1075/1075_2010_Judgement_16-Aug-2018.pdf", "MOHAN LAL versus THE STATE OF PUNJAB", "2018-08-16", "court", 2018, [], None, "c101"),
                ("nCrl_A_J_12_2018_2019-03-04", "court", "https://example.invalid/trap.pdf", "A SUPREME COURT CASE versus WITH A COLLIDING KEY", "2019-03-04", "court", 2019, [], None, None)]   # what a High Court record would map to if it were looked up
for n, (key, src, sid, title, date, dsrc, year, cites, insc, dup) in enumerate(EXTRA_CORPUS, len(ROWS) + 1):
    con.execute("INSERT INTO docs(id,doc_key,source,src_id,title,date,date_source,year,cites,citator,insc,dup_of) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (n, key, src, sid, title, date, dsrc, year, json.dumps(cites), "[]", insc, dup))
    con.execute("INSERT INTO texts(id,text) VALUES (?,?)", (n, "text"))
con.commit()
con.close()
CORPUS = K.Corpus(CORPUS_PATH)
cid = PI.CorpusIdentity(CORPUS, DOCS)
cidx = PI.CorpusIdentity(CORPUS, DOCS_X)
i = cid(101)
check(i.name == "Mohan Lal v. State of Punjab" and i.year == 2018 and i.date == "2018-07-24" and i.citation == "(2018) 17 SCC 627" and i.doc_key == "c101" and i.name_source == "corpus" and i.notes == (),
      "a crawl judgment is found by its id, with its date read from the header, and its reported citation written as text")
check(cid(102) is None and cid(999) is None, "a judgment the corpus cannot name, or does not hold, is not identified")
i = cid(103)
check(i.name == "Sample v. State" and i.year == 2005 and any("neighbours" in n for n in i.notes), "a name from petitioner and respondent, and a note when the year was estimated from neighbouring judgments")
i = cid(1003962500)
check(i.doc_key == "b2026_1_1_23" and i.name == "MOTILAL OSWAL FINANCIAL SERVICES LIMITED v. SANTOSH CORDEIRO AND ANOTHER" and i.citation == "[2026] 1 S.C.R. 1 ; 2026 INSC 5", "a bucket judgment is found through the path in the index's record, with both citations once each")
check(PI.CorpusIdentity(CORPUS, None)(1003962500) is None and PI.CorpusIdentity(CORPUS, DOCS)(1003962999) is None, "a bucket judgment cannot be found without the index record that holds its path")
i = cidx(2000250160)
check(i.doc_key == "n480_2015_2017-07-20" and i.name == "STATE OF X v. Y" and i.court == "Supreme Court" and i.date == "2017-07-20" and i.notes == () and i.citation == "2017 INSC 640",
      "a newer-archive judgment is found in the corpus by its diary number and decision date, and its court-record date counts as read from the court, not estimated")
i = cidx(2000250161)
check(i.doc_key == "c101" and i.name == "Mohan Lal v. State of Punjab" and i.year == 2018 and i.citation == "(2018) 17 SCC 627", "a second copy in the corpus is identified as the judgment it copies, so that its register row and card apply whichever copy a search found")
check(cidx(2000250162) is None and cidx(2000000010) is None and PI.CorpusIdentity(CORPUS, None)(2000250160) is None, "a record with no diary number, a High Court record, and a record the corpus cannot be asked about are not identified by the corpus")
chainx = PI.ChainIdentity(PI.CorpusIdentity(CORPUS, DOCS_X), whox)
check(chainx(2000250160).name_source == "corpus" and chainx(2000000010).name_source == "index_extra_title" and chainx(2000000010).court == "Gauhati High Court" and chainx(2000250162).name == "NO ID v. NOBODY",
      "the chain names a High Court judgment, or a newer record the corpus cannot place, from the index's own record")
chain = PI.ChainIdentity(PI.CorpusIdentity(CORPUS, DOCS), who)
check(chain(101).name_source == "corpus" and chain(7).name_source == "index_case_header" and chain(555) is None, "the chain asks the corpus first, then the index's record, then gives up")
check(chain(1003962500).name_source == "corpus" and who(1003962500).name_source == "index_bucket_title", "when both know a judgment, the corpus answer is the one used")

# ---- the connector ------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("the connector")
HIT = {"doc": 101, "i": 3, "pn": "14", "page": 9, "section": "reasoning", "h": "abc123", "text": "14. The Court held that the accused must be heard."}
before = copy.deepcopy(HIT)
p = PI.passage_from_hit(HIT, chain)
check(p["case_name"] == "Mohan Lal v. State of Punjab" and p["year"] == 2018 and p["citation"] == "(2018) 17 SCC 627" and p["court"] == "Supreme Court" and p["para"] == "14" and p["page"] == 9
      and p["text"] == HIT["text"] and p["identified"] is True and p["kind_label"] is None, "a hit becomes the formatter's passage: case, year, citation, court, paragraph, page and the text as it is")
check(HIT == before, "the hit is not changed")
check(p["source_info"] == {"index_doc": 101, "index_passage": 3, "hash": "abc123", "section": "reasoning", "text_changed": False, "name_source": "corpus", "date_source": "header", "doc_key": "c101", "notes": []},
      "and where it came from is kept: the index row, the corpus row, how the name and date were known")
p = PI.passage_from_hit(dict(HIT, doc=555), chain)
check(p["identified"] is False and "title not available" in p["case_name"] and p["year"] is None and p["citation"] is None and p["source_info"]["notes"] == ["judgment not identified"], "a judgment nobody can name is marked unidentified, with an honest placeholder title")
check(PI.passage_from_hit(HIT, None)["identified"] is False, "with no identity source nothing is identified")
p = PI.passage_from_hit(dict(HIT, text="a\x0cb"), chain)
pg = PI.passage_from_hit(dict(HIT, doc=2000000010), chainx)
check(pg["court"] == "Gauhati High Court" and pg["case_name"] == "STATE OF ASSAM v. RAM DAS" and pg["identified"] is True, "a High Court hit is labelled with its own court, never 'Supreme Court'")
check(PI.passage_from_hit(dict(HIT, doc=2000250160), chainx)["court"] == "Supreme Court" and PI.passage_from_hit(HIT, chain)["court"] == "Supreme Court" and PI.passage_from_hit(dict(HIT, doc=7), whox, court="Other Court")["court"] == "Other Court"
      and PI.passage_from_hit(HIT, chain, court="Other Court")["court"] == "Supreme Court", "a Supreme Court hit says so; the caller's court is used only when the identity names none, and the corpus (Supreme Court only) is not overruled by a caller")
check(p["text"] == "a b" and p["source_info"]["text_changed"] is True, "a control character in the text is replaced and the change is recorded")
check(PI.passage_from_hit(dict(HIT, section="argument"), chain)["kind_label"] == PI.KIND_LABELS["argument"] and PI.passage_from_hit(dict(HIT, section="made_up"), chain)["kind_label"] is None, "an argument passage gets its caution label; an unknown or reasoning tag gets none")
check(all(not CF.wording_violations(v) for v in PI.KIND_LABELS.values()) and "holding" not in " ".join(PI.KIND_LABELS.values()).lower(), "the labels pass the wording guard and never call a passage the Court's holding")
p = PI.passage_from_hit(dict(HIT, pn="preamble-1", page=None), chain)
check(p["para"] is None and p["page"] is None, "a preamble has no paragraph, and a missing page stays missing")
check("url" not in PI.passage_from_hit(HIT, chain) and "doc_id" not in PI.passage_from_hit(HIT, chain), "no link and no open action unless asked for")
check(PI.passage_from_hit(HIT, chain, open_action=True)["doc_id"] == 101 and PI.passage_from_hit(HIT, chain, link_for=lambda d, i: f"https://example.invalid/{d}")["url"] == "https://example.invalid/101", "an open action or a caller's link, when asked for")
check(raises(ValueError, PI.passage_from_hit, dict(HIT, text="  \x0c "), chain) and raises(ValueError, PI.passage_from_hit, {"text": "x"}, chain), "a hit with no text or no doc id is refused")

# ---- the real search code's hits ----------------------------------------------------------------------------------------------------------------------------------------------------
print("hits from the real search code (fake service, no network, no spend)")
sys.path.insert(0, os.path.join(HERE, "review_tools"))
try:
    import fake_pool_fixture as FX
except Exception as e:                                           # numpy or the search code not importable here: the rest of this part is skipped, said plainly
    FX = None
    print(f"[SKIP] the search engine could not be imported ({e!r})")
REG = R.Register.load()
CARDS = CR.load(os.path.join(HERE, "cards", "currency_cards.json"))
F = CF.Formatter(REG, CARDS, quiet_policy="coverage_note", today="2026-10-22")
if FX:
    eng = FX.engine()
    ids = eng.lists_for(FX.Q)["A today"]
    docs = PI.IndexDocs([{"doc": 100 + d, "passages": 10, "src": {"title": f"CASE {d} versus STATE OF TESTLAND", "date": "01-02-2010", "citation": f"[2010] {d + 1} S.C.R. {d + 5}", "case_id": f"2010 INSC {d + 1}", "path": f"p{d}"}}
                         for d in range(12)])
    ident = PI.IndexRowIdentity(docs)
    msgs, bad = [], []
    for rid in ids:
        hit = FX.metas[rid]
        p = PI.passage_from_hit(hit, ident)
        m = F.format(p, intro=False)
        msgs.append((hit, p, m))
        if hit["doc"] >= 200 and p["identified"]:
            bad.append("copy docs have no record but were identified")
    check(len(ids) == 10 and not bad, "the search returns ten hits and every one goes through the connector and the formatter")
    check(all(m.text.count("“") >= 1 and p["text"] in m.text for _, p, m in msgs), "each message holds its passage word for word")
    check(all(p["para"] == hit["pn"] and p["page"] == hit["page"] for hit, p, _ in msgs), "each keeps its paragraph number and page from the index row")
    check(all((p["identified"] and "CASE" in p["case_name"]) or (not p["identified"] and "NOT CHECKED BY US" in m.text and "could not identify" in m.text) for _, p, m in msgs), "an identified hit carries its case's name, and an unidentified one says so in the message")
    check(any(not p["identified"] for _, p, _ in msgs) is any(h["doc"] >= 200 for h, _, _ in msgs), "(the invented copies, docs 200 and 201, are the ones nobody can name)")
    hdr = [(h, p) for h, p, _ in msgs if h["section"] != "reasoning"]
    check(all(p["kind_label"] for h, p in hdr if h["section"] in PI.KIND_LABELS) and all(("Passage:" in m.text) == bool(p["kind_label"]) for _, p, m in msgs), "a passage tagged facts, argument or header carries its caution line in the message; a reasoning one carries none")
    batch = PI.format_hits(F, [h for h, _, _ in msgs], ident, shown=3)
    check(len(batch) == 4 and "Found 10 passages" in batch[0].text and "Showing 3" in batch[0].text, "a batch of hits gets its header message")

# ---- from a hit to a message, with the real register and cards ------------------------------------------------------------------------------------------------------------------------
print("from a hit to a message, with the real register and cards")
m = PI.format_hit(F, HIT, chain, intro=True)
check(m.lines[0].rule == 2 and m.lines[1].rule == 3 and "REPORTED ON THE OVERRULED REGISTER" in m.text and "REPORTED ADVERSE" in m.text and "Mukesh Singh" in m.text, "Mohan Lal's passage, named from the corpus, comes out with the register's and the checker's warnings")
check(m.text.index("REPORTED ADVERSE") < m.text.index("Mohan Lal v. State of Punjab\nSupreme Court") < m.text.index(HIT["text"]) and m.text.rstrip().endswith(CF.INTRO_FOOTER), "warning first, then the case, then the passage, then the not-verified line")
m = PI.format_hit(F, dict(HIT, doc=555), chain)
check(m.lines[0].rule == 6 and "NOT CHECKED BY US" in m.text and "could not identify" in m.text and "No register entry" not in m.text, "a passage from a judgment nobody can name says it could not be identified, never 'no register entry'")
m = PI.format_hit(F, dict(HIT, section="argument"), chain)
check("Passage: Appears to record counsel's arguments, not the Court's view." in m.text and m.text.index("Passage:") < m.text.index(HIT["text"]), "an argument passage says so under the case line")
m = PI.format_hit(F, dict(HIT, doc=1003962500), chain)
check(m.lines[0].rule in (5, 6) and "MOTILAL OSWAL" in m.text, "a bucket judgment's passage is named from its title and goes through the same rules")

tmp.cleanup()
print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
