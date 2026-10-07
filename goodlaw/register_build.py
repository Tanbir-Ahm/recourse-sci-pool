"""Build the Overruled Register from the two outside lists.

List 1: `inbox/520254941-List-of-Overruled-Cases.pdf`, 1,688 pairs (overruled | overruled by), ends about 2015. Recorded as verified by the owner's lawyer (Mr. Advocate), date recorded 2026-10-07,
        on the owner's statement; Claude did not see the verification. Only facts are kept: names, citations, years, the court class and the list's row number.
List 2: the post-2015 list (59 entries), checked by Claude against the judgments in the collection (`external_lists/2026-10-07_overruled_after_2015_pdf/results.csv`), plus the sibling decisions
        found in the same judgments (`data/register/list2_enrich.json`). Trust: candidate (or unchecked); never verified.

    python sci_goodlaw.py register-build --pdf inbox/520254941-List-of-Overruled-Cases.pdf

The build is repeatable: the same inputs give the same file except the build date.
"""
import csv
import json
import os
import re
import warnings

from . import cites as C
from . import register as R

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "register")
ROOT = os.path.dirname(HERE)
LIST1_PDF = os.path.join(ROOT, "inbox", "520254941-List-of-Overruled-Cases.pdf")
LIST2_RESULTS = os.path.join(ROOT, "external_lists", "2026-10-07_overruled_after_2015_pdf", "results.csv")
LIST2_ENRICH = os.path.join(DATA, "list2_enrich.json")

VERIFIER = "Mr. Advocate"
VERIFIED_ON = "2026-10-07"
VERIFICATION_NOTE = ("Recorded from the owner's statement of 2026-10-07 that a lawyer, Mr. Advocate, verified list 1 as fully correct and that the verification date is that day. "
                     "Claude did not see the verification. List 1 ends about 2015: correct as of then, not complete.")

# ----- reading the PDF ----------------------------------------------------------------------------------------------------------------------------------------------------------


def parse_pdf(pdf):
    """The list's rows as [{'no','page','left','right'}] (left = overruled decision, right = overruling decision). Needs pymupdf; reads the file as data only."""
    warnings.filterwarnings("ignore")
    import pymupdf
    doc = pymupdf.open(pdf)
    entries = []
    for pn in range(len(doc)):
        blocks = []
        for b in doc[pn].get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            L, Rr = [], []
            for ln in b["lines"]:
                txt = "".join(sp["text"] for sp in ln["spans"])
                if txt.strip():
                    (L if ln["bbox"][0] < 312 else Rr).append((ln["bbox"], txt))
            for lines in (L, Rr):
                if lines:
                    blocks.append((min(x[0][0] for x in lines), min(x[0][1] for x in lines), "\n".join(t for _, t in lines) + "\n"))
        left = sorted([b for b in blocks if b[0] < 312], key=lambda b: b[1])
        right = sorted([b for b in blocks if b[0] >= 312], key=lambda b: b[1])
        newents = []
        prev_last = entries[-1] if entries else None
        for x0, y0, txt in left:
            m = re.match(r"\s*(\d{1,4})\.\s*(.*)", txt, re.S)
            if m:
                e = {"no": int(m.group(1)), "left": m.group(2), "right": "", "page": pn + 1, "y": y0}
                entries.append(e)
                newents.append(e)
            elif entries:
                entries[-1]["left"] += " " + txt
        for x0, y0, txt in right:
            near = [e for e in newents if abs(e["y"] - y0) < 16]
            if near:
                near[0]["right"] += (" " if near[0]["right"] else "") + txt
            elif prev_last is not None:
                prev_last["right"] += " " + txt
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    return [{"no": e["no"], "page": e["page"], "left": norm(e["left"]), "right": norm(e["right"])} for e in entries]


# ----- one cell -> name, citations, court, years -----------------------------------------------------------------------------------------------------------------------

_CITE_START = re.compile(r",\s+(?=(?:AIR\s*\(?\s*(?:18|19|20)\d\d|\(\s*(?:18|19|20)\d\d\s*\)|\[\s*(?:18|19|20)\d\d\s*\]|(?:18|19|20)\d\d\s*[\(\[A-Z]|JT\b|SCC\b|ILR\b))")
_AIR_RE = re.compile(r"AIR\s*(\d{4})\s+([A-Za-z&]+?)(?:\(\d\))?\s+\d")
_HC_CODE = {"all": "Allahabad", "ap": "Andhra Pradesh", "ker": "Kerala", "cal": "Calcutta", "bom": "Bombay", "mad": "Madras", "del": "Delhi", "pat": "Patna", "punj": "Punjab", "p&h": "Punjab & Haryana",
            "raj": "Rajasthan", "mp": "Madhya Pradesh", "guj": "Gujarat", "kar": "Karnataka", "ori": "Orissa", "orissa": "Orissa", "hp": "Himachal Pradesh", "j&k": "Jammu & Kashmir", "gau": "Gauhati",
            "utt": "Uttarakhand", "chh": "Chhattisgarh", "jha": "Jharkhand", "pun": "Punjab", "pc": "Privy Council", "fc": "Federal Court", "mys": "Mysore", "nag": "Nagpur", "lah": "Lahore"}
_SC_MARK = re.compile(r"AIR\s*\d{4}\s*SC\b|\bSCC\b|\bSCR\b|\bSCALE\b|\bJT\b|\bAIRSCW\b|\bSupreme\b|\bSCJ\b")


def split_cell(cell):
    """(name, citation string) from 'Party Vs. Party, AIR 1965 SC 177 : (1964) 6 SCR 666'."""
    cell = cell or ""
    m = _CITE_START.search(cell)
    if not m:
        return cell.strip(), ""
    return cell[:m.start()].strip(), cell[m.end():].strip()


def court_class(cites):
    """('SC' | 'HC' | 'unknown', detail)"""
    m = _AIR_RE.search(cites)
    if m:
        code = m.group(2)
        if code.upper() == "SC":
            return "SC", "Supreme Court"
        return "HC", _HC_CODE.get(code.lower(), f"High Court/other ({code})")
    if _SC_MARK.search(cites) and "AIR" not in cites:
        return "SC", "Supreme Court"
    return "unknown", None


_YEAR_FORMS = [re.compile(r"\(\s*((?:18|19|20)\d\d)\s*\)"), re.compile(r"\[\s*((?:18|19|20)\d\d)\s*\]"), re.compile(r"\bAIR\s*\(?\s*((?:18|19|20)\d\d)"),
               re.compile(r"\b((?:18|19|20)\d\d)\s*(?:\(\s*\d+\s*\)\s*)?(?:SCC|SCR|AIR|JT|SCALE|Supp)\b")]


def cite_years(cites):
    """Years printed as reporter years in a citation string. A bare four-digit number is not read as a year (page numbers such as 'CriLJ 1947')."""
    ys = {int(k.split(":")[1]) for k, _, _ in R.all_cite_keys(cites)}
    for rx in _YEAR_FORMS:
        ys |= {int(y) for y in rx.findall(cites)}
    return sorted(y for y in ys if 1850 <= y <= 2026)


def display_name(name):
    """'A Vs. B' -> 'A v. B'; a trailing ', etc.' dropped."""
    name = re.sub(r"\s+Vs\.?\s+", " v. ", name or "", flags=re.I)
    return re.sub(r",?\s*etc\.?\s*$", "", name).strip()


def decision_record(cell):
    name, cites = split_cell(cell)
    name = display_name(name)
    court, detail = court_class(cites)
    ys = cite_years(cites)
    air = [int(y) for y in re.findall(r"AIR\s*\(?\s*((?:18|19|20)\d\d)", cites)]
    year = air[0] if air else (ys[0] if ys else None)
    return {"name": name, "court": court, "court_detail": detail, "cites": [c.strip() for c in re.split(r"\s+:\s+", cites) if c.strip()], "keys": R.key_set(cites),
            "year": year, "years": ys}


_STOPW = set("vs the and others another of in re state union india uoi ors anr co ltd limited private pvt p u.p. etc by through its".split())


def _toks(name):
    name = re.sub(r"[^A-Za-z ]", " ", name.lower())
    return {t for t in name.split() if t not in _STOPW and len(t) > 2}


def same_matter(a_name, b_name):
    a, b = _toks(a_name), _toks(b_name)
    return bool(a and b) and len(a & b) / len(a | b) >= 0.5


# ----- list 1 -------------------------------------------------------------------------------------------------------------------------------------------------------------------

MUTUAL_PAIRS = ((247, 506), (265, 242), (270, 258), (446, 645), (463, 535), (594, 474))      # each case listed as overruled by the other (README of the list-1 analysis)


def build_list1(rows, built_on):
    out, no_cite = [], 0
    mutual = {n for p in MUTUAL_PAIRS for n in p}
    for r in rows:
        a, b = decision_record(r["left"]), decision_record(r["right"])
        flags = []
        if r["no"] in mutual:
            flags.append("list_mutual_pair")
        if not b["name"]:
            flags.append("list_no_overruling_decision")
        if a["years"] and b["years"] and max(b["years"]) < min(a["years"]):
            flags.append("year_order_check")
        if not a["keys"] and not a["year"]:
            flags.append("no_citation_or_year_for_overruled")
        same = same_matter(a["name"], b["name"]) if a["court"] != "SC" else False
        if "list_mutual_pair" in flags or "list_no_overruling_decision" in flags:
            treatment = "disputed_listing"
        elif a["court"] != "SC" and same:
            treatment = "reversed_on_appeal"
        else:
            treatment = "overruled"
        row = {"id": f"L1-{r['no']:04d}", "source": "list1", "trust": "verified",
               "overruled": a, "overruling": {**b, "date": None, "bench": None},
               "treatment": treatment, "scope": None, "court_words": None, "same_parties": same, "flags": flags,
               "evidence": {"kind": "outside_list", "ref": f"inbox/520254941-List-of-Overruled-Cases.pdf, row {r['no']} (page {r['page']})"},
               "verification": {"by": VERIFIER, "on": VERIFIED_ON, "basis": "owner's statement; see register meta"},
               "history": [{"on": built_on, "by": "register-build", "event": "created from list 1", "note": f"verification recorded: {VERIFIER}, {VERIFIED_ON}"}]}
        out.append(row)
    return out


# ----- list 2 -------------------------------------------------------------------------------------------------------------------------------------------------------------------

_VERDICT_TREATMENT = {1: "overruled_in_part", 2: "overruled_in_part"}


def build_list2(results_csv, enrich, built_on):
    """Rows for the post-2015 list: one per entry (trust candidate; 'unchecked' where the later judgment is not in our text), plus the sibling decisions named in `enrich['siblings']`."""
    rows_by_no = {int(r["no"]): r for r in csv.DictReader(open(results_csv, encoding="utf-8"))}
    out = []
    for no in sorted(rows_by_no):
        r = rows_by_no[no]
        e = enrich["entries"].get(str(no))
        if e is None:
            raise ValueError(f"list 2 entry {no} has no enrichment record")
        trust = "unchecked" if r["verdict"] == "U" else "candidate"
        out.append(_list2_row(f"L2-{no:03d}", "list2", trust, e, r, built_on))
    for sid, s in enrich["siblings"].items():
        out.append(_list2_row(sid, "list2_sibling", "candidate", s, None, built_on))
    return out


def _list2_row(rid, source, trust, e, r, built_on):
    court = e.get("a_court", "SC")
    a = {"name": e["a_name"], "alt_names": list(e.get("a_alt_names", [])), "court": court, "court_detail": "Supreme Court" if court == "SC" else "High Court",
         "cites": e.get("a_cites", []), "keys": R.key_set(" : ".join(e.get("a_cites", []))), "year": e["a_year"], "years": sorted(set(e.get("a_years", [e["a_year"]])))}
    b = {"name": e["b_name"], "court": "SC", "court_detail": "Supreme Court", "cites": e.get("b_cites", []), "keys": R.key_set(" : ".join(e.get("b_cites", []))),
         "year": e["b_year"], "years": sorted(set(e.get("b_years", [e["b_year"]]))), "date": e.get("b_date"), "bench": e.get("b_bench"), "doc_key": e.get("b_doc_key")}
    ev = {"kind": "judgment_text" if e.get("evidence_basis", "B") in ("B", "H+B") else "law_report_headnote", "basis": e.get("evidence_basis", "B"),
          "ref": e.get("evidence_ref", ""), "checked_by": "Claude (reading the judgment in the collection), 2026-10-07; not a lawyer"}
    if r is not None:
        ev["list_verdict"] = r["verdict"]
    words = e.get("court_words") or (r["court_words"] if r is not None else None)
    note = e.get("note") or (r["note"] if r is not None else "")
    row = {"id": rid, "source": source, "trust": trust, "overruled": a, "overruling": b, "treatment": e["treatment"], "scope": e.get("scope"), "court_words": words,
           "same_parties": False, "flags": list(e.get("flags", [])), "evidence": ev, "verification": None, "note": note,
           "history": [{"on": built_on, "by": "register-build", "event": f"created from {'list 2' if source == 'list2' else 'sibling decision found in the same judgment'}"}]}
    if e.get("split"):
        row["split"] = e["split"]
    return row


# ----- all ------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def build(pdf=LIST1_PDF, out_path=None, built_on=None, list1_rows=None, log=print):
    built_on = built_on or R.today_str()
    rows1 = list1_rows if list1_rows is not None else parse_pdf(pdf)
    if len(rows1) != 1688:
        log(f"warning: list 1 has {len(rows1)} rows, expected 1688")
    enrich = json.load(open(LIST2_ENRICH, encoding="utf-8"))
    rows = build_list1(rows1, built_on) + build_list2(LIST2_RESULTS, enrich, built_on)
    reg = R.Register(rows)
    for row in rows:
        row["match_by"] = reg.match_class(row)
        if row["match_by"] in ("weak", "none") and row["trust"] != "unchecked":
            row.setdefault("flags", []).append("needs_citation_or_year")
    meta = {"built_on": built_on,
            "sources": {"list1": {"file": "inbox/520254941-List-of-Overruled-Cases.pdf", "entries": len(rows1), "ends_about": 2015, "trust": "verified",
                                  "verified_by": VERIFIER, "verified_on": VERIFIED_ON, "note": VERIFICATION_NOTE,
                                  "licence": "Not cleared. The same list is published on www.referencer.in, which reserves its copyright. Only facts (names, citations, years, row numbers) are kept here. The owner asked for the "
                                             "register on 2026-10-07; whether a facts-only register may be used in a product is a question for the lawyer."},
                        "list2": {"file": "external_lists/2026-10-07_overruled_after_2015_pdf/results.csv", "entries": 59, "trust": "candidate",
                                  "note": "Checked by Claude against the judgments in the collection on 2026-10-07; not verified by a lawyer. Reviewer assigned: Mr. Advocate, review pending."},
                        "list2_sibling": {"trust": "candidate", "note": "Decisions the same judgments overruled that list 2 omits; read in the judgment text or its headnote by Claude."}},
            "review": {"reviewer": VERIFIER, "reviewer_note": "The owner named Mr. Advocate as the lawyer reviewer; the owner did not say who reviews flags, so Mr. Advocate is assumed.", "interval_days": 7}}
    path = R.save(rows, meta, out_path)
    log(f"register: {len(rows)} rows -> {path}")
    return rows, meta
