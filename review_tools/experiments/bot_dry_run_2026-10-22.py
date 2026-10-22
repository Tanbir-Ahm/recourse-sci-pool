"""A dry run of the pilot bot's core (goodlaw/bot_core.py), written out as a transcript a person can read. Offline: no chat service, no network, no spend, no real search.

    python review_tools/experiments/bot_dry_run_2026-10-22.py --out review_results/2026-10-22_bot_dry_run

What is real: the Overruled Register and the currency cards (the files in this repository), the wording and the rules. What is invented: the users, the judgments' names (written as bucket records the connector reads), the passages, and the
search (a stub that returns four fixed hits). The transcript is for reading, not evidence about the search.
"""
import argparse
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

from goodlaw import bot_core as B  # noqa: E402
from goodlaw import cardreader as CR  # noqa: E402
from goodlaw import chat_format as CF  # noqa: E402
from goodlaw import passage_input as PI  # noqa: E402
from goodlaw import pilot as P  # noqa: E402
from goodlaw import register as R  # noqa: E402
from goodlaw import watchlist as W  # noqa: E402

DAY = "2026-11-05"
HITS = [{"doc": 1000000001, "i": 0, "pn": "14", "page": 9, "section": "reasoning", "h": "1111aaaa2222bbbb", "text": "14. [Invented passage 1: a paragraph of the first judgment, word for word.]"},
        {"doc": 1000000002, "i": 1, "pn": "3", "page": 2, "section": "argument", "h": "3333cccc4444dddd", "text": "3. [Invented passage 2: counsel for the appellant submitted that the order was bad.]"},
        {"doc": 777, "i": 2, "pn": None, "page": 1, "section": "reasoning", "h": "5555eeee6666ffff", "text": "[Invented passage 3: a paragraph from a judgment nobody can name.]"},
        {"doc": 1000000003, "i": 3, "pn": "8", "page": 4, "section": "reasoning", "h": "7777aaaa8888bbbb", "text": "8. [Invented passage 4: a fourth passage, found but not shown.]"}]
DOCS = PI.IndexDocs([
    {"doc": 1000000001, "passages": 5, "src": {"title": "MOHAN LAL versus STATE OF PUNJAB", "date": "24-07-2018", "citation": "(2018) 17 SCC 627", "case_id": "2018 INSC 1", "path": "a"}},
    {"doc": 1000000002, "passages": 5, "src": {"title": "SAMPLE ONE versus STATE", "date": "01-02-2015", "citation": "[2015] 1 S.C.R. 1", "case_id": "2015 INSC 2", "path": "b"}},
    {"doc": 1000000003, "passages": 5, "src": {"title": "SAMPLE TWO versus STATE", "date": "01-02-2016", "citation": "[2016] 1 S.C.R. 1", "case_id": "2016 INSC 3", "path": "c"}},
])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    reg, cards = R.Register.load(), CR.load(os.path.join(ROOT, "cards", "currency_cards.json"))
    fmt = CF.Formatter(reg, cards, quiet_policy="coverage_note", today=DAY)
    pilot = P.Pilot()
    pilot.add_user("900001", "Adv. A", "the owner", DAY)
    work = tempfile.mkdtemp()
    core = B.BotCore(pilot, fmt, lambda q: HITS, PI.IndexRowIdentity(DOCS), store_dir=os.path.join(work, "store"), export_dir=os.path.join(work, "exports"), today=DAY)
    out = ["# A dry run of the pilot bot's core, 2026-10-22", "",
           "Offline: no chat service, no network, no spend. **Real:** the Overruled Register, the currency cards, the rules and the wording. **Invented:** the users, the judgments' names, the passages and the search (a stub that returns four fixed hits). "
           "Read it as a picture of what a lawyer would see, not as evidence about the search. `quiet_policy` is set to `coverage_note` here only for the picture; it is the owner's open decision.", ""]

    def say(who, text=None, tap=None):
        shown = f"tap: {tap}" if tap else text
        out.extend([f"### {who} writes", "", "```", shown, "```", ""])
        replies = core.handle("900001" if who != "A stranger" else "999999", text=text, tap=tap)
        for r in replies:
            out.extend(["**The bot replies:**", "", "```", r.text, "```", ""])
            if r.buttons:
                out.extend(["Buttons: " + " | ".join(b[0] for b in r.buttons), ""])
            if r.attachment:
                out.extend([f"Attachment: `{os.path.basename(r.attachment)}`", ""])
        return replies

    say("A stranger", "What is the rule on bail?")
    say("Adv. A (first message)", "Hello")
    say("Adv. A", "I understand")
    first = say("Adv. A", "Can bail be refused on a conspiracy allegation?")
    say("Adv. A", tap=first[1].buttons[2][2])
    say("Adv. A", "/watch Mohan Lal v State of Punjab (2018) ; (2018) 17 SCC 627")
    say("Adv. A", "/watch Sample One v State (2015)")
    say("Adv. A", "/watchlist")
    ex = say("Adv. A", "/export")
    with open(ex[0].attachment, encoding="utf-8-sig") as fh:
        out.extend(["The exported file (all its columns, one row each):", "", "```"] + [fh.read()] + ["```", ""])

    out.extend(["## A month later: the watchlist check (not part of the bot's core; shown to complete the picture)", ""])
    wl = core._watchlist("900001")
    changed = {"cards": [dict(c) for c in cards["cards"]]}
    changed["cards"].append({"case": {"name": "Sample One v State", "citation_keys": ["scr:2015:1:1"]}, "status": "ADVERSE_SIGNAL", "statute_note": None, "internal_note": "", "review": None,
                             "user_facing_note": "A later five-judge bench of the Supreme Court (2026) appears to overrule or reject this case, in whole or in part, so check it before relying on this case.",
                             "provenance": {"generated": "2026-12-01"}})
    fmt.cards = CR.load(changed)
    res = wl.run("2026-12-02")
    out.extend([f"Run on 2026-12-02: {res['checked']} cases checked, {res['unchanged']} unchanged, {len(res['alerts'])} draft alert(s). A person reads the draft; nothing is sent until someone approves it, and no sender exists.", ""])
    for al in res["alerts"]:
        out.extend([f"**Draft alert ({al['kind']}, status: {al['status']}):**", "", "```", al["text"], "```", ""])
    out.extend(["## What the owner sees", "", "```"])
    s = pilot.summary()
    out.extend([f"users: {s['users']}, accepted the rules: {s['accepted_rules']}, questions: {s['questions']}, marks: {s['marks']}", f"by mark: {s['by_mark']}", f"misleading passages to review: {s['misleading_to_review']}", "```", ""])
    with open(os.path.join(a.out, "TRANSCRIPT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("wrote", os.path.join(a.out, "TRANSCRIPT.md"), len(out), "lines")


if __name__ == "__main__":
    main()
