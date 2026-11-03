# Legal-AI adoption checklist: an expert's four requirements against what is built (stored 2026-11-03; owner: "Save this for later")

NOT a plan and NOT approved; nothing here is started. Revive only when the owner raises it (adoption by law firms, firm-private upload, on-prem, the lawyer-marked ruler, or "what is open").

The expert's list (as the owner gave it): 1 knowledge ingestion; 2 personalised workflows; 3 custom deployment (on-prem or hosted, plus a GPU); 4 evals and improvement loops.
Claude's assessment, 2026-11-03 (the list describes selling to large firms; our audience today is the public plus individual lawyers). Score: about 1 to 1.5 of 4.

1. **Knowledge ingestion: sound, most important.** Built: public law (BNS, BNSS, 13 Acts on the shelf, 68-case library, wide index of 10-19k judgments, the register). NOT built: a firm's own documents (precedents, clause banks, matter files, past opinions). Partial.
2. **Personalised workflows: sound, drives adoption.** Built: layperson and lawyer modules, Research Note, PDF/Word export, follow-ups, saved chats, search page. NOT built: drafting (not approved), per-firm templates, house style, checklists. Weak.
3. **Custom deployment: half right.** Confidentiality is a real barrier [Certain]; the GPU is doubtful: we call hosted models (Anthropic, Voyage), a GPU matters only if a client insists on local open models, likely with lower quality [Likely]. Today: hosted on Railway, client text goes to third-party APIs, no per-firm separation, privacy policy and DPDP consent not yet drafted by a lawyer. None.
4. **Evals and improvement loops: sound, earns trust.** Built: the machinery (grounding and quote checks, invented-case check, cost logs, feedback notes, measured retrieval sets). NOT built: lawyer-grounded truth (every question set is Claude's; no hallucination rate measured; the lawyer-marked ruler, `SUPPORT_AND_FIT_PLAN.md` S0, is parked) and a loop from real usage to reviewed corrections. Half.

Left out of the list: citation trust (we have done most here), professional liability, fit with Word and the tools lawyers already use, pricing, security assurance.

Suggested order if revived: (1) a small lawyer-marked ruler (item 4; cheapest, the only route to any accuracy statement); (2) firm-private upload (item 1; needs the privacy policy first); (3) on-prem only when a paying firm asks.
Say "no hallucination rate has been measured", never "accurate" or "safe".
