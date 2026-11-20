"""planner_set_C.json: a FRESH set written 2026-11-20 AFTER the held-out run of half B (heldout_run1.txt: 86 of 92; two real misses besides the four known file lookups the router sends up: B08 'Which court is the chargesheet
filed in?' went to explain, and BN16 'Write a detailed legal research memo on default bail' was read as a request to draft) and BEFORE the two rule changes. Half B is no longer held out once its misses are fixed; C is the
check of the changes. Written by Claude, not a lawyer. Same labels as planner_set.json; pins as there (True = the last answer listed the sections)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
C = [
 # file questions that contain the word 'court' or a section word but ask a fact of the file
 ("file", [], False, "Which court is the accused being produced before?"),
 ("file", [], False, "In which court was the bail application filed?"),
 ("file", [], False, "Which court issued the remand order?"),
 ("file", [], False, "What court is the chargesheet addressed to?"),
 ("file", [], False, "Which police station registered the FIR?"),
 ("file", [], False, "Which sections does the remand order mention?"),
 # explain with a court property (the section's own trying court)
 ("explain", [], True,  "which court tries these offences?"),
 ("explain", [], True,  "Which court can try the offences charged?"),
 ("explain", [], False, "which court is competent to try section 309(4) BNS?"),
 ("explain", [], True,  "are the offences triable by a Magistrate?"),
 # research memo versus a request to draft
 ("research", [], False, "Prepare a detailed research memo on the law of parity in bail"),
 ("research", [], False, "Write a research note on default bail under section 187 BNSS"),
 ("research", [], False, "Draft a legal research note on whether a TIP is valid after photographs are published"),
 ("research", [], False, "write me a legal research memorandum on identification parades"),
 ("draft", [], False, "Write a bail application for the accused"),
 ("draft", [], False, "Prepare a bail petition from the documents"),
 ("draft", [], False, "Draft a reply to the complainant's letter"),
 ("draft", [], False, "write a petition under section 483 BNSS for bail"),
 # general regression items
 ("standard", [], False, "Is the bail application maintainable before the Sessions Court?"),
 ("standard", [], False, "What happens if the co-accused is not arrested for a long time?"),
 ("standard", [], False, "Can the police seize a motorcycle without a seizure memo?"),
 ("standard", [], True,  "explain the sections and tell me whether he can be released on bail"),
 ("standard", [], False, "What is the effect of the FSL report being delayed?"),
 ("explain", [], False, "what does section 63 of the BSA provide?"),
 ("explain", [], False, "Explain 483 BNSS in simple language"),
 ("explain", [], True,  "what are the ingredients of the offences charged?"),
 ("explain", [], True,  "tell me the punishment for each charged section"),
 ("file", [], False, "What did the complainant say about the helmet?"),
 ("file", [], False, "When was the FIR registered?"),
 ("file", [], False, "Who is the Investigating Officer?"),
 ("research", [], False, "Are there Supreme Court judgments on bail for snatching?"),
 ("research", [], False, "case law on delay in the TIP"),
 ("smalltalk", [], False, "thank you"),
 ("standard", [], False, "Is anything missing from the chargesheet?"),
 ("standard", [], True,  "what is the maximum punishment he can get and how likely is bail"),
 ("explain", [], True,  "are these sections cognizable and bailable?"),
 ("standard", [], False, "What should I argue on the delay in the remand?"),
 ("research", [], True,  "give me citations for this"),
 ("standard", [], False, "How long can police custody be sought?"),
 ("file", [], False, "How many witnesses does the chargesheet list?"),
]
out = {"_note": __doc__, "C": [{"id": f"C{i:02d}", "q": q, "expect": e, "also": a, "pins": p, "kind": "c"} for i, (e, a, p, q) in enumerate(C, 1)]}
json.dump(out, open(os.path.join(HERE, "planner_set_C.json"), "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(len(out["C"]), dict(Counter(x["expect"] for x in out["C"])))
