"""Tests for goodlaw/statutes.py: reading the sections a case cites and looking up their successors. Run: python test_goodlaw_statutes.py"""
from goodlaw import statutes as S

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


check(S.to_new("IPC", "302") == [{"act": "BNS", "section": "103", "change": True}], "IPC 302 -> BNS 103, marked changed")
check(S.to_new("IPC", "420") == [{"act": "BNS", "section": "318(4)", "change": False}], "IPC 420 -> BNS 318(4)")
check([e["section"] for e in S.to_new("CrPC", "41A")] == ["35(3)", "35(4)", "35(5)", "35(6)"], "CrPC 41A -> BNSS 35(3) to 35(6)")
check(S.to_new("CrPC", "482")[0]["section"] == "528" and S.to_new("CrPC", "438")[0]["section"] == "482", "CrPC 482 -> BNSS 528 and CrPC 438 -> BNSS 482")
check(S.to_new("IPC", "124A") == [], "IPC 124A is in the table with no counterpart")
check(S.to_new("IPC", "99999") is None, "a section not in the table gives None")
check(S.to_new("IPC", "498A")[0]["section"] == "85", "IPC 498A -> BNS 85 (and 86)")

text = ("The complaint was under Section 138 of the Negotiable Instruments Act, 1881. The High Court quashed the proceedings under Section 482 of the Code of Criminal Procedure. "
        "The accused was charged under Sections 420, 468 and 471 read with Section 34 IPC. Section 138 of the Negotiable Instruments Act requires a notice. "
        "Under Section 41A Cr.P.C. a notice of appearance is issued; Article 21 of the Constitution was invoked. Section 138 of the Act applies. S. 302 I.P.C. was also framed.")
c = S.sections_cited(text)
check(c[("NI Act", "138")] == 2, "Section 138 of the Negotiable Instruments Act is counted twice; 'of the Act' alone is not counted")
check(c[("CrPC", "482")] == 1 and c[("CrPC", "41A")] == 1 and c[("IPC", "420")] == 1 and c[("IPC", "468")] == 1 and c[("IPC", "471")] == 1 and c[("IPC", "34")] == 1 and c[("IPC", "302")] == 1,
      "section lists ('Sections 420, 468 and 471 read with Section 34 IPC') and spelled-out or dotted act names are read")
check(c[("Constitution", "21")] == 1, "an Article of the Constitution is read")

rows = S.statute_dimension(text, top=20)
by = {(r["act"], r["section"]): r for r in rows}
check(by[("IPC", "302")]["status"] == "renumbered_changed" and by[("IPC", "420")]["status"] == "renumbered", "the table's change flag becomes renumbered_changed; no flag, renumbered")
check(by[("NI Act", "138")]["status"] == "unaffected" and by[("Constitution", "21")]["status"] == "unaffected", "NI Act and the Constitution are marked unaffected by the recodification")
check(by[("CrPC", "41A")]["successors"][0]["section"] == "35(3)", "successors are listed")
check(rows[0]["count"] == 2 and rows[0]["section"] == "138", "the most-cited provision comes first")
check(S.summarise(rows) == "STATUTE_CHANGED", "any renumbered provision raises the STATUTE_CHANGED flag")
check(S.summarise(S.statute_dimension("Section 138 of the Negotiable Instruments Act applies. Section 139 of the Negotiable Instruments Act raises a presumption.")) is None, "a case on the NI Act alone raises no statute flag")
check(S.statute_dimension("Nothing cited here.") == [] and S.summarise([]) is None, "no sections cited gives nothing")
ev = S.statute_dimension("Section 27 of the Evidence Act and Section 65B of the Evidence Act were relied on.")
check(ev and ev[0]["status"] == "replaced_not_mapped", "the Evidence Act is flagged as replaced by the Bharatiya Sakshya Adhiniyam without inventing a mapping")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
