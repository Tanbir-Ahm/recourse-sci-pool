import sys, glob, os, importlib
base = "/home/user/recourse-sci-pool/review_results"
qs = []
for d in [base + "/2026-11-03_retrieval_misses", base + "/2026-10-31_relevance_gate", base + "/2026-11-03_relevance_neighbours", base + "/2026-11-09_harbouring_alias", base + "/2026-11-09_bail_alias"]:
    sys.path.insert(0, d)
    for f in sorted(glob.glob(d + "/questions*.py")):
        m = os.path.basename(f)[:-3]
        if m == "q_all": continue
        try: mod = importlib.import_module(m)
        except Exception: continue
        for name in dir(mod):
            v = getattr(mod, name)
            if isinstance(v, list):
                for it in v:
                    s = it[0] if isinstance(it, (tuple, list)) and it else it
                    if isinstance(s, str) and len(s) > 25: qs.append(s)
qs = list(dict.fromkeys(qs))
POS = [(q, {}, "x") for q in qs]
