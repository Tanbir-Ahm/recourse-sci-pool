"""Tests for authority_graph.py (who names whom) and authority_search.py (the table the search service loads and the ranking steps), on small invented judgments. No network, no spend.
Run: python test_authority_graph.py"""
import gzip
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authority_graph as AG
import authority_search as AS

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


# ---- the words of a party
check("honorifics, '& Ors', brackets, '@ alias' and 'S/O' are dropped from a party name",
      AG.party_tokens("Shri D.K. Basu & Ors. (Dead) by LRs") == ["d", "k", "basu"] and AG.party_tokens("Herman Tirky @ Herman Orang") == ["herman", "tirky"]
      and AG.party_tokens("Bachan Singh S/O Saudagar Singh") == ["bachan", "singh"] and AG.party_tokens("The State of Maharashtra") == ["state", "of", "maharashtra"])

# ---- 'X v. Y' mentions
TXT = "In Sharad Birdhichand Sarda v. State of Maharashtra (1984) 4 SCC 116, this Court held; see also Hanumant v. The State of Madhya Pradesh AIR 1952 SC 343 and Shri D.K. Basu vs. State of West Bengal (1997) 1 SCC 416."
ms = AG.mentions(TXT)
check("three mentions are found, each with the first party's words, the first three words of the second party and the year beside it",
      len(ms) == 3 and ms[0][0][-3:] == ["sharad", "birdhichand", "sarda"] and ms[0][1] == "stateofmaharashtra" and ms[0][2] == 1984 and ms[1][0][-1] == "hanumant" and ms[1][2] == 1952 and ms[2][0][-3:] == ["d", "k", "basu"] and ms[2][2] == 1997, ms)
check("a sentence without 'v.' has no mention, and a lower-case word before 'v.' ends the first party", AG.mentions("The Court held that the appeal fails.") == [] and AG.mentions("held that Ram Kishan v. State of Bihar") and AG.mentions("held that Ram Kishan v. State of Bihar")[0][0] == ["ram", "kishan"])

# ---- the names of the judgments of an index
NAMES = {
    1: {"name": "Sharad Birdhi Chand Sarda v. State of Maharashtra", "year": 1984, "court": "Supreme Court of India"},
    10: {"name": "Tofan Singh v. State of Tamil Nadu", "year": 2020, "court": "Supreme Court of India"},
    9: {"name": "Tofan Singh v. State of Tamil Nadu", "year": 2013, "court": "Supreme Court of India"},
    20: {"name": "Ram Singh v. State of Punjab", "year": 1950, "court": "Supreme Court of India"},
    21: {"name": "Ram Singh v. State of Punjab", "year": 2013, "court": "Supreme Court of India"},
    30: {"name": "State of Rajasthan v. Mohan Lal", "year": 2001, "court": "Supreme Court of India"},
    40: {"name": "State of Gujarat v. State of Maharashtra", "year": 2002, "court": "Supreme Court of India"},
    50: {"name": "Gian Singh v. State of Punjab & Anr", "year": 2012, "court": "Supreme Court of India"},
    51: {"name": "Gian Singh v. State of Punjab & Another", "year": 2012, "court": "Supreme Court of India"},
    52: {"name": "Gian Singh v. State of Haryana", "year": 2012, "court": "Supreme Court of India"},
}
check("a judgment is known by its first party and the first three words of its second party; several petitioners also by the first one",
      ("sharadbirdhichandsarda", "stateofmaharashtra") in AG.doc_keys(NAMES[1]["name"]) and ("bachansingh", "stateofpunjab") in AG.doc_keys("Bachan Singh, Sohan Singh & Ors v. State of Punjab"))
check("in running text a case is known by its distinctive party: the second one when the first is a State; none when both are generic",
      AG.doc_signature_keys(NAMES[1]["name"]) and AG.doc_signature_keys(NAMES[1]["name"])[0][0] == "sharadbirdhichandsarda" and AG.doc_signature_keys("State of Rajasthan v. Mohan Lal")[0][0] == "mohanlal"
      and AG.doc_signature_keys("State of Gujarat v. State of Maharashtra") == [] and AG.doc_signature_keys("Short v. State") == [])

R = AG.Resolver(NAMES)
t = lambda s: AG.party_tokens(s)
check("a mention matches on the first party (leading words of the sentence trimmed) and the second party", R.resolve(t("In the case of Sharad Birdhichand Sarda"), "stateofmaharashtra") == {1})
check("a different second party does not match; a distinctive first party alone does (it belongs to one case)", R.resolve(t("Sharad Birdhichand Sarda"), "unionofindia") == {1} and R.resolve(t("Mohan Lal"), "stateofpunjab") == set())
check("a generic first party ('State of Rajasthan') is never matched on its own", R.resolve(t("State of Rajasthan"), "someoneelse") == set())
check("one pair of names, cases decades apart: a year picks the case; without a year the latest case not later than the citing judgment is taken",
      R.resolve(t("Ram Singh"), "stateofpunjab", 2013, 2020) == {21} and R.resolve(t("Ram Singh"), "stateofpunjab", 1950, 2020) == {20} and R.resolve(t("Ram Singh"), "stateofpunjab", None, 2015) == {21}
      and R.resolve(t("Ram Singh"), "stateofpunjab", None, 1960) == {20} and R.resolve(t("Tofan Singh"), "stateoftamil", None, 2022) == {10} and R.resolve(t("Tofan Singh"), "stateoftamil", None, 2015) == {9})

# ---- the same case held twice is one case
cid = AG.clusters(NAMES)
check("the same case held twice (same name, same second party, within two years) is one cluster; another second party is another case; cases decades apart stay apart",
      cid[50] == cid[51] and cid[52] != cid[50] and cid[20] != cid[21] and cid[9] != cid[10], cid)

# ---- the whole scan on invented judgments
MET = []
def add(doc, text):
    MET.append({"doc": doc, "text": text})
for k, doc in enumerate((101, 102, 103)):                                  # three judgments name Tofan Singh in full: it may then be recognised by its bare name
    add(doc, f"The Court relied on Tofan Singh v. State of Tamil Nadu (2021) 4 SCC 1 in judgment {k}.")
add(104, "In Tofan Singh the Court held that the statement is not a confession.")                          # bare, in the way a case is cited
add(105, "Tofan Singh was arrested at the border with the contraband.")                                    # a party's name in the facts: not a mention
add(106, "The bench of Tofan Singh, J. dissented on this point.")                                          # a judge of that name: not a mention
add(107, "As held in Sharad Birdhichand Sarda v. State of Maharashtra, AIR 1984 SC 1622, the chain must be complete.")
add(108, "See Sharad Birdhi Chand Sarda vs. State of Maharashtra (1984) 4 SCC 116.")
add(109, "The decision in Sharad Birdhichand Sarda v. State of Maharashtra applies.")
add(1, "Judgment 1 itself: Sharad Birdhi Chand Sarda v. State of Maharashtra says nothing about itself.")                       # never counted for itself
add(200, "In Tofan Singh (supra) an earlier court decided otherwise.")                                      # 200 is dated 2010, before Tofan Singh (2020): a case cannot be cited by an earlier judgment
NAMES.update({101: {"name": "A101 v. State", "year": 2021}, 102: {"name": "A102 v. State", "year": 2021}, 103: {"name": "A103 v. State", "year": 2021}, 104: {"name": "A104 v. State", "year": 2022}, 105: {"name": "A105 v. State", "year": 2022},
              106: {"name": "A106 v. State", "year": 2022}, 107: {"name": "A107 v. State", "year": 2000}, 108: {"name": "A108 v. State", "year": 2001}, 109: {"name": "A109 v. State", "year": 2002}, 200: {"name": "Z200 v. State", "year": 2010}})
cites, cl, stats = AG.scan(MET, NAMES)
tof = cl[10]
check("a full mention counts for the right case (Tofan Singh 2020, not the 2013 reference order)", all(tof in cites.get(d, ()) for d in (101, 102, 103)) and cl[9] not in cites.get(101, ()))
check("after three full mentions the bare name counts too ('in Tofan Singh the Court held')", tof in cites.get(104, ()))
check("a party's name in the facts is not a mention", tof not in cites.get(105, ()))
check("a judge of that name ('Tofan Singh, J.') is not a mention", tof not in cites.get(106, ()))
check("a judgment dated before the case cannot name it", tof not in cites.get(200, ()))
check("three spellings of Sarda are the same case; a judgment never counts itself", all(cl[1] in cites.get(d, ()) for d in (107, 108, 109)) and cl[1] not in cites.get(1, ()))

# ---- the table and what the service does with it
tab = AG.build_table(cites, cl, NAMES, "abc1234", stats)
check("the table carries counts per case, the clusters that differ and who names whom", tab["schema"] == "authority-table-2" and tab["cited_by"][str(cl[1])] == 3 and tab["cited_by"][str(tof)] == 4 and "51" in tab["cluster"] and tab["cites"]["104"] == [tof])
path = os.path.join(tempfile.mkdtemp(), "t.json.gz")
with gzip.open(path, "wt", encoding="utf-8") as fh:
    json.dump(tab, fh)
T = AS.AuthorityTable.load(path, "abc1234")
check("the service loads it and reads the counts, clusters and pointers back", T.named_by(1) == 3 and T.named_by(10) == 4 and T.named_by(50) == 0 and T.cluster_of(51) == T.cluster_of(50) and 104 in T.cites and T.docs_of(T.cluster_of(50)))
try:
    AS.AuthorityTable.load(path, "ffffffff")
    ok = False
except ValueError as e:
    ok = "rebuild" in str(e)
check("a table built for another index commit is refused", ok)
try:
    AS.AuthorityTable({"schema": "authority-table-1", "cited_by": {}, "cites": {}})
    ok = False
except ValueError:
    ok = True
check("a table of another schema is refused", ok)

# ---- the ranking steps
PRM = dict(AS.DEFAULTS)
pool = list(range(1000, 1010))
tab2 = {"schema": "authority-table-2", "index_commit": "x", "cited_by": {"1": 400, "2": 3, "3": 0}, "cluster": {"4": 1}, "cites": {str(d): [1] for d in pool[:5]} | {str(pool[5]): [2], str(pool[6]): [2], str(pool[7]): [2]}}
T2 = AS.AuthorityTable(tab2)
pl = AS.plan(T2, pool, PRM)
check("the court's own pointers: a judgment named by 5 of 10 retrieved judgments is chosen; one named by 3 of 10 too (at least 3 and 8 percent); the most named first", [c for c, n in pl["chosen"]] == [1, 2] and pl["chosen"][0][1] == 5 and pl["threshold"] == 3, pl)
pl2 = AS.plan(T2, pool[:2] + pool[5:6], PRM)
check("a judgment named by only one or two of them is not chosen", pl2["chosen"] == [])
check("the boost is 1 for a judgment nobody names, grows with the share of the retrieved judgments that name it and with the size of its authority, and saturates",
      AS.boost(T2, 3, 0, 10, PRM) == 1.0 and AS.boost(T2, 1, 5, 10, PRM) > AS.boost(T2, 1, 3, 10, PRM) > AS.boost(T2, 2, 3, 10, PRM) > 1.0 and abs(AS.boost(T2, 1, 5, 10, PRM) - (1 + 0.1 + 0.6)) < 1e-9 and AS.boost(T2, 1, 10, 10, PRM) == AS.boost(T2, 1, 5, 10, PRM))
sims = [0.1, 0.9, 0.5, 0.8, 0.7, 0.2]
rows = {1: [0, 1, 2], 4: [3, 4], 2: [5]}
ex = AS.extra_rows(T2, [(1, 5)], rows, sims, [1], dict(PRM, passages=3))
check("the passages added are the best three by meaning of the whole cluster (a duplicate of the case counts), leaving out any that is already a candidate", ex == [3, 4], ex)
check("the facts shown with a result", AS.annotate(T2, 1, 5, 10) == {"named_by_collection": 400, "named_by_retrieved": 5, "retrieved": 10, "pointer": False} and AS.annotate(T2, 1, 5, 10, True)["pointer"] is True)

# ---- the settings come from the environment, clamped
for k in list(os.environ):
    if k.startswith("SCI_AUTH"):
        os.environ.pop(k)
check("default settings", AS.params_from_env() == dict(AS.DEFAULTS, **{}) and not AS.enabled())
os.environ.update({"SCI_AUTH_PRIOR": "5", "SCI_AUTH_MAX": "banana", "SCI_AUTH_MIN_FRAC": '"0.2"', "SCI_AUTHORITY": ' "On" '})
p = AS.params_from_env()
check("settings are clamped, a non-number falls back to the default, quotes are harmless, and ' \"On\" ' switches the step on", p["prior"] == 1.0 and p["max_clusters"] == AS.DEFAULTS["max_clusters"] and p["min_frac"] == 0.2 and AS.enabled())
os.environ.pop("SCI_AUTHORITY")
os.environ["SCI_AUTH_PER_DOC"] = "99"
check("the per-judgment limit is clamped (0 means no limit)", AS.params_from_env()["per_doc"] == 10)
os.environ["SCI_AUTH_PER_DOC"] = "0"
check("a limit of 0 is kept (no limit), and the default is 1", AS.params_from_env()["per_doc"] == 0 and AS.DEFAULTS["per_doc"] == 1)
os.environ.pop("SCI_AUTH_PER_DOC")

print("\nALL PASSED" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
