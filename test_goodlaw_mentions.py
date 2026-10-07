"""Tests for goodlaw/mentions.py: finding the later judgments that cite a target, with confidence tiers. Run: python test_goodlaw_mentions.py"""
import csv
import gzip
import io
import json
import os
import shutil
import tempfile

from goodlaw import corpus as K
from goodlaw import mentions as M

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


T = M.Target("RANGAPPA", "SRI MOHAN", 2010, [], date="2010-05-07", doc_key="c1")

# ---- one text
text = ("The question before us is old. Learned counsel for the appellant submitted that Rangappa v. Sri Mohan, (2010) 11 SCC 441 was wrongly decided. "
        "We do not agree. The decision in Rangappa v. Sri Mohan, (2010) 11 SCC 441 has not been overruled. "
        "In Rangappa v. Sri Mohan (2005) 3 SCC 100 a different matter was decided.")
found, votes = M.extract(text, T, [])
check(len(found) == 2 and all(m["tier"] == "pair" for m in found), "two pair mentions are found; the one followed by a different case's citation (2005) is dropped")
check(votes == {"scc:2010:11:441": 1}, "the compatible citation after the pair earns the text one vote")
check(found[0]["speaker"] == "counsel" and found[1]["speaker"] == "court", "counsel's sentence is told apart from the court's own")
check(found[1]["matched"].startswith("Rangappa v. Sri Mohan") and "has not been overruled" in found[1]["sentence"], "the mention carries its sentence")
i, j = found[1]["target_in_sentence"]
check(found[1]["sentence"][i:j].startswith("Rangappa v. Sri Mohan"), "target_in_sentence points at the mention inside the sentence")

T2 = M.Target("RANGAPPA", "SRI MOHAN", 2010, ["scc:2010:11:441"], date="2010-05-07", doc_key="c1")
found, _ = M.extract(text, T2, [])
check([m["tier"] for m in found] == ["cite", "cite"], "with the citation known, the two mentions are one each (cite and pair hits are merged) and are marked cite")
check(found[0]["detail"] == "scc:2010:11:441", "and say which citation matched")

found, _ = M.extract("As held in (2010) 11 SCC 441 the presumption is mandatory. See also 2010 (11) SCC 441.", T2, [])
check(len(found) == 2 and all(m["tier"] == "cite" for m in found), "a bare citation counts, whichever way it is written")

short_text = "In Bhajan Lal the Court laid down guidelines. Bhajan Lal's case has been followed. The weather was fine."
T3 = M.Target("STATE OF HARYANA", "BHAJAN LAL", 1990, [], date="1990-11-21", doc_key="c1")
found, _ = M.extract(short_text, T3, ["Bhajan"])
check(len(found) == 2 and all(m["tier"] == "short" and m["confidence"] == "low" for m in found), "a distinctive short name alone is a low-confidence mention when nothing stronger is in the text")
strong = short_text + " State of Haryana v. Bhajan Lal (1992) Supp (1) SCC 335 is the leading case."
found, _ = M.extract(strong, T3, ["Bhajan"])
check(found[0]["tier"] == "short" and found[-1]["tier"] == "pair", "a pair mention in the same text is found alongside the short ones")

# parallel citations name the same case whatever the text calls it
T5 = M.Target("ADDITIONAL DISTRICT MAGISTRATE, JABALPUR", "S. S. SHUKLA", 1976, ["air:1976:1207", "scr:1976::172"], date="1976-04-28", doc_key="c1")
found, votes = M.extract("ADM Jabalpur v. Shivakant Shukla (1976) 2 SCC 521 : AIR 1976 SC 1207 was overruled.", T5, [])
check(votes == {"scc:1976:2:521": 1} and found and found[0]["tier"] == "cite", "a citation printed right beside a known one is learned as the same case, even when the case is named differently")
found, votes = M.extract("The Court held in (2001) 4 SCC 99 : AIR 1976 SC 1207 and in (1999) 5 SCC 5.", T5, [])
check(set(votes) == set(), "a citation of a clearly different year beside it is not learned")

# headnote
head = "HELD: Rangappa v. Sri Mohan, (2010) 11 SCC 441 followed. The Judgment of the Court was delivered by Rangappa v. Sri Mohan, (2010) 11 SCC 441 is binding."
bs = head.index("The Judgment")
found, _ = M.extract(head, T2, [], body_start=bs)
check([m["in_headnote"] for m in found] == [True, False] and found[0]["speaker"] == "headnote", "a mention before the court's own judgment begins is marked as headnote")

# lower court
found, _ = M.extract("The High Court held that Rangappa v. Sri Mohan, (2010) 11 SCC 441 does not apply.", T2, [])
check(found[0]["speaker"] == "lower_court", "a mention the High Court is said to have made is marked lower_court")
found, _ = M.extract("It was urged by the respondents. Reliance was placed on Rangappa v. Sri Mohan, (2010) 11 SCC 441.", T2, [])
check(found[0]["speaker"] == "counsel", "counsel's argument carried over from the previous sentence is recognised")

# a party's name with 'case' after it
T4 = M.Target("UNIVERSITY OF DELHI", "RAM NATH", 1963, [], date="1963-01-01", doc_key="c1")
pcs = T4.party_case_patterns()
found, _ = M.extract("Our conclusion is that the University of Delhi case was wrongly decided. The Delhi University's decision was different.", T4, [], party_cases=pcs)
check(len(found) == 1 and found[0]["tier"] == "short" and found[0]["matched"].lower().startswith("university of delhi case"), "a party's name followed by 'case' is found as a short mention")
check(M.Target("STATE OF PUNJAB", "X", 1990).party_case_patterns() != [] and M.Target("STATE", "X", 1990).party_case_patterns() == [], "a one-word stock party name never makes a party-case pattern")

# party words and regexes
check(M.party_words("M/S. ABC TRADERS (DEAD) THROUGH LRS. & ORS.") == ["ABC", "TRADERS"], "party names lose prefixes, 'dead through LRs' and 'and others'")
check(M.party_words("STATE OF U.P. AND ANOTHER") == ["STATE", "OF", "U", "P"], "initials are kept as words")
check(M.Target("", "X", 2000).pair_regex() is None, "a target with no petitioner has no pair pattern")
rx = M.Target("JUGRAJ SINGH AND ANR.", "LABH SINGH AND ORS.", 1994).pair_regex()
check(all(rx.search(t) for t in ["Jugraj Singh & Anr vs. Labh Singh & ors,. [(1995) 2 SCC 31]", "Jugraj Singh and Another v. Labh Singh and Others", "Jugraj Singh v. Labh Singh", "Jugraj Singh vs. Labh Singh etc."]),
      "the pair is found whether a later judgment prints 'and Another', '& Anr.' or nothing after the first name")
check(not rx.search("Jugraj Singh and Labh Singh") and not rx.search("Jugraj Singh v. Another Singh"), "but two names joined by 'and', or a different respondent, are not the pair")
rx = M.Target("RAJINDER KAUR", "PUNJAB STATE & ANR", 1986).pair_regex()
check(rx.search("Smt. Rajinder Kaur vs. State of Punjab is hereby over-ruled") and rx.search("Rajinder Kaur v. Punjab State") and not rx.search("Rajinder Kaur v. State of Haryana"),
      "'Punjab State' and 'State of Punjab' are the same party, and another State is not")
rx = M.Target("STATE OF HARYANA", "BHAJAN LAL", 1990).pair_regex()
check(rx.search("Haryana State v. Bhajan Lal") and rx.search("State of Haryana v. Bhajan Lal") and not rx.search("State of Punjab v. Bhajan Lal"), "and the same when the State is the petitioner")
check(M.Target("STATE OF PUNJAB", "BALDEV SINGH", 1999).short_names() == ["BALDEV"], "stock names (State, Punjab, Singh) are never used alone")

# ---- across a small corpus
def caption(pet, resp, body, tail):
    return f"IN THE SUPREME COURT OF INDIA\nCIVIL APPELLATE JURISDICTION\nCIVIL APPEAL NO. 5 OF 2009\n{pet}\n … Appellant\nVersus\n{resp}\n … Respondent\nJ U D G M E N T\n{body}\n{tail}"


PAD = " ".join(f"fill{i}" for i in range(200))
DOCS = {
    1: caption("STATE OF HARYANA", "BHAJAN LAL", "The FIR can be quashed in the cases set out. " + PAD, "New Delhi;\nNovember 21, 1990."),
    2: caption("RAM", "SHYAM", "Reference is made to State of Haryana v. Bhajan Lal, AIR 1992 SC 604 and Bhajan Lal (1992) Supp (1) SCC 335. That decision has been followed. " + PAD, "New Delhi;\nMarch 11, 1995."),
    3: caption("GOPAL", "HARI", "State of Haryana v. Bhajan Lal (1992) Supp (1) SCC 335 is the leading case. In Bhajan Lal's case guidelines were laid down. " + PAD, "New Delhi;\nApril 04, 2000."),
    4: caption("MOHAN", "SOHAN", "State of Haryana v. Bhajan Lal (1992) Supp (1) SCC 335 is not good law on this point and stands overruled. " + PAD, "New Delhi;\nJune 05, 2005."),
    5: caption("KAMAL", "VIMAL", "The ratio of (1992) Supp (1) SCC 335 was applied. " + PAD, "New Delhi;\nJuly 06, 2010."),
    6: caption("OLD", "CASE", "An earlier judgment mentioning State of Haryana v. Bhajan Lal (1992) Supp (1) SCC 335 cannot exist but the date is before. " + PAD, "New Delhi;\nJanuary 02, 1985."),
    7: caption("PQR", "STU", "State of Haryana v. Bhajan Lal (2001) 4 SCC 99 is a different matter entirely. " + PAD, "New Delhi;\nAugust 08, 2012."),
    8: caption("GOPAL", "HARI", "State of Haryana v. Bhajan Lal (1992) Supp (1) SCC 335 is the leading case. In Bhajan Lal's case guidelines were laid down. " + PAD, "New Delhi;\nApril 04, 2000."),
    9: caption("NO", "MENTION", "Nothing relevant here. " + PAD, "New Delhi;\nApril 09, 2013."),
    10: caption("DEEP", "VEER", "Bhajan Lal's case was relied on, and the later decision is reported at (1992) Supp (1) SCC 335. " + PAD, "New Delhi;\nMay 10, 2014."),
}


def write_gz(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write(content)


base = tempfile.mkdtemp(prefix="mentions_test_")
write_gz(os.path.join(base, "crawl", "shards", "000000-000249.ok9.gap0.err0.jsonl.gz"), "".join(json.dumps({"id": i, "status": "ok", "text": t, "pages": 2}) + "\n" for i, t in DOCS.items()))
dupe_text = DOCS[3]
write_gz(os.path.join(base, "bucket", "shards", "none-0000.ok1.miss0.err0.jsonl.gz"), json.dumps(
    {"status": "ok", "path": "2000_1_1_9", "title": "GOPAL versus HARI", "petitioner": "GOPAL", "respondent": "HARI", "decision_date": "04-04-2000", "citation": "[2000] 1 S.C.R. 1",
     "case_id": "", "text": dupe_text, "key": "k", "bytes": 1, "sha256": "x", "pages": 2, "scan_pages": 0}) + "\n")
buf = io.StringIO()
csv.DictWriter(buf, fieldnames=["decision_date", "title", "path", "tier", "citation", "case_id", "crawl_ids"]).writeheader()
write_gz(os.path.join(base, "registry.csv.gz"), buf.getvalue())
write_gz(os.path.join(base, "none.csv.gz"), "path,title,decision_date,key,status,best_crawl_id,shared_runs,frac,in_crawl\n2000_1_1_9,GOPAL versus HARI,04-04-2000,k,ok,3,60,0.25,uncertain\n")
out = os.path.join(base, "corpus.sqlite")
K.build(os.path.join(base, "crawl"), os.path.join(base, "bucket"), os.path.join(base, "registry.csv.gz"), os.path.join(base, "none.csv.gz"), out, workers=1, log=lambda *_: None)
K.index_cites(out, workers=1, chunk=4, log=lambda *_: None)
cp = K.Corpus(out)
check(cp.get("c8", False)["dup_of"] == "c3", "fixture: text 8 is a second copy of text 3")
check(cp.get("b2000_1_1_9", False)["maybe_dup_of"] == "c3", "fixture: the bucket text marked 'uncertain' points at crawl text 3")

tgt = M.Target.from_doc(cp.get("c1", False))
tgt.cites = ["air:1992:604"]       # known from the law report; the SCC citation has to be learned
res = M.find_mentions(cp, tgt)
docs = [m["doc_key"] for m in res["mentions"]]
check(res["learned_cites"] == ["scc:1992:s1:335"], "the SCC supplement citation is learned from the texts that give it after the parties' names")
check("b2000_1_1_9" not in docs, "a bucket text that may be a second copy of a candidate crawl text is not counted twice")
check(sorted(set(docs)) == ["c10", "c2", "c3", "c4", "c5"], "citing texts are 2, 3, 4, 5 and 10: not 1 (the target), 6 (earlier), 7 (a different case with the same names), 8 (second copy), 9 (no mention)")
by_doc = {d: [m for m in res["mentions"] if m["doc_key"] == d] for d in set(docs)}
check(any(m["tier"] == "cite" for m in by_doc["c2"]), "text 2 cites the AIR page of the target")
check(all(m["confidence"] == "high" for m in by_doc["c5"]) and by_doc["c5"][0]["tier"] == "cite", "text 5 cites only the learned SCC citation, without the names, and is found by it")
check(any(m["tier"] == "short" and m["confidence"] == "medium" for m in by_doc["c3"]), "a short-name mention in a text that also has a pair mention is medium confidence")
check(res["citing_docs"] == 5 and res["citing_docs_high"] == 5, "five distinct citing judgments, all with a high-confidence mention")
check(any(m["tier"] == "cite" for m in by_doc["c10"]) and all(m["confidence"] in ("high", "medium") for m in by_doc["c10"]),
      "text 10 names the case only as 'Bhajan Lal's case' but prints the citation learned from the others: it is read again after the learning, so its mention is no longer low confidence")
check([m["date"] for m in res["mentions"]] == sorted(m["date"] for m in res["mentions"]), "mentions come in date order")
check(any("stands overruled" in m["sentence"] for m in by_doc["c4"]) and by_doc["c4"][0]["speaker"] == "court", "text 4's sentence says the case stands overruled and the court is the speaker")

# a target with no known cites and a cite index still works from names alone
tgt2 = M.Target.from_doc(cp.get("c1", False))
res2 = M.find_mentions(cp, tgt2, learn=False)
check(sorted({m["doc_key"] for m in res2["mentions"]}) == ["c10", "c2", "c3", "c4"] and res2["learned_cites"] == [], "without learning, texts that give neither the parties nor a known citation (text 5) are not found")
check(all(m["confidence"] == "low" for m in res2["mentions"] if m["doc_key"] == "c10"), "and without learning, text 10's short-name mention stays low confidence")

cp.con.close()
shutil.rmtree(base, ignore_errors=True)
# step 2: the citation's mention takes in the case name before it
T2 = M.Target("TOWN MUNICIPAL COUNCIL, ATHANI", "PRESIDING OFFICER, LABOUR COURT", 1970, ["scr:1970:1:51"], date="1970-01-01", doc_key="c1")
txt = "It was so held following the decision in Kerala State Electricity Board v. Amsom, [1977] 1 S.C.R. 996 which overruled the earlier decision of this court in Town Municipal Council, Athani v. Presiding Officer, Labour Court, [1970] 1 S.C.R. 51."
fnd, _ = M.extract(txt, T2, [])
check(fnd and fnd[0]["matched"].startswith("Town Municipal Council, Athani v. Presiding Officer") and fnd[0]["matched"].endswith("51"), f"a citation mention begins at the case name before it (got {fnd[0]['matched'] if fnd else None!r})")
check(M.clean_party("No. 6290/2007) American Hotel & Lodging Association Educational Institute") == "American Hotel & Lodging Association Educational Institute", "a case number left on the front of a title is dropped")
check(M.clean_party("Mohan Lal") == "Mohan Lal" and M.clean_party("M/s. No. 1 Traders") != "", "ordinary names are untouched")

# the page header of a later judgment with the same parties is not a mention
T3 = M.Target("KARNAIL SINGH", "STATE OF HARYANA", 2009, [], date="2009-09-10", doc_key="c35186")
hdr = "[2024] 6 S.C.R. 907 Karnail Singh v. State of Haryana & Ors. (v) A review is by no means an appeal in disguise whereby an erroneous decision is reheard and corrected."
fnd, _ = M.extract(hdr, T3, [])
check(fnd == [], "a citation of another year just before the names marks a later judgment's page header, not a mention of the case")
fnd, _ = M.extract("In Karnail Singh v. State of Haryana the Court held that compliance with the procedure is mandatory in every case where a search is made without a gazetted officer being present. [2024] 6 S.C.R. 907", T3, [])
check(len(fnd) == 1, "a genuine mention before a page number is kept")
fnd, _ = M.extract("The law was laid down in Karnail Singh v. State of Haryana, (2009) 8 SCC 539.", M.Target("KARNAIL SINGH", "STATE OF HARYANA", 2009, ["scc:2009:8:539"], doc_key="c35186"), [])
check(len(fnd) >= 1, "and a mention with the case's own citation is kept")
check(M.speaker("Later judgments such as Noor Aga (supra) ought to be overruled by us.", "According to him, the reference order was flawed.", False)[0] == "counsel", "a sentence after 'According to him ...' is counsel's")
check(M.speaker("He further argued that the judgment does not need reconsideration.", "", False)[0] == "counsel", "'He further argued' is counsel's")
check(M.speaker("According to Mr. Venugopal, the decision in Kannadasan's case must be held to be wrongly decided.", "", False)[0] == "counsel" and M.speaker("ACCORDING TO MR. VENUGOPAL, THE JUDGMENT WAS WRONG.", "", False)[0] == "counsel", "'According to Mr. X' is counsel's, in capitals too")
check(M.speaker("We hold that the judgment was wrong.", "According to him, it was right.", False)[0] == "court", "but a sentence in the court's own voice stays the court's")

hdr2 = "[2024] 6 S.C.R. \x08 907 Karnail Singh v. State of Haryana & Ors. (v) A review is by no means an appeal in disguise whereby an erroneous decision is reheard."
fnd, _ = M.extract(hdr2, T3, [])
check(fnd == [], "a page header whose citation has a stray control character in it is still recognised as a later judgment's header")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
