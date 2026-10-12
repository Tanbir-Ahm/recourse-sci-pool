"""Tests for the cards overlay (goodlaw/overlay.py) and its export in the site bundle. Run: python test_goodlaw_overlay.py

Gates: the wording never says a case 'is good law'; a warning or caution card is passed on with its quote; a quiet card says it is silence, not a finding; a case on neither list gets the fixed 'not checked by us'
sentence; a register case is not also given a card note; a bare name is ignored; the exported bundle works on its own."""
import json
import os
import re
import subprocess
import sys
import tempfile

from goodlaw import overlay as OV
from goodlaw import register as R

FAILURES = []
HERE = os.path.dirname(os.path.abspath(__file__))


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


cards_doc = json.load(open(os.path.join(HERE, "cards", "currency_cards.json"), encoding="utf-8"))
doc = OV.build_overlay(cards_doc, today="2026-10-12")
ov = OV.Overlay(doc)
reg = R.Register.load()
check(len(doc["entries"]) == 76 and doc["counts"] == {"quiet": 46, "not_checked": 28, "warning": 2}, f"one entry per card: 76 ({doc['counts']})")
check(doc["as_of"] == "2026-08-12" and doc["label"].endswith("not lawyer-validated"), "the overlay carries the date of the last judgment it read and the source label")

# wording: never a claim that a case is good law
claims = re.compile(r"\b(?:is|remains|are|stays)\s+(?:still\s+|currently\s+)?(?:good law|valid|binding|correct)\b", re.I)
allowed_negations = ("not a finding that it is still good law", "whether this decision is still good law")
bad = []
for e in doc["entries"]:
    t = e["note"]
    for ok in allowed_negations:
        t = t.replace(ok, "")
    if claims.search(t):
        bad.append(e["name"])
check(not bad, f"no note says a case is good law ({bad[:3]})")
check(all(e["kind"] != "quiet" or "not a finding" in e["note"] for e in doc["entries"]), "a quiet card says it is silence in what we hold, not a finding about the law")
check(all(e["kind"] != "not_checked" or e["note"] == OV.NOT_CHECKED for e in doc["entries"]), "an unchecked card carries the fixed 'not checked by us' sentence")
check(all(e.get("evidence", {}).get("quote") for e in doc["entries"] if e["kind"] == "warning"), "a warning card carries its verified quote")
check(all("evidence" not in e for e in doc["entries"] if e["kind"] in ("quiet", "not_checked")), "a quiet or unchecked card carries no evidence line")

# lookup
e = ov.lookup("Mohan Lal v State of Punjab", 2018, "(2018) 17 SCC 627")
check(e is not None and e["kind"] == "warning", "Mohan Lal (2018) is found by citation and is a warning")
check(ov.lookup("Mohan Lal v. State of Punjab", 2018) is not None, "found by both names and the year too")
check(ov.lookup("Mohan Lal v. State of Punjab", 2005) is None, "a wrong year is not matched by name")
check(ov.lookup("Mohan Lal") is None and ov.lookup("Ram Prasad v. State of Bihar", 2012, "(2012) 3 SCC 100") is None, "a bare name and an unknown case are not found")
check(ov.lookup(None, None, "(2014) 8 SCC 273") is not None, "Arnesh Kumar is found by citation alone")

# the audit of a finished answer
text = ("In Mohan Lal v. State of Punjab (2018) 17 SCC 627 the Court held that the informant cannot investigate. See also Siddharam Satlingappa Mhetre v. State of Maharashtra (2011) 1 SCC 694, "
        "and Arnesh Kumar v. State of Bihar (2014) 8 SCC 273 on arrest. The Court in Ram Prasad v. State of Bihar (2012) 3 SCC 100 differed. The Bhajan Lal case is also well known.")
r = OV.audit_answer(reg, ov, text)
check(len(r["register_notes"]) == 2 and any("Mohan Lal" in n for n in r["register_notes"]), "the two register cases get their register notes")
check(r["card_notes"] == [], "a register case is not given a second, card note")
check(r["not_checked"] == ["Ram Prasad v. State of Bihar"] and "Ram Prasad v. State of Bihar" in r["not_checked_sentence"], "a case on neither list is named in the fixed 'not checked' sentence")
check(any("Arnesh Kumar" in q["case"] for q in r["quiet"]) and "Arnesh" not in " ".join(r["not_checked"]), "a library case with a quiet card is neither noted nor called unchecked")
check("Bhajan" not in json.dumps(r["not_checked"]), "a bare name ('the Bhajan Lal case') is ignored")
card_only = "The Court in Siddharam Satlingappa Mhetre v. State of Maharashtra (2011) held that conditions are not allowed."
fake_reg = R.Register([], {})
r2 = OV.audit_answer(fake_reg, ov, card_only)
check(r2["register_notes"] == [] and len(r2["card_notes"]) == 1 and r2["card_notes"][0]["kind"] == "warning" and r2["not_checked"] == [], "with an empty register, Mhetre's warning card is used (one card note, not called unchecked)")
mhetre = ov.lookup("Siddharam Satlingappa Mhetre v. State of Maharashtra", 2011)
check(mhetre is not None and mhetre["kind"] in ("warning", "caution", "quiet"), f"Mhetre has a card ({mhetre and mhetre['kind']})")
r3 = OV.audit_answer(fake_reg, ov, "In Mohan Lal v. State of Punjab (2018) 17 SCC 627 the Court held X.")
check(len(r3["card_notes"]) == 1 and "appears to overrule" in r3["card_notes"][0]["note"] and r3["card_notes"][0]["evidence"]["quote"], "without the register the warning card is used, with its quote")
check(OV.audit_answer(None, None, "Ram Lal v. State of Delhi (2001) 1 SCC 1 held X.")["not_checked"] == ["Ram Lal v. State of Delhi"], "with no register and no overlay every named case is 'not checked'")
check(OV.audit_answer(reg, ov, "") == {**OV.audit_answer(reg, ov, ""), "not_checked": []} and OV.audit_answer(reg, ov, None)["not_checked_sentence"] is None, "an empty answer gives nothing and does not fail")

# the export works on its own
with tempfile.TemporaryDirectory() as d:
    out = os.path.join(d, "overruled_register")
    proc = subprocess.run([sys.executable, os.path.join(HERE, "sci_goodlaw.py"), "register-export-site", "--out", out], capture_output=True, text=True, cwd=HERE)
    check(proc.returncode == 0 and os.path.exists(os.path.join(out, "overlay_slim.json")) and os.path.exists(os.path.join(out, "overlay.py")), "the site export writes the overlay next to the register")
    code = ("import overruled_register as OR; reg=OR.load(); ov=OR.load_overlay();"
            "from overruled_register import overlay as OV;"
            "r=OV.audit_answer(reg, ov, 'Mohan Lal v. State of Punjab (2018) 17 SCC 627 held X. Ram Lal v. State of Delhi (2001) 1 SCC 1 held Y.');"
            "print(len(r['register_notes']), len(r['not_checked']), len(ov.entries))")
    p2 = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=d, env={**os.environ, "PYTHONPATH": d})
    check(p2.stdout.split() == ["1", "1", "76"], f"the bundle with its overlay works on its own ({p2.stdout.strip()} {p2.stderr.strip()[-150:]})")
    p3 = subprocess.run([sys.executable, os.path.join(HERE, "sci_goodlaw.py"), "register-export-site", "--out", os.path.join(d, "x"), "--no-overlay"], capture_output=True, text=True, cwd=HERE)
    check(p3.returncode == 0 and not os.path.exists(os.path.join(d, "x", "overlay.py")), "--no-overlay leaves the overlay out")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
