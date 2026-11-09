import json,sys,collections
f=sys.argv[1]
rows=json.load(open(f))
def has(r,sec):
    return any(g['type']=='statute' and g['act']=='BNS' and g['sec']==sec for g in r['got'])
def alias(r):
    return sorted({g.get('alias_id') or '' for g in r['got'] if g.get('retrieval')=='alias'})
out=collections.OrderedDict()
for kind,sec in (('pos249','249'),('pos253','253'),('pos254','254')):
    rs=[r for r in rows if r['kind']==kind]
    n=sum(1 for r in rs if has(r,sec))
    out[kind]=(n,len(rs))
neg=[r for r in rows if r['kind']=='neg']
fires=[r for r in neg if any(a.startswith('bns_2') for a in alias(r))]
anyharb=[r for r in neg if any(has(r,s) for s in ('249','253','254'))]
print('positives reached:',dict(out))
print('negatives: alias fires',len(fires),'/',len(neg),'| 249/253/254 present anyway',len(anyharb))
for r in fires: print('  FIRE:',r['q'][:90],alias(r))
for r in anyharb:
    if r not in fires: print('  present by library search:',r['q'][:90],[g['sec'] for g in r['got'] if g['sec'] in ('249','253','254')])
seen=[r for r in rows if r['kind']=='seen'][0]
print('seen question: 249 present',has(seen,'249'),'alias',alias(seen))
if '-v' in sys.argv:
    for r in rows:
        if r['kind'].startswith('pos') and not has(r,{'pos249':'249','pos253':'253','pos254':'254'}[r['kind']]):
            print('  MISS',r['kind'],r['q'][:100])
