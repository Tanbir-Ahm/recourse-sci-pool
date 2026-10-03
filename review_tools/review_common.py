"""Shared pieces of the review tools: where the pool lives, how to read it, and the wording both AI-reviewer prompt packs use."""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_POOL = os.path.normpath(os.path.join(HERE, "..", "review_data", "pool_all.json"))
ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")        # control characters a spreadsheet will not accept
MARKS = ["Yes", "Partly", "No", "Misleading"]
MEANING = {"Yes": "The passage itself states the rule, test or holding that answers the question directly.",
           "Partly": "On the topic and useful, but it does not fully answer the question (only one part, or only background).",
           "No": "Not helpful for this question.",
           "Misleading": "Read on its own, it could leave a wrong impression. Examples: it records an argument by a lawyer that the court then rejects; it describes another case's facts; it states a rule for a different offence or situation; it is cut off so that it says the opposite of the court's view."}


def clean(s):
    return ILLEGAL.sub("", s or "")


def load_pool(path=None):
    """The pool: a list of questions, each with its passages ('rows'). Rows added later for the top-up batch carry topup=True."""
    with open(path or DEFAULT_POOL, encoding="utf-8") as fh:
        return json.load(fh)


def rows_of(q, topup=False):
    """The question's passages from the first batch (topup=False) or the top-up batch (topup=True), in number order."""
    return sorted((r for r in q["rows"] if bool(r.get("topup")) == topup), key=lambda r: r["n"])


def meaning_lines():
    return "\n".join(f"   - {k}: {v}" for k, v in MEANING.items())


def judgment_text(p):
    """How a passage's judgment is shown to a reviewer: its opening header, id, paragraph and page. Never anything about which search found it."""
    para = f"paragraph {p['pn']}" if p["pn"] else "unnumbered paragraph"
    head = clean(p["title"]) if p["title"] else "Opening header not available"
    return f"{head}\n   (Judgment id {p['doc']}, {para}, page {p['page']})"


def passage_blocks(rows):
    """The passages as prompt lines, in the order given."""
    out = []
    for r in rows:
        out += [f"--- PASSAGE {r['n']} ---", f"Judgment: {judgment_text(r)}"]
        if r["also"]:
            out.append("The same text also appears in judgment id(s): " + ", ".join(str(d) for d in r["also"]))
        out += ["Text:", clean(r["text"]).strip(), ""]
    return out


def write_zip(folder, zip_path, top_name):
    """Zips a folder with every file under top_name/ (stable order)."""
    import zipfile
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(folder):
            dirs.sort()
            for f in sorted(files):
                full = os.path.join(root, f)
                z.write(full, os.path.join(top_name, os.path.relpath(full, folder)))
