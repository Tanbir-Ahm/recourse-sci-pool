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
    # the law report's own headnote wording
    ("Cricket Club of India v. Bombay Labour Union & Anr. [1969] 1 SCR 600= AIR [1969] SC 276 over-ruled; Hospital Mazdoor's case AIR 1960 S.C. 610 approved.", "Cricket Club of India v. Bombay Labour Union", "OVERRULES"),
    ("Jagdish & Ors. v. Nathi Mal Kejriwal & Ors., [1986] 4 SCC 510, over-ruled.", "Jagdish & Ors. v. Nathi Mal Kejriwal", "OVERRULES"),
    ("The assumption in A. K. Gopalan v. The State of Madras, [1950] S.C.R. 88, held incorrect.", "A. K. Gopalan v. The State of Madras", "DISAGREES"),
    ("Chhotabhai Jethabhai's case was cited in support of the petition but it was not followed.", "Chhotabhai Jethabhai's case", "DISAGREES"),
    ("Mohan v. Singh, [1960] 2 SCR 5, doubted.", "Mohan v. Singh", "DOUBTS_REFERS"),
    # who overruled whom
    ("Lakhanpal overruled the decision of Shah J. on this point.", "Lakhanpal", "OVERRULED_OTHER"),
    ("The decision of Shah J. was overruled by Lakhanpal.", "Lakhanpal", "OVERRULED_OTHER"),
    ("Chandra Bhan v. State of Rajasthan was overruled by Malik Ram, [1962] 1 SCR 978.", "Chandra Bhan v. State of Rajasthan", "OVERRULES"),
    ("Overruling the earlier decision in Shivji Lal, it was held that the clause needs no extra ingredient.", "Shivji Lal", "OVERRULES"),
    ("Mysore State Road Transport Corporation v. The Mysore Revenue Appellate Tribunal [1975] 1 S.C.R. 493, over-ruled.", "Mysore State Road Transport Corporation", "OVERRULES"),
    ("Kerala SEB v. Amsom, [1977] 1 SCR 996, which overruled the earlier decision in Athani, is the leading case.", "Kerala SEB v. Amsom", "OVERRULED_OTHER"),
    ("Kerala SEB v. Amsom, [1977] 1 SCR 996, which overruled the earlier decision in Athani, is the leading case.", "Athani", "OVERRULES"),
    ("Gopalan's case was disapproved and held to be not correct.", "Gopalan's case", "OVERRULES"),
    # law-report lists: each clause is about its own case
    ("Union of India v. Metal Corporation of India Ltd. [1967] 1 S.C.R. 255 overruled, because Parliament had specified the principles.", "Union of India v. Metal Corporation of India Ltd.", "OVERRULES"),
    ("Mohan Singh v. Bhanwarlal, [1964] 5 S.C.R. 12, disapproved; Amin Lal v. Hunna Mal, [1964] 1 S.C.R. 393, referred to.", "Amin Lal v. Hunna Mal", "NEUTRAL"),
    ("Mohan Singh v. Bhanwarlal, [1964] 5 S.C.R. 12, disapproved; Amin Lal v. Hunna Mal, [1964] 1 S.C.R. 393, referred to.", "Mohan Singh v. Bhanwarlal", "OVERRULES"),
    # a law report's paragraph reference separates one case's note from the next
    ("Mhetre to that extent and other judgments which have followed it are accordingly overruled.[128A-C] Shri Gurbaksh Singh Sibbia and others v. State of Punjab (1980) 2 SCC 565 - relied on.", "Shri Gurbaksh Singh Sibbia and others v. State of Punjab", "FOLLOWS"),
    # the case that did the overruling, named after the case it overruled
    ("After three decades, the Supreme Court overruled its previous decision in A.K. Gopalan and held in its landmark judgment in Maneka Gandhi v. Union of India that the procedure must be reasonable.", "Maneka Gandhi v. Union of India", "OVERRULED_OTHER"),
    ("After three decades, the Supreme Court overruled its previous decision in A.K. Gopalan and held in its landmark judgment in Maneka Gandhi v. Union of India that the procedure must be reasonable.", "A.K. Gopalan", "OVERRULES"),
    # a negated approval is disagreement; the traps around it
    ("At this stage, we are obligated to state that we are not in agreement with the decision rendered in Rajesh Sharma (supra).", "Rajesh Sharma", "DISAGREES"),
    ("The reasoning in Mohan v. Singh, [1960] 2 SCR 5, cannot be followed.", "Mohan v. Singh", "DISAGREES"),
    ("We do not hesitate to follow the decision in Rangappa v. Sri Mohan.", "Rangappa v. Sri Mohan", "FOLLOWS"),
    ("We cannot but follow the decision in Rangappa v. Sri Mohan.", "Rangappa v. Sri Mohan", "FOLLOWS"),
    ("The Court has not only followed but also reiterated Rangappa v. Sri Mohan.", "Rangappa v. Sri Mohan", "FOLLOWS"),
    # the target is the authority that was ignored, or the one a proposition is attributed to
    ("These judgments have clearly ignored a Constitution Bench judgment of this Court in Sibbia case which comprehensively dealt with anticipatory bail, and are therefore per incuriam.", "Sibbia case", "FOLLOWS"),
    ("The decision was given in ignorance of Maneka Gandhi v. Union of India and is per incuriam.", "Maneka Gandhi v. Union of India", "FOLLOWS"),
    ("Reliance was placed on Maneka Gandhi v. Union of India where it was held that the earlier view in Gopalan has been overruled.", "Maneka Gandhi v. Union of India", "NEUTRAL"),
    # traps found by reading adverse readings of cases the reporter marked as followed
    ("In view of two judgments of the Constitution Bench in Romesh Chandra Mehta v. State of West Bengal, [1969] 2 SCR 461 and Illias v. Collector of Customs, [1969] 2 SCR 613, the stand of the appellant cannot be accepted.", "Illias v. Collector of Customs", "NEUTRAL"),
    ("We are unable to agree with Dr. Chitale that this further proposition emerges from the decision in Union of India v. Valluri B. Chaudhary.", "Union of India v. Valluri B. Chaudhary", "NEUTRAL"),
    ("It is not correct to say that the decision in Shri Digvijay Woollen Mills' case does not lay down any principle.", "Shri Digvijay Woollen Mills' case", "NEUTRAL"),
    ("Fazl Ali, J., dissented from the views thus expressed by the majority and reiterated his observations in Brij Bhushan's case.", "Brij Bhushan's case", "FOLLOWS"),
    ("There is nothing to suggest that in Cooper Engineering Ltd. case this Court specifically overruled the decision in R.K. Jain's case.", "R.K. Jain's case", "NOT_OVERRULED"),
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
r = run("It is now suggested that Champakam's case, Romesh Thappar's case and Motilal's case were wrongly decided.", "Motilal's case")
check(r["label"] == "OVERRULES" and r["hedged"], "a reported suggestion across a list of cases is flagged hedged")
r = run("It was argued that Bhajan Lal stands overruled.", "Bhajan Lal")
check(r["label"] == "OVERRULES" and r["hedged"], "an overruling that is only argued is flagged hedged")
r = run("If Rangappa were overruled, the presumption would fall.", "Rangappa")
check(r["label"] == "OVERRULES" and r["hedged"], "a hypothetical is flagged hedged")
r = run("Rangappa was followed, while Mohan v. Singh (2001) 3 SCC 4 stands overruled.", "Rangappa")
check(r["label"] == "OVERRULES" and r["binding"] == "weak", "a cue with another case named between it and the target is flagged weak")
r = run("Mohan v. Singh (2001) 3 SCC 4 stands overruled, while Rangappa was followed.", "Rangappa")
check(r["label"] == "FOLLOWS", "when the other case's overruling comes first and the target is followed after a clause break, the target is not read as overruled")
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

# anaphora: the cue in the next sentence, pointing back at the case
S1 = "The decision in Kartar Singh v. State of Punjab was relied on by the respondents."
S2 = "That decision does not lay down the correct law and we decline to follow it."
i = S1.index("Kartar Singh v. State of Punjab")
r = T.classify_in_context(S1, (i, i + len("Kartar Singh v. State of Punjab")), S2)
check(r["label"] == "OVERRULES" and r["anaphoric"] and r["binding"] == "weak", "a cue in the next sentence that opens 'That decision' is used, marked anaphoric and weak")
r = T.classify_in_context(S1, (i, i + len("Kartar Singh v. State of Punjab")), "Learned counsel then turned to the facts. The decision is wrong, he said.")
check(r["label"] == "FOLLOWS" and not r["anaphoric"], "a next sentence that does not point back at the case is ignored")
r = T.classify_in_context("Kartar Singh v. State of Punjab was overruled.", (0, 28), "That decision was followed in Mohan.")
check(r["label"] == "OVERRULES" and not r["anaphoric"], "the mention's own sentence wins when it already shows a cue")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
