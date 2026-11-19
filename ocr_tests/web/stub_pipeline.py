"""The real pipeline with a fake reader: same command line, same checks, same outputs, invented text, no network, no cost. Used by the site's demo and by its tests (RD_PIPELINE=stub).

  python stub_pipeline.py --input DIR --out RUN --language Assamese --page-type handwritten

Every check, report and file is produced by pipeline.py itself; only the two model calls are replaced (demo.py says what the fake reader returns).
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
OCR = os.path.dirname(HERE)
sys.path.insert(0, OCR); sys.path.insert(0, HERE)
import checker, demo, harness, orient, pipeline

TOK = {"ok": True, "attempts": 1, "ttft": 0.1, "total": 0.2, "finish": "STOP", "prompt_tokens": 20, "output_tokens": 10, "thinking_tokens": 0}


def fake_reader(model, key, system, image, mime):
    time.sleep(float(os.environ.get("STUB_DELAY", "0")))          # lets a test cancel a job that is still running
    if system == orient.PROMPT:
        return dict(TOK, text="UPRIGHT")
    return dict(TOK, text=demo.reading(image, "~~word~~" in system, harness.MEDIA_RESOLUTION == "ultra_high"))


def fake_text(model, key, system, text):
    if system.startswith("You check an English text") and os.environ.get("STUB_SENSE_FAIL"):
        return {"ok": False, "attempts": 2, "error": "RemoteDisconnected: Remote end closed connection without response"}
    if system.startswith("You check an English text"):
        return dict(TOK, text=json.dumps([{"quote": demo.SENSE_QUOTE, "problem": "the sentence has words missing", "severity": "high"}]))
    return dict(TOK, text="TRANSLATION\n" + " ".join(text.split())[:600])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input"); ap.add_argument("--out"); ap.add_argument("--language", default="Assamese")
    ap.add_argument("--page-type", dest="page_type", default="typed", choices=checker.PAGE_TYPES)
    ap.add_argument("--types"); ap.add_argument("--known"); ap.add_argument("--budget-inr", dest="budget_inr", type=float)
    ap.add_argument("--third-view", dest="third_view", default="auto"); ap.add_argument("--orient", default="auto")
    ap.add_argument("--glossary"); ap.add_argument("--designations"); ap.add_argument("--stitch", default="auto")
    ap.add_argument("--sense", default="auto"); ap.add_argument("--marks", default="auto"); ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--pdf-reader", dest="pdf_reader", default="tesseract"); ap.add_argument("--pdf-lang", dest="pdf_lang", default="asm+eng")
    ap.add_argument("--pdf-dpi", dest="pdf_dpi", type=int, default=200); ap.add_argument("--pdf-undecided", dest="pdf_undecided", default="image")
    ap.add_argument("--pdf-no-match", dest="pdf_no_match", action="store_true")
    a = ap.parse_args(argv)
    a.pdf = False                                              # the stub makes no PDF reports
    a.osd_fn = lambda im: {"rotate": 0, "confidence": 30.0}    # no Tesseract needed to say a page is upright
    if os.environ.get("STUB_FAIL"):                                # lets a test see a failed job and its retry
        print("STUB: failing on purpose. key AIza" + "x" * 30 + " in " + os.path.abspath(a.out), flush=True)
        sys.exit(2)
    print("STUB: invented readings, no model is called", flush=True)
    pipeline.run_pipeline(a, fake_reader, fake_text)


if __name__ == "__main__":
    main()
