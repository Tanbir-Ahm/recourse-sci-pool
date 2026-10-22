import sys,pickle,random,gzip,json,glob,collections,re
sys.path.insert(0,sys.argv[1])
import rejoin_guwahati as rj
lex=pickle.load(open(sys.argv[1]+'/lex.pkl','rb'))
random.seed(11)
docs=[]
for f in sorted(glob.glob('../ghc-bucket-data/shards/*.jsonl.gz')):
    for l in gzip.open(f,'rt'):
        r=json.loads(l)
        if r.get('text_source')!='court' and r.get('reasoned_judgment') and not r.get('excluded_type'): docs.append(r)
docs=random.sample(docs,400)
cases=[]
for r in docs:
    for ln in r['text'].split('\n'):
        if len(ln)<70: continue
        # eligible cut points inside the line
        for _ in range(3):
            p=random.randrange(8,len(ln)-8)
            if re.match('[A-Za-z]{2}',ln[p-1:p+1]):               # inside a word
                mL=re.search(r'[A-Za-z]+$',ln[:p]); mR=re.match(r'[A-Za-z]+',ln[p:])
                cases.append((mL.group(),mR.group(),'join'))
            elif ln[p]==' ' and re.match('[A-Za-z] [A-Za-z]',ln[p-1:p+2]):   # at a word end, space lost
                mL=re.search(r'[A-Za-z]+$',ln[:p]); mR=re.match(r'[A-Za-z]+',ln[p+1:])
                cases.append((mL.group(),mR.group(),'space'))
random.shuffle(cases); cases=cases[:20000]
n=len(cases); nj=sum(1 for c in cases if c[2]=='join'); print(n,'cases;',round(nj/n,3),'are mid-word')
def run(name,f):
    c=collections.Counter()
    for L,R,t in cases: c[(t,f(L,R))]+=1
    acc=(c[('join','join')]+c[('space','space')])/n
    print(f"{name:28s} acc {acc:.3f}  glued-two-words {c[('space','join')]/max(1,sum(v for k,v in c.items() if k[0]=='space')):.3f}  split-a-word {c[('join','space')]/max(1,sum(v for k,v in c.items() if k[0]=='join')):.3f}")
run('always join (old rule)',lambda L,R:'join')
run('always space',lambda L,R:'space')
for k in (0.25,0.5,1.0,2.0,4.0):
    run(f'lexicon kappa={k}',lambda L,R,k=k: rj.decide(L,R,lex,k))
# by case: show examples of errors at kappa=1
err=collections.Counter(); ex=collections.defaultdict(list)
for L,R,t in cases:
    d=rj.decide(L,R,lex,1.0)
    if d!=t:
        why='L+R word' if lex.count(L+R)>=rj.T else 'neither'
        err[(t,why)]+=1
        if len(ex[(t,why)])<8: ex[(t,why)].append((L,R))
print(err)
for k,v in ex.items(): print(k,v)
