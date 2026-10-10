"""Overview of Vaquill's Supreme Court parquet from its non-text columns (meta.parquet in scratch)."""
import sys, collections
import pandas as pd
d = pd.read_parquet(sys.argv[1])
print("rows", len(d), "distinct case_id", d.case_id.nunique(), "distinct chunk_id", d.chunk_id.nunique())
print("\nlanguage_code (rows / distinct case_id):")
g = d.groupby("language_code").agg(rows=("chunk_id", "size"), cases=("case_id", "nunique")).sort_values("rows", ascending=False)
print(g.to_string())
print("\ncourt/court_type values:", d.court.value_counts().to_dict(), d.court_type.value_counts().to_dict())
print("\nsection_type (all rows):"); print(d.section_type.value_counts().to_string())
print("\nbox_aware:", d.box_aware.value_counts(dropna=False).to_dict())
print("\nyear dtype/min/max:", d.year.min(), d.year.max(), "| null years:", int(d.year.isna().sum()))
print("\nfill rates over ALL rows (non-null and non-empty):")
for c in ["source_url", "citation", "case_number", "decision_date", "date_of_registration", "title", "petitioner", "respondent", "disposition", "bench", "description", "court_code"]:
    s = d[c]
    ok = s.notna() & (s.astype(str).str.strip() != "")
    print(f"  {c:22s} {ok.mean():7.1%}")
ok = d.judges.map(lambda x: x is not None and len(x) > 0)
print(f"  {'judges':22s} {ok.mean():7.1%}")
print(f"  {'bench_strength>0':22s} {(d.bench_strength.fillna(0) > 0).mean():7.1%}")
print("\nexample rows (English first chunk):")
e = d[(d.language_code.str.lower() == "en") & (d.chunk_index == 0)].head(3)
print(e[["case_id", "chunk_id", "total_chunks", "char_start", "char_end", "page_start", "page_end", "section_type", "citation", "case_number", "decision_date", "source_url", "bench_strength"]].to_string())
