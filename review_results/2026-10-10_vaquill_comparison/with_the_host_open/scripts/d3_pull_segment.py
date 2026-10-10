import sys, json
sys.path.insert(0, sys.argv[1])
import qd_read as Q
URL = "https://oss-data-in.vaquill.ai/qdrant/legal_corpus_v2/shard-0/legal_corpus_v2-shard-0-2026-08-22-12-38-53.snapshot"
want = ["vector_storage-dense/vectors/config.json", "vector_storage-dense/vectors/chunk_0.mmap", "payload_storage/tracker.dat", "payload_storage/page_0.dat", "payload_storage/bitmask.dat",
        "payload_storage/gaps.dat", "payload_storage/config.json", "mutable_id_tracker.mappings", "mutable_id_tracker.versions", "segment.json", "version.info"]
out = sys.argv[2]
import os; os.makedirs(out, exist_ok=True)
for name, hdr, data, stored, real, sparse in Q.walk(URL, 0, 34055680, want=want):
    b = Q.read_member(URL, data, stored, real, sparse)
    fn = os.path.join(out, name.replace("snapshot/files/", "").replace("/", "__"))
    open(fn, "wb").write(b)
    print(f"{name}: stored {stored:,} real {real:,} sparse segments {len(sparse)} -> {fn.split('/')[-1]}")
print(open(os.path.join(out, "segment.json")).read())
print(open(os.path.join(out, "payload_storage__config.json")).read())
