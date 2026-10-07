# "Supreme Court of India Judgments Overruled After 2015 - Research List": what could be checked (2026-10-07)

**Source label: my reading of the judgments in our own collection (46,012 Supreme Court judgments, court-site crawl plus law-report text). Not a lawyer's verification. Nothing here is connected to the live site.**

## Bottom line

The list is a good lead list and not a register. Of its 59 entries (30 distinct overruling judgments):

| Result | Entries | Meaning |
|---|---|---|
| C: confirmed as stated | 41 | The later judgment says, in its own words, that the earlier decision is overruled or not good law, and the list's label fits |
| CN: confirmed, but the list is incomplete or needs a caveat | 11 | True, but a register built from the row alone would mislead (split bench, "to the extent", omitted siblings, later reversal) |
| P: substance right, label stronger than the court's words | 4 | The court said "per incuriam", "unable to concur / do not approve", or "should not be treated as binding" - not "overruled" |
| W: wrong in a material detail | 2 | Row 39 (label false), row 42 (wrong overruling case) |
| U: cannot be checked from our collection | 1 | Row 43 (the later judgment is not in the collection) |

So 52 of 59 (88%) are right that the named later judgment overruled the earlier one at least in part **[Certain for the 49 where I read the judgment's own sentence; headnote only for rows 44 to 46]**. The weaknesses are not in the core facts. They are in four places:

1. **It is incomplete, and it says so.** The PDF calls itself "research-compiled" with no official master database behind it. In our collection alone I found 60 other judgments of three or more judges after 2015 with a sentence that looks like an overruling or a "does not lay down the correct law" (`other_candidates_not_on_the_list.csv`). My reading of the sentences: about 30 are real, fresh overrulings by their own judgment **[Guessing on the number; Likely that it is well above 20]**. The others quote an older overruling or a party's argument. Examples where the sentence plainly says "overruled": Mukund Dewangan (2017, Prabhu Lal), Santhini (2017, Krishna Veni Nagam), Indore Development Authority v. Shailendra (2018, Sree Balaji Nagar), Mohanlal v. State of Punjab (2018, Kader), Janabai (2018), Adani Export (2020), Dheeraj Mor (2020), Bangalore Club (2020), Mahanadi Coalfields (2020), P. Mohanraj (2021), Adani Gas (2021), New Noble Educational Society (2022). My scan also missed at least one: Tofan Singh (2020, 3 judges, `b2020_12_583_874`) overrules Raj Kumar Karwal and Kanhaiyalal, is in the collection, and is neither on the list nor among the scan's hits. So 60 is a floor on the candidates, not a count **[Certain for Tofan Singh; Likely that the true number is higher than my 60]**.
2. **Chains are cut.** The list treats each row alone. Some overrulings were themselves overruled (row 57), some earlier cases were overruled twice (Prabhu Lal: 2017 and 2024; Sree Balaji Nagar: 2018 and 2020), and six rows of the lawyer-verified 2015 list point at a case this list says was later overruled (below).
3. **The label is sometimes stronger than the court's words** (rows 13, 39, 47, 52, 58, 59), and the years mix decision year and reporter year (below).
4. **Provenance.** No author, no verification date, a "corrective note to the earlier response" (so it is a revised draft of something generated or compiled earlier), and a source list ("Indian Kanoon text and citation database, SCC Times, LiveLaw, High Court digests") that I cannot check. It must not be called verified. The earlier 1,688-entry list is different: the owner says a lawyer verified it.

## How I checked

- For each of the 59 entries I found the later (overruling) judgment in the collection. All but one are there: Union of India v. Parshotam Dass (2023, row 43) is not. (Row 42's named judgment is there, but it is not the one that did the overruling; see below.)
- I read sentences of that judgment that name the earlier case together with an adverse phrase (overruled, not good law, not the correct law, per incuriam, do not approve). Where the evidence column of `results.csv` says **B**, I saw the judgment's own sentence in its body; **H** means only the law report's headnote (the report editors' words, not the court's): rows 44, 45 and 46; **H+B** means both.
- Bench sizes are from our collection's metadata, which names the judges in the judgment header. Decision dates are from the same place.
- Cost: nothing outside the collection was used. No Indian Kanoon call, no web page.

## The problem rows

| Row | Problem | What the judgment says | What to do |
|---|---|---|---|
| 39 V. Surendra Mohan | Label "Expressly overruled" is not what happened | Vikash Kumar (2021, 3 judges): the Mohan judgment "stands on a legally vulnerable footing. It would not be a binding precedent, after enforcement of the RPwD Act 2016". The report's headnote lists it as "referred to" | Record as "held not a binding precedent (RPwD Act)", never "overruled" |
| 42 Sree Balaji Nagar | Right fact, wrong overruling case | Overruled by the 5-judge Indore Development Authority v. Manoharlal (2020), and already said to be overruled in Indore Development Authority v. Shailendra (2018, 3 judges). DDA v. Asha Prakash (2023, 2 judges) only quotes the 2020 holding | Correct the "overruled by" to Manoharlal (2020), add Shailendra (2018) |
| 43 Shri Kant Sharma | Cannot check | Parshotam Dass (2023) is not in the collection | Lawyer, or the source judgment |
| 13 Foreshore | Label | The 3-judge bench says Foreshore "cannot be said to be laying down the law correctly" (the report tags it "Not correct law"); "overruled" is used for other decisions in that judgment | Record the court's words |
| 47 SRD Nutrients | Label and year | Unicorn (6 Dec 2019): "clearly per incuriam" because a smaller bench ignored binding larger-bench decisions | Record "per incuriam", year 2019 |
| 52 Asian Resurfacing | Scope | The 5-judge bench is "unable to concur" with directions 36 and 37 and does "not approve" them; the rest of the 2018 judgment stands | Record "directions in paras 36 and 37 not approved", not the whole case |
| 58, 59 Choodamani, Bharat Bhushan | Label | Radhika Agarwal (2025, 3 judges): GST decisions contrary to the anticipatory-bail ratio "should not be treated as binding". Bharat Bhushan is an SLP order, not in the collection | Record "not to be treated as binding", not "overruled" |
| 4, 5 Bhupendra Kumar Bose, T. Venkata Reddy | Wrong proposition described | What is overruled is the "enduring rights" theory for ordinances; the list's description (repeated re-promulgation) is a different holding of the same judgment | Fix the scope text |
| 57 N.N. Global (2021) | Chain cut | True: the 2023 5-judge bench (3:2, Rastogi J and Roy J dissenting) overruled it. But the 7-judge bench in In re Interplay (13 Dec 2023) says "The decision in NN Global 2 and SMS Tea Estates are overruled" | Record both steps; the 2021 holding's current status needs a lawyer's reading |
| 48 Azeez Basha | Split not shown | Four judges overruled the view that a statute-created body cannot be a minority institution; Surya Kant J "modified and clarified", Datta J spoke against overruling; AMU's own status was left to a regular bench | Record the 4:3 split and the single view overruled |
| 50 India Cement | "To the extent" and six omitted | 8:1 (Nagarathna J dissenting): India Cement, Orissa Cement, Federation of Mining Associations of Rajasthan, Mahalaxmi Fabric Mills, Saurashtra Cement, Mahanadi Coalfields and P. Kannadasan are overruled "to the extent of the observations made in the present case" | Add the six, add the qualifier |
| 3, 8, 15, 31, 38 | Omitted siblings in the same judgment | Bhanudas Krishna Gawde (1977; body); "all decisions which took a similar view" as Sun Export (body); Devarapalli Lakshminarayana Reddy (1976, headnote tag "not correct law"); Bhadresh Bipinbhai Sheth (2016, headnote tag only); N. Radhakrishnan (2010, headnote tag) | Add to a register |
| 33 Tomaso Bruno | Same-strength bench | Both Tomaso Bruno (2015) and Arjun Panditrao (2020) are 3-judge benches in our metadata; the court calls Tomaso Bruno "per incuriam" | Lawyer: how is a same-strength overruling treated |

## Chains that a register has to hold

- **Within this list:** N.N. Global (row 57); Mohan Lal (row 34) itself overruled Kader in 2018; Randhir Singh Rana (row 18) is the overruling case of an older row (below).
- **Between this list and the lawyer-verified 2015 list:** six rows of the 2015 list name, as the *overruling* case, a decision this list says was overruled later: row 256 (K.L. Verma, overruled by Adri Dharan Das 2005; both overruled again by Sushila Aggarwal 2020), rows 374 and 499 (State of U.P. v. Synthetics 1980 and State of Bombay v. F.N. Balsara, both overruled by Synthetics 1990, which Lalta Prasad Vaish 2024 overruled), row 407 (Ram Lal Narang, overruled by Randhir Singh Rana 1997, which Vinubhai 2019 overruled), row 598 (H.R.S. Murthy, overruled by India Cement 1990, itself overruled to an extent by MADA 2024), row 1405 (the Delhi High Court's Naz Foundation, which Koushal 2013 reversed and Navtej Johar 2018 overruled) **[Certain that the chains exist; Guessing what a lawyer will conclude about each earlier case]**. Their "overruled" status in the 2015 list cannot be copied forward without a re-read.
- **Design consequence:** no single "overruled" flag. A row carries: the court's own words, the treatment type (overruled / overruled in part / not good law / per incuriam / not binding), bench size and split, decision date, and every later step that touched the overruling case.

## Years

The list mixes the year of decision and the year of the reporter volume. Examples from the collection: Kharak Singh (decided 18 Dec 1962, listed 1963), Chinnaiah (5 Nov 2004, listed 2005), India Cement and Synthetics (25 Oct 1989, listed 1990), Prabhu Lal (30 Nov 2007, listed 2008), Naresh Kumar Yadav (23 Oct 2007, listed 2008), HDFC Bank v. J.J. Mannan (16 Dec 2009, listed 2010), Mhetre (2 Dec 2010, listed 2011), Sree Balaji Nagar (10 Sep 2014, listed 2015), Unicorn (6 Dec 2019, listed 2020). A register must be keyed on citation plus decision date, never on the list's year **[Certain]**.

## What I did not check

- Row 43 (Parshotam Dass), row 59's Bharat Bhushan order and SRD Nutrients' own text: not in the collection.
- The PDF's appendix (State of Uttaranchal v. Rajesh Kumar Gupta overruled by Union of India v. Sanjeev V. Deshpande, 2014): Deshpande is not in the collection.
- Whether any of the 31 overruling judgments was itself later overruled, beyond what the 60 scan hits and the 7-judge Interplay text show.
- The 60 scan hits are machine hits, not individually read.
- Nothing here has been seen by a lawyer. The 2 wrong rows and 4 label rows are my reading of the judgments' words.

## Files

- `results.csv` - one row per entry: verdict, evidence, the court's words (short), note.
- `other_candidates_not_on_the_list.csv` - 60 judgments (2016 onward, three or more judges) with an overruling-looking sentence, unchecked.
- `tools/` - the scripts: `verify_after2015.py` (finds the sentences about each earlier case), `ctx.py` (windows around a phrase in one judgment), `find_a.py` (date lookup), `body_check.py`, `completeness_scan.py`, `build_pdf2_results.py`. They read the local store only.
  The scripts point at the session's scratch folder for the store and the parsed list (paths at the top of each file); they are kept as a record of method, not as a ready-to-run package.
