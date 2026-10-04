"""Tests for rtf_to_txt.py with synthetic Rich Text only (nothing real). Run: python review_tools/test_rtf_to_txt.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rtf_to_txt as r2t

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


BS = chr(92)                                  # a backslash; the RTF escapes below are built from it so no "backslash-u" ever appears in this source


def U(n):
    """The RTF escape for Unicode code point n, followed by its delimiter space."""
    return BS + "u" + str(n) + " "


HEAD = ("{" + BS + "rtf1" + BS + "ansi" + BS + "ansicpg1252" + BS + "cocoartf2822\n"
        "{" + BS + "fonttbl" + BS + "f0" + BS + "froman" + BS + "fcharset0 Times-Roman;}\n"
        "{" + BS + "colortbl;" + BS + "red255" + BS + "green255" + BS + "blue255;}\n"
        "{" + BS + "*" + BS + "expandedcolortbl;;" + BS + "cssrgb" + BS + "c0" + BS + "c0" + BS + "c0;}\n"
        + BS + "pard" + BS + "pardeftab720" + BS + "sa240\n\n" + BS + "f0" + BS + "fs24 " + BS + "cf0 " + BS + "outl0" + BS + "strokewidth0 " + BS + "strokec2 ")

# the way Mac TextEdit stores a pasted JSON reply: escaped braces, U+2028 line breaks (decimal 8232), a paragraph mark at the end
LB = U(8232)
body = (BS + "{" + BS + "uc0" + LB + '"question_id": "Q01",' + LB + '"marks": [' + LB + BS + "{" + LB + '"no": 1,' + LB
        + '"evidence": "the court' + BS + "'92s view " + U(8211) + ' and ' + U(8220) + 'this' + U(8221) + '",' + LB
        + '"path": "a' + BS + BS + 'b"' + LB + BS + "}" + LB + "]" + LB + BS + "}" + BS + "\n}")
text = r2t.rtf_to_text(HEAD + body)
obj = json.loads(text)
check("escaped braces and U+2028 line breaks become plain JSON", obj["question_id"] == "Q01" and obj["marks"][0]["no"] == 1, text[:120])
check("a hex escape for 0x92 becomes a curly apostrophe (Windows-1252)", "court" + chr(0x2019) + "s view" in obj["marks"][0]["evidence"])
check("Unicode escapes keep their characters (en dash, curly quotes) and drop no real text",
      obj["marks"][0]["evidence"] == "the court" + chr(0x2019) + "s view " + chr(0x2013) + " and " + chr(0x201c) + "this" + chr(0x201d), obj["marks"][0]["evidence"])
check("an escaped backslash stays a single backslash in the text (JSON itself reads backslash-b as a backspace, so the raw text is checked)", ("a" + BS + "b") in text and ("a" + BS + BS + "b") not in text)
check("header groups (fonts, colours) leave no text behind", "Times" not in text and "cssrgb" not in text and "255" not in text)
check("no escaped braces are left in the text", BS + "{" not in text and BS + "}" not in text)
check("a fallback character after a Unicode escape is skipped when uc1 is in force", r2t.rtf_to_text("{" + BS + "rtf1 a" + BS + "u8364?b}").strip() == "a" + chr(0x20ac) + "b")
check("a physical line break in the file is not text, but a backslash-newline is a paragraph mark",
      r2t.rtf_to_text("{" + BS + "rtf1 one\ntwo" + BS + "\nthree}").strip() == "onetwo\nthree")

with tempfile.TemporaryDirectory() as tmp:
    src, dst = f"{tmp}/in", f"{tmp}/out"
    os.makedirs(src)
    good = lambda q: HEAD + body.replace("Q01", q)
    for name, content in (("A01_A.rtf", good("Q01")), ("A02_B.rtf", good("Q02")), ("Q03_TA.rtf", good("Q03")), ("A04_A.rtf", good("Q05")), ("notes.rtf", good("Q01")), ("A06_A.rtf", HEAD + r"no json here}")):
        open(f"{src}/{name}", "w", encoding="cp1252").write(content)
    open(f"{src}/readme.txt", "w").write("ignored")
    done, problems = r2t.convert_folder(src, dst, "ChatGPT-J", out=lambda *_: None)
    check("files are renamed the way the reader expects", done == ["Q01_A_ChatGPT-J.txt", "Q02_B_ChatGPT-J.txt", "Q03_TA_ChatGPT-J.txt"], done)
    check("a file whose name and question_id disagree is skipped and reported", any("A04_A.rtf" in p and "skipped" in p for p in problems), problems)
    check("a file name that is not understood is reported", any("notes.rtf" in p and "not understood" in p for p in problems), problems)
    check("a reply that is not JSON after conversion is reported", any("A06_A.rtf" in p and "not valid JSON" in p for p in problems), problems)
    check("the input folder is left untouched", sorted(os.listdir(src)) == ["A01_A.rtf", "A02_B.rtf", "A04_A.rtf", "A06_A.rtf", "Q03_TA.rtf", "notes.rtf", "readme.txt"])
    check("converted files parse as JSON", all(json.load(open(f"{dst}/{n}", encoding="utf-8"))["question_id"].startswith("Q") for n in done))

print("\nALL PASSED" if not FAILS else f"\nFAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
