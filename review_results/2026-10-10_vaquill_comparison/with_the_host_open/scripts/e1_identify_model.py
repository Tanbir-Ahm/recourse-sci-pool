"""Which Voyage model (and which input text) produced the vectors stored in Vaquill's Qdrant snapshot?
Embeds a few stored SC chunks with candidate models/variants and compares with the stored vector (cosine). Hard token cap; prints the spend."""
import sys, json, re, os
import numpy as np
sys.path.insert(0, "/home/user/recourse-sci-pool"); sys.path.insert(0, "/home/user/recourse-sci-pool/review_tools")
import sci_index as si
D = sys.argv[1]
vecs = np.load(D + "/sc_vecs.npy"); pay = json.load(open(D + "/sc_payloads.json"))
CAP = int(sys.argv[2])
# choose 3 English chunks of moderate length
cand = [i for i, p in enumerate(pay) if p["language_code"] == "EN" and 1500 < len(p["text"]) < 3000][:3]
HDR = re.compile(r"\ACase: [^\n]*\nSection: [^\n]*\n\n")
client = si.make_client()
tokens = 0
def emb(texts, model, itype):
    global tokens
    kw = {"model": model}
    if itype: kw["input_type"] = itype
    r = client.embed(texts, **kw)
    tokens += r.total_tokens
    if tokens > CAP: raise SystemExit(f"token cap {CAP} exceeded")
    return np.array(r.embeddings, dtype=np.float32)
variants = {"full text (header kept)": [pay[i]["text"] for i in cand], "header removed": [HDR.sub("", pay[i]["text"], count=1) for i in cand]}
S = vecs[cand]; S = S / np.linalg.norm(S, axis=1, keepdims=True)
print("chunks:", [(pay[i]["chunk_id"], len(pay[i]["text"])) for i in cand])
for model in ("voyage-4-large", "voyage-4", "voyage-4-lite", "voyage-law-2"):
    for vname, texts in variants.items():
        for itype in ("document", None):
            try:
                E = emb(texts, model, itype); E = E / np.linalg.norm(E, axis=1, keepdims=True)
                if E.shape[1] != S.shape[1]:
                    print(f"{model:15s} | {vname:24s} | input_type={str(itype):8s} | dims {E.shape[1]} != 1024"); continue
                cos = (E * S).sum(axis=1)
                print(f"{model:15s} | {vname:24s} | input_type={str(itype):8s} | cosine with stored vector: {np.round(cos, 4).tolist()}")
            except Exception as e:
                print(f"{model:15s} | {vname:24s} | input_type={str(itype):8s} | ERROR {str(e)[:110]}")
                break
print("tokens spent:", tokens, "=> about $%.4f at $0.12 per million" % (tokens / 1e6 * 0.12))
