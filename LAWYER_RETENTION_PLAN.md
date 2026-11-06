# Keeping the lawyer: matters, clocks, hearing briefs, pricing (stored 2026-11-06; owner: "Save this for later")

NOT a plan approved for building and NOT started. Revive only when the owner raises lawyer retention, personalised workflows, matters, clocks, drafting, pricing or payments, or asks what is open. Drafting stays unapproved: ask before starting it. Everything here is Claude's reasoning; demand is unverified. No hallucination rate has been measured.

**Core point.** A lawyer comes, asks a question and leaves because a question box is a utility. Lawyers return for their MATTERS: open cases, dates, drafts, reminders. Retention = the tool holds something painful to leave.

**The shift: from "a question" to "a matter".** A matter = court, case number, sections charged, stage (FIR, arrest, remand, bail, chargesheet, trial, appeal), next hearing date, facts stated once. Questions asked inside a matter are answered with that context. Saved chats already exist in the API (A3); a matter is mostly those chats grouped under a folder plus a few structured fields, so the smallest version is not a rebuild.

**Ideas, ranked by stickiness against risk**
1. **Legal clocks that come to the lawyer (top bet).** Code counts days from dates the lawyer enters: default bail (BNSS 187: "Day 54 of 60 ..."), the 24-hour production rule, appeal limitation, the cheque-bounce notice and complaint windows (NI Act s.138). Reminders by WhatsApp or email. Fixed rules, so no model and almost no hallucination risk; the arrest-compliance checks already use fixed rules [Likely a base]. Must show its working and let the lawyer override; a wrong clock is worse than none.
2. **Hearing brief and daily diary.** Before a date: sections, last order, pending clocks, pinned authorities. After: a voice note (voice input exists in Streamlit) structured into the matter, asking for the next date. A daily habit.
3. **Pinned authorities with currency alerts.** A pinned case that later appears on the Overruled Register triggers an alert. The register covers only part of the law and only subtracts trust: never say "good law".
4. **Drafting in the lawyer's own style (NOT approved).** Bail applications and petitions from the matter, the lawyer's past drafts as the style source; statute text inserted verbatim by code, only checked citations, every draft marked for review. Biggest hallucination risk, biggest switching cost.
5. **Private library.** The lawyer uploads their own drafts and orders and searches them. Needs a lawyer-written privacy policy and DPDP consent first (placeholder today; gate G1).
6. **Client status page.** Plain-language "what happens next" in Hindi or another language, sent by the lawyer; a small referral effect.
Wedge worth considering: cheque-bounce (NI Act s.138) work, high volume for small practices with strictly statutory clocks; the library already has the flow.

**Payment: charge for the matter, not the answer** (per-answer pricing invites comparison with free chatbots).
- Free: today's 20 answers a day, no matters. Solo: N active matters, clocks and reminders, exports, a monthly drafting allowance. Chambers: seats, shared matters, shared library.
- Measured cost [Certain]: Rs 4.1 to 4.4 per answer. Five questions a day for 22 days is about Rs 450 a month in answers alone, before drafting, so the Solo price is likely above about Rs 1,000 a month unless cost falls (cheaper model for some steps, caching). Price points are guesses [Guessing]: test with real lawyers.
- Payments: Razorpay and a small webhook service; Stage 1 of the staged path (the trigger is the owner wanting paying or tracked users); needs the lawyer-drafted privacy policy and consent first.

**Why lawyers leave:** one wrong or invented citation (our checks, register and honest labels are the moat); confidentiality fear (promise plainly: client data private, not used for training, deletable, client names optional); no fit with Word and WhatsApp (exports and reminders cover this).

**Cautions.** Demand is unverified: sit with 10 lawyers (Mr. Advocate plus nine) first; ask what they track and where they lose time; test fake-door buttons. eCourts auto-tracking of dates may be powerful but feasibility and terms are unknown [Guessing]: start with manual dates. Do not build it all. Smallest useful product: matters, clocks, a hearing brief, Word export, WhatsApp reminders (WhatsApp work is HELD by the owner, WHATSAPP_PLAN.md; email first, or ask).

**Retention measures:** weekly active matters per lawyer; returning within 7 days; share of matters with a next date set.

**Decisions needed from the owner when revived:** which practice area first; whether and when to approve drafting; whether to interview lawyers first; the privacy policy and consent (lawyer-drafted); the price after testing.
