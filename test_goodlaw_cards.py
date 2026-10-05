"""Tests for goodlaw/cards.py and goodlaw/cardreader.py: the precomputed currency cards, their wording, reviews, change report and reader. Run: python test_goodlaw_cards.py"""
import csv
import datetime
import gzip
import io
import json
import os
import tempfile

from goodlaw import cardreader as CR
from goodlaw import cards as CD
from goodlaw import corpus as K

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def mention(label, doc_key, year, bench=5, cue="overruled", relation="larger", sentence=None, **kw):
    m = {"doc_key": doc_key, "title": f"Judgment {doc_key}", "date": f"{year}-03-01", "year": year, "bench_size": bench, "bench_relation": relation, "label": label, "cue": cue, "speaker": "court",
         "confidence": "high", "hedged": False, "binding": "strong", "anaphoric": False, "kind": "overruled by this Court", "tier": "pair", "sentence": sentence or f"X v. Y {cue}.", "quote_verified": True}
    m.update(kw)
    return m


def bundle(triage, strong=(), possible=(), legislative=(), citator_over=(), citator_other=(), statute_flag=None, dimension=(), citing=5, weak=0):
    return {"triage": triage, "statute_flag": statute_flag, "statute_dimension": list(dimension), "recent_approving": [mention("FOLLOWS", "a1", 2024, cue="followed")],
            "coverage": {"collection_runs_to": "2026-08-12", "share_of_later_judgments_we_hold": 0.88, "later_years": [], "note": "n"},
            "summary": {"citing_judgments": citing, "latest_citing_year": 2025, "citing_in_last_10_years": 4, "by_treatment": {"FOLLOWS": 3}, "adverse_strong": list(strong), "adverse_possible": list(possible),
                        "legislative": list(legislative), "citator_adverse_overruled": list(citator_over), "citator_adverse_other": list(citator_other), "case_law_table": {}, "weak_signals_set_aside": weak}}


CASE = {"case_name": "Rangappa v Sri Mohan", "citation": "(2010) 11 SCC 441", "year": 2010, "court_class": "SC", "court": "Supreme Court of India", "pools": ["library"], "case_key": "rangappa",
        "recourse_currency": [{"doctrine_key": "rangappa_x", "status": "GOOD_LAW", "last_checked_date": "2026-09-01"}]}
MATCH = {"status": "MATCHED", "doc_key": "c1", "method": "citation", "confidence": "high", "note": None, "candidates": []}
DOC = {"doc_key": "c1", "title": "Rangappa v. Sri Mohan", "date": "2010-05-07", "year": 2010, "bench_size": 3, "source": "crawl", "cites": ["scr:2010:6:507"]}
INFO = {"judgments": {"crawl": 10, "bucket": 5}, "latest_judgment_date": "2026-08-12"}


def card(triage, **kw):
    b = bundle(triage, **kw)
    return CD.card_from_bundle(CASE, MATCH, DOC, b, "2026-10-05", "abc123", INFO, report_file="reports/rangappa_v_sri_mohan.md")


# ---------------------------------------------------------------- the wording
strong1 = [mention("OVERRULES", "b9", 2021, bench=5)]
c = card("ADVERSE_SIGNAL", strong=strong1)
check(c["user_facing_note"] == "A later five-judge bench of the Supreme Court (2021) appears to overrule or reject this case, in whole or in part, so check it before relying on this case.", "a five-judge bench: the note names the bench and the year, says 'appears to', and says to check")
c2 = card("ADVERSE_SIGNAL", strong=[mention("OVERRULES", "b9", 2021), mention("OVERRULES", "b8", 2019, bench=3)])
check(c2["user_facing_note"] == "Later Supreme Court judgments (the latest in 2021) appear to overrule or reject this case, in whole or in part, so check it before relying on this case.", f"more than one judgment: the plural form (got {c2['user_facing_note']!r})")
c3 = card("ADVERSE_SIGNAL", citator_over=[{"code": "O", "meaning": "overruled", "cite": "1996 SC 200", "paras": "(5)", "citing_case": {"doc_key": "c20", "title": "Overruler", "date": "1996-06-06"}}])
check(c3["user_facing_note"].startswith("The law reporters' own note marks this case as overruled") and c3["evidence"][0]["group"] == "citator" and "1996 SC 200" in c3["evidence"][0]["quote"], "only the reporter's citator: the note says so and the evidence carries the citator entry")
c4 = card("QUESTIONED", possible=[mention("DISAGREES", "b7", 2018, bench=2, relation="smaller", cue="unable to agree"), mention("DOUBTS_REFERS", "b6", 2019, cue="larger bench")], legislative=[mention("LEGISLATIVE", "b5", 2015, cue="Parliament amended")])
check(c4["user_facing_note"] == "Later Supreme Court judgments have disagreed with it and doubted it or referred it to a larger bench, and the legislature has since responded to it; its reach may be narrower than it first appears.", f"QUESTIONED lists what the evidence shows (got {c4['user_facing_note']!r})")
c5 = card("QUESTIONED", legislative=[mention("LEGISLATIVE", "b5", 2015, cue="Parliament amended")])
check(c5["user_facing_note"] == "The legislature has since responded to this case, so check whether the law has been changed.", "only a legislative response: that is all the note says")
check(card("NO_ADVERSE_FOUND")["user_facing_note"] is None and card("INSUFFICIENT", citing=1)["user_facing_note"] is None, "a case with nothing against it has no user-facing note at all")
every = [c, c2, c3, c4, c5, card("NO_ADVERSE_FOUND"), card("INSUFFICIENT", citing=1)]
check(all(not CR.check_wording(x["user_facing_note"]) and not CR.check_wording(x.get("statute_note")) for x in every), "no note says 'good law' or anything like it")
check("silence" in card("NO_ADVERSE_FOUND")["internal_note"] and "not a finding" in card("NO_ADVERSE_FOUND")["internal_note"], "the internal note for a quiet case says it is silence, not a finding")

dim = [{"act": "CrPC", "section": "200", "count": 4, "status": "renumbered", "note": "renumbered", "successors": [{"act": "BNSS", "section": "223", "change": False}]},
       {"act": "IPC", "section": "304B", "count": 1, "status": "renumbered", "note": "renumbered", "successors": [{"act": "BNS", "section": "80", "change": False}]},
       {"act": "NI Act", "section": "139", "count": 2, "status": "unaffected", "note": "not part of the 2023 recodification", "successors": []}]
cs = card("NO_ADVERSE_FOUND", statute_flag="STATUTE_CHANGED", dimension=dim)
check(cs["statute_note"] == "The judgment repeatedly discusses CrPC section 200 (renumbered as BNSS section 223). That is a change of number, not a finding that the ruling no longer applies.", f"the statute note is about a section the judgment repeatedly discusses, and about its number, not the doctrine (got {cs['statute_note']!r})")
check("304B" not in cs["statute_note"], "a section cited once is not mentioned")
check(card("NO_ADVERSE_FOUND", dimension=dim)["statute_note"] is None, "no flag, no statute note")
once = [dict(dim[1])] + [dict(dim[2])]
check(card("NO_ADVERSE_FOUND", statute_flag="STATUTE_CHANGED", dimension=once)["statute_note"] is None, "a renumbered section cited only once or twice gives no note at all")

# ---------------------------------------------------------------- the evidence kept for the reviewer
ev = card("ADVERSE_SIGNAL", strong=[mention("OVERRULES", f"b{i}", 2010 + i) for i in range(5)], possible=[mention("DISAGREES", "p1", 2012)], weak=2)["evidence"]
check([e["group"] for e in ev].count("strong") == 3 and ev[0]["year"] == 2014, "at most three strong pieces of evidence, newest first")
long_sentence = "word " * 300
e = card("ADVERSE_SIGNAL", strong=[mention("OVERRULES", "b1", 2020, sentence=long_sentence)])["evidence"][0]
check(len(e["quote"]) <= 705 and e["quote_truncated"] and e["quote"].endswith("..."), "a very long quote is cut, and says it was cut")
weak_card = card("NO_ADVERSE_FOUND", possible=[mention("OVERRULES", "w1", 2019, weak=True, binding="weak")])
check([e["group"] for e in weak_card["evidence"]] == ["weak"] and weak_card["user_facing_note"] is None, "a weak reading set aside is kept as evidence for the reviewer but says nothing to the user")

# ---------------------------------------------------------------- fingerprints and reviews
a, b = card("ADVERSE_SIGNAL", strong=strong1), card("ADVERSE_SIGNAL", strong=strong1)
check(a["fingerprint"] == b["fingerprint"] and len(a["fingerprint"]) == 12, "the same findings give the same fingerprint")
d = card("ADVERSE_SIGNAL", strong=strong1 + [mention("OVERRULES", "b10", 2022)])
check(d["fingerprint"] != a["fingerprint"], "new evidence changes it")
cards_ = [a]
CD.attach_reviews(cards_, [{"case_name": "Rangappa v Sri Mohan", "fingerprint": a["fingerprint"], "verdict": "FALSE_ALARM", "reviewer": "R", "date": "2026-10-06"}])
check(cards_[0]["review"]["current"] is True, "a review of the evidence now on the card is current")
cards_ = [d]
CD.attach_reviews(cards_, [{"case_name": "Rangappa v Sri Mohan", "fingerprint": a["fingerprint"], "verdict": "FALSE_ALARM", "reviewer": "R", "date": "2026-10-06"}])
check(cards_[0]["review"]["current"] is False, "a review of earlier evidence is kept but not current")

# ---------------------------------------------------------------- what changed since the last run
old = [card("NO_ADVERSE_FOUND")]
new = [card("ADVERSE_SIGNAL", strong=strong1)]
ch = CD.compare(old, new)
check(ch and ch[0]["kind"] == "status changed" and ch[0]["detail"] == "NO_ADVERSE_FOUND -> ADVERSE_SIGNAL" and ch[0]["worse"], "a case that moved towards a warning is reported first as worse")
check(CD.compare(new, [card("ADVERSE_SIGNAL", strong=strong1)]) == [], "nothing changed: nothing is reported")
ch2 = CD.compare([card("QUESTIONED", possible=[mention("DISAGREES", "p1", 2012)])], [card("QUESTIONED", possible=[mention("DISAGREES", "p1", 2012), mention("DOUBTS_REFERS", "p2", 2020)])])
check(any(x["kind"] == "new evidence" and "p2" in x["detail"] for x in ch2), "new evidence under the same status is reported")
moved = card("NO_ADVERSE_FOUND")
moved["corpus"]["doc_key"] = "c2"
check(any(x["kind"] == "matched judgment changed" for x in CD.compare(old, [moved])), "a case that now matches a different judgment is reported")
check(any(x["kind"] == "new case" for x in CD.compare([], new)) and any(x["kind"] == "no longer in the library" for x in CD.compare(new, [])), "cases that appear or disappear are reported")
tmp = tempfile.mkdtemp(prefix="cards_test_")
CD.write_changes(ch, os.path.join(tmp, "CHANGES.md"), "2026-10-05")
check("NO_ADVERSE_FOUND -> ADVERSE_SIGNAL" in open(os.path.join(tmp, "CHANGES.md")).read() and "**Rangappa v Sri Mohan**" in open(os.path.join(tmp, "CHANGES.md")).read(), "the change report is written, the worse ones in bold")

# ---------------------------------------------------------------- the review sheet and its round trip
flagged = card("ADVERSE_SIGNAL", strong=strong1)
other_case = dict(CASE, case_name="Other v State", recourse_currency=[])
quiet = CD.card_from_bundle(other_case, MATCH, DOC, bundle("NO_ADVERSE_FOUND"), "2026-10-05", "abc", INFO)
questioned = CD.card_from_bundle(dict(CASE, case_name="Third v State", recourse_currency=[]), MATCH, DOC, bundle("QUESTIONED", possible=[mention("DISAGREES", "p1", 2012)]), "2026-10-05", "abc", INFO)
amb = CD.unchecked_card(dict(CASE, case_name="Fourth v State", recourse_currency=[]), {"status": "AMBIGUOUS_MATCH", "method": "name_year", "confidence": None, "note": "two judgments", "candidates": [{"doc_key": "x1", "title": "T", "year": 2000}]}, "2026-10-05", "abc", INFO)
hc = CD.unchecked_card(dict(CASE, case_name="Fifth v State"), {"status": "NOT_CHECKABLE_HIGH_COURT", "method": None, "confidence": None, "note": "High Court", "candidates": []}, "2026-10-05", "abc", INFO)
rows = CD.review_rows([quiet, questioned, hc, amb, flagged])
check([r["case_name"] for r in rows] == ["Rangappa v Sri Mohan", "Third v State", "Fourth v State"], "the sheet lists flagged and ambiguous cases only, the one Recourse calls GOOD_LAW first")
check(rows[0]["why_in_sheet"].startswith("Recourse's record says GOOD_LAW but the checker says ADVERSE_SIGNAL") and "GOOD_LAW (rangappa_x" in rows[0]["recourse_curated_status"], "and says why, with Recourse's own status beside it")
sheet = os.path.join(tmp, "REVIEW_SHEET.csv")
check(CD.write_review_sheet([quiet, questioned, hc, amb, flagged], sheet) == 3, "the sheet is written")
with open(sheet, encoding="utf-8", newline="") as fh:
    table = list(csv.DictReader(fh))
table[0].update(your_verdict="confirmed adverse", reviewer="Dr R", review_date="2026-10-07", note="read para 12")
table[1].update(your_verdict="maybe")
table[2].update(your_verdict="")
with open(sheet, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=CD.SHEET_COLUMNS)
    w.writeheader()
    w.writerows(table + [dict(table[2], case_name="No Such v Case", your_verdict="FALSE_ALARM")])
reviews_path = os.path.join(tmp, "reviews.json")
recorded, problems = CD.merge_review_sheet(sheet, [quiet, questioned, hc, amb, flagged], reviews_path, today="2026-10-08")
check(recorded == 1 and len(problems) == 2 and any("maybe" in p for p in problems) and any("No Such" in p for p in problems), "one verdict recorded; an unknown verdict and an unknown case are reported, a blank is skipped")
saved = json.load(open(reviews_path))["reviews"][0]
check(saved["verdict"] == "CONFIRMED_ADVERSE" and saved["fingerprint"] == flagged["fingerprint"] and saved["reviewer"] == "Dr R" and saved["date"] == "2026-10-07", "the record carries the verdict, the fingerprint of what was reviewed, the reviewer and the date")
match_csv = os.path.join(tmp, "MATCH_CHECK.csv")
check(CD.write_match_check([quiet, amb, hc], match_csv) == 3 and open(match_csv).read().splitlines()[1].startswith("Fourth v State"), "the match list puts the uncertain matches first")

# ---------------------------------------------------------------- the reader
doc = {"generated": "2026-10-05", "counts": {}, "cards": [flagged, quiet, questioned]}
idx = CR.load(doc)
check(CR.find(idx, case_name="Rangappa v Sri Mohan") is flagged, "a case is found by the exact name the chunks carry")
check(CR.find(idx, case_name="Rangappa vs. Sri Mohan") is flagged and CR.find(idx, case_name="rangappa v. sri mohan") is flagged, "or by the name with punctuation and 'v'/'vs' ignored")
check(CR.find(idx, case_name="Unknown v Nobody", citation="(2010) 11 SCC 441") is flagged and CR.find(idx, citation="[2010] 6 S.C.R. 507") is flagged, "or by a citation, including the judgment's own SCR citation")
check(CR.find(idx, case_name="Unknown v Nobody") is None, "an unknown case has no card")
r = CR.for_answer(flagged, today="2026-10-10")
check(r["level"] == "warning" and r["user_facing_note"].startswith("A later five-judge bench") and r["decided_by"] == "checker" and not r["stale"], "a flagged case gives a warning with its note, decided by the checker")
r = CR.for_answer(quiet, today="2026-10-10")
check(r["level"] == "none" and r["user_facing_note"] is None, "a quiet case gives nothing to say")
check(CR.for_answer(questioned, today="2026-10-10")["level"] == "caution", "a questioned case gives a caution")
check(CR.for_answer(None)["status"] == "NO_CARD" and CR.for_answer(None)["user_facing_note"] is None, "no card: nothing to say, and it says why in the internal note")
check(CR.for_answer(flagged, today="2026-12-30")["stale"] is True and "rebuild it" in CR.for_answer(flagged, today="2026-12-30")["internal_note"], "a card older than 45 days is stale, and says to rebuild")
for verdict, level, has_note in [("CONFIRMED_ADVERSE", "warning", True), ("FALSE_ALARM", "none", False), ("NEEDS_RESEARCH", "warning", True)]:
    rc = json.loads(json.dumps(flagged))
    rc["review"] = {"verdict": verdict, "reviewer": "Dr R", "date": "2026-10-07", "current": True}
    r = CR.for_answer(rc, today="2026-10-10")
    check(r["level"] == level and bool(r["user_facing_note"]) == has_note and r["decided_by"].startswith("human review (Dr R"), f"a current review {verdict} sets the level to {level}")
check(CR.for_answer(dict(flagged, review={"verdict": "FALSE_ALARM", "reviewer": "x", "date": "d", "current": True}), today="2026-10-10")["level"] == "none", "a false-alarm review silences the warning")
rc = json.loads(json.dumps(flagged))
rc["review"] = {"verdict": "FALSE_ALARM", "reviewer": "Dr R", "date": "2026-10-07", "current": False}
r = CR.for_answer(rc, today="2026-10-10")
check(r["level"] == "warning" and "no longer applies" in r["internal_note"], "a review of earlier evidence does not silence a warning")
rc = json.loads(json.dumps(flagged))
rc["review"] = {"verdict": "NEEDS_RESEARCH", "reviewer": "Dr R", "date": "2026-10-07", "current": True}
check(CR.for_answer(rc, today="2026-10-10")["under_review"] is True, "needs-research is flagged as under review")
bad = json.loads(json.dumps(flagged))
bad["user_facing_note"] = "This case is still good law."
r = CR.for_answer(bad, today="2026-10-10")
check(r["user_facing_note"] is None and "withheld" in r["internal_note"], "a note containing a forbidden phrase is withheld, whatever put it there")
check(CR.check_wording("Still valid and GOOD LAW") == ["good law", "still valid"] or set(CR.check_wording("Still valid and GOOD LAW")) == {"good law", "still valid"}, "the wording guard is case-insensitive")

# ---------------------------------------------------------------- the whole build on a small corpus
def judis(pet, resp, date, bench, air, body):
    b = "\n".join(bench)
    return (f"http://JUDIS.NIC.IN\nSUPREME COURT OF INDIA\nPage 1 of 4\nPETITIONER:\n{pet}\n        Vs.\nRESPONDENT:\n{resp}\nDATE OF JUDGMENT:\n{date}\nBENCH:\n{bench[0]}\nBENCH:\n{b}\n"
            f"CITATION:\n {air}\nACT:\nSome Act.\nHEADNOTE:\nHeadnote words.\nJUDGMENT:\n{body}\n")


PAD = " ".join(f"fill{i}" for i in range(150))
JUDGES = ["SARKAR, A.K.", "SHAH, J.C.", "RAY, A.N.", "KHANNA, H.R.", "MATHEW, K.K.", "BEG, M.H.", "CHANDRACHUD, Y.V."]
DOCS = {
    1: judis("ALPHA", "BETA", "05/05/1990", JUDGES[:3], "1991 AIR 11", "Alpha holds. " + PAD),
    2: judis("EPSILON", "ZETA", "05/05/1990", JUDGES[:2], "1991 AIR 33", "Epsilon holds. " + PAD),
    3: judis("GAMMA", "DELTA", "05/05/1990", JUDGES[:2], "1991 AIR 44", "Gamma holds. " + PAD),
    10: judis("P10", "SOME RESPONDENT", "03/03/2000", JUDGES[:5], "2001 AIR 901", "Alpha v. Beta, AIR 1991 SC 11 stands overruled. " + PAD),
    11: judis("P11", "SOME RESPONDENT", "05/03/2000", JUDGES[:3], "2002 AIR 902", "Epsilon v. Zeta, AIR 1991 SC 33 was followed. " + PAD),
    12: judis("P12", "SOME RESPONDENT", "06/03/2001", JUDGES[:3], "2003 AIR 903", "The law laid down in Epsilon v. Zeta, AIR 1991 SC 33 is reiterated. " + PAD),
    13: judis("P13", "SOME RESPONDENT", "07/03/2005", JUDGES[:3], "2004 AIR 904", "We respectfully agree with Epsilon v. Zeta, AIR 1991 SC 33. " + PAD),
    14: judis("P14", "SOME RESPONDENT", "08/03/2000", JUDGES[:2], "2005 AIR 905", "Reference is made to Gamma v. Delta, AIR 1991 SC 44. " + PAD),
}


def write_gz(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write(content)


base = tempfile.mkdtemp(prefix="cards_corpus_")
write_gz(os.path.join(base, "crawl", "shards", "000000-000249.ok.gap0.err0.jsonl.gz"), "".join(json.dumps({"id": i, "status": "ok", "text": t, "pages": 2}) + "\n" for i, t in DOCS.items()))
write_gz(os.path.join(base, "bucket", "shards", "after-0000.ok0.miss0.err0.jsonl.gz"), "")
buf = io.StringIO()
csv.DictWriter(buf, fieldnames=["decision_date", "title", "path", "tier", "citation", "case_id", "crawl_ids"]).writeheader()
write_gz(os.path.join(base, "registry.csv.gz"), buf.getvalue())
write_gz(os.path.join(base, "none.csv.gz"), "path,title,decision_date,key,status,best_crawl_id,shared_runs,frac,in_crawl\n")
corpus_path = os.path.join(base, "corpus.sqlite")
K.build(os.path.join(base, "crawl"), os.path.join(base, "bucket"), os.path.join(base, "registry.csv.gz"), os.path.join(base, "none.csv.gz"), corpus_path, workers=1, log=lambda *_: None)
K.index_cites(corpus_path, workers=1, chunk=5, log=lambda *_: None)

library = [
    {"case_name": "Alpha v Beta", "citation": "AIR 1991 SC 11", "court": "Supreme Court of India", "pools": ["library"], "recourse_currency": []},
    {"case_name": "Epsilon v Zeta", "citation": "AIR 1991 SC 33", "court": "Supreme Court of India", "pools": ["library"], "recourse_currency": []},
    {"case_name": "Gamma v Delta", "citation": "AIR 1991 SC 44", "court": "Supreme Court of India", "pools": ["pilot_tier"], "recourse_currency": []},
    {"case_name": "Nobody v Nowhere", "citation": "(2005) 1 SCC 1", "court": "Supreme Court of India", "pools": ["library"], "recourse_currency": []},
    {"case_name": "Some v High Court Case", "citation": "2025 SCC OnLine Del 1", "court": "High Court of Delhi", "pools": ["library"], "recourse_currency": []},
]
for c in library:
    c["court_class"] = CD.LB.court_class(c)
    c["year"] = CD.LB.year_of(c["citation"])
built, reports = CD.build_all(corpus_path, library, today="2026-10-05", workers=2, log=lambda *_: None)
by = {c["case"]["name"]: c for c in built}
check([c["case"]["name"] for c in built] == [c["case_name"] for c in library], "one card per library case, in the library's order")
check(by["Alpha v Beta"]["status"] == "ADVERSE_SIGNAL" and by["Alpha v Beta"]["corpus"]["doc_key"] == "c1" and by["Alpha v Beta"]["user_facing_note"].startswith("A later five-judge bench"), "the whole build: a case a larger bench overruled gets a warning card")
check(by["Epsilon v Zeta"]["status"] == "NO_ADVERSE_FOUND" and by["Epsilon v Zeta"]["user_facing_note"] is None and by["Epsilon v Zeta"]["support"]["citing_judgments"] == 3, "a case three judgments follow gets a quiet card with no note")
check(by["Gamma v Delta"]["status"] == "INSUFFICIENT", "a case cited once is INSUFFICIENT")
check(by["Nobody v Nowhere"]["status"] == "NOT_IN_COLLECTION" and by["Some v High Court Case"]["status"] == "NOT_CHECKABLE_HIGH_COURT", "a case we do not hold and a High Court case are said to be unchecked, not quietly clean")
check(all(c["provenance"]["generated"] == "2026-10-05" and c["provenance"]["label"] == CD.LABEL_TEXT and c["fingerprint"] for c in built), "every card carries its date, its source label and a fingerprint")
check(set(reports) == {"alpha_v_beta", "epsilon_v_zeta", "gamma_v_delta"} and "Currency report" in reports["alpha_v_beta"], "a readable report is kept for each checked case")
out_dir = os.path.join(tmp, "out")
written = CD.write_cards(built, reports, out_dir)
loaded = CR.load(os.path.join(out_dir, "currency_cards.json"))
check(written["counts"]["ADVERSE_SIGNAL"] == 1 and CR.for_answer(CR.find(loaded, case_name="Alpha v Beta"), today="2026-10-06")["level"] == "warning", "the saved file loads in the reader and the warning comes through")
check(os.path.exists(os.path.join(out_dir, "reports", "alpha_v_beta.md")), "the reports are written beside it")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
