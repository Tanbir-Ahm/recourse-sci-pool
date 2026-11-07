import os, sys, time, json, gc
def st(k):
    for l in open('/proc/self/status'):
        if l.startswith(k+':'): return int(l.split()[1])/1024
def step(name, fn):
    gc.collect(); a=st('VmRSS'); t=time.time()
    try: r=fn()
    except Exception as e: print("   ERR", name, type(e).__name__, str(e)[:100]); r=None
    gc.collect(); b=st('VmRSS')
    print(f"{name:58s} +{b-a:7.1f} MB  total {b:7.1f}  peak {st('VmHWM'):7.1f}  {time.time()-t:5.1f}s", flush=True); return r
os.chdir('/home/user/recourse'); sys.path.insert(0,'/home/user/recourse')
os.environ.update(ACT_SHELF='on', ACT_DETECT='wide', SECTION_XREF='on', REGISTER_HOOKS='on', GROUNDING_CHECKS='warn', ANCHORS='on', CHECKER_LIST='wide')
import warnings; warnings.filterwarnings('ignore')
step("import streamlit+numpy+voyage+anthropic", lambda: [__import__(m) for m in ('numpy','streamlit','voyageai','anthropic')])
import chat_assistant as ca
step("import chat_assistant (+ all it imports)", lambda: None)
import semantic_retrieval as sr
step("semantic_retrieval corpus embeddings (1,666 chunks)", sr._load_corpus_embeddings)
import act_shelf, act_directory
step("act_directory.load()", act_directory.load)
step("act_shelf.load() (13 Acts + 22 MB embeddings json)", act_shelf.load)
import importlib
for m in ('register_hooks','checker_list','grounding_checks','search_service','case_lookup','retrieval','excerpt_anchors','ea_bsa_map','statute_concordance'):
    try: importlib.import_module(m)
    except Exception as e: print("import fail", m, type(e).__name__)
step("after importing remaining modules", lambda: None)
# touch known loaders
import checker_list as cl
for fn in ('load','names','get','_load'):
    if hasattr(cl, fn):
        step("checker_list."+fn+"()", getattr(cl, fn)); break
print([n for n in dir(cl) if not n.startswith('__')][:30])
print("---- more loaders")
step("checker_list.warm() (wide: 38k titles + 19k names)", cl.warm)
import register_hooks as rh
for fn in ('load','warm','_load','ensure'):
    if hasattr(rh, fn):
        step("register_hooks."+fn+"()", getattr(rh, fn)); break
import search_service as ss
print([n for n in dir(ss) if 'library' in n.lower() or 'load' in n.lower() or 'index' in n.lower()][:20])
import statute_concordance as sc2
