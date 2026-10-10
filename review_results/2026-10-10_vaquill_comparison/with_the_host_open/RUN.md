# How the 2026-10-10 "host open" checks were run (all read-only; scratch = the session's scratchpad)

Network: `oss-data-in.vaquill.ai` must be in the environment's allowed domains. Its firewall answers 403 to Python's default User-Agent; `scripts/rangefile.py` and `scripts/qd_read.py` send an identifying one. Run every script as `python3 -P <script> ...` from a directory that holds no data files.

| Step | Script and arguments | Output |
|---|---|---|
| 1. Non-text columns of the Supreme Court parquet (15 s) | `read_meta.py` (writes `meta.parquet` to its working dir; edit the path) | `meta.parquet` (22 MB) |
| 2. Overview, English rows, years and gaps | `a1_overview.py meta.parquet`, `a2_english.py meta.parquet`, `a3_years_gaps.py meta.parquet` | `results/overview_*.txt`, `years_and_gaps.txt` |
| 3. English chunk text (45 s) | `b2_read_text.py <scripts_dir> en_text.parquet` | `en_text.parquet` (404 MB) |
| 4. Chunk clutter, ours against theirs | `b3_chunk_quality.py en_text.parquet` | `results/chunk_quality.txt` |
| 5. Text against ours (448 judgments) | `c1_compare.py meta.parquet en_text.parquet corpus.sqlite out.json 450`; `c3_oov.py ... <sample.json> out.json <scripts_dir>`; `c5_glue.py` (same arguments) | `results/text_agreement_summary.txt`, `oov_*`, `glue_*` |
| 6. Snapshot structure | `d1_tar_walk.py <snapshot url> <bytes> 40` (outer tar), `d7_index_segment.py <scripts_dir> <url> <base> <size> out.json` (one segment, about 4 minutes) | segment indexes |
| 7. Extract all Supreme Court points of a segment | `d8_extract_shard.py <scripts_dir> <url> <segment index json> <out_prefix>` (about 1 minute each; writes payloads with text and float32 vectors) | `sc_shard*_payload.jsonl.gz`, `_vecs.npy`, `results/snapshot_inventory.json` |
| 8. Which model made the vectors (paid, about $0.003) | `e1_identify_model.py <dir with sc_vecs.npy and sc_payloads.json> 200000` (a sample pulled with `d6_pull_sc_sample.py`, not included; the output is in `results/identify_model_output.txt`) | cosines |
| 9. Payload fields and treatment tags | `e2_payload_stats.py`, `g1_treatment.py` | printed |
| 10. Retrieval test 1 (dense only, same judgments; about $0.0002) | `f0_map.py meta.parquet corpus.sqlite ab_mapping.json` then `f1_ab.py <dir> sc_shard0,sc_shard1,sc_shard2,sc_shard3,sc_shard3b ab_result.json` | `results/ab_result.json` |
| 11. Retrieval test 2 (same text, two models; paid, 1.06 million tokens, about $0.13) | `f2_same_text.py <dir> <shards> out.json 1500000` | `results/same_text_result.json` |

`f0_map.py` reads only the tuning half's key entries (the sealed half is dropped before anything else runs). `corpus.sqlite` is the session's unified text store (not in the repository). The vectors and payloads (about 1.5 GB) are not kept in the repository.
