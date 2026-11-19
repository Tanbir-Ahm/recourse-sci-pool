# The Reading Desk: a website around the checked-reading pipeline

A small web app (a Python server that uses only the standard library and Pillow, plain JavaScript in the browser) around `ocr_tests/pipeline.py`. A person signs in, uploads page photos or a PDF,
says the language and whether the pages are typed or handwritten, confirms that nothing in them identifies a minor or the victim of a sexual offence, sees an estimate, and starts
the reading. The result screen shows, for each page and for the joined document:

- the English to read, with the reader's marks kept as marks (a crossed-out word, a word written above the line, a doubtful reading, both values where the two readings disagree, a sentence the sense check underlined);
- **Read these first**: the places to look, each one a click away from the passage it is about;
- the traffic light and why (a reading order, never permission to skip a page);
- the page picture beside the English, the glossary notes, the must-check list, what each reading said;
- a Word file, the full report (PDF when Node and Playwright are installed, otherwise HTML), and the marking sheet;
- a tick-box per page, "I have read this page against the original", that records who and when. It records who looked; it does not say the page is correct.

Every output carries **"Machine draft. Not a certified translation."** Nothing on the site says a page is right. A person who reads the language reads every page.

The design (left rail, the amber "Read these first" box, the two-pane page) follows the clickable prototype made earlier; the layout of another company's product was not copied.

## Run it on your own computer

```
pip install -r ocr_tests/web/requirements.txt    # Pillow, and python-docx (only for the Word file); checked in a clean virtual environment
export GEMINI_API_KEY=...                  # the model key: only in the environment, never in a file, never printed
export RD_USERS="alice:a-long-access-code" # a code is at least 10 characters; several users: "a:code1,b:code2"
python ocr_tests/web/server.py --port 8080 # then open http://127.0.0.1:8080
```

Windows PowerShell: `$env:GEMINI_API_KEY="..."; $env:RD_USERS="alice:a-long-access-code"; python ocr_tests\web\server.py`.

To show the site inside another page (a preview pane), and only then, add `RD_ALLOW_FRAMING=1 RD_COOKIE_SECURE=1 RD_COOKIE_SAMESITE=None` (the browser must be using HTTPS or localhost) and, behind a proxy that rewrites the host name, `RD_TRUST_PROXY=1 RD_ALLOWED_ORIGINS=*`. These weaken the protection against another site framing it or starting a job from it, so do not use them for real papers on an open address.

`python ocr_tests/web/server.py --dev` signs nobody in and only answers to `127.0.0.1` (use it on your own computer only). `RD_PIPELINE=stub` makes every reading invented text with no model and no cost
(the **Try the demo** button does this for its three invented pages whatever the setting is).

What else is used, and what happens without it:

| Needed for | Tool | Without it |
|---|---|---|
| PDF files | `poppler-utils` (`pdfinfo`, `pdftotext`, `pdffonts`, `pdfimages`, `pdftoppm`) | PDF upload is switched off; page photos still work |
| Telling a sideways photo from an upright one, matching a PDF's text layer | `tesseract-ocr` with `asm`, `kan`, `hin` data | the model is asked which way up a photo is; a PDF page is read as an image |
| Word file | `python-docx` | the Word button is hidden |
| Report as PDF | Node and the `playwright` package | the report opens as HTML (it is self-contained; print it from the browser) |

## How it works

```
browser ──► server.py ──► one child process per job: pipeline.py ──► run folder
   ▲            │                                                                    │
   └── JSON ◄── results.py (reads the run folder back: lights, flags, notes, English) ◄┘
```

- `server.py` routes, sign-in, upload, limits, downloads. `config.py` reads the `RD_*` settings (the top of that file lists every one). `auth.py` signed cookies and the wrong-code limit.
- `store.py` one folder per job under the data folder (default `~/.reading_desk`, outside the repository): `meta.json`, `in/` (uploads under neutral names), `run/` (pipeline output), `log.txt`. `usage.jsonl` keeps counts and estimated rupees only.
- `runner.py` starts the pipeline, stops it on cancel or timeout, reads its cost from its own ledger, and redacts anything key-like from an error before a person sees it.
- `results.py` turns the run folder into what the page shows. It decides nothing: every light, flag and note was made by the pipeline's checks; the **Read these first** items follow `report.read_first_page` and `read_first_document` line for line.
- `docx_out.py` the Word file. `demo.py` and `stub_pipeline.py` invented pages and a fake reader, so the demo and the tests run the real pipeline end to end with no model.
- `static/` the page (`index.html`, `app.js`, `style.css`): no library, no font and no script from another site; text from the server or a model is never inserted as HTML.

## Money

Reading costs money on your Google account, and **a page costs more the more is written on it**. By the pipeline's own estimate a short handwritten page is about Rs 2 (Rs 0.7 a reading; plan 10ao) and a full printed page of small type is about Rs 11 to 12 (Rs 3.75 a reading, three readings and a check; plan 10i and the first run through this site). **The real bill has run 1.5 to 2 times the estimate** (plan section 10k). The site therefore:

- shows a range, "Rs 2 to 12 a page", before anything is read, and keeps a job a draft until someone presses **Start reading**;
- gives the pipeline a budget ceiling per job (`--budget-inr`: Rs 14 a page plus 4, so that a dense page can finish, and never above what `RD_JOB_BUDGET_INR`, the user's `RD_DAILY_BUDGET_INR` and the site's `RD_MONTHLY_BUDGET_INR` still allow; defaults Rs 40, 150 and 600). It refuses a job whose lowest estimate would pass a limit;
- counts what running jobs hold back, so two jobs started together cannot pass a cap;
- stops a job that reads past its budget and says so; **Continue** resumes it, and readings that finished are not paid for twice.

A first version of this page said "about Rs 3 a page" with a ceiling of Rs 8 a page. The first real reading through the site (a dense printed page) showed both were wrong; they were replaced before anything was committed.

## What protects the papers, and what does not

Done and tested (`tests/test_web.py`, 35 tests):

- nothing but the page itself is served without signing in; a wrong code is limited to 8 tries in 10 minutes per address and per name; the code is compared in constant time;
- the cookie is signed, expires, is `HttpOnly` and `SameSite=Strict` (and `Secure` with `RD_COOKIE_SECURE=1`); signing out ends that cookie on the server too;
- a write needs the site's own header and an `Origin` that matches (a page on another site cannot start a job); dev mode only answers to local names;
- one person cannot see, change or download another person's job (the answer is 404); a job id is 24 random hex characters, checked before it touches a path; page ids in a URL must be ones the run really has;
- an upload is checked by its bytes (PDF, JPEG, PNG, WebP), by size, by page count and by pixel count, stored under a neutral name, and a chunked upload is refused;
- reports and marking sheets are served in a sandbox (no scripts for a report; scripts but no access to the site for a marking sheet);
- files are deleted `RD_RETENTION_HOURS` (default 72) after a job ends, or when the person deletes the job; an unstarted draft is deleted after 6 hours;
- the model key lives only in the server's environment and in the child process; it is not in any file, log line, error text or page.

**Not done. Read this before real client papers go in:**

- **Page images and text go to Google's Gemini service.** Whether a lawyer may send a client's papers there, under Google's terms for the key's plan, the Advocates Act and Bar Council rules and the Digital Personal Data Protection Act 2023 and its 2025 Rules, has not been checked by anyone who built this. The upload screen makes the person confirm it, and the confirmation is recorded with the job. It is not legal advice.
- No encryption at rest, no backup, no malware scan of uploads, no record of who opened what (only who marked a page as read), no password reset, no way to add a user without restarting the server, no payment.
- It serves plain HTTP. For anything beyond your own computer put it behind a TLS proxy (Caddy, nginx) and set `RD_COOKIE_SECURE=1` and `RD_TRUST_PROXY=1`. A connection that stalls holds a thread for up to 60 seconds, so do not expose it to the open internet without a proxy that limits connections.
- The repository this file lives in looked public when last checked, although earlier notes call it private. The site's data folder is outside the repository on purpose; never commit a job, an upload or a report.
- Flags are not placed on the page picture: the pipeline works on text, not on coordinates, so there are no pins on the image (the prototype's pins were a drawing).
- Most testing so far was on Assamese. Kannada and Hindi are offered, but little has been run on them, and the glossary is Assamese only.
- No text-paste translation, no batch screen, no per-user spend history beyond the Usage page.

## Tests

```
python -m unittest discover -s ocr_tests/web/tests          # server, upload rules, limits, security, the demo end to end, PDFs (stub reader, no network, no cost)
python ocr_tests/web/auth.py; python ocr_tests/web/store.py; python ocr_tests/web/results.py; python ocr_tests/web/docx_out.py     # module self-tests
node ocr_tests/web/tests/e2e_browser.js http://127.0.0.1:8080 owner YOUR-CODE    # a real browser through the demo (needs Playwright; the server in stub or real mode)
```

None of them calls the model or costs anything. A real reading through the site was run once by hand; the numbers are in `OCR_TRANSLATION_TEST_PLAN.md`, section 12.
