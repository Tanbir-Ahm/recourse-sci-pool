# Test plan: reading and translating local-language court and police records

Written 2026-10-25 for the lawyer who asked for a tool that reads and translates trial-court and police records written in Assamese, Kannada and other local languages. The plan was fixed before any result existed. Sections 10 to 10c record the results so far (one real document, scores and counts only); the rest of the plan is still to be run.

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
