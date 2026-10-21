# claude/sci-court-newer: extracted text of judgments from the court's newer archive

Data branch, text only. Never merge or rebase between this branch and `main` or the other data branches (`claude/sci-pool` = the old crawl, `claude/sci-bucket` = the open bucket). Code that builds it lives on `claude/elegant-lovelace-xb15i2` (`new_archive/store_text.py`, `new_archive/first_pass.py`, `new_archive/build_catalogue.py`); the plan and the per-month results are in `new_archive/` there.

**Source.** Judgments of the Supreme Court of India, fetched from the court's own site (`https://api.sci.gov.in/supremecourt/...`) from link lists the owner collected in his browser, then read from the PDFs. Keep the court's source link and the attribution "Supreme Court of India" with anything shown or reproduced. The owner has checked the court's terms (his statement, 2026-10-21). PDFs are not kept; only text.

**Layout.** `shards/YYYY-MM.jsonl.gz`: one file per decision month, one JSON object per line, one judgment per object. `state/processed.json` lists the result files already stored.

**Fields.** `pdf_url` (the court's link, unique key), `diary_no`, `decision_date`, `case_name` / `petitioner` / `respondent` / `case_number` / `neutral_citation` (all read from page 1 by rules; a multi-matter judgment shows only its first matter; suo motu matters have no respondent; `neutral_citation` appears on 2023 and later PDFs), `reportable` (REPORTABLE, NON-REPORTABLE or unmarked, as printed), `pages`, `sha256` (of the PDF), `in_bucket` (`yes` the open bucket holds the same judgment; `no` it does not; `beyond` the judgment is newer than the bucket's last date, 12 Aug 2026), `bucket_title`, `source`, `fetched_on`, and `text`.

**Text.** Raw, as extracted by PyMuPDF; pages are joined by a form feed (`\f`). **Nothing is cleaned**: the court's "Digitally signed" blocks, page-number lines and headers are still in it. These PDFs are typeset (no scans in the samples read so far), but accuracy has not been tested against ground truth. A judgment the bucket also holds is stored here too, so the two texts can be compared.

**What this does not say.** Nothing here says a judgment is good law or has not been overruled. Nothing from this branch has been fed to the index, the checker or the Overruled Register.
