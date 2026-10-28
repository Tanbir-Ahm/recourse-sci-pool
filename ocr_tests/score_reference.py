"""Score English drafts against an official English text of the same document (a true reference).

  python score_reference.py --reference official.txt --draft view1=draft1.txt --draft view2=draft2.txt [--start "After reading"] [--json scores.json]
  python score_reference.py --selftest

For every draft it reports, in plain numbers:
  closeness      for each sentence of the official text, how close the nearest sentence of the draft is (0 to 1, word by word); the mean, and how many
                 official sentences have no close match (under 0.6). A back-translation will not match word for word, so this shows which sentences to
                 read, not what is wrong: a person judges the meaning.
  numbers        numbers and section references in the draft that the official text does not have, and the other way round.
  references     clause, rule, article, section and order numbers, including one-digit ones ("clause 2" against "clause 3"), counted in both texts.
  names          capitalised names and titles one text has and the other lacks.
A draft's numbers or names that differ from the official text are the first things to look at, but they may be faithful to a source that is itself wrong
(an Assamese page that prints Section 422 where the official English says 433): check the source page before blaming the reader.
Inputs are case data: keep them and the output outside the repository. The selftest uses invented text.
"""
import argparse, difflib, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checker

_WORDS = lambda s: re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()


def numbers(text):
    return sorted({re.sub(r"[.,]$", "", n) for n in re.findall(r"\b\d[\d,./]*(?:[A-Z](?![A-Za-z]))?", text) if len(re.sub(r"\D", "", n)) >= 2})


_REFKIND = {"cl": "clause", "cls": "clause", "clauses": "clause", "r": "rule", "rules": "rule", "art": "article", "articles": "article",
            "s": "section", "sections": "section", "o": "order", "ss": "section"}


def legal_references(text):
    """Counts of 'clause 2', 'rule 9', 'article 182', 'section 36', 'order IX' ... including ONE-digit ones, which `numbers` ignores."""
    from collections import Counter
    c = Counter()
    for m in re.finditer(r"\b(clauses?|cls?|rules?|r|articles?|art|sections?|ss?|order|o)\.?\s*(IX|II|[0-9]+)\b", text, re.I):
        k = m.group(1).lower()
        c[(_REFKIND.get(k, k), m.group(2).upper())] += 1
    return c


def closeness(ref_sentences, draft_sentences):
    out = []
    for s in ref_sentences:
        a = _WORDS(s)
        out.append(max((difflib.SequenceMatcher(None, a, _WORDS(d)).ratio() for d in draft_sentences), default=0.0))
    return out


def score(reference, drafts, start=None):
    """reference: the official text. drafts: {name: text}. start: text before the first occurrence of this phrase is ignored in every text."""
    def cut(t):
        t = re.sub(r"\s+", " ", t)
        i = t.find(start) if start else -1
        return t[i:] if i >= 0 else t
    ref = cut(reference); rs = checker.english_sentences("TRANSLATION\n" + ref)
    out = {"reference_sentences": len(rs), "drafts": {}}
    for name, text in drafts.items():
        d = cut(text); ds = checker.english_sentences("TRANSLATION\n" + d)
        c = closeness(rs, ds)
        nr, nd = set(numbers(ref)), set(numbers(d))
        rr, rd = legal_references(ref), legal_references(d)
        names = [t for t in checker.english_term_differences("TRANSLATION\n" + ref, "TRANSLATION\n" + d) if t["kind"] == "name"]
        out["drafts"][name] = {"mean_closeness": round(sum(c) / len(c), 3) if c else 0.0, "sentences_under_0.6": sum(x < 0.6 for x in c),
                               "closeness_per_sentence": [round(x, 2) for x in c],
                               "numbers_not_in_reference": sorted(nd - nr), "numbers_missing_from_draft": sorted(nr - nd),
                               "references_missing_from_draft": sorted("%s %s x%d" % (k[0], k[1], v) for k, v in (rr - rd).items()),
                               "references_not_in_reference": sorted("%s %s x%d" % (k[0], k[1], v) for k, v in (rd - rr).items()),
                               "names_only_in_reference": names[0]["only_in_view_1"] if names else [], "names_only_in_draft": names[0]["only_in_view_2"] if names else []}
    if len(drafts) > 1:
        per = [out["drafts"][n]["closeness_per_sentence"] for n in drafts]
        out["mean_if_the_closer_draft_is_taken_per_sentence"] = round(sum(max(x) for x in zip(*per)) / len(rs), 3) if rs else 0.0
    return out


def selftest():
    ref = "Header line. Section 432 applies to the appropriate Government. The fee is Rs. 500 (five hundred). It was held in Mura Ram vs. Union of India [1981 (1) SCC 106] that it is valid."
    good = ref
    bad = "Header line. Section 422 applies to the appropriate Government. The fee is Rs. 500 (five hundred). It was held in Maru Ram vs. Union Government of India [1981 (1) SCC 106] that it is valid."
    r = score(ref, {"good": good, "bad": bad})
    g, b = r["drafts"]["good"], r["drafts"]["bad"]
    assert g["mean_closeness"] == 1.0 and not g["numbers_not_in_reference"] and not g["numbers_missing_from_draft"], g
    assert b["mean_closeness"] < 1.0 and "422" in b["numbers_not_in_reference"] and "432" in b["numbers_missing_from_draft"], b
    assert any("union government of india" in n for n in b["names_only_in_draft"]), b
    assert r["mean_if_the_closer_draft_is_taken_per_sentence"] == 1.0
    one = score("The case falls under clause 2 of Article 182.", {"d": "The case falls under clause 3 of Article 182."})["drafts"]["d"]
    assert "clause 2 x1" in one["references_missing_from_draft"] and "clause 3 x1" in one["references_not_in_reference"], one
    assert score("Intro. Alpha beta gamma delta.", {"d": "Other intro. Alpha beta gamma delta."}, start="Alpha")["drafts"]["d"]["mean_closeness"] == 1.0
    print("selftest OK (invented text only)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Score English drafts against an official English text.")
    ap.add_argument("--reference"); ap.add_argument("--draft", action="append", default=[], help="name=file, repeatable")
    ap.add_argument("--start", help="ignore everything before the first occurrence of this phrase in every text"); ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.reference and a.draft:
        res = score(open(a.reference, encoding="utf8").read(), {d.split("=", 1)[0]: open(d.split("=", 1)[1], encoding="utf8").read() for d in a.draft}, a.start)
        if a.json:
            json.dump(res, open(a.json, "w", encoding="utf8"), ensure_ascii=False, indent=1)
        for n, d in res["drafts"].items():
            print("%-10s mean closeness %.3f | official sentences with no close match: %d of %d | numbers not in the reference: %s | numbers missing: %s | references missing: %s | references not in the reference: %s"
                  % (n, d["mean_closeness"], d["sentences_under_0.6"], res["reference_sentences"], d["numbers_not_in_reference"], d["numbers_missing_from_draft"],
                     d["references_missing_from_draft"], d["references_not_in_reference"]))
    else:
        sys.exit(__doc__)
