"""Writes results.csv for the 'overruled after 2015' list check: one row per list entry with my verdict, the court's own words (short), and notes.
Verdict codes: C confirmed as stated | CN confirmed, but the list's wording is incomplete or needs a caveat | P partly: substance yes, the court did not use the word 'overruled' |
W wrong in a material detail | U cannot be checked from our collection. Evidence: B = the judgment's own sentence in its body; H = the law-report's headnote only."""
import csv, json, collections
SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/"
rows = {r["no"]: r for r in json.load(open(SP + "pdf2_in/rows.json"))}
BK = {1:"b2017_10_569_999",2:"b2017_10_569_999",3:"b2017_10_569_999",4:"c44452",5:"c44452",6:"b2017_13_1009_1052",7:"b2017_13_1009_1052",8:"b2018_7_1191_1231",9:"b2018_7_379_746",
 10:"b2018_11_765_950",11:"b2018_11_765_950",12:"b2018_11_765_950",13:"b2019_15_795_864",14:"b2019_4_928_944",15:"b2019_15_936_989",16:"b2019_15_936_989",17:"b2019_15_936_989",
 18:"b2019_15_936_989",19:"b2019_15_936_989",20:"b2019_11_74_134",21:"b2019_11_74_134",22:"b2019_11_74_134",**{n:"b2020_2_1_131" for n in range(23,32)},32:"b2020_7_180_282",33:"b2020_7_180_282",
 34:"b2020_9_245_302",35:"b2020_10_135_237",36:"b2020_10_135_237",37:"b2020_10_135_237",38:"b2020_11_1001_1180",39:"b2021_12_311_364",40:"b2021_3_193_254",41:"b2020_3_1_328",
 42:"b2020_3_1_328 (the list names b2023_1_919_924)",43:"",44:"b2023_8_496_580",45:"b2023_8_496_580",46:"b2023_8_496_580",47:"b2019_17_1013_1047",48:"b2024_11_1647_2038",49:"b2024_8_1321_1672",
 50:"b2024_7_1549_1846",51:"b2024_10_1931_2182",52:"b2024_2_946_988",53:"b2024_11_541_640",54:"b2024_11_541_640",55:"b2024_11_541_640",56:"b2024_11_541_640",57:"b2023_9_285_492",58:"b2025_2_1331_1395",59:"b2025_2_1331_1395"}
V = {  # no: (verdict, evidence, court's words (short), note)
1:("C","H+B","MP Sharma is overruled to the extent to which it indicates to the contrary","9-judge bench. Only to that extent."),
2:("C","H+B","Kharak Singh to the extent that it holds that the right to privacy is not protected ... is overruled","Only the second part of Kharak Singh; the first part was held correct."),
3:("CN","H+B","ADM Jabalpur must be and is accordingly overruled","The same judgment also overruled Union of India v. Bhanudas Krishna Gawde (1977); the list omits it."),
4:("CN","B","To this extent, both Bhupendra Kumar Bose and Venkata Reddy are overruled","What was overruled is the 'enduring rights' theory for ordinances. The list's description (re-promulgation) names a different holding of the same judgment."),
5:("CN","B","Bhupendra Kumar Bose and T. Venkata Reddy ... to the extent ... 'creation of enduring rights' ... not correctly decided and should stand overruled","Same note as row 4."),
6:("C","B","Saith and Skelton and Guru Nanak Foundation do not lay the correct position of law and ... are overruled. Any other judgment ... also stands overruled","5-judge bench."),
7:("C","B","same sentence as row 6","5-judge bench."),
8:("CN","H+B","The ratio in Sun Export case is not correct and all the decisions which took similar view ... stand over-ruled","5-judge bench. 'All decisions which took a similar view' are overruled too; the list names one case."),
9:("C","B","Suresh Kumar Koushal needs to be, and is hereby, overruled","5-judge bench. The list's '2013/2014' is right (decided 11 Dec 2013, reported 2014)."),
10:("C","B","The decisions in Sowmithri Vishnu, V. Revathi and W. Kalyani hereby stand overruled","5-judge bench."),
11:("C","B","same sentence as row 10",""),
12:("C","B","same sentence as row 10",""),
13:("CN","B","The decision in Foreshore Cooperative Housing Society Limited cannot be said to be laying down the law correctly","3-judge bench on a 2-judge decision. The court uses 'overruled' for other decisions (Meher Singh, Sudesh) but not for Foreshore; the report's tag for Foreshore is 'Not correct law'."),
14:("C","B","the judgment of Motilal Pesticides is erroneous. We, therefore, overrule this judgment",""),
15:("CN","B","to the extent that the judgments in Amrutbhai Shambubhai Patel, Athul Rao and Bikash Ranjan Rout have held to the contrary, they stand overruled","3-judge bench. Same judgment: Devarapalli Lakshminarayana Reddy (1976) 'held not correct law' (headnote tag); the list omits it."),
16:("C","B","same sentence as row 15",""),
17:("C","B","same sentence as row 15",""),
18:("C","B","Randhir Singh Rana ... and Reeta Nag ... also stand overruled",""),
19:("C","B","same sentence as row 18",""),
20:("C","B","decisions of Gurudwara Sahab v. Gram Panchayat Village Sirthala ... cannot be said to be laying down the law correctly, thus they are hereby overruled","3-judge bench. The judgment spells it 'Gurudwara Sahab'. Gurdwara Sahib itself is not in our collection."),
21:("C","B","same sentence as row 20",""),
22:("C","B","same sentence as row 20",""),
23:("C","B","the decision in Salauddin Abdulsamad Shaikh ... and subsequent decisions ... are hereby overruled","5-judge bench. The list's year 1996 is right."),
24:("C","B","(including K.L. Verma ...) are hereby overruled","Verified list 1 (row 256) also records K.L. Verma as overruled, by Adri Dharan Das (2005): a chain, see README."),
25:("C","B","same sentence as row 24",""),
26:("C","B","same sentence as row 24","Adri Dharan Das is itself the 'overruling case' of row 256 in list 1: chain."),
27:("C","B","same sentence as row 24",""),
28:("C","B","same sentence as row 24","Decided 16 Dec 2009; list says 2010 (reporter year)."),
29:("C","B","same sentence as row 24","The list says 'in relevant part'; the court lists it with the other decisions as overruled."),
30:("C","B","same sentence as row 24","Decided 23 Oct 2007; list says 2008 (reporter year)."),
31:("C","B","observations in Mhetre that no restrictive conditions at all can be imposed ... are hereby overruled","Partly, as the list says. Decided 2 Dec 2010; list says 2011. The headnote's case list for another opinion in the same judgment also tags Bhadresh Bipinbhai Sheth (2016) 'overruled'; the list omits it (headnote only)."),
32:("C","B","do not lay down the law correctly and are therefore overruled","3-judge bench."),
33:("CN","H+B","Tomaso Bruno ... being per incuriam, does not lay down the law correctly ... overruled","Both Tomaso Bruno (2015) and the overruling bench are 3-judge benches in our metadata: lawyer should confirm how the court treated a same-strength decision."),
34:("C","H+B","are not good law and they are specifically overruled","5-judge bench. Mohan Lal itself overruled Kader (2018, 3 judges; omitted by the list): chain."),
35:("C","B","we overrule the views to the contrary expressed in Prakash v. Phulavati and Mangammal v. T.B. Raju","3-judge bench."),
36:("C","B","same sentence as row 35",""),
37:("C","B","The opinion expressed in Danamma is partly overruled to the extent it is contrary to this decision","Partly, as the list says."),
38:("CN","B","we overrule the ratio laid down in Himangni Enterprises","N. Radhakrishnan v. Maestro Engineers (2010) is also tagged 'overruled' in the same judgment; the list omits it."),
39:("W","B","the Mohan judgment stands on a legally vulnerable footing. It would not be a binding precedent, after enforcement of the RPwD Act 2016","The court does not overrule Surendra Mohan; the report's headnote lists it only as 'referred to'. The list's label 'Expressly overruled' is not what the court said."),
40:("C","B","N.V. International has been wrongly decided and is therefore overruled","3-judge bench."),
41:("C","B","the decision rendered in Pune Municipal Corpn. is hereby overruled and all other decisions in which [it] has been followed, are also overruled","5-judge bench."),
42:("W","B","The decision in Shree Balaji Nagar Residential Association cannot be said to be laying down good law, is overruled","The fact is right, the overruling case is not: the 5-judge bench in Indore Development Authority v. Manoharlal (2020) did it. DDA v. Asha Prakash (2023, 2 judges) only quotes that holding. Indore Development Authority v. Shailendra (2018, 3 judges) also says Shree Balaji is overruled (collection, same sentence form): the list shows neither."),
43:("U","-","(not in our collection)","Union of India v. Parshotam Dass (2023) is not in the collection; nothing could be checked."),
44:("C","H","held not good law (the report's tag)","3-judge bench. 'Not good law' is the court's phrase, not 'overruled'."),
45:("C","H","held not good law","3-judge bench."),
46:("C","H","held not good law","3-judge bench."),
47:("P","B","the decisions in SRD Nutrients ... and Bajaj Auto ... are clearly per incuriam","3-judge bench: a smaller bench ignored binding larger-bench decisions. 'Per incuriam', not 'overruled'. Decided 6 Dec 2019; the list says 2020. SRD Nutrients itself is not in our collection."),
48:("CN","B","The view taken in Azeez Basha that an educational institution is not established by a minority if it derives its legal character through a statute, is overruled","7-judge bench; four judges (the Chief Justice's opinion) overruled that one view. Surya Kant J: 'modified and clarified'; Datta J: against overruling. AMU's own status was left to a regular bench."),
49:("C","B","The holding in Chinnaiah that sub-classification of the Scheduled Castes is impermissible is overruled","7-judge bench, 6:1 (Trivedi J dissenting). Decided 5 Nov 2004; the list says 2005."),
50:("CN","B","The decisions in India Cement, Orissa Cement, Federation of Mining Associations of Rajasthan, Mahalaxmi Fabric Mills, Saurashtra Cement, Mahanadi Coalfields and P Kannadasan are overruled to the extent of the observations made in the present case","9-judge bench, 8:1 (Nagarathna J dissenting). 'To the extent' and six other decisions that the list omits. Decided 25 Oct 1989; the list says 1990."),
51:("C","B","The judgment in Synthetics (7J) is overruled in terms of this judgment","9-judge bench, 8:1 (Nagarathna J dissenting). Decided 25 Oct 1989; the list says 1990."),
52:("P","B","we are unable to concur with the directions issued in paragraphs 36 and 37 ... We do not approve the direction","5-judge bench. Only two directions of Asian Resurfacing (automatic vacation of stay; day-to-day hearing). The court says 'unable to concur / not approve', not 'overruled'."),
53:("C","B","the three judgments which concluded otherwise i.e. Prabhu Lal, Roshanben Rahemansha Fakir and Angad Kol are overruled","5-judge bench. Mukund Dewangan (2017, 3 judges) had already overruled Prabhu Lal ('is hereby overruled'); the list shows only 2024."),
54:("C","B","same sentence as row 53",""),
55:("C","B","same sentence as row 53",""),
56:("C","B","We therefore partially overrule the decision in Annappa Irappa Nesaria for the view taken w.r.t the post-1994 amendment position","Partly, as the list says."),
57:("CN","B","[2023, 5 judges] N.N. Global (2021) 4 SCC 379 - overruled (majority); [7 judges, 13 Dec 2023] The decision in NN Global 2 and SMS Tea Estates are overruled","True as far as it goes: the 2023 majority (3:2; Rastogi J and Roy J dissenting) overruled the 2021 decision. But the 2023 decision was itself overruled by the 7-judge bench in In re Interplay (13 Dec 2023). The list omits that."),
58:("P","B","Some decisions of this Court in the context of GST Acts which are contrary to the aforesaid ratio should not be treated as binding","3-judge bench on 2-judge decisions. 'Should not be treated as binding', not 'overruled'; the list itself hedges the label."),
59:("P","B","same sentence as row 58","Bharat Bhushan is an SLP order (SLP (Crl.) 8525/2024), not found in our collection as a judgment."),
}
out = SP.replace("scratchpad/", "scratchpad/") 
dst = "/home/user/recourse-sci-pool/external_lists/2026-10-07_overruled_after_2015_pdf/results.csv"
with open(dst, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["no", "earlier_case", "earlier_year_in_list", "later_case", "later_year_in_list", "later_judgment_in_collection", "verdict", "evidence", "court_words", "note"])
    cnt = collections.Counter()
    for n in range(1, 60):
        r = rows[n]; v = V[n]; cnt[v[0]] += 1
        w.writerow([n, r["a"], r["a_year"], r["b"], r["b_year"], BK[n], v[0], v[1], v[2], v[3]])
print(dict(cnt), sum(cnt.values()))
