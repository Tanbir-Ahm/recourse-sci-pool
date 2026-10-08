"""The weekly review: what a person looks at, once every 7 days, and how the decisions go back into the register.

Rule that does not bend: automation may add caution, never remove it. The checker's flags and the sweep's proposals only ever enter the register when a person confirms them; a flag the checker
stops raising stays open until a person clears it; nothing is deleted (a rejected row stays, marked rejected, with its history).

What is in a week's queue (CSV for the reviewer), most important first:
    flag       the checker's ADVERSE_SIGNAL / QUESTIONED cards (cards/currency_cards.json), kept in `flags.json`: confirm, clear or keep open
    chain      a register row whose overruling decision was itself later overruled: re-read and say whether the recorded status stands
    candidate  rows that come from the post-2015 list or the same judgments, checked by Claude, not by a lawyer: confirm, change or reject
    unchecked  entries nobody could check from our text
    proposal   the sweep's finds (register_sweep.py): add a row or reject (at most `proposal_limit` a week)
    listing    rows of the verified list that the list itself makes doubtful (each case overruled by the other, no overruling decision named, overruling dated before overruled)
    match      rows that cannot be recognised in an answer without a citation or year: supply them (at most `match_limit` a week)
An item the reviewer leaves undecided, or marks `keep`, comes back on `next_due` (seven days later).

    python sci_goodlaw.py register-review-queue --out review_queue.csv       # writes the week's sheet
    python sci_goodlaw.py register-review --sheet review_queue.csv --reviewer "Mr. Advocate"    # records the filled sheet
"""
import csv
import datetime
import json
import os
import re

from . import register as R

INTERVAL_DAYS = 7
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "register")
FLAGS_PATH = os.path.join(DATA, "flags.json")
PROPOSALS_PATH = os.path.join(DATA, "proposals.json")

PRIORITY = {"flag": 1, "candidate": 2, "unchecked": 2, "chain": 3, "proposal": 4, "listing": 5, "match": 6}
CONFIRMS = {"confirm_overruled": "overruled", "confirm_partial": "overruled_in_part", "confirm_not_good_law": "not_good_law", "confirm_per_incuriam": "per_incuriam",
            "confirm_not_binding": "not_binding"}
COLUMNS = ["item_id", "kind", "priority", "case", "later_case", "evidence", "ask", "decision", "new_treatment", "scope", "overruling_case", "overruling_year", "overruled_cites", "overruled_year",
           "note", "reviewer", "review_date", "next_review_if_kept"]


def _d(today):
    return today if isinstance(today, datetime.date) else datetime.date.fromisoformat(today)


def _plus(today, days=INTERVAL_DAYS):
    return (_d(today) + datetime.timedelta(days=days)).isoformat()


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:60]


def _load(path, default):
    if not os.path.exists(path):
        return default
    return json.load(open(path, encoding="utf-8"))


def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def load_flags(path=FLAGS_PATH):
    return _load(path, {"schema": "goodlaw-flags-1", "flags": []})


def load_proposals(path=PROPOSALS_PATH):
    return _load(path, {"schema": "goodlaw-proposals-1", "proposals": []})


# ----- flags from the checker's cards ----------------------------------------------------------------------------------------------------------------------------

def flags_from_cards(cards_doc, flags_doc, today):
    """Add a flag for every card that is ADVERSE_SIGNAL or QUESTIONED; refresh a known flag's last_seen. Returns (new ids, no-longer-raised ids). A flag no longer raised stays open."""
    by_id = {f["id"]: f for f in flags_doc["flags"]}
    new, quiet, raised = [], [], set()
    for card in cards_doc["cards"]:
        if card.get("status") not in ("ADVERSE_SIGNAL", "QUESTIONED"):
            continue
        c = card["case"]
        fid = "F-" + _slug(c["name"])
        raised.add(fid)
        ev = [{"title": e.get("title"), "date": e.get("date"), "bench": e.get("bench_size"), "cue": e.get("cue"), "label": e.get("label"), "quote": (e.get("quote") or "")[:300]}
              for e in card.get("evidence", []) if e.get("group") == "strong"][:3]
        if fid in by_id:
            f = by_id[fid]
            f["last_seen"] = today
            f["status"] = card["status"]
            f["note"] = card.get("user_facing_note")
            f["evidence"] = ev or f.get("evidence", [])
        else:
            f = {"id": fid, "source": "checker", "case": {"name": c["name"], "citation": c.get("citation"), "year": c.get("year"), "doc_key": (card.get("corpus") or {}).get("doc_key")},
                 "status": card["status"], "note": card.get("user_facing_note"), "evidence": ev, "first_seen": today, "last_seen": today, "state": "open", "next_due": None,
                 "history": [{"on": today, "by": "register-review", "event": f"raised by the checker as {card['status']}"}]}
            flags_doc["flags"].append(f)
            new.append(fid)
    for f in flags_doc["flags"]:
        if f["state"] == "open" and f["id"] not in raised and f["last_seen"] != today:
            quiet.append(f["id"])
    return new, quiet


# ----- the queue --------------------------------------------------------------------------------------------------------------------------------------------------------

def _due(rec, today):
    nd = (rec.get("review") or {}).get("next_due") if "review" in rec else rec.get("next_due")
    return not nd or nd <= _d(today).isoformat()


def build_queue(reg, flags_doc, proposals_doc, today, proposal_limit=20, match_limit=20, limit=None):
    """The week's items, most important first. `reg` is a Register. `limit` caps the whole sheet (flags are never cut)."""
    items = []
    for f in flags_doc["flags"]:
        if f["state"] != "open" or not _due(f, today):
            continue
        c = f["case"]
        held = reg.lookup_case(c["name"], c.get("year"), c.get("citation"))
        held = [h["row"] for h in held if h["strength"] == "strong"]
        ev = "; ".join(f"{e.get('title')} ({(e.get('date') or '')[:4]}, {e.get('bench')} judges): {e.get('cue')}: {e.get('quote')[:140]}" for e in f["evidence"][:2])
        ask = "Confirm (overruled / in part / not good law / per incuriam / not binding), clear, or keep open." + (
            f" Already in the register as {', '.join(r['id'] for r in held)}." if held else " Not in the register: a confirmation needs the overruling case.")
        items.append({"item_id": f["id"], "kind": "flag", "case": f"{c['name']} ({c.get('year')})", "later_case": "", "evidence": ev, "ask": ask})
    props = [p for p in proposals_doc["proposals"] if p["state"] == "open" and not p.get("already_in_register") and _due(p, today)]
    props.sort(key=lambda p: (-(p.get("bench") or 0), -int((p.get("date") or "0000")[:4])))
    n_prop = n_match = 0
    for r in reg.rows:
        if r["trust"] == "rejected" or not _due(r, today):
            continue
        rv = r.get("review") or {}
        chain = reg.chain(r)
        base = {"item_id": r["id"], "case": f"{r['overruled']['name']} ({r['overruled'].get('year')})", "later_case": f"{r['overruling']['name']} ({r['overruling'].get('year')})"}
        if r["trust"] == "candidate":
            extra = f" | the overruling decision was itself later: {'; '.join(reg.phrase(c) for c in chain)}" if chain else ""
            items.append({**base, "kind": "candidate", "evidence": f"{r['treatment']}: {r.get('court_words') or ''} | scope: {r.get('scope') or ''} | checked by Claude ({r['evidence'].get('basis')}){extra}",
                          "ask": "Confirm, change the treatment, reject, or keep (the answer says 'reported, not yet confirmed' until you confirm)."})
        elif chain and not rv.get("chain_ok"):
            nxt = "; ".join(f"{reg.phrase(c)} [{c['id']}]" for c in chain)
            items.append({**base, "kind": "chain", "evidence": f"The overruling decision was itself later: {nxt}",
                          "ask": "Does the recorded status of the earlier decision still stand? (confirm = it stands; change = give the new treatment; keep = decide next week)"})
        elif r["trust"] == "unchecked":
            items.append({**base, "kind": "unchecked", "evidence": "named by the outside list; the later judgment is not in our text", "ask": "Confirm from the judgment, reject, or keep."})
        elif r["source"] == "list1" and any(f in r["flags"] for f in ("list_mutual_pair", "list_no_overruling_decision", "year_order_check")) and not rv.get("listing_ok"):
            why = {"list_mutual_pair": "the list also records the reverse (each case overruled by the other)", "list_no_overruling_decision": "the list names no overruling decision",
                   "year_order_check": "the overruling decision's years are earlier than the overruled decision's"}
            items.append({**base, "kind": "listing", "evidence": "; ".join(why[f] for f in r["flags"] if f in why),
                          "ask": "Is the entry right as listed? (confirm = yes, give new_treatment 'overruled' or 'reversed_on_appeal'; change = give the correct treatment or overruling case; keep)"})
        elif "needs_citation_or_year" in r["flags"] and r["source"] == "list1":
            if n_match < match_limit:
                n_match += 1
                items.append({**base, "kind": "match", "evidence": "cannot be recognised in an answer without a citation or a year", "ask": "Supply overruled_cites and/or overruled_year."})
    for p in props[:proposal_limit]:
        items.append({"item_id": p["id"], "kind": "proposal", "case": (p.get("overruled_name") or "(see sentence)"), "later_case": f"{p['title']} ({(p.get('date') or '')[:4]}, {p.get('bench')} judges)",
                      "evidence": f"{p['kind']}: {p['evidence'][:240]}", "ask": "add_row (give overruled_year; overruled_cites is prefilled where the report printed them), reject, or keep."})
    for it in items:
        it["priority"] = PRIORITY[it["kind"]]
        it["next_review_if_kept"] = _plus(today)
    items.sort(key=lambda i: (i["priority"], i["item_id"]))
    if limit:
        items = [i for i in items if i["kind"] == "flag"] + [i for i in items if i["kind"] != "flag"][:max(0, limit - sum(1 for i in items if i["kind"] == "flag"))]
    return items


def write_queue(items, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for it in items:
            w.writerow({c: it.get(c, "") for c in COLUMNS})
    return path


# ----- decisions --------------------------------------------------------------------------------------------------------------------------------------------------------

def _event(rec, event, by, on, note=None):
    rec.setdefault("history", []).append({"on": on, "by": by, "event": event, **({"note": note} if note else {})})


def _keep(rec, today, by):
    rec.setdefault("review", {})["last"] = today
    rec["review"]["next_due"] = _plus(today)
    _event(rec, "kept open at the weekly review", by, today)


def sheet_records(path):
    """The rows of a filled sheet: a CSV, or an Excel workbook (the sheet named 'Review sheet', else the first). Cells come back as text; a date cell becomes YYYY-MM-DD."""
    if not str(path).lower().endswith(".xlsx"):
        with open(path, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    import datetime
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb["Review sheet"] if "Review sheet" in wb.sheetnames else wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    start = next((i for i, r in enumerate(rows) if r and r[0] == "item_id"), None)
    if start is None:
        raise ValueError("no header row starting with item_id")
    head = [str(h) if h is not None else "" for h in rows[start]]
    out = []
    for r in rows[start + 1:]:
        if not r or r[0] in (None, ""):
            continue
        rec = {}
        for h, v in zip(head, r):
            if not h:
                continue
            rec[h] = v.date().isoformat() if isinstance(v, (datetime.datetime, datetime.date)) and hasattr(v, "date") else ("" if v is None else (str(int(v)) if isinstance(v, float) and v == int(v) else str(v)))
        out.append(rec)
    return out


def apply_decisions(rows, flags_doc, proposals_doc, sheet_path, reviewer, today):
    """Record a filled queue sheet. Mutates rows / flags_doc / proposals_doc; returns {'applied': [...], 'errors': [...]}. Rows are never deleted."""
    reg = R.Register(rows)
    by_row = {r["id"]: r for r in rows}
    by_flag = {f["id"]: f for f in flags_doc["flags"]}
    by_prop = {p["id"]: p for p in proposals_doc["proposals"]}
    out = {"applied": [], "errors": []}
    for rec in sheet_records(sheet_path):
        dec = (rec.get("decision") or "").strip().lower()
        if not dec:
            continue
        iid, by = rec["item_id"], (rec.get("reviewer") or reviewer or "").strip() or reviewer
        on = (rec.get("review_date") or "").strip() or today
        note = (rec.get("note") or "").strip() or None
        try:
            if iid in by_flag:
                _apply_flag(reg, rows, by_flag[iid], dec, rec, by, on, note)
            elif iid in by_prop:
                _apply_proposal(rows, by_prop[iid], dec, rec, by, on, note)
            elif iid in by_row:
                _apply_row(by_row[iid], dec, rec, by, on, note)
            else:
                raise ValueError("no such item")
            out["applied"].append((iid, dec))
        except ValueError as e:
            out["errors"].append((iid, dec, str(e)))
    return out


def _confirm_row(row, treatment, by, on, note, scope=None):
    row["trust"] = "reviewer_confirmed"
    row["verification"] = {"by": by, "on": on, "basis": "reviewer's decision at the weekly review"}
    if treatment:
        row["treatment"] = treatment
    if scope:
        row["scope"] = scope
    row.setdefault("review", {})["last"] = on
    row["review"]["next_due"] = None
    _event(row, f"confirmed by the reviewer as {row['treatment']}", by, on, note)


def _apply_row(row, dec, rec, by, on, note):
    nt = (rec.get("new_treatment") or "").strip()
    if nt and nt not in R.TREATMENTS:
        raise ValueError(f"unknown treatment {nt!r}")
    if dec == "keep":
        _keep(row, on, by)
    elif dec == "confirm":
        if row["trust"] in ("candidate", "unchecked"):
            _confirm_row(row, nt or None, by, on, note, (rec.get("scope") or "").strip() or None)
        else:
            if (nt or row["treatment"]) == "disputed_listing":
                raise ValueError("give new_treatment (overruled or reversed_on_appeal) when confirming a disputed listing")
            if nt:
                row["treatment"] = nt
            rv = row.setdefault("review", {})
            rv["last"], rv["next_due"] = on, None
            rv["chain_ok" if (rec.get("evidence") or "").startswith("The overruling decision") else "listing_ok"] = on
            _event(row, "status confirmed as recorded" + (f", treatment {nt}" if nt else ""), by, on, note)
    elif dec == "change":
        if not nt and not (rec.get("overruling_case") or "").strip():
            raise ValueError("change needs new_treatment or overruling_case")
        if nt:
            row["treatment"] = nt
        if (rec.get("overruling_case") or "").strip():
            row["overruling"]["name"] = rec["overruling_case"].strip()
            if (rec.get("overruling_year") or "").strip():
                row["overruling"]["year"] = int(rec["overruling_year"])
        if (rec.get("scope") or "").strip():
            row["scope"] = rec["scope"].strip()
        if row["trust"] in ("candidate", "unchecked"):
            _confirm_row(row, None, by, on, note)
        else:
            _event(row, f"changed by the reviewer (treatment {row['treatment']})", by, on, note)
        row.setdefault("review", {})["next_due"] = None
    elif dec == "reject":
        if row["trust"] not in ("candidate", "unchecked"):
            raise ValueError("a verified or confirmed row is not rejected here: use change")
        row["trust"] = "rejected"
        _event(row, "rejected by the reviewer", by, on, note)
    elif dec == "supply":
        cites, yr = (rec.get("overruled_cites") or "").strip(), (rec.get("overruled_year") or "").strip()
        if not cites and not yr:
            raise ValueError("supply needs overruled_cites or overruled_year")
        o = row["overruled"]
        if cites:
            o["cites"] = list(o.get("cites", [])) + [c.strip() for c in re.split(r"\s+:\s+|;", cites) if c.strip()]
            o["keys"] = R.key_set(" ; ".join(o["cites"]))
        if yr:
            o["year"] = int(yr)
            o["years"] = sorted(set(o.get("years", [])) | {int(yr)})
        row["flags"] = [f for f in row["flags"] if f != "needs_citation_or_year"]
        _event(row, "citation or year supplied by the reviewer", by, on, note)
    else:
        raise ValueError(f"unknown decision {dec!r}")


def _apply_flag(reg, rows, flag, dec, rec, by, on, note):
    if dec == "keep_open" or dec == "keep":
        flag["next_due"] = _plus(on)
        _event(flag, "kept open at the weekly review", by, on)
        return
    if dec == "clear":
        flag["state"] = "cleared"
        flag["decided_by"], flag["decided_on"] = by, on
        _event(flag, "cleared by the reviewer", by, on, note)
        return
    if dec not in CONFIRMS:
        raise ValueError(f"unknown decision {dec!r}")
    treatment = CONFIRMS[dec]
    c = flag["case"]
    held = [h["row"] for h in reg.lookup_case(c["name"], c.get("year"), c.get("citation")) if h["strength"] == "strong" and h["row"]["trust"] != "rejected"]
    if held:
        for row in held:
            _confirm_row(row, treatment, by, on, note, (rec.get("scope") or "").strip() or None)
        ids = [r["id"] for r in held]
    else:
        oc = (rec.get("overruling_case") or "").strip()
        oy = (rec.get("overruling_year") or "").strip()
        if not oc or not oy:
            raise ValueError("not in the register: give overruling_case and overruling_year to confirm")
        n = 1 + max([int(r["id"].split("-")[1]) for r in rows if r["id"].startswith("RC-")] or [0])
        row = {"id": f"RC-{n:03d}", "source": "checker_flag", "trust": "candidate",
               "overruled": {"name": c["name"], "alt_names": [], "court": "SC", "court_detail": "Supreme Court", "cites": [c["citation"]] if c.get("citation") else [],
                             "keys": R.key_set(c.get("citation") or ""), "year": c.get("year"), "years": [c["year"]] if c.get("year") else []},
               "overruling": {"name": oc, "court": "SC", "cites": [], "keys": [], "year": int(oy), "date": None, "bench": None, "doc_key": None},
               "treatment": treatment, "scope": (rec.get("scope") or "").strip() or None, "court_words": None, "same_parties": False, "flags": [],
               "evidence": {"kind": "checker_flag", "ref": flag["id"], "basis": "checker evidence, confirmed by the reviewer"}, "verification": None, "note": flag.get("note") or "",
               "history": [{"on": on, "by": by, "event": f"created from checker flag {flag['id']}"}]}
        _confirm_row(row, treatment, by, on, note)
        rows.append(row)
        ids = [row["id"]]
    flag["state"] = "confirmed"
    flag["decided_by"], flag["decided_on"], flag["register_rows"] = by, on, ids
    _event(flag, f"confirmed by the reviewer as {treatment}; register rows {', '.join(ids)}", by, on, note)


def _apply_proposal(rows, prop, dec, rec, by, on, note):
    if dec == "keep":
        prop["next_due"] = _plus(on)
        _event(prop, "kept at the weekly review", by, on)
    elif dec == "reject":
        prop["state"] = "rejected"
        _event(prop, "rejected by the reviewer", by, on, note)
    elif dec == "add_row":
        name = (rec.get("case") or prop.get("overruled_name") or "").strip()
        cites = (rec.get("overruled_cites") or prop.get("overruled_cites") or "").strip()
        yr = (rec.get("overruled_year") or "").strip()
        if not name or not (yr or cites):
            raise ValueError("add_row needs the overruled case's name and a year or citation")
        nt = (rec.get("new_treatment") or "overruled").strip()
        if nt not in R.TREATMENTS:
            raise ValueError(f"unknown treatment {nt!r}")
        n = 1 + max([int(r["id"].split("-")[1]) for r in rows if r["id"].startswith("RS-")] or [0])
        yrs = [int(yr)] if yr else []
        row = {"id": f"RS-{n:03d}", "source": "sweep", "trust": "reviewer_confirmed",
               "overruled": {"name": name, "alt_names": [], "court": "SC", "court_detail": "Supreme Court", "cites": [cites] if cites else [], "keys": R.key_set(cites), "year": yrs[0] if yrs else None,
                             "years": yrs},
               "overruling": {"name": prop["title"].replace(" versus ", " v. "), "court": "SC", "cites": [], "keys": [], "year": int((prop.get("date") or "0")[:4]) or None,
                              "date": prop.get("date"), "bench": prop.get("bench"), "doc_key": prop["doc_key"]},
               "treatment": nt, "scope": (rec.get("scope") or "").strip() or None, "court_words": prop.get("evidence") if prop["kind"] == "sentence" else None, "same_parties": False, "flags": [],
               "evidence": {"kind": "law_report_headnote" if prop["kind"] == "tag" else "judgment_text", "ref": prop["doc_key"], "basis": "sweep proposal, confirmed by the reviewer"},
               "verification": {"by": by, "on": on, "basis": "reviewer's decision at the weekly review"}, "note": "", "history": [{"on": on, "by": by, "event": f"added from sweep proposal {prop['id']}"}]}
        rows.append(row)
        prop["state"] = "added"
        prop["register_row"] = row["id"]
        _event(prop, f"added to the register as {row['id']}", by, on, note)
    else:
        raise ValueError(f"unknown decision {dec!r}")
