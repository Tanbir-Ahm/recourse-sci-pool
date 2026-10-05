"""Lists every English PDF in the open bucket with its size (anonymous S3 listing; no PDF is downloaded)."""
import re, json, sys, urllib.parse, urllib.request, time
HOST = "https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/"
def page(prefix, token=None):
    q = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
    if token: q["continuation-token"] = token
    for attempt in range(4):
        try:
            return urllib.request.urlopen(HOST + "?" + urllib.parse.urlencode(q), timeout=60).read().decode("utf-8")
        except Exception as e:
            time.sleep(2 ** attempt); err = e
    raise err
sizes = {}
for year in range(1950, 2026):
    token = None; n = 0
    while True:
        x = page(f"data/pdf/year={year}/english/", token)
        for k, s in re.findall(r"<Key>([^<]+)</Key>.*?<Size>(\d+)</Size>", x, re.S):
            sizes[k] = int(s); n += 1
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", x)
        token = m.group(1) if m else None
        if not token: break
    print(year, n, file=sys.stderr)
json.dump(sizes, open("bucket_pdf_sizes.json", "w"))
print("files", len(sizes), "bytes", sum(sizes.values()))
