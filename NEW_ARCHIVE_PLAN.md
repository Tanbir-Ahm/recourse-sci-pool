# Plan: fetching post-May-2017 judgments from the court's newer archive (`/supremecourt/...`)

Written 2026-10-21 after the owner sent three links (two distinct) for January 2018. Everything marked [Certain] was observed in this session; nothing here has been run as a crawl. No new routine is created by this file (needs the owner's say-so).

## 1. What the three links showed (probed 2026-10-21, 14 requests in all, 2 s apart, User-Agent of the existing crawler)

| Link | Result |
|---|---|
| `/supremecourt/2013/13533/13533_2013_Judgement_05-Jan-2018.pdf` (sent twice) | 200, `application/pdf`, 80,188 bytes, 5 pages, typeset text layer (no images). *Leena Vivek Masal v. State of Maharashtra*, Criminal Appeals 9, 10, 11 of 2018, decided 5 Jan 2018 (three appeals in one judgment). |
| `/supremecourt/2015/1383/1383_2015_Judgement_08-Jan-2018.pdf` | 200, PDF, 77,762 bytes, 16 pages, typeset text. *State of Himachal Pradesh v. Raj Kumar*, Criminal Appeal 31 of 2018, 8 Jan 2018. |

[Certain] Both links work from this environment, and the files are the court's own typeset judgments (reportable and non-reportable).

[Certain] *Raj Kumar* (8 Jan 2018) is already in the bucket; *Leena Vivek Masal* (5 Jan 2018) is **not**: the bucket lists only three judgments for 5 Jan 2018 (Dinesh Bhai Patel, National Kamgar Union, Inox Wind). So the newer archive holds at least one judgment the bucket lacks, which fits the 77% bucket coverage for 2018 to 2025.

## 2. What the URL is made of, and why it cannot be counted through

`/supremecourt/<year>/<diary no>/<diary no>_<year>_<Judgement|Order>_<DD-Mon-YYYY>.pdf`

- The old archive was one running number (`judis/<id>.pdf`), so the crawl just counted up. This one needs **three facts per judgment: the diary number, the diary year and the exact decision date**. A wrong date answers 200 with an empty `text/html` body (6 Jan and `05-JAN-2018` both did), the same "empty ID" signal the old crawl classified as a gap. The folder URL answers 403, so there is no directory listing. The case-insensitive form of the month does not work: write `Jan`, not `JAN`.
- [Certain] The same pattern serves **orders** (`..._Order_05-Jan-2018.pdf` returned the one-page record of proceedings for the same matter). A crawl must ask for `Judgement` only.
- [Certain] The diary number is **not** the case number printed in the judgment (13533/2013 is SLP(Crl) 4678 of 2013; 1383/2015 is SLP(Crl) 1204 of 2015) and **not** derivable from the bucket's CNR (Raj Kumar's CNR carries 336; its diary number is 1383). The bucket's metadata has no diary number.
- [Likely] Brute force is not workable: a decision date can concern a diary number from any filing year, with tens of thousands of numbers per year, for several hundred decision dates a year. That is millions of requests per month of judgments, and it would be impolite to the court's server. Do not do it.

So the earlier routine (count up from an ID) has no equivalent. What is needed is a **list of (year, diary no, date)** from somewhere.

## 3. Where the list can come from (decision needed from the owner)

1. **The owner (or a helper) supplies links in batches**, as in this message. Works today; slow; the easiest first step to prove the pipeline end to end. [Certain it works for these two]
2. **The court's own judgment list by date**, which presumably produced these links. [Guessing] I could not reach `www.sci.gov.in`, `main.sci.gov.in` or `digiscr.sci.gov.in` from this environment (no connection at all; the network policy blocks them), and I do not know whether those pages need a CAPTCHA. If they do, we do not get around it (standing rule in `RUNBOOK.md`). If the owner can say which page gave him the links, I can say whether it is workable.
3. **A third-party list** (for example Indian Kanoon) is not a source of diary numbers as far as the repo shows; no step here relies on it.

**Question for the owner: which page or tool did the three links come from?** That one answer decides whether this is automatable.

## 4. The pipeline, once a link list exists (reuses the existing code)

| Step | What | Reuse |
|---|---|---|
| A. Intake | A text file of links, one per line. Reject anything not matching the pattern above or containing `_Order_`. De-duplicate (the owner's list already held one link twice). Store in `new_archive/links/` with the date received. | new, small |
| B. Fetch | Polite fetch, 1.5 s pause, 2 workers at most, stop on 403/429/redirect/HTML (no workarounds). One request per link, no date guessing. | `sci_crawl.classify_response` as is. These PDFs start `%PDF-` with no 4-byte prefix and arrive with a matching Content-Length, both cases it already accepts; an empty 200 is "gap" |
| C. Extract | PyMuPDF text, then delete the PDF; keep text, page count, size, sha256 of the PDF and the source URL, as the crawl did. | existing shift code; the ledger key is the URL, not an ID, so the shard layout (250 IDs a block) needs a small variant |
| D. De-duplicate | (1) by sha256 and by `(year, diary no)` inside the list. (2) Against the crawl and the bucket by decision date plus party names, with the matcher in `coverage/bucket_match/` (decision date is in the bucket's `worklist.csv.gz`). A judgment that decides several matters (Masal: three appeals) can have **several diary numbers pointing at one judgment**; keep one. | `coverage/bucket_match/` |
| E. Clean | Remove the "Digitally signed by ... Signature Not Verified" block and "Page No. n of m" lines; the bucket's margin letters do not appear here (typeset, not scanned). Check on 20 PDFs before trusting. | `sci_bucket.clean_text()` as a start |
| F. Feed | Mark the source as a new third source ("court archive, newer path") beside crawl and bucket; index through `sci_index.py`; run the mention finder, rules and second reader as for any judgment. | existing |
| G. Report | Count: links received, fetched ok, empty (wrong date), not a judgment, already held (crawl / bucket), new. Say how many of the new ones are in the Overruled Register or on a card. | new, small |

Rules that carry over unchanged: nothing here says a case is good law; text only is stored, PDFs are not kept; STOP-file kill switch; source acknowledgement (Supreme Court of India) kept with anything reproduced; no merge to `main`, no pull request and no routine without the owner's say-so.

## 5. Proposed first run (small, free, reversible)

1. The owner sends 20 to 50 more links across 2018 to 2025, mixed on purpose: some in the bucket, some not, at least one 2024 or later (the court's own 2024 on-wards judgments carry no law-report table, which matters for the checker).
2. I run steps A to E on them and report: how many the bucket also holds, how many are new, whether the text is cleaner or worse than the bucket's, and any 403 or 429. Cost: only the court server's bandwidth; no API spend.
3. On that evidence the owner decides whether to ask someone for a bulk list (section 3), and only then whether to schedule a routine.

## 6. What this plan does not claim

- It does not say how many 2018+ judgments the court's archive holds that the bucket lacks. Only one is known (Masal), from one sampled date. Indian Kanoon's list suggests about 1,970 for 2018 to 2025 [Likely], but that figure includes things the court may not post.
- It does not know whether the newer archive is complete, whether the file names ever change, or whether the court's terms allow automated fetching. The last of these should be checked by the owner before any bulk run.

## 7. Update, second batch (owner's message, same day): source page named, five links from 2019 to 2024

**The source page** is `https://www.sci.gov.in/judgements-judgement-date/` (judgments by date). [Certain] It cannot be read from this environment: the environment's network policy refuses the host (`CONNECT tunnel failed, response 403`). Whether the page can be read by a program, or sits behind a CAPTCHA, is **not known**; I have not seen it. If the owner adds `www.sci.gov.in` under Allowed domains (cloud environment menu, Network access, Edit), I can look at what the page returns. If it asks for a CAPTCHA or a login I stop there, as `RUNBOOK.md` requires, and the plan stays "owner supplies links".

**A second URL form.** From 2019 on the file name carries three more numbers:
`/supremecourt/<year>/<diary no>/<diary no>_<year>_<a>_<b>_<c>_Judgement_<DD-Mon-YYYY>.pdf`, for example `558_2019_9_1502_17589` and `3781_2014_13_1501_17658`. [Certain] Two probes with the 2018-style short form and with a wrong diary folder both came back as empty 200 answers, so every part of the name has to be right. [Likely] `b` is the item number (1501 or 1502 in four of the five links); [Guessing] `a` and `c` are a court or list number and a running record number: `c` rises with the date (17,589 in Oct 2019; 30,814 in Oct 2021; 47,540 in Oct 2023; 56,561 in Oct 2024), but it still cannot be used without the diary number. So the conclusion in section 2 holds even more firmly: **no enumeration, a list of links is needed.** The intake step must accept both forms (the short form for early 2018, the long form after) and treat the whole path as the key.

**The five links** (all fetched once, 2 s apart): all five return 200, `application/pdf`, 75 KB to 594 KB, 11 to 43 pages, with a text layer. [Certain] Only n4 and n5 carry an embedded image each (likely a seal or signature [Guessing]); none is a scan.

| Date | Case (from page 1) | In the bucket? |
|---|---|---|
| 18 Oct 2019 | State of Bihar v. M/s Riga Sugar Co. (Civil Appeals 7951 and others of 2019) | **No** (bucket has 3 other judgments that day) |
| 21 Oct 2019 | Om Parkash v. Amar Singh (Civil Appeals 8175-8176 of 2019, with a contempt petition) | **No** (bucket has 2 other judgments that day) |
| 22 Oct 2021 | Union of India v. Ms. A. Shainamol, IAS (Civil Appeals 11480-81 of 2018) | Yes |
| 10 Oct 2023 | Vikrant Kapila v. Pankaja Panda (Civil Appeal 5355 of 2023) | **No** (bucket has 6 other judgments that day) |
| 16 Oct 2024 | IDBI Bank v. Ramswaroop Daliya (SLP(C) 8159-8160 of 2023) | Yes |

[Likely] 3 of 5 are missing from the bucket (matched by decision date and party names by eye against `worklist.csv.gz`). With the Masal link, 4 of 7 judgments sent so far are missing from the bucket. That is a small sample and the links may have been picked because they were missing, so it is **not** a rate; it only confirms the gap is real and appears in recent years too, including 2023.

**What changes in the plan:** nothing in steps A to G; the intake pattern is widened to the long form. The first small run can use these seven links as they stand: fetch, extract, clean, compare with the bucket, report. Not done yet; waiting for the owner to say go.

## 8. Update: `www.sci.gov.in` allowed by the owner, then refused by the court's own server (2026-10-21)

After the owner allowed the host, two requests (the judgments-by-date page and `robots.txt`, 2 s apart, with the crawler's honest User-Agent) reached the court's server and both got **HTTP 403 "Access Denied"** from its content-delivery layer (Akamai, `AkamaiGHost`). [Certain] This is a block by the court's side, not by our sandbox. Following `RUNBOOK.md` ("never try to get around a block, CAPTCHA, login page or access denied"), nothing further was tried: no changed User-Agent, no retries, no other route to the same page. [Guessing] Such layers often refuse automated clients and cloud addresses; the cause here is not known.

Consequence: the list of links cannot come from this environment. The plan stays "owner supplies links" (section 5), or a person copies the day's links from the page in a normal browser. `api.sci.gov.in` PDF links keep working from here.

## 9. Strategy to avoid hand-collecting links for 2017 to 2026 (owner: "too much manual work", 2026-10-21)

Principle: shrink the list, then find the feed. Nothing here gets around the court's block (section 8).

**A. Find the data behind the listing page (owner, about 5 minutes, then automatic).** In a normal browser open the judgments-by-date page, press F12, open the Network tab, run one search for a one-week range, and send me the address and parameters of the request that returned the results (not cookies, tokens or the CAPTCHA answer). Three outcomes:
1. The request goes to `api.sci.gov.in` (which answers us, section 1) and needs no CAPTCHA or token: I page through it politely (1.5 s pause, 2 workers, STOP file) and get every link for 2017 to 2026, with diary and extra numbers, automatically. [Guessing] that this is the case; the page was never seen.
2. It needs a CAPTCHA or a browser token: stop. Go to B.
3. It goes to `www.sci.gov.in` itself: blocked for us (section 8). Go to B.

**B. Owner's browser as the hand, once per range, not per link.** If the page accepts a date range, the owner saves each results page (Ctrl+S, "Webpage, HTML only") into `inbox/` and I read the links out of the saved files offline. A month or a quarter per file, so 2018 to 2026 is a few dozen files, not thousands of links. A small console snippet that collects the links on the page is possible only after I have seen one saved page. The owner should check the court's terms first.

**C. Fetch only what the checker needs (cuts the list by roughly 5 to 20 times).**
1. Only judgments the bucket lacks: about 1,970 for 2018 to 2025 and about 770 for 2026 [Likely; from Indian Kanoon's yearly counts in `coverage/COVERAGE_NOTE.md`, which may count orders or duplicates].
2. Criminal law first: the index keeps criminal judgments only, so a non-criminal judgment would be dropped anyway.
3. The register's own demand is small: of the 59 post-2015 overruling entries, only 1 (row 43) has the later judgment missing from our text, and the correcting judgments missing in `review_results/2026-10-09_index_gap_sizing/` are mostly older ones. So for the Overruled Register the post-2017 gap hardly matters [Likely]. It matters for the lawyer research mode (recent authority), not for the "is this overruled" warning.
4. Demand-driven list: post-2017 judgments that our corpus or cards cite but do not hold (neutral citations such as "2023 INSC 123", and case names). I can compute this from the corpus after the 15-minute rebuild (`IK_PLAN.md`); the owner then looks up a few dozen cases, not thousands.
5. Hypothesis to test, not a finding: the bucket is mostly judgments printed in the law reports, so what is missing is mostly non-reportable. In the seven judgments sent so far the missing ones were 3 non-reportable and 1 reportable of 4; the three held were all reportable. [Guessing, n = 7]. Test: count "NON-REPORTABLE" on page 1 of bucket judgments for 2018 to 2025. If the bucket holds almost none, the missing set is the non-reportable half, which is less likely to overrule anything.

**D. Not recommended without the owner's say-so.** A paid scraping service that returns diary numbers (it scrapes the court site, costs money and has its own terms; found by search, not checked), and third-party libraries that claim to read the court's feed (not inspected, not trusted).

**E. Keep the bucket as the base.** It is refreshed about every two weeks (`BUCKET_RUNBOOK.md`); direct fetches then only cover what it never gets.

Order of work: A (owner, 5 minutes) while I run the small pass on the seven links; then C4 and C5 (no spend); B only if A fails.

## 10. Result of step A (owner sent the request behind the listing page, 2026-10-21)

- The search is a POST to `https://www.sci.gov.in/wp-admin/admin-ajax.php` (WordPress), action `get_judgements_judgement_date`, fields `from_date`, `to_date` (DD-MM-YYYY), `language`, and a set of form-protection fields: a CAPTCHA answer (`siwp_captcha_value`; a simple sum in this case), a per-page nonce, a one-time token, a form time and a signature. The owner's one-day test was 18 to 19 Aug 2022. (The token, nonce and signature values the owner pasted are session values; they are deliberately **not** recorded here and were not used.)
- Consequences [Certain]: the endpoint is on `www.sci.gov.in`, which refuses our client (section 8), and it is guarded by a CAPTCHA and a signed, time-stamped form. This is outcome 2 and 3 of section 9A. **No automated route exists for us, and none will be built**: solving the CAPTCHA by program or replaying the tokens would be getting around the court's guard (`RUNBOOK.md`, standing rule).
- What remains is route B, with the CAPTCHA answered by a person: the owner runs a search in his own browser and hands me what the page returned. The effort is per search, not per link. Open questions for him to test: the longest date range the form accepts (one month? one year?), and whether the results are paginated.

## 11. Result of the first real pass (1 to 10 Jan 2019; details in `new_archive/2019-01-01_to_10/README.md`)

The owner's manual route works: one search with a CAPTCHA he answered, one snippet, 53 links. 41 English judgments were fetched cleanly (typeset, not scans); 11 translations and 1 link without a diary number were skipped. **9 of the 41 (22%) are not in the bucket, 5 of them criminal; all 4 non-reportable judgments were among the missing.** The owner's list also lacks 2 judgments the bucket holds, so the page copy is not guaranteed complete.

Still open: the longest date range the form takes, whether results are paginated (the two missing judgments may point to it), and the court's terms. Not done: storing the extracted text, de-duplication against anything but the bucket, cleaning, feeding the index.

## 12. Result for a full month (January 2019; `new_archive/2019-01/README.md`)

The form takes 30 days. 150 links: 115 English judgments (all fetched, typeset, no scans), 34 translations, 1 without a diary number. **32 of the 115 (28%) are not in the bucket: all 15 non-reportable ones, and 18 of 34 criminal ones.** The copied list also lacks 6 judgments the bucket holds, so the court page (or the snippet) under-lists. The bucket holds at most about 74% of the month's judgments.

Cost of the manual route, as measured: the fetch takes about 4 seconds per judgment; the owner's work is one search and one snippet per month. Suggested order: newest first (2026, then 2025, 2024, ...), because the bucket is weakest there (2026: 22% of Indian Kanoon's count, 2025: 63%) and recent law is what the lawyer research mode needs. Rough size: about 10 searches for 2026, 12 for each earlier year.

## 13. Result for January 2026 (`new_archive/2026-01/README.md`)

107 English judgments, all fetched, all typeset. **64 of 107 (60%) are not in the bucket**, including all 24 non-reportable ones and 38 of 80 reportable ones. For this month the bucket holds at most about 40%. So for 2026 the direct route is not a gap-filler but the main source: the bucket's 2026 folder has only 214 judgments for the whole year to 12 August. One bucket judgment (State of U.P. v. Anurudh) is not in the owner's list, so the copied list is not complete for 2026 either (1 of 108).

Run time: about 8 seconds per judgment this time (14 minutes for 107). Roughly 100 judgments a month means 15 to 20 minutes of fetching per month, so a year is about 3 to 4 hours of unattended fetching, in blocks.

## 14. Results for February to June 2026 (`new_archive/2026-02_to_06_SUMMARY.md`)

504 further links, all English judgments, all fetched (about 65 minutes unattended, no blocks). With January: **611 judgments for January to June 2026, 424 (69%) not in the bucket, including all 129 non-reportable ones.** The bucket holds at most about 31% of the six months and its share falls by month (40% in January, 22% in May). For 2026 the direct route is the main source. The owner's copied lists were almost complete (5 bucket judgments absent from 616).

The catalogue (`catalogue.csv`) now has 733 rows. Names were improved this round (suo motu "In Re" matters, "and others" on its own line, many numbered parties); 1 row has no name and 5 have no second side (suo motu). Still not done: storing the extracted text, cleaning it, feeding the index, July to October 2026 and 2018 to 2025, de-duplication against anything but the bucket.

## 15. Results for July to October 2026 (`new_archive/2026-07_to_10_SUMMARY.md`); 2026 to date is complete

451 further links, all English judgments, all fetched (about 60 minutes, no blocks). **2026 to 16 October: 1,062 judgments.** Of the 801 decided on dates the bucket covers (to 12 August), **591 (74%) are not in the bucket**; the other 261 are newer than the bucket's last date. The bucket holds 12% of July and early August.

New check: the court's neutral citations (2026 INSC 1 to 1,149) are a running count. The catalogue holds 1,055 of them, so the owner's lists are about 92% complete; 94 numbers are missing, 5 of them in the bucket. They are listed in `2026_missing_insc_numbers.csv` with the dates to look at. The catalogue has 1,184 rows.

Decision for the owner: 2026 is now the main source and the direct route works. The next years (2025 down to 2018) are 12 searches a year each, with the bucket better there (about 77% overall, 63% for 2025). Neutral citations run from 2023 only in these PDFs, so the completeness check works for 2023 onwards.

## 16. Decisions of 2026-10-21 (owner) and the text store

- The owner checked the court's terms on automated fetching and approved fetching the rest (his statement). He is collecting 2018, 2019, 2020 and 2017 (from 5 May 2017) himself.
- Fetching runs one year at a time, never in parallel: 2025, then 2024, 2023, 2022, 2021, each month's results pushed as it finishes.
- **Text store (owner's say-so: "store the extracted text, compressed, as monthly files on a new data branch such as claude/sci-court-newer").** Branch `claude/sci-court-newer`: `shards/YYYY-MM.jsonl.gz` (raw text, one judgment per line, with the catalogue fields); `store_text.py` builds it and is idempotent; a watcher stores each month as its results appear. 1,184 judgments stored so far in 15 MB (about 13 KB a judgment, so roughly 150 MB for 11,000). Stored for every fetched judgment, bucket-held ones included, so the two texts can be compared. Nothing is cleaned yet and nothing from the branch has gone into the index, checker or register.

## 17. Fetching plan to 2017 and the reminder (owner, 2026-10-21)

Order of work (owner: "complete the fetching till 2017 cleanly and completely as planned"): (1) fetch every English judgment in the uploaded link lists of 2017 (from May) to 2025, one year at a time, newest first after 2025; (2) when the queue ends, check that every English link has a result: list the rows that are not `ok` (error, truncated, empty), fetch each once more, and report any still failing; (3) check each month's count against its link list and each shard against its results; (4) only then report and rebuild the catalogue. **After that, remind the owner of the 74 links with no diary number and the two fixes (FOLLOW_UPS 1o).** The snippet for fix 1: it prints each broken row's text and every link inside the row (run on June 2017; untested because the page was never seen):

    (()=>{const out=[];document.querySelectorAll('a[href*="supremecourt//"]').forEach(a=>{let b=a;for(let i=0;i<6&&b.parentElement;i++){b=b.parentElement;if(b.innerText&&b.innerText.includes('Diary Number'))break}out.push((b.innerText||'').replace(/\s+/g,' ').trim()+' || '+[...b.querySelectorAll('a')].map(x=>x.textContent.trim()+' -> '+x.href).join(' | '))});console.log(out.length+' broken rows');copy(out.join('\n'))})()
