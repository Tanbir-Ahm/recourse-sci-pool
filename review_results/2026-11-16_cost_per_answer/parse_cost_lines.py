import json,glob,statistics as st,collections
rows=[]
seen=set()
for f in sorted(glob.glob('review_results/**/*.log',recursive=True)+glob.glob('review_results/**/*.txt',recursive=True)):
    for line in open(f,errors='replace'):
        i=line.find('COST_QUESTION ')
        if i<0: continue
        try: r=json.loads(line[i+14:].strip())
        except Exception: continue
        key=(r['q'],r['inr'])
        if key in seen: continue
        seen.add(key); rows.append((f,r))
for f,r in rows:
    ans=[c for c in r['calls'] if c['label'].startswith('answer')]
    other=sum(c['inr'] for c in r['calls'] if not c['label'].startswith('answer'))
    ain=sum(c.get('in',0) for c in ans); aout=sum(c.get('out',0) for c in ans)
    n=len(ans)
    print(f.split('/')[1][:25].ljust(26), r['audience'][:3], r['style'], 'inr=%.2f'%r['inr'], 'answer_calls=%d'%n, 'in=%d out=%d'%(ain,aout), 'other_inr=%.2f'%other, 'eff=%s'%r['switches'].get('effort'), 'model=',ans[0]['model'] if ans else None, 'usdinr',r['usd_inr'])
print()
for aud in ('layman','lawyer'):
    v=[r['inr'] for f,r in rows if r['audience']==aud]
    if v: print(aud,len(v),'min %.2f median %.2f mean %.2f max %.2f'%(min(v),st.median(v),st.mean(v),max(v)))
