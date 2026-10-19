"""
replay_fix1.py -- replays the owner's four section-17 questions (staging test of 2026-10-19) through the Recourse engine's section handling and prints what each turn hands to the answer model.
Run from a Recourse checkout that has the named-section rule:  python -X utf8 replay_fix1.py <path to the Recourse checkout>
It calls Voyage once per turn (about 25-60 tokens, a fraction of a cent) for the question embedding; it never calls the answer model.
Set SECTION_RULE=off to see the same turns as they were before the fix.
"""
import os
import sys

RECOURSE = sys.argv[1] if len(sys.argv) > 1 else "."
sys.path.insert(0, RECOURSE)
os.chdir(RECOURSE)
os.environ["ACT_SHELF"] = "on"
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
import act_directory as AD       # noqa: E402
import act_shelf as S            # noqa: E402
import chat_assistant as CA      # noqa: E402
import section_rule as R         # noqa: E402,F401
import web_chat as W             # noqa: E402

T = ["Can a disproportionate assets case under PC act be filed without section 17 approval?",
     "I am asking about section 17, NOT section 17 A",
     "Does section 17 require authorisation of a police officer not below the rank of SP to register a case of disproportionate assets?",
     "No section 17 order exists for this case of disproportionate assets"]
fake_rewrite = lambda prompt, current: ('{"follow_up": true, "standalone": "No order from a Superintendent of Police exists for this case of disproportionate assets."}', 0.0)
os.environ["CHAT_MODE"] = "on"
turns = []
print("SECTION_RULE =", os.environ.get("SECTION_RULE", "(unset: on)"))
for i, q in enumerate(T, 1):
    eq, rec = W.question_for_engine(turns, q, call=fake_rewrite if i == 4 else (lambda p, c: ('{"follow_up": true, "standalone": "%s"}' % q.replace('"', ''), 0.0)))
    cur = CA._extract_current_message(eq)
    acts = CA._acts_named(eq)
    res = S.search(eq, acts, current_message=cur)
    per = res["info"]["per_act"].get("pc_act_1988", {})
    expl = CA._explicit_section_matches(cur)
    after = CA._drop_sections_claimed_by_shelf(expl, eq, cur)
    held = S.held_state(res["matches"], acts)
    clause = "## The section the person asked about" in AD.prompt_block(acts, held=held)
    print(f"\nTURN {i}: {q}")
    print(f"  Acts found: {[a['id'] for a in acts]}")
    print(f"  sections handed over: {[(m['section_number'], m['retrieval']) for m in res['matches']]}")
    print(f"  BNS/BNSS section read from the bare number: before the drop {[(e['act'], e['section_number']) for e in expl]}, after {[(e['act'], e['section_number']) for e in after]}")
    print(f"  prompt clause 'The section the person asked about': {'YES' if clause else 'no'}")
    turns.append({"q": q, "answer": {"state": "single_match", "response_text": "x"}})
