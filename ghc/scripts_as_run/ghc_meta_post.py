import requests,re,io,collections,sys,time
def rget(*a,**k):
    for i in range(5):
        try: return requests.get(*a,**k)
        except Exception: time.sleep(3*(i+1))
    raise RuntimeError('S3 unreachable')
import pyarrow.parquet as pq, pandas as pd
B="https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com"
def keys(prefix):
    out=[];tok=None
    while True:
        p={"list-type":"2","prefix":prefix,"max-keys":"1000"}
        if tok: p["continuation-token"]=tok
        t=rget(B,params=p,timeout=60).text
        out+=list(zip(re.findall(r"<Key>([^<]*)</Key>",t),map(int,re.findall(r"<Size>(\d+)</Size>",t))))
        if "<IsTruncated>true" in t: tok=re.search(r"<NextContinuationToken>([^<]*)<",t).group(1)
        else: return out
frames=[];sizes={}
for y in range(2018,2027):
    for k,s in keys(f"data/pdf/year={y}/court=18_6/"): sizes[k.split('/')[-1]]=s
    for k,s in keys(f"metadata/parquet/year={y}/court=18_6/"):
        if k.endswith('.parquet'):
            r=rget(f"{B}/{k}",timeout=120); df=pq.read_table(io.BytesIO(r.content)).to_pandas()
            df['reg_year']=y; df['bench']=k.split('bench=')[1].split('/')[0]; frames.append(df[['cnr','title','decision_date','date_of_registration','disposal_nature','judge','pdf_link','pdf_exists','reg_year','bench']])
df=pd.concat(frames,ignore_index=True)
df['fname']=df.pdf_link.str.split('/').str[-1]; df['size']=df.fname.map(sizes)
df['dyear']=pd.to_datetime(df.decision_date,errors='coerce').dt.year
df.to_pickle('ghc_meta_post2017.pkl')

df['ctype']=df.title.str.split('/').str[0].str.strip().str.upper()
print('rows',len(df))
g=df.groupby('dyear').agg(n=('cnr','size'),ge10=('size',lambda s:(s>=10000).sum()),ge30=('size',lambda s:(s>=30000).sum()),ab=('ctype',lambda s:(s=='AB').sum()))
b=df[df['size']>=10000]
g['ge10_non_ab']=b[b.ctype!='AB'].groupby('dyear').size()
print(g.to_string()); print('TOTAL',g.sum().to_dict()); print('size of >=10KB non-AB:',round(b[b.ctype!='AB']['size'].sum()/1e6),'MB'); print(b.bench.value_counts().to_dict())
