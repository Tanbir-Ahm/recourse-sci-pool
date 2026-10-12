"""Round 2: spot-checks of statements in the replacement keys (N02, N12, N15, and the N20 addition) against the text of the judgments that are in the index. Read-only, no spend, nothing searched for any question.
Each line: (question, index doc, what the key says, a regular expression for words the judgment should contain). A match shows the words are there, a miss shows they are not in this judgment's indexed text. PRIVATE."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, ROOT)
import pool_runner as PR, sci_index as si
head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, _, _ = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
by = {}
for m in metas:
    by.setdefault(m["doc"], []).append(m["text"])
C = [
 ("N02", 14580, "D.K. Basu: a person arrested must be produced before the Magistrate within 24 hours (Art. 22(2), s.57 CrPC)", r"(?:twenty[- ]four|24)\s*hours"),
 ("N02", 14580, "D.K. Basu: Article 22(2) mentioned", r"22\s*\(\s*2\s*\)"),
 ("N02", 14580, "D.K. Basu: section 57 CrPC mentioned", r"section\s*57\b|\bs\.\s*57\b"),
 ("N02", 41736, "Arnesh Kumar: arrest safeguards; refers to D.K. Basu; production before the Magistrate", r"D\.?\s?K\.?\s?Basu|Magistrate"),
 ("N12", 39579, "Gian Singh: High Court may quash non-compoundable offences on settlement (s.482 CrPC)", r"(?:settle|compromise).{0,400}(?:482|inherent)|(?:482|inherent).{0,400}(?:settle|compromise)"),
 ("N12", 39579, "Gian Singh: bench", r"Constitution Bench|three[- ]Judge|Hon.ble.{0,30}Chief Justice|LODHA"),
 ("N12", 1000250282, "Parbatbhai Aahir: parameters for quashing on settlement; follows Gian Singh", r"Gian Singh"),
 ("N12", 1000250282, "Parbatbhai Aahir: economic offences of large magnitude / serious impact on society are not quashed", r"economic|society"),
 ("N12", 41348, "Narinder Singh: guidelines for quashing where the parties have settled", r"(?:settle|compromise).{0,300}(?:quash|482)|(?:quash|482).{0,300}(?:settle|compromise)"),
 ("N12", 41348, "Narinder Singh: cheating / s.420 mentioned", r"\b420\b|cheating"),
 ("N15", 1000252794, "Rajnesh v. Neha: interim maintenance; overlapping proceedings; disclosure of assets", r"interim maintenance"),
 ("N15", 1000252794, "Rajnesh v. Neha: Domestic Violence Act mentioned", r"Domestic Violence"),
 ("N15", 1000252794, "Rajnesh v. Neha: section 20 or 23 of the DV Act", r"Section\s*(?:20|23)\b"),
 ("N15", 1000252355, "Shyamlal Devda: interim maintenance", r"interim maintenance|maintenance pendente"),
 ("N15", 1000252355, "Shyamlal Devda: Domestic Violence Act mentioned", r"Domestic Violence"),
 ("N15", 1000004478, "Juveria: monetary relief under s.20 of the DV Act", r"monetary relief|Section\s*20\b"),
 ("N15", 1000004478, "Juveria: interim maintenance", r"interim"),
]
for q, doc, says, rx in C:
    ps = by.get(doc, [])
    pat = re.compile(rx, re.I | re.S)
    hit = [t for t in ps if pat.search(t)]
    print(f"{q} doc {doc}: {len(hit)} of {len(ps)} passages match  | the key: {says}")
    if hit:
        t = re.sub(r"\s+", " ", hit[0])
        m = pat.search(t)
        a = max(0, (m.start() if m else 0) - 160)
        print("      ...", t[a:a + 560])
