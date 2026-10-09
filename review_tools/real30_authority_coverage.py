"""Which of the authorities named in the owner's 30-question file (received 2026-10-09) can a search over the index reach at all?

    python review_tools/real30_authority_coverage.py [--corpus corpus.sqlite] [--index-dir ../recourse-sci-index] [--out review_results/2026-10-09_real30_file_review/authority_coverage.json]

Each authority is looked up by party names (letters and digits only) and year in the corpus store, then in the index: IN INDEX (embedded), FILTERED OUT (in the collection, left out of the index
by its criminal-law filter) or NOT IN COLLECTION. Names only: nothing is searched, nothing is spent. The table of authorities was read off the owner's file by hand; `role` says why it is
named: key (the ruling that answers the question), stale (the older ruling the file calls the trap), control (a control question's authority) or extra (added here, not in the file).
PRIVATE, like the rest of review_data/ and review_results/."""
import argparse
import glob
import gzip
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DEFAULT_INDEX = os.path.normpath(os.path.join(ROOT, "..", "recourse-sci-index"))
DEFAULT_OUT = os.path.join(ROOT, "review_results", "2026-10-09_real30_file_review", "authority_coverage.json")

# (question, role, label, tokens that must all be inside the normalised title, year or None, years of slack)
AUTHORITIES = [
    ("Q1", "key", "Mihir Rajesh Shah v. State of Maharashtra (2025)", ["mihirrajeshshah"], 2025, 0),
    ("Q1", "stale", "Pankaj Bansal v. Union of India (2023)", ["pankajbansal", "unionofindia"], 2023, 0),
    ("Q1", "stale", "Prabir Purkayastha v. State (NCT of Delhi) (2024)", ["prabirpurkayastha"], 2024, 0),
    ("Q1", "stale", "Vihaan Kumar v. State of Haryana (2025)", ["vihaankumar"], 2025, 0),
    ("Q2", "key", "Satender Kumar Antil v. CBI (2025, notice by WhatsApp)", ["satenderkumarantil"], 2025, 0),
    ("Q2", "key", "Satender Kumar Antil v. CBI (2022)", ["satenderkumarantil"], 2022, 0),
    ("Q2", "key", "Arnesh Kumar v. State of Bihar (2014)", ["arneshkumar", "bihar"], 2014, 0),
    ("Q3", "key", "D.K. Basu v. State of West Bengal (1996/97)", ["dkbasu"], 1996, 1),
    ("Q4", "stale", "Salauddin Abdulsamad Shaikh v. State of Maharashtra (1995/96)", ["salauddinabdulsamadshaikh"], 1995, 1),
    ("Q4", "key", "Sushila Aggarwal v. State (NCT of Delhi) (2020)", ["sushilaaggarwal"], 2020, 0),
    ("Q5", "stale", "Ritu Chhabaria v. Union of India (2023)", ["rituchhabaria"], 2023, 0),
    ("Q5", "key", "CBI v. Kapil Wadhawan (2024)", ["kapilwadhawan", "centralbureau"], 2024, 0),
    ("Q5", "key", "Shaurya Sunil Kumar Singh v. CBI (2026)", ["shauryasunilkumarsingh"], 2026, 0),
    ("Q6", "key", "In Re: Inhuman Conditions in 1382 Prisons (the order of 23 Aug 2024; the collection holds only the 14 May 2024 one)", ["inhumanconditions"], 2024, 0),
    ("Q7", "stale", "Damodar S. Prabhu v. Sayed Babalal H. (2010)", ["damodarsprabhu"], 2010, 0),
    ("Q7", "key", "Sanjabij Tari v. Kishore S. Borcar (2025)", ["sanjabijtari"], 2025, 0),
    ("Q8", "key", "Rakesh Ranjan Shrivastava v. State of Jharkhand (2024)", ["rakeshranjanshrivastava"], 2024, 0),
    ("Q9", "stale", "Dashrath Rupsingh Rathod v. State of Maharashtra (2014)", ["dashrathrupsingh"], 2014, 0),
    ("Q9", "key", "Bridgestone India v. Inderpal Singh (2015)", ["bridgestone", "inderpal"], 2015, 0),
    ("Q10", "stale", "Mohan Lal v. State of Punjab (2018)", ["mohanlal", "punjab"], 2018, 0),
    ("Q10", "key", "Mukesh Singh v. State (Narcotic Branch of Delhi) (2020)", ["mukeshsingh", "narcotic"], 2020, 0),
    ("Q11", "stale", "Kanhaiyalal v. Union of India (2008)", ["kanhaiyalal", "unionofindia"], 2008, 0),
    ("Q11", "stale", "Raj Kumar Karwal v. Union of India (1990)", ["rajkumarkarwal"], 1990, 0),
    ("Q11", "key", "Tofan Singh v. State of Tamil Nadu (2020)", ["tofansingh"], 2020, 0),
    ("Q12", "key", "Rikhab Birani v. State of U.P. (2025)", ["rikhabbirani"], 2025, 0),
    ("Q13", "key", "Parbatbhai Aahir v. State of Gujarat (2017)", ["parbatbhaiaahir"], 2017, 0),
    ("Q13", "key", "State of Haryana v. Bhajan Lal (1990/92)", ["bhajanlal", "haryana"], 1990, 2),
    ("Q14", "key", "Indian Oil Corp. v. NEPC India (2006)", ["nepcindia"], 2006, 0),
    ("Q15", "stale", "Rajesh Sharma v. State of U.P. (2017)", ["rajeshsharma", "stateofup"], 2017, 0),
    ("Q15", "stale", "Social Action Forum for Manav Adhikar v. Union of India (2018)", ["socialactionforum"], 2018, 0),
    ("Q15", "key", "Shivangi Bansal v. Sahib Bansal (2025)", ["shivangibansal"], 2025, 0),
    ("Q16", "key", "Kamatchi v. Lakshmi Narayanan (2022)", ["kamatchi", "lakshminarayanan"], 2022, 0),
    ("Q17", "key", "Ude Singh v. State of Haryana (2019)", ["udesingh"], 2019, 0),
    ("Q17", "key", "Kumar @ Shiva Kumar v. State of Karnataka (2024)", ["kumarshivakumar", "karnataka"], 2024, 0),
    ("Q18", "key", "Attorney General for India v. Satish (2021)", ["attorneygeneralforindia", "satish"], 2021, 0),
    ("Q19", "key", "Ramji Lal Bairwa v. State of Rajasthan (2024)", ["ramjilalbairwa"], 2024, 0),
    ("Q20", "key", "Pramod Suryabhan Pawar v. State of Maharashtra (2019)", ["pramodsuryabhanpawar"], 2019, 0),
    ("Q21", "stale", "Shafhi Mohammad v. State of H.P. (2018)", ["shafhimohammad"], 2018, 0),
    ("Q21", "key", "Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal (2020)", ["arjunpanditrao"], 2020, 0),
    ("Q22", "key", "Bachan Singh v. State of Punjab (1980)", ["bachansingh", "punjab"], 1979, 1),
    ("Q22", "key", "Manoj v. State of M.P. (2022)", ["manoj", "madhyapradesh"], 2022, 0),
    ("Q23", "key", "Pulicherla Nagaraju v. State of A.P. (2006)", ["pulicherlanagaraju"], 2006, 0),
    ("Q24", "stale", "Vijay Madanlal Choudhary v. Union of India (2022)", ["vijaymadanlalchoudhary"], 2022, 0),
    ("Q24", "key", "Tarsem Lal v. Directorate of Enforcement (2024)", ["tarsemlal", "directorateofenforcement"], 2024, 0),
    ("Q25", "stale", "Subhash Kashinath Mahajan v. State of Maharashtra (2018)", ["subhashkashinathmahajan"], 2018, 0),
    ("Q25", "key", "Union of India v. State of Maharashtra (review order of 1 Oct 2019)", ["unionofindia", "stateofmaharashtra"], 2019, 0),
    ("Q25", "key", "Prathvi Raj Chauhan v. Union of India (2020)", ["prathvirajchauhan"], 2020, 0),
    ("Q26", "key", "Omprakash Sahni v. Jai Shankar Chaudhary (2023)", ["omprakashsahni"], 2023, 0),
    ("Q26", "key", "Bhagwan Rama Shinde Gosai v. State of Gujarat (1999)", ["shindegosai"], 1999, 1),
    ("Q27", "stale", "Sangeet v. State of Haryana (2012)", ["sangeet", "stateofharyana"], 2012, 1),
    ("Q27", "key", "In Re: Policy Strategy for Grant of Bail (2025)", ["policystrategyforgrantofbail"], 2025, 0),
    ("Q28", "control", "Amardeep Singh v. Harveen Kaur (2017)", ["amardeepsingh", "harveenkaur"], 2017, 0),
    ("Q28", "control", "Shilpa Sailesh v. Varun Sreenivasan (2023)", ["shilpasailesh"], 2023, 0),
    ("Q29", "control", "State of A.P. v. Suda Suresh Veera Venkata Naga Raju (2026)", ["sudasuresh"], 2026, 0),
    ("Q29", "extra", "Poolpandi v. Superintendent, Central Excise (1992): the older law on a lawyer at interrogation", ["poolpandi"], 1992, 0),
]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def index_status(index_dir, rows):
    """{doc_key: 'in_index' | 'not_criminal' | other skip reason} from the index's own document records."""
    seen, bypath = {}, {}
    for f in glob.glob(os.path.join(index_dir, "index", "*.docs.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                seen[r["doc"]] = r.get("skip") or ("in_index" if r.get("passages", 0) > 0 else "no_passage")
                if isinstance(r.get("src"), dict) and r["src"].get("path"):
                    bypath[r["src"]["path"]] = r["doc"]
    out = {}
    for key, source, sid, bucket_path in rows:
        d = int(sid) if source == "crawl" else bypath.get(bucket_path)
        if d is not None:
            out[key] = (d, seen.get(d, "unknown"))
    return out


def run(corpus, index_dir):
    con = sqlite3.connect(corpus)
    docs = list(con.execute("select doc_key, source, src_id, bucket_path, title, pet, resp, date, year, insc from docs"))
    status = index_status(index_dir, [(k, s, sid, bp) for k, s, sid, bp, *_ in docs])
    res = []
    for q, role, label, toks, year, slack in AUTHORITIES:
        hits = []
        for key, source, sid, bp, title, pet, resp, date, y, insc in docs:
            name = norm(title) + norm(f"{pet} {resp}")
            if all(t in name for t in toks) and y is not None and abs(y - year) <= slack:
                d, st = status.get(key, (None, "unknown"))
                hits.append({"doc_key": key, "index_doc": d, "title": (title or "")[:80], "date": date, "insc": insc, "state": st})
        if not hits:
            where = "not_in_collection"
        elif any(h["state"] == "in_index" for h in hits):
            where = "in_index"
        else:
            where = "filtered_out" if all(h["state"] == "not_criminal" for h in hits) else "other_skip"
        res.append({"q": q, "role": role, "label": label, "where": where, "hits": hits})
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--corpus", default=os.environ.get("RECOURSE_CORPUS") or os.path.join(ROOT, "corpus.sqlite"))
    ap.add_argument("--index-dir", default=DEFAULT_INDEX)
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args(argv)
    res = run(a.corpus, a.index_dir)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for r in res:
        print(f"{r['q']:4} {r['role']:8} {r['where']:18} {r['label']}")
    keys = [r for r in res if r["role"] == "key"]
    stale = [r for r in res if r["role"] == "stale"]
    print()
    print(f"key authorities: {sum(r['where'] == 'in_index' for r in keys)} of {len(keys)} reachable; stale authorities: {sum(r['where'] == 'in_index' for r in stale)} of {len(stale)} reachable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
