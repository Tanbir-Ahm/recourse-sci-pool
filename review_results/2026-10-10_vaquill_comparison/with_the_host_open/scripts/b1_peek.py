import sys, time, textwrap
sys.path.insert(0, sys.argv[1])
import pyarrow.parquet as pq
from rangefile import RangeFile
URL = "https://oss-data-in.vaquill.ai/v2026.08.1/in_supreme-court_judgments.parquet"
SIZE = 3761559020
t = time.time()
pf = pq.ParquetFile(RangeFile(URL, SIZE, tail=4 * 1024 * 1024))
tb = pf.read_row_group(5, columns=["case_id", "chunk_index", "total_chunks", "language_code", "text", "text_original", "section_type", "char_start", "char_end", "page_start", "page_end"])
print("row group 5 rows", tb.num_rows, "seconds", round(time.time() - t, 1))
d = tb.to_pandas()
print(d.language_code.value_counts().to_dict())
print("text == text_original share:", float((d.text == d.text_original).mean()))
e = d[d.language_code == "en"]
r = e.iloc[3]
print("\n--- ENGLISH chunk", r.case_id, r.chunk_index, "of", r.total_chunks, r.section_type, "pages", r.page_start, r.page_end, "chars", r.char_start, r.char_end)
print("[text] len", len(r.text)); print(r.text[:900]); print("...")
print("[text_original] len", len(r.text_original)); print(r.text_original[:700])
for lang in ("pun", "hin"):
    x = d[d.language_code == lang].iloc[2]
    print(f"\n--- {lang.upper()} chunk", x.case_id, x.chunk_index, "of", x.total_chunks)
    print(x.text_original[:400])
