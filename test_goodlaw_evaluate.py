"""Tests for goodlaw/evaluate.py: the agreement tables against the reporter's citator codes. Run: python test_goodlaw_evaluate.py"""
from goodlaw import evaluate as E

FAILURES = []


def check(condition, description):
    print(f"[{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        FAILURES.append(description)


# (target, citing, code, cite, label read, cue, sentence)
R = [
    ("c2", "c9", "O", "1980 SC 1", "OVERRULES", "overruled", "s"),
    ("c2", "c8", "O", "1980 SC 2", "DISAGREES", "differ", "s"),
    ("c2", "c7", "O", "1980 SC 3", "NEUTRAL", None, "s"),
    ("c2", "c6", "HO", "1980 SC 4", None, None, None),
    ("c4", "c5", "NF", "1980 SC 5", "DISAGREES", "not followed", "s"),
    ("c4", "c4", "F", "1980 SC 6", "FOLLOWS", "followed", "s"),
    ("c4", "c3", "RF", "1980 SC 7", "NEUTRAL", None, "s"),
    ("c4", "c2", "RF", "1980 SC 8", "OVERRULES", "overruled", "s"),
    ("c6", "c1", "D", "1980 SC 9", "DISTINGUISHES", "distinguished", "s"),
    ("c6", "c3", "D", "1980 SC 10", None, None, None),
    ("c6", "c5", "R", "1980 SC 11", "NEUTRAL", None, "s"),
]
s = E.summarise(R)
check(s["adverse"] == {"pairs": 5, "mention_found": 4, "read_as_any_adverse": 3, "overruled_pairs": 4, "read_as_overrules": 1}, "adverse codes: 5 pairs, mention found in 4, read as adverse in 3, overruled-code pairs 4 of which 1 read as overrules")
check(s["others"]["pairs"] == 6 and s["others"]["mention_found"] == 5 and s["others"]["read_as_adverse"] == 1 and s["others"]["read_as_overrules"] == 1, "other codes: 6 pairs, 5 with a mention, 1 read as adverse (a possible false alarm)")
check(s["positive"] == {"pairs": 3, "read_as_follows_or_not_overruled": 1, "read_as_adverse": 1}, "positive codes F and RF: 3 pairs, 1 read as following, 1 as adverse")
check(s["distinguished"] == {"pairs": 2, "read_as_distinguishes": 1}, "code D: 2 pairs, 1 read as distinguishes")
check(s["by_code"]["O"] == {"OVERRULES": 1, "DISAGREES": 1, "NEUTRAL": 1}, "the confusion table is kept per code")

# rows from the real runner carry (eligible, hedged, binding, speaker): a counsel-only reading is not a usable reading, and hedged or weak ones are 'possible'
R2 = [
    ("c2", "c9", "O", "x", "OVERRULES", "overruled", "s", True, False, "strong", "court"),
    ("c2", "c8", "O", "x", "OVERRULES", "overruled", "s", True, True, "strong", "court"),
    ("c2", "c7", "O", "x", "OVERRULES", "overruled", "s", False, False, "strong", "counsel"),
    ("c4", "c5", "R", "x", "DISAGREES", "not followed", "s", True, False, "weak", "court"),
    ("c4", "c6", "R", "x", "DISAGREES", "not followed", "s", True, False, "strong", "court"),
    ("c4", "c7", "F", "x", "FOLLOWS", "followed", "s", True, False, "strong", "court"),
]
s2 = E.summarise(R2)
check(s2["adverse"]["read_as_any_adverse"] == 2 and s2["adverse"]["mention_found"] == 3, "a reading only in counsel's voice is a found mention but not an adverse reading")
check(s2["tiers"] == {"adverse_codes": {"clean": 1, "possible": 1}, "other_codes": {"possible": 1, "clean": 1}}, "adverse readings split into clean and possible (hedged or weak)")
check(s2["by_code"]["O"] == {"OVERRULES": 2, "NO_COURT_VOICE": 1}, "the confusion table shows the counsel-only reading apart")

pairs = [("c2", "c9", "O", "x"), ("c3", "c9", "F", "x"), ("c4", "c9", "R", "x"), ("c5", "c9", "D", "x")]
dev, held = E.split(pairs)
check([p[0] for p in dev] == ["c2", "c4"] and [p[0] for p in held] == ["c3", "c5"], "even target ids are the development half, odd ids the held-out half")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED")
    for f in FAILURES:
        print(" -", f)
    raise SystemExit(1)
print("ALL PASSED")
