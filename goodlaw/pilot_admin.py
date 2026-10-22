"""The owner's tools for the pilot, on the command line. Offline; they read and write one private file and nothing else.

    python -m goodlaw.pilot_admin init --store pilot_store
    python -m goodlaw.pilot_admin add-user --store pilot_store --id 123456 --label "Adv. A" --by "the owner"
    python -m goodlaw.pilot_admin users --store pilot_store                          # labels and state; chat ids are shown only as their last three characters
    python -m goodlaw.pilot_admin switch --store pilot_store --id 123456 --off --by "the owner"
    python -m goodlaw.pilot_admin summary --store pilot_store                        # counts of users, questions and marks; the misleading passages to look at
    python -m goodlaw.pilot_admin export-marks --store pilot_store --out marks.csv
    python -m goodlaw.pilot_admin pause --store pilot_store / resume --store pilot_store   # the stop file: while it exists the bot answers everyone with "paused"
    python -m goodlaw.pilot_admin settings                                           # every setting, who decided it, and which are still placeholders

The store holds chat ids and lawyers' marks. It must be outside the repository or in `pilot_store/` (which is git-ignored); any other place inside the repository is refused. Nobody is on the list until
the owner adds them: this file creates no user, and a chat id is only known once a person has written to the bot, which does not exist yet.
"""
import argparse
import json
import os
import sys

from . import bot_core as B
from . import pilot as P
from . import pilot_settings as S

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_store(store):
    path = os.path.abspath(store)
    inside = os.path.commonpath([path, REPO]) == REPO
    if inside and os.path.commonpath([path, os.path.join(REPO, "pilot_store")]) != os.path.join(REPO, "pilot_store"):
        raise SystemExit(f"refused: {store} is inside the repository but not in pilot_store/ (git-ignored). Use a folder outside the repository or pilot_store/.")
    return path


def _pilot(store):
    path = check_store(store)
    return P.Pilot(os.path.join(path, "pilot.json"), keep_question_text=S.load()["keep_question_text"]["value"], rules_version=S.load()["rules_version"]["value"]), path


def _mask(uid):
    return "…" + uid[-3:]


def main(argv=None, out=None):
    out = out or sys.stdout
    ap = argparse.ArgumentParser(prog="python -m goodlaw.pilot_admin")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "add-user", "users", "switch", "summary", "export-marks", "pause", "resume"):
        sp = sub.add_parser(name)
        sp.add_argument("--store", default="pilot_store")
        if name == "add-user":
            sp.add_argument("--id", required=True); sp.add_argument("--label", required=True); sp.add_argument("--by", required=True); sp.add_argument("--on")
        if name == "switch":
            sp.add_argument("--id", required=True); sp.add_argument("--by", required=True)
            g = sp.add_mutually_exclusive_group(required=True)
            g.add_argument("--on", action="store_true"); g.add_argument("--off", action="store_true")
        if name == "export-marks":
            sp.add_argument("--out", required=True)
    sub.add_parser("settings")
    a = ap.parse_args(argv)

    if a.cmd == "settings":
        for n, v, st, note in S.report(S.load()):
            print(f"{n} = {v!r}   [{st}]", file=out)
            if st in ("placeholder", "default", "open"):
                print(f"    {note}", file=out)
        return 0
    pilot, path = _pilot(a.store)
    try:
        if a.cmd == "init":
            os.makedirs(path, exist_ok=True)
            pilot._save()
            print(f"pilot store ready at {a.store}; {len(pilot.users())} users on the list", file=out)
        elif a.cmd == "add-user":
            pilot.add_user(a.id, a.label, a.by, a.on)
            print(f"added {a.label} ({_mask(a.id)}); they must accept the rules before they get an answer", file=out)
        elif a.cmd == "users":
            for uid, u in pilot.users().items():
                state = "off" if not u["active"] else ("accepted " + str(u["accepted_on"]) if u["accepted_version"] == pilot.rules_version else "has not accepted the rules")
                print(f"{u['label']:<20} {_mask(uid):<8} {state:<30} added by {u['added_by']} on {u['added_on']}", file=out)
            if not pilot.users():
                print("nobody is on the list", file=out)
        elif a.cmd == "switch":
            pilot.set_active(a.id, a.on, a.by)
            print(f"{'switched on' if a.on else 'switched off'}: {_mask(a.id)}", file=out)
        elif a.cmd == "summary":
            print(json.dumps(pilot.summary(), indent=1, default=list), file=out)
        elif a.cmd == "export-marks":
            print(f"{pilot.export_marks_csv(a.out)} marks written to {a.out}", file=out)
        elif a.cmd == "pause":
            os.makedirs(path, exist_ok=True)
            open(os.path.join(path, B.PILOT_STOP), "w").close()
            print("paused: the bot answers everyone with a pause notice until you run resume", file=out)
        elif a.cmd == "resume":
            f = os.path.join(path, B.PILOT_STOP)
            if os.path.exists(f):
                os.remove(f)
            print("resumed", file=out)
    except P.PilotError as e:
        print(f"refused: {e}", file=out)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
