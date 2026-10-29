"""test_sci_anchors.py -- sci_anchors.py: the word-for-word check, the export gate, the reviewer's confirmation and the sheet. Offline and free (a fake PDF text, no network).
Run: python test_sci_anchors.py"""
import copy
import glob
import gzip
import json
import os
import sys
import tempfile

import sci_anchors as SA

FAILURES = []
HERE = os.path.dirname(os.path.abspath(__file__))


def check(cond, msg):
    print(f"[{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        FAILURES.append(msg)


# ---- normalisation: the same words in the same order give the same string
check(SA.norm("A.R. Antulay’s case is “correct” — and still holds the field.") == SA.norm("a.r. antulay's CASE is 'correct' and still   holds the\nfield"), "quotes, dashes, capitals, line breaks and spacing do not matter")
check(SA.norm("end of one line.\nhttp://JUDIS.NIC.IN                SUPREME COURT OF INDIA                Page 15 of 16\nstart of the next") == "end of one line start of the next", "the court's page header inside a paragraph is removed")

SRC = SA.norm("""In conclusion we hold:-
(1)    The dictum in A.R. Antulay’s case is correct and still holds the field.
(2)    It is neither advisable, nor feasible, nor judicially permissible to draw or prescribe an outer limit for conclusion of all criminal proceedings.
http://JUDIS.NIC.IN                SUPREME COURT OF INDIA                Page 15 of 16
The criminal courts are not obliged to terminate trial merely on account of lapse of time.""")
check(SA.find_segment("The dictum in A.R. Antulay's case is correct and still holds the field.", SRC), "a segment that is in the source is found")
check(SA.find_segment("outer limit for conclusion of all criminal proceedings. The criminal courts are not obliged to terminate trial", SRC), "a segment that runs across the page header is found")
check(not SA.find_segment("The dictum in A.R. Antulay's case is incorrect and still holds the field.", SRC), "negative control: one changed word is NOT found")
check(not SA.find_segment("The dictum in A.R. Antulay's case is correct and still holds the whole field.", SRC), "negative control: one added word is NOT found")
check(not SA.find_segment("The dictum in A.R. Antulay's case is correct and holds the field.", SRC), "negative control: one dropped word is NOT found")
check(not SA.find_segment("holds the field still and correct is case", SRC) and not SA.find_segment("", SRC), "negative control: the same words in another order, or nothing, is NOT found")
check(not SA.find_segment("time", SRC[:SRC.index("lapse of time") - 3]), "a word is matched whole, not as part of another word")
near, ratio = SA.nearest("The dictum in Antulay's case is incorrect and still holds the field", SRC)
check(near and "dictum" in near and ratio > 0.8, f"the nearest stretch is reported for a near miss ({near!r}, {ratio})")

# ---- verify_anchor with a fake fetch and a fake text
ANCHOR = {"id": "t1", "link": "https://example.invalid/x.pdf", "excerpts": [
    {"label": "A", "segments": ["The dictum in A.R. Antulay’s case is correct and still holds the field.", "It is neither advisable, nor feasible, nor judicially permissible to draw or prescribe an outer limit."]},
    {"label": "B", "segments": ["The criminal courts are not obliged to terminate trial merely on account of lapse of time."]}]}
RAW = """In conclusion we hold:-
(1) The dictum in A.R. Antulay’s case is correct and still holds the field.
(2) It is neither advisable, nor feasible, nor judicially permissible to draw or prescribe an outer limit for conclusion of all criminal proceedings.
http://JUDIS.NIC.IN SUPREME COURT OF INDIA Page 1 of 2
The criminal courts are not obliged to terminate trial merely on account of lapse of time."""
tmp = tempfile.mkdtemp()
pdf = os.path.join(tmp, "f.pdf")
open(pdf, "wb").write(b"%PDF fake")
r = SA.verify_anchor(ANCHOR, tmp, None, fetch=lambda url, d: pdf, text_of=lambda p: RAW)
check(r["ok"] and r["check"]["all_found"] and r["check"]["segments_checked"] == 3 and len(r["check"]["sha256"]) == 64 and r["check"]["pages"] == 1 and r["check"]["url"] == ANCHOR["link"], f"all segments found: ok ({r['check']['segments_checked']} checked)")
bad = copy.deepcopy(ANCHOR)
bad["excerpts"][1]["segments"] = ["The criminal courts are not obliged to terminate trial merely on account of the lapse of time."]
rb = SA.verify_anchor(bad, tmp, None, fetch=lambda url, d: pdf, text_of=lambda p: RAW)
check(not rb["ok"] and not rb["check"]["all_found"] and rb["failures"][0]["excerpt"] == "B" and rb["failures"][0]["nearest"], "a segment with one added word fails and says where and what is nearest")

# ---- 'also_in' phrases are checked against a later judgment in the index (a small fake shard)
idx = tempfile.mkdtemp()
with gzip.open(os.path.join(idx, "000000-000099.docs1.meta.jsonl.gz"), "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({"doc": 7, "i": 1, "text": "In para 29 it was observed as follows: the dictum is correct"}) + "\n")
    fh.write(json.dumps({"doc": 7, "i": 0, "text": "what this Court observed in P. Ramachandra Rao v. State of Karnataka (2002 (4) SCC 578)."}) + "\n")
    fh.write(json.dumps({"doc": 8, "i": 0, "text": "another judgment"}) + "\n")
check([p["i"] for p in SA.index_passages(idx, 7)] == [0, 1] and SA.index_passages(idx, 500) == [], "the index reader returns one judgment's passages in order, and nothing for a judgment it does not hold")
anc2 = dict(ANCHOR, also_in=[{"doc": 7, "name": "Balbir", "must_contain": ["P. Ramachandra Rao v. State of Karnataka (2002 (4) SCC 578)", "In para 29 it was observed as follows"]}])
r2 = SA.verify_anchor(anc2, tmp, idx, fetch=lambda url, d: pdf, text_of=lambda p: RAW)
check(r2["ok"] and r2["check"]["also_in"][0]["found"] is True, "the citation and paragraph shown elsewhere are found in the later judgment")
anc3 = dict(ANCHOR, also_in=[{"doc": 7, "name": "Balbir", "must_contain": ["In para 31 it was observed"]}])
check(not SA.verify_anchor(anc3, tmp, idx, fetch=lambda url, d: pdf, text_of=lambda p: RAW)["ok"], "negative control: a phrase the later judgment does not hold fails the check")

# ---- the data file, export gate, confirmation, sheet (on a copy of the data)
real = SA.load()
check(real["schema"] == SA.SCHEMA and len(real["anchors"]) >= 2, "anchors/anchors.json loads")
check(all((a.get("check") or {}).get("all_found") and a["check"]["segments_checked"] == sum(len(e["segments"]) for e in a["excerpts"]) and len(a["check"]["sha256"]) == 64 for a in real["anchors"]), "every anchor has a passing check that covered every segment")
check(all(a["status"] in SA.STATUSES and a["link"].startswith("https://api.sci.gov.in/") and a["case_name"] and a["year"] for a in real["anchors"]), "every anchor has a status, the official link, a name and a year")
check(not any("good law" in SA.excerpt_text(e).lower().replace("are not good law", "") for a in real["anchors"] for e in a["excerpts"] if "are not good law" not in SA.excerpt_text(e).lower()), "no excerpt says a case is good law (the one court sentence 'are not good law' is the Bench's own)")
work = os.path.join(tempfile.mkdtemp(), "anchors.json")
doc = copy.deepcopy(real)
doc["anchors"].append({"id": "unchecked", "topic": "x", "case_name": "X v. Y", "year": 2000, "link": "https://api.sci.gov.in/x.pdf", "excerpts": [{"label": "L", "segments": ["s"]}], "status": "machine_checked"})
SA.DATA = work
SA.save(doc)
out = tempfile.mkdtemp()
rc = SA.main(["export", "--out", out])
exported = json.load(open(os.path.join(out, "excerpt_anchors.json"), encoding="utf-8"))
check(rc == 1 and [a["id"] for a in exported["anchors"]] == [a["id"] for a in real["anchors"]], "export writes only the anchors that passed the check, and reports the one that did not (exit 1)")
SA.save(real)
out2 = tempfile.mkdtemp()
check(SA.main(["export", "--out", out2]) == 0 and len(json.load(open(os.path.join(out2, "excerpt_anchors.json")))["anchors"]) == len(real["anchors"]), "with all checked, export is clean (exit 0)")
check(SA.main(["confirm", real["anchors"][0]["id"], "--by", "Mr. Advocate", "--on", "2026-10-20"]) == 0, "confirm runs")
after = SA.load()
check(after["anchors"][0]["status"] == "reviewer_confirmed" and after["anchors"][0]["confirmed_by"] == "Mr. Advocate" and after["anchors"][0]["confirmed_on"] == "2026-10-20" and after["anchors"][1]["status"] == "machine_checked", "the reviewer's confirmation is recorded on that anchor only")
check(SA.main(["confirm", "no_such_anchor", "--by", "x"]) == 1, "an unknown anchor id is refused")
SA.save(real)
md = SA.sheet_markdown(real)
check(all(SA.excerpt_text(e) in md.replace("\n", " ") or SA.excerpt_text(e)[:200] in md for a in real["anchors"] for e in a["excerpts"]), "the sheet carries every excerpt's words")
check(all(a["link"] in md for a in real["anchors"]) and "Until you confirm" in md and "Are these exactly the judgment's words?" in md and "Has the Supreme Court, or a statute, since changed or limited this?" in md, "the sheet carries the official links and asks the reviewer the questions")
check("is good law" not in md.lower() and "29" in md and "(2002) 4 SCC 578" in md, "the sheet never says a case is good law; it shows the paragraph and citation we would display")
outs = tempfile.mkdtemp()
check(SA.main(["sheet", "--out", outs]) == 0 and os.path.exists(os.path.join(outs, "ANCHOR_SHEET_trial_delay.md")), "the sheet command writes the Markdown file")
SA.DATA = os.path.join(HERE, "anchors", "anchors.json")

# ---- old printed reports (the landmark topic, 2026-10-29): what a check may look past, and what it may not
OLD_RAW = """The circumstances should be fully estab-
lished and the facts so established should be consistent only with the hypothesis of the guilt of the accused.(1) Again,
1043
the circumstances should be of a conclusive nature and tendency."""
OLD_SEG = "The circumstances should be fully established and the facts so established should be consistent only with the hypothesis of the guilt of the accused. Again, the circumstances should be of a conclusive nature and tendency."
OLD = {"id": "old1", "link": "https://example.invalid/old.pdf", "excerpts": [{"label": "P", "segments": [OLD_SEG]}]}


def _verify(anchor, raw=OLD_RAW):
    return SA.verify_anchor(anchor, tmp, None, fetch=lambda url, d: pdf, text_of=lambda p: raw)


check(not _verify(OLD)["ok"], "old report, no options: a split word, a footnote mark and a page number inside the sentence fail the check (the default is strict)")
check(not _verify(dict(OLD, verify_options={"join_hyphens": True}))["ok"], "join_hyphens alone does not excuse the footnote mark and the page number")
full = {"ignore_page_numbers": True, "ignore_footnote_marks": True, "join_hyphens": True}
ro = _verify(dict(OLD, verify_options=full))
check(ro["ok"] and ro["check"]["options"] == full and "page number" in ro["check"]["method"] and "footnote marks" in ro["check"]["method"] and "hyphens" in ro["check"]["method"] and "No word was ignored" in ro["check"]["method"], "with the three options the same words pass, and the record says what was looked past")
check("options" not in r["check"] and "looked past" not in r["check"]["method"], "an anchor with no options keeps its old record (no 'options', no allowance sentence)")
changed = copy.deepcopy(OLD)
changed["excerpts"][0]["segments"] = [OLD_SEG.replace("guilt of the accused", "innocence of the accused")]
check(not _verify(dict(changed, verify_options=full))["ok"], "negative control: with every option on, a changed word still fails")
dropped_word = copy.deepcopy(OLD)
dropped_word["excerpts"][0]["segments"] = [OLD_SEG.replace("fully ", "")]
check(not _verify(dict(dropped_word, verify_options=full))["ok"], "negative control: with every option on, a dropped word still fails")

# page numbers: only a line that holds nothing but one to four digits
check("1043" not in SA.source_variants("a\n1043\nb", {"ignore_page_numbers": True})[0] and "1043 persons" in SA.source_variants("a\n1043 persons\nb", {"ignore_page_numbers": True})[0] and "1043" in SA.source_variants("a\n1043\nb")[0], "page numbers: a line of digits alone is dropped; digits within a line of words are not; without the option nothing is dropped")
# footnote marks: stuck to a word, one or two digits (or the OCR's (l)); a list number after a space is kept
fm = SA.source_variants("Pradesh.(1) It held that (1) the accused, and Pradesh.(l) Next", {"ignore_footnote_marks": True})
check(SA.norm(fm[0]) == "pradesh it held that 1 the accused and pradesh next", "footnote marks: '(1)' and '(l)' stuck to a word are dropped in the first reading; a list number after a space is kept")
check(len(fm) == 2 and SA.norm(fm[1]) == "pradesh 1 it held that 1 the accused and pradesh l next", "footnote marks: the text is also read with the marks kept")
# the loophole closed: a bracketed number that is part of the segment's own words must match exactly
BR = {"id": "br", "link": "https://example.invalid/b.pdf", "verify_options": {"ignore_footnote_marks": True}, "excerpts": [{"label": "S", "segments": ["The accused shall be examined under section 313(2) of the Code."]}]}
BR_RAW = "The accused shall be examined under section 313(2) of the Code."
check(_verify(BR, BR_RAW)["ok"], "a segment that holds its own bracketed number ('313(2)') passes when the archive has it")
BR_BAD = copy.deepcopy(BR)
BR_BAD["excerpts"][0]["segments"] = ["The accused shall be examined under section 313(3) of the Code."]
check(not _verify(BR_BAD, BR_RAW)["ok"], "negative control: a WRONG bracketed number ('313(3)' for '313(2)') fails (it was once looked past on both sides)")
BR_PLAIN = copy.deepcopy(BR)
BR_PLAIN["excerpts"][0]["segments"] = ["The accused shall be examined under section 313 of the Code."]
check(_verify(BR_PLAIN, BR_RAW)["ok"], "a segment written without the bracket still matches the reading with the mark dropped")
# footnote lines inside a sentence: exact lines only
FN_RAW = "It is well to remember that the rule is\n(1) (1838) 2 Lew. 227.\nthat the circumstances must be fully proved."
FN = {"id": "fn", "link": "https://example.invalid/f.pdf", "excerpts": [{"label": "F", "segments": ["It is well to remember that the rule is that the circumstances must be fully proved."]}]}
check(not _verify(FN, FN_RAW)["ok"] and _verify(dict(FN, verify_options={"ignore_lines": ["(1) (1838) 2 Lew. 227."]}), FN_RAW)["ok"], "ignore_lines: the named footnote line is looked past, and only then")
check(not _verify(dict(FN, verify_options={"ignore_lines": ["(1) (1838) 2 Lew. 228."]}), FN_RAW)["ok"], "negative control: a line that is not exactly the footnote line is not dropped")
check("(1) (1838) 2 Lew. 227." in SA.describe_options({"ignore_lines": ["(1) (1838) 2 Lew. 227."]}) and SA.describe_options({}) == "" and SA.describe_options(None) == "", "the allowance sentence names the footnote line; no options, no sentence")

# ---- the real landmark anchors: what was looked past, and that it is on record
by_id = {a["id"]: a for a in real["anchors"]}
sarda, han = by_id["circumstantial_evidence_sharad_sarda"], by_id["circumstantial_evidence_hanumant"]
check(sarda["topic"] == han["topic"] == "circumstantial_evidence" and sarda["status"] == han["status"] == "machine_checked" and not sarda.get("confirmed_by") and not han.get("confirmed_by"), "the two landmark anchors are machine_checked and confirmed by nobody")
check(sarda["check"]["options"] == sarda["verify_options"] and han["check"]["options"] == han["verify_options"] and "looked past" in sarda["check"]["method"], "what each check looked past is written into its record")
check(all(r_["found"] is True for a in (sarda, han) for r_ in a["check"]["also_in"]) and len(sarda["check"]["also_in"]) == 8 and len(han["check"]["also_in"]) == 2, "the paragraph numbers and the AIR citation are each backed by later judgments that quote them (8 and 2), all found")
check(sarda["aliases"] == ["Sharad Sarda"] and "aliases" not in han, "the short name the labeller may look for is data on the Sarda anchor only")
check(SA.TOPIC_INFO.keys() >= {a.get("topic") for a in real["anchors"]}, "every topic in the data has sheet wording")

# ---- the sheet, per topic
outc = tempfile.mkdtemp()
check(SA.main(["sheet", "--out", outc, "--topic", "circumstantial_evidence"]) == 0 and sorted(os.listdir(outc)) == sorted(["ANCHOR_SHEET_circumstantial_evidence.md"] + (["ANCHOR_SHEET_circumstantial_evidence.docx"] if any(f.endswith(".docx") for f in os.listdir(outc)) else [])), "sheet --topic writes that topic's sheet only")
mdc = open(os.path.join(outc, "ANCHOR_SHEET_circumstantial_evidence.md"), encoding="utf-8").read()
check("Sharad Birdhichand Sarda" in mdc and "Hanumant" in mdc and "Antulay" not in mdc and "Ramachandra" not in mdc, "the circumstantial sheet is about the two landmark cases and not the trial-delay ones")
check(all(SA.excerpt_text(e).replace("\n", " ") in mdc.replace("\n", " ") for a in (sarda, han) for e in a["excerpts"]) and sarda["link"] in mdc and han["link"] in mdc, "the sheet carries every excerpt word for word, with the court's links")
check("paragraphs 152 to 154 of the SCC report" in mdc and "paragraph 10 of the AIR report" in mdc and "How the words were checked" in mdc and "No word was ignored" in mdc, "the sheet shows each paragraph with its report and says what the check looked past")
check("is good law" not in mdc.lower() and "Until you confirm" in mdc and "panchsheel" in mdc, "the sheet never says a case is good law; it asks the reviewer to confirm the description")
outa = tempfile.mkdtemp()
check(SA.main(["sheet", "--out", outa]) == 0 and {"ANCHOR_SHEET_trial_delay.md", "ANCHOR_SHEET_circumstantial_evidence.md"} <= set(os.listdir(outa)), "sheet with no topic writes one sheet for each topic in the data")
check(SA.main(["sheet", "--out", tempfile.mkdtemp(), "--topic", "no_such_topic"]) == 1, "an unknown topic is refused")

print("\nALL PASSED" if not FAILURES else f"\n{len(FAILURES)} FAILED: {FAILURES}")
sys.exit(1 if FAILURES else 0)
