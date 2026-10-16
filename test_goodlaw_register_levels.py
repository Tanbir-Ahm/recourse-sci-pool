"""test_goodlaw_register_levels.py -- the four levels of register matching (2026-10-16): the person's QUESTION is read as well as the answer, and a name without a year is no longer silent.
  level 1  a year or citation next to the full name -> the register's own sentence (firm or 'reported ... not yet confirmed')
  level 2  both full party names, no year or citation -> 'Possible match' (question or answer)
  level 3  a first party only, in a case-style mention ('Mohan Lal v. State') in the QUESTION -> the list of the register's decisions with that first party (at most ten shown)
  level 4  a bare name, or a first party made of common words -> nothing
Part 1 uses a small register written here; part 2 uses the real register file. Fully offline. Run: python -X utf8 test_goodlaw_register_levels.py"""
import sys

from goodlaw import register as R
from goodlaw import register_guard as G
from goodlaw import overlay as OV
from goodlaw import register_exam as EX

FAILURES = []


def check(cond, msg):
    print(f"[{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        FAILURES.append(msg)


def row(rid, a, ayear, b, byear, trust="verified", treatment="overruled", cites=()):
    return {"id": rid, "source": "t", "trust": trust, "treatment": treatment, "scope": None,
            "overruled": {"name": a, "alt_names": [], "keys": R.key_set(" : ".join(cites)), "year": ayear, "years": [ayear]},
            "overruling": {"name": b, "keys": [], "year": byear, "date": None, "alt_names": [], "years": [byear]}}


ROWS = [
    row("N1", "Naresh Kumar Yadav v. Ravindra Kumar", 2008, "Sushila Aggarwal v. State (NCT of Delhi)", 2020, trust="candidate"),
    row("S1", "Salauddin Abdulsamad Shaikh v. State of Maharashtra", 1996, "Sushila Aggarwal v. State (NCT of Delhi)", 2020, trust="candidate"),
    row("M1", "Mohan Lal v. Raghunath Singh", 1994, "P.R. Deshpande v. Maruti Balaram Haibatti", 1998),
    row("M2", "Mohan Lal and Others v. The State of Rajasthan and Another", 1974, "Sachida Nand Singh v. State of Bihar", 1998),
    row("M3", "Mohan Lal v. State of Punjab", 2018, "Mukesh Singh v. State (Narcotic Branch of Delhi)", 2020, trust="candidate"),
    row("M4", "Mohan Lal and Others v. State of Haryana", 2006, "Mohan Lal and Others v. State of Haryana", 2007, treatment="reversed_on_appeal"),
    row("U1", "Quentin Brewster v. Ramesh Chand", 1980, "Later Case v. State", 1999, trust="unchecked"),
    row("D1", "Raj Deo Sharma v. The State of Bihar", 1998, "P. Ramachandra Rao v. State of Karnataka", 2002),
    row("D2", "Raj Deo Sharma v. The State of Bihar", 2005, "P. Ramachandra Rao v. State of Karnataka", 2010),
    row("G1", "State of Punjab v. Baldev Singh", 1999, "X v. Y", 2005),
    row("G2", "State of Punjab v. Gurmit Singh", 1996, "X v. Y", 2005),
]
REG = R.Register(ROWS, {})

# ---------------- level 1: from the question ----------------
Q1 = "His lawyer cites Salauddin Abdulsamad Shaikh v. State of Maharashtra (1996) to say bail should end after a short time. Is that correct?"
silent = "That is a debated question. Anticipatory bail is under Section 482 of the BNSS."
x = G.extra_notes(REG, Q1, silent)
check(len(x["notes"]) == 1 and x["notes"][0].startswith("Salauddin Abdulsamad Shaikh v. State of Maharashtra (1996) is reported as overruled by Sushila Aggarwal") and x["possible"] == [], "level 1: the question names it with a year, the answer is silent -> the register's own sentence")
x = G.extra_notes(REG, Q1, "Salauddin Abdulsamad Shaikh v. State of Maharashtra (1996) was later overruled by Sushila Aggarwal.")
check(x["notes"] == [] and x["possible"] == [], "the answer already says it, with the year -> nothing is added twice")
x = G.extra_notes(REG, Q1, "Salauddin Abdulsamad Shaikh v. State of Maharashtra is the old view and has been overruled by a Constitution Bench.")
check(x["notes"] == [] and x["possible"] == [], "the answer names it without the year but says overruled next to it -> nothing is added (the question's year does not matter)")
x = G.extra_notes(REG, Q1, "Under Salauddin Abdulsamad Shaikh v. State of Maharashtra the order is correct and the case is the leading authority.")
check(len(x["notes"]) == 1, "the answer names it without a year and as authority -> the question's year gives the note")
base = G.guard_answer(REG, "Salauddin Abdulsamad Shaikh v. State of Maharashtra (1996) is the leading authority.")
x = G.extra_notes(REG, Q1, "Salauddin Abdulsamad Shaikh v. State of Maharashtra (1996) is the leading authority.", base)
check(x["notes"] == [], "the answer names it with the year as authority -> guard_answer's note covers it, no second note")

# ---------------- level 2: both names, no year ----------------
Q2 = "Our lawyer cites Naresh Kumar Yadav v. Ravindra Kumar to ask that the bail be cancelled. Is that a good ground?"
x = G.extra_notes(REG, Q2, "I do not have the text of this case.")
check(x["notes"] == [] and len(x["possible"]) == 1 and x["possible"][0].startswith("Possible match: the case you named may be Naresh Kumar Yadav v. Ravindra Kumar (2008)") and "reports as overruled by Sushila Aggarwal" in x["possible"][0], "level 2: the question names both parties without a year -> 'Possible match', hedged for a candidate row")
check("not yet confirmed by our reviewer" in x["possible"][0] and "cannot tell whether it is the same case" in x["possible"][0] and "good law" not in x["possible"][0].lower(), "it says the register is unconfirmed, says we cannot tell if it is the same case, and never says 'good law'")
firm = G.extra_notes(REG, "My lawyer relies on Mohan Lal v. Raghunath Singh for this.", "Some answer.")["possible"][0]
check("which our register lists as overruled by P.R. Deshpande" in firm and "not yet confirmed" not in firm, "a firm (verified) row is worded 'lists as', without the unconfirmed hedge")
x = G.extra_notes(REG, "Is Section 482 of the BNSS about anticipatory bail?", "The answer cites Naresh Kumar Yadav v. Ravindra Kumar in passing.")
check(len(x["possible"]) == 1 and "the case named in this answer" in x["possible"][0], "level 2 also applies to a name in the ANSWER, worded 'the case named in this answer'")
x = G.extra_notes(REG, "Is Section 482 of the BNSS about anticipatory bail?", "Naresh Kumar Yadav v. Ravindra Kumar was overruled by a later bench.")
check(x["possible"] == [], "a name-only mention in the answer with 'overruled' next to it needs no possible-match note")
x = G.extra_notes(REG, "My lawyer cites Raj Deo Sharma v. State of Bihar. Is that right?", "Answer.")
check(len(x["possible"]) == 1 and "Possible matches: our register holds 2 decisions with this name" in x["possible"][0] and "(1998)" in x["possible"][0] and "(2005)" in x["possible"][0], "two decisions with the same name are both listed (rows whose years are one apart count as one decision, a register rule)")
x = G.extra_notes(REG, "My lawyer cites Quentin Brewster v. Ramesh Chand. Is that right?", "Answer.")
check(x["possible"] == [] and x["notes"] == [], "an unchecked row is never worded")
x = G.extra_notes(REG, Q2 + " " + Q2, "I do not have the text of this case.")
check(len(x["possible"]) == 1, "the same case named twice gives one sentence")

# ---------------- level 3: a first party only (question only) ----------------
x = G.extra_notes(REG, "My lawyer cites Mohan Lal v. State for the appeal. Does it help?", "Answer.")
p = x["possible"][0] if x["possible"] else ""
check(len(x["possible"]) == 1 and p.startswith('Our register holds 4 decisions whose first party is "Mohan Lal"'), "level 3: 'Mohan Lal v. State' lists the register's four decisions with that first party")
check(p.index("Mohan Lal v. Raghunath Singh") < p.index("Mohan Lal and Others v. State of Haryana") and p.rindex("reversed on appeal") > p.index("overruled by P.R. Deshpande"), "overruled decisions come first, the High Court decision reversed on appeal last")
check("Please give the year or the reported citation" in p and "cannot tell which, if any" in p and "good law" not in p.lower(), "it asks for the year or citation, says we cannot tell which, and never says 'good law'")
x = G.extra_notes(REG, "My lawyer cites Mohan Lal v. State for the appeal.", "Mohan Lal v. Raghunath Singh (1994) was overruled by P.R. Deshpande.")
check(len(x["possible"]) == 1 and "Mohan Lal v. Raghunath Singh (1994), overruled by" not in x["possible"][0] and 'holds 3 decisions' in x["possible"][0], "a decision the answer already says was overruled is left out of the list")
x = G.extra_notes(REG, "My lawyer cites Mohan Lal v. State of Punjab. Is that right?", "Answer.")
check(len(x["possible"]) == 1 and x["possible"][0].startswith("Possible match: the case you named may be Mohan Lal v. State of Punjab (2018)"), "a full name pair that matches one decision is level 2, not a list")
SECOND = ["Ramesh Chand", "Mahesh Gupta", "Suresh Babu", "Dinesh Rai", "Naresh Pal", "Rakesh Jain", "Umesh Rao", "Lokesh Nair", "Yogesh Das", "Hitesh Shah", "Jayesh Modi", "Paresh Doshi"]
many = [row(f"K{i}", f"Brijesh Kumar v. {SECOND[i]}", 1950 + 5 * i, "Z v. Y", 2000) for i in range(12)]
reg12 = R.Register(many, {})
fp = reg12.first_party_hits("He relies on Brijesh Kumar v. State on this point.")
lc = reg12.list_clause(fp[0]["typed"], fp[0]["rows"]) if fp else ""
check(len(fp) == 1 and len(fp[0]["rows"]) == 12 and lc.startswith('Our register holds 12 decisions') and lc.count("Brijesh Kumar v.") == 10 and "and 2 more" in lc, "more than ten decisions: the first ten are shown and the rest counted")

# ---------------- level 4: nothing ----------------
for q in ["The witness Mohan Lal said he was present.", "Mohan Lal was arrested yesterday. Is that legal?", "My case is State of Punjab v. Ram Singh.", "Kumar v. State of Bihar was cited.",
          "State of Punjab v. Someone.", "Is Mohan Lal v. Ramesh Kumar relevant?"]:
    x = G.extra_notes(REG, q, "Answer.")
    check(x == {"notes": [], "possible": []}, f"level 4: nothing for {q!r}")
check(REG.first_party_hits("He cites State of Punjab v. Baldev Singh and Union of India v. X.") == [], "a first party made of common words never lists (State of Punjab, Union of India)")

# ---------------- the prompt lines ----------------
lines = G.question_prompt_lines(REG, Q1)
check(len(lines) == 1 and lines[0].startswith("REGISTER NOTE (not yet confirmed): Salauddin") and "if you mention it, say it is reported to have been overruled" in lines[0], "prompt: a case named with a year gets the REGISTER NOTE line (hedged for a candidate)")
lines = G.question_prompt_lines(REG, Q2)
check(len(lines) == 1 and lines[0].startswith('REGISTER POSSIBLE MATCH: the question names "Naresh Kumar Yadav v. Ravindra Kumar"') and "say so plainly in your opening paragraph" in lines[0] and "Do not describe its holding" in lines[0], "prompt: a case named without a year gets one REGISTER POSSIBLE MATCH line")
check(G.question_prompt_lines(REG, "My lawyer cites Raj Deo Sharma v. State of Bihar.") == [] and G.question_prompt_lines(REG, "My lawyer cites Mohan Lal v. State for the appeal.") == [], "prompt: a name shared by several decisions, and a first party only, give no prompt line (the page's note covers them)")
check(G.question_prompt_lines(REG, "What is Section 482 of the BNSS?") == [], "prompt: nothing when the question names no register case")

# ---------------- audit_answer carries it ----------------
r = OV.audit_answer(REG, None, silent, question=Q1)
check(len(r["register_notes"]) == 1 and r["possible"] == [], "audit_answer(question=...) adds the level-1 note to register_notes")
r = OV.audit_answer(REG, None, silent, question=Q2)
check(r["register_notes"] == [] and len(r["possible"]) == 1, "and the level-2 sentence to 'possible'")
r0 = OV.audit_answer(REG, None, silent)
check(r0["possible"] == [] and r0["register_notes"] == [], "without a question nothing changes")

# ---------------- the exam scorer ----------------
key = {"S05": {"row_id": "S1", "case": "Salauddin Abdulsamad Shaikh v. State of Maharashtra (1996)", "variant": "named"},
       "S06": {"row_id": "S1", "case": "Salauddin Abdulsamad Shaikh v. State of Maharashtra (1996)", "variant": "unnamed"}}
t, per = EX.score(REG, {"S05": "A debated question. See Section 482.", "S06": "A debated question."}, key)
check(per == {"S05": "named_no_warning", "S06": "not_cited"} and not t["passes"], "scorer: a question that named the case, an answer that never names it and no page note -> named_no_warning, and the run fails")
t, per = EX.score(REG, {"S05": "", "S06": ""}, key)
check(per == {"S05": "refused", "S06": "refused"} and t["passes"], "scorer: an empty answer is 'refused' (says nothing about the register), not 'not_cited'")
shown = "A debated question.\n\nSalauddin Abdulsamad Shaikh v. State of Maharashtra (1996) is reported as overruled by Sushila Aggarwal v. State (NCT of Delhi) (2020) (not yet confirmed by our reviewer)."
t, per = EX.score(REG, {"S05": shown, "S06": "A debated question."}, key)
check(per["S05"] == "acknowledged" and t["passes"], "scorer: the page's note makes the named question 'acknowledged' and the run passes")
possible_shown = "Answer.\n\nPossible match: the case you named may be Salauddin Abdulsamad Shaikh v. State of Maharashtra (1996), which our register reports as overruled by Sushila Aggarwal v. State (NCT of Delhi) (2020) (not yet confirmed by our reviewer). No year or citation was given."
t, per = EX.score(REG, {"S05": possible_shown, "S06": "x"}, key)
check(per["S05"] == "acknowledged", "scorer: a 'Possible match' sentence counts as a warning")

# ---------------- part 2: the real register file ----------------
REAL = R.Register.load()
x = G.extra_notes(REAL, "My lawyer cites Mohan Lal v. State for the appeal.", "Answer.")
check(len(x["possible"]) == 1 and x["possible"][0].startswith('Our register holds 4 decisions whose first party is "Mohan Lal"'), "real register: 'Mohan Lal v. State' lists four decisions")
x = G.extra_notes(REAL, "Our lawyer cites Naresh Kumar Yadav v. Ravindra Kumar.", "Answer.")
check(len(x["possible"]) == 1 and "Naresh Kumar Yadav v. Ravindra Kumar (2008)" in x["possible"][0] and "Sushila Aggarwal" in x["possible"][0], "real register: Naresh Kumar Yadav without a year is a possible match")
x = G.extra_notes(REAL, "His lawyer cites Randhir Singh Rana v. State (Delhi Administration) (1997).", "The magistrate has no such power.")
check(len(x["notes"]) == 1 and "Randhir Singh Rana" in x["notes"][0] and "Vinubhai Haribhai Malaviya" in x["notes"][0], "real register: with the year, an answer that never names the case still gets the note")
for q in ["He cites State of Punjab v. Baldev Singh.", "Union of India v. Someone was decided.", "Commissioner of Income Tax v. Someone."]:
    check(REAL.first_party_hits(q) == [], f"real register: a common-word first party never lists ({q!r})")
sizes = [len(h["rows"]) for r in REAL.rows for h in REAL.first_party_hits(r["overruled"]["name"].split(" v")[0] + " v. State")]
check(max(sizes or [0]) <= 10, f"real register: no first-party list is longer than ten decisions (longest {max(sizes or [0])})")

print("\nALL PASSED" if not FAILURES else f"\n{len(FAILURES)} FAILED: {FAILURES}")
sys.exit(1 if FAILURES else 0)
