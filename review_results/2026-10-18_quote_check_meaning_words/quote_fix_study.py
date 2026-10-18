"""Old vs new quote check on real library text (Recourse chunks/*.json). Random 22-48 word spans; each span is perturbed in one way and put in quotation marks.
HARMLESS edits should stay unflagged; MEANING edits (a decisive word deleted, swapped, a number changed) should be flagged. Counts only quotes the old check accepted."""
import sys, json, random, glob, importlib.util
sys.path.insert(0, "/home/user/recourse")
import grounding_checks as NEW
spec = importlib.util.spec_from_file_location("gc_old", sys.argv[1]); OLD = importlib.util.module_from_spec(spec); spec.loader.exec_module(OLD)
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 11)
texts = []
for f in sorted(glob.glob("/home/user/recourse/chunks/*.json")):
    try: d = json.load(open(f, encoding="utf-8"))
    except Exception: continue
    for c in (d if isinstance(d, list) else d.get("chunks", [])):
        t = c.get("text") if isinstance(c, dict) else None
        if t and len(t.split()) > 120: texts.append(t)
FLIP = NEW._FLIP | NEW._NUMBER_WORDS
tok = lambda w: w.lower().strip(".,;:()[]\"'“”‘’")
isflip = lambda w: tok(w) in FLIP or tok(w).isdigit()
FUNC = {"the", "a", "an", "of", "to", "in", "that", "is", "by", "for", "on", "as", "it", "be", "this", "with", "from"}
def span():
    t = random.choice(texts); w = t.split(); i = random.randrange(0, len(w) - 60)
    return t, w[i:i + random.randint(22, 48)]
def p_drop_func(w):
    idx = [k for k in range(2, len(w) - 2) if tok(w[k]) in FUNC]
    if not idx: return None
    w = list(w); del w[random.choice(idx)]; return w
def p_drop_two_func(w):
    idx = [k for k in range(2, len(w) - 2) if tok(w[k]) in FUNC]
    if len(idx) < 2: return None
    w = list(w)
    for k in sorted(random.sample(idx, 2), reverse=True): del w[k]
    return w
def p_add_func(w):
    w = list(w); w.insert(random.randrange(2, len(w) - 2), random.choice(["the", "a", "also", "thus"])); return w
def p_hyphen(w):
    s = " ".join(w)
    return s.replace("-", " ", 1).split() if "-" in s else None
def p_tiny_spelling(w):
    idx = [k for k in range(2, len(w) - 2) if len(tok(w[k])) > 6 and tok(w[k]).isalpha() and not isflip(w[k])]
    if not idx: return None
    k = random.choice(idx); w = list(w); w[k] = w[k] + "s"; return w
def p_delete_flip(w):
    idx = [k for k in range(2, len(w) - 2) if isflip(w[k])]
    if not idx: return None
    w = list(w); del w[random.choice(idx)]; return w
def p_swap_flip(w):
    pairs = {"may": "shall", "shall": "may", "not": "now", "and": "or", "or": "and", "any": "no", "all": "some", "must": "may", "only": "also", "unless": "if", "except": "including", "no": "any", "can": "cannot"}
    idx = [k for k in range(2, len(w) - 2) if tok(w[k]) in pairs]
    if not idx: return None
    k = random.choice(idx); w = list(w); w[k] = pairs[tok(w[k])]; return w
def p_change_number(w):
    idx = [k for k in range(2, len(w) - 2) if tok(w[k]).isdigit() or tok(w[k]) in NEW._NUMBER_WORDS]
    if not idx: return None
    k = random.choice(idx); w = list(w); t = tok(w[k]); w[k] = str(int(t) + 1) if t.isdigit() else ("two" if t != "two" else "three"); return w
HARMLESS = [("drop one article/preposition", p_drop_func), ("drop two of them", p_drop_two_func), ("add a small word", p_add_func), ("hyphen -> space", p_hyphen), ("ordinary word +s", p_tiny_spelling)]
MEANING = [("delete a decisive word", p_delete_flip), ("swap a decisive word", p_swap_flip), ("change a number", p_change_number)]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 700
res = {}
for kind, group in (("HARMLESS", HARMLESS), ("MEANING", MEANING)):
    for name, fn in group:
        tried = old_ok = new_flag_of_old_ok = old_flag = new_flag = 0; ex = []
        n = 0
        while n < N:
            t, w = span(); n += 1
            q = fn(w)
            if not q: continue
            ans = 'The court said "%s" there.' % " ".join(q)
            o, nw = OLD.check_quotes(ans, t), NEW.check_quotes(ans, t)
            tried += 1; old_flag += bool(o); new_flag += bool(nw)
            if not o:
                old_ok += 1
                if nw:
                    new_flag_of_old_ok += 1
                    if len(ex) < 2: ex.append(" ".join(q)[:150])
        res[(kind, name)] = (tried, old_flag, new_flag, old_ok, new_flag_of_old_ok, ex)
print(f"{'':9s}{'edit':30s} {'tried':>6s} {'old flags':>10s} {'new flags':>10s}   newly flagged among those old accepted")
for (kind, name), (tried, of, nf, ook, nfo, ex) in res.items():
    print(f"{kind:9s}{name:30s} {tried:6d} {of:10d} {nf:10d}   {nfo} of {ook}")
    for e in ex: print("            e.g.", e)
