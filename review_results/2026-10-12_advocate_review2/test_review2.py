"""Tests Mr. Advocate's second review (section-by-section triggers for PWDVA, NDPS, UAPA; leading cases) against the index and Machine Spec v2. Dev check, no Voyage calls. PRIVATE."""
import collections, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, ROOT)
import machine_spec_v2 as S, pool_runner as PR, sci_index as si
TXT = open("/tmp/claude-0/adv2.txt", encoding="utf-8").read().split("\n")
# --- his plain-language phrases, by Act and section (table rows: Section || subject || phrases)
phr = []   # (act, section, phrase)
act = None
for ln in TXT:
    if ln.startswith("The Protection of Women from Domestic Violence Act"): act = "PWDVA"
    if ln.startswith("1. NDPS Act"): act = "NDPS"
    if ln.startswith("2. UAPA"): act = "UAPA"
    if " || " in ln and act and re.match(r"^\d+[A-Z]? \|\|", ln):
        cells = ln.split(" || ")
        sec = cells[0]
        for p in re.findall(r"“([^”]+)”", cells[-1]):
            phr.append((act, sec, p))
print("1. HIS PLAIN-LANGUAGE PHRASES:", len(phr), collections.Counter(a for a, _, _ in phr))
res = collections.defaultdict(lambda: collections.Counter())
cross = collections.Counter(); misses = []
for a, sec, p in phr:
    n1, n2 = S.question_acts(p, "N1"), S.question_acts(p, "N2")
    res[a]["phrases"] += 1
    res[a]["N1_intended"] += a in n1; res[a]["N2_intended"] += a in n2
    for o in n2:
        if o != a: cross[(a, o)] += 1
    if a not in n2: misses.append((a, sec, p))
for a in ("PWDVA", "NDPS", "UAPA"):
    r = res[a]; print(f"   {a}: {r['phrases']} phrases | intended Act fires under N1: {r['N1_intended']} | under N2: {r['N2_intended']}")
print("   fired a DIFFERENT Act under N2 (from_act -> other_act: count):", dict(cross))
print("   examples of phrases that fire nothing (N2):")
for a, sec, p in misses[:40]: print(f"      [{a} s.{sec}] {p}")
# --- his key cases in the index and in the v2 labels
head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, _, _ = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
labels = S.judgment_labels((m["doc"], m["h"], m["text"]) for m in metas)
tmap = PR.titles([PR.DEFAULT_INDEX], metas, None)
docs = {m["doc"] for m in metas}
cases = [("SATISH CHANDER AHUJA", "PWDVA"), ("ROHAN SHAH", "PWDVA"), ("NEHA CHATURVEDI", "PWDVA"), ("KARNAIL SINGH", "NDPS"), ("VIJAYSINH", "NDPS"), ("TOFAN SINGH", "NDPS"), ("MOHANLAL", "NDPS"), ("WATALI", "UAPA"), ("THWAHA", "UAPA")]
print("\n2. HIS LEADING CASES: in the index? labelled with the intended Act by v2?")
for key, a in cases:
    f = [(d, str(tmap(d))[:75]) for d in docs if key in str(tmap(d)).upper()]
    if not f: print(f"   {key}: NOT in the index"); continue
    for d, t in f[:3]:
        n = sum(1 for m in metas if m["doc"] == d)
        k = sum(1 for m in metas if m["doc"] == d and a in S.passage_acts(m["text"]))
        print(f"   {key}: doc {d} {t} | passages {n}, marked {a}: {k}, labelled {a}: {d in labels[a]}")
# --- section-specific markers: how common are his section/Act pairs in the index (distinct passages)
pairs = [("PWDVA", r"\bsections?\s*17\s+of\s+the\s+(?:Domestic Violence Act|Protection of Women from Domestic Violence Act|(?-i:DV Act|PWDVA))"), ("NDPS", r"\bsection\s*50\s+of\s+the\s+(?:(?-i:NDPS)|Narcotic Drugs and Psychotropic Substances)\s*Act"),
         ("NDPS", r"\bsection\s*67\s+of\s+the\s+(?:(?-i:NDPS)|Narcotic Drugs and Psychotropic Substances)\s*Act"), ("NDPS", r"\bsection\s*52A\s+of\s+the\s+(?:(?-i:NDPS)|Narcotic Drugs and Psychotropic Substances)\s*Act"),
         ("UAPA", r"\bsection\s*43D\s*\(\s*5\s*\)"), ("UAPA", r"\bsection\s*43E\b"), ("UAPA", r"\bsections?\s*(?:38|39)\s+of\s+the\s+(?:(?-i:UAPA)|Unlawful Activities \(Prevention\) Act)")]
print("\n3. HOW OFTEN HIS KEY SECTIONS APPEAR AS ACT-LINKED CITATIONS (passages):")
for a, rx in pairs:
    r = re.compile(rx, S.FLAGS); print(f"   {a}: {rx[:70]}: {sum(1 for m in metas if r.search(m['text']))}")
