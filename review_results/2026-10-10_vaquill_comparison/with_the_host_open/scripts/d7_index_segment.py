"""Writes the full member index of one segment (file name -> data offset, stored size, real size, sparse map) to JSON. Args: scripts_dir url base size out.json"""
import sys, json, time
sys.path.insert(0, sys.argv[1])
import qd_read as Q
url, base, size, out = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
t = time.time(); raw = {}
for name, hdr, data, stored, real, sparse in Q.walk(url, base, size):
    raw[name.replace("snapshot/files/", "")] = [data, stored, real, sparse]
json.dump(raw, open(out, "w"))
print("indexed", len(raw), "files in", round(time.time() - t), "s ->", out, flush=True)
