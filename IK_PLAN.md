# Step 6 plan: using the Indian Kanoon (IK) API for the checker

Written 2026-10-06, revised the same day after the owner pasted IK's terms and pricing. A new cloud session starts without this conversation, so this file is the hand-over. Facts are labelled: **[seen]** read in a file, screenshot or pasted page; **[inferred]** worked out from those; **[unverified]** from memory, to be checked.

## What IK's terms and pricing say (pasted by the owner, 2026-10-06)
- **Prices per request [seen]:** Search Rs 0.50; Original Document Rs 0.50; Document Rs 0.20; Document Fragment Rs 0.05; Document Metainfo Rs 0.02. Pre-paid: when the balance runs out the API returns nothing. IK may change prices with one week's notice.
- **Free credit [seen]:** Rs 500 at sign-up for development and testing; **non-commercial use gets Rs 10,000 free every month, after use-case verification by the site administrator.**
- **Balance [seen, screenshot]:** Rs 391.16 on 2026-10-06, so Rs 108.84 of the Rs 500 has been used [inferred]. That points to Recourse's own earlier fetches on this same account (its notes say 2026-09-05), so the key in Recourse's `.env` is very likely this account's [inferred]. The usage table showing zero calls probably covers only a recent period.
- **Attribution [seen]:** whenever IK search results, documents or classifiers are used to show information to users, **including as context for a retrieval (RAG) system or for fine-tuning**, the "powered by IKanoon" logo must be shown clearly and unaltered; for RAG or fine-tuning, in a prominent place such as the product's About section or documentation. The logo must not imply endorsement or that IK wrote the content.
- **Storage [seen: silent]:** nothing says whether results may be stored, and nothing forbids it; the attribution clause names RAG and fine-tuning, which both involve keeping the text, so keeping it for the user's own product looks contemplated, **provided attribution is given** [inferred]. Republishing or redistributing the text is not addressed.
- **Key [seen]:** securing the key is the owner's responsibility; misuse is not refunded; IK shows the last 30 days of usage (IP address, query, signed certificate). The terms speak of signed requests (public-private key); Recourse's client sends `Authorization: Token <key>`, which worked for it before [seen in code]. Phase 0 settles which form works.
- **Termination [seen]:** either side, at will, one month's notice. Governing law India, courts and arbitration in Bangalore.
- **Data [seen]:** provided "AS IS", no warranty of accuracy.

## What was found in Recourse (read-only, 2026-10-06)
- Recourse uses IK-sourced judgment text (its `corpus/` files, marked `source_type: primary`, fetched through the API) as retrieval context, but **no "powered by IKanoon" logo or attribution text exists in its code**: the only IK mention shown to users is a text link "Read the full judgment on Indian Kanoon" (`app.py` line 1643). Read from code, not from the deployed site. Under the clause above this is probably a gap in Recourse, and the checker's cards would add to it if they were built on IK text. To be fixed in the Recourse repository by its owner (this repo may not change it); a patch can be drafted.
- `RECOURSE_DEPLOY.md` says the deployed `recourse_app.py` does no live IK fetch; the same balance also pays for Recourse's other IK features (Lane B fetches up to 6 documents, about Rs 1.20, per question).

## What the owner does before the next session
1. **Decide whether the use is non-commercial.** If Recourse and this checker are genuinely non-commercial (no payment, no advertising, no plan to charge), apply through the Contact link for the Rs 10,000-a-month non-commercial allowance, describing the use truthfully: a research aid that checks, with a human reviewer, whether cited Supreme Court judgments are still good law. If the use is commercial, or may become so, say so; do not describe it otherwise to obtain credit. Until the application is answered, work inside the current balance.
2. **Add IK's logo to Recourse** (About section or documentation, as the terms require): download it from the terms page, unaltered. A patch for the Recourse repo can be drafted; the owner applies it.
3. **Turn on Balance alert** (account page) at about Rs 150.
4. **Do not change the key** on "Set API-Key": Recourse's deployment uses it.
5. In the cloud environment settings add the environment variable `INDIANKANOON_API_KEY` (the value goes there, never in chat) and set Network access to **Custom** with `api.indiankanoon.org` added to the allowed domains, keeping the default package-manager list. Start a **new session** on this repository and branch `claude/sharp-euler-unyfv0`; say "IK ready".

## What the next session does (each phase stops for approval before spending)
- **Phase 0, smoke test (about Rs 0.02):** one `/docmeta/` call on a known tid (Youth Bar Association, tid 151036912). Confirms the key, the network, which authentication form works, the real response shape and the real price (owner reads the dashboard). Nothing else is built until this works.
- **Phase 1, client with guard rails (`goodlaw/ik.py`, no spend):** key from the environment only, never printed or logged; a hard rupee cap per run and in total; a **dry run** listing every call and its price before any call; a disk cache of raw responses so nothing is fetched twice; stop at once on an auth, balance or 429 error; throttled; tests with a fake server; response fields read from the real Phase 0 response, not guessed.
- **Phase 2, the cited-by gap for the five cases (about Rs 1 to 3):** for each case one `/doc/` call asking for its cited-by list (`maxcitedby`; **[unverified]** parameter name and price), or a search on its citation if that is not offered. Compare with the judgments we hold (title and date) and list those we lack: the coverage gap, measured. Also check the Vedhasingh reference (G. Sagar Suri) and whether it was decided.
- **Phase 3, read the missing citing judgments, Supreme Court only.** Cheapest first: a **document fragment (Rs 0.05)** asking for the passages around the case's name gives exactly what the rules and the second reader read, at a quarter of a full document's price (Rs 0.20); fetch a full document only when a fragment is not enough. Phase 0 and 2 test whether fragments carry enough context. Dry run with count and cost first; the owner approves a cap.
- **Phase 4, make them readable by the checker:** an extra source labelled "Indian Kanoon API", de-duplicated against crawl and bucket, run through the mention finder, rules and second reader like any other judgment. Storage: fetched text stays in a **private** repository or the cache only, never public, and cards that rest on it carry the IK attribution. Derived evidence (the passage and the reading) is what the cards keep.
- **Phase 5, re-run:** cards for the five, then the other 71 checkable library cases if the result and the budget justify it; document, test, commit, push (no PR).

## Budget rule
Balance Rs 391.16 on 2026-10-06. Keep at least **Rs 200 untouched for the live Recourse site**; the checker's cap is about Rs 150 (for example 5 cited-by calls, Rs 1, and up to 1,500 fragments, Rs 75, with room to spare) until the non-commercial allowance is granted or the owner tops up. Phases 0 to 2 should cost under Rs 10.

## Not in this plan, on purpose
- Scraping `indiankanoon.org` pages (ruled out by the owner; API only).
- Changing the API key, creating further IK accounts for free credit, or changing the Recourse repository (read-only here).
- Putting the key or any fetched text into a commit, or into any public place.
