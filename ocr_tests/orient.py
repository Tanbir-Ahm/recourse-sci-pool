"""Find out which way up a page photograph is, and turn it upright before it is read (plan section 10ae).

  python orient.py --selftest

Found on the first sideways phone photo (10ae): read as given, the two views agreed on 34.8% of letters; turned a quarter turn, 82.4%. The pipeline had no check
for a page that was photographed turned. Two signals, both used only to turn a page when they are sure:
  1. Tesseract's own orientation detector (free, local). Tested on 11 known-upright pages turned four ways (44 pictures): 34 right answers, 0 wrong ones, 10 "no answer"
     (sideways typed pages with little text, and a very small crop); on the one real sideways handwritten page it was right but not confident.
  2. One short question to the reading model about a small copy of the page, asked only when Tesseract is not sure.

  detect(image_bytes, mime, caller, key)  ->  {"rotate": 0 | 90 | 180 | 270, "answer": the model's word, "ok": bool}
      rotate is the number of degrees to turn the IMAGE CLOCKWISE so that the writing reads normally.
  turn(image, rotate)                     ->  the turned PIL image
The answer is one of UPRIGHT, ROTATE_CLOCKWISE_90, ROTATE_COUNTERCLOCKWISE_90, ROTATE_180. Anything else (no answer, an error, two answers) means "do nothing": a page is
never turned on a guess. The model sees a copy no larger than 800 pixels on the long side, so the question costs about the same as a small read.
decide(osd, model) is the whole policy, in plain words: a confident Tesseract answer is used (confidence 0.5 or more for "upright", 5 or more for "turned"); otherwise the model's
answer is used, and when both answer and disagree the page is NOT turned and is marked doubtful; with no usable answer the page is left alone and marked unchecked.
A page that is turned is read ONLY after turning; the original file is kept. The report says the page was turned, and by how much.
"""
import io, os, re, sys

PROMPT = ("This is a photograph or scan of a page with writing on it. The page may have been photographed turned. Decide how the IMAGE must be rotated so that the "
          "writing reads normally: the lines run from left to right, the first line is at the top, and the letters stand upright. Answer with exactly one of these words "
          "and nothing else: UPRIGHT (no rotation needed), ROTATE_CLOCKWISE_90, ROTATE_COUNTERCLOCKWISE_90, ROTATE_180.")
ANSWERS = {"UPRIGHT": 0, "ROTATE_CLOCKWISE_90": 90, "ROTATE_180": 180, "ROTATE_COUNTERCLOCKWISE_90": 270}
SMALL = 800


def small_copy(im):
    """A copy of the image no larger than SMALL pixels on the long side, as JPEG bytes."""
    im = im.convert("RGB")
    s = SMALL / max(im.size)
    if s < 1:
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))))
    b = io.BytesIO(); im.save(b, "JPEG", quality=85)
    return b.getvalue()


def parse(text):
    """The one answer in a reply, or None when there is none or more than one."""
    found = {w for w in ANSWERS if re.search(r"\b" + w + r"\b", (text or "").upper())}
    if "ROTATE_CLOCKWISE_90" in found and "ROTATE_COUNTERCLOCKWISE_90" in found:
        return None
    if len(found) != 1:
        return None
    return found.pop()


def detect(im, caller, model, key):
    """im: a PIL image. caller(model, key, system, image_bytes, mime) -> the reading dict of harness.call_gemini. Returns {'rotate', 'answer', 'ok', 'result'}."""
    res = caller(model, key, PROMPT, small_copy(im), "image/jpeg")
    ans = parse(res.get("text")) if res.get("ok") else None
    return {"rotate": ANSWERS[ans] if ans else 0, "answer": ans, "ok": ans is not None, "result": res}


def turn(im, rotate):
    """Turn a PIL image clockwise by 0, 90, 180 or 270 degrees."""
    return im if not rotate else im.rotate(-rotate, expand=True)


OSD_UPRIGHT_MIN, OSD_TURNED_MIN = 0.5, 5.0


def osd(im):
    """Tesseract's orientation detector on a PIL image. Returns {'rotate': 0|90|180|270 or None, 'confidence': float or None}; 'rotate' is the clockwise turn that makes the
    writing upright. No answer (too little text, tesseract missing, any error) comes back as None."""
    import subprocess, tempfile, shutil
    if not shutil.which("tesseract"):
        return {"rotate": None, "confidence": None}
    try:
        with tempfile.TemporaryDirectory() as td:
            f = os.path.join(td, "p.png")
            im.convert("RGB").save(f)
            r = subprocess.run(["tesseract", f, "stdout", "--psm", "0", "-l", "osd"], capture_output=True, text=True, timeout=60)
        d = dict(l.split(":", 1) for l in r.stdout.splitlines() if ":" in l)
        rot = int(d["Rotate"].strip()); conf = float(d["Orientation confidence"].strip())
        return {"rotate": rot, "confidence": conf} if rot in (0, 90, 180, 270) else {"rotate": None, "confidence": None}
    except Exception:
        return {"rotate": None, "confidence": None}


def decide(o, m=None):
    """The policy. o: osd() result. m: the model's detect() result, or None if it was not asked or did not answer. Returns {'rotate', 'status', 'why', 'need_model'}.
    status: upright | turned | doubtful | unchecked. need_model says whether the model should be asked at all (decide(o) with no model answer yet)."""
    r, c = o.get("rotate"), o.get("confidence")
    if r is not None and c is not None:
        if r == 0 and c >= OSD_UPRIGHT_MIN:
            return {"rotate": 0, "status": "upright", "why": "Tesseract: upright", "need_model": False}
        if r != 0 and c >= OSD_TURNED_MIN:
            return {"rotate": r, "status": "turned", "why": "Tesseract: turned, confidence %.1f" % c, "need_model": False}
    mm = m if (m and m.get("ok")) else None
    sure = r is not None and c is not None and c >= OSD_UPRIGHT_MIN
    if mm is None:
        if m is None:
            return {"rotate": 0, "status": "unchecked", "why": "not sure yet", "need_model": True}
        if sure:
            return {"rotate": 0, "status": "doubtful", "why": "Tesseract thinks the page is turned %d degrees (confidence %.1f) but could not be confirmed" % (r, c), "need_model": False}
        return {"rotate": 0, "status": "unchecked", "why": "no usable answer from Tesseract or the model", "need_model": False}
    if sure and r != mm["rotate"]:
        return {"rotate": 0, "status": "doubtful", "why": "Tesseract says turn %d degrees, the model says turn %d: not turned" % (r, mm["rotate"]), "need_model": False}
    return {"rotate": mm["rotate"], "status": "turned" if mm["rotate"] else "upright", "why": "the model%s" % (" and Tesseract agree" if sure else " (Tesseract unsure)"), "need_model": False}


def check(im, caller=None, model=None, key=None, osd_fn=None):
    """Full check of one page image. Returns decide()'s dict plus 'model_result' (the raw reply when the model was asked)."""
    o = (osd_fn or osd)(im)
    d = decide(o)
    d["osd"] = o; d["model_result"] = None
    if d["need_model"]:
        m = detect(im, caller, model, key) if caller else None
        d2 = decide(o, m if m else {"ok": False})
        d2["osd"] = o; d2["model_result"] = m["result"] if m else None
        return d2
    return d


def selftest():
    from PIL import Image, ImageDraw
    assert parse("UPRIGHT") == "UPRIGHT" and parse("ROTATE_CLOCKWISE_90.") == "ROTATE_CLOCKWISE_90" and parse("rotate_180") == "ROTATE_180"
    assert parse("ROTATE_COUNTERCLOCKWISE_90") == "ROTATE_COUNTERCLOCKWISE_90"             # the shorter word is inside the longer one but is not a second answer
    assert parse("UPRIGHT or ROTATE_180") is None and parse("") is None and parse(None) is None and parse("I cannot tell") is None
    im = Image.new("RGB", (400, 200), "white"); ImageDraw.Draw(im).rectangle((0, 0, 40, 40), fill="black")          # a mark in the top-left corner
    assert turn(im, 0) is im
    t = turn(im, 90); assert t.size == (200, 400) and t.getpixel((199, 5)) == (0, 0, 0), "a clockwise quarter turn moves the top-left corner to the top-right"
    t = turn(im, 180); assert t.size == (400, 200) and t.getpixel((399, 199)) == (0, 0, 0)
    t = turn(im, 270); assert t.size == (200, 400) and t.getpixel((5, 399)) == (0, 0, 0), "a counterclockwise quarter turn moves it to the bottom-left"
    seen = {}
    def fake(model, key, system, image, mime):
        seen["system"], seen["mime"] = system, mime
        seen["size"] = Image.open(io.BytesIO(image)).size
        return {"ok": True, "text": "ROTATE_CLOCKWISE_90"}
    big = Image.new("RGB", (3000, 4000), "white")
    d = detect(big, fake, "m", "k")
    assert d["rotate"] == 90 and d["ok"] and max(seen["size"]) == SMALL and seen["system"] == PROMPT and seen["mime"] == "image/jpeg", (d, seen)
    assert detect(im, lambda *a: {"ok": False, "text": None}, "m", "k")["rotate"] == 0 and not detect(im, lambda *a: {"ok": True, "text": "maybe"}, "m", "k")["ok"]
    U = {"rotate": 0, "confidence": 30.0}
    assert decide(U)["status"] == "upright" and decide(U)["need_model"] is False
    assert decide({"rotate": 90, "confidence": 12.0}) == {"rotate": 90, "status": "turned", "why": "Tesseract: turned, confidence 12.0", "need_model": False}
    assert decide({"rotate": None, "confidence": None})["need_model"] and decide({"rotate": 90, "confidence": 0.53})["need_model"]          # the real sideways page: right but not confident
    assert decide({"rotate": 90, "confidence": 0.53}, {"ok": True, "rotate": 90})["rotate"] == 90 and decide({"rotate": 90, "confidence": 0.53}, {"ok": True, "rotate": 90})["status"] == "turned"
    assert decide({"rotate": 90, "confidence": 0.53}, {"ok": True, "rotate": 0})["status"] == "doubtful" and decide({"rotate": 90, "confidence": 0.53}, {"ok": True, "rotate": 0})["rotate"] == 0
    assert decide({"rotate": None, "confidence": None}, {"ok": True, "rotate": 270})["rotate"] == 270
    assert decide({"rotate": None, "confidence": None}, {"ok": False})["status"] == "unchecked" and decide({"rotate": 90, "confidence": 0.6}, {"ok": False})["status"] == "doubtful"
    assert decide({"rotate": 180, "confidence": 0.3}, {"ok": True, "rotate": 0})["status"] == "upright", "a model that says upright against a Tesseract answer under 0.5 confidence"
    c1 = check(im, fake, "m", "k", osd_fn=lambda i: U); assert c1["status"] == "upright" and c1["model_result"] is None
    c2 = check(im, fake, "m", "k", osd_fn=lambda i: {"rotate": None, "confidence": None}); assert c2["rotate"] == 90 and c2["model_result"] is not None
    assert check(im, None, "m", "k", osd_fn=lambda i: {"rotate": None, "confidence": None})["status"] == "unchecked"
    o = osd(Image.new("RGB", (50, 50), "white")); assert set(o) == {"rotate", "confidence"}                                     # a blank picture: no answer, no crash
    print("selftest OK (invented images only)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        sys.exit(__doc__)
