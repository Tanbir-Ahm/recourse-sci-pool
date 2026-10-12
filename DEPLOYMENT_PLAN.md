# From research repository to website: inventory and step-by-step plan (written 2026-10-12)

Facts below were read from the repositories, the files and the live site on 2026-10-12. [Certain] = read from a file or a command; [Likely] = strong inference; [Guessing] = a judgment. Nothing in this plan has been done on the live site.

## 1. What exists, and where

| Where | What it holds | Size | State |
|---|---|---|---|
| `recourse-sci-pool`, branch `main` (= `claude/sharp-euler-unyfv0` plus 2 later commits on the branch) | All code, tests, the Overruled Register data, the currency cards, the sealed stage F question files, every result, plan and sheet | 1,444 files, 43 MB | Merged on 2026-10-12 |
| `recourse-sci-pool`, branch `claude/sci-index` | **The index**: 640 files, 10,503 judgments, 236,155 passages (+ 2,607 from three side indexes kept in `review_data/side_index`), voyage-law-2, 1,024-dimension float16 vectors, passage text | **540 MB** | Frozen at commit `3c80a26` (ends 13 Jul 2026). **Not on `main`** |
| `recourse-sci-pool`, branch `claude/sci-pool` | The crawl (raw judgment text) | 275 MB | Data branch; not on `main` |
| `recourse-sci-pool`, branch `claude/sci-bucket` | The 2017 to 2026 bucket text | 154 MB | Data branch; not on `main` |
| Local only, not in git | `corpus.sqlite` (about 1.8 GB, the checker's store; rebuild about 15 minutes) | n/a | **Lost if this container is reclaimed**; the cards and register are in git |
| `recourse` (public as of today), branch `main` only | The live website: `recourse_app.py` (Streamlit), `chat_assistant.py` (answers; also used by the WhatsApp bot), 38 MB core embeddings, `pilot_tier_search.py` (a separately labelled, stricter tier), 70 test files | 451 files | Head `721e063`, 29 Sept 2026; matches the live page |
| Railway project "perceptive-enthusiasm", production | Two services online: `whatsapp-bot` (with a volume) and the website | n/a | **Subscription unpaid, "Trial maxed out"** |

Correction to something I said on 12 Oct: "everything is on `main`" is true of the code and results, **not of the three data branches**. Do not delete those branches.

## 2. What we built and tested, and whether it goes on the site

| Piece | Evidence | Deploy? |
|---|---|---|
| **Search recipe B** (meaning + keyword + section search, merged; re-ranked by rerank-3-lite; passage-type weights; section boost) over the big index | Stage F: floors met (useful 79%, key authority in top 10 on 81%, Yes 40%); Misleading 14% against a 15% limit (weak pass, 16% without the soft-overlap questions). LLM-judged only | **Yes, as a separately labelled tier, shadow mode first.** Domains A, B, C, E, H, I may go to shadow mode; D, F, G, J may not |
| **Act-boost N1/N2** | Failed rules 1, 3, 4, 6; slightly worse than B | **No. Shelved** |
| **Overruled Register + three locks** (demote before, fixed prompt fact during, scan after) | Own tests pass; **trap exam never run; Mr. Advocate has not reviewed it**; patch written (`REGISTER_SITE_PATCH.md`), never applied | **Yes, but only after the trap exam and his review** |
| **Cards overlay + "not checked by us" wording** (standing item 0) | Specified, not built. The checker catches about 3 in 10 verified overrulings | Build, then deploy with the register |
| Stale-ruling leak seen in stage F (N10: E. Micheal Raj in B's top 5) | One of 4 measurable currency traps leaked | This is why the register must be live before anything is shown |
| 19 side-index judgments | Already in the 238,762 passages | Ship with the index |
| Sealed questions, keys, packs, marks, reading sheets, Mr. Advocate sheets | Private test material | **Never deploy** (the repository is private; keep it so) |
| Weekly register review routine | Exists | Keep running |
| Monthly bucket refresh | Postponed until stage F scoring ended (now over) | Decide after the first shadow month |

## 3. Blockers and risks, most serious first

1. **Billing.** Railway says the subscription is unpaid. Until it is paid the production site can be suspended and a new service may not start. [Certain: banner in the screenshot]
2. **The index does not fit the way the site is built.** The site holds a 38 MB embeddings file inside a Streamlit container. The index is 540 MB on disk and about 470 MB of vectors plus about 260 MB of text in memory, and the keyword search is built in memory at start (about 25 seconds here). [Certain for sizes] A container with less than about 2 GB of memory is risky [Guessing; check your Railway plan]. Putting it inside the website container could make the live site slow or crash.
3. **The WhatsApp bot shares `chat_assistant.py`** with the site. Any change to answering changes both. [Certain: the file says so] I know nothing else about that service.
4. **Shared credit.** Each question to the new tier costs one embedding and one re-rank (stage F: 29 questions cost about 3 cents in Voyage). The Voyage balance is shared with the live site, reserve $5. The answer-writing step (Anthropic) is the larger cost and already exists.
5. **No lawyer has checked anything yet.** Marks are ChatGPT and Gemini; the key and the register are unreviewed; the site's own promise is that it cannot misstate law.
6. **I cannot deploy.** I have no Railway access, the Recourse repository is read-only for this project, and this session's network blocks WebSockets, so I cannot even read a real answer from the live site.
7. **(Added 2026-10-12) Case names.** 5,678 of 10,522 judgments in the index (54%) are named only by their opening lines and 324 by nothing; the site's panel shows a name and a link. Needs a names table before anything is shown (`SEARCH_SERVICE.md`, limit 1).
8. **Fragile working copy.** This container is temporary. Everything worth keeping must be pushed (it is), and `corpus.sqlite` must be rebuilt after any reset.

## 4. The design I recommend

**A separate small search service**, not the index inside the website.

- A third Railway service ("sci-search"), reachable only from the website's private network, that loads the index once and answers `POST /search {question}` with the top passages (recipe B), each labelled "wider pool, not independently verified".
- The website's `chat_assistant.py` calls it as one more tier, **exactly like the existing pilot tier**, and **fails open**: if the service is down or slow, the site answers as it does today.
- The register hooks (`register_hooks.py`) and the cards overlay sit on the website side and apply to every case the answer names.
- A switch (an environment variable) turns the tier off in seconds.

Why: it keeps 0.7 GB of memory off the live site, lets you try it without touching production, and can be removed without redeploying the site.
Alternative (simpler, riskier): load the index in the website container.

## 5. Step by step

**Phase 0: you, this week (nothing technical)**
1. Pay or resolve the Railway balance. Confirm the plan's memory and volume limits.
2. Tell me what `whatsapp-bot` is, who uses it, and whether it uses the same Anthropic and Voyage keys.
3. Decide the product: a safety site for ordinary people, or a research tool for lawyers. This changes wording and what may be shown.
4. Confirm the first deployment is a **staging copy**, not production.
5. Decide how I get write access to the Recourse repository: either you apply my patch files yourself (current arrangement), or you let me push to a branch (not `main`) of `Tanbir-Ahm/recourse`.
6. Send Mr. Advocate: the register sheet, the key sheet v2, the reading sheet. Ask for the writer's corrected Declaration.

**Phase 1: me, no access needed (about the next sessions)**
7. Build the cards overlay export and the fixed "not checked by us" wording (standing item 0).
8. Re-export the register bundle and refresh `REGISTER_SITE_PATCH.md` against the current Recourse head (`721e063`).
9. Build and run the 50-question trap exam with the locks off and on; a lawyer reads 20 answers.
10. Build `sci_search_service.py` from the stage F retrieval code (`pool_runner.Engine`), with tests, a health endpoint, a size and memory report, and a start command.

**Phase 2: staging (me and you)**
11. Decide how the index reaches the service (it is 540 MB and must not sit in the website repository): a Railway volume filled once from the `claude/sci-index` branch, or a private release file. I prepare the loader.
12. Create a separate staging Railway project with the website branch plus the search service; set `VOYAGE_API_KEY` and the Anthropic key there; keep production untouched.
13. Run the website's 70 tests and ours; test the WhatsApp path on staging.

**Phase 3: shadow mode (about two to four weeks)**
14. Staging (or production with the tier hidden) logs, for each real question: the question, the tier's passages, the register and card notes. Nothing is shown to users.
15. Each week: read the log, count passages with an overruled case, review flags with Mr. Advocate (the weekly sheet already exists).

**Phase 4: limited show (only if Phase 3 is clean and a lawyer agrees)**
16. Show the tier only in the site's "not independently verified" panel, domains A, B, C, E, H, I (arrest and bail first), with register warnings and "not checked by us" wording and the "as of 13 July 2026" date.
17. Keep the kill switch; watch cost and complaints.

**Phase 5: later**
18. Never feed the tier to the verified answer path without a lawyer-reviewed pass. D, F, G, J only after their own test. Refresh the index monthly (bucket refresh) and re-run a small check each time.

## 6. Phase 1 status (updated 2026-10-12, same day; all on branch `claude/sharp-euler-unyfv0`, nothing on the live site)
| Step | State |
|---|---|
| 7. Cards overlay + "not checked by us" | **Built and tested** (`goodlaw/overlay.py`, `test_goodlaw_overlay.py`). Covers the 76 library cases only; wider coverage needs the corpus store rebuilt |
| 8. Site patch refreshed | **Built and tested on a scratch copy at 721e063**: `site_patch/recourse_721e063.patch` applies cleanly; Recourse's free suite 63 of 63 pass; Streamlit render checked. **Not applied** (yours to apply). No real-model run |
| 9. Trap exam | **Runner and a criminal-domain exam built and tested with a stand-in assistant; not run** (needs the real model and keys, on your machine). Finding: 35+ of the original 50 questions are outside criminal law, so a new 28-question exam over the 14 register rows that are in the index was made (`site_patch/README.md`) |
| 10. Search service | **Built, tested, run on the real index**: same list as the saved stage F B list on 4 of 4 questions; about 1.5 GB memory, 27 to 33 s start, 1.3 to 3.7 s per question (`SEARCH_SERVICE.md`). **New blocker found: 54% of judgments in the index have only their opening lines as a "name"** |

## 7. What I need to start Phase 1 now (historical: Phase 1 was started on the owner's instruction)
Nothing more from you: say "start Phase 1" and I begin with steps 7 to 10 on this repository. Steps 1 to 6 and 11 to 12 are yours or need your access.
