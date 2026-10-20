import sys, time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args=["--no-sandbox"])
    pg = b.new_page()
    pg.goto("http://localhost:8599", wait_until="networkidle")
    pg.get_by_role("button", name="Sign in").click()
    pg.wait_for_selector("text=LOGGED_IN", timeout=30000)
    time.sleep(1)
    txt = pg.inner_text("body")
    print(txt)
    b.close()
