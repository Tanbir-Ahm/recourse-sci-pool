"""Tests for goodlaw/benchcite.py: the bench a case is said to have, as later judgments describe it. Run: python test_goodlaw_benchcite.py"""
import sys
from goodlaw import benchcite as B

FAILED = []


def check(ok, msg):
    print(("[PASS] " if ok else "[FAIL] ") + msg)
    if not ok:
        FAILED.append(msg)


def size(sentence, name):
    i = sentence.index(name)
    return B.attached_size(sentence, (i, i + len(name)))


check(size("In Lalita Kumari v. Govt. of U.P., a Constitution Bench of this Court held that registration is mandatory.", "Lalita Kumari v. Govt. of U.P.") == (5, False),
      "'Constitution Bench' alone means at least five, and is not exact")
check(size("A three-Judge Bench of this Court in Arnesh Kumar v. State of Bihar held so.", "Arnesh Kumar v. State of Bihar") == (3, True), "a descriptor just before the case")
check(size("Arnesh Kumar (supra), a two-Judge Bench decision, was followed.", "Arnesh Kumar") == (2, True), "a descriptor just after the case; '(supra)' is not another case")
check(size("The three-Judge Bench in A v. B overruled the two-Judge Bench in C v. D.", "C v. D") == (2, True) and size("The three-Judge Bench in A v. B overruled the two-Judge Bench in C v. D.", "A v. B") == (3, True),
      "with two cases in a sentence each gets the descriptor next to it, and no other case's")
check(size("The Division Bench of the Delhi High Court in X v. Y held so.", "X v. Y") is None, "a High Court Division Bench says nothing about a Supreme Court bench")
check(size("As held by a Bench of five Judges in Sibbia, anticipatory bail is wide.", "Sibbia") == (5, True), "'a Bench of five Judges'")
check(size("The Court examined the facts of the case and in Sibbia the appeal was allowed.", "Sibbia") is None, "no descriptor gives None")
check(size("A three-Judge Bench in Foo v. State, and thereafter this Court in Sibbia held so.", "Sibbia") is None, "a descriptor with another case between it and the mention is not attached")


def mention(doc, sentence, name, tier="cite", head=False):
    i = sentence.index(name)
    return {"doc_key": doc, "tier": tier, "in_headnote": head, "sentence": sentence, "target_in_sentence": (i, i + len(name))}


S = "A three-Judge Bench of this Court in Sibbia v. State held so."
ms = [mention("a", S, "Sibbia v. State"), mention("b", S, "Sibbia v. State"), mention("c", S, "Sibbia v. State", tier="short")]
check(B.estimate(ms) == (3, True, 2, 2), "two judgments agreeing give the estimate; a short-name mention does not count")
check(B.estimate(ms[:1]) is None, "one judgment is not enough")
check(B.estimate([ms[0], ms[1], mention("c", "A five-Judge Bench in Sibbia v. State held so.", "Sibbia v. State")]) is None, "two against one is below four in five: no estimate")
check(B.estimate([mention("a", S, "Sibbia v. State", head=True), mention("b", S, "Sibbia v. State", head=True)]) is None, "headnote mentions are not read")
check(B.estimate([mention("a", S, "Sibbia v. State"), mention("a", S, "Sibbia v. State"), mention("b", S, "Sibbia v. State")])[3] == 2, "a judgment counts once however often it says it")

print()
print("ALL PASSED" if not FAILED else f"{len(FAILED)} FAILED")
sys.exit(1 if FAILED else 0)
