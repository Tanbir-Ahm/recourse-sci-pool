"""Tests for goodlaw/treatment.py: what a sentence does with the case it names. Run: python test_goodlaw_treatment.py

Each case is (sentence, the words that name the target, expected label). The sentences follow the phrasing judges use, including the traps the
rules are built to avoid: negation, an objection being overruled, counsel's arguments, another case sitting between the cue and the target, and a
cue that measures something against the target rather than judging the target.
"""
from goodlaw import textutil as X
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
    # found on the Overruled-Cases list (2026-10-07): a passive verdict on the law laid down in the case, far from its name; a scanned "is"
    ('The law laid down by this Court in Paras Ram vs. State of Haryana, (1992) 4 SCC 662, that for an offence under Section 5, the recovery must be of "arms and ammunitions" and not of either arm or "ammunition" has been held to be not good law by the Constitution Bench in Sanjay Dutt\u2019s case (supra).', "Paras Ram vs. State of Haryana, (1992) 4 SCC 662", "OVERRULES"),
    ("The decision in Mohan v. Singh has been held not to be good law.", "Mohan v. Singh", "OVERRULES"),
    ("We are of the view that the decision in Jugraj Singh\u2019s case 1s erroneous.", "Jugraj Singh\u2019s case", "DISAGREES"),
    ("The decision in Smt. Rajinder Kaur vs. State of Punjab is hereby over-ruled.", "Smt. Rajinder Kaur vs. State of Punjab", "OVERRULES"),
    ("The view expressed in Narasimhaiah\u2019s case (supra) and Nanjudaiah\u2019s case (supra), is not correct and is over-ruled while that expressed in A.S. Naidu\u2019s case (supra) is affirmed.", "Nanjudaiah\u2019s case (supra)", "OVERRULES"),
    ("The decision in Ram Lal v. State is not correct and is overruled.", "Ram Lal v. State", "OVERRULES"),
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

# errors found by reading a random sample of the checker's own adverse readings (each sentence is real wording from a judgment)
NOT_ADVERSE = ("NEUTRAL", "FOLLOWS", "LIMITS", "DISTINGUISHES", "NOT_OVERRULED", "OVERRULED_OTHER")
for sentence, target, why in [
    ("The Division Bench held that it would not be proper to follow the view and in view of the decision of this Court in Janki Das v. State the contention is not tenable.", "Janki Das v. State", "a decision named as the ground ('in view of') is not the one rejected"),
    ("This argument, we think, is not tenable having regard to the majority decision of this Court in State of West Bengal v. Subodh Gopal Bose.", "State of West Bengal v. Subodh Gopal Bose", "'having regard to T' makes T the authority"),
    ("The Court affirmed the correctness of the decision in K. T. Moopil Nair's case.", "K. T. Moopil Nair's case", "'affirmed the correctness' supports the case"),
    ("The Court then referred to the Constitution Bench decision in Rameshwar Shaw's case and left it to be decided on facts.", "Rameshwar Shaw's case", "'referred to the Constitution Bench decision' cites a decision, it does not refer a question"),
    ("Chaudhary v. State was considered by a larger Bench of this Court in Safdarjung Hospital v. Sethi, when the case law was reviewed.", "Chaudhary v. State", "a larger bench merely considering a case is not a doubt about it"),
    ("This view was held to be erroneous by this Court, in State Bank of India v. R. K. Jain.", "State Bank of India v. R. K. Jain", "'held erroneous by this Court in T': T is the authority"),
    ("The order is per incuriam, passed ignoring the express provisions of Section 7(1) of the Criminal Law (Amendment) Act, 1952 and the earlier decision of this Court in Gurucharan Das Chadha v. State of Rajasthan.", "Gurucharan Das Chadha v. State of Rajasthan", "the authority a decision ignored is not the decision called per incuriam, even a long way after the cue"),
    ("The affidavit filed in response to the rule nisi has not been affirmed by the deponent; see Khudi Ram Das v. State of West Bengal.", "Khudi Ram Das v. State of West Bengal", "'not been affirmed' of an affidavit"),
    ("I am also unable to agree with the view of Chagla, C.J., that the ratio in the decision of Kikabhai's case has no application to the present case.", "Kikabhai's case", "disagreement with a judge's reading of T is not disagreement with T"),
    ("The Court negatived the contention of the appellants that the decision in Khaja Mian Wakf Estate has been over-ruled by the Bank Nationalisation case.", "Khaja Mian Wakf Estate", None),
]:
    r = run(sentence, target)
    if why:
        check(r["label"] in NOT_ADVERSE, f"not read as adverse: {why} (got {r['label']}, cue {r['cue']!r})")
    else:
        check(r["hedged"] or r["label"] in NOT_ADVERSE, f"a contention the Court negatived is hedged (got {r['label']}, hedged {r['hedged']})")
for sentence, target, why in [
    ("In these circumstances, we do not think we will be justified in not following the decision of this Court in Abdulla Ahmed v. Animendra Kissen Mitter.", "Abdulla Ahmed v. Animendra Kissen Mitter", "a double negative: 'not justified in not following' follows T"),
    ("In doing so the High Court has not followed the dictum laid down by this Court in Shranappa Mutyappa Halke v. State of Maharashtra.", "Shranappa Mutyappa Halke v. State of Maharashtra", "a High Court that did not follow T ignored the authority T"),
    ("It was held by this Court in K. S. Venkataraman & Co. v. State of Madras that the assumption underlying the reasoning of the Judicial Committee was not correct.", "K. S. Venkataraman & Co. v. State of Madras", "what T held (that another view was not correct) is not a judgment on T"),
    ("The correctness of the view as laid down in Gopalan's case was doubted by Subba Rao, J. in Kochuni v. The State of Madras.", "Kochuni v. The State of Madras", "'doubted by a judge in T' makes T the place of the doubt"),
    ("The decision in Indian Airlines' case has in terms been declared to be no longer good law and has been overruled in Sukhdev Singh's case by the Constitution Bench.", "Sukhdev Singh's case", "the case that overruled is not the case overruled"),
    ("The majority judgment of this Court in Bharat Kala Bhandar Ltd. v. Municipal Committee contains observations which appear to throw doubt on the correctness of the decision in the Raleigh Investment Company's case.", "Bharat Kala Bhandar Ltd. v. Municipal Committee", "the case containing the doubt is not the case doubted"),
    ("Therefore, the observation in Kerala v. Ramaswami Iyer & Sons that Basappa's case was wrongly decided is open to doubt.", "Basappa's case", None),
    ("There was a criticism that Dhillon's case was no longer good law in the light of Kesavananda Bharati, which was repelled.", "Dhillon's case", None),
]:
    r = run(sentence, target)
    if why:
        check(r["label"] in NOT_ADVERSE, f"not read as adverse: {why} (got {r['label']}, cue {r['cue']!r})")
    else:
        check(r["hedged"] or r["label"] in NOT_ADVERSE, f"a taken-back cue is hedged: {sentence[:50]}... (got {r['label']}, hedged {r['hedged']})")
sp = X.sentences("(1) [1963] 3 S.C.R. 338 at 366. 501 The conduct of the appellant in not following the previous decision of the High Court is calculated to create confusion.")
check(len(sp) == 2, "a footnote's citation line ends its own sentence even when the next page's number follows it")
for sentence, target, why in [
    ("State of Assam -Directions to be complied with: (i) In terms of direction contained in para 100.2, it is directed to provide the particulars of cases in which the mandate of Sections 41, 41-A of CrPC and Arnesh Kumar (Supra) has not been followed.", "Arnesh Kumar (Supra)", "non-compliance with T's mandate is not a judgment on T"),
    ("A two-Judge Bench held that the intervening decisions curtailing the scope of Gurbaksh Singh Sibbia (supra) were per incuriam.", "Gurbaksh Singh Sibbia (supra)", "decisions that curtailed T are what was called per incuriam"),
    ("While considering the issues referred to a larger Bench, referred to hereinabove, the decision of the Constitution Bench of this Court in Gurbaksh Singh Sibbia (supra) is required to be considered in detail.", "Gurbaksh Singh Sibbia (supra)", "the issues were referred, not T"),
]:
    r = run(sentence, target)
    check(r["label"] in NOT_ADVERSE, f"not read as adverse: {why} (got {r['label']}, cue {r['cue']!r})")
r = run("To test the hypothesis that this Court was wrong in not following the dicta of the Constitution Bench in Lalita Kumari, a reverse process can be employed.", "Lalita Kumari")
check(r["hedged"] or r["label"] in NOT_ADVERSE, "a hypothesis being tested is hedged")
r = run("This judgment has been legislatively overruled by Section 142(2) of the Negotiable Instruments Act.", "This judgment")
check(r["label"] == "LEGISLATIVE", f"'legislatively overruled' is a legislative response, not a judicial overruling (got {r['label']})")
r = run("However, a five-Judge Bench of this Court in Vijaysinh Chandubha Jadeja v. State of Gujarat reported in (2011) 1 SCC 609, overruled the decisions in Prabha Shankar Dubey (supra) and Joseph Fernandez (supra) and disapproved the concept of substantial compliance.", "Prabha Shankar Dubey (supra)")
check(r["label"] == "OVERRULES" and r["binding"] == "strong", f"'X, overruled the decisions in T': X before the verb does not make T's reading weak (got {r['label']}, {r['binding']})")
r = run("Rangappa was followed, while Mohan v. Singh (2001) 3 SCC 4 stands overruled.", "Rangappa")
check(r["binding"] == "weak", "a case between the target and the cue still makes the reading weak")
check("PUTTASWAMY" not in X.flatten("held in the matter. JUSTICE K S PUTTASWAMY (RETD) v. UNION OF INDIA [ASHOK BHUSHAN, J.] The Court then said") and "705" not in X.flatten("held. A B C D E F G H 705 The Court said"), "running captions and margin letters of the digital law reports are dropped")
check(X.flatten("Section 5 applies to A, B and C and the State.") == "Section 5 applies to A, B and C and the State.", "ordinary lettered lists are not mistaken for margin letters")
r = run("[1954] SCR 1077 partly overruled Para 2 [1964] 1 SCR 332 partly overruled Para 3 [1978] 2 SCR 621 relied on Para 3", "[1978] 2 SCR 621")
check(r["label"] in NOT_ADVERSE, f"in a case-law table each entry ends at its paragraph number: an earlier entry's 'overruled' is not this one's (got {r['label']})")
r = run("[1954] SCR 1077 relied on Para 2 [1978] 2 SCR 621 partly overruled Para 3", "[1978] 2 SCR 621")
check(r["label"] == "OVERRULES", "and an entry's own code still counts")
# wording from the held-out half's wrong readings, added after that half had been scored once (so these fixes are not measured on it)
for sentence, target, what in [
    ("This view was neither overruled nor departed from in the Safdarjung Hospital case (supra).", "Safdarjung Hospital case", "'neither overruled nor'"),
    ("It cannot be said that the decision in Laxman Pimputkar's case can be deemed to have overruled by necessary implication the view of the High Court.", "Laxman Pimputkar's case", "'cannot be said that ... overruled'"),
    ("We are not prepared to hold that the decision in Shantilal Mangaldas's case is overruled by the Bank Nationalisation case.", "Shantilal Mangaldas's case", "'not prepared to hold that ... overruled'"),
    ("The majority decision in Chiranjit Lal Chowdhuri's case has binding force till it is reconsidered or overruled by this Court.", "Chiranjit Lal Chowdhuri's case", "'till it is ... overruled'"),
    ("The decisions in U.P. Warehousing Corporation and Indian Airlines Corporation are in direct conflict with the decision of this Court in Naraindas Barot v. S.T.C. and are wrongly decided.", "Naraindas Barot v. S.T.C.", "'in direct conflict with T'"),
    ("The petitioners pray for reconsideration of the three decisions in S.G. Jaisinghani v. Union of India.", "S.G. Jaisinghani v. Union of India", "a prayer"),
    ("For these reasons the contention put forward by Mr. Dikshit in Man Industrial Corporation's case on this score is overruled.", "Man Industrial Corporation's case", "an overruled contention"),
]:
    r = run(sentence, target)
    check(r["label"] in NOT_ADVERSE or r["hedged"], f"not a clean adverse reading: {what} (got {r['label']}, hedged {r['hedged']}, cue {r['cue']!r})")
import goodlaw.mentions as _M
check(_M.speaker("The Attorney General referred to a number of earlier decisions wanting us to infer that the observations did not state the correct law.", "", False)[0] == "counsel", "the Attorney General referring to decisions is counsel's voice")
# modern wording found by reading the modern answer key's misses
for sentence, target, what in [
    ("He referred to a judgment of this Court in Meters and Instruments Private Limited v. Kanchan Mehta which reads as follows: the observation is clear.", "Meters and Instruments Private Limited v. Kanchan Mehta", "'reads as follows' is not following the case"),
    ("The Court examined the following passage from Rangappa v. Sri Mohan in the light of the facts.", "Rangappa v. Sri Mohan", "'the following passage' is not following the case"),
    ("The decisions in Rowther-I, Forbes-II and Rasiklal do not seem to follow a consistent line about the liability.", "Forbes-II", "'follow a consistent line' is not following the case"),
]:
    r = run(sentence, target)
    check(r["label"] != "FOLLOWS", f"not read as followed: {what} (got {r['label']}, cue {r['cue']!r})")
r = run("Following the decision in Rangappa v. Sri Mohan, the presumption is rebuttable.", "Rangappa v. Sri Mohan")
check(r["label"] == "FOLLOWS", "'Following the decision in T' is still following it")
r = run("In the decision in Raghbir Singh Sehrawat v. State of Haryana, the observation made was that it is not possible to take possession of the entire land in a day, cannot be accepted as laying down the law correctly and same is contrary to precedent.", "Raghbir Singh Sehrawat v. State of Haryana")
check(r["label"] == "DISAGREES", f"'cannot be accepted as laying down the law correctly' judges the decision it follows (got {r['label']})")
r = run("We are of the view that the judgments in Purbanchal Cables and Conductors (supra) and Shakti Tubes which held that the Act shall apply only when the contract was entered after its enforcement, do not lay down the correct law.", "Purbanchal Cables and Conductors (supra)")
check(r["label"] == "OVERRULES", f"'judgments in T, which held that ..., do not lay down the correct law' is a verdict on T (got {r['label']})")
r = run("It was held in Mohan v. Singh that the view of the High Court does not lay down the correct law.", "Mohan v. Singh")
check(r["label"] != "OVERRULES", "but 'it was held in T that the view ... does not lay down the correct law' is still T's holding, not a verdict on T")
# errors found by reading a sample of modern adverse readings (tuning half of the modern answer key)
for sentence, target, what in [
    ("In the case of Indore Development Authority (supra), the decision of this Court in the case of Pune Municipal Corporation (supra) has been specifically overruled.", "Indore Development Authority (supra)", "'In T, the decision of Y has been overruled': T did the overruling"),
    ("In S. Nagaraj (supra), it was also made clear by this Court that binding decisions cannot be ignored even on the principles of per incuriam.", "S. Nagaraj (supra)", "the principles of per incuriam are the topic"),
    ("There is nothing in the Satyawati Sharma judgment which can be said to be per incuriam.", "Satyawati Sharma", "'nothing ... which can be said to be per incuriam'"),
    ("The submission that after the amendment the law laid down in National Seeds Corporation Limited (supra) is no more a good law cannot be accepted.", "National Seeds Corporation Limited (supra)", "a submission that T is no longer good law, rejected"),
    ("It was not open for the High Court to not follow the binding decision of this Court in Peerappa Hanmantha Harijan (supra).", "Peerappa Hanmantha Harijan (supra)", "a High Court not following T ignored the authority"),
    ("However, by not following the decision of this Court in D.S. Nakara (supra), the Division Bench of the High Court has not considered the matter.", "D.S. Nakara (supra)", "'by not following T' by a High Court"),
]:
    r = run(sentence, target)
    check(r["label"] in NOT_ADVERSE or r["hedged"], f"not a clean adverse reading: {what} (got {r['label']}, hedged {r['hedged']}, cue {r['cue']!r})")
r = run("In case this Court does not agree with the decision rendered in Dinesh Chandra Sangma (supra), the matter may be referred to a larger Bench.", "Dinesh Chandra Sangma (supra)")
check(r["hedged"] or r["label"] in NOT_ADVERSE, "a conditional ('In case this Court does not agree') is hedged")
import goodlaw.mentions as _M2
check(_M2.speaker("The reliance of Mr. Rao on the judgment of this Court in K. Ethirajan is not tenable.", "", False)[0] == "counsel", "'The reliance of Mr. Rao on ...' is counsel's voice")
check(_M2.speaker("The stand of the State appears to be that the judgment was not correctly decided.", "", False)[0] == "counsel", "'The stand of the State' is a party's voice")
r = run("This Court overruled the judgment of this Court reported as Vannattankandy Ibrayi v. Kunhabdulla Hajee and held as under.", "Vannattankandy Ibrayi v. Kunhabdulla Hajee")
check(r["label"] == "OVERRULES", "'overruled the judgment ... Y' is still an overruling of Y")
r = run("Accordingly, the earlier decision of this Court in H. Anraj vs. Govt. of T.N. was overruled.", "H. Anraj vs. Govt. of T.N.")
check(r["label"] == "OVERRULES", "'the earlier decision in T was overruled' is still an overruling of T")
# step 2: span and voice around the mention, and the sentence after it
r = run("Town Municipal Council Athani v. Presiding Officer, Labour Court, [1970] 1 S.C.R.51 over-ruled in [1977] 1 S.C.R. 996.", "Town Municipal Council Athani v. Presiding Officer, Labour Court")
check(r["label"] == "OVERRULES", f"headnote style 'T, [cite], over-ruled in [cite]': T was overruled, the overruler is cited after (got {r['label']})")
r = run("In any case majority decision in Dhillon's case (supra) is neither overruled nor departed from in Kesavananda's case (supra).", "Dhillon's case (supra)")
check(r["label"] == "NOT_OVERRULED", f"'is neither overruled nor departed from' says the case stands (got {r['label']})")
r = run("But be that as it may, we find ourselves with all respect unable to agree with the view taken in Tarak Nath Ghosh's case (supra).", "Tarak Nath Ghosh's case (supra)")
check(r["label"] == "DISAGREES" and not r["hedged"], f"'be that as it may' is not a hedge (got {r['label']}, hedged {r['hedged']})")
r = run("We are unable to subscribe to the view which has been adopted in the above decision in M Krishnan (supra).", "M Krishnan (supra)")
check(r["label"] == "DISAGREES", f"'unable to subscribe to the view which has been adopted in the above decision in T' is disagreement with T (got {r['label']})")
r = run("The legal position cannot be said to have been correctly appreciated in Angad Kol's case (supra), for the reasons discussed by us.", "Angad Kol's case (supra)")
check(r["label"] == "DISAGREES", f"'cannot be said to have been correctly appreciated in T' is disagreement (got {r['label']})")
S1 = "The learned counsel relied on Angad Kol's case (supra)."
S2 = "Thus, the decision is required to be overruled as the vehicle was a light motor vehicle."
i = S1.index("Angad Kol's case (supra)")
r = T.classify_in_context(S1, (i, i + len("Angad Kol's case (supra)")), S2)
check(r["label"] == "OVERRULES" and r["anaphoric"] and r["binding"] == "weak", f"'Thus, the decision is required to be overruled' in the next sentence is read as about the case, marked anaphoric and weak (got {r['label']}, {r.get('anaphoric')}, {r['binding']})")
r = T.classify_in_context(S1, (i, i + len("Angad Kol's case (supra)")), "Thus, the matter is remanded for fresh consideration. The High Court shall decide it.")
check(not r["anaphoric"], "a next sentence that does not point back at the case adds nothing")
r = T.classify_in_context(S1, (i, i + len("Angad Kol's case (supra)")), "The decision of the High Court in Sharma was per incuriam of the Constitution Bench.")
check(not r["anaphoric"], "a bare 'The decision ...' with no concluding marker is not taken to be about the case")
# false alarms found by reading the checker's flagged cards for Recourse's own library (each sentence is real wording from a judgment)
NOT_LEGISLATIVE = NOT_ADVERSE
for sentence, target, why in [
    ("This, undoubtedly, is the position even under the decision in Shreya Singhal (supra) which has read down Section 79(3)(b) and the Intermediary Rules already noted.", "Shreya Singhal (supra)", "'undoubtedly' is not 'undo'"),
    ("Siddharam Satlingappa Mhetre v. State of Maharashtra is worthy of mention in this context, despite its partial overruling in Sushila Aggarwal (supra).", "Sushila Aggarwal (supra)", "'its overruling in T': T did the overruling"),
    ("In 2020 a three-judges Bench answered a Reference Order in Tofan Singh v. State of Tamil Nadu42 and re-examined the ratio of Kanhaiyalal33 (supra) and Raj Kumar Karwal35 (supra).", "Tofan Singh v. State of Tamil Nadu42", "the case that re-examined others is not itself re-examined"),
    ("For all these reasons, we do not accede either to Shri Puneet Jain's argument to refer Mukesh Singh (supra) to a larger Bench for reconsideration, or to Shri Lekhi's argument based on the same judgment.", "Mukesh Singh (supra)", "a refusal to refer is not a doubt"),
    ("Later judgments such as Noor Aga (supra) ought to be overruled by us, inasmuch as they are contrary to several Constitution Bench judgments of this Court.", "Noor Aga (supra)", None),
]:
    r = run(sentence, target)
    if why:
        check(r["label"] in NOT_ADVERSE and r["label"] != "LEGISLATIVE", f"not read as a warning: {why} (got {r['label']}, cue {r['cue']!r})")
    else:
        check(r["hedged"], f"'ought to be overruled' is hedged (got {r['label']}, hedged {r['hedged']})")
r = run("We decline to accept the submission that Noor Aga (supra) is no longer good law.", "Noor Aga (supra)")
check(r["label"] in NOT_ADVERSE, f"declining to accept that a case is no longer good law leaves it standing (got {r['label']})")
r = run("Siddharam Satlingappa Mhetre v. State of Maharashtra was overruled in Sushila Aggarwal (supra) to that extent.", "Siddharam Satlingappa Mhetre v. State of Maharashtra")
check(r["label"] == "OVERRULES", "and the case that was overruled is still read as overruled")

# a 'not' that belongs to an earlier clause ("is not correct and is overruled") does not turn the overruling into its opposite, but a 'not' on the verb still does
for sentence, target in [("The decision in Ram Lal v. State is not over-ruled.", "Ram Lal v. State"), ("The decision in Ram Lal v. State has never been overruled and is good law.", "Ram Lal v. State")]:
    r = run(sentence, target)
    check(r["label"] == "NOT_OVERRULED", f"a negated verb still says the case stands: {sentence} (got {r['label']})")

# the case is the place where something was held, not the case being judged (found when names with "& Ors." began to be recognised)
for sentence, target, why in [
    ("The decision rendered in ignorance of a binding precedent and/or ignorance of a provision has been held to be per incuriam in Subhash Chandra & Ors. v. Delhi Subordinate Services Selection Board & Ors. (2009) 15 SCC 458, Dashrath Rupsingh Rathod v. State of Maharashtra (2014) 9 SCC 129, and Central Board of Dawoodi Bohra Community & Ors. v. State of Maharashtra & Ors. (2005) 2 SCC 673.",
     "Subhash Chandra & Ors. v. Delhi Subordinate Services Selection Board & Ors. (2009) 15 SCC 458", "'held to be per incuriam in T' names the case that held it"),
    ("The decision rendered in ignorance of a binding precedent and/or ignorance of a provision has been held to be per incuriam in Subhash Chandra & Ors. v. Delhi Subordinate Services Selection Board & Ors. (2009) 15 SCC 458, Dashrath Rupsingh Rathod v. State of Maharashtra (2014) 9 SCC 129, and Central Board of Dawoodi Bohra Community & Ors. v. State of Maharashtra & Ors. (2005) 2 SCC 673.",
     "Dashrath Rupsingh Rathod v. State of Maharashtra (2014) 9 SCC 129", "and so are the cases listed after it"),
    ("It has been held by this Court in Ram Pravesh Singh & Ors. v. State of Bihar & Ors.55 that directions given under Article 142 is not law laid down under Article 141.",
     "Ram Pravesh Singh & Ors. v. State of Bihar & Ors.", "a footnote number after the name does not make the proposition the case's own"),
    ("It has been held by this Court in Ram Pravesh Singh & Ors. v. State of Bihar & Ors.55 that directions given under Article 142 is not law laid down under Article 141.",
     "Ram Pravesh Singh & Ors. v. State of Bihar", "nor does '& Ors.' and a footnote number after a shorter match of the name"),
]:
    r = run(sentence, target)
    check(r["label"] in NOT_ADVERSE and r["label"] != "LEGISLATIVE", f"not read as a warning: {why} (got {r['label']}, cue {r['cue']!r})")

# the case is a point in time, or the ground named in an opening phrase, and the verdict belongs to the clause that follows (found on Puttaswamy, a settled case)
for sentence, target, why in [
    ("One\u2019s sexual orientation is undoubtedly an attribute of privacy\u2026\u201d125 With these observations by five of the nine judges in Puttaswamy,the basis on which Koushal upheld the validity of Section 377 stands eroded and even disapproved.",
     "Puttaswamy", "the case is the ground named in an opening phrase"),
    ("The judgments in MP Sharma and Kharak Singh being those of 8 and 6 judges respectively, judgments of smaller benches delivered during the period upto Puttaswamy would be per incuriam.",
     "Puttaswamy", "'up to T' fixes a point in time"),
    ("In view of Mohan v. Singh, the earlier decision in Ram Lal is overruled.", "Mohan v. Singh", "the case is the ground for overruling another"),
]:
    r = run(sentence, target)
    check(r["label"] in NOT_ADVERSE and r["label"] != "LEGISLATIVE", f"not read as a warning: {why} (got {r['label']}, cue {r['cue']!r})")
for sentence, target, want in [
    ("With respect, the decision in Mohan v. Singh does not lay down the correct law.", "Mohan v. Singh", "OVERRULES"),
    ("The Bench felt. With respect, Mohan v. Singh does not lay down the correct law.", "Mohan v. Singh", "OVERRULES"),
    ("Applying Maneka Gandhi, Mohan v. Singh must be held to be wrongly decided.", "Mohan v. Singh", "OVERRULES"),
]:
    r = run(sentence, target)
    check(r["label"] == want, f"an opening phrase that is not about the case does not hide a verdict on it: {sentence[:50]}... (got {r['label']})")

# the three misreads that settled library cases showed once more mentions counted as confident (Mukesh Singh, Sushila Aggarwal, Puttaswamy)
r = run("The acquittal was merely on technical ground in view of Mohan Lal\u2019s case (supra) which was diluted in Varinder Kumar\u2019s case (supra) and then overruled subsequently by the Constitution Bench of this Court in Mukesh Singh\u2019s case (supra).", "Mukesh Singh\u2019s case")
check(r["label"] == "OVERRULED_OTHER", f"'overruled subsequently by the Constitution Bench in T': T is the case that did the overruling, an adverb between the verb and 'by' changes nothing (got {r['label']})")
r = run("The acquittal was merely on technical ground in view of Mohan Lal\u2019s case (supra) which was diluted in Varinder Kumar\u2019s case (supra) and then overruled subsequently by the Constitution Bench of this Court in Mukesh Singh\u2019s case (supra).", "Mohan Lal\u2019s case")
check(r["label"] == "OVERRULES", f"and the case it overruled is still read as overruled (got {r['label']})")
for sentence, target, why in [
    ("After marshalling the entire range of juridical materials on anticipatory bail, the Constitution Bench in Sushila Aggarwal held the judgements of this Court that postulated greater limitations on the grant of anticipatory bail to be not good law.",
     "Sushila Aggarwal", "'T held X to be not good law': the verdict is on X"),
    ("In Sushila Aggarwal, the Constitution Bench held earlier views not to be good law.", "Sushila Aggarwal", "'T held X not to be good law': the verdict is on X"),
    ("There is, therefore, all the greater reason why any one provision is not, by construction, treated as nullifying the existence and effect of another.\u201d132 In Puttaswamy, a unanimous verdict by a nine judge Bench declared privacy to be constitutionally protected.",
     "Puttaswamy", "a cue in the sentence the splitter ran into this one (closing quote, footnote number, capital) is not about the case"),
]:
    r = run(sentence, target)
    check(r["label"] in NOT_ADVERSE and r["label"] != "LEGISLATIVE", f"not read as a warning: {why} (got {r['label']}, cue {r['cue']!r})")
r = run("The earlier test was applied for years.\u201d12 Mohan v. Singh is overruled.", "Mohan v. Singh")
check(r["label"] == "OVERRULES", f"a verdict in the case's own sentence after a run-together break is still read (got {r['label']})")
r = run("The earlier test was applied for years.\u201d12 Mohan v. Singh has been held to be not good law.", "Mohan v. Singh")
check(r["label"] == "OVERRULES", f"'has been held to be not good law' (passive) is still read as a verdict on the subject (got {r['label']})")

# "be not good law" is a verdict only when nothing negates it
for sentence, target, why in [
    ("Ram Lal v. State, which governs the field, cannot be held to be not good law.", "Ram Lal v. State", "a double negative leaves the case standing"),
    ("It cannot be said that Ram Lal v. State is held to be not good law.", "Ram Lal v. State", "a double negative leaves the case standing"),
]:
    r = run(sentence, target)
    check(r["label"] in NOT_ADVERSE and r["label"] != "LEGISLATIVE", f"not read as a warning: {why} (got {r['label']}, cue {r['cue']!r})")
r = run("We are of the view that the decision in Jugraj Singh\u2019s case 1s erroneous.", "Jugraj Singh\u2019s case")
check(r["cue"] == "1s erroneous", f"a cue is shown as printed even when a scanned word was read as the word it stands for (got {r['cue']!r})")
r = run("The Court said that a strike 1s legal; the decision in Mohan v. Singh was followed.", "Mohan v. Singh")
check(r["label"] == "FOLLOWS", f"reading a scanned 'is' changes nothing else (got {r['label']})")

# and the real ones still fire
for sentence, target, want in [
    ("The Court in Ashoka Marketing Ltd. did not follow the decision in Orient Paper Mills v. State of Orissa.", "Orient Paper Mills v. State of Orissa", "DISAGREES"),
    ("The Division Bench felt that the decision in Ram Sarup's case was erroneous and needed reconsideration.", "Ram Sarup's case", None),
    ("We therefore find ourselves unable to agree with the majority in the Northern India Caterers' case.", "Northern India Caterers' case", "DISAGREES"),
    ("The matter was placed before a larger Bench to reconsider Mohan v. Singh.", "Mohan v. Singh", "DOUBTS_REFERS"),
]:
    r = run(sentence, target)
    check(r["label"] == want if want else r["label"] in ("OVERRULES", "DISAGREES", "DOUBTS_REFERS"), f"still read as adverse: {sentence[:60]}... (got {r['label']}, cue {r['cue']!r})")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
