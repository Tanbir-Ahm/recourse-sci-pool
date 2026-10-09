#!/usr/bin/env python3
"""Prepares saved reviewer replies for ingest_llm_reviews.py without touching a single mark.

    python review_tools/normalise_replies.py --src DIR_AS_RECEIVED --out DIR_FOR_THE_READER [--drop R06_A_ChatGPT.txt --drop R02_A_ChatGPT.txt ...]

What it does (and nothing else):
  1. Undoes the Markdown escaping that copying a reply out of a chat window can add: a backslash before an underscore or a square bracket (\\_ \\[ \\]) is removed. These three sequences are not valid JSON, so a
     reply that contains them cannot be read at all until they go; removing them changes no word, no mark, no number. Any other backslash (\\" \\n \\\\ and so on) is left exactly as it is.
  2. Reports files that are not replies (the saved text is the prompt, recognisable by its opening line or its closing line) and files that are byte-identical to another file (the same reply saved under two
     names). It never drops a file on its own: a file named with --drop is left out of the output folder and the reason is written to the manifest; everything else is copied.
Writes OUT/<files> and, next to OUT (not inside it, so the reader does not see it), OUT_NORMALISATION.json (per file: sha256 as received, sha256 as written, how many escapes were removed, whether it was dropped, and the problems found). The files as received stay untouched.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys

ESCAPES = re.compile(r"\\([_\[\]])")
PROMPT_OPEN = re.compile(r"^\s*QUESTION ID:\s*\S+\s*\(prompt version")
PROMPT_CLOSE = re.compile(r"END OF PASSAGES\.\s*Now reply with the single JSON object")


def unescape_markdown(text):
    """Returns (text without the escapes a chat window's copy button adds, number of escapes removed)."""
    out, n = ESCAPES.subn(r"\1", text)
    return out, n


def is_prompt_echo(text):
    return bool(PROMPT_OPEN.match(text) or PROMPT_CLOSE.search(text[-400:]))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(src, out, drop=()):
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
        entry = {"sha256_as_received": sha(raw[f]), "markdown_escapes_removed": n, "problems": problems, "dropped": f in drop}
        if f in drop:
            entry["sha256_as_written"] = None
        else:
            data = new.encode("utf-8")
            with open(os.path.join(out, f), "wb") as fh:
                fh.write(data)
            entry["sha256_as_written"] = sha(data)
        manifest["files"][f] = entry
    with open(os.path.normpath(out) + "_NORMALISATION.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--drop", action="append", default=[], help="a file to leave out (not a reply, or a duplicate); may be repeated")
    a = ap.parse_args(argv)
    m = run(a.src, a.out, a.drop)
    n = sum(e["markdown_escapes_removed"] for e in m["files"].values())
    print(f"{len(m['files'])} files read; {sum(1 for e in m['files'].values() if e['dropped'])} left out; {n} markdown escapes removed in {sum(1 for e in m['files'].values() if e['markdown_escapes_removed'])} files")
    for f, e in m["files"].items():
        if e["problems"]:
            print(f"  {f}: {'; '.join(e['problems'])}" + ("  [LEFT OUT]" if e["dropped"] else "  [KEPT: decide]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
