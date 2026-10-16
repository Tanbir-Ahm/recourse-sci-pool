# Production check after the merge of Recourse PR #2 (2026-10-16)

**What was done (by the owner, on recourse.co.in, after merging PR #2 into Recourse `main`, `74d13ce`):** the TADA appeal question (Q2 of the staging test, naming Bilal Ahmed Kaloo v. State of Andhra Pradesh (1997)) was asked with `SCOPE_GATE` still unset, so the topic bar was closed. Output: `q2_refusal_production.txt` (pasted by the owner; Claude cannot see Railway).

**What the page showed:** the refusal ("Recourse can't help with this one") and, under it, the box "Currency notes (checked by code, not by the model)" with ONE sentence: Bilal Ahmed Kaloo (1997) was overruled by Nalini (1999).

**What that proves (Claude ran the same question through the register code offline in two checkouts; the note is a deterministic function of the code and the register bundle):**

| Code | Note produced for this question |
|---|---|
| Recourse `9ea94bb` (before the held rows) | "Bilal ... (1997) was overruled by ... Nalini ... (1999). Note: ... Nalini ... was itself later overruled by Bilal Ahmed Kaloo ... (1997); the current position should be checked." (the false chain sentence) |
| Recourse `74d13ce` (merged `main`) | "Bilal ... (1997) was overruled by ... Nalini ... (1999)." (one sentence) |

Production showed the one-sentence form, so the website service runs the held-rows code (at least `6e092fc`, which carries the NALSA link fix and the "reported" clause in the same deployment). Also shown: refusal notes work live on production (they exist only from `9ea94bb`), and the register is ON there. [Certain for the register code. The exact deployed commit (`74d13ce`, or `6e092fc` / `f76cd6a`, which have the same register code) cannot be told apart from this output, and Claude has not seen the Railway deployment list.]

**What it does not show:** levels 2 and 3 of the register notes (this question names the case with its year, level 1); the NALSA link fix and the "reported" wording (both need an answered question); any answer to an opened question (the gate was closed); the staging answers the owner said "look fine" (never sent to Claude).
