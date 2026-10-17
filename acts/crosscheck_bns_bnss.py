"""
crosscheck_bns_bnss.py -- reads Recourse's own copy of the BNS and the BNSS (chunks/bharatiya_*_chunks.json, made from the Gazette) against India Code's two versions of the same Acts: its
database (section records) and its PDF. Written 2026-10-17 to answer "were the BNS/BNSS texts checked the way the five new Acts were, and could they hold garbled text?" (FOLLOW_UPS 2ah).
READ-ONLY: nothing in Recourse is changed; the output is a report and a table.

Three readings are made, each word by word, in order, both ways (the same comparison as check 4 of Recourse's build_act_chunks.py):
  rc_vs_db   Recourse's chunk against India Code's database record
  rc_vs_pdf  Recourse's chunk against India Code's PDF (located by India Code's section headings)
  db_vs_pdf  India Code's database against India Code's PDF (how much India Code agrees with itself)
A difference is put in a class: a label or an Act number India Code adds ("Illustrations", "(10 of 1897)"), the heading of the NEXT chapter stuck to the end of a Recourse chunk, a lost apostrophe, or
OTHER. Every OTHER was read by hand against the three texts (VERDICTS); one not listed there prints as NOT REVIEWED. The Gazette itself is not available here, so where Recourse and India Code
disagree, a human reading decides which is right; the verdicts say what was decided and why.

What it cannot show: an error that Recourse's text shares with India Code; whether either is the law today. A BNS/BNSS section that India Code also lost shows as "same", not as a defect.

Usage (needs indiacode.gov.in and PyMuPDF):  python acts/crosscheck_bns_bnss.py --recourse <Recourse checkout> [--workdir DIR] [--out acts/crosscheck_bns_bnss_report.json]
"""
import argparse
import collections
import difflib
import json
import os
import re
import sys

ACTS = {"bns": {"act_id": "AC_CEN_5_23_00048_2023-45_1719292564123", "uuid": "4bb3e636-ed67-4731-8fb1-7ebfd83e1584", "name": "The Bharatiya Nyaya Sanhita, 2023", "code": "BNS", "chunks": "bharatiya_nyaya_sanhita_2023_chunks.json"},
        "bnss": {"act_id": "AC_CEN_5_23_00049_202346_1719552320687", "uuid": "72592ac7-d084-4545-95d3-0c98dc49fac3", "name": "The Bharatiya Nagarik Suraksha Sanhita, 2023", "code": "BNSS", "chunks": "bharatiya_nagarik_suraksha_sanhita_2023_chunks.json"}}

# What each OTHER difference was found to be (read against all three texts, 2026-10-17).  (act, section): (who is wrong, what)
VERDICTS = {
    ("bnss", "183"): ("RECOURSE", "lost the last line of the confession certificate, '(Signed) A. B. Magistrate.'"),
    ("bnss", "401"): ("RECOURSE", "lost the last sub-section (10) ('Nothing in this section shall affect the provisions of the Probation of Offenders Act, 1958 ...'); the section ends at (9)"),
    ("bnss", "480"): ("RECOURSE", "'on the execution by him of a bond' reads 'o the execution' (a letter lost in the extraction; the key bail section)"),
    ("bnss", "359"): ("RECOURSE", "the compounding table is flattened cell by cell and wrapped cells run together; India Code's version of the table is also messy"),
    ("bnss", "531"): ("RECOURSE", "the chunk holds the section (1,841 characters) plus both Schedules and the printer's footer (98,051 in all); too long to embed, so section 531 is not searchable"),
    ("bnss", "33"): ("INDIA CODE (database and PDF)", "both lack 'shall, in the absence of any reasonable excuse, the burden of proving which excuse shall lie' in section 33(2)"),
    ("bnss", "53"): ("INDIA CODE (database and PDF)", "both end sub-section (3) with a stray fragment, 'not available, by a registered medical practitioner soon after the arrest is made:'"),
    ("bnss", "58"): ("INDIA CODE (database only)", "the database record titled 'Person arrested not to be detained more than twenty-four hours' carries the body of the next section; its PDF and Recourse agree"),
    ("bnss", "215"): ("INDIA CODE (database and PDF)", "both lack sub-sections (2) and (3) of section 215 (withdrawal of a complaint; the meaning of 'Court')"),
    ("bnss", "219"): ("INDIA CODE (database and PDF)", "both lack sub-section (7)"),
    ("bnss", "12"): ("INDIA CODE (PDF text layer)", "'udicial' for 'judicial'"),
    ("bnss", "189"): ("INDIA CODE (PDF text layer)", "'round' for 'ground'"),
    ("bnss", "145"): ("neither", "'wilfully' / 'willfully': a spelling variant"),
    ("bns", "72"): ("INDIA CODE (database only)", "the database lacks clauses (b) and (c) of section 72(2); its PDF and Recourse agree"),
    ("bns", "130"): ("INDIA CODE (PDF text layer)", "the PDF's text lacks the 'Z.' at the end of an illustration; the database and Recourse have it"),
    ("bns", "59"): ("INDIA CODE (database only)", "a stray '33' and 'coommitted' in the database"),
    ("bns", "358"): ("RECOURSE (harmless)", "the Gazette's signature block and printer's line are on the end of the last section"),
    ("bnss", "2"): ("INDIA CODE (database only)", "the database splices the end of the explanation to clause (h) into the start of clause (i) ('officermeans of an electronic device ...'); its PDF and Recourse agree"),
    ("bnss", "35"): ("INDIA CODE (database only)", "'pn erson' for 'person'"),
    ("bnss", "253"): ("INDIA CODE (database only)", "a stray page number ('97') inside the sentence"),
    ("bnss", "276"): ("INDIA CODE (database only)", "a stray page number ('102') inside the sentence"),
    ("bnss", "300"): ("neither", "the next chapter's heading is on the end of Recourse's chunk; India Code adds '(2 of 2016)'"),
    ("bns", "49"): ("INDIA CODE (database only)", "'llustrations' for 'Illustrations' (a lost capital I)"),
    ("bns", "51"): ("INDIA CODE (database only)", "'llustrations' for 'Illustrations' (a lost capital I)"),
    ("bns", "113"): ("neither", "India Code adds the Act number '(37 of 1967)'; a sub-heading follows the section in the PDF"),
    ("bns", "356"): ("neither", "'Illustration' labels (India Code) and the next sub-heading on the end of the chunk"),
}
LABELS = re.compile(r"(illustrations?|llustrations|exceptions?|explanations?)")
ACTNO = re.compile(r"(\d+ of \d{4}|\d{4} \d+ of)( \d+ of \d{4})*")
HEADING_DEBRIS = re.compile(r"(chapter [ivxl]+\b|of |[a-e] [a-z]|part [ivx]+)")


def classify(d):
    """d: {'tag', 'loaded' (what the first text has), 'pdf' (what the second has)} -> class"""
    a, b, tag = d["loaded"], d["pdf"], d["tag"]
    if tag == "insert" and LABELS.fullmatch(b):
        return "label"
    if tag == "insert" and ACTNO.fullmatch(b):
        return "act_number"
    if tag == "delete" and HEADING_DEBRIS.match(a):
        return "next_heading_on_chunk"
    if tag == "replace" and re.sub(r"[^a-z]", "", a) == re.sub(r"[^a-z]", "", b):
        return "apostrophe_or_spacing"
    return "OTHER"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--recourse", required=True)
    ap.add_argument("--workdir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "__crosscheck_cache"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "crosscheck_bns_bnss_report.json"))
    args = ap.parse_args(argv)
    sys.path.insert(0, os.path.abspath(args.recourse))
    import build_act_chunks as B
    os.makedirs(args.workdir, exist_ok=True)
    fetcher = None
    report = {"written": "2026-10-17", "acts": {}}
    for key, a in ACTS.items():
        # --- India Code: the database's sections, and the PDF
        dbp, pdfp = os.path.join(args.workdir, f"{key}_db.json"), os.path.join(args.workdir, f"{key}.pdf")
        if not (os.path.exists(dbp) and os.path.exists(pdfp)):
            fetcher = fetcher or B.Fetcher()
            recs = B.section_records(fetcher.act_records(a["act_id"]), a["act_id"])
            chunks = B.build_sections(recs, {"key": key, "code": a["code"], "name": a["name"], "citation": "", "sections_url": ""}, "crosscheck")
            name, data, pages = B.pick_english_pdf(fetcher.original_pdfs(a["uuid"]), a["name"])
            json.dump(chunks, open(dbp, "w", encoding="utf-8"), ensure_ascii=False)
            open(pdfp, "wb").write(data)
        db = json.load(open(dbp, encoding="utf-8"))
        pdf_text = B.body_text(B.pdf_body_lines(open(pdfp, "rb").read()))
        rc_raw = json.load(open(os.path.join(args.recourse, "chunks", a["chunks"]), encoding="utf-8"))
        rc = {c["section_number"]: c for c in rc_raw}
        # --- the three readings
        rc_body = {n: re.sub(r"^\s*\d+[A-Z]?\.\s*", "", c["text"], count=1) for n, c in rc.items()}
        db_body = {}
        dbm = []
        for c in db:
            c2 = dict(c)
            B.strip_repeated_heading(c2)
            B.set_aside_state_amendments(c2)
            dbm.append(c2)
            db_body[c["section_number"]] = c2["text"].partition("\n")[2]
        rc_as_chunks = [{"section_number": c["section_number"], "title": c["title"], "text": f"{c['section_number']}. {c['title']}\n{rc_body[c['section_number']]}", "footnotes": "", "omitted": False} for c in db]
        readings = {}
        # rc_vs_db: no PDF anchors needed
        diffs = []
        words = equal = 0
        per = {}
        for c in db:
            n = c["section_number"]
            x, y = B.cmp_tokens(rc_body[n]), B.cmp_tokens(db_body[n])
            words += len(x)
            per[n] = [len(x), 0]
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, x, y, autojunk=False).get_opcodes():
                if tag == "equal" or (tag == "replace" and "".join(x[i1:i2]) == "".join(y[j1:j2])):
                    equal += i2 - i1
                    per[n][1] += i2 - i1
                    continue
                diffs.append({"section": n, "tag": tag, "loaded": " ".join(x[i1:i2]), "pdf": " ".join(y[j1:j2])})
        readings["rc_vs_db"] = {"words": words, "identical": equal, "diffs": diffs, "per_section": per}
        for name, chunks in (("rc_vs_pdf", rc_as_chunks), ("db_vs_pdf", dbm)):
            r = B.ordered_compare(chunks, pdf_text)
            readings[name] = {"words": r["words"], "diffs": r["diffs"], "bare_numbers_ignored": r["digits_ignored"]}
        out = {"sections": len(db), "recourse_chunks": len(rc_raw), "readings": {}}
        for name, r in readings.items():
            rest = [d for d in r["diffs"] if not (key == "bnss" and d["section"] == "531" and name != "rc_vs_db") or True]
            cls = collections.Counter(classify(d) for d in rest)
            others = collections.defaultdict(list)
            for d in rest:
                if classify(d) == "OTHER":
                    others[d["section"]].append({"tag": d["tag"], "first": d["loaded"][:80], "second": d["pdf"][:80]})
            out["readings"][name] = {"words": r["words"], "identical_words": r.get("identical"), "differences": len(rest), "classes": dict(cls),
                                     "OTHER_by_section": {s: len(v) for s, v in sorted(others.items(), key=lambda kv: (-len(kv[1]), kv[0]))}}
            if name == "rc_vs_db":
                big = {c["section_number"] for c in rc_raw if len(c["text"]) > 40000}          # a chunk that holds the Schedules and the printer's footer is not a fair test of the section
                w = sum(v[0] for n, v in r["per_section"].items() if n not in big)
                e = sum(v[1] for n, v in r["per_section"].items() if n not in big)
                out["readings"][name]["words_without_oversize_chunks"], out["readings"][name]["identical_without_oversize_chunks"] = w, e
                out["readings"][name]["sections_with_a_difference"] = len({d["section"] for d in rest})
        out["not_reviewed"] = sorted({d["section"] for name in ("rc_vs_db", "rc_vs_pdf", "db_vs_pdf") for d in readings[name]["diffs"] if classify(d) == "OTHER"
                                      and (key, d["section"]) not in VERDICTS and not (d["tag"] == "insert" and re.fullmatch(r"[a-e] [a-z ]+|\d+ [a-e] [a-z ]+|of [a-z ]+|\d+ of \d{4}( \d+)?", d["pdf"]))})
        out["verdicts"] = {s: {"who": v[0], "what": v[1]} for (k, s), v in VERDICTS.items() if k == key}
        # --- the embedded file: which chunks never made it, and the garbled cover pages
        out["preamble_chunk_has_hindi_in_a_broken_font"] = bool(re.search(r"[ऀ-ॿ]", rc_raw[0]["text"]))
        out["chunks_over_40000_chars"] = [c["section_number"] for c in rc_raw if len(c["text"]) > 40000]
        report["acts"][key] = out
    json.dump(report, open(args.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for key, o in report["acts"].items():
        print(f"== {key.upper()}: {o['sections']} sections on India Code, {o['recourse_chunks']} Recourse chunks (one is the Gazette cover page)")
        for name, r in o["readings"].items():
            print(f"   {name:10s} {r['words']:7d} words, {r['differences']:4d} differences  {r['classes']}")
        print("   verdicts:", {s: v['who'] for s, v in o['verdicts'].items()})
        print("   OTHER differences in sections not listed in VERDICTS (NOT REVIEWED):", o["not_reviewed"])
        print("   cover-page chunk with Hindi in a broken font:", o["preamble_chunk_has_hindi_in_a_broken_font"], "| chunks too long to embed:", o["chunks_over_40000_chars"])
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
