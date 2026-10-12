"""Follow-up checks on Mr. Advocate's regexes: (a) repair of the PWDVA passage pattern, (b) precision of the two standalone NDPS phrases, (c) case-insensitive acronyms, (d) hyphen and 'the' variants of Act titles, (e) the PC Act / NDPS supplement patterns. PRIVATE, dev only."""
import collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, ROOT)
import pool_runner as PR, sci_index as si
TXT = open("/tmp/claude-0/advocate_doc.txt", encoding="utf-8").read().split("\n")
def grab(label_start, after_text):
    i = next(k for k, l in enumerate(TXT) if l.startswith(after_text))
    j = next(k for k in range(i, len(TXT)) if TXT[k].startswith(label_start))
    return TXT[j + 1].strip()
# (a) PWDVA passage pattern
i0 = next(k for k, l in enumerate(TXT) if l.startswith("Protection of Women from Domestic Violence Act, 2005") and TXT[k + 1].startswith("Risk rating"))
pw = next(TXT[k + 1].strip() for k in range(i0, i0 + 9) if TXT[k].startswith("Recommended passage-side strong marker"))
fixed = pw.replace("(?:Domestic Violence Act|PWDVA)\\b|\\bprotection officer", "(?:Domestic Violence Act|PWDVA)\\b)|\\bprotection officer")
try:
    re.compile(pw); print("(a) original compiles?! (unexpected)")
except re.error as e:
    print("(a) original PWDVA passage pattern: COMPILE ERROR:", e)
rx_pw = re.compile(fixed); print("    repaired by closing the 'section ... of the Act' group; compiles: True")
head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, _, _ = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
per = collections.Counter(m["doc"] for m in metas if rx_pw.search(m["text"]))
print("    repaired pattern: passages", sum(per.values()), "| judgments", len(per), "| with 3+ marked passages", sum(1 for v in per.values() if v >= 3), "(my draft: 262 passages, 18 judgments with 3+)")
# which alternative carries it
alts = {"title/PWDVA/DV Act": re.compile(r"(?i)\b(?:Protection of Women from Domestic Violence Act|PWDVA|DV Act)\b"), "section N of the DV Act": re.compile(r"(?i)\bsection\s*(?:12|18|19|20|21|22|23|31)\s+of\s+(?:the\s+)?(?:Domestic Violence Act|PWDVA)\b"),
        "protection officer": re.compile(r"(?i)\bprotection officer\b"), "aggrieved woman": re.compile(r"(?i)\baggrieved woman\b"), "shared household + order": re.compile(r"(?i)\bshared household\b.{0,100}\b(?:residence|protection|monetary|compensation|ex parte)\s+order\b")}
for k, r in alts.items():
    c = collections.Counter(m["doc"] for m in metas if r.search(m["text"]))
    print(f"      {k:28} passages {sum(c.values()):5} judgments {len(c):4}")
# (b) NDPS standalone phrases
nd_title = re.compile(r"(?i)\bNDPS(?:\s+Act)?\b|\bNarcotic Drugs and Psychotropic Substances Act\b")
nd_stand = re.compile(r"(?i)\b(?:commercial quantity|conscious possession)\b")
dt = collections.Counter(m["doc"] for m in metas if nd_title.search(m["text"]))
ds = collections.Counter(m["doc"] for m in metas if nd_stand.search(m["text"]))
only_stand = [d for d, v in ds.items() if v >= 3 and dt.get(d, 0) == 0]
print(f"\n(b) NDPS: judgments with 3+ passages carrying 'commercial quantity' or 'conscious possession': {sum(1 for v in ds.values() if v >= 3)}; of them with NO passage naming the NDPS Act at all: {len(only_stand)}")
tmap = PR.titles([PR.DEFAULT_INDEX], metas, None)
for d in only_stand[:8]:
    print("      ", d, str(tmap(d))[:70])
# (c) case-insensitive acronyms
print("\n(c) acronyms that become ordinary words when case-insensitive:")
for name, ci, cs in (("IT Act", r"(?i)\bIT Act\b", r"\bIT Act\b"), ("PC Act", r"(?i)\bPC Act\b", r"\bPC Act\b"), ("DV Act", r"(?i)\bDV Act\b", r"\bDV Act\b"), ("MV Act", r"(?i)\bMV Act\b", r"\bMV Act\b"), ("NI Act", r"(?i)\bNI Act\b", r"\bNI Act\b"), ("JJ Act", r"(?i)\bJJ Act\b", r"\bJJ Act\b"), ("DP Act", r"(?i)\bDP Act\b", r"\bDP Act\b")):
    a = re.compile(ci); b = re.compile(cs)
    na = sum(1 for m in metas if a.search(m["text"])); nb = sum(1 for m in metas if b.search(m["text"]))
    print(f"      {name}: case-insensitive {na} passages, upper-case only {nb}")
# (d) variants
def cnt(rx, fl=re.I): r = re.compile(rx, fl); return sum(1 for m in metas if r.search(m["text"]))
print("\n(d) title variants his patterns miss: 'Money-Laundering' (hyphen)", cnt(r"prevention of money-laundering act"), "of", cnt(r"prevention of money[- ]laundering act"), "| 'Scheduled Castes and the Scheduled Tribes' (with 'the')", cnt(r"scheduled castes and the scheduled tribes \(prevention of atrocities\) act"), "of", cnt(r"scheduled castes and (?:the )?scheduled tribes \(prevention of atrocities\) act"))
# (e) supplements: compile
sup = [l.strip() for l in TXT if l.startswith("(?i)\\b") and ("17A" in l or "Section\\s*17\\s" in l or "Section\\s*19\\s" in l or "previous|prior" in l or "demand|acceptance" in l or "preliminary" in l or "abettor" in l or "known sources" in l or "pending work" in l or "recovery|seizure" in l or "no recovery" in l or "kingpin" in l or "cartel|drug network" in l or "NDPS|narcotic drugs and psychotropic substances act" in l)]
print("\n(e) supplement patterns found:", len(sup))
bad = 0
for s in sup:
    try: re.compile(s)
    except re.error as e: bad += 1; print("      COMPILE ERROR:", e, "|", s[:80])
print("      all compile" if not bad else f"      {bad} do not compile")
tests = [("is previous sanction required under Section 19 of the PC Act", True), ("official asked for a bribe to expedite pending work", True), ("pending work in my file at the office", False), ("police alleged no recovery of contraband from the accused under NDPS", True), ("the kingpin of the gang was caught", False), ("demand and acceptance of illegal gratification by a public servant", True)]
crx = [re.compile(s) for s in sup]
for text, exp in tests:
    got = any(r.search(text) for r in crx)
    print(f"      {'ok  ' if got == exp else 'WRONG'} expected {str(exp):5} got {str(got):5} | {text}")
