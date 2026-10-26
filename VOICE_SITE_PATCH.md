# Patch notes for the Recourse owner: never showing a lawyer's argument, and keeping the courts in order

**Status: written, not applied, not tested inside Recourse.** The Recourse repository is read-only for this project. The insertion points below were read from the checkout as it stands today (`pilot_tier_search.py`, `sci_search_tier.py`, `chat_assistant.py`); line numbers will have moved.

The owner's instruction (2026-10-25):

> 1. Supreme court 2. High court 3. Trial court 4. Lawyer's arguments (But never put forward as binding principles). But these arguments must never be shown in the responses.

This is a filter in code, not a line in a prompt. `authority.py` reads the passage itself and decides whose words it is; how it was measured, and where it is wrong, is in `review_results/2026-10-25_voice_rule/RESULTS_IN_PLAIN_TERMS.md`. Nothing in it says a case is good law, and nothing in it says a passage is right or helpful: a passage can be the court's own words, correctly tier 1, and still go against the person asking.

## 1. The bundle

```
python3 -I export_voice_bundle.py <recourse checkout>/passage_authority
```

writes five files (`authority.py`, `textutil.py`, `hc_labels.py`, `court_file_labels.csv`, `__init__.py`), about 140 KB, pure Python with no dependency, no network and nothing to spend. The one data file is the slim label table of section 2(d): 758 rows, no judges' names. It was imported and used from an otherwise empty directory as a check. Re-export it after any change here, and run `python test_authority.py` in this repository first (see the test files).

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

**(c) What the page shows: the line saying whose words, which is now mandatory.** Owner's decision, 2026-10-25: the rule reads word patterns and is wrong sometimes, so the reader is told whose words each result shows. Every kept result carries `voice_line` and `tier_select.verify` raises if one is missing, so it cannot be left out by accident. Print it directly above the quote, in the same type size, not as a tooltip or a footnote:

```python
for r in tier_select.pick(candidates):          # or, on the site, the same two calls on its own chunks
    show(r["voice_line"])                       # e.g. "the Supreme Court, as quoted by Gauhati High Court"
    show(r["authority"]["quote"])               # the run of sentences with no lawyer's or party's words in it
```

The lines it produces: "*{court}'s own words*"; "*the Supreme Court, as quoted by {court}*" (or "a High Court, as quoted by ..."); "*The trial court's view, as recorded by {court}, not this court's own holding*" (or "The court below's view ..." for a High Court's view inside a Supreme Court judgment); "*The words of a section, as set out by {court}*"; "*Quoted words: this passage does not show whose they are*" (a passage cut out of the middle of a quotation; tier unknown, ranked last); and " *(background to the case; it states no rule)*" added to any of them when the passage tells the story of the case. None says a case is good law or that the words are right.

* `v["tier"]` is 1, 2 or 3, or `None`; `None` sorts last and is never promoted.
* **Order, owner's decisions of 2026-10-25:** the strict order (Supreme Court, High Court, trial court, then states-law, then score), and a passage never ranks above the court that wrote its judgment: a High Court judgment quoting the Supreme Court stays at High Court rank, and in a Supreme Court judgment the Court's own words come before its recital of the High Court's view. The verdict carries `own_tier`, so `sort_key` applies this without the caller passing anything.

**(d) The label and the bench: `hc_labels`.** Owner's request, 2026-10-26. Every Gauhati High Court result needs a clean title, a case number, a date, the bench it was decided at, and a link; the stored fields do not give them cleanly (a judge's name trails a party, the case number swallows party names, double spaces). The Supreme Court results need none of this and are left as they are.

```python
from passage_authority import hc_labels

card = hc_labels.card(src, result)       # src: the stored fields of the judgment; result: one row from tier_select.pick
show(card["heading"])                     # "SHRI JOSE PULLAN @ JOSEPH P Vs SMTI UMA JASRASARIA ... · CRL.REVN 33(SH)/2009 · 2011-04-27"
show(card["bench_label"])                 # "Shillong bench (Meghalaya), until March 2013"
show(card["voice_line"]); show(card["quote"])
link(card["url"])
```

`card` returns exactly: `heading`, `court`, `title`, `case_no`, `date`, `bench_label`, `url`, `voice_line`, `quote`, `also_decided_in` (the judgments whose twin passage was folded under this one, as document numbers; the page can say "also decided in ..."). `hc_labels.clean_label(src)` and `hc_labels.bench_of(src)` are there if the page wants the pieces.

What each field is, and where it comes from:

* **Title and case number, 758 court files of 2010-2017:** from the slim table `court_file_labels.csv` (found next to `hc_labels.py`), built from the court's monthly lists re-read by position. The old wording is not in the bundle. A row says what was done to it in this repository's full table; the bundle drops that column.
* **Every other judgment** (2018 on, and the Supreme Court): the title stored in the index with double spaces mended, nothing else changed. A typo in the source stays a typo.
* **Bench:** from the path code of a 2018-on file (`as` Guwahati, `ar` Itanagar, `nl` Kohima, `az` Aizawl) or from the bracketed code in the case number of an older one (`K` Kohima, `AP` Itanagar, `AZ` Aizawl, `SH` Shillong, `AT` Agartala, `IM` Imphal). No code means the principal seat at Guwahati, unless the case names another state. The Shillong, Agartala and Imphal benches ended on 23 March 2013, and the label says "until March 2013".
* **Url:** the stored one. A record with no address gives `None`; do not print an empty link.

**The shape caveat.** `card` and `clean_label` read the index's `src` fields (`scope`, `url`, `title`, `citation`, `path`, `court`, `date`). The site's own pilot chunks (`pilot_tier_search.py`) have other names (`case_name`, `citation`, `chunk_method`, ...). Either `sci_search_service.py` returns the card itself (preferred, nothing to map), or the site builds a dict with those seven keys from its chunk before calling. If `path` and `url` are both missing, `bench_label` and `url` come back empty (`None`) rather than guessed: the bench is read from the file's path or address, so a chunk without either gets no bench line. The page should print nothing for an empty field, not a default. Do not fill in "Guwahati" for it.

## 3. Fail closed, not open

`REGISTER_SITE_PATCH.md` fails **open** on purpose: a missing register leaves the answer as it is today. This one is the other way round. `safe_classify` catches every error and returns `blocked: True`, because the thing it prevents is a lawyer's argument being shown as the law; the cost of failing is a shorter list, never a wrong one. Do not wrap it in a try/except that lets the passage through.

## 4. What it does not do

* It does not decide whether a passage helps the person asking, or whether the case is still good law. The register and the currency cards do that, separately.
* It reads word patterns, so it is wrong sometimes, and the measured rates are in the results note: of the passages it blocks, about three in four are ones I had marked as nothing but a lawyer's or a party's words; of the passages that were nothing but that, it blocks about nine in ten. The tier matches my reading on about five in six. Those are my labels, not a lawyer's.
* One hole is measured and not fixed: where a judgment quotes a lower court **without any quotation mark or phrase that shows it is doing so**, the words are read as the deciding court's own. That is why point 2(c) requires the page to name the voice: a reader who is told whose words these are can catch what the rule cannot.
