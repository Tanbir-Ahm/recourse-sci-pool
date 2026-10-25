# Test plan: reading and translating local-language court and police records

Written 2026-10-25 for the lawyer who asked for a tool that reads and translates trial-court and police records written in Assamese, Kannada and other local languages. Nothing has been built or run yet. This plan decides what we test, on what, and what result counts as a pass, before any result exists.

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

- **Reading (page image to text in the original script):** a general vision AI model; an Indian-language document reader such as Sarvam Vision; a Google document OCR service; and free OCR (Tesseract) as the baseline.
- **Translation (to English):** an AI model; IndicTrans2 (free, open-source); Google Translate.
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
