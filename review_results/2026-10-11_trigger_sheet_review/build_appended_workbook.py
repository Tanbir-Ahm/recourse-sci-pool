#!/usr/bin/env python3
"""Appends three sheets to a COPY of the owner's trigger workbook (the five original sheets are not touched): 'Claude Review', 'Index Reality Check', 'Machine Spec (draft)'.
Numbers come from trigger_audit.py / machine_spec_test.py (this folder). PRIVATE."""
import json
import os

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "review_data", "ruler", "inputs", "2026-10-11_owner_trigger_workbook.xlsx")
OUT = os.path.join(ROOT, "review_data", "ruler", "inputs", "2026-10-11_trigger_workbook_with_claude_appends.xlsx")
audit = json.load(open(os.path.join(HERE, "trigger_audit.json")))["marker_audit"]

wb = openpyxl.load_workbook(SRC)
before = [(ws.title, ws.dimensions) for ws in wb.worksheets]
HDR = PatternFill("solid", fgColor="DDE6F0")


def sheet(title, intro, header, rows, widths):
    ws = wb.create_sheet(title)
    ws.append([intro])
    ws["A1"].font = Font(bold=True)
    ws.append([])
    ws.append(header)
    for c in ws[3]:
        c.font = Font(bold=True)
        c.fill = HDR
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for r in rows:
        ws.append(r)
    for row in ws.iter_rows(min_row=4):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    for i, w in enumerate(widths):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i + 1)].width = w
    ws.freeze_panes = "A4"
    return ws


# ---------------------------------------------------------------- Claude Review
review = [
    ["Revised Trigger Map", "KEEP the design: separate question-side triggers from passage-side markers; strong and secondary tiers; a false-positive note per Act; statute and case links; multi-label allowed.",
     "(1) The trigger phrases are descriptions, not keywords. A real question ('My husband threw me out of the house ... too late to file a domestic violence case?') shares almost no exact phrase with 'domestic violence complaint under the DV Act' or 'thrown out of the marital home'. A matcher needs literal anchors (see 'Machine Spec (draft)'). (2) 'Secondary marker with context nearby' and 'DV Act (when the document context confirms India)' cannot be run: no distance or rule is given. We use Tier 1 only. (3) Bare 'domestic violence' is not a trigger in the original; it should be. (4) Three rows (BNS/IPC, BNSS/CrPC, BSA/IEA) are general codes: their strong markers sit in 13.9%, 11.8% and 2.7% of all passages and in 73%, 58% and 18% of all judgments, so they cannot discriminate (see 'Index Reality Check'). (5) Six rows (ITPA, PCMA, PCR Act, CGST, Muslim Women Act, PDPP) have under 100 marked passages in our Supreme Court criminal-law index.",
     "Use rows 1-9 and 13-15 of the map (13 Acts) for the test; treat the three codes as issue-level only; park the six thin rows; park Companies Act."],
    ["False-Positive Audit", "Largely right, and it corrects real defects in my first draft table (Appendix A of the draft test): 'cheque' alone, 'prevention of money' (truncated), 'contraband', 'protection of women', 'atrocities' and 'scheduled caste' alone, 'juvenile' alone, 'dowry' alone as a PASSAGE marker, 'Enforcement Directorate' alone, bare section numbers. I accept every one of those corrections.",
     "It states risks as High/Very high without measuring them. We measured the code families. It does not say how a 'Medium-High' risk changes a boost. Still unmeasured: precision of the strong markers (they were not read passage by passage).",
     "Adopt as written. Add measurements (sheet 'Index Reality Check')."],
    ["Case Law & Statute Sources", "Good provenance for why each term was chosen; mostly well-known Supreme Court cases whose dates look right to me [Likely].",
     "I did not open any link. A few entries need checking by Mr. Advocate before anyone relies on them: 'Hitesh Verma v. State of Uttarakhand' is given as Uttarakhand High Court, 20 Jul 2020 (the widely cited decision on 'within public view' is the Supreme Court's, later in 2020; the sheet may be citing the High Court order under appeal) [Likely]; 'N. Mahesh v. G.N. Nanjundaswamy' is dated 14 Aug 2026 with the court given only as 'Indian court'; the ITPA row cites a search-results page, not a judgment; the Motor Vehicles row cites the statute page twice; several 2026 items are unverified. None of this changes the words we would use; it matters if the sheet is quoted as authority.",
     "Mr. Advocate to confirm the section numbers named in the Machine Spec; the cases are background only."],
    ["Implementation Notes", "Sound principles: two-stage taxonomy, marker hierarchy, no bare section numbers, multi-label, keep modern and legacy codes, normalise abbreviations, measure trigger false positives and marker precision separately.",
     "No matcher is specified, no weights, and 'tune weights with held-out manually labelled passages' cannot be done: we have none. The evaluation proposal needs one thing we can add cheaply: the question writer tags each new question with the Act(s) it concerns, so trigger precision and recall can be measured BEFORE any search.",
     "Adopt. Add the 'Act tag' column to the new-question workbook."],
    ["Layperson Trigger Additions", "The most useful sheet for real users; right that broad wording should be low-weight; right not to use lay phrases as passage markers.",
     "The phrases are paraphrases a user will rarely repeat ('thrown out of the marital home' versus 'threw me out of the house'). Two ways to use them were tested on the 30 used questions: (a) literal regex anchors written from the high-signal phrases fire on 11 of 30 questions and every firing looked right; (b) semantic routing (embed every phrase, route each question to the closest Act) FAILS: the nearest-Act scores are 0.2 to 0.5 for every question, and a question about anticipatory bail scores 0.54 on SC/ST, higher than the true domestic-violence question (0.46). Broad wording ('arrest', 'fraud', 'evidence', 'theft') fires on most questions and discriminates nothing.",
     "Use the high-signal phrases as literal anchors; do not use the broad wording or semantic routing in this test."],
]
sheet("Claude Review", "CLAUDE'S REVIEW OF THE FIVE SHEETS (2026-10-11). The five original sheets are unchanged. LLM-assisted analysis, not legal advice; Mr. Advocate to confirm the legal content.",
      ["Sheet", "What is good", "What is wrong or missing (with evidence)", "Recommendation"], review, [26, 60, 100, 50])

# ---------------------------------------------------------------- Index Reality Check
SHORT_FULL = {"PWDVA": "Protection of Women from Domestic Violence Act, 2005", "NDPS": "NDPS Act", "POCSO": "POCSO Act", "SC/ST": "SC/ST (Prevention of Atrocities) Act", "NI Act": "Negotiable Instruments Act", "PMLA": "PMLA", "UAPA": "UAPA",
              "DPA": "Dowry Prohibition Act", "JJ Act": "Juvenile Justice Act", "BNS/IPC": "BNS / IPC", "BNSS/CrPC": "BNSS / CrPC", "BSA/IEA": "BSA / Evidence Act", "PC Act": "Prevention of Corruption Act", "Arms Act": "Arms Act",
              "IT Act": "Information Technology Act", "ITPA": "Immoral Traffic (Prevention) Act", "PCMA": "Prohibition of Child Marriage Act", "PCR Act": "Protection of Civil Rights Act", "MV Act": "Motor Vehicles Act", "PDPP": "Prevention of Damage to Public Property Act",
              "Companies Act": "Companies Act", "CGST": "CGST Act", "Muslim Women Act": "Muslim Women (Protection of Rights on Marriage) Act, 2019"}
KEEP = ["PWDVA", "NDPS", "POCSO", "SC/ST", "NI Act", "PMLA", "UAPA", "DPA", "JJ Act", "PC Act", "Arms Act", "IT Act", "MV Act"]
CODES = ["BNS/IPC", "BNSS/CrPC", "BSA/IEA"]
tot_p, tot_j = 238762, 10522
rows = []
for a in SHORT_FULL:
    d = audit[a]
    status = "KEEP (test)" if a in KEEP else ("EXCLUDE: general code, issue-level only" if a in CODES else ("PARK: under 100 marked passages" if d["passages"] < 100 else "PARK: marker is mostly civil or ambiguous in this index [Guessing]"))
    rows.append([SHORT_FULL[a], d["passages"], round(100 * d["passages"] / tot_p, 2), d["judgments"], round(100 * d["judgments"] / tot_j, 2), d["judgments_3plus"], status])
sheet("Index Reality Check", "HOW OFTEN EACH ACT'S STRONG PASSAGE MARKER (title, acronym, Act-linked section) APPEARS IN OUR INDEX: 238,762 passages, 10,522 Supreme Court judgments (index commit 3c80a26 plus three small side indexes). Measured 2026-10-11.",
      ["Act / family", "Passages with a strong marker", "% of all passages", "Judgments with one or more", "% of all judgments", "Judgments with 3 or more marked passages", "Decision for the fix test"], rows, [48, 16, 12, 16, 12, 18, 52])
ws = wb["Index Reality Check"]
n = ws.max_row + 2
for t in ["Label coverage: in judgments with 3 or more passages carrying the marker, a passage-level marker marks on average only 19% to 40% of their passages (PWDVA 30%, NDPS 40%, POCSO 25%, SC/ST 26%, NI Act 36%, PMLA 30%, UAPA 24%, DPA 19%, PC Act 26%, Arms Act 20%); in 3 to 77 judgments per Act it marks under 10%. Operative paragraphs usually say 'the Act' or 'Section 12', not the full title. So a passage-level boost would mostly lift introductory paragraphs. A JUDGMENT-level label (3 or more marked passages) is proposed instead.",
          "The right judgment for the domestic-violence question (R16, Kamatchi) has 4 marked passages of 44 (9%); the two judgments that crowded it out have none, so a PWDVA boost would not lift them."]:
    ws.cell(row=n, column=1, value=t).alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=n, start_column=1, end_row=n, end_column=7)
    ws.row_dimensions[n].height = 70
    n += 1

# ---------------------------------------------------------------- Machine Spec
import re as _re
src = open(os.path.join(HERE, "machine_spec_test.py"), encoding="utf-8").read()
anch_block = src.split("ANCH = {")[1].split("\n}\n")[0]
anchors = {}
for line in anch_block.strip().split("\n"):
    m = _re.match(r'\s*"([^"]+)": \[(.*)\],?\s*$', line)
    if m:
        anchors[m.group(1)] = [x for x in _re.findall(r'r"((?:[^"\\]|\\.)*)"', m.group(2))]
marker_block = src.split("MARK = {")[1].split("}\ntot =")[0]
markers = {}
for m in _re.finditer(r'"([^"]+)": r"((?:[^"\\]|\\.)*)"', marker_block):
    markers[m.group(1)] = m.group(2)
markers["PWDVA"] = markers["PWDVA"] + r"|section\s+(12|18|19|20|22|23)\s+of\s+the\s+(D\.?V\.?|domestic violence)   [the label-coverage percentages were measured on the title and acronym part only]"
markers["JJ Act"] = r"juvenile justice \(care and protection of children\) act|\bJJ Act\b|\bJJB\b|juvenile justice board|child welfare committee"
markers["IT Act"] = r"information technology act|\bIT Act\b"
markers["MV Act"] = r"motor vehicles act|\bMV Act\b"
spec_rows = []
for a in KEEP:
    spec_rows.append([SHORT_FULL[a], " | ".join(anchors.get(a, [])), markers.get(a, "(not measured in the label-coverage check; same rule: full title / acronym / Act-linked section)"), "3 or more passages of the judgment carry the strong marker"])
ws = sheet("Machine Spec (draft)", "DRAFT MACHINE SPEC for the named-Act boost in the fix test (13 Acts). Question anchors are case-insensitive regular expressions unless the pattern is an acronym (ED, OTP, UPI, NCB, MDMA, case-sensitive in code). Draft: Mr. Advocate to review before any freeze; none of it is tuned on any result.",
           ["Act", "Question-side anchors (a question fires the Act if ANY matches; written from the workbook's high-signal phrases)", "Passage-side strong marker (regex; Tier 1 only)", "Judgment label rule"], spec_rows, [40, 90, 70, 36])
n = ws.max_row + 2
for t in ["GLOBAL RULES. (1) Only these 13 Acts. BNS/IPC, BNSS/CrPC and BSA/IEA are issue-level and never boost. The six thin rows and Companies Act are parked. (2) Broad everyday wording and the secondary-marker/context tiers are NOT used in this test (no matcher or evidence yet). (3) A question may fire several Acts; a judgment is labelled if it carries a strong marker of ANY fired Act in 3 or more passages; the boost multiplies the final score of every passage of a labelled judgment once. (4) Bare section numbers are never markers. (5) Section 66A is never surfaced as a valid offence (handled elsewhere). (6) The question writer adds a column 'Act(s) the question concerns (if any)' so trigger precision and recall are measured before any search.",
          "TEST ON THE 30 USED QUESTIONS (a dev check, not evidence): the anchors fire on 11 of 30 (NI Act 3, NDPS 2, POCSO 2, PMLA 1, SC/ST 1, DPA 1, PWDVA 1), none looked wrong to me, and 19 questions fire nothing (general criminal law). Semantic routing and the original long phrases were tried and rejected (see 'Claude Review')."]:
    ws.cell(row=n, column=1, value=t).alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=n, start_column=1, end_row=n, end_column=4)
    ws.row_dimensions[n].height = 120
    n += 1

assert [(w.title, w.dimensions) for w in wb.worksheets[:5]] == before, "original sheets changed"
wb.save(OUT)
print("saved", OUT, "| sheets:", wb.sheetnames, "| anchors parsed for", len(anchors), "Acts, markers for", len(markers))
