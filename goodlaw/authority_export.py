"""A lawyer's list of cases as a spreadsheet file (CSV), each with what we know about its later treatment, the date that evidence is as of, and a note that travels with the row.

Offline: it reads the register and the cards through goodlaw/chat_format.py (so a row says what a result message says), writes a file, and sends nothing. Nothing is connected to any service.

    f = Formatter(Register.load(), cardreader.load("cards/currency_cards.json"), quiet_policy="coverage_note")
    rows = build_rows(f, [{"name": "Mohan Lal v State of Punjab", "year": 2018, "citation": "(2018) 17 SCC 627"}, ...])
    write_csv(rows, "authorities_2026-10-22.csv")                    # or export_watchlist(wl, path) for a saved watchlist

Columns: case, year, citation, status, what_we_know, evidence_as_of, checked_by, also, section_numbers, exported_on, note. Every row has a status and a note, so a spreadsheet row is never silent:
a case with nothing adverse says "No warning found in what we hold" and that this is not a finding, and an unchecked case says "Not checked by us". The file does not follow the formatter's `quiet_policy`
(whether a quiet card gets a line in a chat message was decided on 2026-10-22 as "coverage_note", see goodlaw/data/pilot_settings.json; the file would spell it out whatever the chat setting): a blank status cell would read as "fine".

The note says what kind of reading the row is: a register row a person confirmed, a register row not yet confirmed, the checker's pattern-rule reading (not lawyer-validated), or not checked. Rows are
ordered most pressing first (confirmed register rows, then other warnings, then cautions, then not checked, then no warning found); within a group the input order is kept, or pass `order="input"`.

Spreadsheet safety: a cell that starts with = + - @ or a tab or return would be run as a formula by Excel or Sheets, so such a cell gets a leading apostrophe; whitespace and line breaks inside a cell
become single spaces; the file is UTF-8 with a byte-order mark, so Excel reads the Indian-language names and the curly quotes correctly. No wording of ours claims a case is good law
(chat_format's guard runs on every row; a register row's own "held not to be good law in" is a court's holding and is allowed).
"""
import csv
import io
import re
from datetime import date

from . import chat_format as CF
from . import watchlist as W

COLUMNS = ["case", "year", "citation", "status", "what_we_know", "evidence_as_of", "checked_by", "also", "section_numbers", "exported_on", "note"]
INTERNAL_COLUMN = "internal_refs"
NOTES = {
    1: "From the Overruled Register: a row a lawyer reviewed or confirmed. The register records only decisions that a later Supreme Court judgment overruled; it shows no other treatment and says nothing about cases not on it.",
    2: "From the Overruled Register: a row not yet confirmed by our reviewer. Treat it as a pointer to check, not as a fact.",
    3: "Pattern-rule reading of Supreme Court texts, not lawyer-validated. It points to a judgment to read; it is not a ruling on the case.",
    4: "Pattern-rule reading of Supreme Court texts, not lawyer-validated. It points to judgments to read; it is not a ruling on the case.",
    5: "Pattern-rule reading of Supreme Court texts, not lawyer-validated. The checker catches only some overrulings, and our collection lacks some judgments, so this is not a finding that the case is good law.",
    6: "Not checked. Verify the case yourself before you cite it.",
}
CHECKED_BY = {
    1: "Overruled Register (reviewed list)",
    2: "Overruled Register (candidate row, not yet confirmed)",
    3: "Checker (pattern-rule reading)",
    4: "Checker (pattern-rule reading)",
    5: "Checker (nothing adverse found in what we hold)",
    6: "",
}
_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value):
    """A cell's text: whitespace and line breaks as single spaces, and an apostrophe in front of anything a spreadsheet would run as a formula."""
    s = re.sub(r"\s+", " ", "" if value is None else str(value)).strip()
    return "'" + s if s.startswith(_FORMULA) else s


def _order_key(rule, firm, i):
    """Most pressing first: a confirmed register row, a warning a person confirmed, any other warning, a caution, not checked, no warning found; input order within a group."""
    if rule == 1:
        return (0, i)
    if rule == 3 and firm:
        return (1, i)
    if rule in (2, 3):
        return (2, i)
    return ({4: 3, 6: 4, 5: 5}.get(rule, 6), i)


def build_rows(formatter, cases, exported_on=None, include_internal=False, order="severity"):
    """One row per distinct case (by the watchlist's key), as a dict of COLUMNS. `cases` are {name, year, citation, label (optional)}."""
    f = CF.Formatter(formatter.register, formatter.cards, quiet_policy="coverage_note", today=formatter.today)       # the file always spells a quiet case out
    on = str(exported_on)[:10] if exported_on else (str(formatter.today)[:10] if formatter.today else date.today().isoformat())
    seen, items = set(), []
    for i, c in enumerate(cases):
        name = (c.get("name") or "").strip()
        if not name:
            raise ValueError("every case needs a name")
        key = W.watch_key(name, c.get("year"), c.get("citation"))
        if key in seen:
            continue
        seen.add(key)
        cur = f.currency(name, c.get("year"), c.get("citation"))
        main = [l for l in cur.lines if l.level != CF.INFO]
        statute = next((l for l in cur.lines if l.level == CF.INFO), None)
        lead = main[0]
        know = ("Nothing adverse found in the later Supreme Court judgments we hold. " + lead.body) if lead.rule == 5 else lead.body
        also = "; ".join(f"{l.headline}: {l.body}" for l in main[1:])
        row = {"case": c.get("label") or name, "year": c.get("year") or "", "citation": c.get("citation") or "", "status": lead.headline, "what_we_know": know,
               "evidence_as_of": lead.as_of or "", "checked_by": CHECKED_BY[lead.rule] if not (lead.rule == 3 and lead.firm) else "Checker, confirmed by our reviewer",
               "also": also, "section_numbers": statute.body if statute else "", "exported_on": on, "note": NOTES[lead.rule]}
        if include_internal:
            row[INTERNAL_COLUMN] = "; ".join(l.key for l in cur.lines)
        bad = CF.wording_violations(" ".join(str(row[k]) for k in ("status", "what_we_know", "also", "section_numbers", "note")))
        if bad:
            raise CF.WordingError(f"a row contains {bad}: nothing was written")
        items.append((i, lead.rule, lead.firm, row))
    if order == "severity":
        items.sort(key=lambda it: _order_key(it[1], it[2], it[0]))
    elif order != "input":
        raise ValueError("order must be 'severity' or 'input'")
    return [r for *_, r in items]


def _columns(rows):
    return COLUMNS + ([INTERNAL_COLUMN] if rows and INTERNAL_COLUMN in rows[0] else [])


def to_csv_text(rows):
    """The file's text (without the byte-order mark)."""
    buf = io.StringIO(newline="")
    w = csv.writer(buf)
    cols = _columns(rows) if rows else COLUMNS
    w.writerow(cols)
    for r in rows:
        w.writerow([safe_cell(r.get(c)) for c in cols])
    return buf.getvalue()


def write_csv(rows, path):
    """Writes the file as UTF-8 with a byte-order mark (so Excel reads it correctly). Returns the number of rows."""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(to_csv_text(rows))
    return len(rows)


def cases_from_watchlist(wl):
    """The saved cases of a Watchlist as export cases, in the order they were saved."""
    return [{"name": c["name"], "year": c["year"], "citation": c["citation"], "label": c["label"]} for c in wl.cases().values()]


def export_watchlist(wl, path, exported_on=None, include_internal=False):
    return write_csv(build_rows(wl.formatter, cases_from_watchlist(wl), exported_on, include_internal), path)
