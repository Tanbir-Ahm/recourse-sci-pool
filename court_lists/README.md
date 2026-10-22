# The Gauhati High Court's own monthly lists, 2010 to 2017

`pdf/`: the 95 monthly list PDFs from https://ghconline.gov.in/index.php/judgments-up-to-2017/ (December 2010 is missing: the court's link is dead). `court_list_rows.csv.gz`: all 7,412 judgments they name, parsed. `by_month/YYYY/YYYY-MM.csv`: the same rows month by month, with
- `court_url`: the judgment on the court's own site (the primary source; reachable only from the owner's laptop, not from the cloud machine);
- `court_file_received`: `no` until the owner's download of that file has been read and stored (then `yes`);
- `backup_in_bucket` / `backup_bucket_key`: whether the open bucket holds the same case (matched by decision date and case number), and its key: the backup copy.
Policy (owner, 2026-10-22): the court's own file is the main text; the open bucket's copy is the backup, used only where the court's file has not been received.

## Policy update, 2026-10-22 (owner: "Yes, bucket-first, use the zip route for the 888")

The bucket's text is the main text wherever the bucket has the judgment. The court's own file is fetched (by the owner, via zips) only for the 888 criminal-subject judgments the bucket lacks. This replaces the earlier "court file is the main text" rule. Stored bucket text is hard-wrapped at 80 columns and needs a cleaning step before embedding.
