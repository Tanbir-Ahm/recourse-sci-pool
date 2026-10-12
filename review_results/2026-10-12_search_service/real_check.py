import json, sys, os, time
sys.path.insert(0,'/home/user/recourse-sci-pool')
import sci_search_service as S
pool=json.load(open('review_results/2026-10-12_fix_test_f/pool.json'))
idx, sides = S._paths()
svc=S.SearchService.load(idx, sides, rerank_model="rerank-3-lite")
qs=pool['questions']
names=list(qs[0]['lists']); B=[n for n in names if n.startswith('B ')][0]
same=0; tot=0
for q in qs[:4]:
    res=svc.search(q['question'])
    got=[(r['doc'],r['passage_id']) for r in res['results']]
    want=[(e['doc'],e['h']) for e in q['lists'][B]]
    ok = got==want
    ov=len(set(got)&set(want))
    print(q['qid'], 'identical' if ok else f'differs (overlap {ov}/10)', res['seconds'],'s', '|', res['results'][0]['case_name'])
    tot+=1; same+=ok
print(same,'of',tot,'identical to the saved stage F list for B'); print(json.dumps(svc.health()['today']), 'rss', S.current_rss_mb())
