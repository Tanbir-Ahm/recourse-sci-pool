"""Reads the English chunks' text_original of Vaquill's Supreme Court parquet (all 56 row groups) -> en_text.parquet in scratch. Also checks text == text_original on 6 row groups."""
import sys, time
sys.path.insert(0, sys.argv[1])
from concurrent.futures import ThreadPoolExecutor
import pyarrow as pa, pyarrow.compute as pc, pyarrow.parquet as pq
from rangefile import RangeFile
URL = "https://oss-data-in.vaquill.ai/v2026.08.1/in_supreme-court_judgments.parquet"
SIZE = 3761559020
def one(g):
    for attempt in range(6):
        try:
            pf = pq.ParquetFile(RangeFile(URL, SIZE, tail=4 * 1024 * 1024))
            t = pf.read_row_group(g, columns=["case_id", "chunk_index", "language_code", "text_original"])
            t = t.filter(pc.equal(t["language_code"], "en")).drop(["language_code"])
            return g, t
        except Exception as e:
            time.sleep(1 + 2 * attempt)
    raise RuntimeError(g)
t0 = time.time()
with ThreadPoolExecutor(8) as ex:
    parts = dict(ex.map(one, range(56)))
tbl = pa.concat_tables([parts[g] for g in range(56)])
pq.write_table(tbl, sys.argv[2], compression="zstd")
print("english chunks", tbl.num_rows, "seconds", round(time.time() - t0))
# text vs text_original on a few row groups
same = tot = 0
for g in (0, 11, 23, 34, 45, 55):
    pf = pq.ParquetFile(RangeFile(URL, SIZE, tail=4 * 1024 * 1024))
    t = pf.read_row_group(g, columns=["text", "text_original"]).to_pydict()
    same += sum(a == b for a, b in zip(t["text"], t["text_original"])); tot += len(t["text"])
print("text == text_original on 6 row groups:", same, "of", tot)
