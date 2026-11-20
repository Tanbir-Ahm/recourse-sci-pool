"""Builds planner_set.json: the frozen question set for the Matter Workspace planner (W1 + W2), written 2026-11-20 BEFORE any planner code
(owner's go: 'Go ahead with W1 and W2 together'). Written by Claude, not a lawyer.
Kinds (expect): file (answer lives in the documents), explain (explain named or charged sections: law on hand), standard (apply the law on hand to the facts, no cases),
research (an explicit ask for cases or a detailed note), draft (a request to draft), smalltalk (thanks/hello).
'also' lists other kinds that are acceptable. 'pins' says whether the last answer in the conversation listed the charged sections (so 'the sections' can be resolved by code).
Half A is for writing the rules; half B is held out and run ONCE after the rules are fixed. The file and draft items and the legal items are the router set of 2026-11-20 (commit 4c5b51c), relabelled by size."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "..", "2026-11-20_matter_routing", "router_set.json")))

# law items of the router set -> size (primary, also)
LAW = {
 "A25": ("explain", []), "A26": ("standard", []), "A27": ("explain", []), "A28": ("standard", []), "A29": ("standard", []), "A30": ("standard", []), "A31": ("standard", []), "A32": ("standard", []),
 "A33": ("standard", ["research"]), "A34": ("standard", ["research"]),
 "A35": ("standard", []), "A36": ("standard", []), "A37": ("standard", []), "A38": ("standard", []), "A39": ("standard", []), "A40": ("standard", []), "A41": ("standard", []), "A42": ("standard", []),
 "A43": ("standard", []), "A44": ("standard", []), "A45": ("standard", []), "A46": ("standard", []),
 "A47": ("explain", ["standard"]), "A48": ("explain", []), "A49": ("explain", []), "A50": ("standard", []),
 "A57": ("standard", []), "A58": ("standard", []), "A59": ("standard", []), "A60": ("smalltalk", []), "A61": ("smalltalk", []),
 "A62": ("standard", []), "A63": ("standard", []), "A64": ("explain", []), "A66": ("standard", []), "A67": ("standard", []),
 "B25": ("explain", []), "B26": ("explain", []), "B27": ("explain", []), "B28": ("standard", []), "B29": ("standard", []), "B30": ("standard", []), "B31": ("standard", []),
 "B32": ("explain", ["standard"]), "B33": ("standard", []), "B34": ("explain", []),
 "B35": ("standard", []), "B36": ("standard", []), "B37": ("standard", []), "B38": ("standard", []), "B39": ("standard", []), "B40": ("standard", []), "B41": ("standard", []), "B42": ("standard", []),
 "B43": ("standard", []), "B44": ("standard", []), "B45": ("standard", []), "B46": ("standard", []),
 "B47": ("explain", ["standard"]), "B48": ("explain", []), "B49": ("explain", []), "B50": ("explain", []),
 "B57": ("standard", []), "B58": ("standard", []), "B59": ("standard", []), "B60": ("smalltalk", []), "B61": ("smalltalk", []),
 "B62": ("standard", []), "B63": ("standard", []), "B64": ("explain", []), "B66": ("standard", []), "B70": ("standard", []),
}
NEW = {
 "A": [
  ("explain", [], True,  "explain the sections in a clear manner"),
  ("explain", [], True,  "explain these sections"),
  ("explain", [], True,  "what does each of these sections mean?"),
  ("explain", [], True,  "Explain 115(2) in simple words"),
  ("explain", [], True,  "what is the punishment for these sections"),
  ("explain", [], True,  "are these sections bailable"),
  ("standard", [], False, "explain the sections in a clear manner"),
  ("explain", [], False, "Explain section 309 of the BNS"),
  ("explain", [], False, "what are the ingredients of robbery under section 309?"),
  ("explain", [], True,  "explain the charges in simple language"),
  ("explain", ["standard"], True, "Which of these sections is the most serious?"),
  ("standard", [], True,  "explain the sections charged and tell me if he will get bail"),
  ("research", [], False, "Which Supreme Court judgments deal with default bail?"),
  ("research", [], False, "Any case law on parity as a ground for bail?"),
  ("research", [], False, "What do courts say about delay in filing the chargesheet?"),
  ("research", [], False, "Give me a detailed research note on bail in robbery cases"),
  ("research", [], False, "Cite the leading cases on test identification parades"),
  ("research", [], False, "Is there a High Court decision on photographs shown to the witness before the TIP?"),
  ("research", [], True,  "go deeper on this"),
  ("research", [], False, "What did the Supreme Court hold in Arnesh Kumar?"),
  ("research", [], False, "precedents for bail where the co-accused is absconding"),
  ("research", [], False, "Find judgments on the evidentiary value of CCTV footage"),
 ],
 "B": [
  ("explain", [], True,  "can you explain the sections to me"),
  ("explain", [], True,  "Break down each charged section for me"),
  ("explain", [], False, "what do 309(4) and 115(2) actually say?"),
  ("explain", [], True,  "explain the sections in simple language"),
  ("explain", [], True,  "What is the meaning of common intention in section 3(5)?"),
  ("explain", [], True,  "is each of these offences cognizable?"),
  ("standard", [], False, "explain the sections"),
  ("explain", [], False, "Tell me what section 115 BNS covers"),
  ("explain", [], False, "what's the punishment under section 309(4) BNS"),
  ("explain", [], True,  "explain the provisions in plain language"),
  ("explain", ["standard"], True, "Do these sections allow the police to arrest without a warrant?"),
  ("standard", [], True,  "explain these sections and how strong our bail position is"),
  ("research", [], False, "What has the Supreme Court said about bail in robbery cases?"),
  ("research", [], False, "Show me case law on common intention"),
  ("research", [], False, "judgments on recovery under a disclosure statement"),
  ("research", [], False, "Write a detailed legal research memo on default bail"),
  ("research", [], False, "Which cases say a delayed FSL report cannot defeat the chargesheet?"),
  ("research", [], False, "any precedent on hurt caused during snatching"),
  ("research", [], False, "what was held in Sushila Aggarwal"),
  ("research", [], False, "Is there authority that identification by photograph is weak?"),
  ("research", [], True,  "explain in detail with citations"),
  ("research", [], False, "list landmark judgments on bail"),
 ],
}
out = {"_note": "FROZEN 2026-11-20 before any planner code (owner's go: 'Go ahead with W1 and W2 together'). Written by Claude, not a lawyer. Context: a lawyer's matter holding the synthetic chargesheet of review_results/2026-11-19_matter_files/docs. "
                "expect = the size the planner should choose: file | explain | standard | research | draft | smalltalk; also = other acceptable sizes; pins = the last answer in the conversation listed the charged sections. "
                "Half A is for writing the rules; half B is held out and run ONCE after the rules are fixed; no rule change after that without a new set. "
                "The worst error is a question that needs law or a draft sent to file, explain or smalltalk (an answer without law); the others are reported (money, or a thinner answer with a Go-deeper tap).",
       "A": [], "B": []}
for half in ("A", "B"):
    for x in R[half]:
        if x["expect"] == "law":
            exp, also = LAW[x["id"]]
        else:
            exp, also = x["expect"], []                      # file and draft stay as frozen on 2026-11-20
        out[half].append({"id": x["id"], "q": x["q"], "expect": exp, "also": also, "pins": False, "kind": x.get("kind")})
    for i, (exp, also, pins, q) in enumerate(NEW[half], 1):
        out[half].append({"id": f"{half}N{i:02d}", "q": q, "expect": exp, "also": also, "pins": pins, "kind": "new_" + exp})
json.dump(out, open(os.path.join(HERE, "planner_set.json"), "w"), indent=1, ensure_ascii=False)
from collections import Counter
for half in ("A", "B"):
    print(half, len(out[half]), dict(Counter(x["expect"] for x in out[half])))
