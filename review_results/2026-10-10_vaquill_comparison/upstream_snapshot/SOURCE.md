# Upstream documents quoted in ../README.md

Source: https://github.com/Vaquill-AI/open-india-law (branch `main`), fetched 2026-10-10 02:46 to 02:47 UTC from raw.githubusercontent.com. The commit was not recorded; the sha256 of each saved file is in `SHA256SUMS`, so a later change upstream is detectable.
Saved unmodified (the original paths use `/`; here they are joined with `_`):

| Saved as | Original path |
|---|---|
| `README.md` | `README.md` |
| `COVERAGE.md` | `COVERAGE.md` |
| `coverage.yml` | `coverage.yml` |
| `data_LICENSE.md` | `data/LICENSE.md` |
| `data_QDRANT_RESTORE.md` | `data/QDRANT_RESTORE.md` |
| `data_coverage_02-judgments-by-year.csv` | `data/coverage/02-judgments-by-year.csv` |
| `data_coverage_09-held-vs-embedded.csv` | `data/coverage/09-held-vs-embedded.csv` |
| `scripts_pipeline_UNIFIED_CHUNKING_SCHEMA.md` | `scripts/pipeline/UNIFIED_CHUNKING_SCHEMA.md` |
| `vaquill_sc_by_year.json` | derived by us: the "Supreme Court of India" column of `data/coverage/02-judgments-by-year.csv`, year to count (1950 to 2025, sum 34,954) |

Licence as stated upstream (README, "Licensing and commercial use"): scripts Apache-2.0; data and compilation CC BY 4.0, attribution required ("Structured Indian primary-law data from the Open India Law corpus by Vaquill AI (https://github.com/Vaquill-AI/open-india-law), used under CC BY 4.0."); the underlying legal text is a government work. These copies are kept as evidence for the comparison, not redistributed as a dataset.

The `parquet` files, the Hugging Face dataset and the Qdrant snapshots were **not** reachable from this environment (`oss-data-in.vaquill.ai` and huggingface.co answer HTTP 403), so nothing here was read from them.
