"""Tests for goodlaw/treatment.py: what a sentence does with the case it names. Run: python test_goodlaw_treatment.py

Each case is (sentence, the words that name the target, expected label). The sentences follow the phrasing judges use, including the traps the
rules are built to avoid: negation, an objection being overruled, counsel's arguments, another case sitting between the cue and the target, and a
cue that measures something against the target rather than judging the target.
"""
from goodlaw import treatment as T

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def run(sentence, target):
    i = sentence.index(target)
    return T.classify(sentence, (i, i + len(target)))


CASES = [
    # overruling
    ("We hold that the decision in Suresh Kumar Koushal v. Naz Foundation is overruled.", "Suresh Kumar Koushal v. Naz Foundation", "OVERRULES"),
    ("Accordingly, the judgment in Koushal's case is not good law.", "Koushal's case", "OVERRULES"),
    ("Sowmithri Vishnu v. Union of India and V. Revathi v. Union of India stand overruled.", "Sowmithri Vishnu v. Union of India", "OVERRULES"),
    ("In our considered opinion, Rajendra Prasad is no longer good law on this point.", "Rajendra Prasad", "OVERRULES"),
    ("The view taken in Mithu was wrongly decided and cannot survive.", "Mithu", "OVERRULES"),
    ("The decision in Ram Lal was rendered per incuriam of the earlier Constitution Bench.", "Ram Lal", "OVERRULES"),
    ("The said decision in Shyam v. State is hereby disapproved.", "Shyam v. State", "OVERRULES"),
    # the case stands
    ("The decision in Rangappa has not been overruled and continues to hold the field.", "Rangappa", "NOT_OVERRULED"),
    ("Bhajan Lal has never been overruled.", "Bhajan Lal", "NOT_OVERRULED"),
    ("Baldev Singh remains good law.", "Baldev Singh", "NOT_OVERRULED"),
    # disagreement
    ("We are unable to subscribe to the view taken in Joseph Fernandez v. State of Goa.", "Joseph Fernandez v. State of Goa", "DISAGREES"),
    ("With respect, we differ from the view expressed in Kehar Singh.", "Kehar Singh", "DISAGREES"),
    ("The reasoning in Gopal v. Hari cannot be accepted.", "Gopal v. Hari", "DISAGREES"),
    ("The view taken in Prabha Shankar Dubey that substantial compliance suffices is neither borne out from the language of the section nor in consonance with the dictum in Baldev Singh.", "Prabha Shankar Dubey", "DISAGREES"),
    # a cue that measures something against the target supports the target
    ("The view taken in Prabha Shankar Dubey that substantial compliance suffices is neither borne out from the language of the section nor in consonance with the dictum in Baldev Singh.", "Baldev Singh", "FOLLOWS"),
    # doubt and reference
    ("We have serious doubts about the correctness of the decision in Kartar Singh.", "Kartar Singh", "DOUBTS_REFERS"),
    ("The decision in Hari v. Gopal requires reconsideration by a larger bench.", "Hari v. Gopal", "DOUBTS_REFERS"),
    ("The question is referred to a Constitution Bench for reconsideration of Mohan v. Singh.", "Mohan v. Singh", "DOUBTS_REFERS"),
    # distinguishing
    ("The decision in Rangappa is distinguishable on facts.", "Rangappa", "DISTINGUISHES"),
    ("Rangappa has no application to the present case.", "Rangappa", "DISTINGUISHES"),
    ("The case of Bir Singh cannot be distinguished.", "Bir Singh", "FOLLOWS"),
    # limits
    ("The ratio of Damodar Prabhu must be read in the context of the facts before the Court.", "Damodar Prabhu", "LIMITS"),
    # following
    ("The decision in Rangappa was followed in Basalingappa.", "Rangappa", "FOLLOWS"),
    ("We respectfully agree with the view in Lalita Kumari.", "Lalita Kumari", "FOLLOWS"),
    ("The law laid down in Arnesh Kumar was reiterated by this Court.", "Arnesh Kumar", "FOLLOWS"),
    # a bare mention
    ("Reference may be made to Kesavananda Bharati v. State of Kerala.", "Kesavananda Bharati v. State of Kerala", "NEUTRAL"),
    # legislative response
    ("Parliament amended Section 142 of the Negotiable Instruments Act to overcome the effect of Dashrath Rupsingh Rathod.", "Dashrath Rupsingh Rathod", "LEGISLATIVE"),
]
for sentence, target, want in CASES:
    got = run(sentence, target)["label"]
    check(got == want, f"{want}: {sentence[:90]}" + ("" if got == want else f"   (got {got}: {run(sentence, target)['cue']!r})"))

# traps
r = run("The High Court overruled the objection and relied on Rangappa.", "Rangappa")
check(r["label"] != "OVERRULES", "an objection being overruled is not an overruling of the case")
r = run("It was argued that Bhajan Lal stands overruled.", "Bhajan Lal")
check(r["label"] == "OVERRULES" and r["hedged"], "an overruling that is only argued is flagged hedged")
r = run("If Rangappa were overruled, the presumption would fall.", "Rangappa")
check(r["label"] == "OVERRULES" and r["hedged"], "a hypothetical is flagged hedged")
r = run("Rangappa was followed, while Mohan v. Singh (2001) 3 SCC 4 stands overruled.", "Rangappa")
check(r["label"] == "OVERRULES" and r["binding"] == "weak", "a cue with another case named between it and the target is flagged weak")
r = run("Mohan v. Singh (2001) 3 SCC 4 stands overruled, while Rangappa was followed.", "Rangappa")
check(r["label"] == "OVERRULES" and r["binding"] == "weak", "and the same when the order is reversed")
r = run("In Rangappa the Court examined the matter " + "at great length and " * 20 + "the earlier view stands overruled.", "Rangappa")
check(r["label"] != "OVERRULES", "a cue far from the mention is not tied to it")
s = "The decision in Rangappa v. Sri Mohan (2010) 11 SCC 441 has not been overruled."
i = s.index("Rangappa")
r = T.classify(s, (i, s.index("441") + 3))
check(r["label"] == "NOT_OVERRULED", "a target span that includes its citation works")
check(run("The decision in Rangappa has not been overruled.", "Rangappa")["cue"] is not None and "overrul" in run("The decision in Rangappa has not been overruled.", "Rangappa")["cue"].lower(), "the words that caused the label are returned")
r = run("Rangappa was distinguished in one case but followed in another.", "Rangappa")
check(r["label"] == "DISTINGUISHES" and ("FOLLOWS", "followed") in [(a, b.lower()) for a, b in r["all"]], "the strongest treatment wins and the others are kept in `all`")
check(run("The matter was decided on 5 May 2017.", "matter")["label"] == "NEUTRAL" and run("The matter was decided on 5 May 2017.", "matter")["all"] == [], "no cue gives NEUTRAL with nothing in `all`")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
