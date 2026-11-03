"""
End-to-end miss measurement: which sections actually REACH THE ANSWER MODEL for each question.

It runs Recourse's real chat_assistant._answer_question_core (scope check, curated overrides, explicit-section lookup, offence keywords, Act Directory + Act shelf, library search with the
caps and thresholds, the follow-up carry) with the MODEL STUBBED OUT: the scope check answers 'in_scope', and the two functions that would call the answer model just hand back the list of
material they were given. So what is recorded is exactly the material the prompt would carry. Retrieval (Voyage embeddings) is real; the answer model, the Act Directory's Haiku pass (ACT_DETECT=ai)
and the wider search are NOT run (no Anthropic key in the sandbox; SCI_SEARCH_MODE unset).

Usage (cwd MUST be the Recourse checkout; the retrieval reads its data relative to it):
    cd /home/user/recourse && python3 <this file> <config> <questions module name> [outfile]
configs:  lib      ACT_SHELF off                        (the library alone, as production ran before the shelf)
          shelf    ACT_SHELF=on ACT_DETECT=wide         (today's staging minus the Haiku pass)
          shelfc   shelf + EVIDENCE_COMPANIONS=on
          shelfw   shelf + STATUTE_WIDEN=on
          fixes    every fix of 2026-11-03 on (STATUTE_WIDEN, STATUTE_ALIASES, the evidence word pass of ACT_DETECT=wide)
"""
import os, sys, json, importlib, hashlib

CONFIGS = {
    "lib": {"ACT_SHELF": "off"},
    "shelf": {"ACT_SHELF": "on", "ACT_DETECT": "wide"},
    "shelfc": {"ACT_SHELF": "on", "ACT_DETECT": "wide", "EVIDENCE_COMPANIONS": "on"},
    "shelfw": {"ACT_SHELF": "on", "ACT_DETECT": "wide", "STATUTE_WIDEN": "on"},
    "fixes": {"ACT_SHELF": "on", "ACT_DETECT": "wide", "STATUTE_WIDEN": "on", "STATUTE_ALIASES": "on"},
}


def main():
    cfg, qmod = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else None
    here = os.path.dirname(os.path.abspath(__file__))
    for k in ("ACT_SHELF", "ACT_DETECT", "EVIDENCE_COMPANIONS", "RELEVANCE_GATE", "SCI_SEARCH_MODE", "CHAT_MODE", "SECTION_XREF", "ANCHORS", "LANDMARKS", "STATUTE_WIDEN", "STATUTE_ALIASES", "EVIDENCE_DETECT"):
        os.environ.pop(k, None)
    os.environ.update(CONFIGS[cfg])
    sys.path.insert(0, "/home/user/recourse")
    sys.path.insert(0, here)
    sys.path.insert(0, os.path.join(here, "..", "2026-11-03_relevance_neighbours"))
    sys.path.insert(0, os.path.join(here, "..", "2026-10-31_relevance_gate"))
    import chat_assistant as CA
    qs = importlib.import_module(qmod).POS

    CA.classify_scope = lambda q: ("in_scope", "stub", None)
    CA._fetch_pilot_related_judgments = lambda *a, **k: []
    CA.generate_grounded_response = lambda *a, **k: ""
    CA._answer_from_wider_search_only = lambda *a, **k: None
    CA._answer_single_match = lambda question, matches: {"state": "single_match", "matches": matches}
    try:
        CA._progress = lambda *a, **k: None
    except Exception:
        pass

    rows = []
    for item in qs:
        q, exp = item[0], item[1]
        kind = item[2] if len(item) > 2 else ""
        try:
            r = CA._answer_question_core(q)
        except Exception as exc:  # noqa: BLE001
            rows.append({"q": q, "kind": kind, "exp": {k: sorted(v) for k, v in exp.items()}, "error": repr(exc)[:200], "got": []})
            continue
        got = []
        for m in (r.get("matches") or []):
            if not isinstance(m, dict):
                continue
            got.append({"type": m.get("type"), "act": (m.get("act") or ""), "sec": str(m.get("section_number") or ""), "case": m.get("case_name"),
                        "retrieval": m.get("retrieval"), "source": m.get("source"), "score": m.get("score")})
        rows.append({"q": q, "kind": kind, "state": r.get("state"), "exp": {k: sorted(v) for k, v in exp.items()}, "got": got})
    if out:
        json.dump(rows, open(out, "w"), indent=1)
    print("done", cfg, len(rows))


if __name__ == "__main__":
    main()
