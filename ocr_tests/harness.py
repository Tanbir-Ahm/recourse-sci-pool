"""Run page images through reader models and keep an honest ledger of time, tokens and cost.

No case data belongs in this folder. Page images, outputs and the ledger stay OUTSIDE version control; pages are
referred to by an ID only (for example A01 = group A page 1; the file is A01.png), never by name.

  export GEMINI_API_KEY=...      # set in the environment's secrets; never pasted in chat, never printed
  python harness.py --pages PAGES_DIR --out RUN_DIR --models gemini-4-argon,gemini-3.7-flash --runs 2 \
                    --language Assamese --budget-inr 150
  python harness.py --report RUN_DIR/ledger.jsonl
  python harness.py --selftest          # wiring test with a fake caller; no network, no cost

Every call (including failed ones) is appended to RUN_DIR/ledger.jsonl with its time, tokens, estimated cost and why it
ended. The run stops before a call that would take the estimated spend past --budget-inr. Outputs are saved as
RUN_DIR/<page>/<model>/run<N>.txt; combinations already done are skipped, so a stopped run can be continued.
Cost is an ESTIMATE from models.json; the billing account is the truth.
"""
import argparse, base64, json, os, re, statistics, sys, tempfile, time, unicodedata, urllib.error, urllib.request

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


def call_gemini(model, key, system, image_bytes, mime, max_tokens=32768, tries=3, timeout=300):
    """One streaming call. Returns a dict; never raises. Time to first token and total time are measured."""
    body = {"contents": [{"role": "user", "parts": [{"text": "Transcribe and translate this page."},
                                                      {"inline_data": {"mime_type": mime, "data": base64.b64encode(image_bytes).decode()}}]}],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
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


def run(args, caller=call_gemini):
    models, fx = load_models(args.models_file)
    prompt = open(args.prompt or os.path.join(HERE, "prompts", "read_translate.txt")).read().format(language=args.language)
    pages = sorted(f for f in os.listdir(args.pages) if os.path.splitext(f)[1].lower() in IMG_TYPES)
    os.makedirs(args.out, exist_ok=True)
    ledger_path = os.path.join(args.out, "ledger.jsonl")
    ledger = read_ledger(ledger_path)
    calls = 0
    for fname in pages:
        page = os.path.splitext(fname)[0]
        img = open(os.path.join(args.pages, fname), "rb").read()
        mime = IMG_TYPES[os.path.splitext(fname)[1].lower()]
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
                    if rec["status"] != "ok":
                        outfile = outfile.replace(".txt", ".INCOMPLETE.txt")      # never mistaken for a good reading
                    os.makedirs(os.path.dirname(outfile), exist_ok=True)
                    open(outfile, "w").write(res["text"]); rec["outfile"] = os.path.relpath(outfile, args.out)
                with open(ledger_path, "a") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                ledger.append(rec)
                print(f"{page} {model} run {run_no}: {rec['status']}, {rec['total'] and round(rec['total'],1)} s, Rs {rec['cost_inr']:.2f} (running total Rs {spent_inr(ledger):.2f})", flush=True)
    return ledger


def report(path):
    ledger = read_ledger(path)
    by = {}
    for r in ledger:
        by.setdefault(r["model"], []).append(r)
    print(f"{'model':26} calls  ok  incomplete/failed   median time   median cost (Rs)   total (Rs)")
    for m, rs in by.items():
        good = [r for r in rs if r["status"] == "ok"]
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
    print("selftest OK (fake caller; no network, no cost)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages"); ap.add_argument("--out", default="run_out"); ap.add_argument("--models", default="gemini-4-argon,gemini-3.7-flash")
    ap.add_argument("--runs", type=int, default=2); ap.add_argument("--language", default="Assamese"); ap.add_argument("--prompt")
    ap.add_argument("--models-file", dest="models_file"); ap.add_argument("--budget-inr", type=float, dest="budget_inr"); ap.add_argument("--max-calls", type=int, dest="max_calls")
    ap.add_argument("--force", action="store_true"); ap.add_argument("--report"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest: selftest()
    elif a.report: report(a.report)
    elif a.pages:
        a.model_list = a.models.split(","); run(a)
    else: sys.exit("need --pages (or --report / --selftest)")
