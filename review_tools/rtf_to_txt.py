"""Turns reply files saved as Rich Text (.rtf, for example from Mac TextEdit) into plain-text reply files the reader accepts.

A reviewer who pastes an AI tool's JSON reply into a rich-text editor gets a .rtf file in which every brace is escaped
(\\{ \\}), every line break is a U+2028 character, and curly quotes are escape codes. This script undoes that, character
for character, and names each file the way the reader expects: Q<question>_<A|B|TA|TB>_<tool>.txt.

    python review_tools/rtf_to_txt.py IN_DIR OUT_DIR --tool ChatGPT-J

The question number comes from the file name (A01_A.rtf, Q01_A.rtf and Q01_A_anything.rtf all mean question 1, order A) and
is checked against the "question_id" inside the reply; a mismatch is reported and the file is skipped, never guessed at.
Nothing in IN_DIR is changed. The converted text is not edited in any other way, so the reader's quote check
(every "evidence" quote must appear word for word in its passage) still tests the reviewer's reply, not this script.
"""
import argparse
import json
import os
import re
import sys

_SKIP_DESTINATIONS = {"fonttbl", "colortbl", "expandedcolortbl", "stylesheet", "info", "pict", "header", "footer", "listtable", "listoverridetable", "generator"}
_SYMBOLS = {"emdash": "—", "endash": "–", "lquote": "‘", "rquote": "’", "ldblquote": "“", "rdblquote": "”", "bullet": "•", "tab": "\t", "par": "\n", "line": "\n"}
_NAME_RE = re.compile(r"^[A-Za-z]?(\d{1,2})_(T?[AB])(?:_.*)?\.rtf$", re.I)


def rtf_to_text(rtf):
    """Plain text of an RTF string. Handles groups, escaped symbols, \\'hh (Windows-1252), \\uN with fallback characters, and paragraph marks."""
    out, i, n = [], 0, len(rtf)
    stack = []                        # one (skip, uc) pair per open group
    skip, uc = False, 1
    pending_skip_chars = 0            # fallback characters still to drop after a \uN
    while i < n:
        c = rtf[i]
        if c == "{":
            stack.append((skip, uc)); i += 1
            if rtf.startswith("\\*", i):
                skip = True
            continue
        if c == "}":
            if stack:
                skip, uc = stack.pop()
            i += 1
            continue
        if c == "\\":
            i += 1
            if i >= n:
                break
            d = rtf[i]
            if d in "\\{}":
                if not skip and not pending_skip_chars:
                    out.append(d)
                elif pending_skip_chars:
                    pending_skip_chars -= 1
                i += 1
            elif d == "'":
                hexpair = rtf[i + 1:i + 3]
                i += 3
                if pending_skip_chars:
                    pending_skip_chars -= 1
                elif not skip:
                    out.append(bytes([int(hexpair, 16)]).decode("cp1252", "replace"))
            elif d in "\r\n":
                if not skip:
                    out.append("\n")
                i += 1
            elif d == "~":
                if not skip:
                    out.append(" ")
                i += 1
            elif d in "-_*":
                i += 1
            elif d.isalpha():
                m = re.compile(r"([a-zA-Z]+)(-?\d+)? ?").match(rtf, i)
                word, param = m.group(1), m.group(2)
                i = m.end()
                if word in _SKIP_DESTINATIONS:
                    skip = True
                elif word == "uc":
                    uc = int(param or 1)
                elif word == "u":
                    if not skip:
                        cp = int(param)
                        out.append(chr(cp + 65536 if cp < 0 else cp))
                    pending_skip_chars = uc
                elif word in _SYMBOLS and not skip:
                    out.append(_SYMBOLS[word])
            else:
                i += 1
            continue
        if c in "\r\n":                # a physical line break in the file is not text in RTF
            i += 1
            continue
        if pending_skip_chars:
            pending_skip_chars -= 1
        elif not skip:
            out.append(c)
        i += 1
    text = "".join(out).replace(" ", "\n").replace(" ", "\n")
    return text.strip() + "\n"


_LABEL = re.compile(r"\A\s*json[ \t]*\n", re.I)


def convert_folder(in_dir, out_dir, tool, out=print):
    """Converts every .rtf in in_dir. Returns (converted names, problems)."""
    os.makedirs(out_dir, exist_ok=True)
    done, problems = [], []
    for name in sorted(os.listdir(in_dir)):
        if not name.lower().endswith(".rtf"):
            continue
        m = _NAME_RE.match(name)
        if not m:
            problems.append(f"{name}: file name not understood (expected something like A01_A.rtf or Q01_A.rtf)")
            continue
        qn, order = int(m.group(1)), m.group(2).upper()
        text = rtf_to_text(open(os.path.join(in_dir, name), "r", encoding="cp1252", errors="replace").read())
        label = _LABEL.match(text)            # a tool's code box has a heading ("JSON") that comes along when the reply is copied; it is not part of the reply
        if label:
            text = text[label.end():].lstrip("\n")
        try:
            qid = json.loads(text).get("question_id")
        except Exception as e:
            problems.append(f"{name}: not valid JSON after conversion ({str(e)[:80]})")
            continue
        if qid != f"Q{qn:02d}":
            problems.append(f"{name}: file name says question {qn:02d} but the reply says {qid!r}; skipped")
            continue
        new = f"Q{qn:02d}_{order}_{tool}.txt"
        with open(os.path.join(out_dir, new), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        done.append(new)
        out(f"{name} -> {new}" + ("  (a leading 'JSON' label copied from the tool's code box was dropped; nothing else was changed)" if label else ""))
    return done, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("in_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--tool", required=True, help="tool name plus initials, for example ChatGPT-J")
    a = ap.parse_args(argv)
    done, problems = convert_folder(a.in_dir, a.out_dir, a.tool)
    for p in problems:
        print("PROBLEM:", p)
    print(f"{len(done)} converted, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
