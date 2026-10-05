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
check(votes == {"scc:2010:11:441": 2}, "the compatible citation after the pair is voted for in each sentence it follows")
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

# party words and regexes
check(M.party_words("M/S. ABC TRADERS (DEAD) THROUGH LRS. & ORS.") == ["ABC", "TRADERS"], "party names lose prefixes, 'dead through LRs' and 'and others'")
check(M.party_words("STATE OF U.P. AND ANOTHER") == ["STATE", "OF", "U", "P"], "initials are kept as words")
check(M.Target("", "X", 2000).pair_regex() is None, "a target with no petitioner has no pair pattern")
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
}


def write_gz(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write(content)


base = tempfile.mkdtemp(prefix="mentions_test_")
write_gz(os.path.join(base, "crawl", "shards", "000000-000249.ok9.gap0.err0.jsonl.gz"), "".join(json.dumps({"id": i, "status": "ok", "text": t, "pages": 2}) + "\n" for i, t in DOCS.items()))
write_gz(os.path.join(base, "bucket", "shards", "after-0000.ok0.miss0.err0.jsonl.gz"), "")
buf = io.StringIO()
csv.DictWriter(buf, fieldnames=["decision_date", "title", "path", "tier", "citation", "case_id", "crawl_ids"]).writeheader()
write_gz(os.path.join(base, "registry.csv.gz"), buf.getvalue())
write_gz(os.path.join(base, "none.csv.gz"), "path,title,decision_date,key,status,best_crawl_id,shared_runs,frac,in_crawl\n")
out = os.path.join(base, "corpus.sqlite")
K.build(os.path.join(base, "crawl"), os.path.join(base, "bucket"), os.path.join(base, "registry.csv.gz"), os.path.join(base, "none.csv.gz"), out, workers=1, log=lambda *_: None)
K.index_cites(out, workers=1, chunk=4, log=lambda *_: None)
cp = K.Corpus(out)
check(cp.get("c8", False)["dup_of"] == "c3", "fixture: text 8 is a second copy of text 3")

tgt = M.Target.from_doc(cp.get("c1", False))
tgt.cites = ["air:1992:604"]       # known from the law report; the SCC citation has to be learned
res = M.find_mentions(cp, tgt)
docs = [m["doc_key"] for m in res["mentions"]]
check(res["learned_cites"] == ["scc:1992:s1:335"], "the SCC supplement citation is learned from the texts that give it after the parties' names")
check(sorted(set(docs)) == ["c2", "c3", "c4", "c5"], "citing texts are 2, 3, 4 and 5: not 1 (the target), 6 (earlier), 7 (a different case with the same names), 8 (second copy), 9 (no mention)")
by_doc = {d: [m for m in res["mentions"] if m["doc_key"] == d] for d in set(docs)}
check(any(m["tier"] == "cite" for m in by_doc["c2"]), "text 2 cites the AIR page of the target")
check(all(m["confidence"] == "high" for m in by_doc["c5"]) and by_doc["c5"][0]["tier"] == "cite", "text 5 cites only the learned SCC citation, without the names, and is found by it")
check(any(m["tier"] == "short" and m["confidence"] == "medium" for m in by_doc["c3"]), "a short-name mention in a text that also has a pair mention is medium confidence")
check(res["citing_docs"] == 4 and res["citing_docs_high"] == 4, "four distinct citing judgments, all with a high-confidence mention")
check([m["date"] for m in res["mentions"]] == sorted(m["date"] for m in res["mentions"]), "mentions come in date order")
check(any("stands overruled" in m["sentence"] for m in by_doc["c4"]) and by_doc["c4"][0]["speaker"] == "court", "text 4's sentence says the case stands overruled and the court is the speaker")

# a target with no known cites and a cite index still works from names alone
tgt2 = M.Target.from_doc(cp.get("c1", False))
res2 = M.find_mentions(cp, tgt2, learn=False)
check(sorted({m["doc_key"] for m in res2["mentions"]}) == ["c2", "c3", "c4"] and res2["learned_cites"] == [], "without learning, texts that give neither the parties nor a known citation (text 5) are not found")

cp.con.close()
shutil.rmtree(base, ignore_errors=True)
print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
