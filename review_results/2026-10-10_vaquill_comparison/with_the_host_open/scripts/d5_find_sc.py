"""For each segment of one shard snapshot, sample a few payloads to see which courts' points it holds."""
import sys, json, struct, collections, time
sys.path.insert(0, sys.argv[1])
import qd_read as Q
import lz4.block
URL = sys.argv[2]
SEGS = json.loads(sys.argv[3])            # [[base_offset, size], ...] of the segment members in the outer tar
NS = int(sys.argv[4])
for base, size in SEGS:
    t0 = time.time()
    m = index_segment_ok = Q.index_segment(URL, base, size)
    pst = m.get("payload_storage/tracker.dat"); ver = m.get("mutable_id_tracker.versions")
    npts = (ver.real // 8) if ver else None
    if not pst:
        print("segment at", base, "has no payload_storage tracker; files:", list(m)[:6]); continue
    # number of points from the tracker header
    head = pst.read(0, 8); nslots = struct.unpack("<II", head)[0]
    n = min(nslots, npts or nslots)
    idxs = sorted(set(int(i * (n - 1) / max(1, NS - 1)) for i in range(NS)))
    cts, cases = collections.Counter(), []
    for i in idxs:
        rec = pst.read(8 + 16 * i, 16); page, blk, ln, _ = struct.unpack("<IIII", rec)
        if ln == 0: continue
        pg = m.get(f"payload_storage/page_{page}.dat")
        if not pg: cts["(page missing)"] += 1; continue
        raw = pg.read(blk * 128, ln)
        try: p = json.loads(lz4.block.decompress(raw))
        except Exception: cts["(undecodable)"] += 1; continue
        cts[p.get("court_type")] += 1
        if len(cases) < 3: cases.append(p.get("case_id"))
    print(f"segment @{base:>14,} ({size/1e9:5.2f} GB) points~{n:,} | sample court_type {dict(cts)} | e.g. {cases} | {time.time()-t0:.0f}s", flush=True)
