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


# ---- the choice of passages: strong words outweigh weak ones, and what the rules flagged is always shown
weak_many = mention("The appellant relied on and the High Court followed and affirmed, approved and reaffirmed Sibbia v. State as explained, distinguished and referred to.", "Sibbia v. State")
strong_one = mention("Thus we overrule the decision in Sibbia v. State.", "Sibbia v. State", confidence="medium")
ordered = R.candidate_passages([weak_many, strong_one], limit=1)
check(len(ordered) == 1 and "overrule" in ordered[0]["text"], "one strong word outweighs a string of weak ones (the first blind run left an explicit overruling out)")
many = [mention(f"Sibbia v. State is mentioned in point {i} where the Court doubts nothing at all.", "Sibbia v. State") for i in range(8)]
shown = R.candidate_passages(many, limit=2, must={6, 7})
check(len(shown) == 2 and all(any(f"point {i} " in p["text"] for i in (6, 7)) for p in shown), "the mentions the rules flagged are shown first")
check(len(R.candidate_passages(many, limit=2, must={3, 4, 5})) == 3, "flagged mentions are all shown even beyond the limit")
check(R.cue_score("we overrule it") == 4 and R.cue_score("it was followed and relied on") == 2 and R.cue_score("nothing here") == 0, "cue scores: 4 for a strong word, 1 for a weak one")

# ---- items for a case, and what the answers say about it
def cm(doc, sentence, name, label=None, conf="high", speaker="court", head=False, title="Later v State", date="2020-01-01"):
    m = mention(sentence, name, confidence=conf, head=head)
    m.update(doc_key=doc, title=title, date=date, year=int(date[:4]), label=label or "NEUTRAL", speaker=speaker)
    return m


ms = [cm("d1", "The Court overrules Sibbia v. State here.", "Sibbia v. State", label="OVERRULES"),
      cm("d2", "Learned counsel cited Sibbia v. State for bail.", "Sibbia v. State"),
      cm("d3", "In Sibbia v. State this Court held bail is wide, but that view is wrongly decided.", "Sibbia v. State", conf="medium"),
      cm("d4", "Sibbia v. State is flagged by the rules but only by a low-confidence match.", "Sibbia v. State", label="DISAGREES", conf="low")]
its = R.items_for_target("c100", "Sibbia v State (1980)", ms)
check([i["id"] for i in its] == ["c100:d1", "c100:d3"], "an item for each judgment where the rules read it as adverse or a passage has a strong word; none for a bare citation or a low-confidence match")
check(its[0]["_rule"] == ["OVERRULES"] and its[1]["_rule"] == [] and all(i["hash"] and len(i["hash"]) == 12 for i in its), "items carry the rules' labels (for the comparison) and a hash of the passages")
check(all("_rule" not in R.public(i) and "hash" not in R.public(i) for i in its), "the reader's view of an item has no rule label")
rec = lambda it, t, q: {"id": it["id"], "treatment": t, "quote": q, "note": "", "hash": it["hash"], "reader": "r", "date": "2026-10-06"}
summ = R.summarise(its, {"c100:d1": rec(its[0], "OVERRULES", "The Court overrules Sibbia"), "c100:d3": rec(its[1], "CITED", "")})
check(summ["items"] == 2 and summ["read"] == 2 and summ["pending"] == 0 and summ["confirmed"] == 1 and summ["reader_only"] == [] and summ["dismissed"] == [], "the reader confirms the flagged judgment and finds nothing in the other")
summ2 = R.summarise(its, {"c100:d1": rec(its[0], "CITED", ""), "c100:d3": rec(its[1], "DISAGREES", "that view is wrongly decided")})
check(len(summ2["dismissed"]) == 1 and summ2["dismissed"][0]["id"] == "c100:d1" and len(summ2["reader_only"]) == 1 and summ2["reader_only"][0]["id"] == "c100:d3", "a dismissed flag and a reader-only finding are told apart")
stale = dict(rec(its[0], "OVERRULES", "The Court overrules Sibbia"), hash="000000000000")
check(R.summarise(its, {"c100:d1": stale})["pending"] == 2, "a verdict whose passages have changed since is not used")
check(R.summarise(its, {"c100:d3": rec(its[1], "OVERRULES", "words not in the passage")})["adverse"] == [], "a quote not in the passages is never counted")
check(R.summarise([], {}) is None, "nothing to read, no summary")

check(R.check_verdict(item, {"id": "r1", "treatment": "OVERRULES", "quote": "decision is overruled."})["quote_verified"] and R.check_verdict(item, {"id": "r1", "treatment": "OVERRULES", "quote": "In \u00abSibbia v. State\u00bb the Court was wrong and the decision is overruled."})["quote_verified"], "a quote verifies whether or not the reader copied the case markers")

print()
print("ALL PASSED" if not FAILED else f"{len(FAILED)} FAILED")
sys.exit(1 if FAILED else 0)
