# Step 6 plan: using the Indian Kanoon (IK) API for the checker

Written 2026-10-06. A new cloud session starts without this conversation, so this file is the hand-over. Facts are labelled: **[seen]** read in a file or screenshot, **[told]** said by the owner, **[unverified]** from memory or inference and to be checked.

## Where things stand
- **[seen]** IK API account of tanviry160@gmail.com shows balance Rs 391.16 and zero calls in its usage table (screenshot, 2026-10-06).
- **[seen]** Recourse's client (`indiankanoon_client.py`) reads `INDIANKANOON_API_KEY` from the environment, `.env`, or Streamlit secrets; endpoints `/search/`, `/doc/<tid>/`, `/docmeta/<tid>/`, all `POST` with header `Authorization: Token <key>`. Its comments give Rs 0.20 per full document and Rs 0.02 per metadata call; search and cited-by prices are on IK's pricing page, which this environment cannot read (egress blocked, 2026-10-06).
- **[seen]** The same balance pays for Recourse's live features (Lane B "related judgments" fetches up to 6 full documents per question, about Rs 1.20).
- **[seen]** Recourse's notes say its `corpus/` texts for the five cases were fetched through the API on 2026-09-05, but the dashboard shows zero calls: either the dashboard table covers only a recent period, or Recourse's key belongs to a different IK account. To be settled by the owner (step 3 below).
- Done already: the five library cases not in our collection are checked as external targets (`goodlaw/targets/external.json`, `FOLLOW_UPS.md` 1f). What is still missing is the later judgments we do not hold.

## What the owner does (before the next session)
1. Read IK's **Terms and Conditions** and **Agreement** pages (links on the account page) and answer: may API results be stored (kept, not only displayed)? may they be used inside a product other people use? any attribution or rate limits? Paste the relevant clauses into the chat (text only, never the key). This decides where fetched text may be kept.
2. Copy the **Pricing** page text into the chat (price of search, document, docfragment, docmeta, and of the cited-by and cites lists).
3. Check the key's account: on the account page, **Set API-Key** shows the key. Do **not** change it: Recourse's deployment uses the current key and would stop working. Only confirm that Recourse's `.env` key is this account's key (compare the last 4 characters; do not paste it).
4. Turn on **Balance alert** (account page) at about Rs 150, so the live site is never drained silently.
5. In the cloud environment settings: add the environment variable `INDIANKANOON_API_KEY` (set the value there; never in chat), and set Network access to **Custom** with `api.indiankanoon.org` added to the allowed domains, keeping the default package-manager list. Start a **new session** on this repository and branch `claude/sharp-euler-unyfv0`; say "IK ready".

## What the next session does (each phase stops for approval before spending)
- **Phase 0, smoke test (about Rs 0.02):** one `/docmeta/` call on a known tid (Youth Bar Association, tid 151036912). Confirms key, network, the real response shape, and the real price (owner reads the dashboard). Nothing else is built until this works.
- **Phase 1, client with guard rails (`goodlaw/ik.py`, no spend):** key from the environment only, never printed or logged; a hard rupee cap per run and in total; a **dry run** that lists every call and its price before any call is made; a disk cache of raw responses so nothing is fetched twice; stop at once on an auth, balance or 429 error; throttled; tests with a fake server. Response fields are read from the real Phase 0 response, not guessed.
- **Phase 2, the cited-by gap for the five cases (a few rupees):** for each of the five, ask IK for its cited-by list (the `/doc/` call with the cites/cited-by options, if the pricing allows it; otherwise a search on the citation). Compare with the judgments we hold (by title and date) and list those we lack: that is the coverage gap, measured. Also check the Vedhasingh reference (G. Sagar Suri) and whether it was decided.
- **Phase 3, fetch the missing citing judgments, Supreme Court only:** dry run first with the count and the cost; the owner approves a cap. At Rs 0.20 a document, Rs 100 buys about 500 documents.
- **Phase 4, make them readable by the checker:** an extra source in the store labelled "Indian Kanoon API", de-duplicated against crawl and bucket by title and date, then the mention finder, rules and second reader run on them like any other judgment. Where the text is kept depends on the Terms (step 1): either a private data repository, or only derived evidence (the mention sentences) with the text discarded after each run. Fetched text is **not** pushed anywhere until the Terms are read.
- **Phase 5, re-run:** cards for the five, then the same for the other 71 checkable library cases if the budget and the result justify it (prices in Phase 2 make that estimate exact). Then document, test, commit, push (no PR).

## Budget rule
Balance Rs 391.16 on 2026-10-06. Keep at least **Rs 200 untouched for the live Recourse site**; the checker's cap is about Rs 150 until the owner tops up. Phases 0 to 2 should cost under Rs 10.

## Not in this plan, on purpose
- Scraping `indiankanoon.org` pages (ruled out by the owner; API only).
- Changing the API key, or touching the Recourse repository (read-only).
- Letting fetched text or the key into any commit before the Terms are read.
