"""
measure.py -- runs the frozen matter-files measurement (frozen_questions.json, quote_cases.json, both committed in 3cbce34 before any matter-files code existed) against Recourse's matter_files.py.
M1 extraction, M2 retrieval (words / meaning / hybrid; meaning needs VOYAGE_API_KEY, never printed), M2b scores of the absent questions, M3 quote cases, M4 the documents block's fencing, M5 that matter B's passages never reach
matter A's search (here: search() is called with matter A's rows only, as the API does; the API test proves the database side). Writes results.json next to this file.
Run: python3 -I measure.py /home/user/recourse
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/user/recourse")
sys.path.insert(0, REC)
import matter_files as MF  # noqa: E402

FQ = json.load(open(os.path.join(HERE, "frozen_questions.json")))
QC = json.load(open(os.path.join(HERE, "quote_cases.json")))


def path_of(p):
    return os.path.join(REC, p.split(":", 1)[1]) if p.startswith("RECOURSE:") else os.path.join(HERE, p)


def load(key, p):
    data = open(path_of(p), "rb").read()
    kind = MF.sniff(data, os.path.basename(path_of(p)))
    ex = MF.extract(data, kind)
    return {"key": key, "name": os.path.basename(path_of(p)), "kind": kind, "ex": ex, "passages": MF.passages(ex)}


def embed(texts, input_type):
    import voyageai
    c = voyageai.Client()
    out = []
    for i in range(0, len(texts), 64):
        out.extend(c.embed(texts[i:i + 64], model="voyage-law-2", input_type=input_type).embeddings)
    return out


def main():
    res = {}
    # ---------------- M1
    m1 = {}
    files = {}
    for group in ("matter_A_files", "matter_B_files", "extraction_only"):
        for key, p in FQ[group].items():
            try:
                f = load(key, p)
                files[key] = f
                m1[key] = {"kind": f["kind"], "unit": f["ex"]["unit"], "count": f["ex"]["count"], "unread": f["ex"]["unread"], "passages": len(f["passages"]), "chars": sum(len(u["text"]) for u in f["ex"]["units"])}
            except MF.Refused as e:
                m1[key] = {"refused": e.code}
    res["M1"] = m1
    # ---------------- M3 (quote cases)
    docmap = QC["docs"]
    qdocs = {no: {"unit": files[k]["ex"]["unit"], "units": {u["loc"]: u["text"] for u in files[k]["ex"]["units"]}} for no, k in docmap.items()}
    m3 = []
    for c in QC["cases"]:
        got = MF.check_quotes(c["text"], qdocs)
        g = [[r["verdict"]] + ([r["found_on"]] if r["verdict"] == "other_page" else [r["found_doc"], r["found_on"]] if r["verdict"] == "other_doc" else []) for r in got]
        m3.append({"id": c["id"], "expect": c["expect"], "got": g, "pass": g == c["expect"]})
    res["M3"] = {"passed": sum(x["pass"] for x in m3), "total": len(m3), "cases": m3}
    # ---------------- M2 retrieval
    a_keys = list(FQ["matter_A_files"])
    doc_no = {k: i + 1 for i, k in enumerate(a_keys)}
    rows = []
    for k in a_keys:
        for p in files[k]["passages"]:
            rows.append({"doc": doc_no[k], "key": k, "loc": p["loc"], "loc_to": p["loc_to"], "text": p["text"], "vec": None})
    b_rows = [{"doc": 1, "key": "JOR", "loc": p["loc"], "loc_to": p["loc_to"], "text": p["text"], "vec": None} for p in files["JOR"]["passages"]]
    have_voyage = bool(os.environ.get("VOYAGE_API_KEY"))
    qvecs = {}
    if have_voyage:
        vecs = embed([r["text"] for r in rows], "document")
        for r, v in zip(rows, vecs):
            r["vec"] = v
        qs = [q["q"] for q in FQ["questions"]]
        qvecs = dict(zip([q["id"] for q in FQ["questions"]], embed(qs, "query")))
    modes = ["words"] + (["meaning", "hybrid"] if have_voyage else [])
    m2 = {}
    for mode in modes:
        per = []
        for q in FQ["questions"]:
            got = MF.search(q["q"], rows, qvec=qvecs.get(q["id"]), mode=mode)
            locs = [(r["key"], loc) for r in got for loc in range(r["loc"], r["loc_to"] + 1)]
            hit = any(tuple(g) in locs for g in q["gold"]) if q["gold"] else None
            first = next((r["rank"] for r in got if any(g[0] == r["key"] and r["loc"] <= g[1] <= r["loc_to"] for g in q["gold"])), None) if q["gold"] else None
            top = max([r["score_kw"] for r in got] or [0]) if mode == "words" else max([(r["score_vec"] or 0) for r in got] or [0])
            per.append({"id": q["id"], "hit": hit, "rank": first, "handed": [f"{r['key']}:{r['loc']}" + (f"-{r['loc_to']}" if r["loc_to"] != r["loc"] else "") for r in got], "top_score": top,
                        "chars": sum(len(r["text"]) for r in got)})
        answerable = [p for p in per if p["hit"] is not None]
        m2[mode] = {"hits": sum(1 for p in answerable if p["hit"]), "of": len(answerable), "misses": [p["id"] for p in answerable if not p["hit"]],
                    "absent_top_scores": {p["id"]: p["top_score"] for p in per if p["id"] in (40, 41, 42)},
                    "answerable_top_score_min": min(p["top_score"] for p in answerable), "per": per}
    res["M2"] = m2
    res["M2_handover"] = {"k": MF.HANDOVER, "max_chars": MF.HANDOVER_CHARS, "passage_chars": MF.PASSAGE_CHARS, "voyage": have_voyage, "rows_in_matter_A": len(rows)}
    # ---------------- M5 (the search is given matter A's rows only; nothing of matter B can come back)
    q43 = next(q for q in FQ["questions"] if q["id"] == 43)
    got = MF.search(q43["q"], rows, qvec=qvecs.get(43), mode="hybrid" if have_voyage else "words")
    res["M5"] = {"q43_handed": [f"{r['key']}:{r['loc']}" for r in got], "matter_B_in_result": any(r["key"] == "JOR" for r in got),
                 "matter_B_would_rank_first_if_mixed": (MF.search(q43["q"], rows + b_rows, mode="words") or [{}])[0].get("key") == "JOR"}
    # ---------------- M4 (fencing)
    inj = files["INJ"]
    chosen = [{"doc": doc_no["INJ"], "loc": p["loc"], "loc_to": p["loc_to"], "text": p["text"]} for p in inj["passages"]]
    block = MF.documents_block({doc_no["INJ"]: {"name": inj["name"], "unit": "page", "unread": inj["ex"]["unread"]}}, chosen)
    lines = block.split("\n")
    doc_lines = [ln for ln in lines if ln.startswith("| ")]
    ours = [ln for ln in lines if ln and not ln.startswith("| ")]
    res["M4"] = {"planted_text_only_on_fenced_lines": all(("Ignore all previous" not in ln and "END OF DOCUMENTS" not in ln and "Hard rules" not in ln) for ln in ours),
                 "planted_text_present_fenced": any("Ignore all previous" in ln for ln in doc_lines),
                 "fake_citation_neutralised": "[Doc" not in "\n".join(doc_lines), "block_ends_once": sum(1 for ln in ours if "END OF THE PERSON'S DOCUMENTS" in ln) == 1, "end_marker_inside_documents_neutralised": "END OF THE PERSON'S DOCUMENTS" not in "\n".join(doc_lines),
                 "unread_page_listed": "not read: 3" in block, "model_behaviour": "NOT TESTED (no Anthropic key in the sandbox)"}
    json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1)
    print(json.dumps({"M1": {k: (v.get("refused") or (v["count"], v["unread"], v["passages"])) for k, v in m1.items()}, "M3": f"{res['M3']['passed']}/{res['M3']['total']}",
                      "M2": {m: f"{v['hits']}/{v['of']} misses={v['misses']}" for m, v in m2.items()}, "M5": res["M5"], "M4": res["M4"]}, indent=1))
    for c in m3:
        if not c["pass"]:
            print("M3 FAIL", c)


if __name__ == "__main__":
    main()
