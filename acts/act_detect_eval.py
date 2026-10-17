#!/usr/bin/env python3
"""Measure the second Act-detection pass (Recourse act_detect.py, switch ACT_DETECT) before it is switched on anywhere.  (2026-10-17, owner's "YES. Go ahead." on FOLLOW_UPS 2aj steps 1 and 2.)

Three question sets, all of them written BEFORE this code existed:
  * the 75 Act-shelf gold questions (Recourse `act_shelf/eval_questions.json`; five Acts, fifteen each; Claude's own, 2026-10-16) -- does the right Act come up?
  * 27 ordinary criminal-law questions that concern none of those Acts (below, Claude's own) -- does an Act come up that should not?
  * the project's own question sets (the 30 real questions, the 29 of Stage F, the three trap exams: 161 questions) -- what changes for questions that were written for other purposes?

  python acts/act_detect_eval.py                 the word pass only: free, no model, no network.
  python acts/act_detect_eval.py --ai            also the AI pass, on the questions the word pass leaves empty. REAL MONEY: one Haiku call each, about Rs 0.2 [Likely].
                                                 Needs ANTHROPIC_API_KEY in the environment (the build sandbox has none, so the AI pass has never been run).
  python acts/act_detect_eval.py --ai --limit 10 the first 10 of those, to see what it does before paying for the rest.
Add RECOURSE=/path/to/recourse if the Recourse checkout is not at /home/user/recourse. --json FILE writes every row.

What this can and cannot show. The 75 questions are Claude's, not real users'; the word pass was written after reading the five Acts' own text and the owner's trigger workbook, and a few of its patterns were widened after seeing which of the 75 were missed, so its score here is an optimistic ceiling.
The ordinary questions are a false-alarm check, not a measure of harm: a match only adds a line saying the question "looks like it is about" an Act, and (with ACT_SHELF on) hands that Act's text to the answer model.
Nothing here says an Act applies to anyone's case."""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REC = os.environ.get("RECOURSE", "/home/user/recourse")
sys.path.insert(0, REC)
import act_detect as AD          # noqa: E402
import act_directory as D        # noqa: E402

SHELF = {"pc_act_1988", "pocso_act_2012", "uapa_1967", "pmla_2002", "sc_st_act_1989"}

# Ordinary criminal-law questions that concern none of the Directory's Acts (Claude's own, written 2026-10-17 before the word pass was tuned). The last three DO describe a bribe by a public servant and are
# marked as such: they are the owner's own kind of sentence, and a match on them is right, not a false alarm.
ORDINARY = [
    ("My sister was arrested at night with no woman police officer there. Is that allowed?", None),
    ("My son has been in jail 65 days in a cheating case and no chargesheet has been filed. Can he get bail?", None),
    ("Someone snatched my gold chain on the road. Which section applies and is it bailable?", None),
    ("My neighbour hit me with a stick and I have a head injury. The police are not registering my FIR. What can I do?", None),
    ("A business partner took 8 lakhs from me for a shop and disappeared. Is it cheating or just a civil dispute?", None),
    ("Police entered my house at 2 am without a warrant and took my phone and laptop. Is that legal?", None),
    ("Can the police arrest me for a threat made on a phone call without a warrant?", None),
    ("My brother is accused of stealing from his employer. Employer says he took money from the till. Can the police arrest him?", None),
    ("My landlord took my security deposit and refuses to return it, and then called the police on me when I protested. What are my rights?", None),
    ("A shopkeeper took money from me for a mobile phone and gave a fake bill. What can I do?", None),
    ("My employer took Rs 20,000 from my salary as penalty. Can I complain to the police?", None),
    ("A teacher took money from parents for admission and never gave receipts. Is this a crime?", None),
    ("My friend was arrested for beating a man in a pub fight. How does bail work for hurt cases?", None),
    ("Can an arrested person insist on speaking to a lawyer before the police question him?", None),
    ("A man forged my signature on a property paper. Which offence is that and can I file an FIR?", None),
    ("My brother was arrested yesterday and not yet produced before the magistrate. What do I do?", None),
    ("The police have registered an FIR against my father for rash driving causing a death. Can he get anticipatory bail?", None),
    ("Our neighbour threatens to kill us over a boundary dispute. What can we do?", None),
    ("I want to quash an FIR filed against me out of a family dispute. When does the High Court do that?", None),
    ("A bank manager misused the funds of a customer. Can he be arrested for criminal breach of trust?", None),
    ("My son's friend gave him a lift and the bike had stolen parts. Is he liable for receiving stolen property?", None),
    ("What is the difference between cognizable and non-cognizable offences?", None),
    ("A government school teacher slapped my child in class. Can I file a police complaint?", None),
    ("My boss, a manager in a private company, asked me to pay a commission to get my pending bill cleared.", None),
    ("The police station officer asked me to pay Rs 2000 to register my complaint about the stolen bike.", "pc_act_1988"),
    ("The tehsildar took Rs 10,000 from us to sign our land papers", "pc_act_1988"),
    ("A police constable demanded money to not file a case against me", "pc_act_1988"),
]


def sets():
    out = {}
    q = json.load(open(os.path.join(REC, "act_shelf/eval_questions.json")))["questions"]
    out["gold75"] = [{"id": r["id"], "q": r["q"], "want": r["act_key"], "kind": r["kind"]} for r in q]
    out["ordinary"] = [{"id": f"ORD{i+1:02d}", "q": t, "want": a, "kind": "layman"} for i, (t, a) in enumerate(ORDINARY)]
    root = os.path.dirname(HERE)
    others = []
    def jl(path, key="question"):
        try:
            return [json.loads(l)[key] for l in open(os.path.join(root, path), encoding="utf-8") if l.strip()]
        except Exception as exc:  # noqa: BLE001
            print(f"  (could not read {path}: {exc})")
            return []
    for name, path in (("stageF", "review_results/2026-10-12_fix_test_f/questions.jsonl"), ("trap_criminal", "register_exam/criminal/questions.jsonl"),
                       ("trap_situation", "register_exam/situation/questions.jsonl"), ("trap_original", "register_exam/questions.jsonl")):
        others += [{"id": f"{name}{i+1:02d}", "q": t, "want": "?", "kind": "project"} for i, t in enumerate(jl(path))]
    try:
        real = json.load(open(os.path.join(root, "review_data/ruler/real30_v1.json")))["questions"]
        others += [{"id": f"real{i+1:02d}", "q": (r.get("question") or r.get("q") or ""), "want": "?", "kind": "project"} for i, r in enumerate(real)]
    except Exception as exc:  # noqa: BLE001
        print(f"  (could not read real30: {exc})")
    out["project"] = [r for r in others if r["q"]]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", action="store_true", help="also run the AI pass (real money, needs ANTHROPIC_API_KEY)")
    ap.add_argument("--limit", type=int, default=0, help="with --ai: stop after this many model calls")
    ap.add_argument("--json", dest="out", default="", help="write every row to this file")
    args = ap.parse_args()

    ids = {e["id"] for e in D.load()["acts"] if e.get("detect") is not False}
    entries = [{"id": e["id"], "short": e["short"]} for e in D.load()["acts"] if e.get("detect") is not False]
    if args.ai and not os.environ.get("ANTHROPIC_API_KEY"):
        print("--ai needs ANTHROPIC_API_KEY in the environment. Stopping before spending anything."); return 2
    data, rows, calls, spent = sets(), [], 0, 0.0

    for name, qs in data.items():
        print(f"\n=== {name}: {len(qs)} questions ===")
        for r in qs:
            named = sorted({a["id"] for a in D.detect(r["q"])})
            word = sorted({h["id"] for h in AD.wide(r["q"], ids)} - set(named))
            ai_hits, inr = [], 0.0
            if args.ai and not named and not word and (not args.limit or calls < args.limit):
                hits, inr = AD.ai(r["q"], entries)
                ai_hits, calls, spent = sorted({h["id"] for h in hits}), calls + 1, spent + inr
            rows.append({"set": name, **r, "named": named, "word": word, "ai": ai_hits, "inr": round(inr, 4)})
        sub = [x for x in rows if x["set"] == name]
        if name == "gold75":
            for label, keys in (("Directory only", ("named",)), ("+ word pass", ("named", "word")), ("+ AI pass", ("named", "word", "ai"))):
                if label.endswith("AI pass") and not args.ai:
                    continue
                got = [set().union(*[set(x[k]) for k in keys]) for x in sub]
                ok = sum(x["want"] in (g & SHELF) for x, g in zip(sub, got)); wrong = sum(bool((g & SHELF) - {x["want"]}) for x, g in zip(sub, got))
                lay = sum(x["want"] in (g & SHELF) for x, g in zip(sub, got) if x["kind"] == "layman")
                print(f"  {label:16s} right Act {ok}/{len(sub)} = {ok/len(sub):.0%} (layman {lay}/{sum(1 for x in sub if x['kind']=='layman')}); fired a WRONG one of the five on {wrong}")
            for act in sorted(SHELF):
                s = [x for x in sub if x["want"] == act]
                print(f"    {act:16s} {sum(x['want'] in set(x['named'])|set(x['word'])|set(x['ai']) for x in s)}/{len(s)}")
            miss = [x for x in sub if x["want"] not in set(x["named"]) | set(x["word"]) | set(x["ai"])]
            print(f"  still missed ({len(miss)}): " + ", ".join(x["id"] for x in miss))
        else:
            fired = [x for x in sub if x["word"] or x["ai"]]
            if name == "ordinary":
                good = [x for x in fired if x["want"] and x["want"] in set(x["word"]) | set(x["ai"])]
                bad = [x for x in fired if x not in good]
                print(f"  new matches: {len(fired)} of {len(sub)}; {len(good)} on the three questions that really are about a bribe by a public servant; {len(bad)} others")
                for x in bad:
                    print(f"    [{x['id']}] {sorted(set(x['word'])|set(x['ai']))}: {x['q'][:110]}")
            else:
                print(f"  new matches on {len(fired)} of {len(sub)} (these questions have no answer key: read them)")
                for x in fired:
                    print(f"    [{x['id']}] {sorted(set(x['word'])|set(x['ai']))}: {x['q'][:120]}")
    if args.ai:
        print(f"\nAI pass: {calls} calls, about Rs {spent:.2f} in all ({(spent/calls if calls else 0):.2f} each)")
    by = collections.Counter(a for x in rows for a in x["word"] + x["ai"])
    print("\nmatches by Act: " + ", ".join(f"{k} {v}" for k, v in by.most_common()))
    if args.out:
        json.dump({"run_on": __import__("datetime").date.today().isoformat(), "ai": bool(args.ai), "calls": calls, "inr": round(spent, 4), "rows": rows}, open(args.out, "w"), indent=1)
        print(f"written: {args.out}")
    print("\nCaveats: the 75 questions are Claude's and some word-pass patterns were widened after seeing which were missed, so that score is an optimistic ceiling; a match is a ranking hint, never a legal conclusion.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
