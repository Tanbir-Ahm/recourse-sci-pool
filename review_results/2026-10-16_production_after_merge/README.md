# Production checks after the merge of Recourse PR #2 (2026-10-16)

## Check 1: the gate still closed (`q2_refusal_production.txt`)

**What was done (by the owner, on recourse.co.in, after merging PR #2 into Recourse `main`, `74d13ce`):** the TADA appeal question (Q2 of the staging test, naming Bilal Ahmed Kaloo v. State of Andhra Pradesh (1997)) was asked with `SCOPE_GATE` still unset, so the topic bar was closed. Output: `q2_refusal_production.txt` (pasted by the owner; Claude cannot see Railway).

**What the page showed:** the refusal ("Recourse can't help with this one") and, under it, the box "Currency notes (checked by code, not by the model)" with ONE sentence: Bilal Ahmed Kaloo (1997) was overruled by Nalini (1999).

**What that proves (Claude ran the same question through the register code offline in two checkouts; the note is a deterministic function of the code and the register bundle):**

| Code | Note produced for this question |
|---|---|
| Recourse `9ea94bb` (before the held rows) | "Bilal ... (1997) was overruled by ... Nalini ... (1999). Note: ... Nalini ... was itself later overruled by Bilal Ahmed Kaloo ... (1997); the current position should be checked." (the false chain sentence) |
| Recourse `74d13ce` (merged `main`) | "Bilal ... (1997) was overruled by ... Nalini ... (1999)." (one sentence) |

Production showed the one-sentence form, so the website service runs the held-rows code (at least `6e092fc`, which carries the NALSA link fix and the "reported" clause in the same deployment). Also shown: refusal notes work live on production (they exist only from `9ea94bb`), and the register is ON there. [Certain for the register code. The exact deployed commit (`74d13ce`, or `6e092fc` / `f76cd6a`, which have the same register code) cannot be told apart from this output, and Claude has not seen the Railway deployment list.]

**What it does not show:** levels 2 and 3 of the register notes (this question names the case with its year, level 1); the NALSA link fix and the "reported" wording (both need an answered question); any answer to an opened question (the gate was closed); the staging answers the owner said "look fine" (never sent to Claude).

## Check 2: the gate open (`q2_answer_gate_open_production.txt`)

The owner then set `SCOPE_GATE=open` on production and asked Q2 again. He wrote that he was sending the answer and the `SCOPE_OPEN` line; **only the answer arrived**. Unseen: what the library supplied (`SCOPE_OPEN` `library` and `wider`), the cost (`COST_QUESTION`), and the contents of the "Read the source" box (closed or empty in the paste, so whether the NALSA link is gone is NOT shown).

**Worked:**
- an answer instead of the refusal, with the fixed notice at the top;
- the opening paragraph says Bilal (1997) was overruled by Nalini (1999): the right direction, from the verified row; a step later says "reported to have been overruled";
- no false "Nalini overruled by Bilal" note and no "itself later overruled" chain sentence;
- the wider-search box (feed mode) lists five passages and puts the register line on the four that name Bilal.

**Defects found (nothing fixed yet; the owner's go is awaited):**
1. **The "not checked" sentence names the overruling case:** "Cases named in this answer that we have not checked: SIT v. Nalini and Others." The name finder (`overlay.case_mentions`) cuts "State through Superintendent of Police, CBI/SIT v. Nalini and Others" at the comma and the slash and keeps "SIT v. Nalini and Others", which does not match the register's full name, so the rule that leaves out overruling cases fails. Reproduced offline on the pasted answer text [Certain]. Cosmetic, but the box then says the controlling case is unchecked.
2. **A library section is stretched over a case it does not fit.** Step 3 says to ask whether an appeal lies to the Supreme Court "under Section 420 of the BNSS". The library's text of BNSS 420 is only the appeal where the High Court has reversed an acquittal and sentenced to death, life or ten years or more [Certain]; it does not fit a conviction by a TADA Designated Court. [Likely] the real route is an appeal to the Supreme Court under section 19 of TADA (from general knowledge of law, not in the library; Mr. Advocate to confirm), and the BNSS does not govern an old-regime TADA trial. Step 2's BNSS 404(2) (certified copy of the judgment on application) does match the library text. No check catches a retrieved section being misapplied; this is the failure mode to expect from an open gate.
3. **The account of Bilal's facts and holding is not in the material.** The answer says Bilal's accused was "convicted of offences including the sedition-type offence" and describes what the Court held. None of the five fed passages states what Bilal's accused was convicted of or the holding: they carry counsel's argument in Nalini and quotations cut off at "...". [Guessing] "sedition-type" came from the question's own word. A lawyer must read the judgment.
4. The wider-search box lists the same passage three times (three PDFs, 1999-05-11, connected appeals).
5. The pasted answer begins with the line "our situation" (unexplained; probably a copy glitch).

**Proposed, awaiting the owner's go:** (a) fix 1 in `goodlaw/overlay.py` and re-export the bundle; (b) add a clause to the scope note for opened topics: do not present a BNS or BNSS section as the governing provision or the appeal route for a matter under another statute unless the material shows it applies; say that the route comes from that statute and is not in the material (the Hard rules block stays untouched); (c) test both on staging before the next merge; (d) Mr. Advocate reads this answer.
