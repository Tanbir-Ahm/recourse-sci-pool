import json,sys,collections
d=json.load(open('fts_proxy_out.json')); R=d['rows']
def court(r): return 'HC' if (r['doc'] or 0)>=2_000_000_000 else 'SC'
def block(sel,name):
    n=len(sel)
    if not n: return
    long600=[r for r in sel if r['len']>600]
    # relevant words exist in the passage (>=2 of the question's words) but none in what the page shows
    never_page=[r for r in sel if r['all']>=2 and r['shown']==0]
    never_model=[r for r in sel if r['all']>=2 and r['window']==0]
    half_page=[r for r in sel if r['all']>=2 and r['shown']*2<r['all']]
    print(f"{name}: top-12 passages {n:,} in {len({r['doc'] for r in sel}):,} judgments | longer than 600 chars {len(long600)/n:.0%} | question words in the passage but NONE in the page excerpt: {len(never_page)} ({len(never_page)/n:.1%}), {len({r['doc'] for r in never_page})} judgments | NONE in the model's 900 chars: {len(never_model)} ({len(never_model)/n:.1%}), {len({r['doc'] for r in never_model})} judgments | fewer than half of the matched words shown: {len(half_page)/n:.1%}")
block(R,'ALL'); block([r for r in R if court(r)=='SC'],'Supreme Court'); block([r for r in R if court(r)=='HC'],'Gauhati HC')
print('questions',d['questions'])
