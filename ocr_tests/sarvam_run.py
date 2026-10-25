"""Run a scanned PDF through Sarvam Vision (document digitise) and score it against reference terms.

Nothing about any real case belongs in this file or in the repo: the PDF and the reference terms are
passed on the command line and stay outside version control.

  pip install sarvamai pymupdf
  export SARVAM_API_KEY=...            # set as an environment variable, never pasted in chat
  python sarvam_run.py --pdf FILE.pdf --english-pages 1,3,4 --assamese-pages 2,12 --ref refs.json --out OUTDIR
  python sarvam_run.py --selftest      # wiring test with a fake client; its output is NOT Sarvam's

refs.json: {"3": ["term", "term"], "7": [...]}  (page number -> terms read by eye from the page image;
matching is lenient: lower-case, non-alphanumerics removed, substring).
One language per job and at most 10 pages per PDF and at most 10 documents per job are the API's limits (docs.sarvam.ai), so each page is sent
as its own one-page PDF, and the pages are split into an English job and an Assamese job. A third job sends
every page with no language set, to see how the default behaves.
"""
import argparse, json, os, re, sys, time
import pymupdf

TERMINAL = {"completed", "partially_completed", "failed", "rejected"}
POLL_SECONDS = 10     # docs.sarvam.ai: Document AI is limited to 10 requests per minute on every plan


def call(fn, *args, **kwargs):
    """Retry on HTTP 429 (rate limit); anything else is raised."""
    for attempt in range(8):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            if getattr(exc, "status_code", None) != 429 or attempt == 7:
                raise
            time.sleep(15)


def page_pdf(doc, n):
    one = pymupdf.open()
    one.insert_pdf(doc, from_page=n - 1, to_page=n - 1)
    data = one.tobytes()
    one.close()
    return data


def run_job(client, doc, pages, language, label, out, reuse=False):
    saved = os.path.join(out, f"{label}.json")
    if reuse and os.path.exists(saved):
        print(f"[{label}] reusing saved results (no call made)")
        return texts_from(json.load(open(saved))["results"])
    files = [(f"p{n}.pdf", page_pdf(doc, n), "application/pdf") for n in pages]
    kw = {"file": files}
    if language:
        kw["language"] = language
    job = call(client.doc_ai.digitise, **kw)
    print(f"[{label}] job {job.job_id} started ({len(pages)} pages, language={language or 'default'})", flush=True)
    t0 = time.time()
    while True:
        st = call(client.doc_ai.get_status, job.job_id)
        if st.status in TERMINAL:
            break
        if time.time() - t0 > 900:
            raise TimeoutError(f"{label}: still {st.status} after 15 minutes")
        time.sleep(POLL_SECONDS)
    print(f"[{label}] {st.status}; usage={st.usage}", flush=True)
    # The default output is HTML and "md" is refused for such a job, so read the structured JSON:
    # documents[].pages[].blocks[] each with text, layout_tag and reading_order (no confidence field has been seen).
    res = call(client.doc_ai.get_results, job.job_id, format="json")
    data = res.model_dump() if hasattr(res, "model_dump") else res
    with open(os.path.join(out, f"{label}.json"), "w") as f:
        json.dump({"status": st.status, "usage": str(st.usage), "results": data}, f, ensure_ascii=False, indent=1, default=str)
    return texts_from(data)


def texts_from(data):
    texts = {}
    for d in data.get("documents") or []:
        name = d.get("filename") or d.get("file_name") or ""
        m = re.search(r"p(\d+)", name)
        if not m:
            continue
        blocks = []
        for pg in d.get("pages") or []:
            blocks += pg.get("blocks") or ([{"text": pg.get("content") or "", "reading_order": 0}] if pg.get("content") else [])
        blocks.sort(key=lambda b: b.get("reading_order") or 0)
        texts[int(m.group(1))] = "\n".join(b.get("text") or "" for b in blocks)
    return texts


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def score(texts, refs, hand=range(3, 11)):
    per = {p: (sum(t in norm(texts.get(p, "")) for t in terms), len(terms)) for p, terms in refs.items()}
    tot = lambda keys: (sum(per[k][0] for k in keys), sum(per[k][1] for k in keys))
    a, b = tot(per)
    hk = [k for k in per if k in hand]
    h, hb = tot(hk) if hk else (0, 1)
    return per, 100 * a / b, 100 * h / hb


def report(name, texts, refs):
    per, allp, hw = score(texts, refs)
    print("%-22s" % name + " ".join("p%d:%d/%d" % (p, *per[p]) for p in per) + " | all %3d%% | pages 3-10 %3d%%" % (allp, hw))


def script_chars(s):
    return sum("ঀ" <= c <= "৿" for c in s)       # Assamese/Bengali block


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf"); ap.add_argument("--ref"); ap.add_argument("--out", default="sarvam_out")
    ap.add_argument("--english-pages", default=""); ap.add_argument("--assamese-pages", default="")
    ap.add_argument("--selftest", action="store_true"); ap.add_argument("--reuse", action="store_true", help="reuse saved job results in --out instead of paying again")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.pdf and a.ref and a.english_pages and a.assamese_pages):
        sys.exit("need --pdf, --ref, --english-pages and --assamese-pages (or --selftest)")
    if not os.environ.get("SARVAM_API_KEY"):
        sys.exit("SARVAM_API_KEY is not set in this session.")
    from sarvamai import SarvamAI
    os.makedirs(a.out, exist_ok=True)
    client = SarvamAI()
    doc = pymupdf.open(a.pdf)
    en_pages = [int(x) for x in a.english_pages.split(",")]
    as_pages = [int(x) for x in a.assamese_pages.split(",")]
    refs = {int(k): v for k, v in json.load(open(a.ref)).items()}
    en = run_job(client, doc, en_pages, "en-IN", "english_pages_en-IN", a.out, a.reuse)
    asm = run_job(client, doc, as_pages, "as-IN", "assamese_pages_as-IN", a.out, a.reuse)
    dflt = {}
    allp = list(range(1, len(doc) + 1))
    for i in range(0, len(allp), 10):                      # API limit: at most 10 documents per job
        dflt.update(run_job(client, doc, allp[i:i + 10], None, f"all_pages_default_{i // 10 + 1}", a.out, a.reuse))
    matched = {**en, **asm}
    json.dump({"matched": matched, "default": dflt}, open(os.path.join(a.out, "texts.json"), "w"), ensure_ascii=False)
    report("sarvam_matched_lang", matched, refs)
    report("sarvam_default_lang", dflt, refs)
    for name, t in (("sarvam_matched_lang", matched), ("sarvam_default_lang", dflt)):
        print("%-22s" % name, " | ".join("p%d: %d Assamese-script chars" % (p, script_chars(t.get(p, ""))) for p in as_pages))


def selftest():
    class R:
        def __init__(s, **k): s.__dict__.update(k)
    class Fake:
        def __init__(s): s.doc_ai = s; s.jobs = {}
        def digitise(s, file, language=None): jid = f"j{len(s.jobs)}"; s.jobs[jid] = file; return R(job_id=jid, status="queued")
        def get_status(s, jid): return R(status="completed", usage="fake")
        def get_results(s, jid, format="json"):
            return R(documents=[R(file_name=n, pages=[R(content="alpha beta 302")]) for (n, _b, _t) in s.jobs[jid]],
                     model_dump=lambda: {"documents": [{"filename": n, "pages": [{"blocks": [{"text": "alpha beta 302", "reading_order": 1}]}]} for (n, _b, _t) in s.jobs[jid]]})
    one = pymupdf.open(); one.new_page(); one.new_page(); one.new_page()
    os.makedirs("selftest_out", exist_ok=True)
    t = run_job(Fake(), one, [1, 2], "en-IN", "selftest", "selftest_out")
    assert set(t) == {1, 2} and "302" in t[1], t
    per, allp, hw = score(t, {1: ["alpha", "302"], 2: ["gamma"]})
    assert per[1] == (2, 2) and per[2] == (0, 1), per
    print("selftest OK (fake client; no Sarvam call was made)")


if __name__ == "__main__":
    main()
