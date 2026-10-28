"""Step 2 of the pipeline (plan section 11): decide, page by page, whether a PDF's own text can be used or the page must be read as a picture.

  python pdf_triage.py FILE.pdf [FILE2.pdf ...] [--lang asm+eng] [--dpi 200] [--reader tesseract|vision] [--text-out DIR] [--render-out DIR] [--no-match] > triage.json
  python pdf_triage.py --selftest

Per page the verdict is one of:
  use_text_layer   the text inside the PDF is clean and agrees with what the page shows: use it (exact and free), no OCR.
  treat_as_image   there is no usable text, or it shows signs of a broken font encoding, or it disagrees with the picture: render the page and read it.
  person_decides   the evidence is mixed or could not be gathered: a person looks.
The match with the picture is made on BASE LETTERS ONLY (vowel signs ignored), because a PDF drawn without proper Assamese shaping
shows vowel signs in the wrong places while its text is fine (the first group C file: 98% of base letters agree, 66% of words do).
The picture is read with one of two readers (--reader):
  tesseract (default)  free and local: nothing leaves this machine. Weak: 83.3% on the one good file, only 3 points above the 80% cut-off.
  vision               Google Cloud Vision: much better on clean typed pages (about 98% on the same file) but EACH PAGE IS SENT TO GOOGLE.
                       Needs GOOGLE_CLOUD_API_KEY in the environment (never printed). Use it only where the owner has allowed cloud processing.
Either way the match is a rough test on typed text, not on handwriting. Cut-offs are a first guess from two files; tune them on more files.
Needs the poppler tools (pdfinfo, pdftotext, pdffonts, pdfimages, pdftoppm). The reader is optional (without it the verdict falls back to person_decides).
The JSON holds counts and verdicts only, never page text. --text-out and --render-out write page text and page images: those are CASE DATA, keep them outside the repository.
The selftest uses invented text and files it builds itself.
"""
import argparse, base64, difflib, json, os, re, shutil, subprocess, sys, tempfile, time, unicodedata, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checker

MIN_LETTERS = 20      # fewer letters than this on a page: no usable text layer
MATCH_OK = 80.0       # base-letter agreement (percent) with the picture at or above which the text layer is trusted
MATCH_BAD = 60.0      # below this the text layer is taken not to be what the page shows
TOOLS = ("pdfinfo", "pdftotext", "pdffonts", "pdfimages", "pdftoppm")
VISION_LANG = {"asm": "as", "eng": "en", "hin": "hi", "kan": "kn", "ben": "bn", "mar": "mr", "tam": "ta", "tel": "te", "mal": "ml", "guj": "gu", "pan": "pa", "ori": "or"}


def run(cmd, timeout=180):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf8", errors="replace", timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", "%s is not installed" % cmd[0]
    except subprocess.TimeoutExpired:
        return 124, "", "%s timed out" % cmd[0]


def page_count(pdf):
    rc, out, err = run(["pdfinfo", pdf])
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if rc != 0 or not m:
        raise RuntimeError("cannot read the PDF: %s" % (err.strip() or "pdfinfo gave no page count"))
    return int(m.group(1))


def text_layer(pdf, n):
    return run(["pdftotext", "-f", str(n), "-l", str(n), "-enc", "UTF-8", pdf, "-"])[1]


def page_fonts(pdf, n):
    """Fonts used on the page: name, embedded, has a Unicode map. pdffonts prints a table; the last five columns are emb, sub, uni, object, generation."""
    rc, out, _ = run(["pdffonts", "-f", str(n), "-l", str(n), pdf])
    fonts = []
    for line in out.splitlines()[2:]:
        t = line.split()
        if len(t) >= 6 and t[-5] in ("yes", "no") and t[-3] in ("yes", "no"):
            fonts.append({"name": t[0], "embedded": t[-5] == "yes", "unicode_map": t[-3] == "yes"})
    return fonts


def page_images(pdf, n):
    rc, out, _ = run(["pdfimages", "-list", "-f", str(n), "-l", str(n), pdf])
    imgs = []
    for line in out.splitlines()[2:]:
        t = line.split()
        if len(t) >= 5 and t[3].isdigit() and t[4].isdigit():
            imgs.append({"type": t[2], "width": int(t[3]), "height": int(t[4])})
    return imgs


def analyse_text(text, fonts):
    """Signs that a text layer is junk. Returns (number of letters, dict of the signs that fired)."""
    chars = [c for c in text if not c.isspace()]
    letters = [c for c in chars if unicodedata.category(c)[0] == "L"]
    signs = {}
    if chars:
        bad = sum(c == "�" for c in chars); pua = sum(0xE000 <= ord(c) <= 0xF8FF for c in chars)
        if bad / len(chars) >= 0.01 or pua / len(chars) >= 0.02:
            signs["replacement_or_private_use_characters"] = bad + pua
        if len(chars) >= 50 and len(letters) / len(chars) < 0.3:
            signs["mostly_symbols_and_digits"] = round(len(letters) / len(chars), 2)
    if len(letters) >= 20:
        accented = sum(0xC0 <= ord(c) <= 0x17F for c in letters)
        if accented / len(letters) > 0.25:
            signs["accented_latin_letters_dominate"] = round(accented / len(letters), 2)
    words = text.split()
    if len(words) >= 10:
        starts = sum(unicodedata.category(w[0]).startswith("M") for w in words)
        if starts / len(words) > 0.03:
            signs["words_start_with_a_vowel_sign"] = round(starts / len(words), 2)
    if any(f["embedded"] and not f["unicode_map"] for f in fonts) and any(ord(c) > 127 for c in chars):
        signs["embedded_font_without_unicode_map"] = True
    return len(letters), signs


def skeleton(text):
    """Base letters only, in the comparison form of checker.norm: no vowel signs, spaces, digits or punctuation."""
    return "".join(c.lower() for c in checker.norm(text) if unicodedata.category(c)[0] == "L")


def similarity(a, b):
    """Percent of base letters that agree (100 minus edit distance over the longer text; difflib's ratio above 6000 letters)."""
    if not a or not b:
        return 0.0
    if max(len(a), len(b)) > 6000:
        return round(100 * difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), 1)
    return round(100 * (1 - checker.edit_distance(a, b) / max(len(a), len(b))), 1)


def tesseract_read(png, lang):
    if not shutil.which("tesseract"):
        return None, "Tesseract is not installed"
    rc, out, _ = run(["tesseract", "--list-langs"])
    have = set(out.split()[1:]) if rc == 0 else set()
    use = [l for l in lang.split("+") if l in have]
    if not use:
        return None, "Tesseract has none of the language data %s" % lang
    rc, out, err = run(["tesseract", png, "stdout", "-l", "+".join(use)], timeout=300)
    return (out, None) if rc == 0 else (None, "Tesseract failed: %s" % err.strip()[:120])


def vision_read(png, lang):
    """Read a page image with Google Cloud Vision. The key comes from the environment and is never printed or put in the URL."""
    key = os.environ.get("GOOGLE_CLOUD_API_KEY")
    if not key:
        return None, "GOOGLE_CLOUD_API_KEY is not set"
    hints = [VISION_LANG[l] for l in lang.split("+") if l in VISION_LANG]
    body = {"requests": [{"image": {"content": base64.b64encode(open(png, "rb").read()).decode()},
                          "features": [{"type": "DOCUMENT_TEXT_DETECTION"}], "imageContext": {"languageHints": hints}}]}
    req = urllib.request.Request("https://vision.googleapis.com/v1/images:annotate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "X-Goog-Api-Key": key})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                resp = json.load(r)["responses"][0]
            if "error" in resp:
                return None, "Cloud Vision error: %s" % str(resp["error"].get("message", ""))[:100]
            return resp.get("fullTextAnnotation", {}).get("text", ""), None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 2:
                time.sleep(3 * (attempt + 1)); continue
            return None, "Cloud Vision failed: HTTP %d" % e.code
        except Exception as e:
            if attempt < 2:
                time.sleep(3); continue
            return None, "Cloud Vision failed: %s" % type(e).__name__
    return None, "Cloud Vision failed"


def decide(n_letters, n_images, signs, match):
    """The verdict for one page and the reasons, in plain words."""
    if n_letters < MIN_LETTERS:
        if n_images:
            return "treat_as_image", ["no usable text layer (%d letters) and the page holds a picture" % n_letters]
        return "person_decides", ["no usable text and no picture: a blank or drawn page?"]
    if len(signs) >= 2:
        return "treat_as_image", ["the text layer shows %d signs of a broken font encoding (%s)" % (len(signs), ", ".join(sorted(signs)))]
    weak = (" (one sign of a problem: %s)" % ", ".join(signs)) if signs else ""
    if match is None:
        return "person_decides", ["the text layer looks clean%s but could not be compared with the picture" % weak]
    if match >= MATCH_OK:
        return "use_text_layer", ["the text layer agrees with the picture on %.1f%% of base letters%s" % (match, weak)]
    if match < MATCH_BAD:
        return "treat_as_image", ["the text layer agrees with the picture on only %.1f%% of base letters" % match]
    return "person_decides", ["the text layer agrees with the picture on %.1f%% of base letters: between %.0f%% and %.0f%%" % (match, MATCH_BAD, MATCH_OK)]


def triage(pdf, lang="asm+eng", dpi=200, text_out=None, render_out=None, match=True, stem=None, reader="tesseract"):
    missing = [t for t in TOOLS if not shutil.which(t)]
    if missing:
        raise RuntimeError("missing tools: %s (install poppler-utils)" % ", ".join(missing))
    stem = stem or os.path.splitext(os.path.basename(pdf))[0]
    pages, notes = [], []
    for n in range(1, page_count(pdf) + 1):
        text = text_layer(pdf, n); fonts = page_fonts(pdf, n); imgs = page_images(pdf, n)
        n_letters, signs = analyse_text(text, fonts)
        m, how, png = None, None, None
        want_png = match or render_out
        with tempfile.TemporaryDirectory() as td:
            if want_png:
                prefix = os.path.join(td, "p")
                rc, _, err = run(["pdftoppm", "-r", str(dpi), "-f", str(n), "-l", str(n), "-png", "-singlefile", pdf, prefix])
                png = prefix + ".png" if rc == 0 and os.path.exists(prefix + ".png") else None
                if not png:
                    notes.append("page %d: could not render (%s)" % (n, err.strip()[:80]))
            if match and png and n_letters >= MIN_LETTERS:
                reading, why = (vision_read if reader == "vision" else tesseract_read)(png, lang)
                if reading is None:
                    how = why
                else:
                    m = similarity(skeleton(text), skeleton(reading)); how = ("Cloud Vision (%s)" if reader == "vision" else "Tesseract (%s)") % lang
            elif match and n_letters >= MIN_LETTERS:
                how = "no rendered page to read"
            verdict, reasons = decide(n_letters, len(imgs), signs, m)
            rec = {"page": n, "verdict": verdict, "reasons": reasons, "text_letters": n_letters, "images": imgs,
                   "fonts": fonts, "junk_signs": signs, "match_percent": m, "match_reader": how}
            if text_out and verdict == "use_text_layer":
                os.makedirs(text_out, exist_ok=True); p = os.path.join(text_out, "%s_p%d.txt" % (stem, n))
                open(p, "w", encoding="utf8").write(text); rec["saved_text"] = p
            if render_out and verdict != "use_text_layer" and png:
                os.makedirs(render_out, exist_ok=True); p = os.path.join(render_out, "%s_p%d.png" % (stem, n))
                shutil.copyfile(png, p); rec["saved_image"] = p
        pages.append(rec)
    kinds = sorted({p["verdict"] for p in pages})
    return {"file": os.path.basename(pdf), "pages": len(pages), "verdict": kinds[0] if len(kinds) == 1 else "mixed: handle page by page",
            "per_page": pages, "notes": notes,
            "thresholds": {"min_letters": MIN_LETTERS, "match_ok": MATCH_OK, "match_bad": MATCH_BAD, "status": "first guess from two files"}}


def _mini_pdf(path, lines):
    """A one-page PDF with real Helvetica text, built by hand so the selftest needs nothing else."""
    esc = lambda s: s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = "BT /F1 16 Tf 50 780 Td 22 TL " + " ".join("(%s) Tj T*" % esc(l) for l in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            "<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    out = b"%PDF-1.4\n"; offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out)); out += ("%d 0 obj\n%s\nendobj\n" % (i, o)).encode("latin-1")
    x = len(out)
    out += ("xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)).encode() + b"".join(("%010d 00000 n \n" % o).encode() for o in offs)
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)).encode()
    open(path, "wb").write(out)


def selftest():
    # signs of junk (invented strings)
    n, s = analyse_text("অসমীয়া ভাষা পৰীক্ষাৰ বাবে অৰ্থহীন পাঠ এই নথিখনৰ বাক্যসমূহ ইচ্ছাকৃতভাৱে", [])
    assert not s and n > 20, (n, s)
    n, s = analyse_text("ÃÅÆÇÈÉÊËÌÍÎÏ ÐÑÒÓÔÕÖØÙÚÛÜ ÝÞßÀÁÂÃÄÅÆÇ", [])
    assert "accented_latin_letters_dominate" in s, s
    n, s = analyse_text(" ".join(["ি" + "ক"] * 12) + " কথা", [])
    assert "words_start_with_a_vowel_sign" in s, s
    n, s = analyse_text("abc�" * 20, [])
    assert "replacement_or_private_use_characters" in s, s
    n, s = analyse_text("Ã" * 30, [{"name": "X", "embedded": True, "unicode_map": False}])
    assert len(s) >= 2, s
    # base-letter comparison ignores vowel-sign placement, spaces, digits and the Assamese ra
    assert similarity(skeleton("ঘুৰমা লিপিৰা 123"), skeleton("ঘুরমা লপিরা")) == 100.0
    assert similarity(skeleton("abcdef"), skeleton("xyzxyz")) < 20
    # the decision rules
    assert decide(5, 1, {}, None)[0] == "treat_as_image"
    assert decide(5, 0, {}, None)[0] == "person_decides"
    assert decide(100, 0, {"a": 1, "b": 1}, 99)[0] == "treat_as_image"
    assert decide(100, 0, {}, None)[0] == "person_decides"
    assert decide(100, 0, {}, 85.0)[0] == "use_text_layer"
    assert decide(100, 0, {"a": 1}, 85.0)[0] == "use_text_layer"
    assert decide(100, 0, {}, 70.0)[0] == "person_decides"
    assert decide(100, 0, {}, 40.0)[0] == "treat_as_image"
    # the Vision reader: no key means a clear message and no network call
    saved = os.environ.pop("GOOGLE_CLOUD_API_KEY", None)
    try:
        assert vision_read("/nonexistent.png", "asm+eng") == (None, "GOOGLE_CLOUD_API_KEY is not set")
    finally:
        if saved is not None:
            os.environ["GOOGLE_CLOUD_API_KEY"] = saved
    assert VISION_LANG["asm"] == "as" and VISION_LANG["eng"] == "en"
    # real files, built here
    with tempfile.TemporaryDirectory() as td:
        if all(shutil.which(t) for t in TOOLS):
            good = os.path.join(td, "text.pdf")
            _mini_pdf(good, ["The quick brown fox jumps over the lazy dog.", "Order dated fifteen February under the heading of this code.",
                             "Closing line of this invented test page only.", "Another plain sentence to give the page enough letters."])
            r = triage(good, lang="eng", match=False)
            assert r["pages"] == 1 and r["per_page"][0]["verdict"] == "person_decides" and r["per_page"][0]["text_letters"] > 100, r
            if shutil.which("tesseract") and "eng" in run(["tesseract", "--list-langs"])[1].split():
                r = triage(good, lang="eng")
                assert r["per_page"][0]["verdict"] == "use_text_layer" and r["per_page"][0]["match_percent"] >= MATCH_OK, r["per_page"][0]
            try:
                from PIL import Image, ImageDraw
                img = Image.new("RGB", (600, 200), "white"); ImageDraw.Draw(img).text((20, 80), "picture only, no text layer", fill="black")
                scan = os.path.join(td, "scan.pdf"); img.save(scan)
                r = triage(scan, lang="eng", match=False)
                assert r["per_page"][0]["verdict"] == "treat_as_image" and r["per_page"][0]["images"], r
            except ImportError:
                print("  (Pillow missing: image-only file test skipped)")
            for bad in (os.path.join(td, "nothing.pdf"),):
                open(bad, "wb").write(b"not a pdf")
                try:
                    triage(bad, match=False); raise AssertionError("a broken file must raise")
                except RuntimeError:
                    pass
        else:
            print("  (poppler tools missing: file tests skipped)")
    print("selftest OK (invented text and files built here)")


def main(argv):
    ap = argparse.ArgumentParser(description="Decide per page whether a PDF's text layer can be used.")
    ap.add_argument("pdfs", nargs="*"); ap.add_argument("--lang", default="asm+eng", help="Tesseract languages for the match check")
    ap.add_argument("--dpi", type=int, default=200); ap.add_argument("--text-out"); ap.add_argument("--render-out")
    ap.add_argument("--reader", choices=("tesseract", "vision"), default="tesseract", help="vision sends every page to Google")
    ap.add_argument("--no-match", action="store_true", help="skip the comparison with the picture"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.pdfs:
        sys.exit(__doc__)
    seen, stems = {}, []
    for p in a.pdfs:                                   # two files with the same name must not overwrite each other's saved pages
        st = os.path.splitext(os.path.basename(p))[0]; seen[st] = seen.get(st, 0) + 1
        stems.append(st if seen[st] == 1 else "%s_%d" % (st, seen[st]))
    res = [triage(p, a.lang, a.dpi, a.text_out, a.render_out, not a.no_match, st, a.reader) for p, st in zip(a.pdfs, stems)]
    print(json.dumps(res if len(res) > 1 else res[0], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
