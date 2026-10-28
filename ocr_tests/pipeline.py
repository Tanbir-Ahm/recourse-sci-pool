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
  view 3   the image again at ultra-high detail, ONLY if the checker flags the page (--third-view auto); it is used as a tiebreak hint
Then checker.py sets a traffic light, redundancy.py adds the checks that need no model, and report.py / marksheet.py write one report
and one marking sheet per page. The light is a reading order, never permission to skip reading a page: a person reads every page in full for now.
Page type is typed or handwritten (--page-type for all pages, --types FILE.json for {"page id": "handwritten"}). A handwritten page is never green.
Outputs in RUN: ledger.jsonl (every call, cost an ESTIMATE), checks/<page>.json, report/<page>.html (+ .pdf with --pdf), marksheets/<page>_marksheet.html,
summary.json. All of it except the ledger holds page text or images: CASE DATA, keep RUN outside the repository.
Cost: about Rs 1 to 1.5 per read logged (the real bill has run 1.5 to 2 times higher). --budget-inr stops the run before a call that would pass it;
a stopped run is resumed by running the same command again (finished calls are skipped). Cloud Vision for the PDF match (--pdf-reader vision) is
outside the budget and sends each PDF page to Google.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, time
from types import SimpleNamespace
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checker, harness, marksheet, report

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


def read_pages(out, folder, runs_args, caller, media=None):
    """Run the harness over a folder of views (a view file is <page>__view<N>.<ext>); media sets the image-detail setting for this run only."""
    ns = SimpleNamespace(pages=folder, out=out, models_file=None, prompt=None, language=runs_args.language, runs=1, model_list=[MODEL],
                         budget_inr=runs_args.budget_inr, max_calls=None, force=False)
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


def run_pipeline(args, caller=None, text_caller=None):
    real = caller is None
    caller = caller or harness.call_gemini
    text_caller = text_caller or (lambda model, key, system, text: harness.call_gemini(model, key, system, None, None, text=text))
    out = os.path.abspath(args.out); os.makedirs(out, exist_ok=True)
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
    if work:                                                   # views 1 and 2 of every page image
        vd, files = make_views(work, out)
        read_pages(out, vd, args, caller)
        ledger = harness.read_ledger(ledger_path)
        for pid in files:
            t1, f1 = reading(ledger, out, pid + "__view1"); t2, f2 = reading(ledger, out, pid + "__view2")
            readings[pid] = {"view1": t1, "view2": t2, "f1": f1, "f2": f2}
            image_of[pid] = files[pid]["original"]
            results[pid] = checker.check_page(types.get(pid, args.page_type), t1, t2, None, f1, f2, None, known)
        flagged = [p for p in files if results[p]["needs_third_view"] and results[p].get("agreement_view1_vs_view2") and args.third_view == "auto" or args.third_view == "always"]
        if flagged and args.third_view != "off":               # view 3 only where the first two views leave something to settle
            v3 = os.path.join(out, "_views3"); os.makedirs(v3, exist_ok=True)
            for pid in flagged:
                src = files[pid]["original"]; shutil.copyfile(src, os.path.join(v3, pid + "__view3" + os.path.splitext(files[pid]["view1"])[1]))
            read_pages(out, v3, args, caller, media="ultra_high")
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
            marksheet.build(pid, chk.get("page_type", "?"), a, b, names[0], names[1], img))
        summary.append({"page": pid, "light": chk["light"], "page_type": chk.get("page_type"), "must_check_items": len(chk.get("must_check", [])),
                        "reasons": chk["reasons_red"] + chk["reasons_amber"], "third_view": bool(rd.get("view3"))})
    json.dump({"pages": summary, "estimated_cost_inr": round(cost, 2), "note": "cost is an estimate from models.json; the billing account is the truth"},
              open(os.path.join(out, "summary.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    if args.pdf:
        node = shutil.which("node")
        if not node:
            print("PDF output skipped: Node is not installed (the HTML reports are in %s/report)" % out)
        else:
            npm = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
            htmls = [os.path.join(out, "report", p["page"] + ".html") for p in summary]
            r = subprocess.run([node, os.path.join(HERE, "print_pdf.js")] + htmls, capture_output=True, text=True, env={**os.environ, "NODE_PATH": npm})
            print(r.stdout.strip() or ("PDF output failed: " + r.stderr.strip()[:200]))
    print("\n%-28s %-6s %s" % ("page", "light", "to do"))
    for s in summary:
        print("%-28s %-6s %s" % (s["page"], s["light"].upper(), "read the whole page" if s["light"] == "red" else "check the flagged items, then the must-check list" if s["light"] == "amber" else "tick the must-check list"))
    print("\nEstimated model cost for this run: Rs %.2f (a lower bound; the billing account is the truth). Outputs: %s" % (cost, out))
    return summary


def selftest():
    import pdf_triage
    from PIL import Image
    if not all(shutil.which(t) for t in pdf_triage.TOOLS):
        print("  (poppler tools missing: pipeline wiring test skipped)"); return
    td = tempfile.mkdtemp(); inp = os.path.join(td, "in"); os.makedirs(inp)
    Image.new("RGB", (300, 200), "white").save(os.path.join(inp, "pg1.png"))
    lines = ["The quick brown fox jumps over the lazy dog.", "Order dated fifteen February under the heading of this code.",
             "Closing line of this invented test page only.", "Another plain sentence to give the page enough letters."]
    pdf_triage._mini_pdf(os.path.join(inp, "doc.pdf"), lines)
    Image.new("RGB", (600, 200), "white").save(os.path.join(inp, "scan.pdf"))
    state = {"n": 0}
    def fake(model, key, system, image, mime):
        state["n"] += 1
        date = "16/8/92" if (state["n"] == 2 or harness.MEDIA_RESOLUTION == "ultra_high") else "15/8/92"     # only pg1's second view (and any ultra-high view) differs
        return {"ok": True, "attempts": 1, "text": "TRANSCRIPTION\n1. dated %s end\nTRANSLATION\nThe first line is here. The second line follows." % date,
                "ttft": 1.0, "total": 2.0, "finish": "STOP", "prompt_tokens": 1000, "output_tokens": 500, "thinking_tokens": 0}
    def fake_text(model, key, system, text):
        return {"ok": True, "attempts": 1, "text": "TRANSLATION\nThe first line is here. The second line follows.", "ttft": 1.0, "total": 2.0, "finish": "STOP",
                "prompt_tokens": 500, "output_tokens": 300, "thinking_tokens": 0}
    real = pdf_triage.tesseract_read
    pdf_triage.tesseract_read = lambda png, lang: ("\n".join(lines), None)
    out = os.path.join(td, "run")
    args = argparse.Namespace(input=inp, out=out, language="English", page_type="typed", types=None, known=None, budget_inr=None, third_view="auto", pdf=False,
                              pdf_reader="tesseract", pdf_lang="eng", pdf_dpi=100, pdf_undecided="image", pdf_no_match=False)
    try:
        s = {x["page"]: x for x in run_pipeline(args, fake, fake_text)}
        led = harness.read_ledger(os.path.join(out, "ledger.jsonl"))
        pages = {r["page"] for r in led}
        assert {"pg1__view1", "pg1__view2", "pg1__view3", "scan_p1__view1", "scan_p1__view2", "doc_p1__en1", "doc_p1__en2"} <= pages, pages
        assert "doc_p1__view1" not in pages, "a page with a good text layer must not be read as an image"
        assert "scan_p1__view3" not in pages, "view 3 only for pages that are flagged"
        assert s["pg1"]["light"] == "amber" and s["pg1"]["third_view"] and s["scan_p1"]["light"] == "green" and s["doc_p1"]["light"] == "green", s
        chk = json.load(open(os.path.join(out, "checks", "pg1.json")))
        assert chk["third_view_on_disagreements"][0]["third_view"] == "view 2", chk["third_view_on_disagreements"]
        for sub, ext in (("checks", ".json"), ("report", ".html"), ("marksheets", "_marksheet.html")):
            for pid in ("pg1", "scan_p1", "doc_p1"):
                assert os.path.exists(os.path.join(out, sub, pid + ext)), (sub, pid)
        assert json.load(open(os.path.join(out, "summary.json")))["pages"][0]["light"] == "amber"          # red and amber pages are listed first
        n = len(led); state["n"] = 0
        run_pipeline(args, fake, fake_text)
        assert len(harness.read_ledger(os.path.join(out, "ledger.jsonl"))) == n, "a resumed run must repeat nothing"
        args2 = argparse.Namespace(**{**vars(args), "out": os.path.join(td, "run2"), "page_type": "handwritten", "third_view": "off", "budget_inr": 0.9})
        state["n"] = 0
        s2 = {x["page"]: x for x in run_pipeline(args2, fake, fake_text)}
        assert all(x["light"] != "green" for x in s2.values() if x["page"] != "doc_p1"), s2         # handwriting is never green; the budget stops the run early
    finally:
        pdf_triage.tesseract_read = real
    print("selftest OK (fake callers; no network, no cost)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The checked-reading pipeline (plan section 11).")
    ap.add_argument("--input"); ap.add_argument("--out", default="run_out"); ap.add_argument("--language", default="Assamese")
    ap.add_argument("--page-type", dest="page_type", choices=checker.PAGE_TYPES, help="typed or handwritten (required unless --types covers every page)")
    ap.add_argument("--types", help="JSON file {page id: typed|handwritten}"); ap.add_argument("--known", help="JSON list of confirmed names (case data: keep outside the repository)")
    ap.add_argument("--budget-inr", dest="budget_inr", type=float); ap.add_argument("--third-view", dest="third_view", choices=("auto", "off", "always"), default="auto")
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
