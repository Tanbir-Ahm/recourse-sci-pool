"""
browser_check.py -- opens every Act Directory link in a real browser (headless Chromium) and reads what a person would see.  A one-off human-facing companion to
`python act_directory.py check-links`, which asks India Code's data API for the record behind each link and compares its title, Act number and year with the Directory entry.
India Code's site is a client-side app that answers HTTP 200 for ANY address, so "the page opens" proves nothing by itself; this script reads the rendered page and requires that
  * the page (title or heading) shows the Act's name exactly as India Code's own record gives it (the 'indiacode.title' that check-links wrote), and
  * where the page shows an Act number and year in its metadata table, they equal the entry's.
Written 2026-10-16.  Not run by the site.  Needs: playwright for Python, Chromium (the sandbox has /opt/pw-browsers/chromium), indiacode.gov.in reachable.

    python acts/browser_check.py --directory <recourse>/acts_directory.json --out acts/link_check_report.json [--chromium /opt/pw-browsers/chromium]
"""
import argparse
import json
import re
import sys
import time


def norm(text):
    t = (text or "").lower().replace("’", "'")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--directory", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chromium", default="/opt/pw-browsers/chromium")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    data = json.load(open(args.directory, encoding="utf-8"))
    report, bad = [], 0
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, args=["--no-sandbox"])
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36", viewport={"width": 1280, "height": 900})
        for e in data["acts"]:
            row = {"id": e["id"], "url": e.get("url"), "expected_title": (e.get("indiacode") or {}).get("title"), "act_no": e.get("act_no")}
            pg = ctx.new_page()
            try:
                resp = pg.goto(e["url"], wait_until="networkidle", timeout=60000)
                pg.wait_for_timeout(2000)
                row["http"] = resp.status if resp else None
                row["final_url"] = pg.url
                row["page_title"] = pg.title()
                row["headings"] = [h.inner_text().strip() for h in pg.query_selector_all("h1, h2")][:6]
                body = pg.inner_text("body")
                lines = [l.strip() for l in body.splitlines() if l.strip()]
                meta = {}
                for i, l in enumerate(lines):
                    m = re.match(r"^(Act Number|Act Year|Jurisdiction|Collection|Enact Date|Enforcement Date|Ministry Name)\s+(.+)$", l)       # 'Act Year<TAB>1988' on one line in the table
                    if m:
                        meta[m.group(1)] = m.group(2).strip()
                row["metadata_table"] = meta
                shown = norm(" ".join([row["page_title"]] + row["headings"] + lines[:60]))
                want = norm(row["expected_title"])
                name_ok = bool(want) and want in shown
                num_ok = True
                m = re.match(r"\s*(\d+)\s+of\s+(\d{4})", e["act_no"])
                if meta.get("Act Number") and meta.get("Act Year") and m:
                    num_ok = (meta["Act Number"].lstrip("0"), meta["Act Year"]) == (m.group(1), m.group(2))
                lost = bool(re.search(r"page not found|404|no results", norm(row["page_title"] + " " + " ".join(row["headings"]))))
                row["name_on_page"], row["number_on_page_ok"], row["looks_like_not_found"] = name_ok, num_ok, lost
                row["ok"] = bool(row["http"] == 200 and name_ok and num_ok and not lost)
            except Exception as exc:  # noqa: BLE001
                row["error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
                row["ok"] = False
            pg.close()
            bad += 0 if row["ok"] else 1
            report.append(row)
            print(("ok   " if row["ok"] else "FAIL ") + f"{e['id']:32s} {row.get('page_title', row.get('error', ''))[:80]}")
            time.sleep(0.3)
        browser.close()
    json.dump({"checked_on": time.strftime("%Y-%m-%d", time.gmtime()), "directory": args.directory, "rows": report}, open(args.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\n{len(report) - bad} of {len(report)} pages show the right Act; report: {args.out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
