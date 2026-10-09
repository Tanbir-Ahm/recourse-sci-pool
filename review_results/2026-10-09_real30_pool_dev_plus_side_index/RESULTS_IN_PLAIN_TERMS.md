# The library fix, in plain terms (2026-10-09)

**The problem.** Three of the 30 questions (Q6, Q15, Q21) could not be answered from our library, because the judgment that gives the current answer was not in it. For Q21 (is a certificate needed for CCTV footage?) the library held the old ruling (Shafhi Mohammad, 2018) but not the court's later ruling that overruled it (Arjun Panditrao, 2020). Arjun Panditrao was in our collection but our own filter had left it out as "not criminal enough".

**What I did.** I did not touch the main library. I made a small second library (17 judgments, 2,572 paragraphs, 6 MB, cost $0.10) holding the judgments that the Overruled Register says correct a ruling we hold, but that our filter had left out. Then I ran the same 19 tuning questions again over "main + small library" ($0.09).

**What happened.**
1. **Q21 is fixed as far as finding goes.** The 2020 ruling now comes second in three of the four versions of the search (third in the other). Before, it was not there at all.
2. **The old ruling still comes first.** The search cannot know that a ruling was overruled. That is the job of the register: it would put a badge on Shafhi Mohammad. So the two parts need each other: the library must hold the new ruling, and the register must mark the old one.
3. **Nothing else got worse.** 88 of the 100 result lists are identical to before; 4 of the 12 that changed are Q21 itself; the other 8 moved by one place or swapped one paragraph, and none of the new judgments is in them. That is the normal small shake you get from adding any text to the library.
4. **The other 16 added judgments did not show up in the top ten for any of the 19 questions.** Most are civil, tax, land, service-law and constitutional cases; three are criminal-procedure judgments (Antulay, Singhara Singh, Baliram Hiray). Each corrects a ruling that our library holds. They matter for a library that tells users when a ruling has been replaced, not for these questions.

**What I could not do.** Q6 needs the Supreme Court's order of 23 August 2024 on prisons, and Q15 needs Shivangi Bansal (July 2025). Neither is in our collection, and from this working environment I cannot reach the court's website or Indian Kanoon (the network policy refuses the connection). To fix it: allow `api.sci.gov.in` and `indiankanoon.org` for the environment, or upload the two documents.

**What it means for the test.** Nothing in the measurement changes: J and S's marks are on the main-index results. If you want the final system to include the small library, the sealed run (which can be done only once) has to be done with it, so decide before that run.
