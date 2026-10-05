import gzip, json, re, os, glob, statistics
import pymupdf as fitz
D="/home/user/recourse-sci-pool-data"
W=lambda s: re.findall(r"[a-z0-9]+", s.lower())
def shingles(ws,n=8): return {" ".join(ws[i:i+n]) for i in range(max(len(ws)-n+1,0))}
CITE=re.compile(r"\(?\b(?:19|20)\d{2}\)?\s*\d{0,2}\s*(?:Supp\.?\s*\(?\d+\)?\s*)?(?:SCC|SCR|AIR)\b[^\s,;.]{0,12}",re.I)
VS=re.compile(r"\b([A-Z][A-Za-z.\-' ]{2,40}?)\s+(?:v\.?|vs\.?)\s+([A-Z][A-Za-z.\-' ]{2,40}?)(?=[\s,;:(\[]|$)")
def key(m): return re.sub(r"[^a-z]","",(m.group(1)+m.group(2)).lower())[:24]
match=json.load(open("matches.json"))
def crawl_text(i):
    f=glob.glob(f"{D}/shards/{i//250*250:06d}-*.jsonl.gz")[0]
    for l in gzip.open(f,"rt",encoding="utf-8"):
        r=json.loads(l)
        if r["id"]==i: return r["text"]
rows=[]
for f,(cid,ov) in match.items():
    if ov<200: continue
    b=fitz.open(f); bt="".join(p.get_text() for p in b)
    ct=crawl_text(cid)
    bw,cw=W(bt),W(ct)
    bs,cs=shingles(bw),shingles(cw)
    cont_c_in_b=len(cs&bs)/max(len(cs),1); cont_b_in_c=len(bs&cs)/max(len(bs),1)
    ek=lambda c: 1-c**(1/8)
    ccites={m.group(0).strip() for m in CITE.finditer(ct)}; bcites={m.group(0).strip() for m in CITE.finditer(bt)}
    cn={key(m) for m in VS.finditer(ct)}; bn={key(m) for m in VS.finditer(bt)}
    rows.append(dict(f=os.path.basename(f)[:12],year=int(os.path.basename(f)[:4]),words_b=len(bw),words_c=len(cw),cont=cont_c_in_b,cont_rev=cont_b_in_c,err=ek(cont_c_in_b),
                     name_recall=len(cn&bn)/max(len(cn),1),n_names_c=len(cn),n_names_b=len(bn),cite_recall=len(ccites&bcites)/max(len(ccites),1),n_cites_c=len(ccites)))
print(f"{len(rows)} judgments compared (same judgment, two sources: the court-site PDF text from the crawl, and the bucket's scanned law-report PDF)\n")
print(f"{'PDF':14}{'yr':>5}{'words(bucket)':>14}{'words(crawl)':>13}{'crawl 8-word runs found in bucket':>35}{'implied word diff':>18}{'case names found':>17}")
for r in sorted(rows,key=lambda r:r['year']):
    print(f"{r['f']:14}{r['year']:>5}{r['words_b']:>14}{r['words_c']:>13}{r['cont']:>35.2f}{r['err']:>18.3f}{r['name_recall']:>12.2f} ({r['n_names_c']})")
m=lambda k: statistics.median(r[k] for r in rows)
print(f"\nmedian: crawl text found in bucket text {m('cont'):.2f} | implied word-level difference about {m('err')*100:.1f}% | case names found {m('name_recall'):.2f} | cite strings found {m('cite_recall'):.2f}")
print("by year (median runs found / names found):", {y:(round(statistics.median(r['cont'] for r in rows if r['year']==y),2),round(statistics.median(r['name_recall'] for r in rows if r['year']==y),2)) for y in sorted({r['year'] for r in rows})})
json.dump(rows,open("fidelity.json","w"))
