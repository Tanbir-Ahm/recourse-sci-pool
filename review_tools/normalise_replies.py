#!/usr/bin/env python3
"""Prepares saved reviewer replies for ingest_llm_reviews.py without touching a single mark.

    python review_tools/normalise_replies.py --src DIR_AS_RECEIVED --out DIR_FOR_THE_READER [--drop R06_A_ChatGPT.txt --drop R02_A_ChatGPT.txt ...] [--manifest PATH]

What it does (and nothing else):
  1. Undoes the Markdown escaping that copying a reply out of a chat window can add: a backslash before an underscore, a square bracket or a backtick (\\_ \\[ \\] \\`) is removed. These four sequences are not valid JSON, so a
     reply that contains them cannot be read at all until they go; removing them changes no word, no mark, no number. (The backtick was added on 2026-10-10 after the third batch, when two ChatGPT replies, and the
     two re-asked replies after them, all carried a backslash before a backtick that a passage contained.) Any other backslash (\\" \\n \\\\ and so on) is left exactly as it is, with the one exception in 1b.
  1b. Only for a file that still cannot be read after step 1: if every doubled backslash before a quotation mark (\\\\") is turned into a single one (\\") and the file then CAN be read, that is written; otherwise the
     file is left as it was. The copy button turns a quoted \\" into \\\\" when a quote inside a reply holds quotation marks. The (number, mark) pairs are compared before and after and must be identical, or nothing is changed.
     A file that already reads is never touched by 1b.
  2. Reports files that are not replies (the saved text is the prompt, recognisable by its opening line or its closing line) and files that are byte-identical to another file (the same reply saved under two
     names). It never drops a file on its own: a file named with --drop is left out of the output folder and the reason is written to the manifest; everything else is copied.
Writes OUT/<files> and, next to OUT (not inside it, so the reader does not see it), OUT_NORMALISATION.json (per file: sha256 as received, sha256 as written, how many escapes were removed, whether it was dropped, and the problems found). The files as received stay untouched.
A later upload (for example two replies that were missing) is added to an existing OUT folder with a second run and its own --manifest PATH, so the first manifest is not overwritten.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys

ESCAPES = re.compile(r"\\([_\[\]`])")
DOUBLED_QUOTE = re.compile(r'\\\\"')
MARK_PAIRS = re.compile(r'"no"\s*:\s*(\d+)\s*,\s*"mark"\s*:\s*"([A-Za-z]+)"')
PROMPT_OPEN = re.compile(r"^\s*QUESTION ID:\s*\S+\s*\([^)\n]*prompt version")          # '(prompt version: order A)' and '(top-up batch, prompt version: order A)'
PROMPT_CLOSE = re.compile(r"END OF PASSAGES\.\s*Now reply with the single JSON object")


def unescape_markdown(text):
    """Returns (text without the escapes a chat window's copy button adds, number of escapes removed)."""
    out, n = ESCAPES.subn(r"\1", text)
    return out, n


def repair_doubled_quote_escapes(text):
    """Returns (text, number of changes). Changes nothing unless the text cannot be read as JSON, the change makes it readable, and the (number, mark) pairs are identical before and after."""
    try:
        json.loads(text)
        return text, 0
    except ValueError:
        pass
    fixed, n = DOUBLED_QUOTE.subn(r'\\"', text)
    if not n or MARK_PAIRS.findall(fixed) != MARK_PAIRS.findall(text):
        return text, 0
    try:
        json.loads(fixed)
    except ValueError:
        return text, 0
    return fixed, n


def is_prompt_echo(text):
    return bool(PROMPT_OPEN.match(text) or PROMPT_CLOSE.search(text[-400:]))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(src, out, drop=(), manifest_path=None):
    names = sorted(f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f)))
    raw = {f: open(os.path.join(src, f), "rb").read() for f in names}
    same = {}
    for f, b in raw.items():
        same.setdefault(sha(b), []).append(f)
    dups = {h: fs for h, fs in same.items() if len(fs) > 1}
    drop = set(drop)
    unknown = drop - set(names)
    if unknown:
        raise SystemExit(f"--drop names files that are not in {src}: {sorted(unknown)}")
    os.makedirs(out, exist_ok=True)
    manifest = {"source_folder": os.path.abspath(src), "files": {}, "identical_files": sorted(dups.values()), "prompt_echoes": []}
    for f in names:
        text = raw[f].decode("utf-8")
        problems = []
        if is_prompt_echo(text):
            problems.append("the saved text is the prompt, not a reply")
            manifest["prompt_echoes"].append(f)
        for fs in dups.values():
            if f in fs:
                problems.append("byte-identical to " + ", ".join(x for x in fs if x != f))
        new, n = unescape_markdown(text)
        new, n2 = repair_doubled_quote_escapes(new)
        entry = {"sha256_as_received": sha(raw[f]), "markdown_escapes_removed": n, "doubled_quote_escapes_repaired": n2, "problems": problems, "dropped": f in drop}
        if f in drop:
            entry["sha256_as_written"] = None
        else:
            data = new.encode("utf-8")
            with open(os.path.join(out, f), "wb") as fh:
                fh.write(data)
            entry["sha256_as_written"] = sha(data)
        manifest["files"][f] = entry
    with open(manifest_path or os.path.normpath(out) + "_NORMALISATION.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--drop", action="append", default=[], help="a file to leave out (not a reply, or a duplicate); may be repeated")
    ap.add_argument("--manifest", default=None, help="where to write the manifest (default: OUT_NORMALISATION.json next to OUT); use it when adding a later upload to an existing OUT folder")
    a = ap.parse_args(argv)
    m = run(a.src, a.out, a.drop, a.manifest)
    n = sum(e["markdown_escapes_removed"] for e in m["files"].values())
    print(f"{len(m['files'])} files read; {sum(1 for e in m['files'].values() if e['dropped'])} left out; {n} markdown escapes removed in {sum(1 for e in m['files'].values() if e['markdown_escapes_removed'])} files; "
          f"doubled-quote escapes repaired in {sum(1 for e in m['files'].values() if e['doubled_quote_escapes_repaired'])} files")
    for f, e in m["files"].items():
        if e["problems"]:
            print(f"  {f}: {'; '.join(e['problems'])}" + ("  [LEFT OUT]" if e["dropped"] else "  [KEPT: decide]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
