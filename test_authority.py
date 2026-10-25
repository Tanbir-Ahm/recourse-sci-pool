"""Tests for authority.py (no network, no model, costs nothing). Run: python test_authority.py

Every passage quoted here is real text from a public judgment in the index, and most of them are cases where an earlier version of the rules was wrong; the
comment on each says which. The measured accuracy against hand labels is in review_results/2026-10-25_voice_rule/.
"""
import authority as A

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


HC = {"court": "Gauhati High Court"}
SC = {"court": "Supreme Court of India"}

# ---------------------------------------------------------------- one sentence at a time
check(A.voice_of("Mr. M.K. Borah, learned counsel for the petitioner submits that the allegations are false.")[0] == A.COUNSEL, "a named lawyer submitting is counsel")
check(A.voice_of("It was further submitted that the sequence of events is improbable.")[0] == A.COUNSEL, "an impersonal submission is counsel")
check(A.voice_of("Learned counsel for the appellant has vehemently argued that the prosecution failed to prove motive.")[0] == A.COUNSEL, "an argument is counsel")
check(A.voice_of("This court records its appreciation for the assistance rendered by the learned Amicus Curiae.")[0] is None,
      "a lawyer merely mentioned is not the speaker: the court is thanking them")
check(A.voice_of("From the contentions and submissions made by the learned counsel for the parties, two issues have arisen for consideration.")[0] is None,
      "the court describing the submissions it has received is not counsel")
check(A.voice_of("Thus, having carefully considered the submissions of learned Advocates of both sides, I find no merit in this petition.")[0] == A.COURT,
      "the court deciding after hearing the lawyers is the court")
check(A.voice_of("It is difficult to accept the said contention.")[0] == A.COURT, "the court rejecting an argument is the court, not the argument")
check(A.voice_of("Heard Mr. R. Ali, learned counsel for the petitioner and also heard Mr. P. Borthakur, learned Additional Public Prosecutor.")[0] == A.COURT,
      "the court recording who appeared is the court")
check(A.voice_of("The learned Chief Judicial Magistrate held that the offence under Section 389 of the Indian Penal Code is a non-compoundable offence.")[0] == A.LOWER_COURT,
      "a magistrate who held something is the court below")
check(A.voice_of("It has been observed by the learned Court below that the accused appeared and pleaded not guilty.")[0] == A.LOWER_COURT, "the verb may come before the court below")
check(A.voice_of("The learned Court by the said order had held that the provision under Section 143(A) of the N.I. Act is discretionary.")[0] == A.LOWER_COURT,
      'a judgment never calls itself "the learned Court"')
check(A.voice_of("If the arrest effected by the police officer does not satisfy the requirements of Section 41 of the Code, Magistrate is duty bound not to authorise his further detention.")[0] is None,
      "a rule ABOUT magistrates is not a magistrate speaking (it is Arnesh Kumar, and reading it as the court below demoted it wrongly)")
check(A.voice_of("In Vijaysinh the Supreme Court has held that the requirements of Section 50 of the NDPS Act are mandatory.")[0] == A.HIGHER_COURT, "a higher court quoted")
check(A.voice_of("The prosecution case is that the accused demanded dowry from the deceased.")[0] == A.PARTY, "a party's case is the party's")
check(A.voice_of("The mere claim that a telegram was sent could not have been a ground to hold that the prosecution version was unacceptable.")[0] is None,
      "the court's own words about the prosecution's version are not the prosecution's")
check(A.voice_of("We are unable to accept the contention of learned counsel that the presumption does not arise.")[0] == A.COURT,
      "first person wins: a court writing 'we' speaks for itself even while describing the argument it rejects")
check(A.voice_of("The High Court held that the complaint was not maintainable.", own_tier=A.SC)[0] == A.LOWER_COURT, "in a Supreme Court judgment the High Court is the court below")
check(A.voice_of("The High Court held that the complaint was not maintainable.", own_tier=A.HC)[0] is None, "in a High Court judgment those same words are not a court below")

# ---------------------------------------------------------------- does the sentence state law
check(A.substantive("The presumption under Section 139 of the N.I. Act is rebuttable and the accused must lead evidence."), "a rule states law")
check(A.substantive("Thus for the reasons stated above, I have no hesitation in my mind to hold that the allegations make out a civil dispute."), "a holding states law")
check(not A.substantive("The accused petitioner was arrested in said All Women P S Case No. 43/1998 and was detained in custody for 21 days."),
      "the file's history is not law, however well it matches a question")
check(not A.substantive("I have perused the relevant materials and considered the submissions."), "perusing is not law")
check(not A.substantive("Heard both sides."), "a fragment is not law")

# ---------------------------------------------------------------- the whole passage
TRIAL_QUOTE = ('6. The learned Trial Court upon considering the evidences coming on record had drawn the following conclusions ; “During his entire evidence PW1 has failed to state '
               'the manner of handing over the amount to the accused. But merely because the accused had put his signature in Ext.1 the statutory presumption u/s 139 of the Act cannot be '
               'raised when the prosecution has failed to show that the accused was liable to pay. Hence, I hold that the accused does not have any liability towards the complainant.')
v = A.classify(TRIAL_QUOTE, src=HC)
check(v["tier"] == A.TRIAL and v["voice"] == A.LOWER_COURT, "a quoted trial-court conclusion is tier 3, not the High Court's own (entry 21 of the tier test)")
check(all(s[0] == A.LOWER_COURT for s in v["sentences"][1:]), 'the trial judge\'s own "I hold" inside the quotation stays the trial judge\'s')

COUNSEL_ONLY = ('6. As regards the contention that the order was passed mechanically, the learned senior counsel, referring to Section 41(1) and Section 41(A), submits that there is a '
                'difference between the provisions.')
v = A.classify(COUNSEL_ONLY, src=HC)
check(v["blocked"] and "lawyer" in v["reason"], "a passage that is only a submission is blocked: it must never be shown")

MIXED = ('11. Mr. M.K. Borah, learned counsel for the petitioner submits that the allegations levelled in the FIR are fabricated. The jurisdiction of this Court under Section 482 for '
         'quashing the FIR is well settled: the Court is required to test the allegations at their face value and to see whether they prima facie constitute any offence.')
v = A.classify(MIXED, src=HC)
check(not v["blocked"] and v["tier"] == A.HC, "a passage where the court states the law after setting out the argument is kept, at the court's own tier")
check("learned counsel" not in v["quote"] and "jurisdiction of this Court" in v["quote"], "what a page quotes from it holds none of the lawyer's words")

CITED = ('63. Learned counsel for the appellant has also cited a ruling of the Apex Court in Sudarshan v. State of Maharashtra wherein it was observed as follows: “The necessity of '
         'sending the copy of the FIR to the Magistrate concerned hardly needs to be emphasised. For this reason, this statutory requirement is provided under Section 157 of the Code.”')
v = A.classify(CITED, src=HC)
check(not v["blocked"] and v["tier"] == A.SC, "inside the quotation marks a lawyer opens, the words belong to the court being cited, and carry that court's tier")
check("Learned counsel" not in v["quote"], "the lawyer's framing of the citation is still not quoted")

FACTS = "7. The accused petitioner was arrested in said All Women P S Case No. 43/1998 and was detained in custody for 21 days. After the investigation was over, the police submitted the charge-sheet."
v = A.classify(FACTS, src=HC)
check(not v["blocked"] and v["states_law"] is False, "the court's own background narrative is not blocked, only marked as stating no law (so it sorts last)")

APPROVAL = "6. We are in full agreement with the above conclusions of the High Court and we find no good grounds to interfere with the same. As rightly argued by learned counsel for the respondent, the identity of the body was never disputed."
v = A.classify(APPROVAL, src=SC)
check(not v["blocked"] and v["tier"] == A.SC, "the Supreme Court agreeing with the High Court is the Supreme Court's own words (an earlier version blocked this)")

UNNAMED = "” So far as the question of conspiracy under Section 120-B is concerned, it is not necessary to have direct evidence because a conspiracy is hatched in secrecy."
check(A.classify(UNNAMED, src=SC)["tier"] is None, "a passage cut out of the middle of somebody's quotation has no known tier, so it is never promoted")

check(A.classify("", src=HC)["blocked"] is False or True, "empty text does not raise")
check(A.safe_classify(None, src=HC)["blocked"] is True, "anything unreadable is blocked, not let through")

# ---------------------------------------------------------------- the court whose judgment it is
check(A.deciding_court(None, 42917)[0] == A.SC and A.deciding_court(None, 1_000_254_066)[0] == A.SC, "the crawl and the open bucket are Supreme Court judgments")
check(A.deciding_court(HC, 2_000_753_784)[0] == A.HC and A.deciding_court({"court": "Chief Judicial Magistrate"}, None)[0] == A.TRIAL, "an extra source names its court")
check(A.deciding_court({"court": "Some Other Body"}, None)[0] is None, "a court the rules do not know is no tier at all, so it can never be ordered above a known one")

# ---------------------------------------------------------------- the order, which is the owner's rule in code
SC_LAW = {"authority": {"tier": A.SC, "states_law": True, "blocked": False}, "score": 0.10}
HC_LAW = {"authority": {"tier": A.HC, "states_law": True, "blocked": False}, "score": 0.20}
TRIAL_LAW = {"authority": {"tier": A.TRIAL, "states_law": True, "blocked": False}, "score": 0.99}
HC_FACTS = {"authority": {"tier": A.HC, "states_law": False, "blocked": False}, "score": 0.95}
ARGUMENT = {"authority": {"tier": None, "states_law": False, "blocked": True}, "score": 1.00}
out = A.order([TRIAL_LAW, ARGUMENT, HC_FACTS, SC_LAW, HC_LAW])
check(out == [SC_LAW, HC_LAW, HC_FACTS, TRIAL_LAW], "Supreme Court, then High Court, then the trial court - whatever the scores say")
check(ARGUMENT not in out, "a lawyer's argument is not in the list at all")
check(A.order([TRIAL_LAW])[0] is TRIAL_LAW, "a trial court's view is still shown when it is all there is; it is only never above a higher court")
check(A.sort_key({"tier": A.TRIAL, "states_law": True}, 0.99) > A.sort_key({"tier": A.HC, "states_law": False}, 0.01),
      "no similarity score, however high, can lift a trial court above a High Court")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED:")
    for f in FAILURES:
        print("  -", f)
    raise SystemExit(1)
print("ALL PASSED")
