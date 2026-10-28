"""Join the readings of the pages of one document into one text, so a sentence that runs over a page break is translated whole (plan section 10t).

  python stitch.py --selftest

Why: translating page by page cut sentences at the page break (6 of 8 breaks in the first Kannada file) and made the model guess singular or plural
("appellant" became "appellants" six times). Translating the joined text twice gave neither fault. No model is used here; this only joins text.

  stitch_pages({1: text, 2: text, ...})  ->  (joined text, log)
Each page's text is the original-script reading (the part of a reading before the TRANSLATION heading) or a PDF's own text layer.
Rules, all visible in the log so a person can check each join:
  - a line that holds only a page number (1 to 3 digits) at the top of a page is dropped from the joined text and named in the log;
  - a page whose last line does not end a sentence (no full stop, danda, question or exclamation mark, colon, closing quote or bracket) and is not a
    separator line (-oOo-, -000-) is JOINED to the next page with a space; otherwise the next page starts a new paragraph;
  - nothing else is changed, added or tidied. A heading or list line that ends a page without a full stop is joined by mistake: that costs a missing
    paragraph break, never a lost word, and the log shows it.
"""
import re

END = ".?!:;)]}”\"'’।৷॥…"          # full stop, danda (Devanagari, Bengali, double), closing quotes and brackets
SEPARATOR = re.compile(r"^[\s\-_–—*=~.oO0]{3,}$")        # -oOo-, -000-, ****, ----


def source_lines(reading):
    """The original-script lines of a harness reading (everything before the TRANSLATION heading), or the whole text if there is no heading."""
    t = reading or ""
    i = t.rfind("TRANSLATION")
    head = t[:i] if i >= 0 else t
    head = re.sub(r"^\s*[*#]*\s*TRANSCRIPTION[*:#]*[ \t]*\n?", "", head, count=1)
    lines = [l.rstrip() for l in head.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def stitch_pages(pages):
    """pages: {page number: text of that page}. Returns (text, log) with one log entry per page break and per dropped page-number line."""
    out, log = [], []
    for n in sorted(pages):
        lines = source_lines(pages[n])
        if lines and re.fullmatch(r"\d{1,3}", lines[0].strip()):
            log.append({"page": n, "action": "dropped the first line (a page number)", "line": lines[0].strip()})
            lines = lines[1:]
            while lines and not lines[0].strip():
                lines.pop(0)
        if not lines:
            log.append({"page": n, "action": "no text on this page"})
            continue
        prev = next((l.strip() for l in reversed(out) if l.strip()), "")
        if prev:
            mid = prev[-1] not in END and not SEPARATOR.match(prev)
            log.append({"page": n, "action": "joined to the previous page (it ends mid-sentence)" if mid else "new paragraph",
                        "previous_page_ends": prev[-30:], "this_page_starts": lines[0].strip()[:30]})
            if mid:
                out[-1] = out[-1].rstrip() + " " + lines[0].lstrip()
                lines = lines[1:]
            else:
                out.append("")
        out += lines
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    return text, log


def selftest():
    p = {1: "TRANSCRIPTION:\n1\n\nfirst words of a long\nsentence that goes on and\n\nTRANSLATION\nignored",
         2: "TRANSCRIPTION:\n2\n\non the next page. A second sentence ends here.\n\nTRANSLATION\nignored",
         3: "TRANSCRIPTION:\n\nNew paragraph on page three.\n-oOo-\n\nTRANSLATION\nx",
         4: "TRANSCRIPTION:\n(c) a heading line\n\nTRANSLATION\nx"}
    text, log = stitch_pages(p)
    assert text == "first words of a long\nsentence that goes on and on the next page. A second sentence ends here.\n\nNew paragraph on page three.\n-oOo-\n\n(c) a heading line", repr(text)
    acts = [(x["page"], x["action"].split(" (")[0]) for x in log]
    assert (1, "dropped the first line") in acts and (2, "dropped the first line") in acts, acts
    assert (2, "joined to the previous page") in acts and (3, "new paragraph") in acts and (4, "new paragraph") in acts, acts          # a separator line ends a page
    t2, l2 = stitch_pages({1: "TRANSCRIPTION\nಅಆ ಇ.\n", 2: "TRANSCRIPTION\n\n\nTRANSLATION\n"})
    assert t2 == "ಅಆ ಇ." and l2[-1]["action"] == "no text on this page", (t2, l2)
    t3, _ = stitch_pages({1: "অসমীয়া পরিও।", 2: "নতুন পাতা"})
    assert t3 == "অসমীয়া পরিও।\n\nনতুন পাতা", repr(t3)           # a danda ends a sentence
    print("selftest OK (invented text only)")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        selftest()
    else:
        sys.exit(__doc__)
