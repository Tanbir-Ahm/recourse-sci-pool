import time, re
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args=["--no-sandbox"])
    pg = b.new_page()
    pg.goto("http://localhost:8599", wait_until="networkidle")
    pg.get_by_role("button", name="Sign in").click()
    pg.wait_for_selector("text=LOGGED_IN", timeout=30000)
    print("claims:", pg.inner_text("pre, code").strip()[:700])
    print("at login:", re.findall(r"ID_TOKEN_EXP_IN_SECONDS=-?\d+", pg.inner_text("body")))
    time.sleep(12)
    pg.reload(wait_until="networkidle")
    pg.wait_for_selector("text=LOGGED_IN", timeout=30000)
    print("12 s later, after reload:", re.findall(r"ID_TOKEN_EXP_IN_SECONDS=-?\d+", pg.inner_text("body")), "still logged in:", "LOGGED_IN" in pg.inner_text("body"))
    b.close()
