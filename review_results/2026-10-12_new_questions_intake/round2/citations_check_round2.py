"""Mechanical pre-check of the citations in the round-2 key against the text of the other judgments in the index. For each authority the key names (N12 dropped), it asks:
  (1) is the case named in other indexed judgments, and with which citation(s) (within ~220 characters after the name, stopping at the next case name)?
  (2) is the key's own citation among them? (3) if not, does the key's citation appear next to some other case's name?  (4) for a judgment that is in the index, does its own text carry the key's citation (INSC numbers, headers)?
This is NOT a verification: a case cited by nobody else in the index cannot be checked this way, and a citation repeated by other judgments is only as good as they are. It shows where a person should look first.
Read-only on the index; nothing is searched for any question; no service is called. PRIVATE (it reads the key). Output: citations_check_round2.json and citations_check_round2_out.txt.
Run: python3 -P review_results/2026-10-12_new_questions_intake/round2/citations_check_round2.py [--reuse]   (about 5 minutes the first time; --reuse re-reads the cache of matching passages)"""
import collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, ROOT)
import pool_runner as PR, sci_index as si

# (question, label shown, regex for the case name as later judgments write it, the key's citation or None, index document(s) if the judgment is in the index)
E = [
 ("N01", "Siddharth v. State of U.P.", r"Siddharth\s+v\.?\s+State\s+of\s+(?:U\.?P\.?|Uttar)", "(2022) 1 SCC 676", []),
 ("N01", "Aman Preet Singh v. CBI", r"Aman\s*Preet\s+Singh\s+v", None, []),
 ("N01", "Satender Kumar Antil v. CBI", r"Satender\s+Kumar\s+Antil\s+v", "(2022) 10 SCC 51", [1000254065]),
 ("N01", "Joginder Kumar v. State of U.P.", r"Joginder\s+Kumar\s+v\.?\s+State\s+of\s+(?:U\.?P\.?|Uttar)", "(1994) 4 SCC 260", []),
 ("N02", "D.K. Basu v. State of W.B.", r"D\.?\s?K\.?\s?Basu\s+v", "(1997) 1 SCC 416", [14580]),
 ("N02", "Arnesh Kumar v. State of Bihar", r"Arnesh\s+Kumar\s+v", "(2014) 8 SCC 273", [41736]),
 ("N03", "Niranjan Singh v. Prabhakar Rajaram Kharote", r"Niranjan\s+Singh\s+v", "(1980) 2 SCC 559", [4587]),
 ("N03", "Sundeep Kumar Bafna v. State of Maharashtra", r"(?:Sundeep|Sandeep)\s+Kumar\s+Bafna\s+v", "(2014) 16 SCC 623", [41343]),
 ("N04", "Bikramjit Singh v. State of Punjab", r"Bikramjit\s+Singh\s+v", "(2020) 10 SCC 616", [1000252765]),
 ("N04", "Hitendra Vishnu Thakur v. State of Maharashtra", r"Hitendra\s+Vishnu\s+Thakur\s+v", "(1994) 4 SCC 602", [1000001711]),
 ("N04", "M. Ravindran v. Intelligence Officer, DRI", r"Ravindran\s+v", "(2021) 2 SCC 485", [1000252778]),
 ("N05", "Dilip Singh v. State of M.P.", r"Dilip\s+Singh\s+v\.?\s+State\s+of\s+(?:M\.?P\.?|Madhya)", "(2021) 2 SCC 779", []),
 ("N05", "Ramesh Kumar v. State (NCT of Delhi)", r"Ramesh\s+Kumar\s+v\.?\s+State\s*\(?\s*(?:NCT|N\.C\.T)", "2023 INSC 596", [1000255096]),
 ("N05", "U.N. Gupta @ Udhav Narayan Gupta v. State of Bihar", r"(?:U\.?\s?N\.?\s+Gupta|Udhav\s+Narayan\s+Gupta)", None, []),
 ("N06", "Shajan Skaria v. State of Kerala", r"Shajan\s+Skaria\s+v", "2024 INSC 625", [1000255914]),
 ("N06", "Hitesh Verma v. State of Uttarakhand", r"Hitesh\s+Verma\s+v", "(2020) 10 SCC 710", [1000252799]),
 ("N06", "Swaran Singh v. State", r"Swaran\s+Singh\s+(?:&\s+Ors\.?\s+)?v\.?\s+State", "(2008) 8 SCC 435", [32269]),
 ("N06", "Ramesh Chandra Vaishya v. State of U.P.", r"Ramesh\s+Chandra\s+Vaishya\s+v", "2023 SCC OnLine SC 668", [1000255070]),
 ("N06", "Prathvi Raj Chauhan v. Union of India", r"Prathvi\s+Raj\s+Chauhan\s+v", "(2020) 4 SCC 727", [1000252416]),
 ("N07", "Sripati Singh v. State of Jharkhand", r"Sripati\s+Singh\s+v", None, [1000253391]),
 ("N07", "Sampelly Satyanarayana Rao v. IREDA", r"Sampelly\s+Satyanarayana\s+Rao\s+v", "(2016) 10 SCC 458", [43948]),
 ("N07", "Womb Laboratories v. Vijay Ahuja", r"Womb\s+Laboratories", None, []),
 ("N07", "Indus Airways v. Magnum Aviation", r"Indus\s+Airways\s+(?:\(P\)\s+Ltd\.?\s+|Pvt\.?\s+Ltd\.?\s+)?v", "(2014) 12 SCC 539", [41392]),
 ("N08", "Yogendra Pratap Singh v. Savitri Pandey", r"Yogendra\s+Pratap\s+Singh\s+v", "(2014) 10 SCC 713", [41940, 39246]),
 ("N08", "Sarav Investment v. Llyods Register of Shipping", r"Sarav\s+Investment", "(2007) 14 SCC 753", [29653]),
 ("N08", "Narsingh Das Tapadia v. Goverdhan Das Partani", r"Narsingh\s+Das\s+Tapadia", "(2000) 7 SCC 183", [17418]),
 ("N09", "C.C. Alavi Haji v. Palapetty Muhammed", r"Alavi\s+Haji\s+v", "(2007) 6 SCC 555", [29085]),
 ("N09", "K. Bhaskaran v. Sankaran Vaidhyan Balan", r"Bhaskaran\s+v\.?\s+Sankaran", "(1999) 7 SCC 510", []),
 ("N09", "Vinod Shivappa v. Nanda Belliappa", r"Vinod\s+Shivappa\s+v", "(2006) 6 SCC 456", [27788]),
 ("N10", "Hira Singh v. Union of India", r"Hira\s+Singh\s+(?:&\s+Anr\.?\s+)?v\.?\s+Union\s+of\s+India", None, [1000252568]),
 ("N10", "E. Micheal Raj v. Intelligence Officer, NCB", r"Micheal\s+Raj\s+v", "(2008) 5 SCC 161", [30812]),
 ("N11", "Madan Lal v. State of H.P.", r"Madan\s+Lal\s+v\.?\s+State\s+of\s+(?:H\.?P\.?|Himachal)", "(2003) 7 SCC 465", [19299]),
 ("N11", "Avtar Singh v. State of Punjab", r"Avtar\s+Singh\s+v\.?\s+State\s+of\s+Punjab", "AIR 2002 SC 3343", [18827]),
 ("N11", "Mohan Lal v. State of Rajasthan", r"Mohan\s+Lal\s+v\.?\s+State\s+of\s+Rajasthan", "(2015) 6 SCC 222", []),
 ("N11", "Dharampal Singh v. State of Punjab", r"Dharampal\s+Singh\s+v\.?\s+State\s+of\s+Punjab", "(2010) 9 SCC 608", [36871]),
 ("N11", "Sorabkhan Gandhkhan Pathan v. State of Gujarat", r"Sorabkhan", "(2004) 13 SCC 608", []),
 ("N11", "Union of India v. Md. Nawaz Khan", r"Nawaz\s+Khan", "(2021) 10 SCC 100", [1000253281]),
 ("N13", "Hridaya Ranjan Prasad Verma v. State of Bihar", r"Hridaya\s+Ranjan\s+(?:Prasad|Pd\.?)\s+Verma", "(2000) 4 SCC 168", [20323]),
 ("N13", "Sarabjit Kaur v. State of Punjab", r"Sarabjit\s+Kaur\s+v", "(2023) 5 SCC 360", []),
 ("N13", "Delhi Race Club (1940) Ltd. v. State of U.P.", r"Delhi\s+Race\s+Club", "2024 INSC 626", [1000255917]),
 ("N14", "Sharat Babu Digumarti v. Govt. of NCT of Delhi", r"Digumarti", "(2017) 2 SCC 18", [44402]),
 ("N15", "Rajnesh v. Neha", r"Rajnesh\s+v", "(2020) 15 SCC 17", [1000252794]),
 ("N15", "Shyamlal Devda v. Parimala", r"Shyamlal\s+Devda", "(2020) 3 SCC 14", [1000252355]),
 ("N15", "Juveria Abdul Majid Patni v. Atif Iqbal Mansoori", r"Juveria\s+Abdul", "(2014) 10 SCC 736", [1000004478]),
 ("N16", "State of M.P. v. Jogendra", r"State\s+of\s+(?:M\.?P\.?|Madhya\s+Pradesh)\s+v\.?\s+Jogendra", None, [1000253600]),
 ("N16", "Rajinder Singh v. State of Punjab", r"Rajinder\s+Singh\s+v\.?\s+State\s+of\s+Punjab", "(2015) 6 SCC 477", []),
 ("N16", "Appasaheb v. State of Maharashtra", r"Appasaheb\s+(?:&\s+Anr\.?\s+)?v\.?\s+State\s+of\s+Maharashtra", "(2007) 9 SCC 721", [31195]),
 ("N17", "Rupali Devi v. State of U.P.", r"Rupali\s+Devi\s+v", "(2019) 5 SCC 384", [1000251591]),
 ("N17", "Y. Abraham Ajith v. Inspector of Police", r"Abraham\s+Ajith\s+v", "(2004) 8 SCC 100", [26334]),
 ("N17", "Ramesh v. State of T.N.", r"Ramesh\s+v\.?\s+State\s+of\s+(?:T\.?N\.?|Tamil)", "(2005) 3 SCC 507", []),
 ("N18", "In Re: Right to Privacy of Adolescents", r"Right\s+to\s+Privacy\s+of\s+Adolescents", "2024 INSC 614", [1000255899]),
 ("N18", "Independent Thought v. Union of India", r"Independent\s+Thought\s+v", "(2017) 10 SCC 800", [1000250306]),
 ("N18", "Anversinh v. State of Gujarat", r"Anversinh\s+v", "(2021) 3 SCC 12", [1000252878]),
 ("N19", "P. Yuvaprakash v. State", r"Yuvaprakash\s+v", "2023 INSC 676", [1000255124]),
 ("N19", "Rishipal Singh Solanki v. State of U.P.", r"Rishipal\s+Singh\s+Solanki", "(2022) 8 SCC 602", [1000253442]),
 ("N19", "Vinod Katara v. State of U.P.", r"Vinod\s+Katara\s+v", "2024 LiveLaw (SC) 210", [1000254297]),
 ("N19", "Suresh v. State of U.P.", r"Suresh\s+v\.?\s+State\s+of\s+(?:U\.?P\.?|Uttar)", None, []),
 ("N20", "State of H.P. v. Mango Ram", r"Mango\s+Ram", "(2000) 7 SCC 224", [17136]),
 ("N20", "State of Punjab v. Gurmit Singh", r"State\s+of\s+Punjab\s+v\.?\s+Gurmit\s+Singh", "(1996) 2 SCC 384", [16186]),
 ("N20", "Mahmood Farooqui v. State (Govt. of NCT of Delhi)", r"Mahmood\s+Farooqui", "(2017) 6 SCC 631", []),
 ("N21", "Gunwantlal v. State of M.P.", r"Gunwantlal\s+v", "(1972) 2 SCC 194", [1000000735]),
 ("N21", "Sanjay Dutt v. State through CBI", r"Sanjay\s+Dutt\s+v", "(1994) 5 SCC 410", [1000001771]),
 ("N21", "State of Jharkhand v. Jagdish Lakra", r"Jagdish\s+Lakra", "2026 INSC 686", []),
 ("N22", "Alister Anthony Pareira v. State of Maharashtra", r"Alister\s+Anthony\s+Pareira", "(2012) 2 SCC 648", [38962]),
 ("N22", "State v. Sanjeev Nanda", r"Sanjeev\s+Nanda", "(2012) 8 SCC 450", [35162]),
 ("N23", "Laxman v. State of Maharashtra", r"Laxman\s+v\.?\s+State\s+of\s+Maharashtra", "(2002) 6 SCC 710", [18615]),
 ("N23", "Koli Chunilal Savji v. State of Gujarat", r"Koli\s+Chunilal\s+Savji", "(1999) 9 SCC 562", [16637]),
 ("N23", "Surendra Bangali v. State of Jharkhand", r"Surendra\s+Bangali", "2021 LiveLaw (SC) 82", []),
 ("N23", "Paparambaka Rosamma v. State of A.P.", r"Paparambaka\s+Rosamma", "(1999) 7 SCC 695", [16680]),
 ("N24", "Kushal Kumar Agarwal v. Directorate of Enforcement", r"Kushal\s+Kumar\s+Agarwal", "2025 INSC 760", [1000256707]),
 ("N24", "Manharibhai Muljibhai Kakadia v. Shaileshbhai Mohanbhai Patel", r"Manharibhai", "(2012) 10 SCC 517", [39617]),
 ("N25", "Neeraj Dutta v. State (Govt. of NCT of Delhi)", r"Neeraj\s+Dutta\s+v", "(2023) 4 SCC 731", [1000254584]),
 ("N25", "Jagtar Singh v. State of Punjab", r"Jagtar\s+Singh\s+v\.?\s+State\s+of\s+Punjab", None, []),
 ("N25", "P. Satyanarayana Murthy v. Dist. Inspector of Police", r"Satyanarayana\s+Murthy\s+v", "(2015) 10 SCC 152", [42944]),
 ("N25", "B. Jayaraj v. State of A.P.", r"Jayaraj\s+v\.?\s+State\s+of\s+(?:A\.?P\.?|Andhra)", "(2014) 13 SCC 55", [41352]),
 ("N26", "Bilkis Yakub Rasool v. Union of India", r"Bilkis\s+Yakub\s+Rasool\s+v", None, [1000255467]),
 ("N26", "Union of India v. V. Sriharan", r"Union\s+of\s+India\s+v\.?\s+V\.?\s+Sriharan", "(2016) 7 SCC 1", [43153]),
 ("N26", "Radheshyam Bhagwandas Shah v. State of Gujarat", r"Radheshyam\s+Bhagwandas\s+Shah", "(2022) 8 SCC 552", []),
 ("N27", "Mallikarjun Kodagali v. State of Karnataka", r"Mallikarjun\s+Kodagali", "(2019) 2 SCC 752", [1000251075]),
 ("N27", "Vishnu Kumar Gupta v. State of M.P.", r"Vishnu\s+Kumar\s+Gupta", "2026 INSC 770", []),
 ("N27", "Celestium Financial v. A. Gnanasekaran", r"Celestium", None, [1000256564]),
 ("N27", "Satya Pal Singh v. State of M.P.", r"Satya\s+Pal\s+Singh\s+v", "(2015) 15 SCC 613", [43002]),
 ("NR1", "Enforcement Directorate v. Kapil Wadhawan", r"Kapil\s+Wadhawan", "2023 LiveLaw (SC) 249", [1000254853]),
 ("NR1", "Chaganti Satyanarayana v. State of A.P.", r"Chaganti\s+Satyanarayana", "(1986) 3 SCC 141", [9024]),
 ("NR1", "State of M.P. v. Rustam", r"State\s+of\s+(?:M\.?P\.?|Madhya\s+Pradesh)\s+v\.?\s+Rustam", "1995 Supp (3) SCC 221", []),
 ("NR2", "Arup Bhuyan v. State of Assam (2011)", r"Arup\s+Bhuyan\s+v", "(2011) 3 SCC 377", [37441]),
 ("NR2", "State of Kerala v. Raneef", r"Raneef", "(2011) 1 SCC 784", [37314]),
]

# the year the key gives for authorities named without a citation (used only to discard citations of other cases of the same name)
KEY_YEAR = {"Aman Preet Singh v. CBI": 2021, "U.N. Gupta @ Udhav Narayan Gupta v. State of Bihar": 2024, "Sripati Singh v. State of Jharkhand": 2021, "Womb Laboratories v. Vijay Ahuja": 2019, "Hira Singh v. Union of India": 2020,
            "State of M.P. v. Jogendra": 2022, "Suresh v. State of U.P.": 2024, "Jagtar Singh v. State of Punjab": 2023, "Bilkis Yakub Rasool v. Union of India": 2024, "Celestium Financial v. A. Gnanasekaran": 2025}
CITE_FORMS = [
 (re.compile(r"\(\s*((?:19|20)\d\d)\s*\)\s*(\d+)\s*SCC\s*(\d+)\b", re.I), lambda m: f"({m[1]}) {m[2]} SCC {m[3]}"),
 (re.compile(r"\b((?:19|20)\d\d)\s*\(\s*(\d+)\s*\)\s*SCC\s*(\d+)\b", re.I), lambda m: f"({m[1]}) {m[2]} SCC {m[3]}"),
 (re.compile(r"\b((?:19|20)\d\d)\s+Supp\s*\(\s*(\d+)\s*\)\s*SCC\s*(\d+)\b", re.I), lambda m: f"{m[1]} Supp ({m[2]}) SCC {m[3]}"),
 (re.compile(r"\bAIR\s+((?:19|20)\d\d)\s+SC\s+(\d+)\b", re.I), lambda m: f"AIR {m[1]} SC {m[2]}"),
 (re.compile(r"\b((?:19|20)\d\d)\s+INSC\s+(\d+)\b", re.I), lambda m: f"{m[1]} INSC {m[2]}"),
 (re.compile(r"\b((?:19|20)\d\d)\s+SCC\s+On\s*Line\s+SC\s+(\d+)\b", re.I), lambda m: f"{m[1]} SCC OnLine SC {m[2]}"),
 (re.compile(r"\b((?:19|20)\d\d)\s+LiveLaw\s*\(\s*SC\s*\)\s*(\d+)\b", re.I), lambda m: f"{m[1]} LiveLaw (SC) {m[2]}"),
]
NEXT_CASE = re.compile(r"\sv(?:s)?\.?\s|;\s|\bIn re\b", re.I)


def cites_in(s):
    out = []
    for rx, fmt in CITE_FORMS:
        for m in rx.finditer(s):
            out.append((m.start(), fmt(m)))
    return sorted(out)


def cite_year(c):
    m = re.search(r"(?<!\d)((?:19|20)\d\d)(?!\d)", c or "")
    return int(m[1]) if m else None


def reporter(c):
    return "AIR" if c.startswith("AIR") else "INSC" if "INSC" in c else "SCC OnLine" if "OnLine" in c else "LiveLaw" if "LiveLaw" in c else "SCC"


def year_of_title(t):
    ys = [int(y) for y in re.findall(r"(?<!\d)(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.]((?:19|20)\d\d)(?!\d)", t or "")]
    return ys[0] if ys else None


def norm_cite(c):
    got = cites_in(c)
    return got[0][1] if got else c


def main():
    import pickle
    reuse = "--reuse" in sys.argv
    import tempfile
    cache = os.path.join(os.environ.get("CIT_CACHE_DIR", tempfile.gettempdir()), "citations_candidates.pkl")        # a cache of the matching passages, so that the verdict logic can be re-run in seconds with --reuse; never inside the repository
    head = PR.index_head(PR.DEFAULT_INDEX)
    metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
    extra_titles = {}
    for d in PR.FINAL_SIDE_INDEXES:
        metas, M, _info, extra = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
        extra_titles.update(extra)
    title = PR.titles([PR.DEFAULT_INDEX] + [os.path.join(ROOT, d) for d in PR.FINAL_SIDE_INDEXES], metas, extra_titles or None)
    ent = []
    for q, label, nrx, cite, docs in E:
        c = norm_cite(cite) if cite else None
        ys = [y for y in (year_of_title(title(d) or "") for d in docs) if y]
        ent.append({"q": q, "label": label, "nrx": re.compile(nrx, re.I), "cite": c, "key_cite_text": cite, "docs": docs, "doc_year": ys[0] if ys else None, "key_year": cite_year(c) if c else KEY_YEAR.get(label)})
    # pass 1 (slow, once): the passages that name the case, and the passages that carry the key's citation
    if reuse and os.path.exists(cache):
        cand_name, cand_cite = pickle.load(open(cache, "rb"))
    else:
        texts = [(m["doc"], re.sub(r"\s+", " ", m["text"])) for m in metas]
        cand_name = [[] for _ in ent]; cand_cite = [[] for _ in ent]
        by_cite = collections.defaultdict(list)
        for i, e in enumerate(ent):
            if e["cite"]:
                by_cite[e["cite"]].append(i)
        for doc, t in texts:
            for i, e in enumerate(ent):
                if e["nrx"].search(t):
                    cand_name[i].append((doc, t))
            if "SCC" in t or "INSC" in t or "LiveLaw" in t or "AIR" in t:
                for _, c in cites_in(t):
                    for i in by_cite.get(c, ()):
                        if (doc, t) not in cand_cite[i]:
                            cand_cite[i].append((doc, t))
        pickle.dump((cand_name, cand_cite), open(cache, "wb"))
    # pass 2 (fast): the verdicts
    res = []
    for i, e in enumerate(ent):
        own_docs = set(e["docs"])
        alt = collections.Counter(); with_key_docs = set(); snippets = []; name_docs = set(); n_name = 0; elsewhere = collections.Counter(); own = False; foot_docs = set()
        for doc, t in cand_name[i]:
            if doc in own_docs:
                continue
            n_name += 1; name_docs.add(doc)
            for m in e["nrx"].finditer(t):
                after = t[m.end(): m.end() + 230]
                cut = next((x for x in NEXT_CASE.finditer(after) if x.start() > 60 or x.group().strip(". ;").lower() not in ("v", "vs")), None)       # the case's own 'v. Respondent' (up to ~60 characters) is not the next case
                seg = after[: cut.start()] if cut else after
                for _, c in cites_in(seg):
                    y0 = e["doc_year"] or e["key_year"]
                    if y0 and cite_year(c) and not (y0 - 1 <= cite_year(c) <= y0 + 2) and c != e["cite"]:
                        continue                                    # a citation from another period: another case of the same name
                    alt[c] += 1
                    if e["cite"] and c == e["cite"]:
                        with_key_docs.add(doc)
                        if len(snippets) < 2:
                            snippets.append((doc, t[max(0, m.start() - 40): m.end() + 140]))
        if e["cite"]:
            for doc, t in cand_cite[i]:
                for c_pos, c in cites_in(t):
                    if c != e["cite"]:
                        continue
                    pre = t[max(0, c_pos - 170): c_pos]
                    nm = None
                    for mm in e["nrx"].finditer(pre):
                        nm = mm
                    if doc in own_docs:
                        own = True
                    elif nm is not None:
                        between = pre[nm.start():]
                        if ";" not in between and len(re.findall(r"\sv(?:s)?\.?\s", between)) <= 1:
                            with_key_docs.add(doc); alt[c] += 1
                            if len(snippets) < 2:
                                snippets.append((doc, t[max(0, c_pos - 150): c_pos + 40]))
                            break
                    elif re.search(r"(?:^|\s)\d{1,3}\s*$", pre):
                        foot_docs.add(doc)                          # a footnote list: the number before the citation is the footnote's, the case name stands in the text
                    else:
                        who = re.findall(r"([A-Z][A-Za-z.&'\u2019 ]{2,40}?\sv\.?\s[A-Z][A-Za-z.&'\u2019() ]{2,40})[,\s(\[]*$", pre)
                        elsewhere[who[-1].strip() if who else "(name not read)"] += 1
                        break
        year_flag = ""
        if e["cite"] and e["doc_year"] and cite_year(e["cite"]) and abs(cite_year(e["cite"]) - e["doc_year"]) > 1:
            year_flag = f" YEAR DOES NOT FIT: the key's citation is of {cite_year(e['cite'])}; the judgment in the index is dated {e['doc_year']}."
        if e["cite"] is None:
            if alt:
                verdict = "NO CITE IN THE KEY; other indexed judgments cite it as " + ", ".join(f"{c} (x{n})" for c, n in alt.most_common(3)); code = "no-cite-alt"
            else:
                verdict = "NO CITE IN THE KEY; " + (f"named in {n_name} passages of other judgments, never with a citation I could read" if n_name else "not named in any other indexed judgment"); code = "no-cite"
        elif with_key_docs:
            verdict = f"OK: other indexed judgments cite it as {e['cite']} ({len(with_key_docs)} judgment(s))"; code = "confirmed"
        elif own and e["docs"]:
            verdict = f"OK in its own text: the judgment itself carries {e['cite']}"; code = "own"
        elif alt:
            top = alt.most_common(3)
            if reporter(e["cite"]) not in {reporter(c) for c in alt}:
                verdict = f"parallel citation to check: the key gives {e['cite']}; other indexed judgments give {', '.join(f'{c} (x{n})' for c, n in top)} (a different reporter, not necessarily a conflict)"; code = "parallel"
            else:
                verdict = f"CHECK: the key says {e['cite']}; other indexed judgments cite this case as " + ", ".join(f"{c} (x{n})" for c, n in top); code = "alt-differs"
        elif foot_docs & name_docs:
            verdict = f"OK (footnote): the citation {e['cite']} stands in a footnote of {len(foot_docs & name_docs)} judgment(s) whose text names the case"; code = "confirmed-fn"
        elif foot_docs and not elsewhere:
            verdict = f"footnote only: the citation {e['cite']} stands in a footnote list ({len(foot_docs)} judgment(s), e.g. doc {sorted(foot_docs)[0]}); the case name is not read there. Consistent with the key, not a confirmation"; code = "footnote-only"
        elif elsewhere:
            top = elsewhere.most_common(3)
            verdict = f"CHECK: the key's citation {e['cite']} appears in the index next to other names: " + "; ".join(f"{n} (x{k})" for n, k in top); code = "cite-elsewhere"
        elif n_name:
            verdict = f"not confirmed: named in {n_name} passages of other judgments, never with a citation I could read"; code = "unconfirmed"
        else:
            verdict = "not checkable here: neither the name nor the citation appears in any other indexed judgment"; code = "not-checkable"
        verdict += year_flag
        if year_flag:
            code += "+year"
        res.append({"q": e["q"], "label": e["label"], "key_cite": e["key_cite_text"], "docs": e["docs"], "code": code, "verdict": verdict, "n_name_passages": n_name, "n_name_judgments": len(name_docs),
                    "alt_cites": alt.most_common(5), "cite_next_to": elsewhere.most_common(4), "own_text": own, "snippets": snippets})
    json.dump({"index_head": head, "rows": res}, open(os.path.join(HERE, "citations_check_round2.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    cnt = collections.Counter(r["code"] for r in res)
    for r in res:
        print(f"{r['q']:4} {r['label'][:58]:58} | {r['key_cite'] or '-':24} | {r['verdict']}")
    print("\n", dict(cnt), "of", len(res))


if __name__ == "__main__":
    main()
