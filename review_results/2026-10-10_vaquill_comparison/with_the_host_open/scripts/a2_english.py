"""English rows of Vaquill's Supreme Court parquet: years, completeness, chunk geometry, labels, bench fields."""
import sys, collections
import numpy as np
import pandas as pd
d = pd.read_parquet(sys.argv[1])
e = d[d.language_code == "en"].copy()
print("English rows", len(e), "cases", e.case_id.nunique())
# years
yr = e.drop_duplicates("case_id").groupby("year").size()
print("\nEnglish cases per year (selected):", {int(y): int(yr.get(y, 0)) for y in (2005, 2006, 2007, 2008, 2009, 2010, 2011, 2023, 2024, 2025)})
dy = pd.to_datetime(e.drop_duplicates("case_id").decision_date, errors="coerce").dt.year
print("decision_date year == year column:", float((dy.values == e.drop_duplicates("case_id").year.values).mean()))
print("latest decision_date:", e.decision_date.max(), "| earliest:", e.decision_date.min())
# completeness
g = e.groupby("case_id").agg(n=("chunk_index", "size"), nd=("chunk_index", "nunique"), tot=("total_chunks", "max"), tmin=("total_chunks", "min"), mx=("chunk_index", "max"))
print("\nper English case: chunks present vs total_chunks")
print("  cases:", len(g), "| complete (distinct indexes == total):", int((g.nd == g.tot).sum()), "| missing some:", int((g.nd < g.tot).sum()), "| duplicate chunk_index rows:", int((g.n > g.nd).sum()), "| total_chunks inconsistent:", int((g.tmin != g.tot).sum()))
print("  chunk-count per case: median", g.n.median(), "mean", round(g.n.mean(), 1), "max", g.n.max(), "| cases with 1 chunk:", int((g.n == 1).sum()), "| with <=2:", int((g.n <= 2).sum()))
# geometry
e = e.sort_values(["case_id", "chunk_index"])
e["len"] = e.char_end - e.char_start
print("\nchunk length (char_end-char_start): median", int(e["len"].median()), "p10", int(e["len"].quantile(.1)), "p90", int(e["len"].quantile(.9)), "max", int(e["len"].max()), "min", int(e["len"].min()))
e["prev_end"] = e.groupby("case_id").char_end.shift(1)
ov = (e.prev_end - e.char_start).dropna()
print("overlap with previous chunk (chars): median", int(ov.median()), "p10", int(ov.quantile(.1)), "p90", int(ov.quantile(.9)), "| share with overlap>0:", float((ov > 0).mean()), "| gaps (negative overlap):", float((ov < 0).mean()))
last = e.groupby("case_id").char_end.max()
print("document length by char_end (median):", int(last.median()), "| sum chars (indexed text volume incl overlaps):", int(e["len"].sum()))
# pages
print("\npage_start/page_end: null", int(e.page_start.isna().sum()), "| page_start==0:", int((e.page_start == 0).sum()), "| median page span", float((e.page_end - e.page_start).median()), "| chunks spanning >1 page:", float(((e.page_end - e.page_start) > 0).mean()))
fc = e[e.chunk_index == 0]
print("first chunk starts on page:", fc.page_start.value_counts().head(4).to_dict())
# labels
print("\nsection_type, English:"); print(e.section_type.value_counts().to_string())
print("section_priority values:", e.section_priority.value_counts().head(8).to_dict())
# bench
c = e.drop_duplicates("case_id").copy()
c["nj"] = c.judges.map(lambda x: len(x) if x is not None else 0)
print("\nbench_strength distribution:", c.bench_strength.value_counts().sort_index().to_dict())
print("len(judges) distribution:", c.nj.value_counts().sort_index().head(12).to_dict())
print("bench_strength == len(judges):", float((c.bench_strength == c.nj).mean()), "| bench_strength==1 share:", float((c.bench_strength == 1).mean()))
print("examples:", c[["case_id", "bench_strength", "judges"]].head(6).to_dict("records"))
print("\ndisposition top:", c.disposition.value_counts().head(8).to_dict())
