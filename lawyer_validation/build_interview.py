"""Builds LAWYER_INTERVIEW_SCRIPT.docx (python build_interview.py)."""
from docx.shared import Pt
from docx_kit import *

d = new_doc(margin_cm=2.0, base_pt=10.5)
footer(d, "Recourse · lawyer interviews · internal · not for the lawyer")

d.add_paragraph("Talking to ordinary lawyers", style="Title")
para(d, "Interview script for ten lawyers, about 35 minutes each. Written 21 November 2026.", italic=True, color=GREY, after=6)

box(d, [
    "**What this is for.** We do not yet know what an ordinary lawyer would come back to Recourse for. Every plan so far (matters, clocks, drafting, a hearing-prep sheet) is our guess. These ten conversations are how we find out, before we build more.",
    "**The one rule.** Ask for stories about the last time, never opinions about the future. People are polite about ideas and honest about their last Tuesday.",
], fill="E8F1E9")

d.add_heading("1. Who to talk to", level=1)
bullets(d, [
    "**Ten criminal practitioners.** Mix on purpose: three juniors (up to 5 years), four in the middle (5 to 15 years, district and Sessions courts), two who appear in the High Court, one who still works mostly on old IPC and CrPC matters.",
    "**At least two who doubt AI tools.** Their objections are the most useful ones.",
    "**Not Mr. Advocate.** He is our reviewer and knows the tool. He can sit in as a ninth or tenth voice only after the other eight.",
    "**Not friends who will be kind.** Ask each lawyer at the end who else we should talk to, and take the second name, not the first.",
    "**Language.** Hold the interview in the language the lawyer prefers (English, Hindi, Assamese). Translate the questions in your head, not on paper; the meaning matters, not the exact words.",
    "**Thank them.** Offer a free hearing-prep sheet for one of their matters (see the other document). It is a thank-you and a test in one.",
])

d.add_heading("2. Rules for the person asking", level=1)
table(d, ["Do", "Do not"], [
    ["Ask 'tell me about the last time you ...'", "Ask 'would you use a tool that ...?' (everyone says yes)"],
    ["Stay quiet after a question. Count to five.", "Fill the silence or suggest an answer"],
    ["Ask 'what happened next?' and 'how long did that take?'", "Explain what Recourse does or defend it"],
    ["Write down their exact words, especially complaints", "Promise anything: dates, features, accuracy"],
    ["Ask what they do today, even if it is clumsy", "Say the tool is accurate or safe. We have no measured error rate."],
    ["Show the sample sheet only at the end (part G)", "Take any real client paper or name in the interview"],
], [8.5, 8.5], size=9.5)
para(d, "", after=2)

d.add_heading("3. Before you begin: say this aloud", level=1)
box(d, [
    "\"Thank you for the time. This is 35 minutes. I am not selling anything. I am trying to understand how lawyers prepare for hearings, so that we build something useful and not something clever. Please do not tell me any client's name or details. I will take notes and will not record unless you agree. What you say is used only to decide what to build, and I will not quote you by name. You can stop me at any time.\"",
], fill="F3F4F6", size=10)

d.add_heading("4. The questions", level=1)

def part(title, minutes, qs, probes=None, note=None):
    d.add_heading(f"{title}  ({minutes} min)", level=2)
    if note:
        para(d, note, italic=True, color=GREY, size=9.5)
    numbered_items = qs
    for q in numbered_items:
        p = d.add_paragraph(style="List Bullet")
        add_runs(p, q)
        p.paragraph_format.space_after = Pt(2)
    if probes:
        para(d, "Probes: " + "  ·  ".join(probes), italic=True, color=GREY, size=9.5, after=4)

part("A. Their practice", 3, [
    "How many years have you practised? Which courts do you appear in, and what kinds of criminal matters?",
    "Do you work alone, with juniors, or with a clerk? Who does the first reading of the papers?",
    "Roughly how many of your live matters today are under the old codes (IPC, CrPC) and how many under BNS and BNSS?",
    "Which language do you argue in, and which do you draft in?",
])
part("B. The last hearing (the heart of the interview)", 10, [
    "Think of the last matter where you had a hearing. Walk me through the evening before and the morning of.",
    "Which papers did you open? In what order? Where did you look up the law?",
    "How did you know the dates, and how many days the client had been in custody?",
    "What took the longest? What did you wish someone had done for you?",
    "Tell me about a time something nearly went wrong, or did go wrong, in preparing for a hearing.",
], probes=["What happened next?", "How long did that take?", "Who helped you?", "Show me how you did it (on the phone or the file)."],
    note="Spend the most time here. If the lawyer says 'I just manage', ask for a specific matter and walk it step by step.")
part("C. Dates and counting", 4, [
    "How do you keep track of next dates: diary, phone, Excel, clerk, court app?",
    "When did you last miss a date, or nearly miss one? What happened?",
    "When you need to count days (custody, default bail, limitation), who does the counting? How sure are you? Does anyone check it?",
])
part("D. Drafting", 5, [
    "What did you draft in the last two weeks? Take me through the last bail application, reply or petition you wrote.",
    "What do you start from: an old draft, a template, a junior's draft? What do you re-type every time?",
    "Which part is slowest: the facts, the grounds, the prayer, the formatting? How long did the whole thing take?",
    "What do you do with a junior's draft? What do you check first?",
])
part("E. Looking up the law", 4, [
    "When did you last check a section, a punishment, or whether an offence is bailable? How did you do it?",
    "With the new codes, how do you move between old and new section numbers?",
    "What do you use for cases today, and what annoys you about it?",
    "Has any tool ever given you a wrong or an invented citation? What did you do?",
])
part("F. AI tools and trust", 4, [
    "Have you used ChatGPT, Claude or similar for work? For what, last time? What did you do with the answer?",
    "What would you never use such a tool for?",
    "What would a tool have to show you before you relied on a point of law from it?",
    "What would you need to be told before you uploaded a client's chargesheet to any tool? Who must be able to see it?",
])
part("G. Show and tell: the sample sheet", 6, [
    "Hand over the sample hearing-prep sheet (synthetic matter). Say nothing for one minute while they read it.",
    "Then ask, one at a time and writing down their words: What is this? When would you use it? What is missing? What is wrong? What would you cross out?",
    "Which part do you trust, and which part do you not trust? Why?",
    "If you had this the night before a hearing, who prepares something like it today, and how long does it take them?",
], note="Do not explain the sheet. If they ask what a line means, that is a finding: write it down and answer after the interview.")
part("H. The ask", 3, [
    "Would you let us make one of these for a real matter of yours, with names reduced to initials, and tell us honestly what is wrong with it? (Wait for the answer.)",
    "If yes: agree the date. Explain the redaction rule (section 5). If no: ask what would make it possible.",
    "Who else should I speak to?",
], note="This is the strongest question in the interview. A lawyer who hands over a real matter has told you more than ten compliments.")
part("I. Money (last, never first)", 2, [
    "What do you pay for research tools today, and who pays? Per month, per year?",
    "For something that prepared a matter for you, what would feel fair: a monthly amount, an amount per matter, or per document? What would feel too much?",
], note="Write the numbers. Do not quote a price and do not react to theirs.")

d.add_heading("5. Redaction rule for the real matter (part H)", level=1)
bullets(d, [
    "Replace the client's and the complainant's names with initials. Remove addresses, phone numbers, Aadhaar, bank and vehicle numbers.",
    "Keep court names, case numbers, dates and sections. We need them.",
    "Send only what you are allowed to send. If in doubt, send a public court order instead.",
    "We will use the papers only to make your sheet, will not train anything on them, and will delete them after the test. Written consent is taken before anything is sent.",
    "**Our side.** Until a lawyer has written the privacy and consent text, no real client paper goes into the live service. Use public orders, or paper redacted as above, and keep it on staging only.",
])

d.add_heading("6. After each interview: five minutes, same day", level=1)
para(d, "Fill one row of the grid below while it is fresh. Use their words in quotation marks.")
table(d, ["Field", "Their answer"], [
    ["Interview no., years, courts, solo or office, languages", ""],
    ["Share of live matters under IPC / CrPC", ""],
    ["Time to prepare the last hearing; the slowest step", ""],
    ["How they track dates; a missed or nearly missed date (story)", ""],
    ["Who counts days; how sure they are", ""],
    ["Last thing drafted; how long; the slowest part", ""],
    ["Tools used today for law and cases; the complaint", ""],
    ["AI use so far; what they would never use it for", ""],
    ["What they need to be told before uploading papers", ""],
    ["Reaction to the sample sheet: trust / do not trust / missing / cross out", ""],
    ["Offered a real matter? (yes / maybe / no) and the date", ""],
    ["Money: what they pay now; what feels fair", ""],
    ["Best quote", ""],
], [7.0, 10.0], size=9)
para(d, "", after=2)

d.add_heading("7. What counts as a real signal", level=1)
table(d, ["Strong (it is true for them)", "Weak (politeness)"], [
    ["Tells a specific story with a date, a matter or a mistake", "'This is very useful' with no story"],
    ["Names a step that costs them hours every week", "'AI will change law'"],
    ["Hands over a real (redacted) matter and a date", "'Send me the link'"],
    ["Asks 'when can I have this?' or 'can you do it for my other matter?'", "Asks about features we do not have"],
    ["Corrects the sheet: 'this date is wrong' or 'we never count it that way'", "Agrees with everything on the sheet"],
    ["Says what they would pay and who pays", "'It should be free'"],
], [8.5, 8.5], size=9.5)
para(d, "", after=2)

d.add_heading("8. Decisions we make from the ten, written down before the first interview", level=1)
para(d, "The thresholds are my starting suggestions [Guessing]. Change them now if you wish; do not change them after the first interview.", italic=True, color=GREY, size=9.5)
table(d, ["If, out of ten lawyers ...", "Then we ..."], [
    ["6 or more describe hearing preparation as slow and name a specific slow step", "Treat hearing preparation as the product. Build the sheet, then the matter around it."],
    ["5 or more track dates by hand, and 3 or more tell of a missed or nearly missed date", "Build day counts and reminders next, with a rule table a lawyer has checked."],
    ["5 or more draft a bail application or reply every week and call it the slowest part", "Ask for approval to start drafting (it is not approved). Fewer than 3: leave drafting alone for now."],
    ["5 or more say most live matters are under IPC and CrPC", "Load the IPC and CrPC first, before anything else."],
    ["5 or more would not upload client papers until told something specific", "Write the privacy and consent text with a lawyer before any real matter goes in."],
    ["4 or more say they would use the sheet, and 3 or more offer a real matter", "Run the two-week manual test (see LAWYER_VALIDATION_PLAN.md)."],
    ["Fewer than 3 show any of the signals above", "Stop building features. Rethink who the user is."],
], [8.5, 8.5], size=9.5)
para(d, "", after=2)

d.add_page_break()
d.add_heading("Pocket card: the twelve questions", level=1)
numbered(d, [
    "Tell me about the last matter where you had a hearing: the evening before, the morning of.",
    "Which papers did you open, in what order, and where did you look up the law?",
    "How did you know the dates and the days in custody?",
    "What took the longest? What do you wish someone had done?",
    "When did something nearly go wrong in preparing for a hearing?",
    "How do you track next dates? When did you last miss one?",
    "Who counts the days, and who checks the count?",
    "What did you draft in the last two weeks, and what do you re-type every time?",
    "When did you last check a section or a punishment, and how? How do you move between old and new section numbers?",
    "Has a tool ever given you a wrong or an invented case?",
    "What would you need to be told before uploading a client paper to any tool?",
    "(After the sample sheet) What is missing, what is wrong, what would you cross out, and would you let us make one for a real matter?",
], size=10.5, after=3)

d.save("LAWYER_INTERVIEW_SCRIPT.docx")
print("saved")
