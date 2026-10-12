"""The three arms of the fix test (FIX_TEST_RULES_v1.md, frozen 2026-10-12), as pure functions: C (cap of 2 per judgment in the top 5), N1 and N2 (named-Act boost, precise or broader question anchors).
Nothing here calls a service. The runner (`pool_runner.py --fix-test`) gives these functions the scores of ONE re-rank call, so B, C, N1 and N2 are compared on the same candidates and the same scores."""
import machine_spec_v2 as S

B_VERSION = "B baseline (rerank-3-lite)"
C_VERSION = "C cap 2 per judgment"
N1_VERSION = "N1 named-Act boost (precise)"
N2_VERSION = "N2 named-Act boost (broad)"
FIX_VERSIONS = (B_VERSION, C_VERSION, N1_VERSION, N2_VERSION)
BOOST = 1.10                      # the section-number boost's size, the same for N1 and N2 (rules, section 1)
CAP, TOP, SHOWN = 2, 5, 10


def order_by(scores):
    return [r for r, _ in sorted(scores.items(), key=lambda x: -x[1])]


def cap_per_judgment(order, doc_of, cap=CAP, top=TOP, shown=SHOWN):
    """C. `order`: all candidates, best first. Places 1 to `top` are filled in score order, skipping a passage when `cap` passages of its judgment already hold places; the skipped passages are not
    lost: they go back among the rest, and places top+1 to `shown` are the best of everything not placed, in score order."""
    placed, used = [], {}
    for r in order:
        if len(placed) == top:
            break
        d = doc_of(r)
        if used.get(d, 0) >= cap:
            continue
        placed.append(r)
        used[d] = used.get(d, 0) + 1
    chosen = set(placed)
    return (placed + [r for r in order if r not in chosen])[:shown]


def boosted_docs(question, tier, labels):
    """(acts that fire, set of judgments that carry any fired Act's label). tier 'N1' (precise anchors) or 'N2' (precise or plain-language). `labels`: {act: set(docs)} from machine_spec_v2.judgment_labels."""
    acts = S.question_acts(question, tier)
    docs = set()
    for a in acts:
        docs |= labels[a]
    return sorted(acts), docs


def apply_boost(final, doc_of, docs, factor=BOOST):
    """Every passage of a labelled judgment has its final score multiplied by `factor`, once. The scores given are already (re-ranker x type weight x section boost)."""
    if not docs:
        return dict(final)
    return {r: s * (factor if doc_of(r) in docs else 1.0) for r, s in final.items()}


def arms(question, final, doc_of, labels):
    """{version: ordered top 10}, {'N1': [acts], 'N2': [acts]} for one question, from `final` = {row id: score}."""
    base = order_by(final)
    out = {B_VERSION: base[:SHOWN], C_VERSION: cap_per_judgment(base, doc_of)}
    fired = {}
    for tier, version in (("N1", N1_VERSION), ("N2", N2_VERSION)):
        acts, docs = boosted_docs(question, tier, labels)
        fired[tier] = acts
        out[version] = order_by(apply_boost(final, doc_of, docs))[:SHOWN]
    return out, fired
