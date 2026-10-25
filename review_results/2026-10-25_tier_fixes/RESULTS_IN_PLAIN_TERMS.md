# Fixes 2, 3 and 4 of the separate-tier test: results in plain terms (2026-10-25)

Done on the owner's word "Yes, do the fixes for 2, 3 and 4" (the numbering is that of "Problems this test turned up" in `../2026-10-25_tier_test/RESULTS_IN_PLAIN_TERMS.md`). No spending, no network, nothing written to the index or the data branches, nothing connected to the site. The code is new helper modules in this repository; the site (read-only here) will call them when it is connected.

## What I got wrong first [Certain]

- **The label fault was far bigger than the "22" I reported: 403 of the 758 court files of 2010-2017 (53%) were stored with a wrong title or case number.** My check found only the obvious kind (a judge's honorific in the title) and I said so ("the true number is higher by an unknown amount"); the unknown amount is 381. One of the 22 was also a false alarm: a bucket title that says "MINISTRY OF LAW AND JUSTICE".
- The commonest fault is not a visible honorific. It is a judge's surname stuck after the respondent: `THE STATE OF ASSAM SINGH` (106 titles), `PHUKAN` (53), `KUMAR SARMA` (28), `SARMA` (26), `PATHAK` (16). 384 titles had a judge's name or part of it stuck on; 18 had the parties swallowed into the case number; 1 had a stray remark.
- I guessed that `THE STATE OF ASSAM RANJAN PATHAK` was two respondents run together. It is a judge: the list's judge column for that row holds the rest of the name. [Likely: I read it off the list, I did not open the judgment]
- The cause is my own earlier list reader (`ghc/parse_court_lists.py`, written in this project on 2026-10-21): it told the columns apart by how a line looked, not by where it stood, and it did not find a case number with a bench in brackets such as `77(AT)/2010`. The index took its titles from that reading.

## Fix 2: the same passage is not shown twice [Certain]

`tier_select.py`, `pick(rows)`: a passage that reads the same as one already chosen (80% of its 8-word shingles in common each way, the measure `index_dedupe.py` already uses) is not shown again; the next candidate takes its place and the kept result lists the judgments it stands for in `also_in`, so a page can say "also decided in Crl.Rev.P. 221/2025". The cosine bar 0.50, three results at most and one passage per judgment are unchanged.

On the 65 saved results of the tier test it removes 3: R08 and R09 (the twin petitions) and one in the Rangappa legal question, where a 2011 Shillong judgment and a 2025 judgment quote the same Supreme Court paragraph (98% and 97% in common); the 2011 one is listed as "also in". **62 results are shown now. By my earlier ratings: 50 on point, 8 related, 4 off the subject (93.5% on point or related, was 93.8%).** No pair within the saved lists sat between 30% and 80% in common, so the 80% line did not decide any case. The refill (a fourth candidate taking the freed place) is tested on made-up lists, not on the real ones: the saved lists hold only the first three picks. Showing it on real data would mean re-running R08, R09 and the Rangappa question, about $0.004; I did not, as this step was to cost nothing.

## Fix 3: titles and case numbers of the court files [Certain]

1. **The 95 monthly lists were read again by position** (`ghc/reparse_court_lists.py`): the judge column starts where the header "JUDGMENT DELIVERED BY" starts, the subject column where "SUBJECT" starts, and a case number may carry a bench in brackets. 
2. **Checked against the old reading on all 95 lists** (`ghc/compare_court_list_parsers.py`): same rows, same dates, same links in every file; **7,412 listed judgments, 0 differences that are not of a named kind, 0 words lost.** The kinds: 3,673 respondents with a judge's name, a statute year or a case type stuck to them; 202 case numbers with the parties inside; 34 respondents empty or a judge's name; 4 petitioners with stuck text; 229 only in the subject or judge fields; 3,270 the same. So 3,913 of 7,412 listed rows (53%) had a wrong party or case field, criminal or not.
3. **The 758 court files in the index were matched to their rows** (file name of the address, date, first case number: all 758 found exactly) and `ghc/court_lists/court_file_labels.csv` was built (`ghc/build_court_file_labels.py`). The builder stops if a title would gain a word the stored title or citation did not hold, or lose one that is not in the row's judge or subject text; it did not stop. **355 titles unchanged, 385 had judge or subject words removed, 18 rebuilt from the case-number text.**

| Before | After |
|---|---|
| `M/S KOJANI’S DHANKHETI THE HON’BLE MR JUSTICE T VAIPHEI Vs` , case no. `CRL.REVN 33(SH)/2009 SHRI JOSE PULLAN @ JOSEPH P VS SMTI UMA JASRASARIA @ AGARWAL PROPRIETOR OF` | `SHRI JOSE PULLAN @ JOSEPH P Vs SMTI UMA JASRASARIA @ AGARWAL PROPRIETOR OF M/S KOJANI’S DHANKHETI` , `CRL.REVN 33(SH)/2009`, Shillong bench |
| `THE UNION OF INDIA & ORS. THE HON೦BLE MR. JUSTICE B.K. SHARMA THE HON೦BLE MR. JUSTICE K. MERUNO Vs` , `W.P.(Crl.) 8(K)/2009 SHRI LAVITO SEMA VS` | `SHRI LAVITO SEMA Vs THE UNION OF INDIA & ORS.` , `W.P.(Crl.) 8(K)/2009`, Kohima bench |
| `TAFAR TAPPO & ORS. Vs THE STATE OF ASSAM. MR MADAN B. LOKUR GOSWAMI` | `TAFAR TAPPO & ORS. Vs THE STATE OF ASSAM.` |
| `RAJIB ALI Vs THE STATE OF ASSAM RANJAN PATHAK` | `RAJIB ALI Vs THE STATE OF ASSAM` |
| `SMTI HEERA BARUA Vs PIUSH AGARWAL D AGARWAL` | `SMTI HEERA BARUA Vs PIUSH AGARWAL` |

`hc_labels.clean_label(src)` returns court, title, case number, date, link, bench and whether the label differs from what is stored. A court file takes its label from the table; every other Guwahati judgment keeps its stored words, with the double spaces mended (396 titles had them). Over all 7,557 Guwahati judgments in the index it gives no title with a judge's honorific and none empty.

What it does not do: it does not rewrite the index (the stored `src` still holds the old words, by design); it does not touch the 6,799 judgments taken from the bucket (scopes ghc_bucket and ghc_post2017), whose titles come from the bucket's own fields and show no fault of this kind; typos in the source stay (`ANDF 2 ORS.`, `ND ANR`), because mending a spelling is guessing.

## Fix 4: the bench is named [Certain unless marked]

`hc_labels.bench_of` and `court_file_bench`. The bucket's file path names the bench for the judgments of 2018 on (and part of the earlier ones): `asghccis` Assam (Guwahati), `arghccis` Arunachal Pradesh (Itanagar), `nlghccis` Nagaland (Kohima), `azghccis` Mizoram (Aizawl), each checked against the state named in the shown titles. For the court files of 2010-2017 the court's own case number carries a code: `K` Kohima, `AP` Itanagar, `AZ` Aizawl, `SH` Shillong, `AT` Agartala, `IM` Imphal; I checked each against the parties of every list row that carries it (Tripura 13 of 16 `AT` rows, Meghalaya 25 of 61, Arunachal 22 of 35, Manipur 6 of 7, Mizoram 4 of 6, Nagaland 48 of 77; the other rows name no state, except one `K` row against the State of Assam). A case number with no code was heard at the principal seat in Guwahati: of the 5,049 such list rows that the bucket also holds, 5,042 are Assam-bench and 7 Arunachal [Likely for the ones the bucket does not hold]. Where there is no code and the parties name another state, the bench is left unnamed rather than guessed.

**All 7,557 Guwahati judgments in the index:** principal seat, Guwahati 6,368; Itanagar 719; Aizawl 265; Kohima 193; Shillong 5; Imphal 3; Agartala 1; not named 3. Shillong, Imphal and Agartala were benches of this court until 23 March 2013, when Meghalaya, Manipur and Tripura got High Courts of their own; their labels say "until March 2013".

## The tier test's own results with the three fixes (`tier_results_with_the_fixes.csv`)

62 results shown (was 65). Bench of what is shown: principal seat 46, Itanagar 9, Kohima 4, Aizawl 3. Two labels changed (RAJIB ALI, HEERA BARUA, above); the Shillong judgment is the one the duplicate rule folded under the 2025 judgment. The verdict of the tier test (PASS) is unchanged.

## Not fixed, and limits

- **Problem 1 of the tier test (a passage that is a lower court's words, a party's argument or background facts; a passage that is on point but goes against the asker) is untouched.** These fixes make the list cleaner, not more trustworthy. I have no tested fix for it.
- The 80% line is a choice, not a measurement; it has the precedent of `index_dedupe.py`. Passages that are the same idea in different words are not folded.
- The 403 corrections are certain only as far as the lists are: the new reading puts every word in the column it stands in, and the old and new readings agree on every word. A wrong cell in the court's own list would stay wrong.
- "Principal seat" for a case number without a code is an inference from the court's numbering, tested on 5,049 rows, not a statement on the judgment.
- Nothing here shows the judges' names; the table holds them whole (`judges` column), if the site wants a "bench of judges" line.

## Tests and files

`python test_tier_select.py` (13 checks), `test_hc_labels.py` (26), `test_reparse_court_lists.py` (10, on a list drawn here with the two faults in it; the old reader fails the same list), all ALL PASSED, and the existing `test_sci_index.py`, `test_index_dedupe.py`, `test_sci_bucket.py` still pass.

New: `tier_select.py`, `hc_labels.py`, `ghc/reparse_court_lists.py`, `ghc/compare_court_list_parsers.py`, `ghc/build_court_file_labels.py`, `ghc/court_lists/reparsed_rows_2010_2017.csv.gz` (7,412 rows), `ghc/court_lists/court_file_labels.csv` (758 rows, old and new side by side), the three test files, and this folder.

How the site would use them once connected: `tier_select.pick(candidates)` for the list, `hc_labels.clean_label(src)` for each result's heading and link, `also_in` for "also decided in ...".
