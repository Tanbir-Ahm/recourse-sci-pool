import os, sys, time, json, gc
def rss():
    for l in open('/proc/self/status'):
        if l.startswith('VmRSS:'): return int(l.split()[1])/1024
def step(name, fn):
    gc.collect(); a=rss(); t=time.time(); r=fn(); gc.collect(); b=rss()
    print(f"{name:55s} +{b-a:7.1f} MB  (total {b:7.1f} MB) {time.time()-t:5.1f}s", flush=True); return r
os.chdir('/home/user/recourse'); sys.path.insert(0,'/home/user/recourse')
print(f"baseline python {rss():.1f} MB")
step("import numpy", lambda: __import__('numpy'))
step("import streamlit", lambda: __import__('streamlit'))
step("import voyageai", lambda: __import__('voyageai'))
step("import anthropic", lambda: __import__('anthropic'))
import semantic_retrieval as sr
step("corpus_embeddings.json -> _load_corpus_embeddings()", sr._load_corpus_embeddings)
c=sr._corpus_cache
print("   matrix dtype/shape:", c['matrix'].dtype, c['matrix'].shape, f"{c['matrix'].nbytes/1e6:.1f} MB")
step("import chat_assistant", lambda: __import__('chat_assistant'))
step("import recourse_app (streamlit script module)", lambda: None)
