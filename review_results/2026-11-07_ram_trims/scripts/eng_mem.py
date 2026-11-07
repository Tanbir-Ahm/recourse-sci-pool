import sys, os, warnings, ctypes, gc; warnings.filterwarnings('ignore'); sys.path.insert(0,'/home/user/recourse'); os.chdir('/home/user/recourse')
os.environ.update(ACT_SHELF='on', CHECKER_LIST='wide', VOYAGE_API_KEY='stub')
def rss():
    for l in open('/proc/self/status'):
        if l.startswith('VmRSS:'): return int(l.split()[1])/1024
import chat_assistant, semantic_retrieval as sr, act_shelf, checker_list
sr._load_corpus_embeddings(); act_shelf.load(); checker_list.warm()
gc.collect(); a=rss(); ctypes.CDLL("libc.so.6").malloc_trim(0)
print("ENG", "keep" if os.environ.get("KEEP_RECORD_VECTORS") else "release", "RSS after load %.0f MB (after malloc_trim %.0f), fitz loaded: %s"%(a, rss(), 'fitz' in sys.modules))
