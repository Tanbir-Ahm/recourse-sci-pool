"""Asks the live Recourse site (https://recourse.co.in/) a situation, through a headless browser, and saves what the page shows. Read-only use of the public site; each question costs the site a little model credit.
python3 ask_live_site.py smoke            -> loads the page, saves its text
python3 ask_live_site.py ask N02 N09 ...  -> asks those sealed stage F questions (texts from review_data/ruler/fix_test_f_v1.json) and saves each answer page"""
import json, os, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
URL = "https://recourse.co.in/"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
def launch(p):
    return p.chromium.launch(executable_path=CHROME, headless=True, proxy={"server": os.environ["HTTPS_PROXY"]}, args=["--no-sandbox"])
def main():
    mode = sys.argv[1]
    with sync_playwright() as p:
        b = launch(p)
        if mode == "smoke":
            pg = b.new_page(); pg.goto(URL, timeout=90000); pg.wait_for_selector("textarea", timeout=90000)
            txt = pg.inner_text("body"); open(os.path.join(HERE, "smoke_home.txt"), "w").write(txt); pg.screenshot(path=os.path.join(HERE, "smoke_home.png"))
            print(txt[:1500]); b.close(); return
        qs = {q["id"]: q["text"] for q in json.load(open(os.path.join(ROOT, "review_data/ruler/fix_test_f_v1.json")))["questions"]}
        for qid in sys.argv[2:]:
            pg = b.new_page(viewport={"width": 1200, "height": 1600}); pg.goto(URL, timeout=90000); pg.wait_for_selector("textarea", timeout=90000)
            pg.fill("textarea", qs[qid]); t0 = time.time()
            pg.get_by_role("button", name="Check my situation").click()
            time.sleep(5)
            for _ in range(60):                                     # up to ~5 minutes
                busy = pg.get_by_role("button", name="Reading").count()
                if not busy and time.time() - t0 > 8:
                    break
                time.sleep(5)
            time.sleep(3)
            txt = pg.inner_text("body"); open(os.path.join(HERE, f"answer_{qid}.txt"), "w").write(f"QUESTION {qid}: {qs[qid]}\n\nSECONDS: {time.time()-t0:.0f}\n\n{txt}")
            pg.screenshot(path=os.path.join(HERE, f"answer_{qid}.png"), full_page=True)
            print(qid, "done in", int(time.time() - t0), "s;", len(txt), "characters"); pg.close()
        b.close()
main()
