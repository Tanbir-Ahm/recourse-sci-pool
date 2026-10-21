import requests,re,io,collections,sys
import pyarrow.parquet as pq, pandas as pd
B="https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com"
def keys(prefix):
    out=[];tok=None
    while True:
        p={"list-type":"2","prefix":prefix,"max-keys":"1000"}
        if tok: p["continuation-token"]=tok
        t=requests.get(B,params=p,timeout=60).text
        out+=list(zip(re.findall(r"<Key>([^<]*)</Key>",t),map(int,re.findall(r"<Size>(\d+)</Size>",t))))
        if "<IsTruncated>true" in t: tok=re.search(r"<NextContinuationToken>([^<]*)<",t).group(1)
        else: return out
frames=[];sizes={}
for y in range(1990,2018):
    for k,s in keys(f"data/pdf/year={y}/court=18_6/"): sizes[k.split('/')[-1]]=s
    for k,s in keys(f"metadata/parquet/year={y}/court=18_6/"):
        if k.endswith('.parquet'):
            r=requests.get(f"{B}/{k}",timeout=120); df=pq.read_table(io.BytesIO(r.content)).to_pandas()
            df['reg_year']=y; df['bench']=k.split('bench=')[1].split('/')[0]; frames.append(df[['cnr','title','decision_date','date_of_registration','disposal_nature','judge','pdf_link','pdf_exists','reg_year','bench']])
df=pd.concat(frames,ignore_index=True)
df['fname']=df.pdf_link.str.split('/').str[-1]; df['size']=df.fname.map(sizes)
df['dyear']=pd.to_datetime(df.decision_date,errors='coerce').dt.year
df.to_pickle('ghc_meta_to2017.pkl')
print('rows',len(df),'| with a PDF size',df['size'].notna().sum(),'| pdf_exists false',(~df.pdf_exists.astype(bool)).sum())
d=df[df.dyear<=2017]
print('decided up to 2017:',len(d))
g=d.groupby('dyear').agg(n=('cnr','size'),ge10=('size',lambda s:(s>=10000).sum()),ge30=('size',lambda s:(s>=30000).sum()))
print(g.tail(14).to_string()); print('TOTAL ge10KB',int(g.ge10.sum()),'ge30KB',int(g.ge30.sum()),'bytes>=10KB',round(d[d['size']>=10000]['size'].sum()/1e6),'MB')
print('decided after 2017 but registered up to 2017:',int((df.dyear>2017).sum()))
