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
