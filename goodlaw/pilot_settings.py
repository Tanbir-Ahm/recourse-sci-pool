"""The pilot's settings, each with who decided it, and the one place that builds the bot core from them.

    s = load()                                       # goodlaw/data/pilot_settings.json
    core = build_core(pilot, register, cards, search_fn, identity, settings=s, store_dir="pilot_store", export_dir="pilot_store/exports")

`load` refuses a file with an unknown setting, a value of the wrong kind, an unknown status, or a decided setting that does not say who decided it and when. `build_core` refuses to build while any
setting is 'open'. The formatter itself still has no default for `quiet_policy`; this file is where the owner's choice is written down and can be read in git. Offline; nothing is sent.
"""
import json
import os

from . import bot_core as B
from . import chat_format as CF
from . import pilot as P

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "pilot_settings.json")
SCHEMA = "goodlaw-pilot-settings-1"
STATUSES = ("decided", "default", "placeholder", "open")
KINDS = {"quiet_policy": str, "keep_question_text": bool, "daily_question_cap": int, "global_daily_cap": int, "passages_shown": int, "rules_version": str}


class SettingsError(Exception):
    pass


def load(path=None):
    """{name: {value, status, ...}} from the settings file, checked."""
    with open(path or DEFAULT_PATH, encoding="utf-8") as f:
        d = json.load(f)
    if d.get("schema") != SCHEMA:
        raise SettingsError(f"unexpected settings schema {d.get('schema')!r}")
    s = d["settings"]
    for name in s:
        if name not in KINDS:
            raise SettingsError(f"unknown setting {name!r}")
    for name, kind in KINDS.items():
        if name not in s:
            raise SettingsError(f"missing setting {name!r}")
        e = s[name]
        if e.get("status") not in STATUSES:
            raise SettingsError(f"{name}: unknown status {e.get('status')!r}")
        if e["status"] != "open":
            v = e.get("value")
            if isinstance(v, bool) != (kind is bool) or not isinstance(v, kind) or (kind is int and v < 1):
                raise SettingsError(f"{name}: the value {v!r} is not a {'positive whole number' if kind is int else kind.__name__}")
        if e["status"] == "decided" and not (e.get("decided_by") and e.get("decided_on")):
            raise SettingsError(f"{name}: a decided setting must say who decided it and when")
    if s["quiet_policy"]["status"] != "open" and s["quiet_policy"]["value"] not in CF.QUIET_POLICIES:
        raise SettingsError(f"quiet_policy must be one of {CF.QUIET_POLICIES}")
    return s


def report(settings):
    """[(name, value, status, note)] for a person to read, open settings first."""
    rows = [(n, e.get("value"), e["status"], e.get("note") or e.get("reason") or "") for n, e in settings.items()]
    return sorted(rows, key=lambda r: (r[2] != "open", r[2] != "placeholder", r[0]))


def build_core(pilot, register, cards, search_fn, identity, settings=None, store_dir=None, export_dir=None, today=None):
    """A BotCore whose formatter and limits come from the settings. Refuses while any setting is open or the pilot's rules version differs from the settings'."""
    s = settings if settings is not None else load()
    opened = [n for n, e in s.items() if e["status"] == "open"]
    if opened:
        raise SettingsError(f"these settings are still open: {', '.join(sorted(opened))}")
    if pilot.rules_version != s["rules_version"]["value"]:
        raise SettingsError(f"the pilot's rules version {pilot.rules_version!r} is not the settings' {s['rules_version']['value']!r}")
    if pilot.keep_question_text != s["keep_question_text"]["value"]:
        raise SettingsError("the pilot's keep_question_text differs from the settings'")
    fmt = CF.Formatter(register, cards, quiet_policy=s["quiet_policy"]["value"], today=today)
    return B.BotCore(pilot, fmt, search_fn, identity, store_dir=store_dir, export_dir=export_dir, daily_question_cap=s["daily_question_cap"]["value"],
                     global_daily_cap=s["global_daily_cap"]["value"], shown=s["passages_shown"]["value"], today=today)


def new_pilot(path=None, settings=None):
    """A Pilot configured from the settings."""
    s = settings if settings is not None else load()
    return P.Pilot(path, keep_question_text=s["keep_question_text"]["value"], rules_version=s["rules_version"]["value"])
