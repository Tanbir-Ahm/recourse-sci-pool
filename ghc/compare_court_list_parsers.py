"""Compares reparse_court_lists.py with parse_court_lists.py on the same list PDFs: the rows, their dates and their links must be the same, and every difference between a row read the
old way and the new way must be one of the named kinds; anything else is printed. A word may move from one field to another, but none may be lost or made up.
Usage: python3 -I compare_court_list_parsers.py LISTS_DIR"""
import collections, glob, importlib.util, os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
def load(name):
    s = importlib.util.spec_from_file_location(name, os.path.join(here, name + ".py")); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
old, new = load("parse_court_lists"), load("reparse_court_lists")
FIELDS = ("case_number", "petitioner", "respondent", "subject", "judges")
words = lambda s: collections.Counter(w for w in re.findall(r"[A-Z0-9]+", s.upper()) if w not in ("VS", "V", "S"))

def compare(lists_dir):
    kinds, odd, rows = collections.Counter(), [], 0
    for f in sorted(glob.glob(os.path.join(lists_dir, "*.pdf"))):
        b = os.path.basename(f); ro, rn = old.parse(f)[2], new.parse(f)[2]
        if len(ro) != len(rn): odd.append((b, "row count", len(ro), len(rn))); continue
        for i, (a, c) in enumerate(zip(ro, rn)):
            rows += 1
            if a["date"] != c["date"] or a["judgment_url"] != c["judgment_url"]: odd.append((b, i, "date or link differs")); continue
            lost = (sum((words(a[k]) for k in FIELDS), collections.Counter()) - sum((words(c[k]) for k in FIELDS), collections.Counter()))
            if lost: odd.append((b, i, "words lost", dict(lost))); continue
            if all(a[k] == c[k] for k in FIELDS): kinds["same"] += 1
            elif a["case_number"] != c["case_number"]: kinds["bench in brackets: parties were inside the case number"] += 1
            elif a["petitioner"] != c["petitioner"]: kinds["petitioner had subject or judge text stuck to it"] += 1
            elif a["respondent"] != c["respondent"]:
                kinds["respondent had a judge's name, a statute year or a case type stuck to it" if a["respondent"].startswith(c["respondent"]) else "respondent was empty or a judge's name; now the party"] += 1
            else: kinds["subject or judges only"] += 1
    return rows, kinds, odd

if __name__ == "__main__":
    rows, kinds, odd = compare(sys.argv[1])
    print(rows, "rows")
    for k, v in sorted(kinds.items(), key=lambda x: -x[1]): print(f"  {v:5d}  {k}")
    print(len(odd), "rows with a difference that is not one of the kinds above (words lost, a changed date or link, a changed row count)")
    for o in odd[:20]: print(" ", o)
