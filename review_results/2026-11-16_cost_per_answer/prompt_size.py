import os, sys, json, types
sys.path.insert(0, "/home/user/recourse")
os.chdir("/home/user/recourse")  # NOTE: writes prompt_size.json into the Recourse checkout; move it here
for k, v in {"RESPONSE_STYLE":"v3","ANSWER_EFFORT":"medium","ACT_SHELF":"on","ACT_DETECT":"wide","SECTION_XREF":"on","PASSAGE_NOTES":"on","ANCHORS":"on","SCOPE_GATE":"open","SCI_SEARCH_MODE":"off","GROUNDING_CHECKS":"warn","STATUTE_ALIASES":"on","STATUTE_WIDEN":"on"}.items():
    os.environ[k] = v
import chat_assistant as CA
CA.classify_scope = lambda q: ("in_scope", "stub", None)
CA._fetch_pilot_related_judgments = lambda *a, **k: []
CALLS = []
class R:  # fake response
    def __init__(s, t):
        s.content = [types.SimpleNamespace(type="text", text=t)]; s.stop_reason = "end_turn"; s.usage = types.SimpleNamespace(input_tokens=0, output_tokens=0)
class M:
    def create(self, **kw):
        m = kw["messages"][0]["content"]
        p = m if isinstance(m, str) else "".join(b["text"] for b in m)
        CALLS.append({"model": kw.get("model"), "chars": len(p), "max_tokens": kw.get("max_tokens")})
        return R("Stub answer.")
CA.client = types.SimpleNamespace(messages=M())
Q = [
 ("tada sedition", "My brother was convicted of sedition by a TADA Designated Court and given life imprisonment. His lawyer is relying on Bilal Ahmed Kaloo. Can he appeal?"),
 ("job cheating", "My father was arrested for cheating a person of Rs 5 lakh by promising a government job. Police say there was forgery of an appointment letter."),
 ("hurt with rod", "My neighbour hit my husband with an iron rod during a quarrel over parking. He has a serious head injury and is in hospital."),
 ("dowry cruelty", "My husband beats me and his family keeps demanding more dowry from my parents."),
 ("stalking", "A man keeps following my daughter to college and sends her messages every day."),
 ("bail theft", "My brother was arrested by police for stealing a mobile phone from a shop and is in custody since yesterday. Will he get bail?"),
 ("arrest legal", "My son was arrested without any notice for an offence that carries three years of imprisonment. Is that arrest legal?"),
 ("pc act s17", "Can a police officer investigate a public servant under the Prevention of Corruption Act without prior approval under section 17?"),
 ("drink drive", "I was stopped by the police while driving after two drinks and they say I caused an accident. What sections can be applied against me?"),
 ("cheque bounce", "My cheque for Rs 3 lakh bounced and the payee has sent a notice. What should I do under section 138?"),
]
out = []
for aud in ("layman", "lawyer"):
    for name, q in Q:
        CALLS.clear()
        CA.answer_style.set_audience(aud) if hasattr(CA.answer_style, "set_audience") else None
        try:
            r = CA.answer_question(q, audience=aud)
            st = r.get("state") if isinstance(r, dict) else None
        except Exception as e:
            st = "ERR " + repr(e)[:100]
        big = max([c["chars"] for c in CALLS if (c["max_tokens"] or 0) >= 4000] or [0])
        out.append({"aud": aud, "name": name, "state": st, "answer_call_chars": big, "calls": CALLS[:]})
        print(aud[:3], name.ljust(14), str(st).ljust(18), "prompt chars", big, "calls", len(CALLS), flush=True)
json.dump(out, open("prompt_size.json", "w"), indent=1)
