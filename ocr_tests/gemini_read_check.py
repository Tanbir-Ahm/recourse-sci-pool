"""Read one handwritten page with several Gemini models, several times each, and score the readings against known facts.

Built for the paid-tier test: the free tier cannot call the largest models, so this first checks which models answer.
Nothing about a real case belongs in this file or in the repo. The image and the facts file stay outside version control.

  export GEMINI_API_KEY=...             # a key on a billing-enabled project; never paste it in chat
  python gemini_read_check.py --image page.png --facts facts.json --models gemini-3.1-pro-preview,gemini-3.5-flash --runs 3 --out out
  python gemini_read_check.py --selftest

facts.json: {"label": "regex", ...}. A label starting with "[digit] " marks a critical number (date, age, amount, section).
Matching is strict and done on normalised text: Assamese ra/wa mapped to the Bengali forms, digits to ASCII, spaces and punctuation collapsed.
"""
import argparse, base64, json, os, re, sys, time, urllib.error, urllib.request

SYSTEM = ("You transcribe handwritten {lang} court and police documents. Transcribe exactly what is written, line by line, in the original script. "
          "NEVER guess: if a word or digit is not clearly legible write [unclear] in its place, and put (?) after a reading you are not sure of. "
          "Number the lines. Do not translate and do not add anything that is not on the page.")


def norm(s):
    s = s.replace("ৰ", "র").replace("ৱ", "ব").replace("‍", "").replace("‌", "")
    s = s.translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))
    return re.sub(r"[\s\-\.\|।,;:()\[\]\"'`*]+", " ", s)


def score(text, facts):
    t = norm(text)
    return [label for label, pat in facts.items() if re.search(pat, t)]


def call(model, parts, system, key, max_tokens=8192, tries=4):
    body = {"contents": [{"role": "user", "parts": parts}], "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens}}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                 json.dumps(body).encode(), {"x-goog-api-key": key, "Content-Type": "application/json"})
    for attempt in range(tries):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=180))
            c = (d.get("candidates") or [{}])[0]
            return {"ok": True, "text": "".join(p.get("text", "") for p in c.get("content", {}).get("parts", [])),
                    "tokens": d.get("usageMetadata", {}).get("totalTokenCount", 0)}
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf8", "replace")
            if e.code in (429, 503) and "quota" not in msg.lower() and attempt < tries - 1:
                time.sleep(30); continue
            return {"ok": False, "code": e.code, "error": msg[:200]}
        except (TimeoutError, OSError) as e:
            if attempt == tries - 1: return {"ok": False, "code": 0, "error": str(e)[:200]}
            time.sleep(20)


def run(args, caller=call):
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key and not args.selftest: sys.exit("GEMINI_API_KEY is not set in this session.")
    facts = json.load(open(args.facts))
    img = base64.b64encode(open(args.image, "rb").read()).decode()
    mime = "image/webp" if args.image.lower().endswith(".webp") else "image/jpeg" if args.image.lower().endswith((".jpg", ".jpeg")) else "image/png"
    os.makedirs(args.out, exist_ok=True)
    summary = {}
    for model in args.models.split(","):
        pre = caller(model, [{"text": "Reply with the single word: ready"}], "Answer briefly.", key, max_tokens=300, tries=2)
        if not pre["ok"]:
            print(f"[{model}] not usable on this key: HTTP {pre['code']} {pre['error'][:110]}  (a quota error means the project is not on a paid tier)")
            summary[model] = None; continue
        digit = [f for f in facts if f.startswith("[digit]")]
        scores = []
        for r in range(1, args.runs + 1):
            res = caller(model, [{"text": "Transcribe this handwritten page."}, {"inline_data": {"mime_type": mime, "data": img}}],
                         SYSTEM.format(lang=args.lang), key)
            if not res["ok"]:
                print(f"[{model}] run {r}: failed HTTP {res['code']} {res['error'][:90]}"); continue
            found = score(res["text"], facts); scores.append((len(found), len([d for d in digit if d in found]), res["tokens"]))
            open(os.path.join(args.out, f"{model}_run{r}.txt"), "w").write(res["text"])
            print(f"[{model}] run {r}: {len(found)}/{len(facts)} facts, {len([d for d in digit if d in found])}/{len(digit)} critical numbers; missed: "
                  + "; ".join(f for f in facts if f not in found), flush=True)
        summary[model] = scores
    print("\nsummary (facts found per run; critical numbers found per run; tokens):")
    for m, s in summary.items():
        print(f"  {m}: " + ("not usable" if s is None else f"facts {[x[0] for x in s]}, numbers {[x[1] for x in s]}, tokens {sum(x[2] for x in s)}"))
    return summary


def selftest():
    import tempfile
    d = tempfile.mkdtemp(); img = os.path.join(d, "x.png"); open(img, "wb").write(b"\x89PNG fake")
    json.dump({"[digit] age 40": r"বয়স ?40", "district": r"ওদালগুর"}, open(os.path.join(d, "f.json"), "w"), ensure_ascii=False)
    def fake(model, parts, system, key, max_tokens=0, tries=0):
        if "pro" in model: return {"ok": False, "code": 429, "error": "You exceeded your current quota"}
        return {"ok": True, "text": "1. থানা/জিলা - ওদালগুৰি\n2. (বয়স ৪০ বছৰ)", "tokens": 10}
    ns = argparse.Namespace(image=img, facts=os.path.join(d, "f.json"), models="m-flash,m-pro", runs=2, out=os.path.join(d, "o"), lang="Assamese", selftest=True)
    s = run(ns, fake)
    assert s["m-pro"] is None and [x[0] for x in s["m-flash"]] == [2, 2] and [x[1] for x in s["m-flash"]] == [1, 1], s
    print("selftest OK (fake caller; no Gemini call was made)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--image"); ap.add_argument("--facts"); ap.add_argument("--models", default="gemini-3.1-pro-preview,gemini-3.5-flash")
    ap.add_argument("--runs", type=int, default=3); ap.add_argument("--out", default="gemini_out"); ap.add_argument("--lang", default="Assamese")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest: selftest()
    elif not (a.image and a.facts): sys.exit("need --image and --facts (or --selftest)")
    else: run(a)
