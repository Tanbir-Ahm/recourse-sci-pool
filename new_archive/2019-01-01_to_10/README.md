# First pass: the court's newer archive, judgments of 1 to 10 January 2019 (2026-10-21)

Source: the owner ran the court's judgments-by-date search for 01-01-2019 to 10-01-2019 in his own browser (CAPTCHA answered by him) and copied the PDF links on the page. `links_all.txt` is that list as received (53 links). `first_pass.py` is the script as run; `results.csv` is its output (one row per link). PDFs and extracted text were **not** committed (PDFs stay outside the repo; text can be re-extracted from the links). Fetching: one request per link, 1.5 to 2 s apart, the crawler's User-Agent, no 403 or 429.

## What the 53 links were
- 41 English judgments (all fetched, all valid PDFs).
- 11 vernacular translations of English judgments in the list (`supremecourt_vernacular`, Hindi, Kannada, Gujarati). Not fetched; the corpus is English. The owner can say otherwise.
- 1 link with no diary number (`supremecourt//2018/2018__Judgement_08-Jan-2019.pdf`): a defect on the court's page. It cannot be fetched; the same defect appears in an older link in this repo (`2011`, 09-Apr-2019). [Guessing] it may be *Chander Bhan Singh v. CBI* (8 Jan 2019), which the bucket has and the list lacks.

## The 41 English judgments [Certain, read from the files]
- 3 to 44 pages, typeset text layer, no embedded images in any, none under 1,500 characters. No two files identical. These are not scans (unlike the bucket's 2017 PDFs).
- Page 1 marker: 35 REPORTABLE, 4 NON-REPORTABLE, 2 with no marker.

## Against the bucket (matched by decision date and party words; the 9 misses were read by hand and are genuinely absent)
- **32 of 41 are in the bucket; 9 are not (22%).**
- The 9 missing: Champa Lal Dhakar v. Naval Singh Rajput (Crl. A. 1931/2009); State of M.P. v. Kalyan Singh (SLP Crl. 5632/2014); Kusumben Inderbhai Dhupia (C.A. 230/2019); Lalichan v. State of Kerala (SLP Crl. 8113/2017); M/s MDDA Ramky ISBT v. Ombir Singh Tomar; Sukh Bilash Thakur v. Bihar State Electricity Board; M/s Sicagen India Ltd. (Crl. A. 26-27/2019); Jagdish Chand v. State of Haryana (Crl. A. 767/2012); Ku. Bhawana v. State of Maharashtra. **Five of the nine are criminal matters**, the kind the index keeps.
- **Reportable or not:** all 4 non-reportable judgments are missing from the bucket; 5 of the 35 reportable ones are (14%). [Likely] The bucket is mostly judgments that go into the law reports. Small sample, one 10-day slice; not a rate for other years.
- **The list is not complete either:** the bucket holds 35 judgments for these dates; 33 are matched by the owner's list. Two bucket judgments (*Madhav Hari Joshi v. Divisional Manager, LIC*, 4 Jan; *Chander Bhan Singh v. CBI*, 8 Jan) are absent from the list. So the copied list lacks at least 2 judgments the court decided in this range [Certain]; the cause is not known (a link in another form, a row the snippet did not catch, or a missing page). Court total for the range is therefore at least 43; the bucket holds 35 of those (about 81%).

## What this does not show
Nothing here says whether these judgments are good law. A different slice could differ. Nothing was fed to the index, the checker or the register.
