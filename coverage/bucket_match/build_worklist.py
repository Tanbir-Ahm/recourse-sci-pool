"""Builds worklist.csv.gz: the bucket judgments the downloader (../../sci_bucket.py) must fetch, with their metadata.

scope "after": dated after 4 May 2017 (the crawl's last date), 7,125 judgments.
scope "none":  dated up to 4 May 2017 but not found in the crawl by name/date (registry tier "none"), 4,833 judgments. The downloader fetches
               these only to compare their texts with the crawl's and keep the ones the crawl truly lacks.

Reads registry.csv.gz (made by bucket_registry_match.py) and the bucket's per-year metadata tables, writes worklist.csv.gz sorted by
(decision date, file path) so block numbers are stable. Run: python build_worklist.py REGISTRY.csv.gz META_DIR OUT.csv.gz
(META_DIR holds meta_<year>.parquet downloaded from s3://indian-supreme-court-judgments/metadata/parquet/year=<year>/metadata.parquet)
"""
import glob, hashlib, re, sys
import pandas as pd

reg_path, meta_dir, out_path = sys.argv[1:4]
reg = pd.read_csv(reg_path, dtype={"crawl_ids": str}).fillna({"crawl_ids": ""})
raw = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{meta_dir}/meta_*.parquet"))], ignore_index=True)
raw = raw.drop_duplicates(["path", "decision_date"]).set_index(["path", "decision_date"])
keep = ["petitioner", "respondent", "judge", "author_judge", "disposal_nature", "nc_display", "cnr", "available_languages"]
meta = raw[keep]
rows = reg[reg.tier.isin(["after", "none"])].copy()
rows["scope"] = rows.tier
rows = rows.join(meta, on=["path", "decision_date"])
rows["_d"] = pd.to_datetime(rows.decision_date, format="%d-%m-%Y")
rows = rows.sort_values(["scope", "_d", "path"]).drop(columns=["_d", "dyear", "crawl_ids"])
cols = ["scope", "decision_date", "path", "key", "size", "title", "petitioner", "respondent", "citation", "case_id", "nc_display", "cnr",
        "judge", "author_judge", "disposal_nature", "available_languages", "tier"]
rows[cols].to_csv(out_path, index=False)
print(rows.scope.value_counts().to_dict(), "rows with no file:", int(rows.key.isna().sum()))
