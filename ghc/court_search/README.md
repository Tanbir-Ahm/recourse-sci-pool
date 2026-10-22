# Court's own list of Guwahati judgments (ghcservices.assam.gov.in), collected in the owner's browser

Owner's decisions (2026-10-22): the court's own "Judgements / Orders" search is used to get the **list** of judgments (case, date, neutral citation, link); the **text** comes from the open bucket where it holds the case (matched by neutral citation, else case number and date), and from the court's own PDFs (owner's laptop) only for judgments the bucket lacks. The owner read the site's terms and allowed the run (2026-10-22). Nothing is fetched from this environment (the host is blocked here).

Findings from the owner's searches, 01-01-2018 to 31-01-2018, Judgement: Category All 474 entries, Category Criminal 474 (the same rows: the Criminal choice does not filter), Category Civil 422. So criminal cases are picked here by case number, not by the dropdown. The page shows at most 1,000 rows per search.

`ghc_month_loop.js` runs in the browser on the empty form: one month per search, one search every ~8 s, nothing in parallel; stops on a CAPTCHA, block, error or timeout; splits a window that reaches 1,000 rows; saves one TSV per year. Tested only against a mock page (`test_mock/`, needs jquery and datatables.net from npm and playwright-core) that imitates the form and a DataTables result table; **not yet run on the real page**.
