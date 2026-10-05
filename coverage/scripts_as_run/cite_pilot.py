import re, sys, collections, json
sys.path.insert(0, "/home/user/recourse-sci-pool")
import sci_index as si
metas, M, _ = si._load_index("/home/user/recourse-sci-index")
print(f"index: {len(metas):,} passages from {len({m['doc'] for m in metas}):,} judgments (ids {min(m['doc'] for m in metas)} to {max(m['doc'] for m in metas)})")
TARGETS = {  # name -> (regex for how later judgments name it, our judgment id)
 "Baldev Singh (1999)":   (r"Baldev\s+Singh", 30317),
 "Bhajan Lal (1990)":     (r"Bhajan\s+Lal", None),
 "Rangappa (2010)":       (r"Rangappa", 36322),
 "Jadeja (2010)":         (r"Vijaysinh|Jadeja", 37060),
 "Md. Ibrahim (2009)":    (r"(?:Md|Mohd|Mohammed)\.?\s+Ibrahim", 35436),
 "Arnesh Kumar (2014)":   (r"Arnesh\s+Kumar", 41736),
 "Nanda Gopalan (2015)":  (r"Nanda\s+Gopalan", 42630),
 "Noor Aga (2008)":       (r"Noor\s+Aga", 31821),
 "Lalita Kumari (2013)":  (r"Lalita\s+Kumari", 40960),
}
CUES = collections.OrderedDict([
 ("followed / relied on / approved", r"\b(followed|relied (?:up)?on|approved|affirmed|reiterated|reaffirmed|held to be correct|laid down|in terms of|as held in|referred to in)\b"),
 ("distinguished / not applicable", r"\b(distinguish(?:ed|able)?|not applicable|inapplicable|different facts|on facts)\b"),
 ("doubted / reconsider / larger bench", r"\b(doubt(?:ed)?|reconsider(?:ation)?|larger bench|referred to a larger|reference to a larger|conflict(?:ing)? (?:of )?(?:view|decision)s?|requires? reconsideration)\b"),
 ("overruled / not good law", r"\b(overrul(?:ed|ing)|not good law|no longer good law|per incuriam|wrongly decided|erroneous(?:ly)?)\b"),
])
SENT = re.compile(r"(?<=[.?!;])\s+")
by_doc = collections.defaultdict(list)
for m in metas: by_doc[m["doc"]].append(m["text"])
out = {}
for name, (rx, tid) in TARGETS.items():
    pat = re.compile(rx)
    citing = {}; cue_docs = collections.defaultdict(set); examples = collections.defaultdict(list)
    for d, texts in by_doc.items():
        if tid is not None and d == tid: continue
        if tid is not None and d < tid: continue        # ids rise with decision date, so a lower id is an earlier case
        for t in texts:
            if not pat.search(t): continue
            sents = SENT.split(re.sub(r"\s+", " ", t))
            for i, s in enumerate(sents):
                if pat.search(s):
                    window = " ".join(sents[max(0, i - 0): i + 2])
                    citing.setdefault(d, 0); citing[d] += 1
                    for cue, crx in CUES.items():
                        if re.search(crx, window, re.I):
                            cue_docs[cue].add(d)
                            if len(examples[cue]) < 2 and cue.startswith(("doubted", "overruled")): examples[cue].append((d, window[:330]))
    out[name] = dict(citing=len(citing), cues={c: len(v) for c, v in cue_docs.items()}, examples=examples)
print("\njudgments in the index that mention each case by name (later ids only), and how many of them use each kind of cue word near the name:")
print(f"{'case':24}{'citing':>8}  " + "  ".join(f"{c.split(' /')[0][:11]:>11}" for c in CUES))
for n, v in out.items():
    print(f"{n:24}{v['citing']:>8}  " + "  ".join(f"{v['cues'].get(c,0):>11}" for c in CUES))
for n in ("Baldev Singh (1999)", "Jadeja (2010)", "Md. Ibrahim (2009)"):
    for cue, ex in out[n]["examples"].items():
        for d, s in ex: print(f"\n[{n} | {cue} | judgment {d}] {s}")
json.dump({n: {k: v for k, v in x.items() if k != 'examples'} for n, x in out.items()}, open("/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/cite_pilot.json", "w"))
