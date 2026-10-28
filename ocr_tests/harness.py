"""Run page images through reader models and keep an honest ledger of time, tokens and cost.

No case data belongs in this folder. Page images, outputs and the ledger stay OUTSIDE version control; pages are
referred to by an ID only (for example A01 = group A page 1; the file is A01.png), never by name.

  export GEMINI_API_KEY=...      # set in the environment's secrets; never pasted in chat, never printed
  python harness.py --pages PAGES_DIR --out RUN_DIR --models gemini-4-argon,gemini-3.7-flash --runs 2 \
                    --language Assamese --budget-inr 150
  python harness.py --pages PAGES_DIR ...   PAGES_DIR may also hold PDFs: each PDF page goes through step 2 (pdf_triage.py) first. A page with a clean
                    text layer is NOT sent to a model: its exact text is saved to RUN_DIR/_text and logged as model "text-layer", cost 0.
                    Any other page is rendered to RUN_DIR/_pages and read like an image. Options: --pdf-reader tesseract|vision (vision sends
                    each PDF page to Google), --pdf-lang asm+eng, --pdf-dpi 200, --pdf-undecided image|skip, --pdf-no-match.
  python harness.py --report RUN_DIR/ledger.jsonl
  python harness.py --selftest          # wiring test with a fake caller; no network, no cost

Every call (including failed ones) is appended to RUN_DIR/ledger.jsonl with its time, tokens, estimated cost and why it
ended. The run stops before a call that would take the estimated spend past --budget-inr. Outputs are saved as
RUN_DIR/<page>/<model>/run<N>.txt; combinations already done are skipped, so a stopped run can be continued.
Cost is an ESTIMATE from models.json; the billing account is the truth.
"""
import argparse, base64, json, os, re, shutil, statistics, sys, tempfile, time, unicodedata, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def load_models(path=None):
    cfg = json.load(open(path or os.path.join(HERE, "models.json")))
    return cfg["models"], float(cfg.get("usd_to_inr", 96))


def cost_usd(model_cfg, prompt_tokens, output_tokens, thinking_tokens):
    """Thinking tokens are billed as output tokens."""
    return (prompt_tokens * model_cfg["price_in"] + (output_tokens + thinking_tokens) * model_cfg["price_out"]) / 1e6


def split_output(text):
    """Return (transcription, translation). The heading must be the uppercase word TRANSLATION."""
    hits = list(re.finditer(r"TRANSLATION", text))
    if not hits:
        return text, ""
    h = hits[-1]
    return text[:h.start()], text[h.end():].lstrip("*:# \n-")


MEDIA_RESOLUTION = None               # set by --media-resolution: low, medium, high or ultra_high (a per-image setting, sent on the v1alpha API)


def call_gemini(model, key, system, image_bytes, mime, max_tokens=32768, tries=3, timeout=300, text=None):
    """One streaming call. Returns a dict; never raises. Time to first token and total time are measured."""
    if text is not None:                                     # a text-only call (translating a PDF's own text layer): no image
        parts = [{"text": text}]
    else:
        image_part = {"inline_data": {"mime_type": mime, "data": base64.b64encode(image_bytes).decode()}}
        if MEDIA_RESOLUTION:
            image_part["media_resolution"] = {"level": "media_resolution_" + MEDIA_RESOLUTION}
        parts = [{"text": "Transcribe and translate this page."}, image_part]
    body = {"contents": [{"role": "user", "parts": parts}],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens}}
    api = "v1alpha" if (MEDIA_RESOLUTION and text is None) else "v1beta"
    url = f"https://generativelanguage.googleapis.com/{api}/models/{model}:streamGenerateContent?alt=sse"
    rec = {"attempts": 0}
    for attempt in range(tries):
        rec["attempts"] += 1
        req = urllib.request.Request(url, json.dumps(body).encode(), {"x-goog-api-key": key, "Content-Type": "application/json"})
        t0 = time.perf_counter(); ttft = None; text = ""; usage = {}; finish = None
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for raw in resp:
                    line = raw.decode("utf8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    d = json.loads(line[5:])
                    for c in d.get("candidates", []):
                        finish = c.get("finishReason", finish)
                        for p in c.get("content", {}).get("parts", []):
                            if p.get("text") and not p.get("thought"):
                                if ttft is None:
                                    ttft = time.perf_counter() - t0
                                text += p["text"]
                    if d.get("usageMetadata"):
                        usage = d["usageMetadata"]
            rec.update(ok=True, text=text, ttft=ttft, total=time.perf_counter() - t0, finish=finish,
                       prompt_tokens=usage.get("promptTokenCount", 0), output_tokens=usage.get("candidatesTokenCount", 0),
                       thinking_tokens=usage.get("thoughtsTokenCount", 0))
            return rec
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf8", "replace")[:160]
            rec.update(ok=False, error=f"HTTP {e.code}: {msg}")
            if e.code in (429, 503) and attempt < tries - 1:
                time.sleep(20 * (attempt + 1)); continue
            return rec
        except (TimeoutError, OSError) as e:
            rec.update(ok=False, error=f"{type(e).__name__}: {str(e)[:120]}")
            if attempt < tries - 1:
                time.sleep(10)
    return rec


def read_ledger(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path) if l.strip()]


def spent_inr(ledger):
    return sum(r.get("cost_inr", 0) for r in ledger)


def log_call(out, ledger, page, model, run_no, res, models, fx):
    """Record one finished call: its status, tokens and estimated cost go to RUN/ledger.jsonl and its text to RUN/<page>/<model>/run<N>.txt.
    An incomplete reading is saved under a different name so it is never mistaken for a good one. Returns the ledger record."""
    rec = {"page": page, "model": model, "run": run_no, "ok": bool(res.get("ok")), "attempts": res.get("attempts", 1),
           "ttft": res.get("ttft"), "total": res.get("total"), "finish": res.get("finish"),
           "prompt_tokens": res.get("prompt_tokens", 0), "output_tokens": res.get("output_tokens", 0),
           "thinking_tokens": res.get("thinking_tokens", 0), "error": res.get("error"), "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    usd = cost_usd(models[model], rec["prompt_tokens"], rec["output_tokens"], rec["thinking_tokens"])
    rec["cost_usd"] = round(usd, 6); rec["cost_inr"] = round(usd * fx, 4)
    if res.get("ok") and res.get("finish") != "STOP":       # a stream that ends with no finish reason was cut off
        rec["status"] = f"INCOMPLETE ({res.get('finish')}): do not trust this reading"
    elif res.get("ok") and not res.get("text", "").strip():
        rec["status"] = "EMPTY"
    else:
        rec["status"] = "ok" if res.get("ok") else "failed"
    if res.get("ok") and res.get("text", "").strip():
        outfile = os.path.join(out, page, model, f"run{run_no}.txt")
        if rec["status"] != "ok":
            outfile = outfile.replace(".txt", ".INCOMPLETE.txt")
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        open(outfile, "w", encoding="utf8").write(res["text"]); rec["outfile"] = os.path.relpath(outfile, out)
    with open(os.path.join(out, "ledger.jsonl"), "a", encoding="utf8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    ledger.append(rec)
    return rec


def sniff(path):
    """What a file really is, from its first bytes, whatever its name says: 'pdf', an image MIME type, or None. A PDF saved with a .php, .aspx or no extension
    (a download link that serves a PDF) is still a PDF."""
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return None
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"\x89PNG"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def collect_pages(args):
    """The pages to work on: (page id, image path, mime) to read with a model, and (page id, triage record) for PDF pages whose own text
    layer is good (step 2, pdf_triage.py). PDF pages are named <file>_p<N>. The triage result is saved in RUN_DIR/triage so a resumed run does not repeat it."""
    work, text_pages, seen = [], [], {}
    for fname in sorted(os.listdir(args.pages)):
        stem = os.path.splitext(fname)[0]
        path = os.path.join(args.pages, fname)
        kind = sniff(path) if os.path.isfile(path) else None
        if kind is None:
            if os.path.isfile(path):
                print("SKIPPED %s: not a PDF or a PNG, JPEG or WebP image (checked by content, not by name)" % fname, flush=True)
            continue
        if kind != "pdf":
            work.append((stem, path, kind))
        else:
            sys.path.insert(0, HERE)
            import pdf_triage
            seen[stem] = seen.get(stem, 0) + 1
            name = stem if seen[stem] == 1 else "%s_%d" % (stem, seen[stem])
            tri_path = os.path.join(args.out, "triage", name + ".json")
            if os.path.exists(tri_path):
                res = json.load(open(tri_path))
            else:
                try:
                    res = pdf_triage.triage(path, getattr(args, "pdf_lang", "asm+eng"), getattr(args, "pdf_dpi", 200), os.path.join(args.out, "_text"),
                                            os.path.join(args.out, "_pages"), not getattr(args, "pdf_no_match", False), name, getattr(args, "pdf_reader", "tesseract"))
                except RuntimeError as e:
                    sys.exit("PDF %s: %s" % (fname, e))
                os.makedirs(os.path.dirname(tri_path), exist_ok=True)
                json.dump(res, open(tri_path, "w"), indent=1)
            for p in res["per_page"]:
                pid = "%s_p%d" % (name, p["page"])
                print("PDF %s page %d: %s (%s)" % (fname, p["page"], p["verdict"], p["reasons"][0]), flush=True)
                if p["verdict"] == "use_text_layer":
                    text_pages.append((pid, p))
                elif p["verdict"] == "person_decides" and getattr(args, "pdf_undecided", "image") == "skip":
                    print("  skipped: a person decides (--pdf-undecided skip)")
                elif p.get("saved_image"):
                    work.append((pid, p["saved_image"], "image/png"))
                else:
                    sys.exit("PDF %s page %d could not be rendered to an image; see %s" % (fname, p["page"], tri_path))
    return work, text_pages


def run(args, caller=call_gemini):
    models, fx = load_models(args.models_file)
    prompt = open(args.prompt or os.path.join(HERE, "prompts", "read_translate.txt")).read().format(language=args.language)
    os.makedirs(args.out, exist_ok=True)
    ledger_path = os.path.join(args.out, "ledger.jsonl")
    ledger = read_ledger(ledger_path)
    work, text_pages = collect_pages(args)
    for pid, p in text_pages:              # a good text layer is the reading: no model call, no cost
        if not any(r["page"] == pid and r["model"] == "text-layer" for r in ledger):
            rec = {"page": pid, "model": "text-layer", "run": 1, "ok": True, "attempts": 1, "ttft": None, "total": 0.0, "finish": "n/a",
                   "prompt_tokens": 0, "output_tokens": 0, "thinking_tokens": 0, "error": None, "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "cost_usd": 0.0, "cost_inr": 0.0, "status": "text layer", "outfile": os.path.relpath(p["saved_text"], args.out), "note": p["reasons"][0]}
            with open(ledger_path, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            ledger.append(rec)
    calls = 0
    for page, img_path, mime in work:
        img = open(img_path, "rb").read()
        for model in args.model_list:
            if model not in models:
                sys.exit(f"{model} is not in models.json")
            key = os.environ.get(models[model]["key_env"], "")
            if not key and caller is call_gemini:
                sys.exit(f"{models[model]['key_env']} is not set in this environment.")
            for run_no in range(1, args.runs + 1):
                outfile = os.path.join(args.out, page, model, f"run{run_no}.txt")
                done = [r for r in ledger if (r["page"], r["model"], r["run"]) == (page, model, run_no) and r["status"] not in ("failed", "EMPTY")]
                if done and not args.force:
                    continue                    # already paid for (a good or an incomplete reading); only failed calls are retried
                prev = [r["cost_inr"] for r in ledger if r["model"] == model and r.get("cost_inr")]
                expected = statistics.median(prev) if prev else 0
                if args.budget_inr is not None and spent_inr(ledger) + expected > args.budget_inr:
                    print(f"STOP: estimated spend Rs {spent_inr(ledger):.2f} + next call about Rs {expected:.2f} would pass the budget of Rs {args.budget_inr}.")
                    return ledger
                if args.max_calls is not None and calls >= args.max_calls:
                    print(f"STOP: reached --max-calls {args.max_calls}."); return ledger
                res = caller(model, key, prompt, img, mime)
                calls += 1
                rec = log_call(args.out, ledger, page, model, run_no, res, models, fx)
                print(f"{page} {model} run {run_no}: {rec['status']}, {rec['total'] and round(rec['total'],1)} s, Rs {rec['cost_inr']:.2f} (running total Rs {spent_inr(ledger):.2f})", flush=True)
    return ledger


def report(path):
    ledger = read_ledger(path)
    by = {}
    for r in ledger:
        by.setdefault(r["model"], []).append(r)
    print(f"{'model':26} calls  ok  incomplete/failed   median time   median cost (Rs)   total (Rs)")
    for m, rs in by.items():
        good = [r for r in rs if r["status"] in ("ok", "text layer")]
        bad = len(rs) - len(good)
        t = statistics.median(r["total"] for r in good) if good else float("nan")
        c = statistics.median(r["cost_inr"] for r in good) if good else float("nan")
        print(f"{m:26} {len(rs):5d} {len(good):4d} {bad:10d}      {t:8.1f} s   {c:14.2f}   {sum(r['cost_inr'] for r in rs):10.2f}")
    print(f"\nESTIMATED total spend: Rs {spent_inr(ledger):.2f} (from models.json prices; the billing account is the truth)")


def selftest():
    d = tempfile.mkdtemp(); pages = os.path.join(d, "pages"); os.makedirs(pages)
    for pid in ("T01", "T02"):
        open(os.path.join(pages, pid + ".png"), "wb").write(b"\x89PNG fake")
    state = {"n": 0}
    def fake(model, key, system, image, mime):
        state["n"] += 1
        if model == "gemini-3.5-flash" and state["n"] % 2 == 0:
            return {"ok": False, "attempts": 3, "error": "HTTP 503: overloaded"}
        if model == "gemini-3.1-pro-preview":
            return {"ok": True, "attempts": 1, "text": "TRANSCRIPTION\n1. x\nTRANSLATION\n1. y", "ttft": 30.0, "total": 31.0, "finish": "MAX_TOKENS",
                    "prompt_tokens": 1000, "output_tokens": 1000, "thinking_tokens": 31000}
        return {"ok": True, "attempts": 1, "text": "TRANSCRIPTION\n1. a\nTRANSLATION\n1. b", "ttft": 1.0, "total": 2.0, "finish": "STOP",
                "prompt_tokens": 1000, "output_tokens": 500, "thinking_tokens": 0}
    ns = argparse.Namespace(pages=pages, out=os.path.join(d, "out"), models_file=None, prompt=None, language="Assamese", runs=1,
                            model_list=["gemini-4-argon", "gemini-3.5-flash", "gemini-3.1-pro-preview"], budget_inr=None, max_calls=None, force=False)
    os.environ["GEMINI_API_KEY"] = "fake"
    led = run(ns, fake)
    assert len(led) == 6, led
    st = {(r["page"], r["model"]): r["status"] for r in led}
    assert st[("T01", "gemini-4-argon")] == "ok" and st[("T02", "gemini-3.1-pro-preview")].startswith("INCOMPLETE"), st
    assert any(r["status"] == "failed" for r in led)
    models, fx = load_models()
    expect = (1000 * 2.0 + 500 * 10.0) / 1e6 * fx
    assert abs([r for r in led if r["model"] == "gemini-4-argon"][0]["cost_inr"] - expect) < 1e-3
    pro = [r for r in led if r["model"] == "gemini-3.1-pro-preview"][0]
    assert pro["cost_inr"] > 20, "thinking tokens must be billed as output"
    n_before = len(led); led2 = run(ns, fake)           # resume: only the one failed call is repeated
    assert len(led2) == n_before + 1, (n_before, len(led2))
    ns2 = argparse.Namespace(**{**vars(ns), "out": os.path.join(d, "out2"), "budget_inr": 0.9, "model_list": ["gemini-4-argon"]})
    led3 = run(ns2, fake)
    assert len(led3) == 1 and spent_inr(led3) < 0.9, led3          # the second call would pass the budget, so it is not made
    assert os.path.exists(os.path.join(d, "out", "T01", "gemini-3.1-pro-preview", "run1.INCOMPLETE.txt"))
    assert split_output("TRANSCRIPTION\nx\nTRANSLATION\ny") == ("TRANSCRIPTION\nx\n", "y")
    # PDFs through step 2 (invented files built here; the picture reader is replaced so the result does not depend on Tesseract)
    sys.path.insert(0, HERE)
    import pdf_triage
    if all(shutil.which(t) for t in pdf_triage.TOOLS):
        d2 = tempfile.mkdtemp(); pg = os.path.join(d2, "pages"); os.makedirs(pg)
        lines = ["The quick brown fox jumps over the lazy dog.", "Order dated fifteen February under the heading of this code.",
                 "Closing line of this invented test page only.", "Another plain sentence to give the page enough letters."]
        pdf_triage._mini_pdf(os.path.join(pg, "doc.pdf"), lines)
        have_pil = True
        try:
            from PIL import Image, ImageDraw
            im = Image.new("RGB", (600, 200), "white"); ImageDraw.Draw(im).text((20, 80), "picture only", fill="black"); im.save(os.path.join(pg, "scan.pdf"))
        except ImportError:
            have_pil = False
        shutil.copyfile(os.path.join(pg, "doc.pdf"), os.path.join(pg, "disguised.php"))          # a PDF served under another name
        open(os.path.join(pg, "notes.txt"), "w").write("not a page")
        real = pdf_triage.tesseract_read
        pdf_triage.tesseract_read = lambda png, lang: ("\n".join(lines), None)
        try:
            ns3 = argparse.Namespace(pages=pg, out=os.path.join(d2, "out"), models_file=None, prompt=None, language="English", runs=1, model_list=["gemini-4-argon"],
                                     budget_inr=None, max_calls=None, force=False, pdf_reader="tesseract", pdf_lang="eng", pdf_dpi=100, pdf_undecided="image", pdf_no_match=False)
            led4 = run(ns3, fake)
            rows = {(r["page"], r["model"]): r for r in led4}
            assert rows[("doc_p1", "text-layer")]["status"] == "text layer" and rows[("doc_p1", "text-layer")]["cost_inr"] == 0, rows
            assert ("doc_p1", "gemini-4-argon") not in rows, "a page with a good text layer must not be sent to a model"
            assert rows[("disguised_p1", "text-layer")]["status"] == "text layer", "a PDF is recognised by its content, not its file name"
            assert not any(r["page"].startswith("notes") for r in led4), "a file that is neither a PDF nor an image is skipped"
            assert os.path.exists(os.path.join(d2, "out", "_text", "doc_p1.txt")) and os.path.exists(os.path.join(d2, "out", "triage", "doc.json"))
            if have_pil:
                assert rows[("scan_p1", "gemini-4-argon")]["status"] == "ok", "a picture-only page is read by the model"
            n = len(led4); assert len(run(ns3, fake)) == n, "a resumed run must not repeat anything"
            ns4 = argparse.Namespace(**{**vars(ns3), "out": os.path.join(d2, "out_skip"), "pdf_no_match": True, "pdf_undecided": "skip"})
            led6 = run(ns4, fake)
            assert not any(r["page"] == "doc_p1" for r in led6), "with --pdf-undecided skip an undecided page is left out"
        finally:
            pdf_triage.tesseract_read = real
    else:
        print("  (poppler tools missing: PDF wiring test skipped)")
    print("selftest OK (fake caller; no network, no cost)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages"); ap.add_argument("--out", default="run_out"); ap.add_argument("--models", default="gemini-4-argon,gemini-3.7-flash")
    ap.add_argument("--runs", type=int, default=2); ap.add_argument("--language", default="Assamese"); ap.add_argument("--prompt")
    ap.add_argument("--models-file", dest="models_file"); ap.add_argument("--budget-inr", type=float, dest="budget_inr"); ap.add_argument("--max-calls", type=int, dest="max_calls")
    ap.add_argument("--force", action="store_true"); ap.add_argument("--report"); ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--media-resolution", dest="media_resolution", choices=("low", "medium", "high", "ultra_high"), help="the model's image-detail setting (argon already uses high by default; ultra_high costs about 1,100 more input tokens)")
    ap.add_argument("--pdf-reader", dest="pdf_reader", choices=("tesseract", "vision"), default="tesseract", help="reader for the PDF match check; vision sends each PDF page to Google")
    ap.add_argument("--pdf-lang", dest="pdf_lang", default="asm+eng"); ap.add_argument("--pdf-dpi", dest="pdf_dpi", type=int, default=200)
    ap.add_argument("--pdf-undecided", dest="pdf_undecided", choices=("image", "skip"), default="image", help="what to do with a PDF page where a person must decide")
    ap.add_argument("--pdf-no-match", dest="pdf_no_match", action="store_true", help="skip the comparison of the text layer with the picture")
    a = ap.parse_args()
    if a.media_resolution:
        MEDIA_RESOLUTION = a.media_resolution
    if a.selftest: selftest()
    elif a.report: report(a.report)
    elif a.pages:
        a.model_list = a.models.split(","); run(a)
    else: sys.exit("need --pages (or --report / --selftest)")
