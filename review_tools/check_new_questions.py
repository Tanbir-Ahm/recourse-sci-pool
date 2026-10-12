"""Recounts the rules for the new test questions (review_data/ruler/question_rules/New_Test_Questions_Rules_and_Guidelines.docx, sections 2, 4, 5, 9, 10, 11) on the writer's workbook.
Nothing is searched, no service is called, nothing is spent. Reads the workbook only.

    python review_tools/check_new_questions.py WORKBOOK.xlsx [--json OUT.json] [--drop N12,...]

Returns a list of checks {id, rule, ok, detail}; exit code 0 only if every check passes. A failed check is a finding for the writer, not a verdict on the question set. Index coverage, duplicates and the
trigger check need the index and are in review_results/2026-10-12_new_questions_intake/.

--drop: scored questions removed before sealing (question rules section 11: a failed question is replaced from the reserves or rewritten once; fewer than 24 usable questions cancels the test). The recount is then made on the set
without them: the id and domain counts follow, every other threshold is unchanged, and check U1 says which ids were dropped and that at least 24 usable questions remain. Controls cannot be dropped."""
import argparse
import collections
import json
import re
import sys

import openpyxl

Q_COLS = ["Id", "Domain (A to K)", "Question text", "Phr (E/L/N)", "Hinglish (Y/N)", "Sec (NEW/OLD/NONE)", "CT (Y/N)", "Era 2017+ (Y/N)", "Control type (K1/K2/K3, domain K only)",
          'Act(s) concerned (from the 13, or "none")', "Act, section or acronym named in the question text (Y/N)", "Look-alike (Y/N)", "Neighbour regime", "Twin of (Id or blank)", "Reserve for domain (reserves only)"]
K_COLS = ["Id", "Expected answer", "Primary authority", "Other acceptable authorities", "Older ruling a search may wrongly show (traps) with what changed and the current authority", "Code that applies and why", "Source URLs", "How verified", "Conf", "To verify"]
DOMAINS = {"A": 3, "B": 3, "C": 3, "D": 2, "E": 3, "F": 3, "G": 3, "H": 3, "I": 2, "J": 2, "K": 3}
USABLE_FLOOR = 24                 # question rules section 11: below this the test is cancelled
ACTS = {"PWDVA": "PWDVA", "NDPS Act": "NDPS", "POCSO Act": "POCSO", "SC/ST Act": "SC/ST", "NI Act": "NI Act", "PMLA": "PMLA", "UAPA": "UAPA", "Dowry Prohibition Act": "DPA", "JJ Act": "JJ Act",
        "PC Act": "PC Act", "Arms Act": "Arms Act", "IT Act": "IT Act", "MV Act": "MV Act"}
WORD_LIMITS = {"E": (None, 60), "L": (None, 50), "N": (None, 120)}
NEW_CODE = re.compile(r"(?:\d+[A-Za-z]?(?:\s*\([^)]*\))*\s*(?:of\s+(?:the\s+)?)?(?:BNSS|BNS|BSA)\b)|(?:\b(?:BNSS|BNS|BSA)\b\W{0,12}(?:section\s*)?\d+)|(?:(?:section|sec\.?|s\.)\s*\d+[A-Za-z]?(?:\s*\([^)]*\))*\s*(?:of\s+(?:the\s+)?)?(?:Bharatiya))", re.I)
OLD_CODE = re.compile(r"(?:\d+[A-Za-z]?(?:\s*\([^)]*\))*(?:\s+Part\s+[IV]+)?\s*(?:of\s+(?:the\s+)?)?(?:IPC|Cr\.?\s?P\.?\s?C\.?|Indian Penal Code|Evidence Act|CrPC)\b)|(?:\b(?:IPC|Cr\.?\s?P\.?\s?C\.?|CrPC)\W{0,12}(?:section\s*)?\d+)|(?:(?:Section|Sec\.?|s\.)\s*\d+[A-Za-z]?(?:\s*\([^)]*\))*\s+of\s+the\s+(?:Evidence Act|Code of Criminal Procedure|Indian Penal Code))", re.I)
CASE_NAME = re.compile(r"\bv\.\s|\bvs\.?\s|\bversus\b|\bIn re\b|\bCrl\.?\s?(?:A|Appeal)\b|\bSLP\b|\bW\.?P\.?\s?\(", re.I)
PHONE_MAIL = re.compile(r"\b\d{10}\b|[\w.]+@[\w.]+\.\w+")


def read(path):
    wb = openpyxl.load_workbook(path)
    out = {}
    for name, cols in (("Questions", Q_COLS), ("Key", K_COLS)):
        if name not in wb.sheetnames:
            out[name] = None
            continue
        rows = list(wb[name].iter_rows(values_only=True))
        hdr = [str(c) if c is not None else "" for c in rows[0]]
        out[name] = {"header": hdr, "rows": [dict(zip(hdr, r)) for r in rows[1:] if any(c is not None and str(c).strip() for c in r)]}
    out["Declaration"] = None
    if "Declaration" in wb.sheetnames:
        out["Declaration"] = [(str(a or ""), str(b or "")) for a, b in list(wb["Declaration"].iter_rows(values_only=True))[1:]]
    out["sheetnames"] = wb.sheetnames
    return out


def tags_of(cell):
    t = (cell or "").strip()
    if not t or t.lower() == "none":
        return set()
    return {ACTS.get(x.strip(), x.strip()) for x in re.split(r"[;+,]", t) if x.strip()}


def words(t):
    return len(re.findall(r"\S+", t or ""))


def sentences(t):
    return len([s for s in re.split(r"(?<=[.?!])\s+", (t or "").strip()) if s])


def code_tag(text):
    new, old = bool(NEW_CODE.search(text)), bool(OLD_CODE.search(text))
    return "MIXED" if new and old else "NEW" if new else "OLD" if old else "NONE"


def check(data, drop=()):
    res = []
    drop = tuple(sorted(set(drop or ())))

    def add(cid, rule, ok, detail=""):
        res.append({"id": cid, "rule": rule, "ok": bool(ok), "detail": detail})

    for s in ("Questions", "Key", "Declaration"):
        add("F1", f"sheet '{s}' present", s in data["sheetnames"])
    if data["Questions"] is None or data["Key"] is None:
        return res
    qh, kh = data["Questions"]["header"], data["Key"]["header"]
    add("F2", "Questions columns exactly as in the rules (section 11.1)", qh == Q_COLS, f"missing {[c for c in Q_COLS if c not in qh]}, extra {[c for c in qh if c not in Q_COLS]}")
    add("F3", "Key columns exactly as in the rules (section 11.1)", kh == K_COLS, f"missing {[c for c in K_COLS if c not in kh]}, extra {[c for c in kh if c not in K_COLS]}")
    if qh != Q_COLS or kh != K_COLS:
        return res                       # the other checks read the columns by their exact names
    kept_all = {r["Id"]: r for r in data["Questions"]["rows"]}                  # as received, dropped rows included
    if drop:
        data = dict(data, Questions=dict(data["Questions"], rows=[r for r in data["Questions"]["rows"] if r["Id"] not in drop]), Key=dict(data["Key"], rows=[r for r in data["Key"]["rows"] if r["Id"] not in drop]))
    Q = {r["Id"]: r for r in data["Questions"]["rows"]}
    K = {r["Id"]: r for r in data["Key"]["rows"]}
    main = [f"N{i:02d}" for i in range(1, 31) if f"N{i:02d}" not in drop]
    res_ids = sorted(i for i in Q if str(i).startswith("NR"))
    plan = dict(DOMAINS)
    for i in drop:
        if i in kept_all and kept_all[i]["Domain (A to K)"] in plan:
            plan[kept_all[i]["Domain (A to K)"]] -= 1
    n_scored_plan = 27 - sum(1 for i in drop if i in kept_all and kept_all[i]["Domain (A to K)"] not in ("K", None))
    if drop:
        bad_drop = [i for i in drop if i not in kept_all or not re.fullmatch(r"N(0[1-9]|[12]\d|30)", i) or kept_all[i]["Domain (A to K)"] == "K"]
        add("U1", f"dropped before sealing: only scored questions, and at least {USABLE_FLOOR} usable questions remain (question rules section 11)", not bad_drop and 30 - len(drop) >= USABLE_FLOOR,
            f"dropped {list(drop)}; {30 - len(drop)} usable of 30" + (f"; not droppable or unknown: {bad_drop}" if bad_drop else ""))
    add("F4", "ids N01 to N30 each once, in order; reserves NR1 to NR3 at most", [r["Id"] for r in data["Questions"]["rows"] if not str(r["Id"]).startswith("NR")] == main and len(res_ids) <= 3 and all(re.fullmatch(r"NR[1-3]", i) for i in res_ids), f"reserves {res_ids}")
    add("F5", "every question has a key row and every key row a question", set(Q) == set(K), f"questions without key {sorted(set(Q) - set(K))}, keys without question {sorted(set(K) - set(Q))}")
    scored = [Q[i] for i in main if i in Q and Q[i]["Domain (A to K)"] != "K"]
    controls = [Q[i] for i in main if i in Q and Q[i]["Domain (A to K)"] == "K"]
    dom = collections.Counter(Q[i]["Domain (A to K)"] for i in main if i in Q)
    add("R1", "domain counts A3 B3 C3 D2 E3 F3 G3 H3 I2 J2 K3 (27 scored + 3 controls)", dict(dom) == plan and len(scored) == n_scored_plan and len(controls) == 3, f"found {dict(sorted(dom.items()))}" + (f"; plan after dropping {list(drop)}: {dict(sorted(plan.items()))}" if drop else ""))
    ct = sorted(str(r["Control type (K1/K2/K3, domain K only)"]) for r in controls)
    add("R2", "controls: exactly one each of K1, K2, K3", ct == ["K1", "K2", "K3"], str(ct))
    ph = collections.Counter(r["Phr (E/L/N)"] for r in scored)
    add("R3", "phrasing among the 27: at least 6 each of E, L, N", all(ph[x] >= 6 for x in "ELN") and sum(ph.values()) == n_scored_plan, f"E {ph['E']}, L {ph['L']}, N {ph['N']}" + (f" ({n_scored_plan} scored after dropping {list(drop)})" if drop else ""))
    hing = [r["Id"] for r in data["Questions"]["rows"] if r["Hinglish (Y/N)"] == "Y"]
    add("R4", "Hinglish 0 to 3 (counted as everyday)", len(hing) <= 3 and all(Q[i]["Phr (E/L/N)"] == "E" for i in hing), str(hing))
    sec = collections.Counter(r["Sec (NEW/OLD/NONE)"] for r in scored)
    add("R5", "code tags among the 27: NEW at least 6, OLD at least 6, NONE at least 8", sec["NEW"] >= 6 and sec["OLD"] >= 6 and sec["NONE"] >= 8, f"NEW {sec['NEW']}, OLD {sec['OLD']}, NONE {sec['NONE']}")
    wrong = [(r["Id"], r["Sec (NEW/OLD/NONE)"], code_tag(r["Question text"])) for r in data["Questions"]["rows"] if code_tag(r["Question text"]) != r["Sec (NEW/OLD/NONE)"]]
    add("R5b", "the code tag agrees with the numbers actually written in the question text", not wrong, f"tag given vs read from text: {wrong}")
    traps = [r["Id"] for r in scored if r["CT (Y/N)"] == "Y"]
    add("R6", "currency traps among the 27: at least 4 (target 6)", len(traps) >= 4, f"{len(traps)}: {traps}")
    era = [r["Id"] for r in scored if r["Era 2017+ (Y/N)"] == "Y"]
    add("R7", "best law from 2017 or later: at least 10 of the 27", len(era) >= 10, f"{len(era)}")
    tg = {r["Id"]: tags_of(r['Act(s) concerned (from the 13, or "none")']) for r in data["Questions"]["rows"]}
    unknown = sorted({a for t in tg.values() for a in t} - set(ACTS.values()))
    add("R8a", "every Act tag is one of the 13 listed Acts or 'none'", not unknown, str(unknown))
    actq = [r["Id"] for r in scored if tg[r["Id"]]]
    covered = collections.Counter(a for r in scored for a in tg[r["Id"]])
    add("R8b", "Act-concerning questions: at least 14 of the 27", len(actq) >= 14, f"{len(actq)}")
    add("R8c", "at least 10 of the 13 Acts covered", len(covered) >= 10, f"{len(covered)} covered; missing {sorted(set(ACTS.values()) - set(covered))}")
    add("R8d", "NDPS, NI Act, PWDVA and POCSO at least 2 each", all(covered[a] >= 2 for a in ("NDPS", "NI Act", "PWDVA", "POCSO")), str({a: covered[a] for a in ("NDPS", "NI Act", "PWDVA", "POCSO")}))
    gen = [r["Id"] for r in scored if not tg[r["Id"]]]
    add("R9", "general criminal-law questions (no listed Act): at least 8", len(gen) >= 8, f"{len(gen)}")
    la = [r["Id"] for r in scored if r["Look-alike (Y/N)"] == "Y"]
    add("R10a", "look-alikes: at least 8 (target 10)", len(la) >= 8, f"{len(la)}")
    la_un = [i for i in la if tg[i] and Q[i]["Act, section or acronym named in the question text (Y/N)"] == "N"]
    add("R10b", "look-alikes under a listed Act that do not name it: at least 3 (target 5)", len(la_un) >= 3, f"{len(la_un)}: {la_un}")
    add("R10c", "every look-alike names its neighbour regime", all((Q[i]["Neighbour regime"] or "").strip() for i in la), str([i for i in la if not (Q[i]["Neighbour regime"] or "").strip()]))
    pairs = {tuple(sorted((r["Id"], r["Twin of (Id or blank)"]))) for r in data["Questions"]["rows"] if r["Twin of (Id or blank)"]}
    cross = all(Q.get(Q[i]["Twin of (Id or blank)"], {}).get("Twin of (Id or blank)") == i for i in Q if Q[i]["Twin of (Id or blank)"])
    add("R11", "twin pairs: at least 2, cross-referenced both ways", len(pairs) >= 2 and cross, f"{sorted(pairs)}")
    add("R12", "reserves marked with the domain they can replace", all(Q[i]["Reserve for domain (reserves only)"] in DOMAINS for i in res_ids), str([(i, Q[i]["Reserve for domain (reserves only)"]) for i in res_ids]))
    # section 9: style, privacy
    long_ = []
    for r in data["Questions"]["rows"]:
        lim = WORD_LIMITS.get(r["Phr (E/L/N)"])
        if lim and words(r["Question text"]) > lim[1] * 1.0:
            long_.append((r["Id"], r["Phr (E/L/N)"], words(r["Question text"]), lim[1]))
    add("S1", "length by style: everyday up to about 60 words, legal up to about 50, narrative up to about 120", not long_, f"over the limit (id, style, words, limit): {long_}")
    bad_n = [(r["Id"], sentences(r["Question text"])) for r in data["Questions"]["rows"] if r["Phr (E/L/N)"] == "N" and not 4 <= sentences(r["Question text"]) <= 8]
    add("S2", "narrative questions have four to eight sentences", not bad_n, str(bad_n))
    names = [r["Id"] for r in data["Questions"]["rows"] if CASE_NAME.search(r["Question text"] or "") or PHONE_MAIL.search(r["Question text"] or "")]
    add("S3", "no case name, case number, phone number or e-mail in a question", not names, str(names))
    # section 10: key
    nok = [i for i in Q if not all(str(K.get(i, {}).get(c) or "").strip() for c in K_COLS)]
    add("K1", "no empty cell in the key", not nok, f"rows with an empty cell: {nok}")
    conf_bad = [i for i, k in K.items() if str(k.get("Conf")) not in ("C", "L", "G")]
    add("K2", "Conf is C, L or G", not conf_bad, str(conf_bad))
    sec_only = [i for i, k in K.items() if re.search(r"secondary (?:source|sources|reports?)?\s*only|secondary only|through secondary", str(k.get("How verified") or ""), re.I) and not re.search(r"read judgment text|read an official", str(k.get("How verified") or ""), re.I) and k.get("Conf") != "G"]
    add("K3", "'secondary source only' forces Conf = G (rules section 10)", not sec_only, f"secondary-only but not G: {sec_only}")
    trapkeys = {"OLDER RULING": 0, "CHANGE": 0, "WHAT CHANGED": 0, "CURRENT AUTHORITY": 0}
    short = []
    for r in scored:
        if r["CT (Y/N)"] == "Y":
            t = str(K.get(r["Id"], {}).get("Older ruling a search may wrongly show (traps) with what changed and the current authority") or "")
            if not all(k in t for k in trapkeys):
                short.append(r["Id"])
    add("K4", "each currency trap states the older ruling, the change, what changed and the current authority (section 7)", not short, str(short))
    noacc = [i for i, k in K.items() if re.match(r"\s*(?:none|n/a)", str(k.get("Other acceptable authorities") or ""), re.I) and not str(Q[i]["Domain (A to K)"]) == "K" and not str(i).startswith("NR3")]
    add("K5", "every scored key lists other acceptable authorities (at least two where they exist); 'none' is listed for review", not noacc, f"'none' for: {noacc}")
    late = [i for i, k in K.items() if re.search(r"\b(?:Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+2026", str(k.get("Primary authority") or "")) and Q[i]["Domain (A to K)"] != "K"]
    add("K6", "primary authority decided on or before 30 June 2026", not late, str(late))
    # declaration
    dec = " ".join(a + " " + b for a, b in (data["Declaration"] or []))
    add("D1", "declaration names any AI tool used and for what (rules section 3 and 11.1)", bool(re.search(r"AI tool|ChatGPT|Gemini|Claude|assistant|language model|LLM", dec, re.I)) and bool(re.search(r"AI tools? used", dec, re.I)), "no 'AI tools used and for what' line" if not re.search(r"AI tools? used", dec, re.I) else "")
    seen_list = [b for a, b in (data["Declaration"] or []) if "trigger-word list" in a.lower() and "additional" not in a.lower()]
    add("D2", "declaration: the writer has not seen the trigger-word list (rules section 3: do NOT consult it while writing)", bool(seen_list) and not seen_list[0].strip().upper().startswith("Y"), f"declared: {seen_list[0][:90] if seen_list else 'no such line'}")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("workbook")
    ap.add_argument("--json")
    ap.add_argument("--drop", default="", help="comma-separated ids dropped before sealing (scored questions only)")
    a = ap.parse_args(argv)
    res = check(read(a.workbook), [x.strip() for x in a.drop.split(",") if x.strip()])
    for r in res:
        print(("PASS " if r["ok"] else "FAIL ") + f"{r['id']:5} {r['rule']}" + ("" if r["ok"] else f"  [{r['detail']}]"))
        if r["ok"] and r["detail"]:
            print(f"             {r['detail']}")
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), indent=1)
    bad = [r for r in res if not r["ok"]]
    print(f"\n{len(res) - len(bad)} of {len(res)} checks pass; {len(bad)} fail")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
