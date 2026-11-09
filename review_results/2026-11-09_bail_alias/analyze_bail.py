import json,sys
rows=json.load(open(sys.argv[1]))
def has(r,sec): return any(g['type']=='statute' and g['act']=='BNSS' and g['sec']==sec for g in r['got'])
def alias(r): return sorted({g['sec'] for g in r['got'] if g.get('retrieval')=='alias' and g['act']=='BNSS' and g['sec'] in ('478','480','483')})
pa=[r for r in rows if r['kind']=='pos_arrest']; p3=[r for r in rows if r['kind']=='pos_483']; ng=[r for r in rows if r['kind']=='neg']
both=sum(1 for r in pa if has(r,'478') and has(r,'480'))
print('arrest positives: 478 and 480 both',both,'/',len(pa),'| 478',sum(has(r,'478') for r in pa),'| 480',sum(has(r,'480') for r in pa))
print('bail-refused positives: 483',sum(has(r,'483') for r in p3),'/',len(p3))
fires=[r for r in ng if alias(r)]
print('negatives: alias fires',len(fires),'/',len(ng),'| 478/480/483 present anyway',sum(1 for r in ng if any(has(r,s) for s in ('478','480','483'))))
for r in fires: print('  FIRE',alias(r),r['q'][:90])
if '-v' in sys.argv:
    for r in pa:
        if not (has(r,'478') and has(r,'480')): print('  MISS arrest',[s for s in ('478','480') if not has(r,s)],r['q'][:90])
    for r in p3:
        if not has(r,'483'): print('  MISS 483',r['q'][:90])
