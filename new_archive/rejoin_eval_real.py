import sys,pickle,random,gzip,json,glob,collections,re,importlib.util
sys.path.insert(0,sys.argv[1])
import rejoin_guwahati as rj
lex=pickle.load(open(sys.argv[1]+'/lex.pkl','rb'))
spec=importlib.util.spec_from_file_location('pe','/home/user/recourse-code/new_archive/plan_embedding.py')
src=open('/home/user/recourse-code/new_archive/plan_embedding.py').read()
ns={}; exec(src[src.index('def unwrap_fixed'):src.index('index_seen')],{'collections':collections},ns); old=ns['unwrap_fixed']
random.seed(3)
docs=[]
for f in sorted(glob.glob('../ghc-bucket-data/shards/*.jsonl.gz')):
    for l in gzip.open(f,'rt'):
        r=json.loads(l)
        if r.get('text_source')!='court' and r.get('reasoned_judgment') and not r.get('excluded_type'): docs.append(r)
docs=random.sample(docs,300)
tok=re.compile(r"[A-Za-z]+")
def score(texts):
    n=rec=frag=0
    for t in texts:
        for w in tok.findall(t):
            n+=1
            if lex.is_word(w): rec+=1
            elif len(w)<=2: frag+=1
    return n,rec/n,frag/n
raw=[d['text'] for d in docs]
print('variant                     tokens   recognised  1-2letter-fragments')
for name,f in [('raw',lambda t:t),('old unwrap_fixed',old)]+[(f'new slack={s}',lambda t,s=s:rj.rejoin(t,lex,slack=s)) for s in (4,8,12,20,40)]:
    n,r,fr=score([f(t) for t in raw]); print(f'{name:26s} {n:8d}   {r:.4f}      {fr:.4f}')
