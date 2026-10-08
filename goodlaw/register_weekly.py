"""The weekly step of the Overruled Register, as one command: write this week's review sheet (CSV and Excel) and a short summary into register_review/DATE/.

    python sci_goodlaw.py register-weekly --out-root register_review

Read-only on the register: it changes no row, flag or proposal (those change only when a person's filled sheet is recorded with `register-review`). Running it twice on one day
writes the same sheet. The weekly routine (REGISTER_ROUTINE_RUNBOOK.md) runs exactly this. The corpus-heavy sweep is NOT part of it: see the runbook.
"""
import collections
import os

from . import register as R
from . import register_review as RV
from . import register_xlsx as X


def run(out_root, today=None):
    today = R.today_str(today)
    reg = R.Register.load()
    flags, props = RV.load_flags(), RV.load_proposals()
    week = RV.build_queue(reg, flags, props, today, 20, 20, 60)
    backlog = RV.build_queue(reg, flags, props, today, 10 ** 6, 10 ** 6, None)
    d = os.path.join(out_root, today)
    os.makedirs(d, exist_ok=True)
    RV.write_queue(week, os.path.join(d, "review_queue.csv"))
    X.export(os.path.join(d, f"Review_Sheet_{today}.xlsx"), "weekly", today)
    kinds, back = collections.Counter(i["kind"] for i in week), collections.Counter(i["kind"] for i in backlog)
    trust = collections.Counter(r["trust"] for r in reg.rows)
    open_flags = [f for f in flags["flags"] if f["state"] == "open"]
    open_props = [p for p in props["proposals"] if p["state"] == "open" and not p.get("already_in_register")]
    weeks = -(-len(backlog) // 60) if backlog else 0
    lines = [f"# Register review sheet for {today}", "",
             "Generated automatically by `register-weekly`. It changes nothing in the register; decisions take effect only when a filled sheet is recorded with `register-review`.", "",
             f"- Items on this week's sheet: **{len(week)}** ({', '.join(f'{k} {v}' for k, v in sorted(kinds.items()))}).",
             f"- Whole backlog that is or will become due: **{len(backlog)}** ({', '.join(f'{k} {v}' for k, v in sorted(back.items()))}); at 60 a week about **{weeks} week(s)** if the cap stays.",
             f"- Register: {len(reg.rows)} rows ({', '.join(f'{k} {v}' for k, v in sorted(trust.items()))}). Open checker flags: {len(open_flags)}. Open sweep proposals not yet in the register: {len(open_props)}.",
             "", "Files in this folder: `review_queue.csv` (the sheet as CSV), `Review_Sheet_" + today + ".xlsx` (the same sheet in Excel with drop-downs for the reviewer). The full register workbook is built with `register-export-xlsx`.", ""]
    with open(os.path.join(d, "SUMMARY.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return {"dir": d, "week": len(week), "kinds": dict(kinds), "backlog": len(backlog), "weeks": weeks, "open_flags": len(open_flags), "open_proposals": len(open_props)}
