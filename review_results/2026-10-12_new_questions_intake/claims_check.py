"""Spot-checks of statements in the new key against the text of the judgments that are in the index (read-only, no spend, nothing searched for any question).
Each line: (question, index doc, what the key says, a regular expression for words the judgment should contain). The script prints how many passages of that judgment match and the best snippet,
so that Mr. Advocate can see the passage. Not legal advice and not a verdict: a match shows the words are there, a miss shows they are not in this judgment's indexed text."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "review_tools")); sys.path.insert(0, ROOT)
import pool_runner as PR, sci_index as si
head = PR.index_head(PR.DEFAULT_INDEX)
metas, M, _ = si._load_index(PR.DEFAULT_INDEX)
for d in PR.FINAL_SIDE_INDEXES:
    metas, M, _, _ = PR.load_supplement(os.path.join(ROOT, d), metas, M, head)
by = {}
for m in metas:
    by.setdefault(m["doc"], []).append(m["text"])
C = [
 ("N01", 1000254065, "Antil endorses Siddharth on s.170 (no arrest at charge-sheet stage)", r"Siddharth"),
 ("N02", 37060, "Vijaysinh: s.50 NDPS applies to personal search; officer must tell the person of the right", r"section 50.{0,300}(?:person|gazetted)|gazetted officer"),
 ("N03", 41343, "Bafna quotes Niranjan Singh: a person who appears and submits to the court's jurisdiction is in custody", r"Niranjan Singh.{0,600}(?:surrender|custody)|(?:surrender|custody).{0,600}Niranjan Singh"),
 ("N04", 1000252765, "Bikramjit: only the Special Court (not a Magistrate) can extend under s.43D(2)(b); default bail right complete", r"43[- ]?D.{0,500}(?:Magistrate|Special Court|Court of Session)"),
 ("N05", 1000255096, "Ramesh Kumar (2023): monetary deposit condition on bail set aside", r"(?:deposit|Rs\.?|rupees).{0,300}condition|condition.{0,300}deposit"),
 ("N06", 1000255914, "Shajan Skaria: s.18 bar applies only where prima facie offence under the Act; 'public view'", r"public view"),
 ("N07", 1000253391, "Sripati Singh: cheque given as security can attract s.138 if the debt is due on presentation", r"security"),
 ("N08", 41940, "Yogendra Pratap Singh: premature complaint not maintainable; overrules Narsingh Das Tapadia", r"Narsingh Das Tapadia.{0,500}(?:overrul|not a good law|not correct)|(?:overrul).{0,300}Narsingh"),
 ("N09", 29085, "C.C. Alavi Haji: notice by registered post presumed served (s.27 General Clauses Act); drawer may pay within 15 days of summons", r"section 27.{0,300}General Clauses|General Clauses Act.{0,300}(?:27|service|served)"),
 ("N10", 1000252568, "Hira Singh: E. Micheal Raj 'not a good law'; neutral substance counts", r"not (?:a )?good law|Micheal Raj"),
 ("N11", 19299, "Madan Lal: occupants of a car, conscious possession (ss.35, 54 NDPS)", r"(?:conscious|possession).{0,400}(?:car|vehicle|occupant)|(?:car|vehicle|occupant).{0,400}(?:conscious|possession)"),
 ("N12", 35436, "Md. Ibrahim: sale deed of property one does not own is not 'making a false document'; only the purchaser can complain of cheating", r"false document.{0,500}(?:sale deed|title|own)|(?:sale deed).{0,400}false document"),
 ("N13", 1000253391, "Sripati Singh: s.420 IPC complaint on loan/security cheque facts held not sustainable (as the key says) while s.138 went on", r"\b420\b|cheating"),
 ("N14", 44402, "Digumarti: s.67 IT Act special; no prosecution under s.292 IPC for the same act once IT Act charge fails", r"292.{0,400}(?:67|Information Technology)|(?:67).{0,400}292"),
 ("N15", 1000253984, "Prabha Tyagi: right to reside in shared household; actual residence not essential", r"shared household"),
 ("N16", 1000253600, "Jogendra: demand for money to construct a house is dowry; Rajinder Singh followed", r"construct|house.{0,200}dowry|dowry.{0,200}house"),
 ("N17", 1000251591, "Rupali Devi: consequence of cruelty at the parental home gives that court jurisdiction", r"consequence|ensue"),
 ("N18", 1000255899, "In Re Right to Privacy of Adolescents: consent of a person below 18 is irrelevant under POCSO", r"consent.{0,300}(?:below|under|less than).{0,40}(?:18|eighteen)|(?:18|eighteen).{0,300}consent"),
 ("N19", 1000255124, "Yuvaprakash: s.94 JJ Act order of documents; school certificate first; is it about a victim or an accused?", r"victim|child in conflict|accused"),
 ("N19", 1000253442, "Rishipal Singh Solanki: principles for juvenility claim by an accused; school certificate first", r"matriculation|school|ossification"),
 ("N20", 17136, "Mango Ram: consent and submission; absence of resistance does not mean consent", r"submission|resist|consent"),
 ("N21", 1000000735, "Gunwantlal: possession of arms requires knowledge/control; recovery from a family house", r"possession.{0,400}(?:knowledge|conscious|control)|(?:knowledge|conscious|control).{0,400}possession"),
 ("N22", 38962, "Alister Anthony Pareira: s.304 Part II possible in drunk-driving deaths; knowledge", r"304.{0,40}Part II|knowledge"),
 ("N23", 18615, "Laxman: doctor's certificate not essential; Paparambaka not correctly decided", r"Paparambaka|certificate|medical"),
 ("N24", 1000256707, "Kushal Kumar Agarwal: s.223 BNSS hearing before cognizance of a PMLA complaint", r"223.{0,500}(?:cognizance|heard|hearing)|PMLA|Money-Laundering"),
 ("N25", 1000254584, "Neeraj Dutta: demand can be proved by circumstantial evidence if complainant dead/hostile", r"circumstantial|hostile|died|dead"),
 ("N26", 1000255467, "Bilkis: appropriate Government is the State where the offender is sentenced; Radheshyam order a nullity", r"appropriate Government.{0,500}(?:sentenced|tried|trial)|Radheshyam"),
 ("N26", 43153, "V. Sriharan Constitution Bench: appropriate Government = State where the offender is sentenced", r"appropriate Government.{0,500}(?:sentenced|within which|territorial)|432\(7\)\(b\)|offender is sentenced"),
 ("N27", 1000251075, "Mallikarjun Kodagali: victim's appeal under the proviso to s.372 needs no leave of the High Court", r"leave.{0,300}(?:proviso|372)|(?:proviso|372).{0,300}leave"),
 ("NR1", 1000254853, "Kapil Wadhawan: remand day counted; Rustam per incuriam", r"Rustam|per incuriam|first day|date of remand"),
 ("NR2", 1000254850, "Arup Bhuyan 2023: mere membership of an unlawful association is an offence; 2011 rulings overruled", r"mere membership|overrul|Raneef"),
]
for q, doc, says, rx in C:
    ps = by.get(doc, [])
    pat = re.compile(rx, re.I | re.S)
    hit = [t for t in ps if pat.search(t)]
    print(f"{q} doc {doc}: {len(hit)} of {len(ps)} passages match  | the key: {says}")
    if hit:
        t = re.sub(r"\s+", " ", hit[0])
        m = pat.search(t)
        a = max(0, (m.start() if m else 0) - 120)
        print("      ...", t[a:a + 520])
