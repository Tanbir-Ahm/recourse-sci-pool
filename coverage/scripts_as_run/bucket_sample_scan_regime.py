import pyarrow.parquet as pq, requests, re, os, random, collections, statistics
import pymupdf as fitz
B="https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=%d/english/%s_EN.pdf"
random.seed(5)
sample=[]
for y in range(2017,2026):
    rows=[r for r in pq.read_table(f"meta_{y}.parquet").to_pylist() if r.get('path')]
    sample += random.sample(rows,3)
stats=[]
os.makedirs("pdfs",exist_ok=True)
for r in sample:
    fn=f"pdfs/{r['year']}_{r['path']}.pdf"
    if not os.path.exists(fn):
        try:
            resp=requests.get(B%(int(r['year']),r['path']),timeout=90)
            if resp.status_code!=200: print('HTTP',resp.status_code,r['path']); continue
            open(fn,'wb').write(resp.content)
        except Exception as e: print('fail',r['path'],type(e).__name__); continue
    doc=fitz.open(fn)
    pages=len(doc); img_pages=0; textless=0; chars=0; fonts=set()
    for p in doc:
        t=p.get_text(); chars+=len(t)
        if len(t.strip())<40: textless+=1
        if p.get_images(): img_pages+=1
        for f in p.get_fonts(): fonts.add(f[3])
    stats.append(dict(year=r['year'],path=r['path'],pages=pages,img_pages=img_pages,textless=textless,chars=chars,producer=doc.metadata.get('producer'),creator=doc.metadata.get('creator'),nfonts=len(fonts),kb=os.path.getsize(fn)//1000))
print(f"{len(stats)} PDFs sampled, 3 per year 2017-2025")
print("pages with an embedded image (a scan):", sum(s['img_pages'] for s in stats), "of", sum(s['pages'] for s in stats))
print("pages with almost no text:", sum(s['textless'] for s in stats))
print("producers:", collections.Counter(s['producer'] for s in stats).most_common(4))
print("creators:", collections.Counter(s['creator'] for s in stats).most_common(4))
print("median chars/page:", int(statistics.median(s['chars']/s['pages'] for s in stats)), "| median file KB:", statistics.median(s['kb'] for s in stats), "| mean KB:", round(statistics.mean(s['kb'] for s in stats)))
import json; json.dump(stats,open('ocr_stats.json','w'))
