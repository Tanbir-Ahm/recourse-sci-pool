"""Tests for goodlaw/pilot_settings.py (the settings and who decided them), goodlaw/pilot_admin.py (the owner's command-line tools) and the pause switch.
Run: python test_goodlaw_pilot_settings.py
"""
import copy
import io
import json
import os
import tempfile

from goodlaw import bot_core as B
from goodlaw import cardreader as CR
from goodlaw import chat_format as CF
from goodlaw import passage_input as PI
from goodlaw import pilot as P
from goodlaw import pilot_admin as A
from goodlaw import pilot_settings as S
from goodlaw import register as R

FAILURES = []
HERE = os.path.dirname(os.path.abspath(__file__))
REG, CARDS = R.Register.load(), CR.load(os.path.join(HERE, "cards", "currency_cards.json"))


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


def raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc:
        return True
    except BaseException:
        return False
    return False


SETTINGS_DIR = tempfile.mkdtemp()
BASE = json.load(open(S.DEFAULT_PATH, encoding="utf-8"))


def write(d, doc):
    path = os.path.join(d, "settings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f)
    return path


def variant(fn):
    doc = copy.deepcopy(BASE)
    fn(doc["settings"], doc)
    return write(SETTINGS_DIR, doc)


def run(argv):
    buf = io.StringIO()
    code = A.main(argv, out=buf)
    return code, buf.getvalue()


# ---- the settings file --------------------------------------------------------------------------------------------------------------------------------------------------------------
print("the settings")
s = S.load()
q = s["quiet_policy"]
check(q["value"] == "coverage_note" and q["status"] == "decided" and q["decided_on"] == "2026-10-22" and "owner" in q["decided_by"] and "weak evidence" in q["reason"], "the quiet-card choice is recorded as decided, with who, when and why (this check pins the choice: changing it must be deliberate)")
check({n: e["status"] for n, e in s.items()} == {"quiet_policy": "decided", "keep_question_text": "default", "daily_question_cap": "placeholder", "global_daily_cap": "placeholder", "passages_shown": "placeholder", "rules_version": "default"},
      "every other setting says honestly that it is a default or a placeholder, not a decision")
check(s["keep_question_text"]["value"] is False and s["daily_question_cap"]["value"] == 10 and s["global_daily_cap"]["value"] == 100 and s["passages_shown"]["value"] == 3 and s["rules_version"]["value"] == P.RULES_VERSION, "the values are the ones the bot core and the pilot already use")
rep = S.report(s)
check([r[0] for r in rep][:3] == ["daily_question_cap", "global_daily_cap", "passages_shown"] and [r[2] for r in rep][:3] == ["placeholder"] * 3 and rep[-1][0] == "rules_version", "the report puts the placeholders first, then the rest by name")

if True:
    check(raises(S.SettingsError, S.load, variant(lambda s_, doc: doc.update(schema="other"))), "a file with another schema is refused")
    check(raises(S.SettingsError, S.load, variant(lambda s_, doc: s_.update(surprise={"value": 1, "status": "default"}))), "an unknown setting is refused")
    check(raises(S.SettingsError, S.load, variant(lambda s_, doc: s_.pop("passages_shown"))), "a missing setting is refused")
    check(raises(S.SettingsError, S.load, variant(lambda s_, doc: s_["quiet_policy"].update(status="maybe"))), "an unknown status is refused")
    check(raises(S.SettingsError, S.load, variant(lambda s_, doc: s_["daily_question_cap"].update(value=0))) and raises(S.SettingsError, S.load, variant(lambda s_, doc: s_["daily_question_cap"].update(value=True)))
          and raises(S.SettingsError, S.load, variant(lambda s_, doc: s_["keep_question_text"].update(value="no"))), "a value of the wrong kind (zero, a boolean for a number, a word for a yes/no) is refused")
    check(raises(S.SettingsError, S.load, variant(lambda s_, doc: s_["quiet_policy"].pop("decided_by"))) and raises(S.SettingsError, S.load, variant(lambda s_, doc: s_["quiet_policy"].pop("decided_on"))), "a decided setting must say who decided it and when")
    check(raises(S.SettingsError, S.load, variant(lambda s_, doc: s_["quiet_policy"].update(value="loud"))), "the quiet policy must be one the formatter knows")
    opened = S.load(variant(lambda s_, doc: s_["quiet_policy"].update(status="open", value=None)))
    check(opened["quiet_policy"]["status"] == "open" and S.report(opened)[0][0] == "quiet_policy", "an open setting loads, and heads the report")

print("building the bot from the settings")
p = S.new_pilot(settings=s)
core = S.build_core(p, REG, CARDS, lambda q: [], PI.IndexRowIdentity(PI.IndexDocs()), settings=s, today="2026-11-05")
check(core.formatter.quiet_policy == "coverage_note" and core.daily_question_cap == 10 and core.global_daily_cap == 100 and core.shown == 3 and p.keep_question_text is False, "the formatter's quiet policy and the bot's limits come from the settings")
check(raises(S.SettingsError, S.build_core, p, REG, CARDS, lambda q: [], None, settings=S.load(variant(lambda s_, doc: s_["quiet_policy"].update(status="open", value=None)))), "while a setting is open, nothing is built")
p2 = P.Pilot(rules_version="v9")
check(raises(S.SettingsError, S.build_core, p2, REG, CARDS, lambda q: [], None, settings=s) and raises(S.SettingsError, S.build_core, P.Pilot(keep_question_text=True), REG, CARDS, lambda q: [], None, settings=s), "a pilot with other rules or other question-text keeping than the settings is refused")

# ---- the owner's tools ---------------------------------------------------------------------------------------------------------------------------------------------------------------
print("the owner's tools")
with tempfile.TemporaryDirectory() as d:
    store = os.path.join(d, "pilot_store")
    code, text = run(["init", "--store", store])
    check(code == 0 and "0 users" in text and os.path.exists(os.path.join(store, "pilot.json")), "init makes an empty store: nobody is on the list")
    code, text = run(["users", "--store", store])
    check(text.strip() == "nobody is on the list", "and says so")
    code, text = run(["add-user", "--store", store, "--id", "123456", "--label", "Adv. A", "--by", "the owner", "--on", "2026-11-01"])
    check(code == 0 and "added Adv. A (…456)" in text and "123456" not in text, "adding a user shows the label and only the last three characters of the chat id")
    code, text = run(["add-user", "--store", store, "--id", "123456", "--label", "Adv. Z", "--by", "the owner"])
    check(code == 1 and text.startswith("refused:"), "a second user with the same id is refused, with a plain message")
    code, text = run(["users", "--store", store])
    check("Adv. A" in text and "…456" in text and "has not accepted the rules" in text and "123456" not in text, "the list shows labels and state, never the whole id")
    pl = P.Pilot(os.path.join(store, "pilot.json"))
    pl.accept("123456", "2026-11-02")
    q1 = pl.start_question("123456", on="2026-11-03")
    pl.set_shown(q1, [("1111aaaa2222bbbb", 5)])
    pl.mark("123456", q1, "1111aaaa2222bbbb", "misleading")
    code, text = run(["users", "--store", store])
    check("accepted 2026-11-02" in text, "after the user accepts the rules the list says so")
    code, text = run(["summary", "--store", store])
    sm = json.loads(text)
    check(sm["users"] == 1 and sm["marks"] == 1 and sm["by_mark"]["misleading"] == 1 and sm["misleading_to_review"] == [["1111aaaa2222bbbb", 5]], "the summary counts users and marks and lists the misleading passages")
    out = os.path.join(d, "marks.csv")
    code, text = run(["export-marks", "--store", store, "--out", out])
    check(code == 0 and "1 marks written" in text and "Adv. A" in open(out, encoding="utf-8").read() and "123456" not in open(out, encoding="utf-8").read(), "the marks sheet uses labels, not ids")
    code, text = run(["switch", "--store", store, "--id", "123456", "--off", "--by", "the owner"])
    check(code == 0 and "switched off: …456" in text and P.Pilot(os.path.join(store, "pilot.json")).gate("123456")[1] == "switched_off", "switching a user off is recorded and takes effect")
    code, text = run(["switch", "--store", store, "--id", "999", "--on", "--by", "the owner"])
    check(code == 1 and text.startswith("refused:"), "switching someone who is not on the list is refused")
    code, text = run(["settings"])
    check(code == 0 and "quiet_policy = 'coverage_note'   [decided]" in text and "[placeholder]" in text, "the settings command shows each setting and who decided it")

print("where the store may live")
check(raises(SystemExit, A.check_store, os.path.join(A.REPO, "goodlaw")) and raises(SystemExit, A.check_store, os.path.join(A.REPO, "pilot_store_extra")) and raises(SystemExit, A.check_store, A.REPO), "a store inside the repository but not in pilot_store/ is refused")
check(A.check_store(os.path.join(A.REPO, "pilot_store")) == os.path.join(A.REPO, "pilot_store") and A.check_store("/tmp/some_store") == "/tmp/some_store", "pilot_store/ (git-ignored) or a folder outside the repository is allowed")
gi = open(os.path.join(HERE, ".gitignore"), encoding="utf-8").read().split()
check("pilot_store/" in gi, "and pilot_store/ is in .gitignore")

# ---- the pause switch ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("the pause switch")
with tempfile.TemporaryDirectory() as d:
    store = os.path.join(d, "s")
    pl = P.Pilot()
    pl.add_user("111", "Adv. A", "the owner", "2026-11-01")
    pl.accept("111", "2026-11-02")
    docs = PI.IndexDocs()
    core = B.BotCore(pl, CF.Formatter(REG, CARDS, quiet_policy="coverage_note", today="2026-11-05"), lambda q: [], PI.IndexRowIdentity(docs), store_dir=store, today="2026-11-05")
    check(core.handle("111", text="/help")[0].text == B.HELP, "before it is paused the bot answers")
    run(["init", "--store", store])
    code, text = run(["pause", "--store", store])
    check(code == 0 and os.path.exists(os.path.join(store, B.PILOT_STOP)), "pause creates the stop file")
    check(all(core.handle(u, text="hello")[0].text == B.PAUSED for u in ("111", "999")) and core.handle("111", tap="m|q1|1111aaaa2222bbbb|r")[0].text == B.PAUSED, "while it exists the bot answers everyone, even a stranger or a tap, with the pause notice")
    run(["resume", "--store", store])
    check(core.handle("111", text="/help")[0].text == B.HELP and run(["resume", "--store", store])[0] == 0, "resume removes it, and resuming twice is harmless")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
