"""Builds the CRIMINAL-DOMAIN trap exam (register_exam/criminal/): questions about register cases that are actually in the criminal-law index (10,503 Supreme Court criminal judgments), because the
live site is a criminal-law tool and refuses most of the original 50 (tax, service, property). A row counts when both party names and the year (within one) match a title in the index; three more are
added by hand after reading the titles (EXTRA). Needs the index checkout (default /home/user/recourse-sci-index); the written files are committed, so running the exam does not need it.
    python site_patch/build_criminal_exam.py [--index DIR] [--out DIR] [--per-row 2]"""
import argparse, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, ROOT)
from goodlaw import register as R, register_exam as EX

EXTRA = {"L2-017": "Bikash Ranjan Rout v. State through the Secretary (Home), NCT of Delhi (16-04-2019)",
         "L2-018": "Randhir Singh Rana v. The State being the Delhi Administration (20/12/1996, reported 1997)",
         "L2-052": "Asian Resurfacing of Road Agency Pvt. Ltd. v. CBI (28-03-2018)"}


def rows_in_index(reg, index_dir):
    import pool_runner as PR, sci_index as si
    metas, _, _ = si._load_index(index_dir)
    title = PR.titles([index_dir], metas, None)
    def year_of(t):
        ys = re.findall(r"(?<!\d)(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.]((?:19|20)\d\d)(?!\d)", t or "")
        return int(ys[0]) if ys else None
    idx = {}
    for d in sorted({m["doc"] for m in metas}):
        t = title(d) or ""
        idx.setdefault(R.party_sigs(re.sub(r"\s*\(\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\)\s*$", "", t)), []).append((t, year_of(t)))
    out = []
    for r in reg.rows:
        o = r["overruled"]
        if r["trust"] == "rejected" or not o.get("year"):
            continue
        s = R.party_sigs(o["name"])
        if s[0] and s[1] and R.indexable(*s) and any(y and abs(y - o["year"]) <= 1 for _, y in idx.get(s, [])):
            out.append(r["id"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="/home/user/recourse-sci-index")
    ap.add_argument("--out", default=os.path.join(ROOT, "register_exam", "criminal"))
    ap.add_argument("--per-row", type=int, default=2)
    a = ap.parse_args(argv)
    reg = R.Register.load()
    ids = rows_in_index(reg, a.index)
    ids += [i for i in EXTRA if i not in ids]
    qs, key = EX.build_exam_rows(reg, ids, a.per_row)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "questions.jsonl"), "w", encoding="utf-8") as f:
        for q in qs:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    json.dump(key, open(os.path.join(a.out, "key.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"rows_in_index_by_name_and_year": [i for i in ids if i not in EXTRA], "added_by_hand_after_reading_titles": EXTRA}, open(os.path.join(a.out, "how_chosen.json"), "w"), indent=1)
    print(f"{len(qs)} questions from {len({k['row_id'] for k in key.values()})} register rows -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
