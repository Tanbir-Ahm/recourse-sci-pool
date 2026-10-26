import sys, json, os
sys.path.insert(0, "/home/user/recourse")
os.chdir("/home/user/recourse")
import chat_assistant as ca
import web_chat

own = "is bail possible in this case?"
rewrites = [
 "Is bail possible for a person arrested by the army under the Armed Forces Special Powers Act, where the trial is delayed?",
 "Can a person arrested under a special law in a disturbed area be granted bail when the trial has been delayed for years?",
 "Is bail possible for a person who was arrested by armed forces personnel and kept in custody for a long time without trial?",
]
def show(tag, r):
    print(tag, r.get("state"))
    print("   statutes :", [(m.get("act"), m.get("section_number"), round(m.get("score", 0), 3)) for m in (r.get("matches") or [])])
    print("   judgments:", [(m.get("case_name"), m.get("paragraph_number"), round(m.get("score", 0), 3)) for m in (r.get("judgment_matches") or [])])

from semantic_retrieval import find_relevant_sections
for rw in rewrites:
    cur = own + "\n" + web_chat.REWRITE_LEAD + rw + ")"
    print("\n=== rewrite:", rw)
    before = find_relevant_sections(cur)
    show("BEFORE (combined only):", before)
    after = ca._find_relevant_sections_for_turn(cur, cur)
    show("AFTER  (merged):", after)
print("\n=== own words alone")
show("OWN:", find_relevant_sections(own))
