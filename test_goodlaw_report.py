"""Tests for goodlaw/report.py and sci_goodlaw.py: triage labels, evidence, citator, statute flag, coverage. Run: python test_goodlaw_report.py"""
import csv
import gzip
import io
import json
import os
import shutil
import tempfile

from goodlaw import corpus as K
from goodlaw import mentions as M
from goodlaw import report as R
import sci_goodlaw

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def judis(pet, resp, date, bench, air, body, citator=""):
    b = "\n".join(bench)
    return (f"http://JUDIS.NIC.IN\nSUPREME COURT OF INDIA\nPage 1 of 4\nPETITIONER:\n{pet}\n        Vs.\nRESPONDENT:\n{resp}\nDATE OF JUDGMENT:\n{date}\nBENCH:\n{bench[0]}\nBENCH:\n{b}\n"
            f"CITATION:\n {air}\n{citator}ACT:\nSome Act.\nHEADNOTE:\nHeadnote words.\nJUDGMENT:\n{body}\n")


LATER_N = [0]


def later(pet, body, date_ddmmyyyy, judges):
    """A later judgment in the JUDIS layout, so its bench is read completely from the header."""
    LATER_N[0] += 1
    names = ["SARKAR, A.K.", "SHAH, J.C.", "RAY, A.N.", "KHANNA, H.R.", "MATHEW, K.K.", "BEG, M.H.", "CHANDRACHUD, Y.V."][:judges]
    return judis(pet, "SOME RESPONDENT", date_ddmmyyyy, names, f"{2000 + LATER_N[0]} AIR {900 + LATER_N[0]}", body)


PAD = " ".join(f"fill{i}" for i in range(150))
DOCS = {
    # targets (JUDIS layout, 1990, with their own AIR citations)
    1: judis("ALPHA", "BETA", "05/05/1990", ["SARKAR, A.K.", "SHAH, J.C.", "RAY, A.N."], "1991 AIR 11", "Alpha holds. " + PAD),
    2: judis("GAMMA", "DELTA", "05/05/1990", ["SARKAR, A.K.", "SHAH, J.C.", "RAY, A.N.", "KHANNA, H.R.", "MATHEW, K.K."], "1991 AIR 22", "Gamma holds. " + PAD),
    3: judis("EPSILON", "ZETA", "05/05/1990", ["SARKAR, A.K.", "SHAH, J.C."], "1991 AIR 33", "Epsilon holds. Section 302 IPC and Section 482 Cr.P.C. were applied. " + PAD),
    4: judis("ETA", "THETA", "05/05/1990", ["SARKAR, A.K.", "SHAH, J.C."], "1991 AIR 44", "Eta holds. " + PAD),
    5: judis("IOTA", "KAPPA", "05/05/1990", ["SARKAR, A.K.", "SHAH, J.C."], "1991 AIR 55", "Iota holds. " + PAD),
    6: judis("LAMBDA", "MU", "05/05/1960", ["SARKAR, A.K.", "SHAH, J.C."], "1961 AIR 66", "Lambda holds. " + PAD, citator=" CITATOR INFO :\n F          1995 SC 700  (3)\n O          1996 SC 200  (5)\n"),
    # citing judgments
    10: later("P10", "Alpha v. Beta, AIR 1991 SC 11 stands overruled. " + PAD, "03/03/2000", 5),
    11: later("P11", "Gamma v. Delta, AIR 1991 SC 22 stands overruled. " + PAD, "04/03/2000", 2),
    12: later("P12", "Epsilon v. Zeta, AIR 1991 SC 33 was followed. " + PAD, "05/03/2000", 3),
    13: later("P13", "The law laid down in Epsilon v. Zeta, AIR 1991 SC 33 is reiterated. " + PAD, "06/03/2001", 3),
    14: later("P14", "We respectfully agree with Epsilon v. Zeta, AIR 1991 SC 33. " + PAD, "07/03/2005", 3),
    15: later("P15", "Reference is made to Eta v. Theta, AIR 1991 SC 44. " + PAD, "08/03/2000", 2),
    16: later("P16", "Learned counsel for the appellant submitted that Iota v. Kappa, AIR 1991 SC 55 stands overruled. We do not agree. " + PAD, "09/03/2000", 2),
    17: later("P17", "Iota v. Kappa, AIR 1991 SC 55 was followed. " + PAD, "10/03/2001", 2),
    18: later("P18", "Iota v. Kappa, AIR 1991 SC 55 was approved. " + PAD, "11/03/2002", 2),
    19: later("P19", "Iota v. Kappa, AIR 1991 SC 55 was reiterated. " + PAD, "12/03/2003", 2),
    7: judis("NU", "XI", "05/05/1990", ["SARKAR, A.K.", "SHAH, J.C."], "1991 AIR 77", "Nu holds. " + PAD),
    21: judis("RHO", "SIGMA", "06/06/1995", ["SARKAR, A.K.", "SHAH, J.C.", "RAY, A.N."], "1996 AIR 211", "Something else entirely. " + PAD).replace("HEADNOTE:\nHeadnote words.", "HEADNOTE:\nNu v. Xi, AIR 1991 SC 77, over-ruled."),
    # a judgment that the reporter's citator for target 6 names (its own AIR cite is 1996 AIR 200)
    20: judis("OVERRULER", "STATE", "06/06/1996", ["SARKAR, A.K.", "SHAH, J.C.", "RAY, A.N."], "1996 AIR 200", "Something else entirely. " + PAD),
}


DOCS[8] = judis("TAU", "UPSILON", "05/05/1990", ["SARKAR, A.K.", "SHAH, J.C."], "1991 AIR 88", "Tau holds. " + PAD)
for n in range(12):
    body = "Tau v. Upsilon, AIR 1991 SC 88 was followed. " + PAD
    if n == 0:
        body = "If Tau v. Upsilon, AIR 1991 SC 88 were overruled, the result would differ. " + PAD
    DOCS[30 + n] = later(f"PT{n}", body, f"{10 + n:02d}/06/2001", 2)
DOCS[70] = judis("OMICRON", "PI", "05/05/1990", ["SARKAR, A.K.", "SHAH, J.C.", "RAY, A.N.", "KHANNA, H.R.", "MATHEW, K.K."], "1991 AIR 140", "Omicron holds. " + PAD)
DOCS[71] = later("PQ1", "We are unable to agree with the view taken in Omicron v. Pi, AIR 1991 SC 140. " + PAD, "10/06/2001", 2)
DOCS[72] = later("PQ2", "Reference is made to Omicron v. Pi, AIR 1991 SC 140. " + PAD, "11/06/2001", 2)
DOCS[73] = later("PQ3", "Reference is made to Omicron v. Pi, AIR 1991 SC 140. " + PAD, "12/06/2001", 2)
DOCS[9] = judis("PHI", "CHI", "05/05/1990", ["SARKAR, A.K.", "SHAH, J.C."], "1991 AIR 99", "Phi holds. " + PAD)
DOCS[60] = later("PP0", "If Phi v. Chi, AIR 1991 SC 99 were overruled, the result would differ. " + PAD, "10/06/2001", 2)
DOCS[61] = later("PP1", "Reference is made to Phi v. Chi, AIR 1991 SC 99. " + PAD, "11/06/2001", 2)


def write_gz(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write(content)


base = tempfile.mkdtemp(prefix="report_test_")
write_gz(os.path.join(base, "crawl", "shards", "000000-000249.ok.gap0.err0.jsonl.gz"), "".join(json.dumps({"id": i, "status": "ok", "text": t, "pages": 2}) + "\n" for i, t in DOCS.items()))
write_gz(os.path.join(base, "bucket", "shards", "after-0000.ok0.miss0.err0.jsonl.gz"), "")
buf = io.StringIO()
csv.DictWriter(buf, fieldnames=["decision_date", "title", "path", "tier", "citation", "case_id", "crawl_ids"]).writeheader()
write_gz(os.path.join(base, "registry.csv.gz"), buf.getvalue())
write_gz(os.path.join(base, "none.csv.gz"), "path,title,decision_date,key,status,best_crawl_id,shared_runs,frac,in_crawl\n")
out = os.path.join(base, "corpus.sqlite")
K.build(os.path.join(base, "crawl"), os.path.join(base, "bucket"), os.path.join(base, "registry.csv.gz"), os.path.join(base, "none.csv.gz"), out, workers=1, log=lambda *_: None)
K.index_cites(out, workers=1, chunk=5, log=lambda *_: None)
cp = K.Corpus(out)


def bundle_for(key):
    doc = cp.get(key, with_text=False)
    return R.build_bundle(cp, M.Target.from_doc(doc), doc, today="2026-10-05")


check(cp.get("c1", False)["bench_size"] == 3 and cp.get("c10", False)["bench_size"] == 5 and cp.get("c11", False)["bench_size"] == 2, "fixture: benches are read (3, 5 and 2)")

a = bundle_for("c1")
check(a["triage"] == "ADVERSE_SIGNAL" and len(a["summary"]["adverse_strong"]) == 1, "a five-judge bench saying 'stands overruled' of a three-judge case gives ADVERSE_SIGNAL")
e = a["summary"]["adverse_strong"][0]
check(R.bench_relation(5, 3, "report_line", "header_full") == "larger" and R.bench_relation(3, 3, "report_line", "report_line") == "equal" and R.bench_relation(2, 3, "report_line", "report_line") == "smaller", "bench relation: complete benches are compared")
check(R.bench_relation(2, 3, "report_line", "signatures") == "smaller", "bench relation: a lower bound that already exceeds the citing bench makes the citing bench smaller")
check(R.bench_relation(3, 2, "report_line", "signatures") == "unknown" and R.bench_relation(3, 3, "report_line", "header") == "unknown", "bench relation: a lower bound the citing bench exceeds or matches proves nothing, a judge may be missing from it")
check(R.bench_relation(3, 2, "signatures", "header_full") == "larger" and R.bench_relation(2, 2, "signatures", "header_full") == "unknown", "bench relation: a citing lower bound that exceeds the complete target bench makes it larger")
check(R.bench_relation(5, 2, "header", "signatures") == "unknown" and R.bench_relation(None, 2, "report_line", "report_line") == "unknown", "bench relation: two lower bounds, or a missing size, give unknown")
check(e["bench_relation"] == "larger" and e["quote_verified"] and "stands overruled" in e["sentence"] and e["cue"] and e["speaker"] == "court", "the evidence carries bench relation, a verified quote, the cue and the speaker")

g = bundle_for("c2")
check(g["triage"] == "QUESTIONED" and not g["summary"]["adverse_strong"] and len(g["summary"]["adverse_possible"]) == 1, "a two-judge bench 'overruling' a five-judge case is only QUESTIONED")
check("smaller bench" in " ".join(g["summary"]["adverse_possible"][0]["why_not_a_clean_overruling"]), "and says why it is not a clean overruling")

c = bundle_for("c3")
check(c["triage"] == "NO_ADVERSE_FOUND" and c["summary"]["citing_judgments"] == 3 and c["summary"]["latest_citing_year"] == 2005, "three approving judgments and nothing adverse give NO_ADVERSE_FOUND")
check(c["summary"]["by_treatment"].get("FOLLOWS") == 3 and len(c["recent_approving"]) == 3 and c["recent_approving"][0]["year"] == 2005, "approvals are counted and the most recent comes first")
check(c["statute_flag"] == "STATUTE_CHANGED" and {r["section"] for r in c["statute_dimension"]} >= {"302", "482"}, "sections 302 IPC and 482 CrPC raise the STATUTE_CHANGED flag")
check("NO_ADVERSE_FOUND" in R.PLAIN and "silence in what we hold" in c["plain"], "the plain-language line says this is silence, not a finding of good law")

d = bundle_for("c4")
check(d["triage"] == "INSUFFICIENT" and d["summary"]["citing_judgments"] == 1, "one citing judgment is INSUFFICIENT")

i = bundle_for("c5")
check(i["triage"] == "NO_ADVERSE_FOUND" and len(i["summary"]["argued_or_lower_court"]) == 1 and not i["summary"]["adverse_possible"], "an overruling that only counsel argues is listed but does not change the triage")
check(i["summary"]["argued_or_lower_court"][0]["speaker"] == "counsel", "and is marked as counsel's")

l = bundle_for("c6")
check(l["triage"] == "ADVERSE_SIGNAL" and l["summary"]["citator_adverse_overruled"] and l["summary"]["citator_adverse_overruled"][0]["cite"] == "1996 SC 200", "the reporter's citator marking it overruled gives ADVERSE_SIGNAL even with no text mention")
cit = {r["code"]: r for r in l["reporter_citator"]}
check(cit["O"]["citing_case"] and cit["O"]["citing_case"]["doc_key"] == "c20" and cit["F"]["citing_case"] is None, "the citator's citing case is found in the collection when we hold it")

h = bundle_for("c7")
check(h["triage"] == "ADVERSE_SIGNAL" and h["summary"]["adverse_strong"] and h["summary"]["adverse_strong"][0]["in_headnote"] and "headnote" in h["summary"]["adverse_strong"][0]["kind"],
      "a law report's headnote saying 'over-ruled' of the case is ADVERSE_SIGNAL, marked as the headnote's word")

t8 = bundle_for("c8")
check(t8["triage"] == "NO_ADVERSE_FOUND" and t8["summary"]["weak_signals_set_aside"] == 1 and "weak or ambiguous" in t8["plain"], "in a heavily cited case a lone hedged 'overruled' is set aside, counted and disclosed, and does not change the triage")
t9 = bundle_for("c9")
check(t9["triage"] == "QUESTIONED", "in a case cited only twice the same hedged reading is enough for QUESTIONED")

o = bundle_for("c70")
check(o["summary"]["adverse_possible"] and o["summary"]["adverse_possible"][0]["label"] == "DISAGREES" and o["summary"]["adverse_possible"][0]["weak"] and "smaller bench" in " ".join(o["summary"]["adverse_possible"][0]["why_not_a_clean_overruling"]),
      "a two-judge bench's disagreement with a five-judge case is kept as evidence but marked weak, with the reason")

cv = a["coverage"]
check(cv["collection_runs_to"] and isinstance(cv["later_years"], list) and "note" in cv, "the coverage block says where the collection ends and how much of the later years it holds")
check(all(x for x in a["limits"]) and a["generated"] == "2026-10-05", "limits are stated and the date is recorded")

# where the collection ends counts the court's newer archive too (its rows are dated from the archive, date_source 'court')
import sqlite3
mem = sqlite3.connect(":memory:")
mem.execute("CREATE TABLE docs (year INTEGER, dup_of TEXT, date TEXT, date_source TEXT)")
mem.executemany("INSERT INTO docs VALUES (?,?,?,?)", [(2025, None, "2025-12-01", "bucket"), (2026, None, "2026-10-16", "court"), (2027, None, "2027-01-01", "neighbours"), (2020, "x", "2020-01-01", "court")])
cv2 = R.coverage(type("C", (), {"con": mem})(), 2010, year_counts_path="/no/such/file.csv")
check(cv2["collection_runs_to"] == "2026-10-16" and "newer archive" in cv2["note"], "the collection's end date counts the court's newer archive and the note names it (an estimated date does not count)")

rows = [{"doc_key": "b1", "label": "DISAGREES", "cue": "not been followed"} for _ in range(4)] + [{"doc_key": "b2", "label": "DISAGREES", "cue": "not been followed"}, {"doc_key": "b1", "label": "OVERRULES", "cue": "overruled"}]
col = R._collapse(rows)
check(len(col) == 3 and col[0].get("repeats") == 3 and "repeats" not in col[1], "the same wording repeated in one judgment is shown once with a count of the repeats; other judgments and other cues are kept")

rows = [{"doc_key": "b1", "label": "OVERRULES", "cue": "overruled", "weak": True}, {"doc_key": "b1", "label": "OVERRULES", "cue": "overruled", "weak": False},
        {"doc_key": "b1", "label": "OVERRULES", "cue": "overruled", "weak": True}]
col = R._collapse(rows)
check(len(col) == 2 and col[0].get("repeats") == 1 and col[1]["weak"] is False, "a firm reading is not hidden behind a weak one with the same wording in the same judgment; the two weak ones still merge")

md = R.render_markdown(a)
check("Triage: ADVERSE_SIGNAL" in md and "stands overruled" in md and "What this collection can and cannot see" in md and "## Limits" in md, "the Markdown report shows the triage, the quote, the coverage and the limits")
check("not lawyer-validated" in md, "the Markdown report carries the source label")

# the command line
doc = sci_goodlaw.resolve(cp, "gamma delta")
check(doc["doc_key"] == "c2", "resolve finds a case by words of its title")
try:
    sci_goodlaw.resolve(cp, "holds")
    amb = False
except ValueError:
    amb = True
check(amb, "resolve refuses an unknown name")
bundle, mdtext = sci_goodlaw.check_one(cp, doc, out_dir=os.path.join(base, "reports"), log=lambda *_: None)
check(os.path.exists(os.path.join(base, "reports", "c2.json")) and os.path.exists(os.path.join(base, "reports", "c2.md")), "check_one writes the JSON bundle and the Markdown report")
check(json.load(open(os.path.join(base, "reports", "c2.json")))["triage"] == "QUESTIONED", "the written bundle is valid JSON with the triage")

cp.con.close()
shutil.rmtree(base, ignore_errors=True)
print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
