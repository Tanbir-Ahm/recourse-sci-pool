import pandas as pd,requests,random,re,collections,pymupdf,io
B="https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com"
df=pd.read_pickle('ghc_meta_to2017.pkl'); big=df[df['size']>=10000]
random.seed(7); S=big.sample(70,random_state=7)
res=[]
for _,r in S.iterrows():
    try:
        b=requests.get(f"{B}/data/pdf/year={r.reg_year}/court=18_6/bench={r.bench}/{r.fname}",timeout=60)
    except Exception as e: continue
    if b.status_code!=200: res.append((r.fname,'http%d'%b.status_code)); continue
    d=pymupdf.open(stream=b.content,filetype='pdf'); t="\n".join(p.get_text() for p in d); low=t.lower()
    the=low.count(' the ')/max(1,len(t))*1000
    head=t[:1500].upper()
    kind='JUDGMENT' if re.search(r'JUDGMENT|J U D G M E N T',head) else ('ORDER' if 'ORDER' in head else 'other')
    res.append((r.fname,r.dyear,round(r['size']/1000),len(d),len(t),sum(len(p.get_images())>0 for p in d),round(the,1),kind))
ok=[x for x in res if len(x)>2]
print('sampled',len(res),'fetched',len(ok))
garb=[x for x in ok if x[6]<3]
print('garbled (fewer than 3 " the " per 1000 chars):',len(garb),'| scans (image on a page):',sum(x[5]>0 for x in ok),'| judgment-headed:',sum(x[7]=='JUDGMENT' for x in ok),'| order-headed:',sum(x[7]=='ORDER' for x in ok))
for x in ok[:70:5]: print(x)
print('garbled by size band:',collections.Counter(('>=30KB' if x[2]>=30 else '10-30KB') for x in garb),'of',collections.Counter(('>=30KB' if x[2]>=30 else '10-30KB') for x in ok))
print('JUDGMENT-headed by size band:',collections.Counter(('>=30KB' if x[2]>=30 else '10-30KB') for x in ok if x[7]=='JUDGMENT'))
