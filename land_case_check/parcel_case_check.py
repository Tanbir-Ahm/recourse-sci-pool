#!/usr/bin/env python3
"""Pilot: check land parcels against eCourtsIndia case data, cheaply and with evidence.

Why a cascade and not one three-field search: the eCourtsIndia case search takes party names, filters and
free text, but has no father's-name field and no dag field. So this tool
  1. searches each holder's name (several English spellings, fuzzy) in the chosen state/district,
  2. scores every hit locally: name, then father (when the party string carries "S/O ..."),
  3. pays for case detail only for the best candidates,
  4. scans the order/judgment text in that detail for the parcel's dag/patta numbers and village names.
Every call is metered against a hard rupee budget. Raw replies are saved so the real response layout can be
checked on the first run (the public docs do not show it).

Usage:
  ECI_TOKEN=eci_live_... python parcel_case_check.py parcels.json --budget 150 --plan payg --state-code <code>
  python parcel_case_check.py --selftest
Input file: a list of parcels, see SAMPLE in this file.  Never commit the token or the raw replies.
"""
import argparse, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request, urllib.error

BASE = "https://webapi.ecourtsindia.com/api/partner"
PRICES = {"payg": {"search": 0.60, "detail": 1.50, "order": 5.25},
          "enterprise": {"search": 0.20, "detail": 0.50, "order": 1.75}}
DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
SAMPLE = [{"label": "example parcel", "dags": ["781"], "patta": ["196"],
           "places_en": ["Kalitakuchi", "Hajo"],
           "holders": [{"name": "ৰমেশ কুমাৰ শৰ্মা", "father": "মহেশ শৰ্মা"}]}]

# ---------- Assamese <-> English name bridge (sound classes, vowels dropped) ----------
ASM = {"ক": "K", "খ": "K", "গ": "G", "ঘ": "G", "ঙ": "N", "চ": "S", "ছ": "S", "জ": "Z", "ঝ": "Z", "ঞ": "N",
       "ট": "T", "ঠ": "T", "ড": "D", "ঢ": "D", "ণ": "N", "ত": "T", "থ": "T", "দ": "D", "ধ": "D", "ন": "N",
       "প": "P", "ফ": "P", "ব": "B", "ভ": "B", "ম": "M", "য": "Z", "ৰ": "R", "র": "R", "ল": "L", "ৱ": "B",
       "শ": "S", "ষ": "S", "স": "S", "হ": "H", "ং": "N", "ৎ": "T"}
LAT_DIGRAPH = [("ch", "S"), ("sh", "S"), ("kh", "K"), ("gh", "G"), ("th", "T"), ("dh", "D"), ("ph", "P"),
               ("bh", "B"), ("jh", "Z"), ("zh", "Z"), ("ng", "N")]
LAT = {"b": "B", "c": "K", "d": "D", "f": "P", "g": "G", "h": "H", "j": "Z", "k": "K", "l": "L", "m": "M", "n": "N",
       "p": "P", "q": "K", "r": "R", "s": "S", "t": "T", "v": "B", "w": "B", "x": "S", "z": "Z"}
TITLES = {"md", "mohd", "sri", "shri", "smt", "mst", "mrs", "mr", "late", "lt", "of", "son", "daughter", "wife",
          "haji", "hazi", "syed", "sayed", "sd", "s", "o", "d", "w", "c"}
ASM_TITLES = {"মঃ", "মোঃ", "মহঃ", "মুঃ", "চৈঃ", "চৈয়দ", "ছৈয়দ", "চৈয়দা", "শ্ৰী", "শ্ৰীমতী", "মছঃ", "মোছাঃ", "মৃত",
              "স্বৰ্গীয়", "স্বৰ্গীয়", "পিতা", "পিতাঃ", "স্বামী", "স্বামীঃ", "স্বাঃ", "হাজী", "হাজি"}
ALIAS = {"আলী": ["Ali"], "আলি": ["Ali"], "আহমেদ": ["Ahmed", "Ahmad"], "হুছেইন": ["Hussain", "Hossain", "Husain"],
         "ৰহমান": ["Rahman", "Rahaman"], "বেগম": ["Begum"], "খাতুন": ["Khatun"], "শৰ্মা": ["Sarma", "Sharma"],
         "দাস": ["Das"], "দেৱী": ["Devi"], "বৰুৱা": ["Baruah", "Barua"], "বৰা": ["Bora", "Boro"], "হাজৰিকা": ["Hazarika"],
         "গোস্বামী": ["Goswami"], "কলিতা": ["Kalita"], "নাথ": ["Nath"], "কুমাৰ": ["Kumar"],
         "চৌধুৰী": ["Choudhury", "Chowdhury"], "মহম্মদ": ["Mohammad", "Mohammed"], "নুৰ": ["Nur", "Noor"],
         "আব্দুল": ["Abdul"], "মকবুল": ["Maqbool", "Makbul"], "ইছলাম": ["Islam"]}


def skel_asm(word):
    s = unicodedata.normalize("NFC", word)
    out, i = [], 0
    while i < len(s):
        c, nxt = s[i], s[i + 1] if i + 1 < len(s) else ""
        if nxt == "়":                        # nukta: য় is a glide, ড় / ঢ় are r-sounds
            if c in "ডঢ":
                out.append("R")
            i += 2
            continue
        if c in ASM:
            out.append(ASM[c])
        i += 1
    return collapse("".join(out))


def skel_lat(word):
    s = re.sub(r"[^a-z]", "", word.lower())
    for dg, cl in LAT_DIGRAPH:
        s = s.replace(dg, cl.lower() + "#")
    out = []
    for ch in s:
        if ch == "#":
            continue
        out.append(LAT.get(ch, ch.upper() if ch.isupper() else ""))
    return collapse("".join(out))


def collapse(s):
    return re.sub(r"(.)\1+", r"\1", s)


def tokens_asm(text):
    return [skel_asm(t) for t in re.split(r"[\s\-:.,()]+", unicodedata.normalize("NFC", text)) if t and t not in ASM_TITLES and skel_asm(t)]


def tokens_lat(text):
    return [skel_lat(t) for t in re.split(r"[^A-Za-z]+", text) if t and t.lower() not in TITLES and skel_lat(t)]


def lev(a, b):
    p = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        c = [i]
        for j in range(1, len(b) + 1):
            c.append(min(p[j] + 1, c[j - 1] + 1, p[j - 1] + (a[i - 1] != b[j - 1])))
        p = c
    return p[-1]


def set_score(A, B):
    if not A or not B:
        return 0.0
    s, l = (A, B) if len(A) <= len(B) else (B, A)
    used, tot = set(), 0.0
    for t in s:
        best, bi = 0.0, -1
        for i, u in enumerate(l):
            if i not in used:
                r = 1 - lev(t, u) / max(len(t), len(u))
                if r > best:
                    best, bi = r, i
        if bi >= 0:
            used.add(bi)
        tot += best
    return (tot / len(s)) * (0.7 + 0.3 * len(s) / len(l))


def english_queries(name_as, limit=4):
    """Up to `limit` English spellings to send to the fuzzy party search (OR'd)."""
    words = [w for w in re.split(r"\s+", name_as.strip()) if w and w not in ASM_TITLES]
    opts = []
    for w in words:
        opts.append(ALIAS.get(w) or [translit(w, "a"), translit(w, "o")])
    combos = [[]]
    for o in opts:
        combos = [c + [x] for c in combos for x in o][:limit * 3]
    seen, res = set(), []
    for c in combos:
        q = " ".join(c)
        if q.lower() not in seen:
            seen.add(q.lower())
            res.append(q)
    return res[:limit]


def translit(word, inherent="a"):
    M = {"ক": "k", "খ": "kh", "গ": "g", "ঘ": "gh", "ঙ": "ng", "চ": "ch", "ছ": "s", "জ": "j", "ঝ": "jh", "ঞ": "n",
         "ট": "t", "ঠ": "th", "ড": "d", "ঢ": "dh", "ণ": "n", "ত": "t", "থ": "th", "দ": "d", "ধ": "dh", "ন": "n",
         "প": "p", "ফ": "f", "ব": "b", "ভ": "bh", "ম": "m", "য": "j", "ৰ": "r", "র": "r", "ল": "l", "ৱ": "w",
         "শ": "s", "ষ": "s", "স": "s", "হ": "h", "ং": "ng"}
    V = {"অ": "o", "আ": "a", "ই": "i", "ঈ": "i", "উ": "u", "ঊ": "u", "ঋ": "ri", "এ": "e", "ঐ": "oi", "ও": "o", "ঔ": "ou"}
    S = {"া": "a", "ি": "i", "ী": "i", "ু": "u", "ূ": "u", "ৃ": "ri", "ে": "e", "ৈ": "oi", "ো": "o", "ৌ": "ou"}
    s = unicodedata.normalize("NFC", word)
    out = []
    for i, c in enumerate(s):
        nxt = s[i + 1] if i + 1 < len(s) else ""
        if c in M:
            out.append(M[c])
            if nxt == "্":
                continue
            if nxt in S:
                continue
            if nxt and nxt not in "ংঁঃ়":
                out.append(inherent)
        elif c in S:
            out.append(S[c])
        elif c in V:
            out.append(V[c])
    return "".join(out)


# ---------- reading court text ----------
def norm_text(t):
    return re.sub(r"\s+", " ", (t or "").translate(DIGITS))


def numbers_after(text, key_re, span=70):
    found = set()
    for m in re.finditer(key_re, text, re.I):
        found.update(re.findall(r"\d+", text[m.end():m.end() + span]))
    return found


def scan_text(text, parcel):
    t = norm_text(text)
    dag = numbers_after(t, r"\bdags?\b|দাগ") & set(map(str, parcel.get("dags", [])))
    patta = numbers_after(t, r"\bpattas?\b|পট্টা") & set(map(str, parcel.get("patta", [])))
    low = t.lower()
    places = [p for p in parcel.get("places_en", []) if p.lower() in low]
    snippet = ""
    if dag:
        m = re.search(r"\bdags?\b|দাগ", t, re.I)
        snippet = t[max(0, m.start() - 80):m.end() + 140] if m else ""
    return {"dag_hit": sorted(dag), "patta_hit": sorted(patta), "place_hit": places, "snippet": snippet}


def strings_under(obj, key):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, str):
                out.append(v)
            else:
                out += strings_under(v, key)
    elif isinstance(obj, list):
        for v in obj:
            out += strings_under(v, key)
    return out


def find_cases(obj):
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj) and any("cnr" in x for x in obj):
            return [x for x in obj if "cnr" in x]
        for v in obj:
            r = find_cases(v)
            if r:
                return r
    elif isinstance(obj, dict):
        for v in obj.values():
            r = find_cases(v)
            if r:
                return r
    return []


REL = re.compile(r"\b(?:s/o|d/o|w/o|c/o|son of|daughter of|wife of)\b", re.I)
LANDY = ("title", "partition", "injunction", "possession", "specific relief", "land", "mutation", "eviction",
         "tenancy", "transfer of property", "declaration", "ejectment", "revenue")


def party_match(holder, case):
    hn, hf = tokens_asm(holder["name"]), tokens_asm(holder.get("father", ""))
    best = {"name": 0.0, "father": None, "party": ""}
    for p in (case.get("petitioners") or []) + (case.get("respondents") or []):
        parts = REL.split(str(p), maxsplit=1)
        ns = set_score(hn, tokens_lat(parts[0]))
        if ns > best["name"]:
            fs = set_score(hf, tokens_lat(parts[1])) if len(parts) > 1 and hf else None
            best = {"name": ns, "father": fs, "party": str(p)}
    return best


def level(m, scan):
    if scan["dag_hit"] and scan["place_hit"]:
        return 3, "text cites this dag and the village"
    if m["name"] >= 0.85 and ((m["father"] or 0) >= 0.85 or scan["place_hit"]):
        return 2, "name and (father or village) match"
    if scan["dag_hit"]:
        return 1, "dag number only: dag numbers repeat across villages, unconfirmed"
    if m["name"] >= 0.85:
        return 1, "name only"
    return 0, "weak"


# ---------- metered API client ----------
class BudgetExceeded(Exception):
    pass


class Api:
    def __init__(self, token, plan, budget, raw_dir=None):
        self.token, self.price, self.budget, self.spent, self.n, self.raw_dir = token, PRICES[plan], budget, 0.0, 0, raw_dir
        self.calls = {"search": 0, "detail": 0, "order": 0}

    def _charge(self, kind):
        if self.spent + self.price[kind] > self.budget:
            raise BudgetExceeded(f"budget Rs {self.budget} reached after Rs {self.spent:.2f}")
        self.spent += self.price[kind]
        self.calls[kind] += 1

    def _get(self, path, params=None):
        url = BASE + path + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
        for attempt in range(4):
            req = urllib.request.Request(url, headers={"Authorization": "Bearer " + self.token, "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.load(r)
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 3:
                    time.sleep(float(e.headers.get("Retry-After", 2 ** (attempt + 1))))
                    continue
                raise
        self.n += 1
        if self.raw_dir:
            os.makedirs(self.raw_dir, exist_ok=True)
            with open(os.path.join(self.raw_dir, f"{self.n:03d}.json"), "w", encoding="utf-8") as f:
                json.dump({"url": url.replace(self.token, "***"), "data": data}, f, ensure_ascii=False)
        return data

    def search(self, params):
        self._charge("search")
        return self._get("/v2/search", params)

    def detail(self, cnr):
        self._charge("detail")
        return self._get("/case/" + urllib.parse.quote(cnr))


# ---------- the cascade ----------
def check_parcel(api, parcel, state_code=None, district_code=None, top_k=5, page_size=50):
    report = {"parcel": parcel.get("label"), "holders": [], "stopped": None}
    try:
        for h in parcel["holders"]:
            qs = english_queries(h["name"])
            params = {"litigants": qs, "nameMatchMode": "fuzzy", "pageSize": page_size}
            if state_code:
                params["stateCodes"] = state_code
            if district_code:
                params["districtCodes"] = district_code
            cases = find_cases(api.search(params))
            scored = []
            for c in cases:
                m = party_match(h, c)
                if m["name"] >= 0.7:
                    land = any(w in (str(c.get("caseType", "")) + " " + str(c.get("actsAndSections", ""))).lower() for w in LANDY)
                    scored.append((m["name"] + (m["father"] or 0) + (0.3 if land else 0), c, m, land))
            scored.sort(key=lambda x: -x[0])
            entry = {"holder": h["name"], "queries": qs, "hits": len(cases), "candidates": []}
            for _, c, m, land in scored[:top_k]:
                detail = api.detail(c["cnr"])
                scan = scan_text(" ".join(strings_under(detail, "markdownContent")), parcel)
                lv, why = level(m, scan)
                entry["candidates"].append({"cnr": c["cnr"], "case_type": c.get("caseType"), "status": c.get("caseStatus"),
                                            "land_like": land, "party": m["party"], "name_score": round(m["name"], 2),
                                            "father_score": None if m["father"] is None else round(m["father"], 2),
                                            "level": lv, "why": why, "scan": scan})
            report["holders"].append(entry)
    except BudgetExceeded as e:
        report["stopped"] = str(e)
    report["spent_rs"] = round(api.spent, 2)
    return report


class FakeApi:
    """Offline stand-in used by --selftest."""
    def __init__(self, cases, details):
        self.cases, self.details, self.spent, self.price, self.budget = cases, details, 0.0, PRICES["payg"], 1000
        self.calls = {"search": 0, "detail": 0, "order": 0}

    def search(self, params):
        self.spent += self.price["search"]
        self.calls["search"] += 1
        return {"data": {"results": self.cases}}

    def detail(self, cnr):
        self.spent += self.price["detail"]
        self.calls["detail"] += 1
        return {"courtCaseData": {"files": {"files": [{"markdownContent": self.details.get(cnr, "")}]}}}


def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok &= bool(cond)
    for a, l in [("মনোৱাৰ", "Manowar"), ("মনোৱাৰ", "Monwar"), ("হুছেইন", "Hossain"), ("হুছেইন", "Hussain"), ("ফজিৰ", "Fazir"),
                 ("আলী", "Ali"), ("আব্দুল", "Abdul"), ("শৰ্মা", "Sharma"), ("যতীন্দ্ৰ", "Jatindra"), ("নাথ", "Nath")]:
        check(f"skeleton {a} ~ {l}", skel_asm(a) == skel_lat(l))
    check("different names score low", set_score(tokens_asm("মনোৱাৰ হুছেইন"), tokens_lat("Rahim Ali")) < 0.5)
    check("english variants", "Fazir Ali" in english_queries("ফজিৰ আলী") or any("Ali" in q for q in english_queries("ফজিৰ আলী")))
    parcel = {"label": "t", "dags": ["781"], "patta": ["196"], "places_en": ["Kalitakuchi"],
              "holders": [{"name": "মনোৱাৰ হুছেইন", "father": "মকবুল হুছেইন"}]}
    cases = [{"cnr": "AAA", "caseType": "Title Suit", "petitioners": ["Manowar Hossain S/O Late Makbul Hussain"], "respondents": ["Rahim Ali"]},
             {"cnr": "BBB", "caseType": "Money Suit", "petitioners": ["Monowar Hussain S/O Chan Mohammad"], "respondents": ["State of Assam"]},
             {"cnr": "CCC", "caseType": "Civil Misc", "petitioners": ["Rahim Ali"], "respondents": ["Abdul Karim"]}]
    details = {"AAA": "Schedule: land covered by Dag No. 781 of Patta No. 196 at village Kalitakuchi, Hajo.",
               "BBB": "Suit for money. Land at village Kalita, dag no 12."}
    rep = check_parcel(FakeApi(cases, details), parcel)
    got = {c["cnr"]: c["level"] for c in rep["holders"][0]["candidates"]}
    check("case citing dag + village = level 3", got.get("AAA") == 3)
    check("same name, other father, no parcel text = level 1 or lower", got.get("BBB", 0) <= 1)
    check("unrelated parties are dropped", "CCC" not in got)
    check("assamese digits read", scan_text("দাগ নং ৭৮১ গাওঁ Kalitakuchi", parcel)["dag_hit"] == ["781"])
    api = Api("x", "payg", 2.0)
    api.spent = 1.9
    try:
        api._charge("search")
        check("budget cap stops spending", False)
    except BudgetExceeded:
        check("budget cap stops spending", True)
    print("ALL PASSED" if ok else "SOME FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("parcels", nargs="?")
    ap.add_argument("--budget", type=float, default=100.0, help="hard cap in rupees")
    ap.add_argument("--plan", choices=list(PRICES), default="payg")
    ap.add_argument("--state-code")
    ap.add_argument("--district-code")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--raw-dir", default="eci_raw")
    ap.add_argument("--out", default="parcel_case_report.json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    token = os.environ.get("ECI_TOKEN")
    if not token or not a.parcels:
        sys.exit("Set ECI_TOKEN and give a parcels.json (see SAMPLE in this file).")
    parcels = json.load(open(a.parcels, encoding="utf-8"))
    api = Api(token, a.plan, a.budget, a.raw_dir)
    reports = []
    for p in parcels:
        r = check_parcel(api, p, a.state_code, a.district_code, a.top_k)
        reports.append(r)
        if r["stopped"]:
            break
    json.dump({"reports": reports, "spent_rs": round(api.spent, 2), "calls": api.calls,
               "coverage_note": "Searched: eCourtsIndia case data only. Not searched: revenue courts, DRT unless supplied, pleadings, registry."},
              open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Done. Spent Rs {api.spent:.2f}. Calls: {api.calls}. Report: {a.out}")


if __name__ == "__main__":
    main()
