# Patch notes for the Recourse owner: connecting the Overruled Register to the live site

**Status: written, not applied, not tested inside Recourse.** The Recourse repository is read-only for this project. The insertion points below were read from the checkout at commit `721e063` (`chat_assistant.py`, `recourse_app.py`, `citation_currency.py`); line numbers will have moved. Everything below fails open: if the bundle is missing or anything raises, the answer goes out exactly as it does today.

The register itself, its rules and its numbers are in `REGISTER.md`. Nothing in the register says a case is "good law": it only words what a row says (verified or confirmed rows firmly, candidate rows as "reported ... not yet confirmed by our reviewer"). That keeps `citation_currency.py`'s rule (code never decides good law) intact.

## 1. The bundle

```
python sci_goodlaw.py register-export-site --out <recourse checkout>/overruled_register
```

writes a package of three modules (`cites.py`, `register.py`, `register_guard.py`), an `__init__.py` with `load()`, and `register_slim.json` (about 790 KB, no history or evidence text). It needs nothing else from this repository (the test suite imports it from an empty directory). Re-export it after each weekly review (the review changes row trust and treatment) and redeploy.

## 2. One thin wrapper, `register_hooks.py` (new file in Recourse)

```python
"""Fail-open hooks around the Overruled Register bundle (overruled_register/). Every function returns its input unchanged on any error."""
import logging

logger = logging.getLogger(__name__)
_REG = None


def _reg():
    global _REG
    if _REG is None:
        import overruled_register as OR
        _REG = OR.load()
    return _REG


def prompt_lines_for_match(m):
    """Lock (b): lines for the prompt about the retrieved case itself."""
    try:
        from overruled_register import register_guard as G
        return G.prompt_facts(_reg(), [" ".join(str(x) for x in (m.get("case_name"), m.get("year"), m.get("citation")) if x)])
    except Exception as exc:
        logger.warning("register prompt lines failed: %s", exc)
        return []


def demote_matches(matches):
    """Lock (a): a retrieved judgment whose own case is a firm register row goes to the end of the list and carries m['register_badge']; a candidate row only carries the badge."""
    try:
        from overruled_register import register_guard as G
        chunks = [{"case_name": m.get("case_name"), "year": m.get("year"), "citation": m.get("citation"), "text": None} for m in matches]
        flags = G.retrieval_flags(_reg(), chunks)
        keep, last = [], []
        for m, f in zip(matches, flags):
            if f["action"] in ("badge", "demote_and_badge") and isinstance(m, dict):
                m["register_badge"] = f["own"]
            (last if f["action"] == "demote_and_badge" else keep).append(m)
        return keep + last
    except Exception as exc:
        logger.warning("register demotion failed: %s", exc)
        return matches


def answer_notes(text):
    """Lock (c): {'notes': [sentences to show], 'review': [weak matches for a person]} for a finished answer."""
    try:
        from overruled_register import register_guard as G
        res = G.guard_answer(_reg(), text or "")
        return {"notes": res["notes"], "review": res["review"]}
    except Exception as exc:
        logger.warning("register guard failed: %s", exc)
        return {"notes": [], "review": []}
```

## 3. Lock (b): the prompt (`chat_assistant.format_retrieved_text_for_prompt`, next to the "PROJECT 2 (citation_currency.py)" block)

After the existing currency block for a judgment match add:

```python
        if m.get("case_name"):
            from register_hooks import prompt_lines_for_match
            reg_lines = prompt_lines_for_match(m)
            if reg_lines:
                block += ("\n\n[Overruled Register -- not optional: if you mention this case at all, state this fact in the same sentence]\n"
                          + "\n".join(reg_lines))
```

and one rule in the system prompt, beside the "fold it in as ONE short plain clause" currency rule: *"A line that starts REGISTER FACT is not optional: whenever you mention that case, say how it was treated in the same sentence. A line that starts REGISTER NOTE (not yet confirmed) means say it is reported to have been so treated; never present its holding as settled."* (The existing currency clause stays optional for a minor mention; the register line does not.)

## 4. Lock (a): retrieval (`_answer_question_core`, after the matches are chosen and before they are formatted)

```python
        from register_hooks import demote_matches
        matches = demote_matches(matches)
```

`recourse_app._render_currency_caveat(m)` can show `m["register_badge"]` (a list of sentences) as the badge. Today's effect on the library: none of the 76 library cases is on the verified list; the two candidate hits are Mohan Lal (2018) and Mhetre (2011).

## 5. Lock (c): the finished answer (the one that matters)

In `chat_assistant`, next to `_attach_cited_judgment_links`:

```python
def _attach_register_notes(result):
    """Adds result['register_notes'] -- sentences for every Overruled Register case the answer names without saying it was overruled. Answer states only; never raises."""
    try:
        if not isinstance(result, dict) or result.get("state") not in _LINK_STATES:
            return result
        from register_hooks import answer_notes
        res = answer_notes(result.get("response_text") or "")
        if res["notes"]:
            result["register_notes"] = res["notes"]
        if res["review"]:
            logger.info("register: weak match(es) for review: %s", res["review"])
    except Exception as exc:  # fail-open
        logger.warning("_attach_register_notes failed: %s", exc)
    return result
```

and in `answer_question`: `return _attach_register_notes(_attach_cited_judgment_links(result))`. In `recourse_app.py`, where `cited_judgment_links` is rendered, show `result["register_notes"]` in a box titled "Currency notes (checked by code, not by the model)". The guard scans the finished text, so it also catches a case the model recalled from memory that was never retrieved. (Option: feed the guard into the existing retry loop beside `_find_court_misattributions`, so the model rewrites the sentence once; the box alone is the simpler first step.)

## 6. What to check after applying

- `python test_goodlaw_register.py` (in this repository) passes; in Recourse, call `answer_notes("Mohan Lal v. State of Punjab (2018) 17 SCC 627 held X.")`: one note, naming Mukesh Singh (2020).
- Run the trap-question exam (`register_exam/questions.jsonl`, 50 questions) through the assistant with the hooks off and on, and score both files with `python sci_goodlaw.py register-exam score --answers FILE`. Pass mark: no answer that names a case in a form the register cannot recognise; a lawyer reads 20 answers.
- Decide the visible wording: candidate rows say "reported ... not yet confirmed by our reviewer" until the reviewer confirms them.

## 7. Limits to know

The guard recognises a case by citation, or by both party names plus a year; a bare name ("the Mohan Lal case") is ignored by design, and a case described without its name is invisible. 110 rows of the 2015 list have no citation or year and cannot be recognised until the reviewer supplies one. See "Limits" in `REGISTER.md`.
