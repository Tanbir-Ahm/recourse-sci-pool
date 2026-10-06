"""Tests for goodlaw/reader.py: the passages a model reads, and the checking of what it says. Run: python test_goodlaw_reader.py"""
import sys
from goodlaw import reader as R

FAILED = []


def check(ok, msg):
    print(("[PASS] " if ok else "[FAIL] ") + msg)
    if not ok:
        FAILED.append(msg)


def mention(sentence, name, prev="", nxt="", confidence="high", head=False):
    i = sentence.index(name)
    return {"sentence": sentence, "target_in_sentence": (i, i + len(name)), "prev": prev, "next": nxt, "confidence": confidence, "in_headnote": head}


m1 = mention("This view in Sibbia v. State is no longer good law.", "Sibbia v. State", prev="The question arises.", nxt="We say so with respect.")
p = R.passage(m1)
check("«Sibbia v. State»" in p and p.startswith("The question arises.") and p.endswith("with respect."), "the passage is the sentence before, the sentence with the case marked, the sentence after")

long = "x" * 900 + " Sibbia v. State " + "y" * 900
pl = R.passage(mention(long, "Sibbia v. State"))
check(len(pl) < 900 and "«Sibbia v. State»" in pl and pl.startswith("…"), "a very long sentence is clipped around the mention")

plain = mention("The appellant cited Sibbia v. State for bail.", "Sibbia v. State")
cue = mention("In Sibbia v. State the Court was wrong and the decision is overruled.", "Sibbia v. State", confidence="medium")
low = mention("Sibbia is mentioned.", "Sibbia", confidence="low")
ps = R.candidate_passages([plain, low, cue])
check(len(ps) == 2 and "overruled" in ps[0]["text"], "a passage with treatment vocabulary comes first and a low-confidence mention is not offered")
check(len(R.candidate_passages([plain] * 5)) == 1, "the same sentence is not offered twice")
check(len(R.candidate_passages([mention(f"Sibbia v. State is cited in point {i}.", "Sibbia v. State") for i in range(9)])) == R.MAX_PASSAGES, "at most MAX_PASSAGES passages")
check(R.candidate_passages([mention("Sibbia v. State here.", "Sibbia v. State", head=True)])[0]["where"] == "headnote", "a headnote passage is labelled as such")
check(R.make_item("r1", "Sibbia (1980)", "Later v State", "2020-01-01", [low]) is None, "no confident mention, no item")

item = R.make_item("r1", "Sibbia (1980)", "Later v State", "2020-01-01", [cue])
good = R.check_verdict(item, {"id": "r1", "treatment": "overrules", "quote": "the decision  is\noverruled."})
check(good["valid"] and good["quote_verified"] and R.is_adverse(good) and good["treatment"] == "OVERRULES", "a verdict with a quote found in the passages (whitespace aside) is verified and adverse")
fake = R.check_verdict(item, {"id": "r1", "treatment": "OVERRULES", "quote": "the Court overruled it in plain words"})
check(fake["valid"] and not fake["quote_verified"] and fake["quote"] == "" and not R.is_adverse(fake), "a quote not in the passages makes the verdict unverified, blanks the quote and is not used")
bare = R.check_verdict(item, {"id": "r1", "treatment": "DISAGREES", "quote": ""})
check(not R.is_adverse(bare) and "a stance without the sentence that shows it" in bare["problems"], "an adverse stance without its sentence is not used")
check(R.check_verdict(item, {"id": "r1", "treatment": "CITED", "quote": ""})["valid"] and not R.is_adverse(R.check_verdict(item, {"id": "r1", "treatment": "CITED"})), "CITED needs no quote and is not adverse")
check(not R.check_verdict(item, {"id": "r1", "treatment": "maybe"})["valid"], "a treatment outside the list is invalid")
check(not R.is_adverse(None), "no verdict is not adverse")

print()
print("ALL PASSED" if not FAILED else f"{len(FAILED)} FAILED")
sys.exit(1 if FAILED else 0)
