import os, sys, json
sys.path.insert(0, "/home/user/recourse")
for k, v in {"ACT_SHELF":"on","ACT_DETECT":"wide","SECTION_XREF":"on","STATUTE_ALIASES":"on","STATUTE_WIDEN":"on","SCOPE_GATE":"open","SCI_SEARCH_MODE":"off","CASE_FILE":"on","CHAT_MODE":"on"}.items():
    os.environ[k] = v
import chat_assistant as CA, web_chat as W, case_file as C

CONVS = [
 ("molestation", "My client was arrested on the charges that he was recording a sexual molestation case. The prime accused was arrested on the charges of rape. My client was arrested as the said video was phone on his phone and was widely shared, and he was apparently present at the crime spot",
  "what are the other sections my client can be charged with? and how can i counter them? give detailed explanations", {("BNS","77"), ("ITACT","66E")}),
 ("job cheating", "My father was arrested for cheating a person of Rs 5 lakh by promising a government job. Police say there was forgery of an appointment letter.",
  "what other sections can the police add against him?", {("BNS","318"), ("BNS","336"), ("BNS","340")}),
 ("hurt with rod", "My neighbour hit my husband with an iron rod during a quarrel over parking. He has a serious head injury and is in hospital.",
  "which sections apply to the neighbour?", {("BNS","115"), ("BNS","117"), ("BNS","118")}),
 ("visa fraud", "A man took Rs 50,000 from me for a visa and then disappeared. The police have registered a case.",
  "what offences does this make out?", {("BNS","318")}),
 ("dowry cruelty", "My husband beats me and his family keeps demanding more dowry from my parents.",
  "what sections can I complain under?", {("BNS","85")}),
 ("stalking", "A man keeps following my daughter to college and sends her messages every day.",
  "what offence is this?", {("BNS","78")}),
 ("bail (regression)", "My brother was arrested by police for stealing a mobile phone from a shop and is in custody since yesterday.",
  "will he get bail?", {("BNSS","478"), ("BNSS","480")}),
 ("arrest (regression)", "My son was arrested without any notice for an offence that carries three years of imprisonment.",
  "is that arrest legal?", {("BNSS","35")}),
]

CA.classify_scope = lambda q: ("in_scope", "stub", None)
CA._fetch_pilot_related_judgments = lambda *a, **k: []
CA.generate_grounded_response = lambda *a, **k: ""
CA._answer_from_wider_search_only = lambda *a, **k: None
CA._answer_single_match = lambda question, matches: {"state": "single_match", "matches": matches}

rows = []
for name, q1, fu, exp in CONVS:
    cf = C.add_from_message(None, q1)
    turns = [{"q": q1, "answer": {"state": "single_match", "response_text": "x", "matches": []}}]
    row = {"name": name, "expected": sorted("%s %s" % e for e in exp)}
    for label, use in (("NO", False), ("WITH", True)):
        q, info = W.question_for_engine(turns, fu, call=lambda p, c: ('{"follow_up": true, "standalone": "Which sections 999?"}', 0.1), case_file=cf if use else None)
        CA._CASE.arg = W.engine_case_file(cf, info, turns, fu) if use else None
        CA._CARRIED.refs = None
        r = CA._answer_question_core(q)
        got = {((m.get("act") or "").upper(), str(m.get("section_number"))) for m in r.get("matches", []) if isinstance(m, dict) and m.get("section_number")}
        row[label] = {"got": sorted("%s %s" % g for g in got), "hits": sorted("%s %s" % e for e in exp & got)}
        CA._CASE.arg = None
    rows.append(row)
json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_followups.json"), "w"), indent=1)
tot = {"NO": 0, "WITH": 0}
for r in rows:
    print("%-22s expected %-34s NO %d  WITH %d" % (r["name"], ", ".join(r["expected"]), len(r["NO"]["hits"]), len(r["WITH"]["hits"])))
    tot["NO"] += len(r["NO"]["hits"]); tot["WITH"] += len(r["WITH"]["hits"])
print("TOTAL expected sections present:", tot, "of", sum(len(r["expected"]) for r in rows))
