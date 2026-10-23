# The court's own list of Guwahati judgments, 2018 to 2026 (ghcservices.assam.gov.in "Judgements / Orders", Judgement, Category All)

Collected by the owner's browser with `ghc/court_search/ghc_month_loop.js` on 2026-10-22/23 (106 months, no CAPTCHA, no window reached the page's 1,000-row cap). `ghc_rows_YYYY.tsv`: window, serial, row text (title, neutral citation, decision date, case number), link to the court's PDF (`pdfWatermark.php?file=...`).

`criminal_judgments_2018_2026.csv`: the rows whose case number is a criminal type (Crl.A, Crl.Pet., Crl.Rev.P., jail appeals, criminal transfer petitions, etc.; AB, bail, IA and MC types left out), matched to the open bucket by case number and decision date (the bucket's date is one day EARLIER than the court's for 2024 and 2025; matched within one day). Columns `bucket_cnr`, `bucket_file`, `bucket_bench`, `bucket_year` give the bucket document.

Caveat: the court's "Judgement" label is narrower than "reasoned judgment": in a read of 150 criminal-type bucket documents NOT on this list, about a third had a JUDGMENT heading or a body of 5,000+ characters (see `ghc/POST2017_SAMPLE.md`). The Criminal choice in the court's Category box does not filter (same rows as All).
