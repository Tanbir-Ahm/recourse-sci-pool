# Test plan: reading and translating local-language court and police records

Written 2026-10-25 for the lawyer who asked for a tool that reads and translates trial-court and police records written in Assamese, Kannada and other local languages. The plan was fixed before any result existed. Sections 10 to 10ad record the results so far (real pages, scores and counts only); section 11 (the last section of this file) is the design that follows from them, and it is built; the rest of the plan is still to be run.

## 1. The question

Can a computer tool read scanned or photographed pages in Assamese or Kannada, including handwriting and badly made PDFs, and give an English draft that is good enough to be useful, without hiding its mistakes?

"Useful" means two things only:

- **Reading aid.** You can read the whole record yourself, quickly, and decide which pages need a formal translation.
- **Draft for the High Court translator.** The translator corrects a draft instead of starting from nothing, which saves time and cost.

**Not tested, not claimed:** a translation you can file as certified. Court rules on translations differ by High Court. Please check the current rules of the High Court you appear in before relying on any machine draft for anything filed.

## 2. What we need from you (about 30 pages)

| Group | Pages | What |
|---|---|---|
| A | 10 | Handwritten pages, for example witness depositions and statements |
| B | 10 | Police and court documents (FIR, seizure memo, remand order, charge-sheet pages), typed or printed |
| C | 5 | The "gibberish" PDFs: pages that look normal on screen but copy out as random letters or symbols |
| D | 5 | Clean typed or printed pages, as a baseline |

- **Languages:** Assamese and Kannada, plus any other you regularly meet. Say which language each page is in.
- **Best case:** pages from closed cases where the High Court translator already produced a translation. Original plus translation gives us a reference answer for free. Where none exists, we need a bilingual person to translate about 10 of the pages (see section 4).
- **Step 0, before the full set:** send 3 example pages of the "gibberish" you mean. In 15 minutes we can tell whether it is an old-font problem (likely fixable), a poor scan, or hard handwriting and shorthand (likely not fully fixable).
- **Per page, one line:** language, handwritten or typed, how it was captured (scan, phone photo, fax, PDF), and whether copying text out of the PDF gives garbage.

**Your decision on confidentiality.** Pages are sent to outside services to be read. Do not send anything that identifies a minor or the victim of a sexual offence. For the rest, you decide what your duty of confidentiality allows. We will tell you which services see the pages, use settings that do not keep data where the service offers them, and delete our copies afterwards. Results will refer to pages by number, never by name.

## 3. What we will compare

Each page goes through every candidate and the outputs are kept separate. The names below are the plan, subject to checking availability and price before we start.

- **Reading (page image to text in the original script):** a general vision AI model; Google's Gemini vision model; an Indian-language document reader such as Sarvam Vision; Google Cloud Vision (its document text detection); and free OCR (Tesseract) as the baseline. We will also run the open-source `legal-ocr-service` (Tesseract in a container with a Google Vision option, built for Gujarati documents) as a named baseline. It is run twice: as published, and with its PDF page rendering fixed to 300 dpi (as published it renders PDF pages at a low default resolution), so we can tell the weakness of the engine from the weakness of that setup. It also needs its language setting changed for Assamese or Kannada.
- **Translation (to English):** an AI model; Google's Gemini; IndicTrans2 (free, open-source); Google Translate.
- **Two-reader check:** where two different readers disagree on a line, the line is marked for a human. Part of the test is whether those marks catch the real mistakes.

Every output must show the page image, the original-script text and the English side by side, with unreadable words marked `[unclear]` instead of guessed.

## 4. What the reviewer does

The reviewer must read the language well. It can be you, or a translator or bilingual colleague. Time estimate: about 15 minutes per page, so roughly 7 to 8 hours for 30 pages. That is my guess; the first 3 pages will tell us.

For each page, compare the tool's English against the reference translation (or the original, if you read it) and log every error on the marking sheet in section 8.

**A material error is any of these:** a wrong or missing name, number, date, amount or place; a lost or added "not" or "no"; who did what to whom reversed; a wrong legal section; a passage left out; a passage invented.

Each error is **Critical** (changes what the evidence says), **Moderate** (awkward, but the meaning survives) or **Minor**.

For every Critical error, also note whether the tool warned about that spot (`[unclear]` or a reader disagreement). A **silent Critical error**, one with no warning, is the failure we care about most.

**Translator timing test (5 pages, Groups A or B):** ask a recognised translator to correct the tool's draft, and note the time taken. Compare with that translator's usual time for a page of the same kind.

## 5. Pass rules (fixed now, before any run)

We judge each group (A, B, C, D) separately, and each tool separately.

| Result | Rule |
|---|---|
| **Usable as a reading aid** | On at least 8 of 10 pages (4 of 5 for C and D) you judge the gist correct, **and** there is no more than 1 silent Critical error in the group |
| **Usable as a draft for the translator** | Correcting the draft takes the translator at least 30% less time than translating from scratch, on at least 4 of the 5 timed pages |
| **Not usable for that group** | Anything else. We say so plainly, per group |
| **Replaces the certified translator** | Not a goal. Not tested. |

**How far the results can be trusted.** 30 pages cannot prove a tool is safe. Even if a tool makes zero silent Critical errors in 30 pages, all that shows is that the true rate is probably below about 1 page in 10. A pass means "worth using carefully, with the original beside it", not "can be trusted". A fail is meaningful: it means the tool is not ready for that kind of page.

**The handwriting group (A) is judged on its own.** If the tools fail on handwriting but pass on typed pages, we recommend them for typed and PDF records only.

## 6. What we report back

One page per tool, with a table by group showing: pages with correct gist, Critical errors found, how many of those were silent, and the translator's timing. We also include the five worst errors, shown in the original and the English, so you can judge their seriousness yourself. We finish with one recommendation: use for X, do not use for Y, and what would change that.

## 7. Timeline (estimate)

- Week 1: Step 0 examples, your confidentiality decision, pages collected.
- Week 2: run all candidates (a few hours of machine time; service fees likely small, to be confirmed before we start).
- Week 3: reviewer marking and the translator timing test.
- Week 4: report and recommendation.

## 8. Marking sheet (one row per error)

| Page ID | Tool | Group | Line / location | What the tool said | What it should say | Type (name, number, date, amount, place, negation, who-did-what, section, omitted, invented) | Severity (Critical / Moderate / Minor) | Did the tool warn here? (yes / no) |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |

Page summary (one row per page and tool): gist correct (yes / no); number of Critical errors; number of silent Critical errors; reviewer minutes.

## 9. Questions for you

1. Which High Court(s) and which languages matter most?
2. Do closed cases with a translator's translation exist, so we can use original-plus-translation pairs?
3. What may you share, and how (secure upload, not email, if possible)?
4. Who will be the reviewer, and who is the translator for the timing test?
5. Does your High Court accept a translator-corrected machine draft for filing? If you don't know, who would?

## 10. Results so far (recorded 2026-10-25; scores only, no case text, one document)

**What was tested.** One real 14-page trial-court bundle: mostly handwritten English on printed forms (11 pages) and handwritten Assamese (about 3 distinct pages, one of them scanned twice). It is a phone scan with no text layer. There is no reference translation and no Assamese-reading reviewer yet, so every score below is against reference terms I read by eye from the page images. That reading is not independent, and the matching is lenient (punctuation and spaces ignored, partial matches count), so true accuracy is at or below these numbers. One document is a first look, not an accuracy figure.

| Candidate | English pages, all (11) | Handwritten English pages only (3 to 10) | Handwritten Assamese pages |
|---|---|---|---|
| Free OCR (Tesseract) through the `legal-ocr-service` code, as published | 11% | 11% | nonsense; the phone number on the page was not recovered in any setting |
| Same code with its page rendering fixed to 300 dpi | 18% | 10% | nonsense |
| **Sarvam Vision**, language set per page | **79%** | **85%** | readable in places, many wrong letters, see below |
| **Sarvam Vision**, language left unset | **83%** | **90%** | same |

**Sarvam Vision, English handwriting: strong at full resolution.** The handwritten cause-of-death opinion, which free OCR lost completely, came out essentially word for word. Case and section numbers, dates and times on the forms were mostly right.

**Sarvam Vision, problems found (all silent: the output has no confidence field and an empty warnings list, even on wrong text):**
- **Invented text.** Caption-style descriptions of stamps were inserted into the output on at least 3 of 14 pages ("The image displays an official seal..."). On one page the Assamese caption named the wrong city for the court and described the national emblem as a person.
- **Inconsistent numbers.** On the FIR form the output gave the FIR number twice, once correct and once with a digit dropped.
- **Names garbled,** including the accused's name, which was read differently on each page it appears. Names are where the readings disagree most.
- **Rotated page missed.** On a page scanned sideways, the table was read but the whole handwritten Assamese column was omitted (0 Assamese characters).
- **Setting-dependent.** On one printed form with handwritten entries, the page-specific language setting recovered 0 of 9 reference terms and leaving it unset recovered 8 of 9.
- **Unstable on Assamese.** The same handwritten page, scanned twice, was read with only 13% agreement between the two outputs. Assamese was also mixed with Bengali letter forms. Earlier trials on small crops (about 1,200 px wide) were much worse than the full-resolution page, so resolution matters.
- **The date of the incident** is read as different dates by different readers (Sarvam and two separate Claude readings, one of the English form and one of the Assamese complaint). No tool flagged the disagreement, and no one has verified the true date yet.

**Sarvam Translate on clean sentences (8 invented Assamese and Kannada witness-statement lines with known English).** All 8 were broadly right, including dates, times and numbers. Two points a person must catch: "accused" came out as "defendant" in one line, and "got my statement signed" came out as "took my statement and signed it", which shifts who signed. A translator should review legal terms and who did what.

**What this changes in the plan**
1. **Handwritten English pages:** a strong reading tool exists, so these can be a reading aid for the lawyer, provided the numbers, dates and names are checked against the original. Formal marking is still needed.
2. **Handwritten Assamese pages:** not usable without a person who reads Assamese. A machine draft may still help the translator, but that is unproven, and the reading and translating steps should stay separate.
3. **Design rule confirmed:** the tool must show the page image beside the text, strip invented captions, and flag lines where two readers disagree or where numbers repeat inconsistently. Sideways pages need rotating first. Each page should be read both with and without the language setting, and the two readings compared.

**Still to run:** Gemini and Google Cloud Vision at full resolution (no key available yet), the line-by-line strip method with two readers, Jurisphere and Niyam (upload the same pages), and a person marking the Assamese pages against a reference translation.

### 10b. First real reference and the line-strip method (recorded 2026-10-26; counts only, no case text)

**What was tested.** One handwritten Assamese complaint page (a 1,217 x 892 px image). The lawyer's side supplied the meaning in English as a gist (not word for word), so the page was scored on 15 facts it states: the district, "Sir", the incident date, about 7 pm, the husband and his name, age, "not at home", "came drunk", "dragged out", "various body parts", "near-dying", the date found, the word for FIR, and the request for action. Matching is strict: a fact counts only if the expected word or number appears. A near miss such as a drink word spelled slightly differently is counted as a miss.

| Reading of the same image | Facts found (of 15) |
|---|---|
| Gemini 3.5 Flash, whole page, run 1 | 9 |
| Gemini 3.5 Flash, whole page, run 2 | 12 |
| Gemini 3.5 Flash-Lite, whole page | 10 |
| Sarvam Vision, full-resolution page | 8 |
| Gemini 3.5 Flash, line strips | 8 |
| Gemini 3.5 Flash-Lite, line strips | 6 |
| Sarvam Vision, line strips | 6 |

**Findings**
1. **Cutting the page into enlarged line strips did not help.** Each model scored the same or lower on strips than on the whole page. The two whole-page runs of the same Gemini model differed by 3 facts, so the strip effect is inside the model's own run-to-run noise. This is one image, so it is a first signal, not a verdict.
2. **No reading got the incident date right except one run.** Whole-page and strip readings gave 26, 27 or an unresolved digit for a date that the reference gives as 29. Only one whole-page Gemini run read 29.
3. **All three strip readers agreed on the husband's age and all were wrong** (they read 50; the reference says about 40). **Agreement between readers is not correctness.** Two readers agreeing on a wrong digit would not be flagged. Reader disagreement caught the date-found error (Sarvam read it right, both Gemini models wrong), but not the age.
4. **Wrong place names, silently.** On the district line, Sarvam's strip reading produced a place that is not the district (one reading named another state's name). Both Gemini models read the district correctly on every strip.
5. **Nobody read "I was not at home" or "drunk" correctly as written** (Sarvam's strip reading of "drunk" was a near miss).
6. **My earlier English-page scores overstated usability for critical digits.** The reference now gives the incident date as 29, and Sarvam read the same date on the English FIR form differently (as 22). That date was not among the reference terms used for the 79 to 83% figure in section 10, so a high term score can hide a wrong critical number.

**What this changes in the plan**
- **Every date, age, amount and section number goes to a person for checking, whatever the readers say.** Reader agreement is not a safeguard for digits.
- **Do not build the strip method as an accuracy fix.** Keep it only if a later, larger test shows a gain.
- **The free-tier Gemini models and Sarvam are about equally unreliable on this handwriting.** A stronger model (paid tier) is still untested.
- **Scoring is now possible** with the lawyer's gists. More reference gists, ideally the translator's full versions, are the most valuable next input.

### 10c. Paid-tier Gemini run on the same page (recorded 2026-10-26; counts only, no case text)

**What was tested.** The same handwritten Assamese complaint page as 10b (1,217 x 892 px), whole page, one prompt asking for a line-by-line transcription with `[unclear]` and `(?)` for doubtful words, temperature 0, 3 runs per model, with `ocr_tests/gemini_read_check.py`. The billing-enabled key could call `gemini-3.1-pro-preview` and `gemini-4-argon`, which the free key could not (quota error). `gemini-3.5-flash` was rerun on the same key for comparison. `gemini-3.8-flash` returned HTTP 503 (overloaded) and then timed out, so it is **not tested**. Total use was about 44,000 tokens; the fee was not checked.

**How it was scored, and why it is not comparable with 10b.** The private 15-fact file of 10b was not available in this session. I wrote a **9-fact** file myself before the run (district, "Sir", incident date, about 7 pm, "husband", the husband's name, his age, the date found, the word for FIR). Three are critical numbers: incident date 29 and age about 40 (both from the 10b reference) and the date found, read as 30 **from the page image by me, not from a reference**. That reading is not independent of the models. The other 6 facts of 10b (not at home, drunk, dragged out, body parts, near-dying, request for action) could not be pattern-scored; the "not at home" and closing-request rows below were compared by hand against the saved readings, with no reference. All counts are therefore "of 9", not "of 15".

| Reader (3 runs each) | Facts found, per run (of 9) | Critical numbers, per run (of 3) | Incident date 29 | Age 40 | Closing request kept | "Not at home" present | `[unclear]` / `(?)` marks per run |
|---|---|---|---|---|---|---|---|
| **gemini-4-argon** | 9, 9, 9 | 3, 3, 3 | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | 0, 0, 0 |
| gemini-3.1-pro-preview | 8, 8, 8 | 2, 2, 2 | 3 of 3 | **0 of 3** (read 50) | **1 of 3** | 1 of 3 | 0, 0, 0 |
| gemini-3.5-flash (rerun) | 6, 7, 5 | 1, 2, 1 | 1 of 3 (read 21 and 25 in the others) | 0 of 3 (read 50) | 3 of 3 | 0 of 3 | 6, 2, 3 |

**Findings**
1. **`gemini-4-argon` is the first reader in this project to read all three critical numbers correctly, in every run.** It is also the first to read the age as 40; the three strip readers in 10b all read 50, as did the other two models here. This is one image and three temperature-0 runs, which are not independent samples. It is a lead worth testing on more pages, not an accuracy figure.
2. **A bigger model was not a better reader.** `gemini-3.1-pro-preview` read the age as 50 in all three runs, with no warning mark. Run-to-run agreement is not correctness (the same lesson as 10b, finding 3).
3. **Silent truncation.** `gemini-3.1-pro-preview` stopped early in 2 of 3 runs (one after the FIR sentence, one in the middle of a word), dropping the closing request, with no error and no mark. The script did not record why. The likely cause is the 8,192-token output limit being shared with the model's own thinking; this is not confirmed.
4. **The "not at home" phrase** was read by `gemini-4-argon` in 3 of 3 runs, by `gemini-3.1-pro-preview` in 1 of 3 (the other two replaced it with an intoxication phrase) and by `gemini-3.5-flash` in 0 of 3. By hand, no reference.
5. **Names and the manner of the beating differ between runs** in every model. For the beating, `gemini-4-argon` gave the same reading in 3 of 3 runs and `gemini-3.1-pro-preview` gave three different ones. These are the lines most likely to change what the evidence says and need a person who reads Assamese.
6. **Warning marks do not track errors.** `gemini-4-argon` and `gemini-3.1-pro-preview` produced no marks at all, including on lines where the names differed between runs. `gemini-3.5-flash` marked 11 spots over 3 runs, but its two wrong incident dates (21, 25) carried no mark on the wrong digit.

**Translation step (not scored).** To let the lawyer check the readings, each of the 9 readings was translated into English by `gemini-4-argon`, told to translate literally and not to correct the reading. The drafts sit beside the page image on a private page outside this repository. Two choices of the translator need a human: a name-like word in the position of the accused is rendered "the accused", and the deceased-marker symbol before the husband's name is rendered "Late". These are translator interpretations, not words on the page. No person who reads Assamese has checked the English.

**A scoring bug, now fixed.** The first-pass scores were wrong because the script did not unify Bengali y-with-dot stored composed or decomposed, so correct readings of two words were marked as missed (first pass: 9, 7, 7 / 7, 7, 7 / 6, 6, 5). `ocr_tests/gemini_read_check.py` now normalises text and patterns to NFD and reports any reading whose finish reason is not `STOP`. The fix was checked on the saved readings with the unchanged facts file (now 9, 9, 9 / 8, 8, 8 / 6, 7, 5) and by a selftest case that fails on the old code. **Earlier scores in 10 and 10b may be understated for any fact containing y-with-dot, r-with-dot or rh-with-dot.** They were not recomputed, because those readings and the 15-fact file are not in this repository.

**What this changes in the plan**
- **`gemini-4-argon` becomes the lead candidate for handwritten Assamese reading, to be tested on at least 3 or 4 more handwritten pages** before any recommendation. One page cannot support one.
- **Every date, age, amount and section number still goes to a person**, whatever the reader. A reader that gives no warning marks (here, two of the three) cannot flag its own errors.
- **Reading and translating stay separate steps.** The English drafts above inherit every reading error and add the translator's own choices.
- **Set the output limit higher or lower the thinking effort for the larger models**, and treat any run whose finish reason is not `STOP` as failed.
- **Still to run:** Google Cloud Vision at full resolution, `gemini-3.8-flash` when it is not overloaded, Jurisphere and Niyam, the two-reader check, and a person who reads Assamese marking the English against a reference translation (the translator's full version is still the most valuable input).

### 10d. A clean handwritten Assamese letter, 13 readers, a real English reference (recorded 2026-10-26; counts only)

**What was tested.** A clean, well-formed handwritten Assamese complaint letter (618 x 1,032 px), a fill-in **template with no real case data** (the police station name, address, and the writer's name and address are left as blanks). The lawyer supplied the English translation of the page, so for the first time the readings are scored against **a reference from a person**, not against my own reading. The reference fixes the letter date (03/09/2025), the incident date (20/08/2025, written "Monday"), the name of the person who borrowed, the amount (20,000), "borrowed", "could not repay me", and "out of reach for 3 days". 50 readings in all: whole page, the same prompt as 10c (line-by-line, `[unclear]` and `(?)` for doubtful words), temperature 0, output limit 32,768 so nothing was cut off. Three runs per reader where it answered.

- **Key A**: the billing-enabled key of 10c (19 readings, six Gemini models and Sarvam Vision).
- **Key B** (`GEMINI_FREE_OCR_KEY`, added 2026-10-26): 31 readings, ten Gemini models and one Gemma. It answered `gemini-3.1-pro-preview` and `gemini-4-argon`, which the first free key could not in 10c. I cannot tell from the API which tier this key is on, so "free" is the owner's label.

**How it was scored.** 20 facts, written as patterns on the Assamese text: 3 critical numbers (letter date, incident date, amount), 2 critical meanings (the money was **borrowed**; he **failed to repay me**), plus the name, the weekday, the agreement, the phone, "3 days", "helpless", "investigation", "justice", the three blanks and the closing. Two of my patterns were wrong on the first try (they missed correct readings) and were fixed before any score was used; the final patterns are in the private facts file, not in this repository. A person who reads Assamese has not yet checked the readings line by line, so a reading can still hide an error my 20 facts do not test.

| Reader (readings) | Facts per run (of 20) | Critical per run (of 5) | Wrong dates | Lost a meaning | Notes |
|---|---|---|---|---|---|
| **Key A** `gemini-3.5-flash` (3) | 20, 20, 20 | 5, 5, 5 | 0 | 0 | |
| **Key A** `gemini-3.6-flash` (3) | 20, 20, 20 | 5, 5, 5 | 0 | 0 | 1 reading starts with an English intro line |
| **Key A** `gemini-3.7-flash` (1 of 3 runs) | 20 | 5 | 0 | 0 | 2 runs failed (overloaded, timeout) |
| **Key A** `gemini-3.5-flash-lite` (3) | 18, 20, 20 | 3, 5, 5 | 1 reading (both dates) | 0 | |
| **Key A** `gemini-4-argon` (3) | 19, 19, 20 | 4, 4, 5 | 2 (incident month 06) | 0 | |
| **Key A** `gemini-3.1-pro-preview` (3) | 20, 19, 19 | 5, 4, 4 | 2 (letter month 07) | 0 | |
| **Key A** `sarvam-vision` (3: language set twice, unset once) | 18, 18, 18 | 3, 3, 3 | 0 | **3 of 3** | all dates right; two meanings changed |
| Key B `gemini-3.5-flash` (3) | 20, 20, 20 | 5, 5, 5 | 0 | 0 | 1 mark, on a non-critical word |
| Key B `gemini-3.6-flash` (3) | 20, 20, 20 | 5, 5, 5 | 0 | 0 | |
| Key B `gemini-3.1-flash-lite` (3) | 20, 20, 20 | 5, 5, 5 | 0 | 0 | |
| Key B `gemini-3.7-flash` (1 of 3 runs) | 20 | 5 | 0 | 0 | 2 runs failed (overloaded) |
| Key B `gemini-3.5-flash-lite` (3) | 20, 18, 20 | 5, 3, 5 | 1 reading (both dates) | 0 | |
| Key B `gemini-pro-latest` (3) | 19, 20, 20 | 4, 5, 5 | 1 (letter month 07) | 0 | alias; the model behind it can change |
| Key B `gemini-flash-lite-latest` (3) | 20, 18, 18 | 5, 3, 3 | 2 readings (both dates) | 0 | alias; 1 reading begins with a stray Latin word |
| Key B `gemini-4-argon` (3) | 19, 19, 19 | 4, 4, 4 | 3 (incident month 06) | 0 | |
| Key B `gemini-3.1-pro-preview` (3) | 19, 19, 19 | 4, 4, 4 | 3 (letter month 07) | 0 | |
| Key B `gemini-3-flash-preview` (3) | 18, 18, 18 | 3, 3, 3 | 3 (year 2023 in both dates) | 0 | marked `(?)` on the letter date in 3 of 3 runs and on the incident date in 1 |
| Key B `gemma-4-26b-a4b-it` (3) | 10, 10, 10 | 2, 2, 2 | 3 (incident month 06) | **3 of 3** | wrong name; meaning lost or invented; see below |

Not completed on key B: `gemini-3.8-flash` and `gemini-flash-latest` (overloaded, then timed out), `gemma-4-31b-it` (HTTP 500 and 503).

**Findings**
1. **The errors that mattered were digits, not meaning, for every Gemini model.** Across the 44 Gemini readings, none lost "borrowed" or "could not repay me" and none got the name wrong. **18 of the 44 (41%) had at least one wrong date**, and 21 of all 50 readings did. The wrong values were the incident month (06 instead of 08), the letter month (07 instead of 09) and, for one model, the year (2023).
2. **Silent errors.** Of the 21 readings with a wrong date, only 3 carried any warning mark, and all 3 were `gemini-3-flash-preview` on its wrong year. The other 18 were silent. Across all 50 readings only 9 had any mark at all, and the only marks on a date line were on `gemini-3-flash-preview`'s dates. This repeats the 10b and 10c finding that a missing warning means nothing.
3. **Sarvam Vision has the opposite weakness.** It got every date, the name and the amount right in all 3 jobs (language set or unset), but in all 3 it changed two words: "borrowed" came out as a word meaning "to hold", and "could not repay me" came out as "could not see me". The reference confirms both are wrong, and neither carried a warning. A comparison of Sarvam against Gemini would have flagged every one of the 18 wrong Gemini dates, and a comparison of Gemini against Sarvam would have flagged both changed words. That is a reason to keep the two-reader check on the plan, not proof it works: here the two readers happen to fail in different places, while in 10b the three strip readers agreed on a wrong age.
4. **Rankings are not stable.** The same model with the same prompt gave different answers on the two keys (`gemini-4-argon`: incident month right in 1 of 3 runs on key A and 0 of 3 on key B; `gemini-3.1-pro-preview`: letter month right in 1 of 3 on key A and 0 of 3 on key B). Between-model differences on one page are no larger than that run-to-run noise, with two exceptions: `gemini-3.5-flash` and `gemini-3.6-flash` were fully right in all 6 of their readings each (both keys), and `gemini-3-flash-preview` was wrong in all 3 of its readings. **The "lead candidate" status given to `gemini-4-argon` in 10c did not hold on a second page**: it wrote the incident month wrong in 5 of 6 runs here.
5. **`gemma-4-26b-a4b-it` is not usable for this.** It read 10 of 20 facts, wrote the person's name as a different name, and in place of "could not repay me" wrote words that read as "could not give my phone". It produced no warning marks.
6. **Smaller output problems.** One `gemini-flash-lite-latest` reading began with a stray Latin word, and one `gemini-3.6-flash` reading began with an English intro line, against the "add nothing" instruction. No reading was cut off.
7. **The page contradicts itself.** The written weekday (Monday) does not fit 20/08/2025, which was a Wednesday, and it does not fit 20/06/2025 either (a Friday). The reference keeps "Monday". A calendar check can flag such a page for a person; it cannot say which part is wrong.

**What this changes in the plan**
- **Dates are the weak spot on a clean page, and models produce them confidently.** Every date goes to a person, as in 10b, whatever the reader says.
- **Do not pick one model on one page.** No model is recommended. The two readers that were right on every run here (`gemini-3.5-flash` and `gemini-3.6-flash`, on both keys) are the ones to include in the next, larger test, together with Sarvam Vision as the second reader.
- **Reading and translating stay separate.** A reader that changes one word (Sarvam) changes what the English will say, with nothing to warn the translator.
- **The English reference now exists, so a translation test is possible** (reading, then English, scored against the reference). That has not been run.
- **Still to run:** Google Cloud Vision, Jurisphere and Niyam, the translation step against this reference, more handwritten pages (including messy ones), and a person who reads Assamese marking the readings line by line.

### 10e. Cost and speed per model, the messy page again with cheaper models, and a correction (recorded 2026-10-26; counts only, no case text)

*Cost note (added 2026-10-27): the per-page costs in this section are lower bounds; see 10k.*

**Correction first.** The English text supplied as "the closest translation" of a handwritten notes page (a page of Assamese-language notes, no case data) is **word-for-word identical to the `gemini-4-argon` run 1 output**, down to a bracketed "[through]" and the British spelling "favourable". It is a model output, not an independent translation, so scoring against it would give `gemini-4-argon` 100% by construction. **No reader was scored against it, and no ranking on the notes page is valid.** An independent human English version of that page is still needed.

**Notes page: what can be counted without a reference.** 12 readers, 34 readings (each model transcribed and translated in one call, 3 runs; Sarvam read with Vision and translated with Sarvam Translate). The prompt told every model to ignore writing showing through from the back and to stop where the text stops. The page breaks off mid-sentence.

| Reader | Readings | Rendered the word for letter-based / articulate sounds as "descriptive" | Finished the broken-off sentence | Reads as English (my judgment) |
|---|---|---|---|---|
| `gemini-4-argon` | 3 | 0 | 0 | fluent |
| `gemini-3.8-flash` | 1 | 0 | 0 | fluent |
| `gemini-3.5-flash` | 3 | 0 | 0 | fluent |
| `gemini-3.6-flash` | 3 | 0 | 0 | fluent; stray repeated word in 2 |
| `gemini-3.5-flash-lite` | 3 | 3 | 0 | fluent to stilted |
| `gemini-flash-lite-latest` | 3 | 2 | 0 | stilted, 1 broken |
| `gemini-3.1-flash-lite` | 3 | 3 | 0 | stilted |
| `gemini-3-flash-preview` | 3 | 1 | 0 | stilted, 1 broken |
| `gemini-3.1-pro-preview` | 3 | 3 | 0 | stilted, 1 broken |
| `gemini-pro-latest` | 3 | 3 | 0 | stilted (Assamese word order carried over) |
| `sarvam-vision` + Translate | 3 | 3 | **3** (invented an ending) | fluent, not faithful |
| `gemma-4-26b-a4b-it` | 3 | 0 | 0 | broken (14 unclear marks per reading) |

"Descriptive" is my judgment of a mistranslation and needs a person who reads Assamese. The two pro-tier models used it in every reading, where `gemini-4-argon` and the 3.5, 3.6 and 3.8 flash models wrote "phonetic" or "articulate". Readers also split on two contested words (22 readings say "place of expression", 11 say "result of expression"; all 31 Gemini and Gemma readings say "through / for the purpose of this discussion", all 3 Sarvam readings say "at the beginning of"); these are not ruled on. The reading and translation come from one call, so a reading error and a translation error cannot be told apart.

**Cost and speed.** One streaming call per run, 3 runs per model, the notes-page photograph (1,108 x 715 px), the same prompt as above, temperature 0, output limit 32,768 tokens. Latency is the time to the first answer token; response time is the time until the answer is complete. Cost per page is computed from the exact token counts the API returned (input tokens, plus output tokens and hidden "thinking" tokens, which are billed as output) at the prices below. **Rupees at about Rs 96 per US dollar**: the last RBI reference rate found was 96.29 on 18 May 2026, and a third-party quote of about 95.95 in mid-September agrees; no late-October rate was found, so treat the rupee figures as approximate and re-check at the time of payment.

| Model | Latency (s) | Response time (s) | Tokens in / out / thinking | Cost per page | Cost per 1,000 pages |
|---|---|---|---|---|---|
| `gemini-3.1-flash-lite` | 1.5 | 2.5 | 1,239 / 373 / 0 | Rs 0.08 | Rs 83 |
| `gemini-3.5-flash-lite` | 1.9 | 2.6 | 1,239 / 372 / 0 | Rs 0.13 | Rs 125 |
| `gemini-flash-lite-latest` | 1.3 | 2.1 | 1,239 / 376 / 0 | unknown | unknown |
| `gemini-4-argon` | 4.6 | 7.3 | 1,274 / 389 / 0 | Rs 0.62 (promo) / Rs 1.24 (after) | Rs 618 / Rs 1,236 |
| `gemini-3-flash-preview` | 9.0 | 10.0 | 1,239 / 389 / 2,156 | Rs 0.79 | Rs 792 |
| `gemini-3.5-flash` | 10.6 | 12.1 | 1,239 / 376 / 2,000 | Rs 2.23 | Rs 2,231 |
| `gemini-3.6-flash` | 12.6 | 14.1 | 1,239 / 390 / 1,717 | Rs 0.85 (promo) / Rs 1.70 (after) | Rs 848 / Rs 1,695 |
| `gemini-3.7-flash` (2 runs) | 175 | 178 | 1,239 / 376 / 648 | Rs 0.46 (promo) | Rs 458 |
| `gemini-3.8-flash` (1 run) | 92 | 95 | 1,239 / 379 / 629 | Rs 0.45 (promo) | Rs 452 |
| `gemma-4-26b-a4b-it` | 12.3 (8 to 34) | 20.3 (16 to 42) | 431 / 392 / 0 | unknown | unknown |
| `gemini-3.1-pro-preview` | not measured | not measured | about 4,350 total in earlier runs | about Rs 3.8 (estimate) | about Rs 3,800 |
| `gemini-pro-latest` | not measured | not measured | about 4,350 total in earlier runs | unknown | unknown |
| Sarvam Vision + Translate | about 14 (Vision) + 1.5 (Translate) | about 15 | 468 characters read | Rs 1.44 (Rs 0.50 per page + Rs 2 per 1,000 characters of translation) | Rs 1,440 |

Medians of 3 runs unless stated. `gemini-3.1-pro-preview` and `gemini-pro-latest` returned HTTP 503 (overloaded) on all 9 timing attempts, so they have no timing; they completed in earlier untimed runs. The 175 s and 95 s of `gemini-3.7-flash` and `gemini-3.8-flash` look like queueing under overload, not normal speed. Sarvam's Vision time is only to about 10 s, because the script polls every 10 s. The models on the second key (`GEMINI_FREE_OCR_KEY`) may cost nothing if that key is on a free tier; this could not be confirmed, so their costs above are at the paid rates.

**The prices are not verified.** They come from third-party price trackers and a web search; Google's own pricing page could not be opened from this environment. Per million input / output tokens: `gemini-4-argon` $2 / $10 as a promotional rate, then $4 / $20 (sources disagree on whether the model is publicly available); `gemini-3.1-pro-preview` $2 / $12; `gemini-3.5-flash` $1.50 / $9; `gemini-3.5-flash-lite` $0.30 / $2.50 (one source); `gemini-3.1-flash-lite` $0.25 / $1.50; `gemini-3-flash-preview` $0.50 / $3; `gemini-3.6-flash`, `3.7-flash` and `3.8-flash` $0.75 / $3.75 as a Vertex introductory rate to 31 December 2026, then $1.50 / $7.50 (the Developer API rate may differ). No price was found for `gemma-4-26b-a4b-it`, and the API does not say which model the two `-latest` aliases point to. Sarvam's rupee prices are from its docs page as recorded in `ocr_tests/README.md` on 2026-10-25.

**The first messy page again, with four cheaper models.** The page of 10 to 10c (handwritten complaint; 3 runs each, 9 private facts, critical numbers: incident date 29, husband's age 40, and a date found, which is my reading of 30). `gemini-4-argon` (10c) read all three critical numbers in every run. Of the new readers: `gemini-3.6-flash` read the incident date as 26 and the age as 50 in all 3 runs (with 3 to 6 warning marks per reading); `gemini-3.1-flash-lite` the same (26 and 50, no warning marks); `gemini-3.5-flash-lite` read 26 and 27 for the two dates in all 3 runs and the age as 40 in 1 of 3; `gemini-3-flash-preview` read both dates right and the age as 50 in all 3 runs, with no warning marks. Only `gemini-4-argon` read the age as 40 in every run.

**What this changes in the plan**
- **Best reader so far for messy handwriting: `gemini-4-argon`, as a lead and not a verdict.** It is the only reader with all three critical numbers on the messy page in every run, takes about 7 s and costs about Rs 0.6 to 1.2 per page at the listed prices. On the clean letter of 10d it wrote the incident month wrong in 5 of 6 runs, and `gemini-3.5-flash` and `gemini-3.6-flash` were right in every run (6 of 6 each). No model is best on every page.
- **Use two readers and a person.** `gemini-4-argon` plus `gemini-3.6-flash` costs about Rs 1.5 to 3 per page and takes about 14 s if the two calls run in parallel (about 21 s one after the other). On the two digit-heavy pages, every critical digit error `gemini-4-argon` made was met by a disagreement from `gemini-3.6-flash`, which would flag the line. This is a small sample, and agreement between readers is not correctness (10b). Every date, age and amount still goes to a person.
- **The pro-tier models are not worth their cost here.** About Rs 3.8 per page, often overloaded, and on the messy page they read the age wrong in all 3 runs with no warning (10c).
- **The cheapest models are not for reading.** At Rs 0.1 per page and 2.5 s they are fast, but they failed the messy page. They may suit first-pass triage.
- **Reading and translating stay separate steps.** A fixed translator applied to every reading would separate reading errors from translation errors; this has not been run.
- **Still to run:** an independent human English version of the notes page; a human-marked reference for more messy handwritten pages; Google Cloud Vision, IndicTrans2 and Google Translate; Jurisphere and Niyam; and the same cost and speed test on a bigger batch of pages, when the overloaded models are available.

### 10f. Cost against efficiency, ranked (recorded 2026-10-26; counts only, no case text)

*Cost note (added 2026-10-27): the per-page costs in this section are lower bounds; see 10k.*

**The question.** Which model gives the most reliable reading of handwritten Assamese for the least money, using only the results in 10c to 10e.

**How efficiency is defined.** *Accuracy* on a page is the share of its critical values a model read right across its runs. The messy handwritten complaint of 10 to 10c has 3 critical values per run (incident date, husband's age, date found; the third is my own reading of the image, the other two come from the lawyer's reference). The clean letter of 10d has 5 per run (letter date, incident date, amount, and the two meaning words "borrowed" and "could not repay me"; from the lawyer's English reference), with the two keys pooled. *Quality Q* is the average of the two page accuracies, or the clean-letter accuracy alone where the messy page was not tested. *Efficiency* is Q divided by the cost per page in rupees (about Rs 96 per US dollar; third-party and unverified prices, see 10e). **The ranking puts models that passed a gate on the messy page first**, each group ordered by efficiency. The gate is: all three critical numbers read right in at least one run. Plain accuracy per rupee ranks the two cheapest models first, because they cost almost nothing, even though neither read the messy page; a reader that fails the hard page still needs a person to check every page, so its low price saves little. The plain rank is in the last column so the effect of the gate is visible.

| Rank | Model | Messy page | Clean letter | Quality Q | Cost per page | Response time | Efficiency (Q per Rs) | Plain rank |
|---|---|---|---|---|---|---|---|---|
| 1 (passed the gate) | `gemini-4-argon` | 100% | 83% | 0.92 | Rs 0.62 (then Rs 1.24) | 7.3 s | 1.48 (then 0.74) | 4 |
| 2 (failed the gate) | `gemini-3.1-flash-lite` | 33% | 100% | 0.67 | Rs 0.08 | 2.5 s | 7.99 | 1 |
| 3 (failed the gate) | `gemini-3.5-flash-lite` | 11% | 87% | 0.49 | Rs 0.12 | 2.6 s | 3.91 | 2 |
| 4 (failed the gate) | `gemini-3-flash-preview` | 67% | 60% | 0.63 | Rs 0.79 | 10.0 s | 0.80 | 5 |
| 5 (failed the gate) | `gemini-3.6-flash` | 33% | 100% | 0.67 | Rs 0.85 (then Rs 1.70) | 14.1 s | 0.79 (then 0.39) | 6 |
| 6 (failed the gate) | `gemini-3.5-flash` | 44% | 100% | 0.72 | Rs 2.23 | 12.1 s | 0.32 | 8 |
| 7 (failed the gate) | `gemini-3.1-pro-preview` | 67% | 83% | 0.75 | Rs 3.82 | not measured | 0.20 | 9 |
| 8 (not rated on the messy page) | `gemini-3.7-flash` | not tested | 100% | 1.00 (clean letter only) | Rs 0.46 (then Rs 0.92) | 178 s | 2.18 (then 1.09) | 3 |
| 9 (not rated on the messy page) | `sarvam-vision` | not tested | 60% | 0.60 (clean letter only) | Rs 1.44 | 15.0 s | 0.42 | 7 |
| 10 (not rated on the messy page) | `gemini-3.8-flash` | not tested | not tested | no data | Rs 0.45 (then Rs 0.90) | 94.6 s | n/a | n/a |
| 11 (not rated on the messy page) | `gemini-pro-latest` | not tested | 93% | 0.93 (clean letter only) | unknown | not measured | n/a | n/a |
| 12 (not rated on the messy page) | `gemini-flash-lite-latest` | not tested | 73% | 0.73 (clean letter only) | unknown | 2.1 s | n/a | n/a |
| 13 (not rated on the messy page) | `gemma-4-26b-a4b-it` | not tested | 40% | 0.40 (clean letter only) | unknown | 20.3 s | n/a | n/a |

Messy-page accuracy is out of 9 critical values (3 runs of 3) for the seven models tested on it; the clean letter is out of 5 per run, with up to 6 runs per model. Rows with an unknown price have no efficiency. `gemini-3.8-flash` has no accuracy data. The notes page of 10d and 10e is not in these figures because its reference was a model output.

**What the ranking says**
1. **`gemini-4-argon` is the most efficient reader that can read the messy page at all**, at about Rs 0.62 and 7 s a page. If its promotional price ends, efficiency halves (1.48 to 0.74) and it stays first, because no other model passed the gate.
2. **The cheapest models are the least useful for this job.** The two lite models cost Rs 0.08 to 0.13 a page and answer in under 3 s, so they top the plain ranking, but they read 1 to 3 of 9 critical numbers on the messy page. They may suit a first triage, not reading.
3. **The pro-tier model is the least efficient**: about Rs 3.8 a page for no better messy-page result than models costing a fifth as much, and it was overloaded when timed.
4. **The two flash models that were perfect on the clean letter fail the messy page.** A second reader earns its cost: `gemini-4-argon` plus `gemini-3.6-flash` is about Rs 1.5 a page, and on the two digit-heavy pages every critical digit `gemini-4-argon` got wrong, `gemini-3.6-flash` disagreed with.
5. **Speed is a separate axis**: about 2.5 s for the lite models, 7 s for `gemini-4-argon`, 10 to 14 s for the flash models, and 95 to 178 s for the 3.7 and 3.8 flash models while overloaded.

**Limits.** The messy-page accuracy rests on **one page** and 3 temperature-0 runs per model, which are not independent samples; one page is the reason only one model passes the gate, and a second messy page could change the order. Other weights for the two pages would move the lower rows but not the top row. The cost of a person checking a page is not in these figures and is probably far larger than any model cost, which is why accuracy comes before price. Models on the second key may cost nothing if that key is on a free tier, which could not be confirmed.

**What this changes in the plan.** Run a second and third messy handwritten page before relying on the lead of `gemini-4-argon`, ideally with a human-marked reference for each; re-price once Google's own pricing page can be read; and keep a person checking every date, age and amount whatever the model.

### 10g. A second notes page, 14 readers; the owner found the `gemini-4-argon` reading closest (recorded 2026-10-26; counts only, no case text)

*Cost note (added 2026-10-27): the per-page costs in this section are lower bounds; see 10k.*

**What was tested.** A photographed page of handwritten Assamese notes (718 x 682 px, no case data) on how Old Indo-Aryan changed into Prakrit and then Assamese, with red underlining and writing showing through from the back of the paper. The page is cut off at the bottom in the middle of a point on the dual number. Every model transcribed and translated in one call (the same prompt as the first notes page of 10d and 10e: ignore writing from the back, stop where the text stops, mark doubtful words); Sarvam read with Vision and translated with Sarvam Translate. Three runs per reader where they answered, timed with one streaming call each; temperature 0; output limit 32,768 tokens.

**There is no reference translation for this page.** I scored 9 content items per reading against my own reading of the page, cross-checked with standard facts about the Prakrit sound changes: the line listing the sounds that were lost, "e and o replace ai and au", three word-change examples (oil, medicine, jackal), retroflex sounds increased, "simplified", "words became vowel-ending", and the dual number. That is not independent, and my reading was wrong on earlier pages (10d). Five models gave a lost-sounds line with all five lost sounds in every reading (`gemini-4-argon`, `gemini-3.1-pro-preview`, `gemini-3.6-flash`, `gemini-3.7-flash`, `gemini-3.8-flash`), and two more did in 2 of 3 (`gemini-pro-latest`, `gemini-3.5-flash`), which supports it but is agreement, not proof.

**The owner's check.** The owner compared the readings with the page and reported that **the `gemini-4-argon` reading came out the closest**. This is the owner's judgment and is recorded as such; it was not an independent line-by-line marking by a person who reads Assamese.

| Reader | Readings | Items right per reading (of 9) | Response time (median) | Cost per page | Main errors |
|---|---|---|---|---|---|
| **`gemini-4-argon`** | 3 | **9, 9, 9** | 11.8 s (range 7.0 to 103 s) | Rs 0.81 | none found |
| `gemini-3.1-pro-preview` | 2 of 3 | 9, 9 | 36 s | about Rs 5.9 | third run overloaded (503) |
| `gemini-3.7-flash` | 2 of 3 | 9, 9 | 217 s | Rs 1.59 | very slow under load |
| `gemini-3.8-flash` | 1 of 3 | 9 | 47 s | Rs 1.40 | other runs overloaded |
| `gemini-3.6-flash` | 3 | 9, 8, 9 | 29.5 s | Rs 2.36 | one wrong example; one extra sound listed |
| `gemini-pro-latest` | 3 | 9, 8, 9 | 33.5 s | price unknown | one wrong example |
| `gemini-3.5-flash` | 3 | 9, 8, 7 | 18.8 s | Rs 3.30 | wrong sound list in 1 run |
| `gemini-3-flash-preview` | 3 | 8, 8, 8 | 12.3 s | Rs 0.94 | sound list wrong in all 3 runs |
| `gemini-3.1-flash-lite` | 3 | 5, 5, 5 | 2.8 s | Rs 0.10 | invented the sound list; "oil > oil > oil"; jackal example wrong |
| `gemini-3.5-flash-lite` | 3 | 5, 5, 4 | 3.1 s | Rs 0.15 | invented the sound list and 2 of the 3 examples |
| `gemini-flash-lite-latest` | 3 | 4, 4, 4 | 2.6 s | price unknown | invented the sound list; nonsense words in one reading |
| `sarvam-vision` + Translate | 3 (language set twice, unset once) | 3, 3, 3 | about 15 s (not re-timed here) | about Rs 1.5 | see below |
| `gemma-4-26b-a4b-it` | 1 | 0 | 503 s, empty | unknown | no output |
| `gemma-4-31b-it` | 1 | 0 | 1,029 s, empty | unknown | no output |

Costs are at about Rs 96 per US dollar with the unverified third-party prices of 10e; Sarvam's is Rs 0.50 per page plus Rs 2 per 1,000 characters translated.

**Findings**
1. **`gemini-4-argon` read all 9 items in all 3 runs, and the owner found its reading closest.** It uses no hidden thinking tokens, so its cost per page moved little between pages (Rs 0.62 on the first notes page, Rs 0.81 here). One of its three runs took 103 s to answer, which looks like an overload spike.
2. **The lite models invented content on a dense page.** In all 9 lite readings the line listing the lost sounds was wrong, and in all 3 lite models the word-change examples were wrong, missing or invented in every reading ("oil > oil > oil"; one reading contained a foreign place name in place of the word for "common people"). `gemini-3.1-flash-lite` gave no warning marks at all. This is more serious than their messy-page result of 10c to 10e, where they only missed digits.
3. **Sarvam changed meanings silently, again.** It read "simplified" as "strong" (so the English says "strengthened"), "words became vowel-ending" as "words became distinct", got the lost sounds and the jackal word wrong, and dropped "o" from "e and o". It was fluent, with no warning marks. This matches 10d.
4. **No reader finished the sentence that breaks off.** All 34 readings, Sarvam's included, stop at the dual number.
5. **Thinking models cost 2 to 3 times more on a dense page.** `gemini-3.6-flash` went from Rs 0.85 on the first notes page to Rs 2.36 here (3,600 to 6,700 thinking tokens against about 1,700), `gemini-3.5-flash` from Rs 2.23 to Rs 3.30, and `gemini-3.1-pro-preview` from about Rs 3.8 to about Rs 5.9. **The cost per page in 10e and 10f is therefore a lower bound for these models**, and their cost against efficiency order in 10f is more favourable to them than a denser page would show.
6. **The overloaded models** (`gemini-3.1-pro-preview`, `gemini-3.7-flash`, `gemini-3.8-flash`) completed only 1 to 2 of 3 runs, and the two Gemma models returned empty output after 8 and 17 minutes.

**What this changes in the plan**
- **`gemini-4-argon` stays the lead reader.** It is now first on the messy handwritten page (10c, 10e) and first on this page, with the owner's own check agreeing, but it was weak on the clean letter's incident month (10d). It still needs a second reader and a person for every date, age and amount.
- **Do not use the lite models to read** records like these pages, whatever they cost; they may serve for a first triage only.
- **10f's ranking is not redone here.** Its top row is unchanged by this page; its cost column is understated for the thinking models, and a three-page re-ranking with per-page cost shown would be the next step.
- **Still to run:** an independent human translation or line-by-line marking by a person who reads Assamese for this page and the first notes page; more messy handwritten pages with such a reference; Google Cloud Vision, IndicTrans2 and Google Translate; Jurisphere and Niyam.

### 10h. A printed land-revenue record: numbers, a land unit and one name (recorded 2026-10-26; counts only, no names, no record numbers)

*Cost note (added 2026-10-27): the per-page costs in this section are lower bounds; see 10k.*

**What was tested.** One photographed page of a printed Assam land-revenue record (a jamabandi): a table in Assamese and English with five holders, two plot numbers, areas in two units, revenue and local-tax columns, and a remarks cell carrying two circle-officer orders (with dates, order numbers and land quantities) and two officers' names in Latin script (1,455 x 875 px). It is a real record about real people. Nothing that identifies it (names, plot, order or patta numbers, the village) is written in this repository. Every model transcribed and translated in one call with a prompt adapted for a printed table (digits copied exactly as printed, no tidying, `[unclear]` for doubtful characters); Sarvam read with Vision (which returns an HTML table, flattened to text) and translated with Sarvam Translate in chunks under its 2,000-character limit. Three runs per reader where they answered; timed streaming calls; temperature 0; output limit 32,768 tokens.

**How it was scored, and the owner's corrections.** There is no reference translation. Three layers:
1. **18 plainly readable items** on the transcription (two dates and two order numbers, two land quantities, the plot number appearing three times, two officers' names, the lot number, the printed header fields, the heading, five holders, the transfer remark). Every reader scored 15 to 18; this layer does not separate them.
2. **The owner's check.** The owner reported that the first holder's name, the person the land was transferred from, was misread by `gemini-4-argon`, and that **everything else in the `gemini-4-argon` reading and translation was right**, including the circle officer's remarks ("mutated by way of inheritance"). It was one name only: the other four holders' names and the fathers' names were right, and across its three runs `gemini-4-argon` gave the same other names each time. This is the owner's judgment, recorded as such.
3. **On the owner's statement, two further scores.** *English details*: 10 pattern checks on the English of the remarks and header (inheritance; transferred to whom and from whom; the order's date and officer; both mutation numbers; both land quantities; both officers' names; no invented relationship; the header fields in English; no repetition loop). *Numbers against `gemini-4-argon`*: 10 number cells compared with the values `gemini-4-argon` gave (patta number, second plot number, two areas in bigha-katha-lessa, two areas in hectare-are-square-metre, two revenue figures, two local-tax figures). **The number score of `gemini-4-argon` is true by construction**, and its patta number read differently in one of its three runs, so that cell is uncertain.

| Reader | Readings | Name of the one misread holder, in the reading | English details (of 10) | Numbers vs `gemini-4-argon` (of 10) | Response time (median) | Cost per page |
|---|---|---|---|---|---|---|
| `gemini-4-argon` | 3 | wrong in all mentions (2 spellings, none right) | **10** | 9.7 | 16.9 s | Rs 1.71 |
| `gemini-3.1-flash-lite` | 3 | right in all | 10 | 7.0 | 4.3 s | Rs 0.19 |
| `gemini-3.7-flash` | 1 of 3 | near (one extra letter) | 10 | 9.0 | 50 s | Rs 1.25 |
| `gemini-3-flash-preview` | 3 | right in all | 9.0 | 7.3 | 42.4 s | Rs 3.25 |
| `gemini-3.1-pro-preview` | 2 of 3 | wrong | 10 | 8.0 | 73 s | Rs 11.5 |
| `gemini-3.8-flash` | 2 of 3 | near or wrong | 10 | 7.5 | 108 s (33 to 184) | Rs 1.34 |
| `gemini-flash-lite-latest` | 3 | right 4, near 2 | 9.3 | 6.3 | 4.0 s | price unknown |
| `gemini-3.5-flash-lite` | 3 | right 2, near 2, wrong 2 | 9.3 | 6.7 | 4.4 s | Rs 0.31 |
| `gemini-3.6-flash` | 3 | near 2, wrong 4 | 9.3 | 7.3 | 42.3 s | Rs 1.82 |
| `gemini-pro-latest` | 1 of 3 | wrong | 10 | 7.0 | 58 s | price unknown |
| `gemini-3.5-flash` | 3 | wrong in all | 8.3 | 7.0 | 28.6 s | Rs 4.94 |
| `sarvam-vision` + Translate | 3 | near 3, wrong 3 | **4** | 8.0 | about 15 s + 3 to 12 s | about Rs 2.7 |
| `gemma-4-26b-a4b-it` | 3 | no output (three empty answers) | none | none | none | unknown |

Costs at about Rs 96 per US dollar with the unverified third-party prices of 10e. The thinking models cost far more on this dense table (`gemini-3-flash-preview` once spent about 31,000 thinking tokens), while `gemini-4-argon` uses none.

**Findings**
1. **The Latin-script and printed items are not where readers differ.** All of them copied the dates, order numbers, quantities and officers' names. The differences are in the Assamese-digit cells, one land unit and one proper name.
2. **Assamese-digit cells split between readers.** Two areas and the first revenue figure were identical in all 30 readings. The second revenue figure read two ways in 15 and 14 readings (and a third in 1); the first local-tax figure read two ways (24 and 6); the second (25 and 5); the second plot number three ways (26, 2, 2). In Assamese the digit 4 looks like a Latin 8, which may be a cause. None of the splits carried a warning mark.
3. **Only `gemini-4-argon` read the two long area numbers (16 to 17 digits each) identically in all three runs**, and the owner found its reading right. No other model matched them in more than one reading, and the models that read the misread holder's name correctly most reliably (`gemini-3.1-flash-lite`, `gemini-3-flash-preview`, `gemini-flash-lite-latest`) read both long areas wrong in every reading.
4. **A land unit was misread in 7 of 30 readings** (the word for katha came out as other words, one of which means "speech" and one "which one"), by `gemini-3-flash-preview` in all 3 readings, `gemini-3.5-flash` in all 3 and `gemini-3.6-flash` in 1. Without a person this changes what a land quantity means, with no warning.
5. **Sarvam's English of the remarks was the furthest from the page.** It lost the inheritance, the order, both quantities and both officers' names, wrote the holders' fathers wrongly, and one of its three runs fell into a repetition loop. Its reading of the dates and order numbers was right. This matches 10d and 10g: Sarvam reads digits and dates well, and translates unfaithfully.
6. **Two lite models invented or hedged details**: one wrote the new holder as a "son-in-law" of the old holder, another wrote "inheritance/gift" in 2 of 3 readings.
7. **One wrong name, with no warning.** For `gemini-4-argon` it was one holder's name, spelled two different ways across its three runs (one in the first run, another in the second and third); a person reading the page against the output would catch it, and the disagreement between runs, and between `gemini-4-argon` and the lite models, would flag it. Consistency across runs is not a reliable flag: `gemini-3.5-flash` was consistently wrong.
8. **No warning marks on any number cell or the name.** only 2 of 30 readings carried any mark at all, and neither was on a number cell or the name.

**Limits.** One record, 3 runs of a temperature-0 model, not independent. The number cells are scored against the output of the model under test, on the owner's confirmation; the two long numbers should be confirmed digit by digit by a person. The four models `gemini-3.1-pro-preview`, `gemini-3.7-flash`, `gemini-3.8-flash` and `gemini-pro-latest` have 1 to 2 readings each because of overload. Prices are unverified. The "details" checks are patterns and can miss wording errors.

**What this changes in the plan**
- **`gemini-4-argon` stays the lead reader and translator for dense printed and handwritten records**, on the owner's finding that it was right except for one name.
- **A person must check every proper name against the original, every land unit, and every number written in Assamese digits**, whatever the reader says. These are the errors found so far, and none came with a warning.
- **Use two readers and compare, plus a re-run.** Differences between `gemini-4-argon` and a second reader, and between two runs of the same reader, flag the name and many of the number cells.
- **Do not use Sarvam Translate for the remarks of a record** without a person checking the English; it may still be useful as a second reader of dates and digits.
- **Still to run:** a human translator's version and line-by-line marking for this record and the notes pages; a decision on which tier of Gemini key may be used for client documents (the data-use terms of the key's tier were not checked); the rest of the plan's 30-page set.

### 10i. A full Assamese newspaper page: dropped text, changed names and digits (recorded 2026-10-27; counts only, no article text)

*Cost note (added 2026-10-27): the per-page costs in this section are lower bounds; see 10k.*

**What was tested.** One photographed Assamese newspaper page (1,127 x 826 px): masthead, a large headline, a photograph, a byline and six columns of small print, ending with a phone number. It is a published article, so nothing in it is confidential. Every model transcribed it in column order (a `[COLUMN n]` marker for each column, digits exactly as printed, `[unclear]` for doubtful words, stop where the text stops) and translated it in the same call. Sarvam read with Vision and translated with Sarvam Translate in chunks (two of its three reading jobs were translated, to limit cost). Timed streaming calls; temperature 0; output limit 32,768 tokens.

**How it was scored.** There is no reference translation. 37 items: 13 on the transcription (masthead; the headline words; the headline surname spelled as printed; the byline; the six years and ages or durations), 12 passages spread over the six columns, which detect dropped text, and 12 facts in the English. The reference is my own reading of the print, which I could read plainly but may have wrong; `gemini-4-argon` and Sarvam agree with it on every item, which is agreement, not proof. **The owner's verdicts, recorded as the owner's judgments:** `gemini-4-argon` was best on both meaning and details; `gemini-3.7-flash` got everything right (one reading); `gemini-3.5-flash` was second best on meaning and details; the other models changed the meaning or the names.

| Reader | Readings | Items right (of 37) | Response time (median) | Cost per page | Main differences from the print |
|---|---|---|---|---|---|
| **`gemini-4-argon`** | 2 of 3 | **37, 37** | 144 s (128 to 195) | Rs 3.62 | none found |
| `gemini-3.7-flash` | 1 of 3 | 36 | 259 s | Rs 1.68 | headline surname spelling changed |
| `gemini-3-flash-preview` | 3 | 36, 36, 34 | 28 s | Rs 2.04 | phone number wrong in all 3 |
| `sarvam-vision` + Translate | 2 | 36, 36 | about 25 s | about Rs 9.6 | byline surname spelling; an invented arrest in the English |
| `gemini-pro-latest` | 1 of 3 | 35 | 105 s | price unknown | one surname wrong |
| `gemini-3.6-flash` | 3 | 34, 35, 35 | 65 s | Rs 4.51 | phone number wrong in all 3; last line dropped in 2 |
| `gemini-3.5-flash` | 3 | 33, 35, 35 | 74 s | Rs 10.76 | last line dropped in 2; one phone digit pair swapped; imprisonment attributed to one event |
| `gemini-3.5-flash-lite` | 3 | 34, 31, 27 | 23 s | Rs 0.86 | last line dropped in 3; names and phone wrong |
| `gemini-flash-lite-latest` | 3 | 33, 29, 31 | 28 s | price unknown | last line dropped in 3; names wrong; an invented year |
| `gemini-3.1-flash-lite` | 3 | 32, 32, 32 | 16 s | Rs 0.51 | the byline and a second person's surname wrong in every reading |
| `gemini-3.1-pro-preview` | 1 of 3 | 18 | 182 s | about Rs 38 | cut off at about half the page |
| `gemini-3.8-flash` | 0 | none | | | overloaded |

**Findings**
1. **Argon read all 37 items in both completed runs**, and the owner found it best on meaning and details. It took 128 to 195 s, against 7 to 17 s on short pages; the page is long and argon was also slow for its output length, which may be load.
2. **A printed name was quietly changed.** 16 of 25 readings wrote the headline surname in the more usual spelling instead of the printed one. Only `gemini-4-argon` (2 of 2) and Sarvam (2 of 2) kept it as printed, apart from a few lite readings.
3. **Names were corrupted by the lite models**: the byline surname and a second person's surname were wrong in every lite reading in some form, and one reading wrote the ashram's name as a different place.
4. **The phone number split.** The right number appeared in 15 of 25 readings; 9 had a digit wrong and 1 had none. **Years**: all five right in 23 of 25 (one reading missed one year, one invented a year).
5. **Text was dropped.** 11 of 25 readings omitted the article's closing sentence; `gemini-3.5-flash-lite` and `gemini-flash-lite-latest` did it every time, `gemini-3.5-flash` and `gemini-3.6-flash` in 2 of 3.
6. **Meaning.** Sarvam's English says she was "arrested for allegedly being an infiltrator" on a march that the article says was to stop infiltration (an invented fact). In one sentence listing two events with imprisonment after them, `gemini-4-argon` (2 of 2) and `gemini-3.7-flash` (1 of 1) attribute the imprisonment to both events, while `gemini-3.5-flash` (3 of 3), `gemini-3.6-flash`, the lite models and Sarvam attribute it to the later event only. **The source sentence is ambiguous in print, and the owner has not ruled on which is right; this is unresolved.**
7. **Thinking models cost far more on a long page**: `gemini-3.1-pro-preview` spent 31,458 of its 32,768 tokens thinking on its one finished run and was cut off (about Rs 38 for half a page), `gemini-3.5-flash` cost Rs 10.8.

**Limits.** Argon completed 2 of 3 runs, `gemini-3.7-flash` 1 of 3 and `gemini-3.1-pro-preview` 1 of 3, because of overload; `gemini-3.8-flash` none. The reference is my reading, and the prices are unverified.

**What this changes in the plan.** `gemini-4-argon` stays the lead reader. `gemini-3.7-flash` becomes a serious candidate for the second reader, on one clean reading plus clean readings on three earlier pages, but it has not been tested on handwriting and was overloaded on most pages. `gemini-3.5-flash` is a close second on meaning. On the pages where both argon and `gemini-3.7-flash` completed (the clean letter, the second notes page, the land record and this page), every critical error argon made was met by a disagreement with `gemini-3.7-flash`; this is a small sample.

### 10j. A small Hindi newspaper clipping (recorded 2026-10-27; counts only, no article text)

*Cost note (added 2026-10-27): the per-page costs in this section are lower bounds; see 10k.*

**What was tested.** A small photographed Hindi (Devanagari) newspaper paragraph about a teacher (422 x 350 px), with stray letters from the neighbouring column at the left edge. Same method as 10i, with a prompt adapted for Hindi. Published text; no confidentiality issue. 26 items scored (14 on the Hindi reading: heading, the professor's name, five digits, four organisation names, two subject names and the final words; 12 facts in the English), against my own reading of the print.

**Two readers could not be run**: `gemini-3.7-flash` (the Google key returned a billing error) and Sarvam (payment required; its free credit is used up). Neither was retried.

| Reader | Readings | Items right (of 26) | Response time (median) | Cost per page |
|---|---|---|---|---|
| `gemini-4-argon`, `gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`, `gemini-flash-lite-latest`, `gemini-3-flash-preview` | 3 each | 26, 26, 26 | 12.5 s, 3.4 s, 2.8 s, 2.1 s, 11.7 s | Rs 0.91, 0.12, 0.18, unknown, 0.95 |
| `gemini-3.5-flash` | 3 | 26, 25, 26 | 17.7 s | Rs 2.12 |
| `gemini-3.6-flash` | 3 | 24, 25, 26 | 12.6 s | Rs 0.93 |
| `gemini-3.8-flash`, `gemini-3.1-pro-preview`, `gemini-pro-latest` | 2 of 3 each | 26, 26 / 26, 25 / 26, 26 | 93 s, 57 s, 102 s | Rs 1.04, 4.21, unknown |

The 24 and 25 scores are artifacts of my pattern: in four readings the phrase "10 o'clock" is split across a line break with a stray edge letter between, and the 10 is present in all of them. All readings are effectively right on these items.

**Findings.** (1) **The page does not separate the models**: all gave the right name, digits, plant, company and the car claim. The cheapest models, at Rs 0.1 to 0.2 and 2 to 3 s, were perfect. (2) **One printed name was quietly changed**: the page prints a polytechnic's name in a variant spelling; `gemini-4-argon` kept it as printed in 3 of 3 readings, while three models wrote the real city's name instead in 10 readings (all readings of `gemini-3.5-flash-lite`, `gemini-3.6-flash` and `gemini-flash-lite-latest`, plus one of `gemini-3.5-flash`). (3) **Stray-letter noise**: `gemini-3.6-flash` put "[Text fragment]" markers inside its English in one reading; two readings flagged 11 `[unclear]` spots on the edge fragments, which is the right behaviour. (4) **Hindi is an easier script than Assamese**, so this says little about the Assamese and Kannada pages the plan is about.

**What this changes in the plan.** Nothing in the ranking. Easy printed pages do not discriminate; the earlier failures came from dense Assamese text and handwriting. The next tests should use the plan's page groups, not more one-off pages.

### 10k. Correction to the cost figures (recorded 2026-10-27; counts only)

**What the billing page shows.** The prepaid credit for the Gemini API was topped up with Rs 500 on 25 October 2026, and on 27 October the balance was Rs 2.85, so about **Rs 497** was used. When the credit ran out, the paid key began returning a billing error.

**What I had estimated.** The timed runs I logged on the paid key for pages 3 to 7 (about 85 completed calls) come to about **Rs 268** at the third-party prices in 10e. The rest, roughly Rs 230, is not itemised: the earlier runs on the first pages and the translation steps were not logged with token counts, and calls that failed or timed out may also be billed. The prices themselves are unverified, so the real cost per token may be higher than assumed.

**What this changes.**
- **The per-page costs in 10e to 10j, and the cost column of the ranking in 10f, are lower bounds for the paid-key models.** The true cost per page is probably higher, perhaps by up to about 1.5 to 2 times, but this was not measured. Their order is unlikely to change, because the cheap and expensive models differ by much more than that.
- **The models run on the second key were not on this account**; their cost is unknown and may be zero.
- **Budgeting.** The 30-page test (the plan's section 2) must be budgeted from the new ledger, not from the figures above. Run a three-page dry run first, multiply by ten, and add a margin.

**What was done about it (Step 3).** The harness (`ocr_tests/harness.py`) now records the tokens, estimated cost and outcome of every call, including failed ones, and stops at a budget set in rupees. It still estimates, so the ledger should be reconciled against the billing page after each batch.

### 10l. Five real pages from the plan's groups, run through the Step 3 harness (recorded 2026-10-27; counts only, no names, places, case numbers or text)

**What was tested.** Five photographed pages supplied by the owner, the first real use of the harness: two typed Assamese government sheets with handwritten marginal notes (group B style), one handwritten English police form with court stamps and one line in Assamese script, one handwritten Assamese police court record, and one handwritten Assamese statement with English words mixed in (group A style). None was a PDF, so **Step 0 (the gibberish PDF diagnosis) is still open**. Language was identified by me, not given. All pages went to Google's paid Gemini key and to Google Cloud Vision; the owner confirmed cloud processing was acceptable, and nothing identifying a minor or the victim of a sexual offence was seen on them. Same prompt as 10d to 10j, temperature 0, two runs for `gemini-4-argon` and `gemini-3.7-flash`, one for `gemini-3.8-flash`. Tesseract (Assamese + English) and Cloud Vision (with Google Translate on its reading) were added as free or near-free baselines.

**Nothing here is scored against a reference yet.** The pages have no human reference translation. Marking sheets (plan section 8) were printed for the owner to fill in; until they are, every comparison below is between readers, and my reading of the images is not a reference. The owner's first impression after reading the outputs was that `gemini-4-argon` was the best reader overall; this is recorded as an impression, not a score.

| Reader | Readings completed | Attempts | Time per reading | Logged cost per page (lower bound, see 10k) |
|---|---|---|---|---|
| `gemini-4-argon` | 10 of 10 | 10 | 8 to 36 s | Rs 0.65 to 1.20 |
| `gemini-3.7-flash` | 7 | 12 (1 empty, 4 failed on overload, timeout or connection reset) | 81 to 258 s | Rs 0.55 to 3.41 |
| `gemini-3.8-flash` | 1 | 8 (2 empty, 4 failed, 1 cut off) | 131 to 261 s | Rs 0.17 to 1.89 |

`gemini-3.7-flash` produced at least one reading for each of the 5 pages only after a second pass. `gemini-3.8-flash` completed on one page. Total logged spend for the five pages was about Rs 23 (lower bound).

**What the two-reader checker found** (`gemini-4-argon` run 1 against `gemini-3.7-flash` run 1; the name items include false hits such as place words):

| Page | Item disagreements | Items to confirm | Differing lines | Argon run 1 against run 2: differing lines / item disagreements |
|---|---|---|---|---|
| 1 typed | 8 | 9 | 32 | 12 / 2 |
| 2 typed | 1 | 8 | 29 | 14 / 0 |
| 3 handwritten English | 11 | 20 | 50 | 24 / 3 |
| 4 handwritten Assamese | 9 | 2 | 32 | 15 / 6 |
| 5 handwritten mixed | 1 | 4 | 13 | 8 / 2 |

**Findings (my reading of the outputs, not yet confirmed by the owner).**
1. **`gemini-3.7-flash` changed the subject, not only a name or digit, on 3 of 5 pages** (1, 2 and 4): a numbered item about one matter came out as a different matter, an official's title came out differently, and the object seized in a police record came out as a different object. The earlier finding that it was clean (10i and the pages before it) came from pages without this kind of dense or handwritten text. Each of these readings was fluent, so nothing in the output warned of it.
2. **The item list alone would have under-reported this**: page 1 had 8 item disagreements but 32 differing lines, and the sentence changes are visible only in the line differences. The marking sheet and the PDF show both, but the plan's "must-check" list is not enough by itself.
3. **`gemini-4-argon` was consistent with the printed text on pages 1 and 2 and with the seizure form on page 4**, but differed from its own second run on 8 to 24 lines per page and on dates and names, so run-to-run agreement is not proof either. Dates differed between the two readers on 3 pages.
4. **Overload is now the main practical problem for the second reader**: five of the twelve `gemini-3.7-flash` attempts and seven of the eight `gemini-3.8-flash` attempts gave no usable reading, and good readings took 80 to 260 s.
5. **Cloud Vision** read the typed pages with mean word confidence 83% and 85% and the handwritten pages with 58%, 70% and 87% (pages 3, 4, 5). **Tesseract** gave 60% and 61% on the typed pages and 31% to 39% on handwriting. **Google Translate on Vision's reading was garbled** on the two pages I read (1 and 4) and is not usable as a translator. Whether Vision's low-confidence words point at the places where Gemini is silently wrong has not been tested; it needs the owner's marks.
6. **A harness fault was found and fixed** (commit e2b9909): a `gemini-3.8-flash` stream that stopped after about 200 tokens with no finish reason was logged as ok. It is now logged as incomplete; one row was relabelled.

**What this changes in the plan.** `gemini-4-argon` stays the lead reader. `gemini-3.7-flash` is not usable as the second reader for handwritten or dense pages on this evidence, and is demoted to "unproven"; the second-reader slot is open (`gemini-3.5-flash` is the next candidate; the owner deferred testing it). Group B needs a human-marked reference before any pass rule is applied. The three-page dry run for budgeting is effectively done: five pages cost about Rs 23 logged, about Rs 5 a page at argon plus the overloaded second reader's retries, which the 30-page budget should multiply and then double for the billing gap in 10k.

**Limits.** Five pages, no reference, two runs each at temperature 0 (not independent). The cost figures are the harness's estimates. Nothing in this section identifies a person, place, case or document.

### 10m. The "gibberish" PDF (Step 0) and `gemini-3.5-flash` as the second reader (recorded 2026-10-27; counts only, no case text)

**What was tested.** (a) One owner-supplied PDF from group C, a one-page digital Assamese file whose sentences are deliberately meaningless (the file says so). (b) `gemini-3.5-flash`, the deferred second-reader candidate, on the five pages of 10l and on that PDF.

**Step 0 diagnosis of the PDF.** It is **not** a broken-text-layer PDF. It has no scanned image, one embedded Unicode TrueType Bengali-script font with a proper Unicode map, and `pdftotext` returns clean, correctly ordered Assamese. What is broken is the **visible rendering**: the file was drawn without proper complex-script shaping, so vowel signs sit in the wrong places on screen (for example, signs that belong before a consonant are drawn after it), and a person looking at the page sees garbled words that the text layer does not contain. This gives the first **exact reference text** in the project, and a rule for this type of file: **extract the text layer first (free, exact), and use OCR only when the layer is missing or does not match the page.** It says nothing about the other four group C files, which may be the opposite case (a good picture over a junk text layer, as with old non-Unicode fonts); each needs the same two-minute check: compare the text layer with what the page shows.

**Scores against the exact text (page rendered to an image at 150 dpi):**

| Reader | Word-for-word right (exact) | Base-letter error rate (vowel-sign positions ignored) | Logged cost per reading |
|---|---|---|---|
| `gemini-4-argon` (2 runs) | 65.7%, 70.4% | 1.8%, 3.1% | Rs 0.97 to 0.99 |
| `gemini-3.5-flash` (2 runs) | 50.9%, 42.6% | 2.9%, 3.1% | Rs 6.36 and 11.15 |
| Cloud Vision | 30.6% | 1.6% | about Rs 0 |
| Tesseract | 26.9% | 14.2% | Rs 0 |

`gemini-3.7-flash` failed (overload) and was not retried. The exact word score is low for every reader because the readers copied the garbled marks as drawn; the base-letter column shows that the letters themselves were read well by all but Tesseract. **Both Gemini models wrote the final sentence of the page correctly and none marked any word `[unclear]`.** On the meaningless lines, `gemini-4-argon` produced fluent, poetic English for words that have no sentence meaning (it made sense where there is none), while `gemini-3.5-flash` mostly transliterated them. For a real page the first behaviour is a risk: a reader that fills in meaning cannot be trusted to say when there is none.

**`gemini-3.5-flash` on the five pages of 10l (one run each):**

| Page | Result |
|---|---|
| 1 typed | Rewrote the subject of one numbered item, invented a date range and a body name, and changed the names in the list. Worse than `gemini-3.7-flash`. |
| 2 typed | Cut off (stream ended with no finish reason, 6,901 thinking tokens, Rs 6.42 spent); unusable. |
| 3 handwritten English | Same reading of the seized article as `gemini-3.7-flash` (bamboo), different from argon (wood); dates differ between the three readers. |
| 4 handwritten Assamese | Close to argon on the main facts (the object, the arrest, the court stage); added a "/34" to the section, changed a column number and the year in a date. |
| 5 handwritten mixed | One clause changed meaning ("beat me" where the others have "remained like that"); "4-5 days" where the others have 15. |

Cost and speed: Rs 2.77 to 4.16 per page on these pages (about 3 to 4 times argon) and Rs 6.36 to 11.15 on the PDF page; 16 to 77 s; 2,300 to 11,900 thinking tokens a page.

**Findings.** (1) **Neither flash model works as the second reader on dense or handwritten Assamese**: both changed the meaning on a typed page where argon did not. The "two readers agree" alarm cannot be built from either of them. (2) **The disagreement between argon and the flash models is still useful as a warning, but not as a second opinion**: where they differ, a person must look; where they agree, the earlier lesson (agreement is not correctness) still applies. (3) **Cloud Vision is the most faithful transcriber on the digital page** and gives a confidence for each word; it was weak on handwriting (58 to 87% mean confidence on pages 3 to 5). It does not translate. (4) Total logged spend across 10l and 10m is about Rs 62 (lower bound, 10k); this round about Rs 39, of which `gemini-3.5-flash` accounted for about Rs 37 including two readings that were unusable.

**What this changes in the plan.** Step 0 is done for one file and gives a triage rule (text layer first). The second-reader slot has no Gemini candidate left on this evidence; the next options are argon run twice (self-consistency), Cloud Vision as an independent transcriber on typed pages, and the human reviewer. The owner's marks on the 10l pages are still the way to turn any of this into scored numbers.

### 10n. A second group C PDF: image only, no text layer (recorded 2026-10-27; counts only)

**What was tested.** A one-page PDF made by a PDF merge tool, containing a single 1240 x 582 JPEG and no fonts and no text layer (`pdftotext` returns nothing, so copying gives nothing). The picture is a page of a published Assamese–English dictionary shown twice side by side: a clean re-typed copy on the left and a low-quality scan of the original on the right, four text columns in all. Published material; no confidentiality issue. I read the whole page and each half cropped and enlarged to twice its size (the halves do not cover exactly the same entries, so the two halves are not compared with each other). No reference text exists: the re-typed half contains errors of its own.

**Step 0 triage, now with two PDFs.** File 1 (10m): good text layer, garbled picture, so extract the text. File 2: no text layer, so render and OCR. A two-minute check separates them: run `pdftotext`, then compare what comes out with what the page shows. Three more files are still needed to know how common each type is.

| Reader (whole page) | Completed | Time | Logged cost |
|---|---|---|---|
| `gemini-4-argon` | 1 of 2 (the other failed on a network error) | 64 s | Rs 2.93 |
| `gemini-3.7-flash` | 1 of 1 | 216 s | Rs 3.23 |
| Cloud Vision, Tesseract | 1 each | about 1 s, 6 s | about Rs 0, Rs 0 |

On the halves: `gemini-4-argon` completed 2 of 2 on each (15 to 71 s, Rs 1.38 to 1.77); `gemini-3.7-flash` completed on the clean half only (299 s) and failed on the scanned half.

**Agreement between readers (character level, punctuation and spaces ignored; this is agreement, not accuracy).**

| Pair | Clean half | Scanned half | Whole page |
|---|---|---|---|
| argon run 1 against run 2 | 98.2% | 98.4% | not repeated |
| argon against Cloud Vision | 97.9% | 87.7% | 91.0% |
| argon against Tesseract | 93.5% | 69.4% | not computed |
| argon against `gemini-3.7-flash` | 91.5% | not available | 88.4% |
| `gemini-3.7-flash` against Cloud Vision | 89.8% | not available | 82.9% |

Cloud Vision mean word confidence 95.5% (clean half), 82.0% (scanned half), 87.2% (whole page); Tesseract 88.6%, 70.4%, 75.1%.

**Findings.** (1) **All four readers handle the clean copy; the scan separates them.** On the blurred half Cloud Vision dropped or garbled whole phrases of two dictionary entries and Tesseract lost nearly a third of the text, while `gemini-4-argon` kept every entry in order. (2) **Argon still made small silent word errors in the blurred spots** (for example a different plausible word where the scan shows another), with no `[unclear]` marks; its two runs on the same half were 98% alike, so run-to-run agreement does not reveal these. (3) **Reading order on four columns worked for argon and `gemini-3.7-flash`**, with `[COLUMN n]` markers in the right order. (4) **The "translation" step has little meaning on a bilingual dictionary page**: much of the text is already English glosses; the two Gemini readers treated the Assamese glosses differently (one reported the English gloss, the other translated the Assamese words), so the English needs a person who reads Assamese. (5) **Total logged spend across 10l to 10n is about Rs 76 (lower bound, 10k).**

**What this changes in the plan.** Nothing in the ranking: argon is the lead reader, with Cloud Vision as a cheap check on clean typed pages only. Group C needs the triage step before any reader is run, so that files with a good text layer are not sent through OCR at all.

### 10o. First run of the section 11 pipeline: three typed Assamese pages (recorded 2026-10-27; counts only, no names, places, case numbers or text)

**What was tested.** Three typed Assamese government sheets with handwritten margin notes (one of them a faded copy), supplied by the owner, run as designed in section 11: `gemini-4-argon` twice, Cloud Vision once, then `checker.py --page typed`. The checker's own selftest (invented text) passed first; this was the first run of the new page check on real readings. No other model was used. No page identified a minor or the victim of a sexual offence. No reference text and no human marks exist for these pages.

| Page | Argon run 1 against run 2 | Argon against Cloud Vision | Cloud Vision mean confidence | Light | Differing lines between runs |
|---|---|---|---|---|---|
| 8 | 97.9% | 89.5% | 85.4% | red | 7 |
| 9 | 86.0% | 66.6% | 69.8% | red | 39 |
| 10 (faded) | 96.4% | 50.9%, and 75% as many letters | 59.5% | red | 8 |

All three pages came out **red**. Cost was about Rs 7 for the six argon readings (Rs 1.11 to 1.28 each, 12 to 52 s; one run failed on a network error and was repeated), logged; Cloud Vision about Rs 0. The checker ran without errors.

**Findings.** (1) **Page 9's red is earned by argon itself**: its two runs agree on only 86% of letters, differ on 39 lines, one run carries a date the other lacks, and four English sentences changed. (2) **Pages 8 and 10 are red mostly because Cloud Vision read them badly, not argon**: on the faded page Cloud Vision garbled digits and dropped lines while argon's reading was coherent. The rule "red if Vision is unsure" therefore sends a page for full human reading without saying which reader is wrong. (3) **The English-sentence comparison caught a real meaning flip that the letter check did not**: on page 10 the two argon runs agree on 96.4% of letters yet one run names one place for a ceremony and the other names a different place. (4) **Handwritten margin notes make pages look different**: argon marked doubtful words on pages 9 and 10 (9 in all) and gave `[unclear]` for the signatures, as intended. (5) **All three typed pages were red, so on this evidence green is rare on faded or low-resolution typed pages**; whether that is the right call needs the owner's marks.

**Proposed tuning, not yet made.** Treat a page whose Cloud Vision confidence is under 80% as having no independent machine check (amber, like handwriting) unless argon's own two runs also disagree, so that Vision's weakness does not decide the colour. This rests on three pages and should be tested on the owner's marks before it is adopted.

**Limits.** Three pages from the same kind of document, not independent of earlier pages 1 and 2; no reference; thresholds are a first guess.

### 10p. Step 3 test package: which image changes help `gemini-4-argon` (recorded 2026-10-28; counts only, no names, places, case numbers or text)

**What was tested.** Four typed Assamese government pages the owner had marked (the marks on three of them give 26 confirmed values), each read by `gemini-4-argon` in five image variants and compared with the baseline readings already made (the original image, two runs): **v1** enlarged 2x; **v2** enlarged 2x with automatic contrast and sharpening; **v3** padded with a white border (6% a side); **v4** the original image with the model's per-image detail setting raised to ultra high; **v5** the one skewed page (measured -1.75 degrees; the other three measured 0) straightened. 26 new calls, about Rs 32 logged (a lower bound, 10k), plus about Rs 5 of probing. Pages 1, 8: one run per variant; pages 9, 10: two runs.

**The detail setting.** Argon already uses high detail by default (1,357 input tokens for the page); asking for high on the standard API changed nothing, and ultra high works only as a per-image setting on the alpha API (2,477 input tokens, about Rs 0.2 more a call). The alpha API may change.

| Variant | Confirmed values found | Invented names | Two runs agree with each other, p9 / p10 | Agree with baseline run 1, p9 / p10 | Avg time | Logged cost (6 calls) |
|---|---|---|---|---|---|---|
| baseline (existing) | 33 of 34 | 0 | 86.0% / 96.4% | n/a | 12 s | n/a |
| v1 enlarged | 22 of 22 | 0 | 89.3% / 96.2% | 90.7% / 94.9% | 13.7 s | Rs 6.78 |
| v2 enlarged + contrast | 22 of 22 | 0 | 87.8% / 89.9% | 85.3% / 86.4% | 12.8 s | Rs 7.54 |
| v3 padded | 21 of 22 | 0 | 98.3% / 97.3% | 98.0% / 94.3% | 13.3 s | Rs 6.92 |
| v4 ultra-high detail | 22 of 22 | 0 | 95.9% / 98.9% | 98.6% / 96.3% | 17.5 s | Rs 8.15 |
| v5 straightened (p10 only, 2 calls) | 10 of 10 | 0 | n/a / 90.2% | n/a / 88.6% | 12.4 s | Rs 2.33 |

**Findings.** (1) **The values are at the ceiling**: argon already finds almost every confirmed number, date and name in every variant, so this test cannot rank the variants on those; it can show regressions and stability. (2) **No variant fixed the one known wrong printed name**: every variant, 7 of 7 readings, still reads it the same wrong way. Image preparation does not cure a name error. (3) **A shared error was exposed by changing the view**: both baseline runs read a handwritten date with the same day number, which the owner's marks say is wrong; padded and contrast variants read a different day consistently, and ultra-high gave a third. Identical runs hid it; different views disagree and would flag it. (4) **A place word on page 10 split the baseline runs, and the other views mostly agree on one reading**: of the 10 variant readings, 9 give one place (one of them garbled) and 1 gives the other; the two baseline runs split one each. The owner has not yet said which is right. (5) **Padding and ultra-high detail made the readings steadier** (page 9 from 86% to 98% and 96%; page 10 from 96% to 97% and 99%); **contrast with sharpening and straightening made them less steady** (page 10 down to 90%, and 86% to 89% against the baseline), so neither is recommended. Enlarging was neutral. (6) **Caveats**: 4 pages, 1 to 2 runs each; the page 9 baseline was one run that added lines the other did not, so some of the gain may be a good draw. Steadier is not more accurate.

**What this changes in the plan.** Step 3 becomes small: **no contrast boost and no straightening by default**; the second argon run reads a **padded** copy of the page (no API risk), with **ultra-high detail** as an optional third view when the first two disagree (it uses the alpha API). The disagreement between differently prepared views is the signal, because identical runs agree with each other even when wrong. The owner's confirmation of the page 9 date and the page 10 place word would turn findings 3 and 4 into measured results.

### 10q. First real run of the built pipeline: a five-page Assamese PDF (recorded 2026-10-28; counts only, no names, places, case numbers or text)

**What was tested.** A five-page PDF supplied by the owner: a published court judgment translated into Assamese, made with a word processor (embedded Bengali-script fonts with Unicode maps, no scanned pictures). Typed, clean pages (letter size, 2,200 to 3,000 letters a page). Public record; it names no minor and no victim of a sexual offence, so it passed the gate. Run with `pipeline.py --page-type typed`, Tesseract for the PDF match, a Rs 60 cap. No reference text and no human marks exist yet.

**Step 2 (PDF triage) on a real "gibberish" PDF.** The text layer was visibly garbled (dropped vowel signs and conjuncts), although its fonts had Unicode maps, so the font checks did not fire. The comparison with the rendered page caught it: base-letter agreement 34.7%, 26.3%, 23.4%, 26.2% on pages 1 to 4 (all `treat_as_image`) and 77.3% on page 5 (`person_decides`, read as an image by default; that page is mostly English and Assamese disclaimer text). This is the first group C file of the kind the plan feared (a good picture over a junk text layer); the rule worked on it.

**Reads.** 10 reads (2 views x 5 pages) and 4 third views, 14 calls, **Rs 14.94 logged** (Rs 9.77 for the 10 reads; the 4 third views, Rs 5.17, turned out not to be needed, see below). Time per read 6 to 72 s, median about 12 s.

| Page | Views agree on letters | Third view agrees with views 1 / 2 | Must-check items | Items that differ | English sentences that changed | Light |
|---|---|---|---|---|---|---|
| 1 | 100.0% | 100.0% / 100.0% | 3 | 0 | 1 (header layout and wording) | amber |
| 2 | 99.8% | 100.0% / 99.8% | 4 | 0 | 1 | amber |
| 3 | 100.0% | not run | 4 | 0 | 0 | green |
| 4 | 99.9% | 99.8% / 99.9% | 11 | 0 | 1 | amber |
| 5 | 99.6% | 99.6% / 100.0% | 0 | 0 | 1 | amber |

**Findings.** (1) **On clean typed pages the two views agree almost perfectly on the original script** (99.6 to 100%), so the machine sees nothing to settle; this says nothing about whether the shared reading is right. (2) **The instability is in the English, not the transcription.** Each amber page was amber only because of English: one sentence worded differently, or a name or citation translated two ways. (3) **The new names-and-numbers comparison between the two English drafts caught two legal naming differences that a sentence-by-sentence comparison missed because the rest of the sentence was identical**: a party designation (one draft "Government of ...", the other "State of ...") and a case citation ("Union Government of India" in one draft against "Union of India" in the other). A literal translation of an Assamese phrase gives a different name from the one the official English judgment uses; a person who knows the established name must settle these. (4) **Three tool problems found by real data and fixed:** the English sentence splitter broke sentences after "vs." and "S.C.C." and so created false differences while hiding real ones (it now skips abbreviations and initials); the names-and-numbers comparison was added; the third view was triggered by English wording differences, which an image view cannot settle (it now runs only when a must-check item differs or letter agreement is under 97%; on this file that would have saved the Rs 5.17). (5) **Few must-check items on legal prose** (22 in all, mostly section numbers): the extractor finds numbers and sections but few names, so the list covers little of the text.

**What this changes in the plan.** Nothing in the design except the third-view trigger. For translated judgments the English names and citations are the main risk, which suggests a glossary of established legal designations (party names, "Union of India", "State of ...") that flags, and never corrects, a literal rendering; this is not built. The owner's marks are still needed to say whether the shared reading is right.

### 10r. The first true reference: the official English text of the same judgment (recorded 2026-10-28; counts only, no names, places, case numbers or text)

**What was tested.** The official English text of the judgment whose Assamese translation was run in 10q (two pages, a text layer, from the court's own website; the Assamese document is a translation of it). Both English drafts of the pipeline (view 1, image as given; view 2, padded copy) were scored against it, sentence by sentence (32 official sentences) plus 6 header fields, with `ocr_tests/score_reference.py` (closeness, numbers, names) and my own reading of every pair. The judgments of severity are mine and a reviewer may disagree. The Assamese document is itself a translation, so the drafts are back-translations and will not match word for word.

| Measure | View 1 | View 2 |
|---|---|---|
| Mean closeness to the official sentences (0 to 1) | 0.702 | 0.706 |
| Official sentences with no close match (under 0.6) | 8 of 32 | 9 of 32 |
| Sentences where this draft is closer by more than 0.05 | 5 | 4 |
| Sentences within 0.05 of each other | 23 | 23 |
| Header fields correct | 5 of 6 | 6 of 6 |
| Sentences with no critical or moderate problem | 26 of 32 | 26 of 32 |
| Critical differences from the official text (names, numbers, legal references) | 5 | 3 |
| of which faithful to a misprint in the Assamese source | 2 | 2 |
| Moderate | 3 | 3 |
| Gist correct, pages of judgment text | 4 of 4 | 4 of 4 |

Taking the closer draft for each sentence would give a mean closeness of 0.722.

**The critical differences.** (a) **Two section references**: both drafts, all three reads, say Section 422 and Section 133 where the official text says 433 both times. At 400 dpi the Assamese page itself prints those two numbers: **the source has two misprints and the readers copied them faithfully.** Every other number and section reference in both drafts (about 25) matches the official text. (b) **A printed case name was silently replaced**: the Assamese page and the official English both print one spelling; both drafts wrote the spelling of the real case name instead, with no warning (the pattern of 10i). (c) **View 1 only**: the respondent's designation and a case citation were rendered literally ("Government of ...", "Union Government of India") where the official text uses the established forms; view 2 has the established forms. Both were flagged by the names-and-numbers comparison of 10q (the only critical differences the pipeline flagged); (a) and (b) were not flagged as problems (the section numbers were on the must-check list as items to confirm).

**The moderate ones, the same in both drafts.** Two sentences are garbled where a page break fell in the middle of a sentence (the pipeline reads and translates each page separately and does not notice); one sentence shifts what stays unaffected (the court's power to pronounce on validity, against the validity itself).

**Findings.** (1) **The choice between the two drafts rarely matters**: 23 of 32 sentences are equally close; it matters at the few places where names or legal designations differ, which supports choosing sentence by sentence only where the drafts differ and checking names against a glossary or the official text. (2) **Agreement of the readers was faithfulness, not correctness**: three reads agreed on two numbers that were wrong in the source. A reader cannot know; only the official text, the law or a person who knows it can. (3) **Silent errors by the plan's measure**: counting the two source-faithful numbers and the silent name replacement, this one document already has 3 silent critical differences in 4 pages of text (2 of them misprints in the source), against the plan's allowance of 1 per group; whether a faithful copy of a printed misprint is an "error" is a decision for the owner. (4) **A page break in mid-sentence is an undetected failure** of the page-by-page design. (5) **The official text, when it exists, is the best checker**: it found the three things above in minutes; most real records will not have one.

**What this changes in the plan.** Nothing is built from it yet. Candidates, in order: a check that flags a page that ends or begins in the middle of a sentence (or reads pages together); an instruction to keep a printed name exactly as printed and mark it, with a test on this document; a glossary of established legal designations; the sentence-by-sentence choice process with its log (on hold at the owner's request); and keeping the official English text as the reference whenever one exists.

### 10s. The first Kannada file: a nine-page PDF (recorded 2026-10-28; counts only, no names, places, case numbers or text)

**What was tested.** A nine-page PDF supplied by the owner: a Kannada translation of an old published civil judgment (a limitation-law case), printed to PDF from a browser, typed, Kannada script, no pictures. It reached the tool under a `.php` name (a download link serving a PDF). Public record; no minor and no victim of a sexual offence, so it passed the gate. Run with `pipeline.py --language Kannada --page-type typed --pdf-lang kan+eng`, Rs 40 cap. No reference text yet; the owner will supply the official English text.

**Problems found before reading anything.** (1) The tool recognised files by name, so the `.php` file was silently ignored (0 pages found); it now recognises PDFs and images by their first bytes and says when it skips a file (commit 1f03562). (2) The PDF's own text layer is junk on pages 1 to 8 (scattered Kannada fragments; the font has no Unicode map): triage fired its signs of a broken encoding (two signs on seven pages, one on page 3) and the comparison with the rendered page agreed on only 26.1% to 32.0% of base letters, so all eight pages were read as images; page 9 (a signature line, one letter extracted, no picture) was "a person decides" and read as an image by default.

**Reads.** 18 reads (2 views x 9 pages) and 1 third view (page 8), **Rs 18.29 logged**; time per read 9 to 22 s (one 107 s). Two whole-document translations (below) cost Rs 5.73 more.

| Measure | Result |
|---|---|
| Views agree on letters | 99.6% to 100% on all 9 pages |
| Lights | 8 amber, 1 green (page 4); every amber page was amber only because of English differences |
| Must-check items (numbers, sections, dates) | 37 across the 9 pages, none differing between the views once a separator ("-000-") stopped being counted as a number |
| Pages that end in the middle of a sentence | 6 of 8 page breaks (pages 1 to 2, 2 to 3, 3 to 4, 4 to 5, 6 to 7, 7 to 8) |

**Findings.** (1) **Argon reads typed Kannada as steadily as typed Assamese**: both views agree to 99.6% or better on every page. This does not show the reading is right; no Kannada reader has marked it. (2) **Page-by-page translation is the wrong unit for this document**: six page breaks cut a sentence, so every English page draft has a broken sentence at each end. The nine Kannada readings were therefore stitched into one text and translated twice, blind, in one piece each (A and B). (3) **Kannada writes English names and titles in Kannada letters, so their English spelling is a guess**: A follows the Kannada letters (a literal back-transliteration of the parties' and judges' names); B gives what look like the established English spellings, probably from the model's memory of the case. 20 of about 50 sentences differ between A and B, nearly all names, date styles and wording. The official English text will show which spellings are right; whichever is closer, names need a glossary or the official text. (4) **Two checker fixes from this file**: a separator such as "-000-" is no longer a value to confirm, and an ordinal ("20th") is no longer a different number from "20".

**Not yet done.** (Done in 10t.) Scoring A, B and the per-page drafts against the official English text, when the owner supplies it.

### 10t. The Kannada file scored against the official English (recorded 2026-10-28; counts only, no names, places, case numbers or text)

**What was tested.** The four English versions of 10s (per-page drafts from view 1, per-page drafts from view 2, stitched translation A, stitched translation B) against the official English text of the same judgment, supplied by the owner as a five-page scan of the law report (a PDF under a `.php` name; its own text layer is OCR with many faults, so it was cleaned by hand against the page images; the cleaned text and all outputs stay outside the repository). The judgment is a published apex-court report from 1950, so it is probably in the models' training data (see the confound below).

**Scores** (`score_reference.py`; closeness is word-by-word likeness, so it measures phrasing, not meaning):

| Version | Mean closeness, whole text (54 sentences) | Mean closeness, judgment body only (29 sentences) | Body sentences with no close match |
|---|---|---|---|
| Per-page, view 1 | 0.683 | 0.771 | 5 |
| Per-page, view 2 | 0.689 | 0.774 | 6 |
| Stitched A (first translation) | 0.703 | 0.821 | 1 |
| Stitched B (second translation) | 0.760 | 0.892 | 1 |

**Counts of real differences, found by reading.**

| Check | Per-page v1 / v2 | Stitched A | Stitched B |
|---|---|---|---|
| Garbled sentence at a page break (of 8 breaks, 6 mid-sentence) | 2 / 2 (word order scrambled, one with a stray "[against]"); 1 more awkward join each | 0 | 0 |
| "appellant" turned into "appellants" (official: singular, 7 times) | 6 / 6 | 0 | 0 |
| Numbers of two digits or more that differ from the official | 0 / 0 | 0 | 0 |
| Dates (16 in the official) | 15 of 16 / 15 of 16 | 15 of 16 | 15 of 16 |
| Clause, rule, article, section references that differ | 1 / 1 | 1 | 1 (shown as "[2]") |
| Names (8 that carry a spelling choice: 2 party names, 5 bench names, 1 agent) written differently from the official | 1 / 1 (the agent's name; the other 7 match) | 8 of 8 | 1 (the same agent's name; the other 7 match) |
| Nonsense word inserted by the translator | 0 / 0 | 0 | 1 ("but" became a stray noun) |

**Findings.** (1) **Stitching beats page-by-page**: no garbled seam and no singular/plural drift in either stitched version, against two garbled seams and six wrong plurals in each per-page version. The likely cause (not tested) is that a page that starts mid-sentence gives the model no context to choose singular or plural; a stitched text does. (2) **Every number of two digits or more, and 15 of 16 dates, matched the official in all four versions.** The one missing date (a dismissal date) is missing in the Kannada text itself, so no reader could have produced it: a translation of a translation can lose a fact before our tool sees the page. (3) **One legal reference is wrong in all four versions** (a clause number in the headnote: the printed Kannada says 3, the official says 2). It is a printed error in the source, copied faithfully by every reading; only B marked it, with a bracket the model added by itself ("3 [2]"; likewise "Order II [IX]" for a reference the official itself prints as "II"). The model's bracket was right both times, but it is not a rule we set, so it cannot be relied on. The first score tool ignored one-digit numbers and would have missed this; `score_reference.py` now also counts clause, rule, article, section and order references. (4) **Names: three of the four versions matched the official on 7 of 8 name spellings; stitched A matched on none.** The Kannada text writes English names in Kannada letters, so the English spelling is a guess; A guessed sound by sound, the other three used the established spellings. The same instruction, run twice on the same text, gave both behaviours, so no single run can be trusted on names. **Confound:** this is a famous reported judgment, so the established spellings (and some of B's legal wording; its closeness of 0.892 is high) may come from the model's memory; on a trial-court or police document the model has never seen, there is nothing to remember, and a name it "knows" may be a different person's. Run-to-run variation, not a property of B, probably explains the gap between A and B. (5) **B has the nonsense word, A does not**: stitched translations are not clean either; a person must read the whole thing. (6) **Three wording shifts are in all four versions** ("judgment" where the official says "decree", twice; "order" where it says "decision"): they come from the Kannada text, not from the readers or the translator.

**What this changes.** Stitching readings into one text before translating is adopted as the unit of translation for typed, multi-page documents (not yet inside `pipeline.py`: it is done by a scratch script). Names and legal references must be checked against the source by a person, never by agreement between two translations. Two translations still catch what one misses (B caught two source misprints, A caught none), and the capitalised-name difference check between two translations would have flagged all 8 names where A and B disagree: a spelling difference between two translations of one text is a usable alarm, agreement is not proof.

**Limits.** One document, one language, a 1950 published judgment; the reference was an OCR'd scan cleaned by one person (the headnote partly reconstructed from the page image); the owner has not marked the Kannada pages; the closeness score is a rough guide only.

### 10u. Steps 2 to 4 built: whole-document translation, names as printed, reference checks (recorded 2026-10-28; counts only, no names, places, case numbers or text)

**What was built.** (2) `stitch.py` joins the readings (or a PDF's own text) of all pages of a document into one text; `pipeline.py` (option `--stitch auto`, the default) then translates the joined text twice, blind, and `checker.check_document` compares the two. A page that ends without a full stop or danda is joined to the next with a space; a leading line that holds only a page number is dropped; every join and drop is listed in the report so a person can check it. Translation 1 is the one to read (fixed in advance; the tool never chooses). Output: `document/<name>_*` (source text, both translations, check, report, PDF with `--pdf`). (3) `prompts/translate_stitched.txt`: names of people, firms, parties and small places are written by sound, never replaced by a name the model knows; the original-script word goes in square brackets after the first appearance; well-known states, cities, courts and the titles of Acts may use the standard English name; every printed number and reference is kept as printed, and a suspected misprint gets `[sic]` and is not corrected; no notes or corrections of the model's own. (4) `redundancy.legal_references` and `reference_flags`: clause, rule, article, section and order numbers are counted (one-digit ones too, which no earlier check saw); a flag is raised when one rule number sits under two different orders, or when the same quoted words are tied to two different clause numbers. All flags say "look at the original"; nothing is corrected.

**Tests on the first Kannada file (the model was called for the translation only; page reads were reused).** Cost of two whole-document translations: Rs 3.1 to 4.1 each logged (Rs 6.2 to 8.1 a pair); the whole-document run added about Rs 6.2 to the Rs 18.3 of page reads.

| Measure | Result |
|---|---|
| Page breaks joined by the tool | 6 of 8, the same 6 as before; the tool's joined text differs from the hand-made one only in a stray line break at 5 of the joins |
| Original-script word in brackets after names | 15 to 20 per translation (both runs of every prompt version) |
| `[sic]` on the two real source misprints (a clause number, an order number) | 12 of 12 possible marks (6 runs x 2); one extra, wrong `[sic]` in one run (on the word "order" where the official says "decision") |
| Printed numbers changed | none in any run (all numbers of two digits or more, and all dates but the one missing from the source, as in 10t) |
| Names that one translation has and the other lacks, per pair of runs | old prompt 18 entries; first new prompt 10; narrowed new prompt 3 in one pair, **15 in a second, fresh pair with the same prompt** |
| Mean closeness to the official English (whole text) | old A 0.703, old B 0.760; new prompt 0.689 / 0.690 (first version), 0.723 / 0.726 (narrowed) |
| Reference flags on the 4 earlier English versions | the clause-number tie is flagged in all 4 (it is the real misprint); the rule-9-under-two-orders flag in the 3 that print "Order II" (the fourth hid it behind its own bracket); no false flag on the official text beyond the one real printed oddity |

**Findings.** (1) **The new rule makes names traceable but not stable**: every name now carries the original-script word, so a person can check it, but two runs still spell some names differently by sound (one pair differed on 3 entries, a second pair on 15). The name-difference flag therefore stays amber on nearly every document, and agreement between two runs is still not proof. (2) **The `[sic]` rule worked on this file**: both real misprints were marked in all 6 runs with the printed value kept; one run added a wrong mark. One document is not enough to say how often a model will notice a misprint it has no reason to suspect; the reference check does not depend on the model and caught the same two. (3) Names written by sound read worse than the established spelling (the first party's name, for example, came out as a sound-by-sound form) and score lower on closeness; that is the price of not letting the model put in a spelling from memory. A person (or a confirmed-names list, `--known`) turns them into the established form. (4) **Bugs found while building**: a text-layer PDF page with a date or number in its must-check list made the report raise an error (never hit before because earlier test pages had none); fixed with a test. The reference check at first read "six" as a Roman numeral and "cls. 2 and 3" as a single clause; both fixed with tests. Sentence-opening words ("On April", "However") no longer count as names in the two-translation comparison.

**Not done.** The same rule is not yet in `prompts/translate_text.txt` (the per-page translation of a PDF page with a good text layer); a mixed document (some pages with a text layer, some read as images) is joined but has not been run for real; the join rule has been run on Kannada only; the narrowed prompt was changed once after the first test, so its numbers come from the second version and one fresh pair (a third pair, not two, would be needed before calling the name noise typical).

### 10v. First run of the full pipeline on a fresh document: a three-page Assamese government notification (recorded 2026-10-28; counts only, no names, places, case numbers or text)

**What was tested.** A three-page scanned PDF supplied by the owner (an image-only file, typed Assamese with a few English lines, an ink signature, a numbered distribution list over two pages and a table). It is dated after the models' likely training cutoff (inferred from a date on it; not known), so it is the first document the model is unlikely to have seen. The whole pipeline was run once as designed (typed pages, two views, third view only if flagged, whole-document translation twice) with no change to any prompt or rule beforehand. The official English text has not been supplied yet (the owner will send it after this test), so every claim below about correctness is my own reading of the page images and is marked as such.

**Run.** 6 page reads and 2 whole-document translations, **Rs 9.34 logged** (Rs 6.98 reads, Rs 2.36 translations); 10 to 37 s a read; no third view (no must-check disagreement, agreement over 97% on every page).

| Measure | Result |
|---|---|
| Views agree on letters | 100%, 99.5%, 100% |
| Lights | 3 amber of 3 (names and wording noise); no red |
| Must-check items (numbers, dates) | 29 (10, 4, 15), none differing between the views |
| Page joins | 2 breaks: 1 paragraph break (correct), 1 join (wrong: a signature block with no full stop was joined to the table heading on the next page) |
| Table | read as two columns (the serial numbers, then the names) instead of rows; both columns have 24 entries, in the same order |
| Names/titles only one translation has | 21 entries (almost all wording noise such as "of Assam"/"to the Govt. of Assam") |

**Findings (my own reading of the images).** (1) **One printed number was misread the same way in every view and every translation**: a digit of a year in a date (a 6 read as a 3). Both views agreed, so the check list showed it as "still confirm", no disagreement fired and the third view was not triggered. This is the blind spot the design names (an error made in every view); it is the first one found on a real file. Checked by cutting out the digit and comparing it with the table's own serial number 6. (2) **[Corrected in 10w: the official English has the same mismatch, so this is the notice's own inconsistency, not a missing or cropped page of the scan.]** The notice text says 32 departments, the table ends at row 24; the tool did not notice (no check compares a number written in words and digits against the rows). (3) **[Withdrawn in 10w: the official English also says "Consumer Affairs", so the output was right and my doubt was wrong.]** (4) **[Mostly withdrawn in 10w: the official English has the same "to the Govt. of" wording as translation 1; only the doubled "No." is a real, cosmetic difference.]** (5) The names rule produced original-script brackets only on places and titles; the document has no personal names, so the name rule was not tested. (6) Everything else on page 1 that I checked against the image (9 numbers and dates apart from the year, reference numbers, postal codes, the two e-mail addresses) matched; I did not check every item on pages 2 and 3.

**What this changes.** (a) A shared misread of a digit needs a check the model does not control: for dates, the notice's own context (a date of a past event cannot be later than the date the page was signed) cannot be used here because the signing date is an e-sign stamp; the realistic control is that a person checks each date digit against the page, which the must-check list asks for, and the sheet should show the date digits zoomed. (b) A check of a number in words against the number of rows or items is worth building (the 24 against 32 case). (c) A line without a full stop that ends a page (signature, heading) is joined wrongly; the log shows it; a table-heading rule could stop it. (d) Amber on all three pages for wording noise means the light did not separate the page with the real error from the others.

**Not done.** Scoring against the official English (the owner will supply it after this test); a person's marks on the sheets; a third view on page 1 to see whether it would have caught the year.

### 10w. The fresh document scored against its official English (recorded 2026-10-28; counts only, no names, places, case numbers or text)

**What was compared.** The official English of the three-page notice of 10v (a three-page image-only PDF; read by Tesseract and by eye, key items checked on the images; the clean text stays outside the repository) against: per-page drafts from view 1 and view 2, and stitched translations 1 and 2. The sentence splitter now treats Govt., Addl., Hon., Dept., Secy., P.S. as abbreviations (distribution lists were being cut into false sentences); selftest added.

| Version | Mean closeness (body, 37 sentences) | Official sentences with no close match |
|---|---|---|
| Per-page, view 1 | 0.894 | 1 |
| Per-page, view 2 | 0.895 | 2 |
| Stitched 1 (the one to read) | 0.919 | 1 |
| Stitched 2 | 0.890 | 2 |

**Numbers.** Every number, date, reference, postal code, amount and e-mail address matched the official in every version **except one**: the year of a cabinet-meeting date (official 2026; both views, both readings and both translations 2023). The checker listed it as "still confirm"; both views agreed; no third view ran. **This is the only silent critical error on the document, and no part of the pipeline flagged it.** Table: 24 rows in the official and in every version; all 24 mean the same in every version (word for word equal: 14 to 15 of 24; the rest differ in "and"/"&" and commas, and in one "National Highway(s)" and one "Cooperative"/"Co-operation").

**Other real differences from the official English.** (1) One designation: the Assamese "co" prefix on a district officer's title was rendered "Sub-District" in **both stitched translations**, but correctly "Co-District" in **both per-page drafts**: the stitched (text-only) translation was worse here, the one place where stitching changed a content word. (2) Two distribution-list items (the Assembly officer's title "Principal Secretary" for the official's "Secretary"; one item pluralised with "for information") differ because **the Assamese file itself says so**: the readers translated what the Assamese says, not what the official English says. The two documents are not mirror images, which matters if the official English is what a court relies on. (3) A doubled "Notification No. Notice No." (literal) and a doubled "Annexure-A" in translation 1. (4) The official carries digital-signature names and dates and a file-number stamp that are not in the Assamese file at all; nothing could have produced them.

**Corrections to what I said after 10v.** I told the owner the annexure might be missing rows (24 of 32 listed): the official English lists 24 too, so it is the notice's own inconsistency. I called one word "softened": the official says the same, so it was right. I said translation 1 added words not in the source: the official has the same words. Three of my four hints were wrong; only the year was a real defect. Hints from my own reading of an unfamiliar script are not evidence.

**Findings.** (1) **The design's admitted blind spot is real and costly**: a digit misread identically in every view is invisible to agreement checks; the must-check list asks for it but only a person looking at the digit catches it. (2) **Stitching did not clearly beat page-by-page on a short document**: closeness 0.919 against 0.894/0.895 for the better translation, but 0.890 for the other, and the stitched versions made the one designation error that the per-page drafts did not. The advantage shown in 10t (no garbled seams) needs page breaks that fall mid-sentence; this document had none. (3) **An established-designation list would have caught the designation**: a short list of official titles used in the state's notifications (Co-District Commissioner and the like) that only raises a flag. (4) Pass rules of section 5: this document has 1 silent critical error (the year) in 1 document; the rule allows at most 1 per group, so it is at the limit, not over it, and one document is not a group. (5) Amber on all pages: the light did not separate the page with the error.

**Not done.** A third view on the page with the year (to see whether it would have caught it); a person's marks on the sheets.

### 10x. The third look, the date magnifier and the designation list (built and tested 2026-10-28; counts only, no names, places, case numbers or text)

**The question.** Would a third look have caught the misread year of 10v and 10w? **Answer: yes, if it had been run.** The third view (the page at ultra-high detail) read the year correctly in 2 of 2 runs (Rs 1.13 a call). The first two views had agreed with each other on 99.8% of letters, so the old rule (a third look only on a disagreement or under 97%) never fired. A re-read of the cropped date line was also right (2 of 2 runs, Rs 0.4 to 0.5) and of a tight crop of the date (2 of 2, Rs 0.4); a crop needs the position of the line, which the pipeline does not have, so only the full-page third look was built.

**Built.** (1) **Third-view rule**: a page that holds a date or an amount always gets a third look (as well as a page with a disagreement or under 97% agreement). `checker.third_view_contradictions` lists every agreed date or amount that the third view reads differently, puts it first in the report and the marking sheet, and turns the page amber with the two values side by side. It is a hint for a person, never an answer. (2) **Dates written with a month name** ("1940ರ ಆಗಸ್ಟ್ 21ರಂದು", "21 August 1940") are now recognised as dates in Kannada, Hindi, Assamese/Bengali and English (month list best-effort and not checked by a reader of those languages; a missing month only means that date is not seen as a date). Before this, no date in a month-name language was recognised as a date: the Kannada file showed no date item on any page. A year at the start of a line ("1950. March 14") was being stripped as if it were an item number; fixed. (3) **Marking sheet**: a magnifier follows the pointer over the page image (2 to 6 times); every date, amount, number and section row has a second line showing the original line with every digit run enlarged, and (when a third view exists) the third view's value in red if it differs; a value typed into "Value on the page" is flagged unless it equals one of the three readings; the CSV has a view-3 column. Tested in a real browser: no script error, the lens opens and closes, the typed-value flag works. (4) **Designation list** (`designations.txt`, 148 titles of Indian officials and court officers, written by Claude from general knowledge and **not checked by a reader or a lawyer**): a title in a translation that is close to a known title but not the same ("Sub-District Commissioner" against "Co-District Commissioner") is flagged in the page checks and the whole-document check; it only flags, never changes. `--designations FILE` replaces the list.

| Test | Result |
|---|---|
| Third view on the page with the year (10v) | contradiction found, date 2023 against 2026, in both runs; page amber with the values shown |
| Third views on 5 Kannada pages that hold dates (9 dates; sheets run earlier with no change) | 0 contradictions (0 false alarms in 9 dates) |
| Month-name dates detected on the Kannada pages (per-page readings) | 10 (17 on the joined text; a date split over two lines of a page is missed per page) |
| Designation flag on 10 English texts (the official, both translations, the per-page drafts of the notice; the Kannada drafts; the Assamese judgment drafts) | 1 true flag (the "Sub-District" title, in both stitched translations); 0 false flags after three fixes (a plural "-ies", a possessive "'s", a leading word such as "etc") |
| Cost of the new third-look rule | about Rs 1.1 to 1.4 for each page that holds a date or an amount; on the 9-page Kannada file about Rs 5 to 6 more (4 pages), on the 3-page notice Rs 1.1 more (1 page) |

**What this does not show.** One document with a misread digit; the third look read the year right in 2 runs, which is not a rate. A digit the third view also misreads would still be missed. Only dates and amounts get the third look (not other numbers: reference numbers, serial numbers, postal codes). The designation list catches a near-miss of a title it knows; a wrong title that is not close to any listed title is not caught. The Kannada and Hindi month names are best-effort. The marking-sheet changes are tested on two pages in a browser, not by a reviewer.

### 10y. The 50-number handwritten page (recorded 2026-10-28; counts only, no names, places, case numbers or text)

**What was tested.** One handwritten page supplied by the owner (who wrote it): 50 numbered lines in Assamese with dates, amounts, a phone-style number, a bank-account-style number, a land-record number, case and section numbers, and two small tables. The owner did not give the true values in advance; the tool read the page blind (two views plus a third at ultra-high detail, because the first two disagreed), the readings were sent to the owner, and the owner reviewed them and returned the list with corrections. Unchanged lines are taken as correct. Cost **Rs 6.75 logged**; the first two views agreed on 99.4% of letters.

| Measure | First look | Second look | Third look |
|---|---|---|---|
| Number values right (of 42 that could be graded) | 41 (97.6%) | 42 | 42 |
| Item numbers 1 to 50 right, as written on the page | 49 | 49 | 50 |

**Findings.** (1) **One value was read wrongly, by one look only** (a land-record number: a 4 for a printed 8); the other two looks were right, the checker listed it as a disagreement and the third look sided with the right reading. No value was wrong in all three looks. (2) **One value could not be graded**: the owner says its last digits are not clear from the image itself; the three looks gave three different readings of it (11 or 12 digits). The checker flagged it as a disagreement, which was the right outcome, but **no look used the [unclear] mark** the instruction asks for (0 marks in 3 reads); each guessed. (3) **One silent correction**: the writer numbered one line 88 where the sequence needed 48 (a slip on the page). The first two looks wrote 48, silently changing what the page says; the third look wrote 88 as written. The instruction is to keep every digit as printed and never correct; two of three looks broke it, and nothing surfaced the difference. (4) **Tool gaps found, all fixed**: the numbering check had never seen lists numbered "1. 2. 3." (it read lines after the item number was already stripped), so it could not have caught a numbering slip on any page since it was built; it now reads the lines as printed and also table rows that start with their number (71 earlier readings scanned: 2 flags, one of them this page's real slip); the no-model checks (numbering, impossible dates) now also run on the third view, so the page's slip is shown as "page check, third view only: numbered list skips from 47 to 88"; the third-view comparison now covers numbers and section numbers, not only dates and amounts (0 false alarms on the 12 earlier pages that have a third view); the date check no longer reads a table cell border as a date separator (it had raised 3 false "impossible date" flags on this page).

**What this does and does not show.** On this page, in 42 gradable values, no value was wrong in every look and none was wrong without a flag. Zero silent wrong values in 42 means the true rate could still be about 7% (rule of three); one page, one writer and one pen is a small sample. The page is easier than a real record (numbers on lines of their own, clean paper, good light). The one silent change was in the item numbering, not a value, and it was a slip by the writer: the machine "fixed" the page. In a legal record that kind of normalisation matters. The test did not cover names or meaning.

### 10z. A second, harder handwritten number page (run and scored 2026-10-28; counts only, no names, places, case numbers or text)

**What was tested.** A second handwritten page from the owner, a phone photo of crumpled paper with shadows and an angle: about 60 lines in two columns and sections (dates, amounts, a table with a total row, bank-account-style numbers, areas with decimals, case and section numbers). Same pipeline as 10y with no change to any prompt: two views plus a third at ultra-high detail (the pipeline ran it because the views disagreed). **Rs 5.49 logged.** Letter agreement between the first two views 99.6%.

**Where the three looks differ (34 lines with numbers; the three agree on 31).** A date of birth (year 1989 in looks 1 and 2, 1987 in look 3); one table cell (4,000 / 8,000 / 4,000); a monthly instalment (12,000 / 17,000 / 12,000). The checker flagged all three: the instalment as a disagreement between views 1 and 2 (the third look sided with view 1); the date of birth as the third look reading an agreed value differently (the 10x rule: a page with a date always gets a third look, and the comparison now lists it first); and the table cell through the new table-sum check below.

**Built during this test.** (1) **Table-sum check** (`redundancy.table_sum_flags`, no model): the amounts of a table column are added and compared with the printed total (a total row inside the table, or a total line right under it). On this page it flagged looks 1 and 3 (the expense column adds to 25,000 under a printed total of 29,000) and not look 2 (which adds to 29,000); the same check passed all three looks on the 50-number page. Arithmetic only: the writer's own sum may be wrong; it only says which readings agree with the page's own total. 74 readings scanned, 2 flags (both this page). (2) **A restart of numbering at 1 is a new list**: the numbering check (10y) raised three false "goes back to 1" flags on a page with several numbered sections; fixed. (3) The designation list lacked the classes of magistrates (first, second, third class); a page's "second class judicial magistrate" was flagged as a near-miss of "first class"; added.

**Results (owner's corrections received 2026-10-28).** 34 values could be graded; one more (the date of birth) the owner says is not clear on the page (the last digit "looked like the English 9", a shape that in Assamese handwriting is also how a 7 is written; the owner has not said which digit was meant).

| Measure | First look | Second look | Third look |
|---|---|---|---|
| Values right, of 34 | 33 | 31 | 33 |

- **One value was wrong in all three looks, with no flag: a mobile-style number** (the writer wrote ...201, every look read ...210, the pattern 9876543210). This is the dangerous case, an error the checks cannot see because every look agrees. Together with 10y (a numbering slip, 88 for 48, silently written as 48 by two looks) it is the second time a look wrote the regular pattern instead of what is on the page; two cases are a hint, not a rate [Likely: the readers pull toward familiar or regular digit patterns].
- **The two other differences were real misreads by one look**: the table cell (look 2 read 8,000, the page says 4,000) and the instalment (look 2 read 17,000, the page says 12,000). Both were flagged (a disagreement; the table-sum check), and looks 1 and 3 were right.
- **The table-sum flag turned out to mark the writer's own slip, not a reading error**: the true cell is 4,000, so the column adds to 25,000 under the page's printed total of 29,000. The one reading that made the column add up (look 2, 8,000) was the wrong one. The check says "this page does not add up", not "this reading is wrong"; an earlier remark in this section that it "says which readings agree with the page's own total" invites the wrong use and should not be relied on.
- **Date of birth**: looks 1 and 2 said ...1989, look 3 said ...1987; whichever is right, the checker's third-look rule put the date at the top of the list, as intended.
- **Totals across the two handwritten pages (10y and this one)**: 76 gradable values, 1 wrong in every look with no flag (1.3%; the true rate could be anywhere from a fraction of a percent to about 7%), 2 values wrong in one look only and flagged, 1 silent change to a numbering digit. Two pages, one writer.

**Not done.** A re-read of number lines digit by digit with an instruction not to complete patterns (a candidate fix for the pattern pull, not tried); a person's time on these pages.

### 10aa. The digit-by-digit read as a check on number lines (run 2026-10-29; counts only, no names, places, case numbers or text)

**What was tested.** The fix proposed after 10z: read every number on the page one digit at a time, with an instruction not to complete, repair or regularise patterns and to write [?] for a digit it is not sure of (`prompts/read_digits.txt`; the instruction names no particular number). Two runs on each of the two earlier handwritten pages (true values known from the owner, 10y and 10z) and two runs on each of two fresh images supplied by the owner (a line of dates in one row, and a short date with a mark above it; true values not yet received). The model was overloaded (HTTP 503) for about two hours, so the calls were retried until all finished; failed calls cost nothing.

**Scoring (values of three digits or more, or with a separator, counted with repeats):**

| | First look | Second look | Third look | Digit-by-digit, run 1 | Digit-by-digit, run 2 |
|---|---|---|---|---|---|
| Page of 50 lines (34 values) | 33 | 34 | 34 | 34 | 34 |
| Page 2 (28 values) | 27 | 25 | 27 | 26 | 26 |
| Both pages (62 values) | 60 | 59 | 61 | 60 | 60 |

**Findings.** (1) **It did not fix the pattern pull, but it broke the agreement**: the mobile-style number that all three normal looks read as the familiar ...210 (the page says ...201) was read ...211 in both digit-by-digit runs: still wrong, but no longer the same as the normal looks, so a method disagreement now flags it. Before, it was a silent error in every look. (2) **It was wrong where normal looks were right**: the monthly instalment (page says 12,000) was read 17,000 and 19,000; two of three normal looks had it right. As a second opinion it adds noise as well as signal. (3) **It read the writer's out-of-sequence line number (88 where 48 was expected) as written in both runs** (one run added an unrequested note naming the oddity); normal looks 1 and 2 had written 48. (4) It read the land-record number right in both runs (one normal look had it wrong). (5) **As a fourth look it left no wrong value agreed by every method on these two pages** (every wrong value in any method differed from another method), where the three normal looks alone left one. That is one value on two pages; it is a hint that a different way of reading has a different failure, not a measured benefit. (6) Cost: Rs 1.2 to 3.7 a call on a full page (about the cost of a normal read), Rs 0.3 to 0.4 on the small images.

**Fresh images (read blind; the owner's true values received the same day).** Image 1, a row of 9 dates, and image 2, a short date with a mark above it (both small, low-resolution crops: 765 x 87 and 235 x 120 pixels).

| | First look | Second look | Third look | Digit-by-digit, run 1 | Digit-by-digit, run 2 |
|---|---|---|---|---|---|
| Image 1, dates right of 9 | 8 | 9 | 8 | 9 | 7 |
| Image 2, date right of 1 | yes | yes | **no (year 96)** | yes | yes |

- **No date was wrong in every method.** The errors were all look-alike digit slips of single looks: a 9 read as 1 (third look and one digit-by-digit run), a 10 read as 13 (first look) and as 15 (one digit-by-digit run), a year 93 read as 96 (third look). Majority across the five looks would have been right on all ten dates; it would not have been right on the instalment of 10z (a tie) or the mobile number (all wrong), so it is not a rule.
- **The third look was wrong twice on these small images** (9 for 1; 93 for 96), after being right on the notice (10v). The checker's rule "the third look reads an agreed value differently" therefore raised **two false alarms in ten dates here** (the agreed first two looks were right both times). A person looking at the page settles each at once; but the higher-detail setting cannot add detail a tiny image does not have, and on these crops it did no better than the normal looks.
- **The digit-by-digit read was perfect in one run and made two slips in the other** (9 for 1; 10 for 15): run-to-run variation is as large as the difference between methods.
- Image 2: the second look listed the small mark above the date as a separate line, which lowered the letter agreement to 80% and turned the page red; the date itself was right in four looks.

**Totals so far over four handwritten pages (72 values)**: first look 69, second look 69, third look 69, digit-by-digit run 1 70, run 2 68 right. **One value (the mobile-style number on page 2) was wrong in every normal look with no flag**; no other value was wrong in all methods. Every method makes a few look-alike slips (about 3 to 6% of values); they differ from one another, which is why disagreement flags work, and why a value on which every look agrees can still be wrong.

### 10ab. Does enlarging a small crop help the reading? (run 2026-10-29; counts only, no names, places, case numbers or text)

**What was tested.** Nine small crops with known values: two small images from the owner (a row of 9 dates, a single date) and seven single lines cut from the two earlier handwritten pages (three phone-style numbers, a land-record number, a date, a transaction number, an instalment, a table cell). Each crop was read blind with one short instruction (transcribe exactly, keep digits as written, [?] if unclear), in four variants, two runs each: as given, enlarged 2 times, enlarged 4 times (plain Lanczos resizing, no sharpening or contrast change), and as given with the ultra-high-detail setting. 72 reads, **Rs 21.86 logged** (Rs 4.5 for each of the three plain variants, Rs 8.3 for the ultra-high one).

**Two crops are left out of the scoring because the owner's key and the crop reads disagree** (the owner is asked to look again): a transaction number (every one of the 8 crop reads says ...109; the key, and all five full-page reads, say ...107) and an instalment (all 8 crop reads say 17,000; the key says 12,000; the full-page reads said 12,000 twice and 17,000 or 19,000 three times). Both turn on a look-alike digit pair, which is also where a person checking the key can slip. Seven crops remain: 15 values per run, 30 per variant.

| Variant | Values right (of 30) |
|---|---|
| As given | 27 |
| Enlarged 2 times | 24 |
| Enlarged 4 times | 25 |
| As given, ultra-high detail | 25 |

**Findings.** (1) **Enlarging did not help; as given was best** (27 against 24 to 25). A difference of 2 to 3 values in 30 is within the run-to-run variation seen elsewhere (10aa), so the safe reading is "no gain from enlargement or the higher-detail setting on small crops", not "enlargement hurts". (2) **The errors do not move with the picture size**: a 9 read as a 1 (first look at the date row), the 10 read as 13, a year read 96 for 93, and the last two digits of the phone-style number page 2 (read ...212 or ...211 in 7 of 8 reads, never ...201, never the familiar ...210 either). Those are look-alike digits, not lack of pixels. (3) No variant fixed the phone-style number that every normal look had read as ...210. (4) The answer key itself is a source of doubt: where a person's key and the machine's reads disagree on a look-alike digit pair, the page itself must settle it, and the sheet's magnifier and enlarged digits are built for that.

**Decision.** No change to the pipeline: no automatic enlargement, no separate crop re-read. **Not tried:** sharpening and contrast (10p found them unhelpful on whole pages), other resizing methods, crops of different sizes, printed rather than handwritten digits.

### 10ac. A handwritten text page and a short text translation (run and scored 2026-10-29; counts only, no names, places, case numbers or text)

**What was tested.** (1) A handwritten Assamese page from the owner (a cropped video frame on ruled paper: a heading and four numbered lines, clear writing, no names), read blind with the normal pipeline (two views; no third view needed). (2) Six short Assamese sentences supplied by the owner as typed text (they did not belong to the image), translated twice with the text-only call. The owner supplied the correct English. Cost Rs 0.74 for the page and Rs 0.30 for the six sentences.

**Results.** (1) **Page: all four lines and the heading were read and translated correctly, in both views** (the owner's verdict; one phrase differed between the two English drafts and the owner accepted both wordings); letter agreement between the views 100%. **One gap, not scored by the owner:** the heading says there are five tips, the page shows four, and the bottom edge of the crop cuts off part of a fifth line, which the tool did not transcribe or mark; this is the third time a number in words or digits (here, the number of list items) disagreed with what the page holds and the tool said nothing (10w: 32 departments against 24 rows). (2) **The six sentences: all six were translated correctly in both drafts** (the owner's reference); mean closeness to the reference 0.80 and 0.83, one sentence in each under 0.6 (word order and word choice differ: one sentence says "through education" where the reference says "to study"; the meaning is the same).

**What this does not show.** Clean handwriting, short sentences, one page, no names and no numbers beyond a count; the names test is still to do.

### 10ad. A handwritten notebook page with names (run and scored 2026-10-29; counts only, no names, places, case numbers or text)

**What was tested.** A phone photo (3072 x 4080) of one handwritten notebook page: a few personal names, a place, a village number and a few short sentences, messy writing at an angle. Read blind: two views, a third because letter agreement was 96.5% (under 97%), and the names-as-printed translation of the first view run twice. The owner supplied the correct readings and English. Cost about Rs 2.0 logged. The owner's key leaves out one line that all three looks read (a name-like line), so that line is not scored.

| Item | First look | Second look | Third look |
|---|---|---|---|
| The writer's own name (3 words) | right | right | right |
| A short given name (English) | right | right | right |
| A first name in a pair (the pair's second name right in all) | wrong | wrong | right |
| The place | right | right | right |
| A village number | wrong (same digit slip in all three) | | |
| "Accused" (a legal term) | right | wrong ("criminal") | right |

**Findings.** (1) **No silent wrong name**: the one name that was read wrongly by two looks (three different readings across the three looks) was flagged as a disagreement; the third look had it right. The names-as-printed translation of the first view carried that wrong name through (it is built from one view's reading, so it inherits the view's errors). (2) **The village number was misread by every look and nothing flagged it**: the key says 124, all three looks read 424; the same look-alike digit pair as in 10z. (3) **A word that means both yesterday and tomorrow was silently resolved as "yesterday"** by the first two looks and both names-as-printed translations; the third look hedged ("tomorrow/yesterday"), which is the faithful rendering; the key says "tomorrow". The same word in the next sentence was right in looks 1 and 2 and "yesterday" in both name translations, so the translations were inconsistent with each other. (4) **An insult was translated with a specific English word in every look** where the key keeps the Assamese word untranslated: a choice the reader made for the translator. (5) A common word meaning "go on" or "come on" was rendered "come" (looks 1, 2) and "crazy" (look 3). (6) In the names rule's first run, an unreadable word was marked "(?)" and spelled by sound, where the third look had written a famous name that may have come from the model's memory; the key does not cover that line, so this cannot be scored.

**Candidate fixes (not built).** For words that the text cannot settle (yesterday or tomorrow, an insult or slang word), write the word as spoken with its possible meanings in brackets instead of choosing; run the names-as-printed translation from the checked reading of all looks, not from view 1 alone. Because these were suggested by this page, a fair test needs a fresh page.

**Limits.** One page, a handful of names, one writer.

## 11. The checked-reading pipeline (design recorded 2026-10-27, rewritten 2026-10-28 after sections 10l to 10p; built, rehearsed once, not yet run on a real test set)

This replaces the first version of this section, which used Cloud Vision as a second reader. It changes no pass rule in section 5.

**Why this shape.** No second model was safe as an independent reader of dense or handwritten Assamese (10l, 10m): the other Gemini models changed meanings, and Cloud Vision garbled the faded pages (10o; it found 17 of 20 values the owner confirmed, but its sentences were nonsense). Two identical argon runs agree with each other even when both are wrong (10p: both read a handwritten date with the same wrong day), so the second read is made of a **different view of the same page**, and the disagreement between views is the signal. Agreement is never treated as correctness.

**Steps for one page.**
1. **Receive and gate** (person). Language and page type (typed or handwritten). Nothing that identifies a minor or the victim of a sexual offence is sent. Original scans at 300 dpi or better are worth more than any processing.
2. **PDFs: triage** (`pdf_triage.py`). The text layer is compared with the rendered page on base letters only (a PDF drawn without proper Assamese shaping shows vowel signs in the wrong places while its text is fine). Good text layer: use it, no reading model. No text, junk text, or a mismatch: read the page as an image. A person decides when the evidence is mixed (read as an image by default). Reader for the comparison: Tesseract (local; 83.3% on the one good file) or Cloud Vision (97.7%; sends each PDF page to Google).
3. **Views** (`pipeline.py`). View 1 is the image as given. View 2 is the same image with a white border (6% a side). **No contrast boost and no straightening**: both made the readings less steady (10p).
4. **Two blind reads** by `gemini-4-argon`, same instructions (`prompts/read_translate.txt`), neither sees the other: original-script text, then an English draft. A run that ends without a finish signal is cut off and the page is red.
5. **Third view only if flagged**: the original image at ultra-high detail (a per-image setting on the alpha API, about Rs 0.2 more a call). It is used only to show which side of a disagreement it sides with, as a hint.
6. **Checker** (`checker.py --page`, `redundancy.py`). Letter agreement between the views; the must-check list (dates, amounts, ages, numbers, sections, names, land units); English sentences that changed between the views; `[unclear]` and `(?)` marks; dropped or cut-off text; and the checks that need no model: impossible dates, numbered lists that skip, English amounts whose digits and words disagree, the same name spelled two ways across pages, names close to a confirmed name (flagged, never corrected).
7. **PDF pages with a good text layer** skip steps 3 to 5: the exact text is translated twice with a text-only call (`prompts/translate_text.txt`, which tells argon to transliterate and mark (?) where a passage has no clear meaning), and the two English drafts are compared (`checker.check_text_page`).
8. **Traffic light, as a reading order only.** Red pages are read first, then amber, then green; **a person reads every page in full for now.** Red: a cut-off or missing reading, much less text in one view, or the views agree on under about 90% of letters. Amber: any must-check item differs, an English sentence changed, doubtful words marked, a page check fired, agreement under about 97%, or the page is handwritten. Green: a typed page with agreement of about 97% or more and nothing flagged. A handwritten page is never green.
9. **A person checks** on the marking sheet (`marksheet.py`): type what the page really says for each value (the sheet flags at once a value that differs from both readings), log every error, download the CSV. A second person re-checks about 1 page in 10 to measure the reviewer's own error rate.
10. **Output**: a report per page (`report.py`, printed to PDF with `print_pdf.js`) with the stamp "Machine draft. Not a certified translation.", a marking sheet, and a summary with red pages first.

**What each check can and cannot catch.**

| Check | Catches | Misses |
|---|---|---|
| View 1 against view 2 (different views of one page) | slips that depend on how the page looks; a run that stops early; a date read differently when the view changes | an error made in every view: the one wrong printed name (10p) was read the same wrong way in all 7 readings |
| English sentences, view 1 against view 2 | a sentence whose meaning wobbles | a wrong meaning given both times |
| Redundancy checks | impossible dates, skipped numbering, an English amount whose digits and words disagree | everything that is internally consistent but wrong |
| A person with the page image | everything on the must-check list and the flagged lines | whatever nobody looks at |

**Dropped, and why.** Cloud Vision as a reader or a light (10o); Google Translate (nonsense on the faded pages); Tesseract as a reader; `gemini-3.5-flash`, `gemini-3.6-flash`, `gemini-3.7-flash`, `gemini-3.8-flash` (10l, 10m); Sarvam (10b to 10j; no confidence output, silent meaning changes); token log-probabilities (argon returns them, but the one known wrong name was read at 98% confidence).

**Cost and time (estimates).** A rehearsal on one image page (3 reads) and one text-layer PDF page (2 translations) cost about Rs 4.4 logged; about 12 seconds a read. A typed image page costs about Rs 2.2 logged for two views, about Rs 3.5 with the third. The real bill has run 1.5 to 2 times the logged figure (10k): budget about Rs 4 to 7 a page for a 30-page set, so Rs 150 to 250, and set `--budget-inr`. Person time is unmeasured; the owner's checking of a typed page took 10 to 15 minutes (10o). The translator timing test (section 2, 5 pages) still decides the 30% rule.

**Status of the parts (2026-10-28).** (Third-look rule, month-name dates, magnifier and designation list: added after 10w, results in 10x; a page that holds a date or an amount now always gets view 3.) Built and selftested on invented text: `checker.py`, `redundancy.py`, `report.py`, `pdf_triage.py`, `harness.py`, `marksheet.py`, `pipeline.py`, `stitch.py`. **Whole-document pass (added after 10t, results in 10u):** for a PDF of two or more pages, the pipeline joins the pages and translates the joined text twice (names by sound with the original-script word in brackets, printed numbers and references kept, `[sic]` on a suspected misprint), checks the two translations and the printed clause/rule/section numbers, and writes a whole-document report next to the page reports; the page-by-page reports are still made. Run for real: the readers and views on four typed pages (10l, 10o, 10p); PDF triage on two files; the whole pipeline once on one image page and one text-layer PDF. **Not built:** amounts in words against digits in the original script (needs a checked Assamese number-word parser), weekday against date; page preparation beyond padding (deliberately); a Kannada or Hindi check (nothing here has been run on those). **Not yet tested:** the traffic-light cut-offs on a full set; handwritten pages through the final pipeline; mixed PDFs (some pages with a text layer, some without).

**Known weak points.** (a) Handwritten pages can never be green, and most of the court material is handwritten. (b) An error made in every view is invisible to the machine checks: only a person or an outside check catches it. (c) Argon fills in meaning where there is none (10m), only partly curbed by the text prompt. (d) The cut-offs are guesses from four typed pages. (e) The ultra-high detail setting uses the alpha API and may change. (f) No page has been marked by more than one person, so the reviewer's own error rate is unknown.

**How the next real test will be read.** For each page: the light the pipeline gave, the errors the reviewer logs, and the silent critical errors (an error on a page the pipeline did not send for full reading, or an error the checker did not point at). The pipeline counts as worth carrying forward only if the red and amber pages catch the pages with critical errors; the section 5 pass rules are applied to what is left.
