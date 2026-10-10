"""EXPLORATORY, after the verdict (not part of the pre-registered rule; no network, no spend): the extra arm X (rerank-2.5) judged by the same three conditions, and the weights question
(places with and without the passage-type weights). Reads results/results.json, writes results/extra_after_verdict.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reranker_test as T       # noqa: E402

d = json.load(open("results/results.json"))
qs, w, u = d["questions"], d["places_weighted"], d["places_unweighted"]
out = {"X_rerank-2.5_against_the_same_conditions_(first_run_only,_not_confirmed,_not_in_the_rule)": T.judge(w["X"], w["C1"], w["C2"], qs),
       "N1_rerank-3_against_the_same_conditions": T.judge(w["N1"], w["C1"], w["C2"], qs),
       "N2_rerank-3-lite_second_run_identical_to_first": all(w["N2"][q] == w["N2b"][q] for q in qs),
       "controls_identical_in_every_key_place": all(w["C1"][q] == w["C2"][q] for q in qs),
       "unweighted_conditions": {a: T.judge(u[a], u["C1"], u["C2"], qs) for a in ("N1", "N2", "X")},
       "R09_unweighted_place": {a: u[a]["R09"] for a in ("C1", "N1", "N2", "X")}, "R09_weighted_place": {a: w[a]["R09"] for a in ("C1", "N1", "N2", "X")}}
json.dump(out, open("results/extra_after_verdict.json", "w"), indent=1)
print(json.dumps(out, indent=1))
