"""The checked-reading pipeline for a run (plan section 11): PDFs and page images in, a report and a marking sheet per page out.

  export GEMINI_API_KEY=...        # in the environment's secrets; never pasted in chat, never printed
  python pipeline.py --input PAGES_DIR_OR_FILE --out RUN --language Assamese --page-type typed|handwritten --budget-inr 40
  python pipeline.py --selftest    # wiring test with fake callers; no network, no cost

For each PDF page, step 2 (pdf_triage.py) decides whether the PDF's own text can be used:
  good text layer    no reading model: the exact text is kept and translated TWICE with a text-only call to argon; the two English drafts are compared
  anything else      the page is rendered to an image and read like a page image
For each page image:
  view 1   the image as given             \\ two blind reads by gemini-4-argon, same instructions, neither sees the other
  view 2   a padded copy (white border)   /
  view 3   the image again at ultra-high detail, ONLY if the checker flags the page (--third-view auto): the first two views disagree on an item, agree on
           fewer letters than 97%, or the page holds a date or an amount (agreement between two views of one image is not proof of a digit: 10w). It is a hint
           for a person, never an answer: the checker lists every agreed date or amount that view 3 reads differently, and puts it first
Before reading, each page image is checked for being photographed turned (--orient auto, the default; orient.py): Tesseract first, the reading model only when Tesseract is not sure; a
turned page is turned upright (the original is kept in RUN and the report says so); a page that cannot be settled is left alone and marked.
Then, for a PDF of two or more pages (--stitch auto, the default), the readings (or the PDF's own text) of all its pages are JOINED into one text
(stitch.py: a sentence that runs over a page break is joined) and translated twice, blind, with prompts/translate_stitched.txt (names by sound with the
original-script word in square brackets, printed numbers and references kept as printed, [sic] on a suspected misprint). checker.check_document compares the two
translations; document/<name>_*.html is the whole-document report. Translation 1 is the one to read: fixed in advance, never chosen by the tool.
Then checker.py sets a traffic light, redundancy.py adds the checks that need no model, and report.py / marksheet.py write one report
and one marking sheet per page. The light is a reading order, never permission to skip reading a page: a person reads every page in full for now.
Page type is typed or handwritten (--page-type for all pages, --types FILE.json for {"page id": "handwritten"}). A handwritten page is never green.
Outputs in RUN: ledger.jsonl (every call, cost an ESTIMATE), checks/<page>.json, report/<page>.html (+ .pdf with --pdf), marksheets/<page>_marksheet.html,
summary.json. All of it except the ledger holds page text or images: CASE DATA, keep RUN outside the repository.
Cost: about Rs 1 to 1.5 per read logged (the real bill has run 1.5 to 2 times higher). --budget-inr stops the run before a call that would pass it;
a stopped run is resumed by running the same command again (finished calls are skipped). Cloud Vision for the PDF match (--pdf-reader vision) is
outside the budget and sends each PDF page to Google.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time
from types import SimpleNamespace
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checker, harness, marksheet, orient, report, stitch

MODEL = "gemini-4-argon"
PAD = 0.06           # white border on each side of view 2, as a share of the width and height
LIGHT_ORDER = {"red": 0, "amber": 1, "green": 2}


def make_views(work, out):
    """view 1 is the image as given; view 2 is the same image with a white border. Returns the views folder and each page's files."""
    from PIL import Image, ImageOps
    vd = os.path.join(out, "_views"); os.makedirs(vd, exist_ok=True)
    files = {}
    for pid, path, mime in work:
        ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(mime, ".png")          # from the content, not the file name
        v1 = os.path.join(vd, pid + "__view1" + ext); shutil.copyfile(path, v1)
        im = Image.open(path).convert("RGB")
        px, py = int(im.width * PAD), int(im.height * PAD)
        v2 = os.path.join(vd, pid + "__view2.png"); ImageOps.expand(im, border=(px, py, px, py), fill=(255, 255, 255)).save(v2)
        files[pid] = {"view1": v1, "view2": v2, "original": path}
    return vd, files


def reading(ledger, out, page):
    """The text of a page's reading and its finish reason. An incomplete reading comes back with the finish 'INCOMPLETE' so the checker turns it red."""
    rows = [r for r in ledger if r["page"] == page and r["model"] == MODEL and r.get("outfile")]
    good = [r for r in rows if r["status"] == "ok"]
    r = good[-1] if good else (rows[-1] if rows else None)
    if not r:
        return None, None
    return open(os.path.join(out, r["outfile"]), encoding="utf8").read(), (r.get("finish") if r["status"] == "ok" else "INCOMPLETE")


def prompt_chooser(args, types):
    """A function page id -> reading prompt. A handwritten page gets prompts/read_translate_marked.txt (marks for crossed-out words, insertions and stamps over text, and the
    rule never to write a garbled sentence; plan 10ak) when --marks is auto or on; a typed page gets the plain prompt unless --marks on."""
    plain = open(os.path.join(HERE, "prompts", "read_translate.txt"), encoding="utf8").read().format(language=args.language)
    marked = open(os.path.join(HERE, "prompts", "read_translate_marked.txt"), encoding="utf8").read().format(language=args.language)
    mode = getattr(args, "marks", "auto")

    def choose(page):
        pid = page.split("__view")[0]
        t = types.get(pid, args.page_type)
        return marked if (mode == "on" or (mode == "auto" and t == "handwritten")) else plain
    return choose


def read_pages(out, folder, runs_args, caller, media=None, prompt_for=None):
    """Run the harness over a folder of views (a view file is <page>__view<N>.<ext>); media sets the image-detail setting for this run only."""
    ns = SimpleNamespace(pages=folder, out=out, models_file=None, prompt=None, language=runs_args.language, runs=1, model_list=[MODEL],
                         budget_inr=runs_args.budget_inr, max_calls=None, force=False, prompt_for=prompt_for)
    harness.MEDIA_RESOLUTION = media
    try:
        harness.run(ns, caller)
    finally:
        harness.MEDIA_RESOLUTION = None


def translate_pages(args, out, text_pages, ledger, models, fx, text_caller):
    """Two blind translations of each good text layer (a text-only call to argon)."""
    prompt = open(os.path.join(HERE, "prompts", "translate_text.txt"), encoding="utf8").read().format(language=args.language)
    key = os.environ.get(models[MODEL]["key_env"], "")
    for pid, p in text_pages:
        text = open(p["saved_text"], encoding="utf8").read()
        for n in (1, 2):
            page = "%s__en%d" % (pid, n)
            if any(r["page"] == page and r["model"] == MODEL and r["status"] == "ok" for r in ledger):
                continue
            if args.budget_inr is not None and harness.spent_inr(ledger) >= args.budget_inr:
                print("STOP: the budget of Rs %s is reached; run the same command again with a higher --budget-inr to continue." % args.budget_inr); return
            res = text_caller(MODEL, key, prompt, text)
            rec = harness.log_call(out, ledger, page, MODEL, 1, res, models, fx)
            print("%s %s: %s, Rs %.2f" % (page, MODEL, rec["status"], rec["cost_inr"]), flush=True)


_DOC = re.compile(r"^(.*)_p(\d+)$")


def group_documents(pids):
    """PDF pages are named <file>_p<N>; a file with two or more pages is a document. Returns {file: {page number: page id}}."""
    docs = {}
    for pid in pids:
        m = _DOC.match(pid)
        if m:
            docs.setdefault(m.group(1), {})[int(m.group(2))] = pid
    return {d: p for d, p in docs.items() if len(p) >= 2}


def page_source(rd):
    """The original-script text of one page for joining: the PDF's own text, else the view-1 reading (view 2 if view 1 did not finish). Returns (text, note)."""
    if "text" in rd:
        return rd["text"], None
    if rd.get("view1") and rd.get("f1") == "STOP":
        return rd["view1"], None
    if rd.get("view2") and rd.get("f2") == "STOP":
        return rd["view2"], "view 1 did not finish: view 2 used"
    return None, "no complete reading"


def sense_check(args, out, ledger_path, models, fx, text_caller, page, english):
    """One text-only call (prompts/sense_check.txt) that lists sentences of the English that may not make sense; no image, no original, never a rewrite (plan 10al). Returns
    (kept findings, number dropped because the quote was not in the text) or None when the check is off, there is no English, or its answer could not be read."""
    if getattr(args, "sense", "auto") == "off" or not english or not english.strip():
        return None
    ledger = harness.read_ledger(ledger_path)
    if not any(r["page"] == page and r["model"] == MODEL and r["status"] == "ok" for r in ledger):
        if args.budget_inr is not None and harness.spent_inr(ledger) >= args.budget_inr:
            print("STOP: the budget of Rs %s is reached; the sense check of %s was not run." % (args.budget_inr, page)); return None
        prompt = open(os.path.join(HERE, "prompts", "sense_check.txt"), encoding="utf8").read().strip()
        res = text_caller(MODEL, os.environ.get(models[MODEL]["key_env"], ""), prompt, english)
        rec = harness.log_call(out, ledger, page, MODEL, 1, res, models, fx)
        print("%s %s: %s, Rs %.2f" % (page, MODEL, rec["status"], rec["cost_inr"]), flush=True)
        ledger = harness.read_ledger(ledger_path)
    t, _ = reading(ledger, out, page)
    items = checker.parse_sense(t or "")
    return checker.match_sense(items, english) if items is not None else None


def page_english(rd):
    """The English of a page to be sense-checked: the PDF text page's draft 1, else the view 1 English (view 2 if view 1 did not finish)."""
    if "text" in rd:
        return report.english(rd.get("english1") or "")
    t = rd.get("view1") if rd.get("f1") == "STOP" else rd.get("view2")
    return report.english(t or "")


def document_mode(args, pages, types):
    """'text' (the joined original-script text translated twice, text only) or 'english' (the per-page English joined). --stitch auto: a document with a handwritten page
    uses 'english', because a text-only translation cannot see the image and made one sentence nonsense on a real affidavit (10ak); a typed document uses 'text'."""
    if args.stitch in ("text", "english"):
        return args.stitch
    return "english" if any(types.get(pid, args.page_type) == "handwritten" for pid in pages.values()) else "text"


def join_english(pages, readings, view, fin):
    """The English of each page's reading (view 1 or view 2) joined into one text, with the seams repaired by stitch.py (a sentence that ran over a page break is joined)."""
    eng = {}
    for n in sorted(pages):
        rd = readings[pages[n]]
        t = rd.get(view) if rd.get(fin) == "STOP" else None
        if t is None:
            t = rd.get("view2" if view == "view1" else "view1")          # the other view when this one did not finish
        e = report.english(t or "")
        if e:
            eng[n] = e
    text, _ = stitch.stitch_pages(eng) if eng else ("", [])
    return text, eng


def page_evidence(pages, results):
    """What the readings of each page showed: the must-check values the views disagree on (with the third view's side) and the corrections marked on the page."""
    items, corr = [], []
    for n in sorted(pages):
        r = (results or {}).get(pages[n]) or {}
        tb = {(t["type"], t["view1"]): t["third_view"] for t in (r.get("third_view_on_disagreements") or [])}
        for i in r.get("must_check") or []:
            if i.get("status") == "DISAGREE":
                items.append({"page": n, "status": "DISAGREE", "type": i["type"], "A": i.get("A"), "B": i.get("B"), "third_view": tb.get((i["type"], i.get("A")))})
        corr += [dict(c, page=n) for c in (r.get("corrections") or [])]
    return items, corr


def stitch_documents(args, out, readings, ledger_path, models, fx, text_caller, known, results=None, types=None):
    """Join each document's pages and translate the joined text twice. Returns a list of summary rows; writes RUN/document/<name>_*."""
    docs = group_documents(readings)
    rows = []
    if args.stitch == "off" or not docs:
        return rows
    results, types = results or {}, types or {}
    prompt = open(os.path.join(HERE, "prompts", "translate_stitched.txt"), encoding="utf8").read().format(language=args.language)
    key = os.environ.get(models[MODEL]["key_env"], "")
    os.makedirs(os.path.join(out, "document"), exist_ok=True)
    for name, pages in sorted(docs.items()):
        src, notes, missing = {}, [], []
        for n in sorted(pages):
            text, note = page_source(readings[pages[n]])
            if text is None:
                missing.append(n)
            else:
                src[n] = text
                if note:
                    notes.append({"page": n, "action": note})
        if missing:
            print("DOCUMENT %s not joined: no complete reading for page(s) %s" % (name, ", ".join(map(str, missing))), flush=True)
            rows.append({"document": name, "status": "not joined: no complete reading for page(s) %s" % ", ".join(map(str, missing))})
            continue
        text, joins = stitch.stitch_pages(src)
        joins = notes + joins
        mode = document_mode(args, pages, types)
        page_items, page_corr = page_evidence(pages, results)
        if mode == "english":                                  # handwritten: the English of the pages (made WITH the image) joined, not a text-only translation of the joined text (10ak)
            e1t, j1 = join_english(pages, readings, "view1", "f1"); e2t, j2 = join_english(pages, readings, "view2", "f2")
            e1, e2, f1, f2 = "TRANSLATION\n" + e1t, "TRANSLATION\n" + e2t, "STOP" if e1t else None, "STOP" if e2t else None
            chk = checker.check_document(text, e1, e2, known, f1, f2, joins, page_items, page_corr)
            chk["translation_mode"] = "english of the pages, joined (made with the page images)"
            sn = sense_check(args, out, ledger_path, models, fx, text_caller, name + "_full__sense", e1t)
            if sn is not None:
                checker.apply_sense(chk, *sn)
            d = os.path.join(out, "document")
            for suffix, body in (("_source.txt", text), ("_translation_1.txt", e1t), ("_translation_2.txt", e2t)):
                open(os.path.join(d, name + suffix), "w", encoding="utf8").write(body)
            json.dump(chk, open(os.path.join(d, name + "_check.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
            open(os.path.join(d, name + "_document.html"), "w", encoding="utf8").write(report.build_document(name, chk, text, e1, e2, args.language))
            rows.append({"document": name, "pages": len(pages), "light": chk["light"], "reasons": chk["reasons_red"] + chk["reasons_amber"],
                         "page_joins": sum(j["action"].startswith("joined") for j in joins), "translation_mode": "english"})
            continue
        ledger = harness.read_ledger(ledger_path)
        for n in (1, 2):
            page = "%s_full__t%d" % (name, n)
            if any(r["page"] == page and r["model"] == MODEL and r["status"] == "ok" for r in ledger):
                continue
            if args.budget_inr is not None and harness.spent_inr(ledger) >= args.budget_inr:
                print("STOP: the budget of Rs %s is reached; run the same command again with a higher --budget-inr to continue." % args.budget_inr); break
            res = text_caller(MODEL, key, prompt, text)
            rec = harness.log_call(out, ledger, page, MODEL, 1, res, models, fx)
            print("%s %s: %s, Rs %.2f" % (page, MODEL, rec["status"], rec["cost_inr"]), flush=True)
        ledger = harness.read_ledger(ledger_path)
        (e1, f1), (e2, f2) = reading(ledger, out, name + "_full__t1"), reading(ledger, out, name + "_full__t2")
        chk = checker.check_document(text, e1 or "", e2 or "", known, f1, f2, joins, page_items, page_corr)
        chk["translation_mode"] = "text of the pages, joined and translated twice"
        sn = sense_check(args, out, ledger_path, models, fx, text_caller, name + "_full__sense", report.english(e1 or ""))
        if sn is not None:
            checker.apply_sense(chk, *sn)
        d = os.path.join(out, "document")
        for suffix, body in (("_source.txt", text), ("_translation_1.txt", report.english(e1 or "") or (e1 or "")), ("_translation_2.txt", report.english(e2 or "") or (e2 or ""))):
            open(os.path.join(d, name + suffix), "w", encoding="utf8").write(body)
        json.dump(chk, open(os.path.join(d, name + "_check.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
        open(os.path.join(d, name + "_document.html"), "w", encoding="utf8").write(report.build_document(name, chk, text, e1 or "", e2 or "", args.language))
        rows.append({"document": name, "pages": len(pages), "light": chk["light"], "reasons": chk["reasons_red"] + chk["reasons_amber"],
                     "page_joins": sum(j["action"].startswith("joined") for j in joins)})
    return rows


def orient_pages(args, out, work, ledger_path, models, fx, caller, osd_fn=None):
    """Step 2b: turn a page that was photographed sideways or upside down (orient.py). Returns (the work list with turned copies in place of the originals, {page id: decision}).
    The decision is saved in RUN/orientation.json so a resumed run asks nothing twice; a turned copy is written to RUN/_oriented/ and the original is kept."""
    from PIL import Image
    if getattr(args, "orient", "auto") == "off" or not work:
        return work, {}
    pf = os.path.join(out, "orientation.json")
    saved = json.load(open(pf)) if os.path.exists(pf) else {}
    od = os.path.join(out, "_oriented"); new, info = [], {}
    models_, key = models, os.environ.get(models[MODEL]["key_env"], "") if models else ""
    for pid, path, mime in work:
        d = saved.get(pid)
        if d is None:
            im = Image.open(path)
            ledger = harness.read_ledger(ledger_path)
            d = orient.check(im, caller, MODEL, key, osd_fn=osd_fn)
            mr = d.pop("model_result", None)
            if mr is not None:
                harness.log_call(out, ledger, pid + "__orient", MODEL, 1, mr, models, fx)
            d.pop("need_model", None)
            saved[pid] = d; json.dump(saved, open(pf, "w", encoding="utf8"), indent=1)
        info[pid] = d
        if d.get("rotate"):
            os.makedirs(od, exist_ok=True)
            ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".png"}.get(mime, ".png")
            q = os.path.join(od, pid + ext)
            if not os.path.exists(q):
                orient.turn(Image.open(path).convert("RGB"), d["rotate"]).save(q, **({"quality": 95} if ext == ".jpg" else {}))
            new.append((pid, q, "image/jpeg" if ext == ".jpg" else "image/png"))
            print("%s: turned %d degrees clockwise before reading (%s)" % (pid, d["rotate"], d.get("why")), flush=True)
        else:
            new.append((pid, path, mime))
            if d.get("status") in ("doubtful", "unchecked"):
                print("%s: orientation %s (%s)" % (pid, d["status"], d.get("why")), flush=True)
    return new, info


def run_pipeline(args, caller=None, text_caller=None):
    real = caller is None
    caller = caller or harness.call_gemini
    text_caller = text_caller or (lambda model, key, system, text: harness.call_gemini(model, key, system, None, None, text=text))
    out = os.path.abspath(args.out); os.makedirs(out, exist_ok=True)
    if getattr(args, "designations", None):
        import redundancy
        redundancy.DESIGNATIONS_PATH = os.path.abspath(args.designations)
    import glossary
    glossary.LANGUAGE = args.language                          # glossary/<language>_legal.csv is used when it exists
    if getattr(args, "glossary", None):
        glossary.ACTIVE_PATH = os.path.abspath(args.glossary)
    models, fx = harness.load_models(None)
    if real and not os.environ.get(models[MODEL]["key_env"]):
        sys.exit("%s is not set in this environment." % models[MODEL]["key_env"])
    pages_dir = args.input
    if os.path.isfile(args.input):
        pages_dir = os.path.join(out, "_input"); os.makedirs(pages_dir, exist_ok=True)
        shutil.copyfile(args.input, os.path.join(pages_dir, os.path.basename(args.input)))
    hargs = SimpleNamespace(pages=pages_dir, out=out, pdf_reader=args.pdf_reader, pdf_lang=args.pdf_lang, pdf_dpi=args.pdf_dpi,
                            pdf_undecided=args.pdf_undecided, pdf_no_match=args.pdf_no_match)
    work, text_pages = harness.collect_pages(hargs)           # step 2: PDFs are triaged here
    types = json.load(open(args.types)) if args.types else {}
    known = json.load(open(args.known, encoding="utf8")) if args.known else None
    ledger_path = os.path.join(out, "ledger.jsonl")

    results, readings, image_of = {}, {}, {}
    work, orientation = orient_pages(args, out, work, ledger_path, models, fx, caller, getattr(args, "osd_fn", None))
    if work:                                                   # views 1 and 2 of every page image
        vd, files = make_views(work, out)
        chooser = prompt_chooser(args, types)
        read_pages(out, vd, args, caller, prompt_for=chooser)
        ledger = harness.read_ledger(ledger_path)
        for pid in files:
            t1, f1 = reading(ledger, out, pid + "__view1"); t2, f2 = reading(ledger, out, pid + "__view2")
            readings[pid] = {"view1": t1, "view2": t2, "f1": f1, "f2": f2}
            image_of[pid] = files[pid]["original"]
            results[pid] = checker.check_page(types.get(pid, args.page_type), t1, t2, None, f1, f2, None, known)
        flagged = [p for p in files if args.third_view == "always" or (args.third_view == "auto" and results[p]["needs_third_view"])]
        if flagged and args.third_view != "off":               # view 3 only where the first two views leave something to settle
            v3 = os.path.join(out, "_views3"); os.makedirs(v3, exist_ok=True)
            for pid in flagged:
                src = files[pid]["original"]; shutil.copyfile(src, os.path.join(v3, pid + "__view3" + os.path.splitext(files[pid]["view1"])[1]))
            read_pages(out, v3, args, caller, media="ultra_high", prompt_for=chooser)
            ledger = harness.read_ledger(ledger_path)
            for pid in flagged:
                t3, f3 = reading(ledger, out, pid + "__view3"); readings[pid]["view3"] = t3
                results[pid] = checker.check_page(types.get(pid, args.page_type), readings[pid]["view1"], readings[pid]["view2"], t3, readings[pid]["f1"], readings[pid]["f2"], f3, known)
    ledger = harness.read_ledger(ledger_path)
    if text_pages:                                             # PDF pages whose own text is used: two blind translations
        translate_pages(args, out, text_pages, ledger, models, fx, text_caller)
        ledger = harness.read_ledger(ledger_path)
        for pid, p in text_pages:
            text = open(p["saved_text"], encoding="utf8").read()
            e1, _ = reading(ledger, out, pid + "__en1"); e2, _ = reading(ledger, out, pid + "__en2")
            readings[pid] = {"text": text, "english1": e1 or "", "english2": e2 or ""}
            results[pid] = checker.check_text_page(text, e1 or "", e2 or "", known)

    for pid, d in orientation.items():
        if pid in results:
            results[pid]["orientation"] = {k: d.get(k) for k in ("status", "rotate", "why")}
            if d.get("status") == "turned":
                results[pid].setdefault("notes", []).append("The page was photographed turned: it was turned %d degrees clockwise before reading (%s)." % (d["rotate"], d.get("why")))
            elif d.get("status") == "doubtful":
                results[pid]["reasons_amber"].append("the page may be photographed turned (%s): check which way up it is" % d.get("why"))
    in_doc = {pid for pages in group_documents(readings).values() for pid in pages.values()} if args.stitch != "off" else set()
    for pid in sorted(results):                                # a page of a joined document is sense-checked as part of the document (below)
        if pid not in in_doc:
            sn = sense_check(args, out, ledger_path, models, fx, text_caller, pid + "__sense", page_english(readings[pid]))
            if sn is not None:
                checker.apply_sense(results[pid], *sn)
    doc_rows = stitch_documents(args, out, readings, ledger_path, models, fx, text_caller, known, results, types)
    ledger = harness.read_ledger(ledger_path)
    cost = harness.spent_inr(ledger)
    for sub in ("checks", "report", "marksheets"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    summary = []
    for pid in sorted(results, key=lambda p: (LIGHT_ORDER[results[p]["light"]], p)):      # red first, then amber, then green
        chk, rd = results[pid], readings[pid]
        json.dump(chk, open(os.path.join(out, "checks", pid + ".json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
        img = image_of.get(pid)
        open(os.path.join(out, "report", pid + ".html"), "w", encoding="utf8").write(report.build(pid, chk, rd, img, args.language, None))
        if "text" in rd:
            a = "TRANSCRIPTION\n%s\nTRANSLATION\n%s" % (rd["text"], report.english(rd["english1"])); b = "TRANSCRIPTION\n%s\nTRANSLATION\n%s" % (rd["text"], report.english(rd["english2"]))
            names = ("English draft 1", "English draft 2")
        else:
            a, b = rd.get("view1") or "", rd.get("view2") or ""
            names = ("view 1 (image as given)", "view 2 (padded copy)")
        open(os.path.join(out, "marksheets", pid + "_marksheet.html"), "w", encoding="utf8").write(
            marksheet.build(pid, chk.get("page_type", "?"), a, b, names[0], names[1], img, rd.get("view3")))
        summary.append({"page": pid, "light": chk["light"], "page_type": chk.get("page_type"), "must_check_items": len(chk.get("must_check", [])),
                        "reasons": chk["reasons_red"] + chk["reasons_amber"], "third_view": bool(rd.get("view3")), "third_view_reason": chk.get("third_view_reason"), "orientation": (chk.get("orientation") or {}).get("status")})
    json.dump({"pages": summary, "documents": doc_rows, "estimated_cost_inr": round(cost, 2), "note": "cost is an estimate from models.json; the billing account is the truth"},
              open(os.path.join(out, "summary.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    if args.pdf:
        node = shutil.which("node")
        if not node:
            print("PDF output skipped: Node is not installed (the HTML reports are in %s/report)" % out)
        else:
            npm = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
            htmls = [os.path.join(out, "report", p["page"] + ".html") for p in summary] + [os.path.join(out, "document", d["document"] + "_document.html") for d in doc_rows if "light" in d]
            r = subprocess.run([node, os.path.join(HERE, "print_pdf.js")] + htmls, capture_output=True, text=True, env={**os.environ, "NODE_PATH": npm})
            print(r.stdout.strip() or ("PDF output failed: " + r.stderr.strip()[:200]))
    print("\n%-28s %-6s %s" % ("page", "light", "to do"))
    for s in summary:
        print("%-28s %-6s %s" % (s["page"], s["light"].upper(), "read the whole page" if s["light"] == "red" else "check the flagged items, then the must-check list" if s["light"] == "amber" else "tick the must-check list"))
    for d in doc_rows:
        print("\nWhole document %-20s %s" % (d["document"], ("%s: read it in full against the original; names, section numbers and changed sentences first" % d["light"].upper()) if "light" in d else d["status"]))
    print("\nEstimated model cost for this run: Rs %.2f (a lower bound; the billing account is the truth). Outputs: %s" % (cost, out))
    return summary


def selftest():
    import pdf_triage
    from PIL import Image
    if not all(shutil.which(t) for t in pdf_triage.TOOLS):
        print("  (poppler tools missing: pipeline wiring test skipped)"); return
    td = tempfile.mkdtemp(); inp = os.path.join(td, "in"); os.makedirs(inp)
    Image.new("RGB", (300, 200), "white").save(os.path.join(inp, "pg1.png"))
    Image.new("RGB", (123, 100), "white").save(os.path.join(inp, "zz_nodate.png"))          # a page with no date or amount: no third view
    Image.new("RGB", (311, 211), "white").save(os.path.join(inp, "zz_sideways.png"))        # Tesseract (stubbed below) says: turn 90 degrees clockwise, confidently
    Image.new("RGB", (257, 111), "white").save(os.path.join(inp, "zz_unsure.png"))          # Tesseract gives no answer: the model is asked
    lines = ["The quick brown fox jumps over the lazy dog.", "Order dated fifteen February under the heading of this code.",
             "Closing line of this invented test page only.", "Another plain sentence to give the page enough letters."]
    pdf_triage._mini_pdf(os.path.join(inp, "doc.pdf"), lines)
    Image.new("RGB", (600, 200), "white").save(os.path.join(inp, "scan.pdf"))
    Image.new("RGB", (600, 200), "white").save(os.path.join(inp, "scan2.pdf"), save_all=True, append_images=[Image.new("RGB", (600, 200), "white")])      # a two-page document
    state = {"n": 0}
    def fake(model, key, system, image, mime):
        if system == orient.PROMPT:                                                             # the orientation question: not counted with the page reads
            state["orient_asked"] = state.get("orient_asked", 0) + 1
            return {"ok": True, "attempts": 1, "text": "UPRIGHT", "ttft": 0.5, "total": 0.6, "finish": "STOP", "prompt_tokens": 300, "output_tokens": 3, "thinking_tokens": 0}
        state["n"] += 1
        if Image.open(__import__("io").BytesIO(image)).size[0] < 200:                          # the small page: no date, no amount
            return {"ok": True, "attempts": 1, "text": "TRANSCRIPTION\n1. plain line end\nTRANSLATION\nThe first line is here. The second line follows.",
                    "ttft": 1.0, "total": 2.0, "finish": "STOP", "prompt_tokens": 1000, "output_tokens": 500, "thinking_tokens": 0}
        date = "16/8/92" if (state["n"] == 2 or harness.MEDIA_RESOLUTION == "ultra_high") else "15/8/92"     # only pg1's second view (and any ultra-high view) differs
        return {"ok": True, "attempts": 1, "text": "TRANSCRIPTION\n1. dated %s end\nTRANSLATION\nThe first line is here. The second line follows." % date,
                "ttft": 1.0, "total": 2.0, "finish": "STOP", "prompt_tokens": 1000, "output_tokens": 500, "thinking_tokens": 0}
    def fake_text(model, key, system, text):
        if system.startswith("You check an English text"):                                     # the sense check (10al): nothing to report on these invented pages
            return {"ok": True, "attempts": 1, "text": "[]", "ttft": 0.5, "total": 1.0, "finish": "STOP", "prompt_tokens": 200, "output_tokens": 3, "thinking_tokens": 0}
        return {"ok": True, "attempts": 1, "text": "TRANSLATION\nThe first line is here. The second line follows.", "ttft": 1.0, "total": 2.0, "finish": "STOP",
                "prompt_tokens": 500, "output_tokens": 300, "thinking_tokens": 0}
    def fake_osd(im):
        if im.size == (311, 211):
            return {"rotate": 90, "confidence": 12.0}
        if im.size == (257, 111):
            return {"rotate": None, "confidence": None}
        return {"rotate": 0, "confidence": 30.0}
    real = pdf_triage.tesseract_read
    pdf_triage.tesseract_read = lambda png, lang: ("\n".join(lines), None)
    out = os.path.join(td, "run")
    args = argparse.Namespace(input=inp, out=out, language="English", page_type="typed", types=None, known=None, budget_inr=None, third_view="auto", pdf=False,
                              pdf_reader="tesseract", pdf_lang="eng", pdf_dpi=100, pdf_undecided="image", pdf_no_match=False, stitch="auto", orient="auto", osd_fn=fake_osd)
    try:
        s = {x["page"]: x for x in run_pipeline(args, fake, fake_text)}
        led = harness.read_ledger(os.path.join(out, "ledger.jsonl"))
        pages = {r["page"] for r in led}
        assert {"pg1__view1", "pg1__view2", "pg1__view3", "scan_p1__view1", "scan_p1__view2", "doc_p1__en1", "doc_p1__en2"} <= pages, pages
        assert "doc_p1__view1" not in pages, "a page with a good text layer must not be read as an image"
        assert "zz_nodate__view3" not in pages, "no third view for a page with no date or amount whose views agree"
        assert "scan_p1__view3" in pages, "a page that holds a date gets a third view even when the two views agree"
        assert s["pg1"]["light"] == "amber" and s["pg1"]["third_view"] and s["scan_p1"]["light"] == "amber" and s["zz_nodate"]["light"] == "green" and s["doc_p1"]["light"] == "green", s
        assert json.load(open(os.path.join(out, "checks", "scan_p1.json")))["third_view_contradicts"][0]["views_1_and_2"] == "15/8/92"
        assert {"scan2_full__t1", "scan2_full__t2"} <= pages and not any(p.startswith(("scan_full", "doc_full", "pg1_full")) for p in pages), "only a file of 2 or more pages is joined"
        for f in ("_source.txt", "_translation_1.txt", "_translation_2.txt", "_check.json", "_document.html"):
            assert os.path.exists(os.path.join(out, "document", "scan2" + f)), f
        assert open(os.path.join(out, "document", "scan2_source.txt")).read().count("dated") == 2, "the two pages are joined into one text"
        dj = json.load(open(os.path.join(out, "summary.json")))["documents"]
        assert len(dj) == 1 and dj[0]["document"] == "scan2" and dj[0]["pages"] == 2 and dj[0]["page_joins"] == 1, dj
        assert state.get("orient_asked") == 1, "the model is asked about orientation only for the page Tesseract could not settle"
        assert "zz_unsure__orient" in pages and "zz_sideways__orient" not in pages and "pg1__orient" not in pages, pages
        o = json.load(open(os.path.join(out, "orientation.json")))
        assert o["zz_sideways"]["status"] == "turned" and o["zz_sideways"]["rotate"] == 90 and o["pg1"]["status"] == "upright" and o["zz_unsure"]["status"] == "upright", o
        assert Image.open(os.path.join(out, "_oriented", "zz_sideways.png")).size == (211, 311) and Image.open(os.path.join(out, "_views", "zz_sideways__view1.png")).size == (211, 311), "read after turning"
        assert not os.path.exists(os.path.join(out, "_oriented", "pg1.png")), "an upright page is not copied"
        assert "turned 90 degrees" in " ".join(json.load(open(os.path.join(out, "checks", "zz_sideways.json")))["notes"])
        assert [x for x in json.load(open(os.path.join(out, "summary.json")))["pages"] if x["page"] == "zz_sideways"][0]["orientation"] == "turned"
        chk = json.load(open(os.path.join(out, "checks", "pg1.json")))
        assert chk["third_view_on_disagreements"][0]["third_view"] == "view 2", chk["third_view_on_disagreements"]
        for sub, ext in (("checks", ".json"), ("report", ".html"), ("marksheets", "_marksheet.html")):
            for pid in ("pg1", "scan_p1", "doc_p1", "zz_nodate"):
                assert os.path.exists(os.path.join(out, sub, pid + ext)), (sub, pid)
        assert json.load(open(os.path.join(out, "summary.json")))["pages"][0]["light"] == "amber"          # red and amber pages are listed first
        n = len(led); state["n"] = 0
        run_pipeline(args, fake, fake_text)
        assert len(harness.read_ledger(os.path.join(out, "ledger.jsonl"))) == n, "a resumed run must repeat nothing"
        args2 = argparse.Namespace(**{**vars(args), "out": os.path.join(td, "run2"), "page_type": "handwritten", "third_view": "off", "budget_inr": 0.9})
        state["n"] = 0
        s2 = {x["page"]: x for x in run_pipeline(args2, fake, fake_text)}
        args3 = argparse.Namespace(**{**vars(args), "out": os.path.join(td, "run3"), "stitch": "off", "third_view": "off"})
        run_pipeline(args3, fake, fake_text)
        assert not os.path.exists(os.path.join(td, "run3", "document")), "--stitch off writes no document"
        assert all(x["light"] != "green" for x in s2.values() if x["page"] != "doc_p1"), s2         # handwriting is never green; the budget stops the run early
        # 10ak: a handwritten two-page document: the marked prompt, the pages' own English joined (no text-only translation call), page disagreements carried to the document view
        ihw = os.path.join(td, "in_hw"); os.makedirs(ihw)
        Image.new("RGB", (300, 200), "white").save(os.path.join(ihw, "hw_p1.png")); Image.new("RGB", (301, 200), "white").save(os.path.join(ihw, "hw_p2.png"))
        hw = {"prompts": [], "text_calls": 0}
        def fake_hw(model, key, system, image, mime):
            if system == orient.PROMPT:
                return {"ok": True, "attempts": 1, "text": "UPRIGHT", "ttft": 0.5, "total": 0.6, "finish": "STOP", "prompt_tokens": 300, "output_tokens": 3, "thinking_tokens": 0}
            hw["prompts"].append(system)
            w = Image.open(__import__("io").BytesIO(image)).size[0]
            page2, view1 = w in (301, 337), w in (300, 301) and harness.MEDIA_RESOLUTION != "ultra_high"      # the ultra-high view reads like view 2 here
            if not page2:
                body = ("TRANSCRIPTION\nThe ~~victim~~ ^witness^ is escorted\nTRANSLATION\nThe ~~victim~~ ^witness^ is escorted. It ends here." if view1
                        else "TRANSCRIPTION\nThe witness is escorted\nTRANSLATION\nThe witness is escorted. It ends here.")
            else:
                d = "02/4/25" if view1 else "9/4/25"
                body = "TRANSCRIPTION\n1. dated %s end\nTRANSLATION\nDated %s here. Sometimes <doubtful: written 'when', likely meant 'sometimes'> he came." % (d, d)
            return {"ok": True, "attempts": 1, "text": body, "ttft": 1.0, "total": 2.0, "finish": "STOP", "prompt_tokens": 1000, "output_tokens": 500, "thinking_tokens": 0}
        hw["sense_calls"] = 0
        def fake_hw_text(model, key, system, text):
            if system.startswith("You check an English text"):
                hw["sense_calls"] += 1
                body = json.dumps([{"quote": "Sometimes <doubtful: written 'when', likely meant 'sometimes'> he came", "problem": "doubtful", "severity": "low"},
                                   {"quote": "a sentence the text does not contain", "problem": "invented", "severity": "high"}])
                return {"ok": True, "attempts": 1, "text": "```json\n" + body + "\n```", "ttft": 0.5, "total": 1.0, "finish": "STOP", "prompt_tokens": 200, "output_tokens": 30, "thinking_tokens": 0}
            hw["text_calls"] += 1
            return {"ok": True, "attempts": 1, "text": "TRANSLATION\nx.", "ttft": 1.0, "total": 2.0, "finish": "STOP", "prompt_tokens": 500, "output_tokens": 300, "thinking_tokens": 0}
        ah = argparse.Namespace(**{**vars(args), "input": ihw, "out": os.path.join(td, "run_hw"), "page_type": "handwritten", "third_view": "auto", "language": "Assamese"})
        run_pipeline(ah, fake_hw, fake_hw_text)
        assert hw["prompts"] and all("~~word~~" in x for x in hw["prompts"]), "every handwritten page is read with the marked prompt"
        assert hw["text_calls"] == 0, "a handwritten document is not translated from its joined text"
        assert hw["sense_calls"] == 1, "one sense check of the joined English, no more"
        dj = json.load(open(os.path.join(td, "run_hw", "document", "hw_check.json")))
        assert dj["translation_mode"].startswith("english") and dj["light"] == "amber", dj["translation_mode"]
        assert dj["page_disagreements"] and dj["page_disagreements"][0]["A"] == "02/4/25" and dj["page_disagreements"][0]["third_view"] == "view 2", dj["page_disagreements"]
        assert any(i["status"] == "DISAGREE" and i["type"] == "date" for i in dj["must_check"]) and dj["corrections"], dj["must_check"]
        assert any("stay unconfirmed" in r for r in dj["reasons_amber"]) and "~~victim~~" in open(os.path.join(td, "run_hw", "document", "hw_translation_1.txt")).read()
        assert [k["problem"] for k in dj["sense_flags"]] == ["doubtful"] and dj["sense_unmatched"] == 1, "a finding whose quote is not in the text is dropped and counted"
        assert any("sense check found 1" in r for r in dj["reasons_amber"]) and "may not make sense" in open(os.path.join(td, "run_hw", "document", "hw_document.html")).read()
        assert any(r["page"] == "hw_full__sense" and r["status"] == "ok" for r in harness.read_ledger(os.path.join(td, "run_hw", "ledger.jsonl")))
        ah2 = argparse.Namespace(**{**vars(ah), "out": os.path.join(td, "run_hw2"), "stitch": "text", "marks": "off"}); hw["prompts"].clear()
        run_pipeline(ah2, fake_hw, fake_hw_text)
        assert hw["text_calls"] == 2 and not any("~~word~~" in x for x in hw["prompts"]), "--stitch text and --marks off restore the old way"
        ah3 = argparse.Namespace(**{**vars(ah), "out": os.path.join(td, "run_hw3"), "sense": "off"}); hw["sense_calls"] = 0
        run_pipeline(ah3, fake_hw, fake_hw_text)
        assert hw["sense_calls"] == 0 and "sense_flags" not in json.load(open(os.path.join(td, "run_hw3", "document", "hw_check.json"))), "--sense off makes no call and adds no finding"
        assert any(r["page"] == "pg1__sense" for r in harness.read_ledger(os.path.join(out, "ledger.jsonl"))) and "sense_flags" in json.load(open(os.path.join(out, "checks", "pg1.json"))), "a single page is sense-checked on its own"
        assert json.load(open(os.path.join(td, "run_hw2", "document", "hw_check.json")))["page_disagreements"], "page disagreements are carried in this mode too"
    finally:
        pdf_triage.tesseract_read = real
    print("selftest OK (fake callers; no network, no cost)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The checked-reading pipeline (plan section 11).")
    ap.add_argument("--input"); ap.add_argument("--out", default="run_out"); ap.add_argument("--language", default="Assamese")
    ap.add_argument("--page-type", dest="page_type", choices=checker.PAGE_TYPES, help="typed or handwritten (required unless --types covers every page)")
    ap.add_argument("--types", help="JSON file {page id: typed|handwritten}"); ap.add_argument("--known", help="JSON list of confirmed names (case data: keep outside the repository)")
    ap.add_argument("--budget-inr", dest="budget_inr", type=float); ap.add_argument("--third-view", dest="third_view", choices=("auto", "off", "always"), default="auto")
    ap.add_argument("--orient", choices=("auto", "off"), default="auto", help="auto: turn a page that was photographed sideways or upside down before reading it")
    ap.add_argument("--glossary", help="a glossary CSV (see glossary/assamese_legal.csv) that replaces the one for --language; words with a settled legal meaning, notes only")
    ap.add_argument("--designations", help="a file of official titles (one per line) that replaces ocr_tests/designations.txt; used only to flag a title close to a known one")
    ap.add_argument("--stitch", choices=("auto", "off", "text", "english"), default="auto", help="auto: join the pages of each document of 2 or more pages; a typed document is translated as joined text (twice), a document with a handwritten page is the pages' own English joined (they were made with the images); text or english forces one way")
    ap.add_argument("--sense", choices=("auto", "off"), default="auto", help="auto: one text-only sense check of the English of each page or joined document (flags sentences that may not make sense; about Rs 0.1 to 0.5 each); off: none")
    ap.add_argument("--marks", choices=("auto", "on", "off"), default="auto", help="auto: handwritten pages are read with the marked prompt (crossed-out words, insertions, stamps over text, doubtful readings explained); on: every page; off: never")
    ap.add_argument("--pdf", action="store_true", help="also print the reports to PDF (needs Node and Playwright)")
    ap.add_argument("--pdf-reader", dest="pdf_reader", choices=("tesseract", "vision"), default="tesseract", help="vision sends each PDF page to Google")
    ap.add_argument("--pdf-lang", dest="pdf_lang", default="asm+eng"); ap.add_argument("--pdf-dpi", dest="pdf_dpi", type=int, default=200)
    ap.add_argument("--pdf-undecided", dest="pdf_undecided", choices=("image", "skip"), default="image"); ap.add_argument("--pdf-no-match", dest="pdf_no_match", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.input:
        if not a.page_type and not a.types:
            sys.exit("say what the pages are: --page-type typed or --page-type handwritten (a handwritten page is never green)")
        a.page_type = a.page_type or "typed"
        run_pipeline(a)
    else:
        sys.exit(__doc__)
