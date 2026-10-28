"""One page's report as a single self-contained HTML file (print it to PDF with print_pdf.js).

  python report.py --selftest

The report shows the traffic light and why, the page image, the English from each reading side by side, what the checks found and the
must-check list, and (in an appendix) the original-script readings. It never says the page is correct; every output carries the stamp
"Machine draft. Not a certified translation." The file holds the page image and the text: it is CASE DATA, keep it outside the repository.
Nothing is loaded from the internet.
"""
import base64, datetime, html, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checker

esc = html.escape
COLOURS = {"green": "#1d7a46", "amber": "#a85f00", "red": "#b3261e"}
CSS = """@page{size:A4 landscape;margin:12mm}body{font-family:'Noto Sans','Noto Sans Bengali','FreeSans','FreeSerif',system-ui,sans-serif;font-size:9.5pt;color:#111}
h1{font-size:16pt;margin:0 0 4px}h2{font-size:12.5pt;margin:14px 0 4px;border-bottom:1px solid #999}h3{font-size:10.5pt;margin:8px 0 3px}
.meta{color:#444;margin:0 0 6px}.warn{border:1.5px solid #b45309;background:#fef3c7;padding:6px 8px;margin:6px 0}.pageimg{text-align:center;margin:8px 0}
.pageimg img{max-height:105mm;max-width:100%;border:1px solid #bbb}table{border-collapse:collapse;width:100%;margin:4px 0}
th,td{border:1px solid #aaa;padding:3px 5px;text-align:left;vertical-align:top;font-size:9pt}th{background:#eee}
pre{white-space:pre-wrap;word-wrap:break-word;font-family:inherit;margin:0;font-size:9pt}.cols{display:flex;gap:8px;align-items:flex-start}
.col{flex:1;border:1px solid #bbb;padding:4px 6px;min-width:0}.small{font-size:8pt;color:#555;margin:3px 0}.none{color:#888;font-style:italic}.pb{page-break-before:always}"""


def pre(t):
    return "<pre>%s</pre>" % esc(t.strip()) if t and t.strip() else "<p class=none>(none)</p>"


def english(t):
    return t.split("TRANSLATION", 1)[1].lstrip("*:# \n-") if t and "TRANSLATION" in t else ""


def original(t):
    return (t.split("TRANSLATION", 1)[0] if t and "TRANSLATION" in t else t or "").replace("TRANSCRIPTION:", "").strip()


def build(pid, check, readings, image_path=None, language="", cost_inr=None):
    """check: a result of checker.check_page or checker.check_text_page. readings: {'view1','view2','view3'} for an image page, or
    {'text','english1','english2'} for a PDF page whose own text was used."""
    col = COLOURS[check["light"]]
    h = ["<h1>Page %s</h1><p class=meta>%s%s. Prepared %s.</p>" % (esc(pid), esc(language), (" &middot; model cost about Rs %.2f (estimate, a lower bound)" % cost_inr) if cost_inr is not None else "", datetime.date.today().isoformat()),
         "<div class=warn><b>Machine draft. Not a certified translation.</b> A person who reads the language must check every name, date, number and amount against the original page before anything is relied on. No reader marks its own mistakes; two readings agreeing does not make a reading correct.</div>"]
    why = "".join("<li><b>Red:</b> %s</li>" % esc(r) for r in check["reasons_red"]) + "".join("<li>Amber: %s</li>" % esc(r) for r in check["reasons_amber"]) + "".join("<li class=small>%s</li>" % esc(n) for n in check.get("notes", []))
    agr = check.get("agreement_view1_vs_view2") or {}
    h.append("<div style='border:2px solid %s;padding:8px 10px;margin:8px 0'><b style='color:%s;font-size:14pt'>%s</b> &nbsp; %s<ul style='margin:6px 0 0 18px'>%s</ul>%s</div>" % (
        col, col, check["light"].upper(), esc(check["person_task"]), why,
        ("<p class=small>The two views agree on %s%% of letters. Cut-offs are a first guess.</p>" % agr["percent"]) if agr else ""))
    if image_path and os.path.exists(image_path):
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        h.append("<div class=pageimg><img src='data:image/%s;base64,%s'></div>" % ({"jpg": "jpeg"}.get(ext, ext), base64.b64encode(open(image_path, "rb").read()).decode()))
    text_page = "text" in readings
    cols = []
    if text_page:
        cols = [("English draft 1", english(readings["english1"])), ("English draft 2", english(readings["english2"]))]
    else:
        cols = [("View 1: image as given", english(readings.get("view1"))), ("View 2: padded copy", english(readings.get("view2")))]
        if readings.get("view3"):
            cols.append(("View 3: ultra-high detail", english(readings["view3"])))
    h.append("<h2>English draft, reading by reading</h2><div class=cols>%s</div>" % "".join("<div class=col><h3>%s</h3>%s</div>" % (esc(n), pre(t)) for n, t in cols))
    if check.get("english_wobble"):
        h.append("<h3>English sentences that changed between the readings</h3><table><tr><th>First</th><th>Second</th></tr>%s</table>" % "".join(
            "<tr><td>%s</td><td>%s</td></tr>" % (esc(w.get("run1") or ""), esc(w.get("run2") or "")) for w in check["english_wobble"]))
    if check.get("english_term_differences"):
        h.append("<h3>Names and numbers that one English draft has and the other lacks</h3><table><tr><th>Kind</th><th>View 1 only</th><th>View 2 only</th></tr>%s</table>" % "".join(
            "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(t["kind"]), esc(", ".join(t["only_in_view_1"])), esc(", ".join(t["only_in_view_2"]))) for t in check["english_term_differences"]))
    if check.get("redundancy_flags"):
        h.append("<h2>Page checks that need no model</h2><ul>%s</ul>" % "".join("<li>%s</li>" % esc(f) for f in check["redundancy_flags"]))
    items = check.get("must_check", [])
    dis = [i for i in items if i["status"] == "DISAGREE"]; con = [i for i in items if i["status"] == "CONFIRM"]
    tb = {(t["type"], t["view1"], t["view2"]): t["third_view"] for t in check.get("third_view_on_disagreements", [])}
    if dis:
        h.append("<h2>Where the two views disagree (check these first)</h2><table><tr><th>Kind</th><th>View 1</th><th>View 2</th><th>View 3 sides with</th></tr>%s</table>" % "".join(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(i["type"]), esc(str(i["A"])) if i["A"] else "<i>not found</i>", esc(str(i["B"])) if i["B"] else "<i>not found</i>",
                                                                       esc(tb.get((i["type"], i["A"], i["B"]), "not run"))) for i in dis))
        h.append("<p class=small>View 3 sides with one reading only as a hint. Agreement is not correctness.</p>")
    if con:
        h.append("<h2>Must-check list (the readings agree; a person still confirms each against the page)</h2><table><tr><th>Kind</th><th>Value</th></tr>%s</table>" % "".join(
            "<tr><td>%s</td><td>%s</td></tr>" % (esc(i["type"]), esc(str(i["A"]))) for i in con))
    if check.get("line_differences"):
        h.append("<h3>Lines that differ between the views (original script)</h3><table><tr><th>View 1</th><th>View 2</th><th>similarity</th></tr>%s</table>" % "".join(
            "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(d["A"] or "-"), esc(d["B"] or "-"), d["similarity"]) for d in check["line_differences"][:60]))
    h.append("<h1 class=pb>Appendix: original-script readings</h1>")
    if text_page:
        h.append("<h3>Text layer of the PDF (exact)</h3>%s" % pre(readings["text"]))
    else:
        for n, k in (("View 1: image as given", "view1"), ("View 2: padded copy", "view2"), ("View 3: ultra-high detail", "view3")):
            if readings.get(k):
                h.append("<h3>%s</h3>%s" % (esc(n), pre(original(readings[k]))))
    return "<!doctype html><html><head><meta charset=utf-8><title>Page %s</title><style>%s</style></head><body>%s</body></html>" % (esc(pid), CSS, "".join(h))


def selftest():
    R = "TRANSCRIPTION\n1. dated 15/8/92 here\nTRANSLATION\nThe first line is here. The second line follows."
    R2 = R.replace("15/8/92", "16/8/92").replace("The second line follows.", "A different sentence entirely <script>alert(1)</script>.")
    chk = checker.check_page("typed", R, R2, R, "STOP", "STOP", "STOP")
    out = build("T01", chk, {"view1": R, "view2": R2, "view3": R}, None, "Assamese", 1.5)
    assert "Machine draft. Not a certified translation." in out and "AMBER" in out and "View 3 sides with" in out
    assert "<script>alert(1)</script>" not in out, "reading text must be escaped"
    assert "http://" not in out and "https://" not in out, "nothing may be loaded from the internet"
    E = "TRANSLATION\nOne line here. Another line there."
    t = build("T02", checker.check_text_page("order here", E, E), {"text": "order here", "english1": E, "english2": E})
    assert "GREEN" in t and "Text layer of the PDF" in t
    print("selftest OK (invented text only)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        sys.exit(__doc__)
