# Test plan: reading and translating local-language court and police records

Written 2026-10-25 for the lawyer who asked for a tool that reads and translates trial-court and police records written in Assamese, Kannada and other local languages. The plan was fixed before any result existed. Section 10 records the first results (one real document, scores only); the rest of the plan is still to be run.

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
