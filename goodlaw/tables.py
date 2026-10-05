"""The law reporters' case-law tables as evidence in a report.

From about 2017 to 2023 the Supreme Court Reports print, in the headnote of each judgment, a table of the earlier cases the judgment cites and what the court did with
each ("overruled", "relied on", "distinguished" ...), see goodlaw.modern_gold. For a case under review, each such row in a later judgment is a statement by the
reporter's editors about what that judgment did with the case. It is evidence of a different kind from a sentence of the judgment, so it is labelled as the reporter's,
verified word for word against the text, and kept apart from the pattern-rule reading.

Judgments from 2024 on print no such table, so this evidence stops at 2023.
"""
from . import cites as C
from . import modern_gold as G
from .textutil import flatten, quote_in_text

# what a code letter means in plain words, for the report
MEANING = {"O": "overruled", "NF": "disapproved or not followed", "D": "distinguished or held inapplicable", "E": "explained or clarified",
           "RF": "relied on", "F": "followed, approved or affirmed", "R": "referred to"}
ADVERSE_LABEL = {"O": "OVERRULES", "NF": "DISAGREES"}


def rows_for_target(text, body_start, target_cites):
    """[{cite, code_text, code, para, quote, quote_verified}] for each row of the judgment's case-law table whose citation is one the target is known by."""
    out = []
    flat_text = None
    for cite, code_text, para in G.table_rows(text, body_start):
        key = C.norm_cite(G.repair_cite(cite))
        if not key or not any(C.keys_match(key, k) for k in target_cites):
            continue
        letter = G.code_letter(code_text)
        if letter is None:
            continue
        quote = flatten(f"{cite} {code_text} {para}")
        if flat_text is None:
            flat_text = flatten(text)
        out.append({"cite": flatten(cite), "code_text": flatten(code_text).strip(" ."), "code": letter, "para": flatten(para), "quote": quote, "quote_verified": quote in flat_text})
    return out


def evidence(corpus, target, mentions):
    """One entry per (citing judgment, table row) for the target, over the judgments in which the target was found. Each entry carries the judgment's identity and bench
    from the mention that found it. `mentions` are the dicts from goodlaw.mentions.find_mentions."""
    docs = {}
    for m in mentions:
        docs.setdefault(m["doc_key"], m)
    cites = target.all_cites()
    out = []
    if not cites:
        return out
    for key, m in docs.items():
        doc = corpus.get(key, with_text=False)
        if not doc or not doc.get("body_start"):
            continue
        text = corpus.text_of(m["doc_id"])
        for row in rows_for_target(text, doc.get("body_start"), cites):
            row.update(doc_key=key, doc_id=m["doc_id"], title=m["title"], date=m["date"], year=m["year"], bench_size=m["bench_size"], bench_source=m["bench_source"], source=m["source"])
            out.append(row)
    return out
