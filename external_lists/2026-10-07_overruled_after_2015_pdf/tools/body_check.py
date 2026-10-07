"""For selected rows, show an adverse sentence about the earlier case in the judgment BODY (after the headnote), to separate the court's own words from the report editors' headnote. Read-only."""
import sys, re, sqlite3
sys.path.insert(0, "/home/user/recourse-sci-pool")
from goodlaw import corpus as K, textutil as X
SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/"
C = K.Corpus(SP + "corpus.sqlite")
CASES = {
 "1,2 Puttaswamy": ("b2017_10_569_999", r"M\.?\s?P\.? Sharma|Kharak\s+Singh"),
 "3 Puttaswamy/ADM": ("b2017_10_569_999", r"ADM\s*\.?\s*Jabalpur"),
 "6,7 HCC": ("b2017_13_1009_1052", r"Saith|Guru\s+Nanak"),
 "8 Dilip Kumar": ("b2018_7_1191_1231", r"Sun\s+Export"),
 "9 Navtej": ("b2018_7_379_746", r"Koushal"),
 "40 Borse": ("b2021_3_193_254", r"N\.?V\.? International"),
 "44-46 Arup Bhuyan": ("b2023_8_496_580", r"Arup\s+Bhuyan|Indra\s+Das|Raneef"),
 "48 AMU": ("b2024_11_1647_2038", r"Azeez\s+Basha"),
}
OV = re.compile(r"overrul|not (?:a )?good law|not (?:the )?correct|wrongly decided|does not lay down|do not lay down|cannot be (?:sustained|accepted)", re.I)
for label, (key, pat) in CASES.items():
    d = C.get(key); t = X.flatten(d["text"])
    bs = d.get("body_start") or 0
    body = t[int(bs):] if bs else t[len(t)//8:]
    sents = re.split(r"(?<=[.;])\s+", body)
    out = []
    for i, s in enumerate(sents):
        if re.search(pat, s, re.I) and OV.search(s):
            out.append(re.sub(r"\s+", " ", s)[:420])
        if len(out) >= 3: break
    print(f"### {label} [{key}] body_start={bs} hits={len(out)}")
    for o in out: print("   -", o)
