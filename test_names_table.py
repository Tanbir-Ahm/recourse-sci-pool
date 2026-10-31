"""Tests for names_table/build_names_table.py on a tiny invented index, crawl and bucket list (no network). Run: python test_names_table.py"""
import gzip, json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "names_table"))
import build_names_table as B

F = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond: F.append(name)

# ---- names
check("capitals become title case, initials and acronyms stay", B.display_name("STATE OF U.P.", "RAM NARESH PANDEY") == "State of U.P. v. Ram Naresh Pandey" and B.display_name("UOI", "M/S. ABC LTD.") .startswith("UOI v. M/s."), B.display_name("STATE OF U.P.", "RAM NARESH PANDEY"))
check("a name already in normal case is left alone", B.display_name("Kailashi Bai", "Aarti Arya & Anr.") == "Kailashi Bai v. Aarti Arya & Anr.")
check("(DELHI ADMN.) keeps its capital", B.display_name("STATE (DELHI ADMN.)", "JAGJIT SINGH") == "State (Delhi Admn.) v. Jagjit Singh", B.display_name("STATE (DELHI ADMN.)", "JAGJIT SINGH"))
check("a number glued to the first word and a caption tail are dropped", B.display_name("49RAM SHANKAR", "STATE") == "Ram Shankar v. State" and B.display_name("1505/2008) Phiroz Ibrahim Khan", "Ismail") == "Phiroz Ibrahim Khan v. Ismail")
check("one party missing gives no name", B.display_name("X", None) is None)
check("caption words make a name suspicious; a petition's name does not", B.suspicious("CRIMINAL APPEAL NO. 5 OF 2009", "State") and B.suspicious(None, "x") and not B.suspicious("People's Union for Civil Liberties & Anr.", "Union of India") and not B.suspicious("Writ Petition Mohan", "State"))
check("the court link and the bucket link are built from the id and the key", B.judis_url(250) == "https://api.sci.gov.in/jonew/judis/250.pdf" and B.bucket_url("data/pdf/year=2017/english/2017_3_962_980_EN.pdf").startswith("https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2017/"))
p, r = B.caption_fallback("IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION CRIMINAL APPEAL NO. 833 OF 2011 (Arising out of SLP(Crl.) No.5930/2010) AZEEZ Appellant(s) :VERSUS: STATE OF KERALA Respondent(s) O R D E R Leave granted.")
check("a modern caption with 'Arising out of SLP(Crl.)' is read", (p, r) == ("AZEEZ", "STATE OF KERALA"), (p, r))
p, r = B.caption_fallback("REPORTABLE IN THE SUPREME COURT OF INDIA CRIMINAL APPELLATE JURISDICTION CRIMINAL APPEAL NO.1233 OF 2006 STATE OF RAJASTHAN ... APPELLANT VERSUS JAG RAJ SINGH @ HANSA ... RESPONDNET J U D G M E N T")
check("a typo in the role word does not stop it", (p, r) == ("STATE OF RAJASTHAN", "JAG RAJ SINGH @ HANSA"), (p, r))
check("text with no 'versus' gives nothing", B.caption_fallback("Some order of the court with no caption") == (None, None))

# ---- a tiny index
tmp = tempfile.mkdtemp()
idx, crawl, side = os.path.join(tmp, "idx"), os.path.join(tmp, "crawl"), os.path.join(tmp, "side")
for d in (os.path.join(idx, "index"), os.path.join(crawl, "shards"), side):
    os.makedirs(d)
def gz(path, rows):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
gz(os.path.join(idx, "index", "a.meta.jsonl.gz"), [{"doc": 250, "i": 0, "text": "x"}, {"doc": 251, "i": 0, "text": "x"}, {"doc": 1000000020, "i": 0, "text": "x"}, {"doc": 1000000021, "i": 0, "text": "x"}])
gz(os.path.join(idx, "index", "a.docs.jsonl.gz"), [{"doc": 250, "passages": 1}, {"doc": 251, "passages": 1, "case": {"pet": "THE STATE", "resp": "BEEMA", "date": "01/02/1990"}},
    {"doc": 1000000020, "passages": 1, "src": {"source": "bucket", "path": "1952_1_172_178", "title": "ADAMJI UMAR DALAL versus THE STATE OF BOMBAY", "date": "26-11-1951"}},
    {"doc": 1000000021, "passages": 1, "src": {"source": "bucket", "path": "9999_nowhere", "title": "A versus B", "date": "01-01-2020"}}])
gz(os.path.join(crawl, "shards", "000250.jsonl.gz"), [
    {"id": "250", "status": "ok", "bytes": "36813", "text": "http://JUDIS.NIC.IN SUPREME COURT OF INDIA Page 1 of 17 PETITIONER: KANGSARI HALDAR & ANOTHER Vs. RESPONDENT: THE STATE OF WEST BENGAL DATE OF JUDGMENT: 18/12/1959 BENCH: X CITATION: 1960 AIR 457 1960 SCR (2) 646 ACT: HEADNOTE: JUDGMENT: Held."},
    {"id": "251", "status": "ok", "bytes": "100", "text": "garbled text with no caption at all"}])
work = {"1952_1_172_178": {"path": "1952_1_172_178", "key": "data/pdf/year=1952/english/1952_1_172_178_EN.pdf", "title": "ADAMJI UMAR DALAL versus THE STATE OF BOMBAY", "petitioner": "ADAMJI UMAR DALAL", "respondent": "THE STATE OF BOMBAY",
        "decision_date": "26-11-1951", "citation": "[1952] 1 S.C.R. 172", "case_id": "1951 INSC 54", "cnr": "C1", "size": "1000"}}
gz(os.path.join(idx, "index", "b.meta.jsonl.gz"), [{"doc": d, "i": 0, "text": "x"} for d in (2000000001, 2000000002, 2000000003, 2000000004)])
gz(os.path.join(idx, "index", "b.docs.jsonl.gz"), [
    {"doc": 2000000001, "passages": 1, "src": {"source": "ghc_post2017", "title": "Dinathso Chaitom Vs THE STATE OF AP", "date": "2020-12-17", "citation": "Crl.Petn./52/2020", "case_id": "Crl.Petn./52/2020", "court": "Gauhati High Court",
                                                "neutral_citation": "None", "url": "https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2020/court=18_6/x.pdf"}},
    {"doc": 2000000002, "passages": 1, "src": {"source": "sci_newer", "title": "BALJINDER SINGH @ LADOO AND OTHERS versus STATE OF PUNJAB", "date": "2024-09-25", "citation": "2024 INSC 738", "case_id": "38050/2011",
                                                "court": "Supreme Court of India", "url": "https://api.sci.gov.in/supremecourt/2011/38050/x.pdf"}},
    {"doc": 2000000003, "passages": 1, "src": {"source": "ghc_court", "title": "SHRI UMA SHANKAR MISHRA Vs M/S FAMILY CREDIT LIMITED & 5 ORS.", "date": "2017-10-31", "citation": "Crl.Pet. 925/2016", "case_id": "Crl.Pet. 925/2016",
                                                "court": "Gauhati High Court", "url": "https://ghconline.gov.in/Judgment/CrlPet9252016.pdf"}},
    {"doc": 2000000004, "passages": 1, "src": {"source": "ghc_post2017", "title": "No Court Given Vs Someone", "date": "2021-01-01", "citation": "WP/1/2021", "url": "https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/y.pdf"}}])
rows, stats, n_side = B.build(idx, crawl, work, [])
by = {r["doc"]: r for r in rows}
check("a crawl judgment is read from its own header, dated and linked to the court's archive", by[250]["name"] == "Kangsari Haldar & Another v. The State of West Bengal" and by[250]["date"] == "1959-12-18" and by[250]["link"].endswith("/judis/250.pdf") and by[250]["link_kind"] == "court_archive_pdf" and by[250]["citations"].get("air"), by[250])
check("an unreadable header falls back to the index's case record", by[251]["name"] == "The State v. Beema" and by[251]["name_source"] == "index_case_record" and by[251]["date"] == "1990-02-01", by[251])
check("a bucket judgment takes its name, date, citation and PDF link from the bucket's metadata", by[1000000020]["name"] == "Adamji Umar Dalal v. The State of Bombay" and by[1000000020]["date"] == "1951-11-26" and by[1000000020]["citations"]["insc"] == "1951 INSC 54" and by[1000000020]["link"].endswith("1952_1_172_178_EN.pdf") and by[1000000020]["link_kind"] == "open_bucket_pdf", by[1000000020])
check("a bucket judgment the list does not know is named from the index but flagged: no link, to review", by[1000000021]["link"] is None and by[1000000021]["name"] == "A v. B", by[1000000021])
check("a row with no name is flagged for a person and keeps its link", by[250]["review"] is False and all(r["review"] == (r["name"] is None) for r in rows if r["link"] and r["doc"] != 2000000004))
check("a High Court judgment of the High Court bucket: name from 'X Vs Y', date, case number, the bucket link, and its court", by[2000000001]["name"] == "Dinathso Chaitom v. The State of AP" and by[2000000001]["court"] == "Gauhati High Court"
      and by[2000000001]["date"] == "2020-12-17" and by[2000000001]["citations"] == {"case_no": "Crl.Petn./52/2020"} and by[2000000001]["link_kind"] == "high_court_bucket_pdf" and by[2000000001]["link"].startswith("https://indian-high-court-judgments"), by[2000000001])
check("Gauhati High Court 'State of AP' is shown as the State of Arunachal Pradesh, the raw name and parties are kept, and a Supreme Court 'State of A.P.' is left alone",
      by[2000000001].get("display_name") == "Dinathso Chaitom v. The State of Arunachal Pradesh" and by[2000000001]["name"] == "Dinathso Chaitom v. The State of AP" and by[2000000001]["respondent"] and
      B.shown_name({"name": "X v. State of A.P.", "court": "Supreme Court of India"}) is None and B.shown_name({"name": "X v. The State of A.P", "court": "Gauhati High Court"}) == "X v. The State of Arunachal Pradesh" and
      B.shown_name({"name": "X v. State of Assam", "court": "Gauhati High Court"}) is None and B.shown_name({"name": "X v. State of Apple", "court": "Gauhati High Court"}) is None)
check("a newer Supreme Court judgment: neutral citation, the court's own link, labelled Supreme Court", by[2000000002]["court"] == "Supreme Court of India" and by[2000000002]["citations"]["insc"] == "2024 INSC 738" and by[2000000002]["link_kind"] == "court_site_pdf"
      and by[2000000002]["name"].startswith("Baljinder Singh") and by[2000000002]["review"] is False, by[2000000002])
check("a High Court judgment from the court's own site gets its own link kind", by[2000000003]["link_kind"] == "high_court_site_pdf" and by[2000000003]["court"] == "Gauhati High Court" and by[2000000003]["name"].startswith("Shri Uma Shankar Mishra"), by[2000000003])
check("the bench glued to a party name by the court site's title is cut off", B.split_parties("TAFAR TAPPO & ORS Vs THE STATE OF ASSAM. MR MADAN B. LOKUR GOSWAMI") == ("TAFAR TAPPO & ORS", "THE STATE OF ASSAM")
      and B.split_parties("A Vs B") == ("A", "B") and B.split_parties("A versus B. Ors") == ("A", "B. Ors") and B.split_parties("no party word here") == (None, None))
check("a document whose court is not recorded is flagged for a person and is NOT labelled the Supreme Court", by[2000000004]["court"] == "Court not recorded" and by[2000000004]["review"] is True, by[2000000004])
check("every older document is labelled the Supreme Court", all(by[d]["court"] == "Supreme Court of India" for d in (250, 251, 1000000020, 1000000021)))
doc = B.write(rows, os.path.join(tmp, "t.json.gz"), {"documents": len(rows)})
d2, byd = B.load(os.path.join(tmp, "t.json.gz"))
check("the table round-trips", byd[250]["name"] == by[250]["name"] and d2["schema"] == B.SCHEMA)

# ---- link verification with a stand-in HEAD
def head(url):
    return (200, "application/pdf", 36813) if url.endswith("/250.pdf") else (200, "application/pdf", 1000) if "1952" in url else (404, None, 0)
res = B.verify_links(rows, {250: 36813, 251: 100}, {B.bucket_url(work["1952_1_172_178"]["key"]): 1000}, 5, pause=0, head=head)
check("a link passes when it is a PDF of the size stored for it", res["court_archive_pdf"]["checked"] == 2 and res["court_archive_pdf"]["ok"] == 1 and res["open_bucket_pdf"]["ok"] == 1, res)
check("a link that is missing is reported with what was found", res["court_archive_pdf"]["bad"][0]["status"] == 404)
print("\nALL PASSED" if not F else f"\n{len(F)} FAILED: {F}")
sys.exit(1 if F else 0)
