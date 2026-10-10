import sys, re
import numpy as np
import pandas as pd
d = pd.read_parquet(sys.argv[1])
e = d[d.language_code == "en"].sort_values(["case_id", "chunk_index"]).copy()
c = e.drop_duplicates("case_id").copy()
c["id_year"] = c.case_id.str.extract(r"^(\d{4})_")[0].astype(float)
c["dd_year"] = pd.to_datetime(c.decision_date, errors="coerce").dt.year
print("cases:", len(c))
print("year == id_year:", round(float((c.year == c.id_year).mean()), 4), "| year == decision_date year:", round(float((c.year == c.dd_year).mean()), 4), "| decision_date year == id_year:", round(float((c.dd_year == c.id_year).mean()), 4))
bad = c[c.year != c.dd_year]
print("year != decision-date year:", len(bad), "| how far apart (year - dd_year):", (bad.year - bad.dd_year).value_counts().head(6).to_dict())
print("examples:", bad[["case_id", "year", "decision_date"]].head(5).to_dict("records"))
print("year != id_year:", int((c.year != c.id_year).sum()), "| dd_year != id_year:", int((c.dd_year != c.id_year).sum()))
print("per decision-date year, 2009:", int((c.dd_year == 2009).sum()), "| per id_year 2009:", int((c.id_year == 2009).sum()), "| per 'year' 2009:", int((c.year == 2009).sum()))
# gaps
e["prev_end"] = e.groupby("case_id").char_end.shift(1)
gap = (e.char_start - e.prev_end).dropna()
neg = gap[gap > 0]
print("\nboundaries:", len(gap), "| with a gap (next starts after previous ends):", len(neg), f"({len(neg)/len(gap):.1%})")
print("gap size quantiles (chars):", {q: int(neg.quantile(q)) for q in (.5, .9, .99, .999)}, "max", int(neg.max()), "| gaps > 50 chars:", int((neg > 50).sum()), "| > 500:", int((neg > 500).sum()))
big = e.loc[neg[neg > 500].index][["case_id", "chunk_index", "char_start", "prev_end"]].head(5)
print(big.to_dict("records"))
# one-chunk cases
n = e.groupby("case_id").size()
one = n[n == 1].index
print("\none-chunk cases:", len(one), "| their char_end median:", int(e[e.case_id.isin(one)].char_end.median()), "| share with char_end<3000:", float((e[e.case_id.isin(one)].char_end < 3000).mean()))
# short docs by year
last = e.groupby("case_id").char_end.max()
c = c.set_index("case_id"); c["doc_chars"] = last
print("median document length (chars) by decade:", c.groupby((c.dd_year // 10 * 10)).doc_chars.median().astype(int).to_dict())
