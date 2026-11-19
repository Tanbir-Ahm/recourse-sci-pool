"""What the Reading Desk site shows for a job: the pipeline's run folder read back as plain data (pages, documents, the 'Read these first' items, the glossary notes), the page images
as small JPEGs, and the progress of a run that is still going. Nothing here decides anything: every light, flag and note was made by the pipeline's own checks, and this module only
reads them. The 'Read these first' items follow report.read_first_page / read_first_document, line for line.
"""
import csv, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OCR_DIR = os.path.dirname(HERE)
sys.path.insert(0, OCR_DIR)
import checker, harness, pipeline, report

STAMP = "Machine draft. Not a certified translation."
SENSE_UNRUN = "the sense check did not run"          # the start of pipeline.SENSE_UNRUN


def notices(reasons):
    """Reasons that must not hide inside a closed list: a check that was asked for and did not happen."""
    return [r["text"][:1].upper() + r["text"][1:] + "." for r in reasons if r["text"].startswith(SENSE_UNRUN)]
RANK = {"red": 0, "amber": 1, "green": 2}
PREVIEW_PX = 1600
PID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,80}$")
_PAGE = re.compile(r"^(.*)_p(\d+)$")


def _json(path, default=None):
    try:
        with open(path, encoding="utf8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _text(path):
    try:
        with open(path, encoding="utf8") as f:
            return f.read()
    except OSError:
        return ""


def _short(s, n=240):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


_LISTLIKE = re.compile(r"^\s*(?:\(?\d{1,3}[.)]|[-*\u2022])\s")
_NOTE = re.compile(r"^\s*\[(?:margin|footer|header)\b", re.I)


def reflow(text):
    """The English as paragraphs. A reader hands the lines of a handwritten page over with a line break at every line end; a blank line, a numbered or bulleted line and a
    margin/footer/header note start a paragraph, every other line break becomes a space. The words are not touched."""
    paras, cur = [], []
    for line in (text or "").replace("\r", "").split("\n"):
        s = line.strip()
        if not s:
            if cur:
                paras.append(" ".join(cur)); cur = []
            continue
        if cur and (_LISTLIKE.match(s) or _NOTE.match(s) or _NOTE.match(cur[-1])):
            paras.append(" ".join(cur)); cur = []
        cur.append(s)
    if cur:
        paras.append(" ".join(cur))
    return paras


# ---------------------------------------------------------------- the 'Read these first' items
def items_page(chk):
    """Where a reader must look on one page, most pressing first. Same sources and order as report.read_first_page."""
    items = []
    for c in chk.get("corrections", []):
        if c["kind"] in checker.CORRECTION_KINDS and c["where"] == "original":
            partial = not c.get("in_all", True)
            find = c["text"] or {"stamp or seal over text": "[stamp over text]", "struck out, unreadable": "[struck: ?]"}.get(c["kind"], "")
            items.append({"kind": "correction", "sev": "check", "title": c["kind"][:1].upper() + c["kind"][1:] + (": " + c["text"] if c["text"] else ""),
                          "detail": "In the line: " + _short(c["line"]) + (" Marked in only some of the readings (%s)." % ", ".join(c.get("views", [])) if partial else ""), "find": find})
    doubts = [c for c in chk.get("corrections", []) if c["kind"] == "doubtful reading, explained" and c["where"] == "English"]
    if doubts:
        items.append({"kind": "doubtful", "sev": "check", "title": "A doubtful reading, explained by the reader" + (" (%d on this page)" % len(doubts) if len(doubts) > 1 else ""),
                      "detail": _short(doubts[0]["text"]), "find": doubts[0]["text"][:30]})
    tb = {(t["type"], t["view1"], t["view2"]): t["third_view"] for t in chk.get("third_view_on_disagreements", [])}
    for i in chk.get("must_check", []):
        if i["status"] == "DISAGREE":
            a, b = (str(i["A"]) if i["A"] else "not found"), (str(i["B"]) if i["B"] else "not found")
            items.append({"kind": "readings_differ", "sev": "high", "title": "%s read differently: %s or %s" % (i["type"].capitalize(), a, b),
                          "detail": "The third look says: %s." % tb.get((i["type"], i["A"], i["B"]), "not run"), "find": a if i["A"] else b})
    for c in chk.get("third_view_contradicts", []):
        items.append({"kind": "third_look", "sev": "high", "title": "%s: both readings say %s, the closer look says %s" % (c["type"].capitalize(), c["views_1_and_2"], c["third_view"]),
                      "detail": "Two readings of one picture agreeing is not proof. Compare each digit with the page.", "find": str(c["views_1_and_2"])})
    for k in chk.get("sense_flags", []):
        items.append({"kind": "sense", "sev": "high" if k["severity"] == "high" else "check", "title": "May not make sense (%s)" % k["severity"], "detail": "%s — %s" % (_short(k["quote"], 200), k["problem"]), "find": _short(k["quote"], 50), "quote": k["quote"]})
    for w in (chk.get("english_wobble") or [])[:4]:
        items.append({"kind": "changed", "sev": "check", "title": "A sentence changed between the readings", "detail": "First: %s Second: %s" % (_short(w.get("run1"), 140), _short(w.get("run2"), 140)), "find": _short(w.get("run1"), 40)})
    return items


def items_document(chk, english1):
    """The same for a whole document (report.read_first_document)."""
    items = []
    for d in chk.get("page_disagreements", []):
        items.append({"kind": "readings_differ", "sev": "high", "title": "%s on page %s: %s or %s" % (str(d["type"]).capitalize(), d["page"], d["A"], d["B"]),
                      "detail": "The third look says: %s. Not confirmed, even though the two translations agree." % (d.get("third_view") or "not run"), "find": str(d["A"])})
    seen = set()
    for c in chk.get("corrections", []):
        if c["kind"] in checker.CORRECTION_KINDS and c["where"] == "original":
            k = (c["kind"], c["text"], c.get("page"))
            if k not in seen:
                seen.add(k)
                find = c["text"] or {"stamp or seal over text": "[stamp over text]", "struck out, unreadable": "[struck: ?]"}.get(c["kind"], "")
                items.append({"kind": "correction", "sev": "check", "title": c["kind"][:1].upper() + c["kind"][1:] + (": " + c["text"] if c["text"] else "") + " (page %s)" % c.get("page", "?"),
                              "detail": "In the line: " + _short(c["line"]), "find": find})
    for x in report._marked_sentences(english1)[:6]:
        items.append({"kind": "marked", "sev": "check", "title": "A passage the reader marked", "detail": _short(x, 260), "find": _short(x, 40)})
    for k in chk.get("sense_flags", []):
        items.append({"kind": "sense", "sev": "high" if k["severity"] == "high" else "check", "title": "May not make sense (%s)" % k["severity"], "detail": "%s — %s" % (_short(k["quote"], 200), k["problem"]), "find": _short(k["quote"], 50), "quote": k["quote"]})
    for w in (chk.get("english_wobble") or [])[:4]:
        items.append({"kind": "changed", "sev": "check", "title": "A sentence changed between the two translations", "detail": "First: %s Second: %s" % (_short(w.get("run1"), 140), _short(w.get("run2"), 140)), "find": _short(w.get("run1"), 40)})
    return items


def _must(chk):
    return [{"status": i["status"], "type": i["type"], "a": i.get("A"), "b": i.get("B")} for i in chk.get("must_check", []) if i.get("type")]


def _gloss(chk):
    return [{"word": n.get("word"), "english": n.get("english"), "note": n.get("text"), "applies_to": n.get("applies_to", [])} for n in chk.get("glossary_notes", [])]


# ---------------------------------------------------------------- names shown for pages
def describe(meta, pid):
    """(document name, page number, label) of a page id, from the files the user uploaded."""
    m = _PAGE.match(pid)
    stem, n = (m.group(1), int(m.group(2))) if m else (pid, 1)
    files = meta.get("files", [])
    for f in files:
        if f.get("stem") == pid and not f.get("group"):                    # a single image
            return stem, 1, f["original"]
    for f in files:
        if f.get("stem") == stem and f.get("kind") == "pdf":
            return stem, n, "%s, page %d" % (f["original"], n)
    grouped = [f for f in files if f.get("group") == stem]
    if grouped and 1 <= n <= len(grouped):
        return stem, n, grouped[n - 1]["original"]
    return stem, n, pid


def doc_display(meta, stem):
    for f in meta.get("files", []):
        if f.get("stem") == stem and f.get("kind") == "pdf":
            return f["original"]
    return meta.get("label") or stem


# ---------------------------------------------------------------- the result of a finished run
def _reports(run_dir, kind, name):
    base = os.path.join(run_dir, "report", name) if kind == "page" else os.path.join(run_dir, "document", name + "_document")
    return {"html": os.path.exists(base + ".html"), "pdf": os.path.exists(base + ".pdf")}


def build(meta, job_dir):
    run = os.path.join(job_dir, "run")
    summary = _json(os.path.join(run, "summary.json"))
    if not summary:
        return None
    ledger = harness.read_ledger(os.path.join(run, "ledger.jsonl"))
    names = {r["page"] for r in ledger}
    pages = []
    for srow in summary.get("pages", []):
        pid = srow["page"]
        chk = _json(os.path.join(run, "checks", pid + ".json"), {})
        doc, n, label = describe(meta, pid)
        is_text = (pid + "__en1") in names
        readings = []
        if is_text:
            e1, _ = pipeline.reading(ledger, run, pid + "__en1"); e2, _ = pipeline.reading(ledger, run, pid + "__en2")
            english = report.english(e1 or "")
            readings = [{"name": "English draft 1", "english": english}, {"name": "English draft 2", "english": report.english(e2 or "")}]
        else:
            t1, f1 = pipeline.reading(ledger, run, pid + "__view1"); t2, f2 = pipeline.reading(ledger, run, pid + "__view2"); t3, _ = pipeline.reading(ledger, run, pid + "__view3")
            rd = {"view1": t1, "view2": t2, "f1": f1, "f2": f2}
            english = chk.get("english_marked") or pipeline.page_english(rd)
            readings = [{"name": "Reading 1: the page as given", "english": report.english(t1 or "")}, {"name": "Reading 2: the page with a white border", "english": report.english(t2 or "")}]
            if t3:
                readings.append({"name": "Reading 3: a closer look", "english": report.english(t3)})
        agr = chk.get("agreement_view1_vs_view2") or {}
        pages.append({
            "id": pid, "doc": doc, "n": n, "label": label, "light": srow["light"], "type": srow.get("page_type"), "text_layer": is_text,
            "agreement": agr.get("percent"), "paras": reflow(english), "reasons": [{"level": "red", "text": r} for r in chk.get("reasons_red", [])] + [{"level": "amber", "text": r} for r in chk.get("reasons_amber", [])],
            "notes": chk.get("notes", []), "person_task": chk.get("person_task"), "english": english, "readings": readings,
            "notices": notices([{"text": t} for t in chk.get("reasons_red", []) + chk.get("reasons_amber", [])]), "read_first": items_page(chk), "glossary": _gloss(chk), "must_check": _must(chk), "third_look": bool(srow.get("third_view")),
            "orientation": (chk.get("orientation") or {}).get("status"), "image": preview_source(run, pid) is not None,
            "report": _reports(run, "page", pid), "marksheet": os.path.exists(os.path.join(run, "marksheets", pid + "_marksheet.html"))})
    pages.sort(key=lambda p: (p["doc"], p["n"], p["id"]))
    docs = []
    for row in summary.get("documents", []):
        name = row["document"]
        if "light" not in row:
            docs.append({"id": name, "display": doc_display(meta, name), "light": None, "status": row.get("status", "not joined")})
            continue
        d = os.path.join(run, "document")
        chk = _json(os.path.join(d, name + "_check.json"), {})
        e1 = _text(os.path.join(d, name + "_translation_1.txt"))
        docs.append({
            "id": name, "display": doc_display(meta, name), "light": row["light"], "pages": [p["id"] for p in pages if p["doc"] == name],
            "reasons": [{"level": "red", "text": r} for r in chk.get("reasons_red", [])] + [{"level": "amber", "text": r} for r in chk.get("reasons_amber", [])],
            "person_task": chk.get("person_task"), "mode": chk.get("translation_mode"), "english": e1, "paras": reflow(e1), "english_2": _text(os.path.join(d, name + "_translation_2.txt")),
            "notices": notices([{"text": t} for t in chk.get("reasons_red", []) + chk.get("reasons_amber", [])]), "read_first": items_document(chk, e1), "names": chk.get("name_differences"), "joins": chk.get("page_joins", []), "references": chk.get("references", {}),
            "reference_flags": chk.get("reference_flags", []), "glossary": _gloss(chk), "must_check": _must(chk), "marks": chk.get("model_marks", {}), "redundancy": chk.get("redundancy_flags", []),
            "report": _reports(run, "doc", name), "disagreements_marked": chk.get("disagreements_marked", 0)})
    lights = [p["light"] for p in pages] + [d["light"] for d in docs if d.get("light")]
    return {"stamp": STAMP, "light": min(lights, key=lambda x: RANK[x]) if lights else None, "pages": pages, "documents": docs,
            "estimated_cost_inr": summary.get("estimated_cost_inr"), "stopped_by_budget": bool(meta.get("stopped_by_budget"))}


# ---------------------------------------------------------------- page images
def preview_source(run, pid):
    """The picture of a page as it was read (turned upright if it was photographed turned), or None."""
    vd = os.path.join(run, "_views")
    try:
        for f in sorted(os.listdir(vd)):
            if f.startswith(pid + "__view1."):
                return os.path.join(vd, f)
    except OSError:
        pass
    tri = os.path.join(run, "triage")
    try:
        for f in os.listdir(tri):
            for p in (_json(os.path.join(tri, f), {}).get("per_page") or []):
                if "%s_p%d" % (f[:-5], p["page"]) == pid and p.get("saved_image"):
                    q = os.path.join(run, "_pages", os.path.basename(p["saved_image"]))
                    return q if os.path.exists(q) else None
    except OSError:
        pass
    return None


def preview_jpeg(run, pid):
    """Path of a JPEG (long side at most PREVIEW_PX) of the page, made once and kept in run/web. None when there is no picture."""
    if not PID_RE.match(pid):
        return None
    src = preview_source(run, pid)
    if not src:
        return None
    out = os.path.join(run, "web", pid + ".jpg")
    if not os.path.exists(out):
        from PIL import Image
        os.makedirs(os.path.dirname(out), exist_ok=True)
        im = Image.open(src).convert("RGB")
        im.thumbnail((PREVIEW_PX, PREVIEW_PX))
        im.save(out + ".part", "JPEG", quality=84)
        os.replace(out + ".part", out)
    return out


# ---------------------------------------------------------------- progress of a run that is going
def stage(led, n_pages):
    """What the run is doing, from the calls that have finished (the pipeline only records a call when it ends, so this names the step after the last finished one when that is clear)."""
    if not led:
        return "Starting"
    last = led[-1]["page"]
    both = {r["page"].split("__")[0] for r in led if r["page"].endswith(("__view2", "__en2"))}
    m = re.search(r"_p(\d+)__", last)
    pg = (" page %s" % m.group(1)) if m else ""
    if "__sense" in last or "_full__t" in last:
        return "Finishing: checking that the English makes sense"
    if "__orient" in last:
        return "Checking which way up the page is"
    if "__view3" in last:
        return "Taking a closer look at%s" % (pg or " the pages")
    if len(both) >= max(1, n_pages):
        return "Both readings are done. Taking a closer look where a date or amount needs it, then checking that the English makes sense"
    if "__view1" in last or "__view2" in last:
        return "Reading%s (two independent readings)" % (pg or " the page")
    if "__en" in last:
        return "Translating the text of%s" % (pg or " the page")
    return "Working"


def progress(meta, job_dir):
    led = harness.read_ledger(os.path.join(job_dir, "run", "ledger.jsonl"))
    n = max(1, int(meta.get("n_pages") or 1))
    expected = 2 * n + max(1, n // 2) + (3 if n > 1 else 1)
    done = meta.get("status") in ("done", "failed", "cancelled")
    return {"calls": len(led), "percent": 100 if meta.get("status") == "done" else (0 if not led else min(95, int(100.0 * len(led) / expected))),
            "stage": stage(led, n) if not done else None, "estimated_cost_inr": round(harness.spent_inr(led), 2)}


# ---------------------------------------------------------------- glossary
def glossary_rows():
    path = os.path.join(OCR_DIR, "glossary", "assamese_legal.csv")
    rows = []
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                src = r.get("source", "")
                group = "1967 Government of Assam glossary" if src.startswith("Government of Assam") else ("The owner's word list" if src.startswith("word and meaning supplied") else "Drafted from general knowledge")
                rows.append({"id": r["id"], "word": r["word"], "variants": [v for v in r.get("variants", "").split("|") if v], "english": r["english"], "avoid": [v for v in r.get("not_as", "").split("|") if v],
                             "kind": r["kind"], "area": r["domain"], "note": r["note"], "group": group, "status": r.get("status", "")})
    except OSError:
        pass
    return rows


def selftest():
    import tempfile
    assert PID_RE.match("demo_p1") and not PID_RE.match("../x") and not PID_RE.match("a/b") and not PID_RE.match("")
    meta = {"label": "Papers", "files": [{"stem": "d1", "kind": "pdf", "original": "scan.pdf"}, {"stem": "img1", "kind": "image/png", "original": "photo.png"},
                                          {"group": "doc", "stem": "doc_p1", "original": "a.jpg", "kind": "image/jpeg"}, {"group": "doc", "stem": "doc_p2", "original": "b.jpg", "kind": "image/jpeg"}]}
    assert describe(meta, "d1_p2") == ("d1", 2, "scan.pdf, page 2") and describe(meta, "img1") == ("img1", 1, "photo.png")
    assert describe(meta, "doc_p2") == ("doc", 2, "b.jpg") and doc_display(meta, "d1") == "scan.pdf" and doc_display(meta, "doc") == "Papers"
    it = items_page({"corrections": [{"kind": "struck out", "text": "victim", "where": "original", "line": "x ~~victim~~", "views": ["view 1"], "in_all": False}],
                     "must_check": [{"status": "DISAGREE", "type": "date", "A": "1/2/20", "B": "2/2/20"}], "sense_flags": [{"quote": "a b c", "problem": "p", "severity": "high"}]})
    assert [i["kind"] for i in it] == ["correction", "readings_differ", "sense"] and "only some" in it[0]["detail"] and it[1]["sev"] == "high"
    L = lambda *names: [{"page": n} for n in names]
    assert stage(L("demo_p1__view1", "demo_p1__view2", "demo_p2__view1"), 3).startswith("Reading page 2") and stage(L("demo_full__sense"), 3).startswith("Finishing") and stage([], 1) == "Starting"
    assert stage(L("a__view1", "a__view2"), 1).startswith("Both readings are done") and stage(L("a_p1__view1", "a_p1__view2", "a_p2__view1"), 2).startswith("Reading page 2")
    assert stage(L("a_p1__view3"), 1).startswith("Taking a closer look at page 1")
    assert notices([{"text": "the sense check did not run or gave no usable answer (x): y"}, {"text": "other"}]) == ["The sense check did not run or gave no usable answer (x): y."]
    assert glossary_rows() and all("word" in r for r in glossary_rows())
    assert reflow("One line\nruns on\n\nNew para\n1. item one\n2. item two\n[footer: p 3]\nafter") == ["One line runs on", "New para", "1. item one", "2. item two", "[footer: p 3]", "after"], reflow("One line\nruns on\n\nNew para\n1. item one\n2. item two\n[footer: p 3]\nafter")
    assert reflow("") == [] and reflow("a\r\nb") == ["a b"]
    print("results selftest OK")


if __name__ == "__main__":
    selftest()
