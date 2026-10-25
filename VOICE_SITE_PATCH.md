# Patch notes for the Recourse owner: never showing a lawyer's argument, and keeping the courts in order

**Status: written, not applied, not tested inside Recourse.** The Recourse repository is read-only for this project. The insertion points below were read from the checkout as it stands today (`pilot_tier_search.py`, `sci_search_tier.py`, `chat_assistant.py`); line numbers will have moved.

The owner's instruction (2026-10-25):

> 1. Supreme court 2. High court 3. Trial court 4. Lawyer's arguments (But never put forward as binding principles). But these arguments must never be shown in the responses.

This is a filter in code, not a line in a prompt. `authority.py` reads the passage itself and decides whose words it is; how it was measured, and where it is wrong, is in `review_results/2026-10-25_voice_rule/RESULTS_IN_PLAIN_TERMS.md`. Nothing in it says a case is good law, and nothing in it says a passage is right or helpful: a passage can be the court's own words, correctly tier 1, and still go against the person asking.

## 1. The bundle

```
python3 -I export_voice_bundle.py <recourse checkout>/passage_authority
```

writes three files (`authority.py`, `textutil.py`, `__init__.py`), about 30 KB, pure Python with no dependency, no data file, no network and nothing to spend. It was imported and used from an otherwise empty directory as a check. Re-export it after any change here, and run `python test_authority.py` in this repository first (49 checks).

## 2. Where it goes

**(a) The site's own wider tier, `pilot_tier_search.search_pilot_tier`.** Its pool (`pilot_chunks`) is not this repository's and nothing filters it today. Inside the loop that scores each chunk, after the similarity bar and before `out.append`:

```python
from passage_authority import authority as PA

v = PA.safe_classify(chunk.get("text") or "", src={"court": chunk.get("court") or ""})
if v["blocked"]:
    continue                                     # every word of it is a lawyer's or a party's
```

and then order the list the owner's way instead of by score alone:

```python
scored.sort(key=lambda sc: PA.sort_key(sc[1]["authority"], sc[0]))      # tier, then states-law, then score
```

**(b) The passages this repository serves, `sci_search_tier`.** The gate belongs on the service side, in this repository, so that the site cannot be served an argument in the first place; `tier_select.pick` already applies it and `tier_select.verify` raises if a blocked passage or an out-of-order list ever reaches a caller. When the service named in `sci_search_tier.py` ("recourse-sci-pool, sci_search_service.py") is built, it must return passages through `tier_select.pick`. Nothing is needed on the site for this.

**(c) What the page shows.** Each kept result carries the verdict. Use it:

* `v["quote"]` instead of the raw passage: it is the run of neighbouring sentences around the best one that holds **no** lawyer's or party's words, so what is on the page is both a true quotation and nobody's argument.
* `v["voice"]` and `v["cue"]` for the line above the quote, so the reader is told whose words these are rather than having to trust the order: "the Supreme Court, as quoted in this judgment" (`higher_court`), "this court's own words" (`court`), **"the trial court's view, as recorded in this judgment" (`lower_court`)**, "the words of the section" (`statute`). A `lower_court` result must carry that line.
* `v["tier"]` is 1, 2 or 3, or `None` when the passage was cut out of the middle of somebody's quotation so that it does not show whose words it is; `None` sorts last and is never promoted.

## 3. Fail closed, not open

`REGISTER_SITE_PATCH.md` fails **open** on purpose: a missing register leaves the answer as it is today. This one is the other way round. `safe_classify` catches every error and returns `blocked: True`, because the thing it prevents is a lawyer's argument being shown as the law; the cost of failing is a shorter list, never a wrong one. Do not wrap it in a try/except that lets the passage through.

## 4. What it does not do

* It does not decide whether a passage helps the person asking, or whether the case is still good law. The register and the currency cards do that, separately.
* It reads word patterns, so it is wrong sometimes, and the measured rates are in the results note: of the passages it blocks, about three in four are ones I had marked as nothing but a lawyer's or a party's words; of the passages that were nothing but that, it blocks about nine in ten. The tier matches my reading on about five in six. Those are my labels, not a lawyer's.
* One hole is measured and not fixed: where a judgment quotes a lower court **without any quotation mark or phrase that shows it is doing so**, the words are read as the deciding court's own. That is why point 2(c) requires the page to name the voice: a reader who is told whose words these are can catch what the rule cannot.
