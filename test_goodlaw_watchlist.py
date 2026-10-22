"""Tests for goodlaw/watchlist.py: saved cases, the re-check against the register and the cards, and draft alerts that a person approves.
Run: python test_goodlaw_watchlist.py

Part 1 uses a small register and cards written here and swaps them between runs to make each kind of change happen. Part 2 saves the 76 real cases and changes the real data in memory.
"""
import copy
import json
import os
import tempfile

from goodlaw import cardreader as CR
from goodlaw import chat_format as CF
from goodlaw import register as R
from goodlaw import watchlist as W

FAILURES = []
HERE = os.path.dirname(os.path.abspath(__file__))
ADV = "A later five-judge bench of the Supreme Court (2020) appears to overrule or reject this case, in whole or in part, so check it before relying on this case."
CAU = "Later judgments doubt or limit this case, so check them before relying on it."


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


def row(rid, a, ayear, b, byear, trust="candidate", treatment="overruled", cites=()):
    return {"id": rid, "source": "t", "trust": trust,
            "overruled": {"name": a, "alt_names": [], "court": "SC", "cites": list(cites), "keys": R.key_set(" : ".join(cites)), "year": ayear, "years": [ayear]},
            "overruling": {"name": b, "court": "SC", "cites": [], "keys": [], "year": byear, "date": None, "bench": None},
            "treatment": treatment, "scope": None, "court_words": None, "same_parties": False, "flags": [], "evidence": {"basis": "B"}, "verification": None, "history": []}


def card(name, status, note=None, generated="2026-10-06", review=None):
    return {"case": {"name": name, "citation_keys": []}, "status": status, "user_facing_note": note, "statute_note": None, "internal_note": "", "review": review, "provenance": {"generated": generated}}


def register(rows):
    return R.Register(rows, {"built_on": "2026-10-07"})


def cards(*cs):
    return CR.load({"cards": list(cs)})


FMT = CF.Formatter(register([]), cards(), quiet_policy="coverage_note", today="2026-10-22")


def fresh(reg_rows=(), card_list=()):
    FMT.register, FMT.cards = register(list(reg_rows)), cards(*card_list)
    return W.Watchlist(FMT, owner="a test chamber")


def kinds(res):
    return [a["kind"] for a in res["alerts"]]


# ---- keys ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("keys")
check(W.watch_key("X v Y", 2018, "(2018) 17 SCC 627") == "scc:2018:17:627", "a case with a reported citation is keyed by it")
check(W.watch_key("Mohan Lal v. State of Punjab", 2018) == W.watch_key("MOHAN LAL VERSUS STATE OF PUNJAB", 2018) == "name:mohanlalvstateofpunjab:2018", "otherwise by its squashed name and year, whatever the spelling of 'v'")
check(W.watch_key("A v B", 2018) != W.watch_key("A v B", 2019), "the year is part of the key")

# ---- saving and the baseline ------------------------------------------------------------------------------------------------------------------------------------------------
print("saving a case")
wl = fresh(card_list=[card("Alpha v Beta", "ADVERSE_SIGNAL", ADV)])
key, cur = wl.add("Alpha v Beta", 2018)
check(cur.lines[0].rule == 3 and wl.pending() == [], "saving a flagged case shows its warning now, and creates no alert: that is the baseline")
check(wl.add("Alpha v Beta", 2018)[0] == key and len(wl.cases()) == 1, "saving it twice keeps one entry")
check(raises(W.WatchlistError, wl.add, "  "), "a case needs a name")
r = wl.run()
check(r["checked"] == 1 and r["unchanged"] == 1 and r["alerts"] == [] and r["baselined"] == 0, "a run with nothing new finds nothing and says so")
r = wl.run()
check(r["alerts"] == [], "and the second run is the same")

# ---- each kind of change -------------------------------------------------------------------------------------------------------------------------------------------------------
print("a new warning")
wl = fresh(card_list=[card("Alpha v Beta", "NO_ADVERSE_FOUND")])
wl.add("Alpha v Beta", 2018)
FMT.cards = cards(card("Alpha v Beta", "ADVERSE_SIGNAL", ADV, generated="2026-11-05"))
r = wl.run("2026-11-06")
a = r["alerts"][0]
check(kinds(r) == [W.NEW_WARNING] and a["status"] == "draft", "a quiet case that gains a checker flag gives one draft NEW_WARNING")
check(a["text"].startswith("WATCHLIST ALERT: New warning on a case you saved") and "REPORTED ADVERSE" in a["text"] and ADV in a["text"] and "As of 5 Nov 2026." in a["text"] and a["text"].endswith(W.FOOTER), "the draft names the case, shows the card's own warning with its date, and ends with the footer")
check(not CF.wording_violations(a["text"]), "and makes no claim that the case is good law")
check([x["id"] for x in wl.pending()] == [a["id"]] and wl.outbox() == [], "it waits as a draft; nothing is in the outbox")
check(wl.run("2026-11-06")["alerts"] == [] and len(wl.state["alerts"]) == 1, "running again does not draft it again")

print("a caution that becomes adverse, a warning that a person confirms")
wl = fresh(card_list=[card("Gamma v Delta", "QUESTIONED", CAU)])
wl.add("Gamma v Delta", 2016)
FMT.cards = cards(card("Gamma v Delta", "ADVERSE_SIGNAL", ADV))
r = wl.run("2026-11-06")
check(kinds(r) == [W.WARNING_CHANGED] and "This replaces an earlier warning" in r["alerts"][0]["text"] and CAU in r["alerts"][0]["text"], "a caution that becomes adverse is WARNING_CHANGED, and the earlier warning is shown")
wl = fresh(card_list=[card("Alpha v Beta", "ADVERSE_SIGNAL", ADV)])
wl.add("Alpha v Beta", 2018)
FMT.cards = cards(card("Alpha v Beta", "ADVERSE_SIGNAL", ADV, review={"current": True, "verdict": "CONFIRMED_ADVERSE", "reviewer": "Mr. Advocate", "date": "2026-11-01"}))
r = wl.run("2026-11-06")
check(kinds(r) == [W.WARNING_CONFIRMED] and "confirmed by our reviewer" in r["alerts"][0]["text"], "a checker flag that a person confirms is WARNING_CONFIRMED")
wl = fresh(reg_rows=[row("C1", "Mohan Lal v. State of Punjab", 2018, "Mukesh Singh v. State", 2020)])
wl.add("Mohan Lal v State of Punjab", 2018)
FMT.register = register([row("C1", "Mohan Lal v. State of Punjab", 2018, "Mukesh Singh v. State", 2020, trust="reviewer_confirmed")])
r = wl.run("2026-11-06")
check(kinds(r) == [W.WARNING_CONFIRMED] and "ON THE OVERRULED REGISTER" in r["alerts"][0]["text"], "a candidate register row that a person confirms is WARNING_CONFIRMED, now in firm wording")
wl = fresh()
wl.add("Mohan Lal v State of Punjab", 2018)
FMT.register = register([row("C1", "Mohan Lal v. State of Punjab", 2018, "Mukesh Singh v. State", 2020)])
check(kinds(wl.run("2026-11-06")) == [W.NEW_WARNING] and "not yet confirmed by our reviewer" in wl.pending()[0]["text"], "a case newly found on the register as a candidate is a NEW_WARNING, still hedged")

print("a warning that goes away is a correction, not an all-clear")
wl = fresh(card_list=[card("Alpha v Beta", "ADVERSE_SIGNAL", ADV)])
wl.add("Alpha v Beta", 2018)
FMT.cards = cards(card("Alpha v Beta", "ADVERSE_SIGNAL", ADV, review={"current": True, "verdict": "FALSE_ALARM", "reviewer": "Mr. Advocate", "date": "2026-11-01"}))
r = wl.run("2026-11-06")
t = r["alerts"][0]["text"]
check(kinds(r) == [W.WARNING_WITHDRAWN] and "We previously warned" in t and ADV in t and "a correction, not an all-clear" in t, "a flag a person cleared is a WARNING_WITHDRAWN that shows what we had said and calls itself a correction")
check("says nothing about whether the case is still reliable" in t and not CF.wording_violations(t) and "no warning found" not in t.lower(), "it does not say the case is fine")
wl2 = fresh(reg_rows=[row("C1", "Mohan Lal v. State of Punjab", 2018, "Mukesh Singh v. State", 2020)])
wl2.add("Mohan Lal v State of Punjab", 2018)
FMT.register = register([])
check(kinds(wl2.run("2026-11-06")) == [W.WARNING_WITHDRAWN], "a register row that is taken away is withdrawn the same way")

print("what is not news")
for before, after, why in ((card("Q v C", "NO_ADVERSE_FOUND"), None, "a quiet case that loses its card"), (None, card("Q v C", "NO_ADVERSE_FOUND"), "a case that gains a quiet card"),
                           (card("Q v C", "INSUFFICIENT"), card("Q v C", "NO_ADVERSE_FOUND"), "too few citing judgments becoming enough, with nothing found")):
    wl = fresh(card_list=[before] if before else [])
    wl.add("Q v C", 2015)
    FMT.cards = cards(after) if after else cards()
    check(wl.run("2026-11-06")["alerts"] == [], f"{why}: no alert, because silence is not news")
wl = fresh(card_list=[card("Alpha v Beta", "ADVERSE_SIGNAL", ADV, generated="2026-10-06")])
wl.add("Alpha v Beta", 2018)
FMT.cards = cards(card("Alpha v Beta", "ADVERSE_SIGNAL", ADV, generated="2026-12-20"))
r = wl.run("2026-12-21")
check(r["alerts"] == [] and r["unchanged"] == 1, "a rebuilt card with the same warning is not a change (a new date alone)")
FMT.cards = cards(card("Alpha v Beta", "ADVERSE_SIGNAL", ADV, generated="2026-01-01"))
r = wl.run("2026-12-21")
check(r["alerts"] == [] and r["cards_older_than_limit"] == 1, "an old card does not alert, but the run says how many cards are older than the limit")

print("an alert is made once, but a new change is a new alert")
wl = fresh(card_list=[card("Alpha v Beta", "NO_ADVERSE_FOUND")])
wl.add("Alpha v Beta", 2018)
FMT.cards = cards(card("Alpha v Beta", "ADVERSE_SIGNAL", ADV))
a1 = wl.run("2026-11-06")["alerts"][0]
FMT.cards = cards(card("Alpha v Beta", "ADVERSE_SIGNAL", ADV, review={"current": True, "verdict": "FALSE_ALARM", "reviewer": "x", "date": "2026-11-20"}))
a2 = wl.run("2026-11-21")["alerts"][0]
FMT.cards = cards(card("Alpha v Beta", "ADVERSE_SIGNAL", ADV))
a3 = wl.run("2026-12-05")["alerts"][0]
check(len({a1["id"], a2["id"], a3["id"]}) == 3 and [a["kind"] for a in wl.state["alerts"]] == [W.NEW_WARNING, W.WARNING_WITHDRAWN, W.NEW_WARNING], "a warning, its withdrawal and its return are three separate alerts")

# ---- a person decides ---------------------------------------------------------------------------------------------------------------------------------------------------------
print("approval")
aid = a1["id"]
check(raises(W.WatchlistError, wl.approve, aid, "  ") and raises(W.WatchlistError, wl.approve, "nope", "Mr. Advocate"), "approving needs a reviewer's name and a real alert")
check(raises(W.WatchlistError, wl.mark_sent, aid), "a draft cannot be marked sent")
x = wl.approve(aid, "Mr. Advocate", "2026-11-07")
check(x["status"] == "approved" and x["reviewer"] == "Mr. Advocate" and x["decided_on"] == "2026-11-07" and aid in [a["id"] for a in wl.outbox()] and aid not in [a["id"] for a in wl.pending()], "approval records who and when and moves it to the outbox")
check(raises(W.WatchlistError, wl.approve, aid, "Mr. Advocate") and raises(W.WatchlistError, wl.reject, aid, "Mr. Advocate"), "an approved alert cannot be approved or rejected again")
check(wl.mark_sent(aid, "2026-11-08")["status"] == "sent" and wl.outbox() == [], "an approved alert can be marked sent, and then leaves the outbox")
y = wl.reject(a2["id"], "Mr. Advocate", "not needed: the lawyer never saw the first warning", "2026-11-22")
check(y["status"] == "rejected" and y["note"].startswith("not needed"), "a draft can be rejected, with a note")
check(raises(W.WatchlistError, wl.reject, a3["id"], ""), "rejecting needs a name too")

# ---- the file -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
print("the file")
with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "store", "a.json")
    FMT.register, FMT.cards = register([]), cards(card("Alpha v Beta", "NO_ADVERSE_FOUND"))
    w = W.Watchlist(FMT, path=path, owner="a test chamber")
    w.add("Alpha v Beta", 2018)
    FMT.cards = cards(card("Alpha v Beta", "ADVERSE_SIGNAL", ADV))
    al = w.run("2026-11-06")["alerts"][0]
    w.approve(al["id"], "Mr. Advocate", "2026-11-07")
    w2 = W.Watchlist(FMT, path=path)
    check(w2.state["owner"] == "a test chamber" and list(w2.cases()) == list(w.cases()) and w2.outbox()[0]["id"] == al["id"], "a new object reads the same cases, owner and alerts from the file")
    check(w2.run("2026-11-06")["alerts"] == [] and sorted(os.listdir(os.path.dirname(path))) == ["a.json"], "it carries on without repeating itself, and leaves no stray files")
    w2.remove(next(iter(w2.cases())))
    check(w2.cases() == {} and raises(W.WatchlistError, w2.remove, "nope"), "a case can be removed from the list")

# ---- the real register and cards ------------------------------------------------------------------------------------------------------------------------------------------------
print("the real register and cards")
REAL_REG = R.Register.load()
cfile = json.load(open(os.path.join(HERE, "cards", "currency_cards.json"), encoding="utf-8"))
REAL = CF.Formatter(REAL_REG, CR.load(cfile), quiet_policy="coverage_note", today="2026-10-22")
wl = W.Watchlist(REAL, owner="all 76 library cases")
for c in cfile["cards"]:
    wl.add(c["case"]["name"], c["case"].get("year"), c["case"].get("citation"))
check(len(wl.cases()) >= 70, f"the library's cases can all be saved ({len(wl.cases())} distinct keys from 76 cards)")
r = wl.run("2026-10-22")
check(r["alerts"] == [] and r["checked"] == len(wl.cases()), "run again on the same data: no alert")
quiet = next(c for c in cfile["cards"] if c["status"] == "NO_ADVERSE_FOUND")
changed = copy.deepcopy(cfile)
for c in changed["cards"]:
    if c["case"]["name"] == quiet["case"]["name"]:
        c["status"], c["user_facing_note"] = "ADVERSE_SIGNAL", ADV
REAL.cards = CR.load(changed)
r = wl.run("2026-11-06")
check(kinds(r) == [W.NEW_WARNING] and quiet["case"]["name"] in r["alerts"][0]["text"], "one quiet card turned into a flag in memory: exactly one NEW_WARNING, naming that case")
rows = copy.deepcopy(REAL_REG.rows)
for x in rows:
    if x["id"] in {i for i in (r2["row"]["id"] for r2 in REAL_REG.lookup_case("Mohan Lal v State of Punjab", 2018, "(2018) 17 SCC 627"))}:
        x["trust"] = "reviewer_confirmed"
REAL.register = R.Register(rows, REAL_REG.meta)
r = wl.run("2026-11-07")
check(kinds(r) == [W.WARNING_CONFIRMED] and "Mohan Lal" in r["alerts"][0]["label"], "Mohan Lal's candidate register row confirmed in memory: exactly one WARNING_CONFIRMED, and no other case moves")
check(all(not CF.wording_violations(a["text"]) and a["text"].endswith(W.FOOTER) for a in wl.state["alerts"]), "every draft passes the wording guard and ends with the footer")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
