"""Reads every non-text column of Vaquill's Supreme Court judgments parquet (v2026.08.1) by range requests -> meta.parquet (local scratch)."""
import sys, time
sys.path.insert(0, ".")
from concurrent.futures import ThreadPoolExecutor
import pyarrow as pa
import pyarrow.parquet as pq
from rangefile import RangeFile
URL = "https://oss-data-in.vaquill.ai/v2026.08.1/in_supreme-court_judgments.parquet"
SIZE = 3761559020
COLS = ["case_id", "chunk_id", "chunk_index", "total_chunks", "char_start", "char_end", "page_start", "page_end", "section_type", "section_priority", "box_aware",
        "court", "court_code", "court_type", "bench", "bench_strength", "judges", "title", "description", "petitioner", "respondent", "disposition", "case_number", "citation",
        "decision_date", "date_of_registration", "year", "source_url", "language_code"]
def one(g):
    for attempt in range(6):
        try:
            pf = pq.ParquetFile(RangeFile(URL, SIZE, tail=4 * 1024 * 1024))
            t = pf.read_row_group(g, columns=COLS)
            return g, t
        except Exception as e:
            time.sleep(1 + 2 * attempt)
    raise RuntimeError(g)
t0 = time.time()
with ThreadPoolExecutor(8) as ex:
    parts = dict(ex.map(one, range(56)))
tbl = pa.concat_tables([parts[g] for g in range(56)])
pq.write_table(tbl, "meta.parquet", compression="zstd")
print("rows", tbl.num_rows, "seconds", round(time.time() - t0))
