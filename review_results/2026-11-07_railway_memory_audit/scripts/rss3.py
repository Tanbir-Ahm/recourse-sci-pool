import os, sys, time, gc, types, warnings, tracemalloc
warnings.filterwarnings('ignore')
def st(k):
    for l in open('/proc/self/status'):
        if l.startswith(k+':'): return int(l.split()[1])/1024
os.chdir('/home/user/recourse'); sys.path.insert(0,'/home/user/recourse')
os.environ.update(ACT_SHELF='on', ACT_DETECT='wide', SECTION_XREF='on', GROUNDING_CHECKS='warn', ANCHORS='on', CHECKER_LIST='wide', EVIDENCE_DETECT='on', STATUTE_WIDEN='on', STATUTE_ALIASES='on', VOYAGE_API_KEY='stub')
import numpy as np
rng = np.random.default_rng(1)
def vec():
    v = rng.normal(size=1024); return (v/np.linalg.norm(v)).tolist()
import voyageai
class FakeResp:
    def __init__(self, n): self.embeddings=[vec() for _ in range(n)]; self.total_tokens=10
class FakeClient:
    def __init__(self,*a,**k): pass
    def embed(self, texts, **k): return FakeResp(len(texts))
voyageai.Client = FakeClient
print(f"start {st('VmRSS'):.0f} MB")
import chat_assistant as CA
print(f"after import chat_assistant {st('VmRSS'):.0f} MB (peak {st('VmHWM'):.0f})")
import semantic_retrieval as sr
sr.voyageai.Client = FakeClient
import act_shelf
act_shelf._embed_query = lambda t: vec()
CA.classify_scope = lambda q: ("in_scope", "stub", None)
CA._fetch_pilot_related_judgments = lambda *a, **k: []
CA.generate_grounded_response = lambda *a, **k: ""
CA._answer_from_wider_search_only = lambda *a, **k: None
CA._answer_single_match = lambda question, matches: {"state": "single_match", "matches": matches}
qs = ["can the police arrest me without a warrant for a cheque bounce","section 17 of the prevention of corruption act proviso","my bank froze my account after a complaint","what is the punishment for theft under BNS 303","can an arrest in a disproportionate assets case be made without an enquiry","bail in a POCSO case section 19","what does section 45 of PMLA say about bail","dowry harassment 498A arrest rules","how do I challenge an FIR under BNSS 528","is a confession to police admissible under the evidence act"]
for i, q in enumerate(qs*3):
    t=time.time()
    try: CA._answer_question_core(q)
    except Exception as e: print("ERR", type(e).__name__, str(e)[:80])
    if i in (0,1,2,9,10,29): print(f"after question {i+1:2d}: RSS {st('VmRSS'):6.0f} MB  peak {st('VmHWM'):6.0f} MB  ({time.time()-t:.1f}s)", flush=True)
try:
    import checker_list; checker_list.warm()
    print(f"after checker_list.warm(): RSS {st('VmRSS'):.0f}  peak {st('VmHWM'):.0f}")
except Exception as e: print("checker warm err", e)
