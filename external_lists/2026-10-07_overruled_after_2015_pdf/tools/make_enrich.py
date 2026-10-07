"""Writes goodlaw/data/register/list2_enrich.json: for each of the 59 entries of the post-2015 list, the names, years, citations and treatment that the register stores, plus the sibling
decisions found in the same judgments. Citations are only ones I saw printed in the judgments' own tags and text (or built from the bucket key of a judgment: [year] volume S.C.R. page);
nothing is filled from memory. Run from the repo root: python3 -I external_lists/2026-10-07_overruled_after_2015_pdf/tools/make_enrich.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, "goodlaw", "data", "register", "list2_enrich.json")

# later judgments: key -> (name, year, date, bench, doc_key, cites, split)
B = {
    "PUTT": ("K.S. Puttaswamy (Retd.) v. Union of India", 2017, "2017-08-24", 9, "b2017_10_569_999", ["(2017) 10 SCC 1", "[2017] 10 S.C.R. 569"], None),
    "KKS": ("Krishna Kumar Singh v. State of Bihar", 2017, "2017-01-02", 5, "c44452", [], None),
    "HCC": ("State of Jharkhand v. Hindustan Construction Co. Ltd.", 2017, "2017-12-14", 5, "b2017_13_1009_1052", ["[2017] 13 S.C.R. 1009"], None),
    "DK": ("Commissioner of Customs v. Dilip Kumar & Co.", 2018, "2018-07-30", 5, "b2018_7_1191_1231", ["[2018] 7 S.C.R. 1191"], None),
    "NAV": ("Navtej Singh Johar v. Union of India", 2018, "2018-09-06", 5, "b2018_7_379_746", ["[2018] 7 S.C.R. 379"], None),
    "JS": ("Joseph Shine v. Union of India", 2018, "2018-09-27", 5, "b2018_11_765_950", ["[2018] 11 S.C.R. 765"], None),
    "NUS": ("Nusli Neville Wadia v. Ivory Properties", 2019, "2019-10-04", 3, "b2019_15_795_864", ["[2019] 15 S.C.R. 795"], None),
    "VI": ("Vijay Industries v. Commissioner of Income Tax", 2019, "2019-03-01", 3, "b2019_4_928_944", ["[2019] 4 S.C.R. 928"], None),
    "VIN": ("Vinubhai Haribhai Malaviya v. State of Gujarat", 2019, "2019-10-16", 3, "b2019_15_936_989", ["[2019] 15 S.C.R. 936"], None),
    "RKG": ("Ravinder Kaur Grewal v. Manjit Kaur", 2019, "2019-08-07", 3, "b2019_11_74_134", ["[2019] 11 S.C.R. 74"], None),
    "SA": ("Sushila Aggarwal v. State (NCT of Delhi)", 2020, "2020-01-29", 5, "b2020_2_1_131", ["[2020] 2 S.C.R. 1"], None),
    "APK": ("Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal", 2020, "2020-07-14", 3, "b2020_7_180_282", ["[2020] 7 S.C.R. 180"], None),
    "MS": ("Mukesh Singh v. State (Narcotic Branch of Delhi)", 2020, "2020-08-31", 5, "b2020_9_245_302", ["[2020] 9 S.C.R. 245"], None),
    "VS": ("Vineeta Sharma v. Rakesh Sharma", 2020, "2020-08-11", 3, "b2020_10_135_237", ["[2020] 10 S.C.R. 135"], None),
    "VD": ("Vidya Drolia v. Durga Trading Corporation", 2020, "2020-12-14", 3, "b2020_11_1001_1180", ["[2020] 11 S.C.R. 1001"], None),
    "VK": ("Vikash Kumar v. Union Public Service Commission", 2021, "2021-02-11", 3, "b2021_12_311_364", ["[2021] 12 S.C.R. 311"], None),
    "BB": ("Government of Maharashtra v. Borse Brothers Engineers & Contractors", 2021, "2021-03-19", 3, "b2021_3_193_254", ["[2021] 3 S.C.R. 193"], None),
    "IDA": ("Indore Development Authority v. Manoharlal", 2020, "2020-03-06", 5, "b2020_3_1_328", ["(2020) 8 SCC 129", "[2020] 3 S.C.R. 1"], None),
    "PD": ("Union of India v. Parshotam Dass", 2023, None, None, None, [], None),
    "AB": ("Arup Bhuyan v. State of Assam", 2023, "2023-03-24", 3, "b2023_8_496_580", ["[2023] 8 S.C.R. 496"], None),
    "UNI": ("Unicorn Industries v. Union of India", 2019, "2019-12-06", 3, "b2019_17_1013_1047", ["[2019] 17 S.C.R. 1013"], None),
    "AMU": ("Aligarh Muslim University v. Naresh Agarwal", 2024, "2024-11-08", 7, "b2024_11_1647_2038", ["[2024] 11 S.C.R. 1647"],
            "Four judges (the Chief Justice's opinion) overruled the view; Surya Kant J, Datta J and Sharma J wrote separately and did not join the overruling. AMU's own minority status was left to a regular bench."),
    "DS": ("State of Punjab v. Davinder Singh", 2024, "2024-08-01", 7, "b2024_8_1321_1672", ["[2024] 8 S.C.R. 1321"], "6:1 (Trivedi J dissenting)"),
    "MADA": ("Mineral Area Development Authority v. Steel Authority of India", 2024, "2024-07-25", 9, "b2024_7_1549_1846", ["[2024] 7 S.C.R. 1549"], "8:1 (Nagarathna J dissenting)"),
    "LPV": ("State of U.P. v. Lalta Prasad Vaish & Sons", 2024, "2024-10-23", 9, "b2024_10_1931_2182", ["[2024] 10 S.C.R. 1931"], "8:1 (Nagarathna J dissenting)"),
    "HCBA": ("High Court Bar Association, Allahabad v. State of U.P.", 2024, "2024-02-29", 5, "b2024_2_946_988", ["[2024] 2 S.C.R. 946"], None),
    "RD": ("Bajaj Allianz General Insurance Co. Ltd. v. Rambha Devi", 2024, "2024-11-06", 5, "b2024_11_541_640", ["[2024] 11 S.C.R. 541"], None),
    "NNG2": ("N.N. Global Mercantile Pvt. Ltd. v. Indo Unique Flame Ltd.", 2023, "2023-04-25", 5, "b2023_9_285_492", ["(2023) 7 SCC 1", "[2023] 9 S.C.R. 285"],
             "3:2 (Rastogi J and Roy J dissenting)"),
    "RA": ("Radhika Agarwal v. Union of India", 2025, "2025-02-27", 3, "b2025_2_1331_1395", ["[2025] 2 S.C.R. 1331"], None),
    "INT": ("In re: Interplay between Arbitration Agreements under the Arbitration and Conciliation Act 1996 and the Indian Stamp Act 1899", 2023, "2023-12-13", 7, "b2023_15_1081_1212",
            ["[2023] 15 S.C.R. 1081"], None),
    "MD": ("Mukund Dewangan v. Oriental Insurance Co. Ltd.", 2017, "2017-07-03", 3, "b2017_7_765_822", ["(2017) 14 SCC 663", "[2017] 7 S.C.R. 765"], None),
    "SHA": ("Indore Development Authority v. Shailendra (Dead) through LRs.", 2018, "2018-02-08", 3, "b2018_2_1_231", ["[2018] 2 S.C.R. 1"], None),
    "ML18": ("Mohanlal v. State of Punjab", 2018, "2018-08-16", 3, "b2018_9_1006_1023", ["(2018) 17 SCC 627", "[2018] 9 S.C.R. 1006"], None),
    "TS": ("Tofan Singh v. State of Tamil Nadu", 2020, "2020-10-29", 3, "b2020_12_583_874", ["[2020] 12 S.C.R. 583"], None),
}

# entries: no -> dict(a_name, [alts], years, cites, B key, treatment, scope, basis, ref, flags, extra)
A = {
    1: ("M.P. Sharma v. Satish Chandra", [], 1954, [1954], ["[1954] SCR 1077", "AIR 1954 SC 300"], "PUTT", "overruled", "the holding that the right to privacy is not protected by the Constitution", "H+B"),
    2: ("Kharak Singh v. State of U.P.", [], 1963, [1962, 1963], ["AIR 1963 SC 1295", "(1964) 1 SCR 332"], "PUTT", "overruled_in_part", "only the holding that privacy is not a protected right; the first part of the decision stands", "H+B"),
    3: ("A.D.M. Jabalpur v. Shivkant Shukla", ["ADM Jabalpur v. Shivakant Shukla"], 1976, [1976], ["(1976) 2 SCC 521", "[1976] Suppl. SCR 172", "AIR 1976 SC 1207"], "PUTT", "overruled", None, "H+B"),
    4: ("Bhupendra Kumar Bose v. State of Orissa", ["State of Orissa v. Bhupendra Kumar Bose"], 1962, [1962], ["1962 Supp (2) SCR 380"], "KKS", "overruled_in_part", "the 'enduring rights' theory for ordinances", "B"),
    5: ("T. Venkata Reddy v. State of A.P.", ["T. Venkata Reddy v. State of Andhra Pradesh"], 1985, [1985], ["(1985) 3 SCC 198"], "KKS", "overruled_in_part", "the 'enduring rights' theory for ordinances", "B"),
    6: ("State of M.P. v. Saith & Skelton (P) Ltd.", ["State of Madhya Pradesh v. Saith and Skelton (P) Ltd."], 1972, [1972], ["(1972) 1 SCC 702", "[1972] 3 SCR 233"], "HCC", "overruled", "the view that a superior court that appoints the arbitrator keeps jurisdiction over later arbitration proceedings", "B"),
    7: ("Guru Nanak Foundation v. Rattan Singh & Sons", ["Guru Nanak Foundation v. Rattan Singh and Sons"], 1981, [1981, 1982], ["[1982] 1 SCR 842"], "HCC", "overruled", "the view that a superior court that appoints the arbitrator keeps jurisdiction over later arbitration proceedings", "B"),
    8: ("Sun Export Corporation v. Collector of Customs", ["Sun Export Corporation, Bombay v. Collector of Customs, Bombay"], 1997, [1997], ["(1997) 6 SCC 564", "[1997] 1 Suppl. SCR 434"], "DK", "overruled", "benefit of ambiguity in an exemption notification goes to the Revenue", "H+B"),
    9: ("Suresh Kumar Koushal v. Naz Foundation", ["Suresh Kumar Koushal and Another v. Naz Foundation and Others"], 2013, [2013, 2014], ["(2014) 1 SCC 1", "[2013] 17 SCR 1019"], "NAV", "overruled", None, "H+B"),
    10: ("Sowmithri Vishnu v. Union of India", [], 1985, [1985], ["(1985) Supp SCC 137", "[1985] Suppl. SCR 741"], "JS", "overruled", None, "B"),
    11: ("V. Revathi v. Union of India", ["V Revathi v. Union of India"], 1988, [1988], ["(1988) 2 SCC 72", "[1988] 3 SCR 73"], "JS", "overruled", None, "B"),
    12: ("W. Kalyani v. State", ["W. Kalyani v. State through Inspector of Police"], 2012, [2012], ["(2012) 1 SCC 358"], "JS", "overruled", None, "B"),
    13: ("Foreshore Cooperative Housing Society Ltd. v. Praveen D. Desai", ["Foreshore Cooperative Housing Society Limited v. Praveen D. Desai"], 2015, [2015], ["(2015) 6 SCC 412", "[2015] 5 SCR 1075"], "NUS", "not_good_law", "section 9A CPC (Maharashtra): limitation as a preliminary issue", "B"),
    14: ("Motilal Pesticides (I) Pvt. Ltd. v. CIT", ["Motilal Pesticides (I) Pvt. Ltd. v. Commissioner of Income Tax"], 2000, [2000], ["(2000) 9 SCC 63"], "VI", "overruled", "section 80HH deduction computed on gross profits", "B"),
    15: ("Amrutbhai Shambhubhai Patel v. Sumanbhai Kantibhai Patel", ["Amrutbhai Shambubhai Patel v. Sumanbhai Kantibai Patel"], 2017, [2017], ["(2017) 4 SCC 177", "[2017] 4 SCR 105"], "VIN", "overruled_in_part", "to the extent it held the contrary to Vinubhai", "B"),
    16: ("Athul Rao v. State of Karnataka", [], 2018, [2018], ["(2018) 14 SCC 298"], "VIN", "overruled_in_part", "to the extent it held the contrary to Vinubhai", "B"),
    17: ("Bikash Ranjan Rout v. State (NCT of Delhi)", ["Bikash Ranjan Rout v. State through the Secretary (Home), Government of NCT of Delhi"], 2019, [2019], ["(2019) 5 SCC 542"], "VIN", "overruled_in_part", "to the extent it held the contrary to Vinubhai", "B"),
    18: ("Randhir Singh Rana v. State (Delhi Administration)", ["Randhir Singh Rana v. The State Being the Delhi Administration"], 1997, [1996, 1997], ["(1997) 1 SCC 361", "[1996] 10 Suppl. SCR 880", "AIR 1997 SC 639"], "VIN", "overruled", None, "B"),
    19: ("Reeta Nag v. State of West Bengal", [], 2009, [2009], ["(2009) 9 SCC 129", "[2009] 13 SCR 276"], "VIN", "overruled", None, "B"),
    20: ("Gurdwara Sahib v. Gram Panchayat Village Sirthala", ["Gurudwara Sahab v. Gram Panchayat Village Sirthala"], 2014, [2014], ["(2014) 1 SCC 669"], "RKG", "overruled", "adverse possession cannot be pleaded by a plaintiff under Article 65 of the Limitation Act", "B"),
    21: ("State of Uttarakhand v. Mandir Sri Laxman Sidh Maharaj", ["State of Uttarakhand v. Mandir Shri Lakshmi Siddh Maharaj"], 2017, [2017], ["(2017) 9 SCC 579", "[2017] 14 SCR 257"], "RKG", "overruled", "adverse possession cannot be pleaded by a plaintiff under Article 65 of the Limitation Act", "B"),
    22: ("Dharampal (dead) through LRs v. Punjab Wakf Board", ["Dharampal (Dead) through LRs v. Punjab Wakf Board"], 2017, [2017, 2018], ["(2018) 11 SCC 449", "[2017] 8 SCR 316"], "RKG", "overruled", "adverse possession cannot be pleaded by a plaintiff under Article 65 of the Limitation Act", "B"),
    23: ("Salauddin Abdulsamad Shaikh v. State of Maharashtra", [], 1996, [1995, 1996], ["(1996) 1 SCC 667", "[1995] 6 Suppl. SCR 556"], "SA", "overruled", "the view that anticipatory bail must end after a fixed period", "B"),
    24: ("K.L. Verma v. State", ["K.L. Verma v. State and another"], 1998, [1998], ["(1998) 9 SCC 348", "(1998) 8 JT 521"], "SA", "overruled", "the view that anticipatory bail must end after a fixed period", "B"),
    25: ("Sunita Devi v. State of Bihar", [], 2005, [2004, 2005], ["(2005) 1 SCC 608", "[2004] 6 Suppl. SCR 707"], "SA", "overruled", "the view that anticipatory bail must end after a fixed period", "B"),
    26: ("Adri Dharan Das v. State of West Bengal", [], 2005, [2005], ["(2005) 4 SCC 303", "[2005] 2 SCR 188"], "SA", "overruled", "the view that anticipatory bail must end after a fixed period", "B"),
    27: ("Nirmal Jeet Kaur v. State of M.P.", ["Nirmal Jeet Kaur v. State of Madhya Pradesh"], 2004, [2004], ["(2004) 7 SCC 558", "[2004] 3 Suppl. SCR 1006"], "SA", "overruled", "the view that anticipatory bail must end after a fixed period", "B"),
    28: ("HDFC Bank Ltd. v. J.J. Mannan", ["HDFC Bank Limited v. J.J. Mannan"], 2010, [2009, 2010], ["(2010) 1 SCC 679", "[2009] 16 SCR 590"], "SA", "overruled", "the view that anticipatory bail must end after a fixed period", "B"),
    29: ("Satpal Singh v. State of Punjab", ["Satpal Singh v. the State of Punjab"], 2018, [2018], ["(2018) 4 SCC 303", "[2018] 3 SCR 739"], "SA", "overruled", "the view that anticipatory bail must end after a fixed period", "B"),
    30: ("Naresh Kumar Yadav v. Ravindra Kumar", [], 2008, [2007, 2008], ["(2008) 1 SCC 632", "[2007] 11 SCR 615"], "SA", "overruled", "the view that anticipatory bail must end after a fixed period", "B"),
    31: ("Siddharam Satlingappa Mhetre v. State of Maharashtra", [], 2011, [2010, 2011], ["(2011) 1 SCC 694", "[2010] 15 SCR 201"], "SA", "overruled_in_part", "the view that no restrictive conditions at all can be imposed on anticipatory bail", "B"),
    32: ("Shafhi Mohammad v. State of Himachal Pradesh", ["Shafhi Mohammad v. State of H.P."], 2018, [2018], ["(2018) 5 SCC 311", "[2018] 3 SCR 1096"], "APK", "overruled", "the view that a section 65B(4) certificate can be dispensed with where the party cannot produce one", "B"),
    33: ("Tomaso Bruno v. State of U.P.", ["Tomaso Bruno and Anr. v. State of Uttar Pradesh"], 2015, [2015], ["(2015) 7 SCC 178", "[2015] 1 SCR 721"], "APK", "overruled", "secondary evidence of electronic records (CCTV footage) under section 65 of the Evidence Act", "H+B"),
    34: ("Mohan Lal v. State of Punjab", ["Mohanlal v. State of Punjab"], 2018, [2018], ["(2018) 17 SCC 627", "[2018] 9 SCR 1006"], "MS", "overruled", "the informant who is also the investigator: acquittal is not automatic", "H+B"),
    35: ("Prakash v. Phulavati", ["Prakash & Ors. v. Phulavati & Ors."], 2016, [2015, 2016], ["(2016) 2 SCC 36", "[2015] 12 SCR 579"], "VS", "overruled", "daughters' rights under section 6 of the Hindu Succession Act: only living daughters of living coparceners", "B"),
    36: ("Mangammal v. T.B. Raju", ["Mangammal v. T.B. Raju & Ors."], 2018, [2018], ["(2018) 15 SCC 662", "[2018] 6 SCR 776"], "VS", "overruled", "daughters' rights under section 6 of the Hindu Succession Act", "B"),
    37: ("Danamma @ Suman Surpur v. Amar", ["Danamma @ Suman Surpur & Anr. v. Amar & Ors."], 2018, [2018], ["(2018) 3 SCC 343", "[2018] 2 SCR 553"], "VS", "overruled_in_part", "to the extent contrary to Vineeta Sharma", "B"),
    38: ("Himangni Enterprises v. Kamaljeet Singh Ahluwalia", [], 2017, [2017], ["(2017) 10 SCC 706", "[2017] 10 SCR 139"], "VD", "overruled", "the holding that landlord-tenant disputes under the Transfer of Property Act are not arbitrable", "B"),
    39: ("V. Surendra Mohan v. State of Tamil Nadu", ["V Surendra Mohan v. State of Tamil Nadu"], 2019, [2019], ["(2019) 4 SCC 237", "[2019] 1 SCR 954"], "VK", "not_binding", "after the RPwD Act 2016, as a decision under the 1995 Act without a reasonable-accommodation analysis", "B"),
    40: ("M/s N.V. International v. State of Assam", ["N.V. International v. State of Assam"], 2020, [2020], ["(2020) 2 SCC 109"], "BB", "overruled", "the rule that delay beyond 120 days cannot be condoned in a section 37 appeal", "B"),
    41: ("Pune Municipal Corporation v. Harakchand Misirimal Solanki", ["Pune Municipal Corporation & Anr. v. Harakchand Misrimal Solanki & Ors."], 2014, [2014], ["(2014) 3 SCC 183", "[2014] 1 SCR 783"], "IDA", "overruled", "the reading of section 24(2) of the 2013 Act on lapse of acquisition", "B"),
    42: ("Sree Balaji Nagar Residential Association v. State of Tamil Nadu", ["Sree Balaji Nagar Residents Association v. State of Tamil Nadu", "Shree Balaji Nagar Residential Association v. State of Tamil Nadu"], 2015, [2014, 2015], ["(2015) 3 SCC 353", "[2014] 7 SCR 799"], "IDA", "overruled", "the reading of section 24(2) of the 2013 Act on lapse of acquisition", "B"),
    43: ("Union of India v. Major General Shri Kant Sharma", [], 2015, [2015], [], "PD", "overruled", None, "-"),
    44: ("Arup Bhuyan v. State of Assam", ["Arup Bhuyan v. Union of India"], 2011, [2011], ["(2011) 3 SCC 377", "[2011] 2 SCR 506"], "AB", "not_good_law", "mere membership of a banned organisation (section 10(a)(i) UAPA)", "H"),
    45: ("Indra Das v. State of Assam", ["Sri Indra Das v. State of Assam"], 2011, [2011], ["(2011) 3 SCC 380", "[2011] 4 SCR 289"], "AB", "not_good_law", "mere membership of a banned organisation (section 10(a)(i) UAPA)", "H"),
    46: ("State of Kerala v. Raneef", [], 2011, [2011], ["(2011) 1 SCC 784", "[2011] 1 SCR 590"], "AB", "not_good_law", "mere membership of a banned organisation (section 10(a)(i) UAPA)", "H"),
    47: ("SRD Nutrients (P) Ltd. v. CCE", ["SRD Nutrients Private Limited v. Commissioner of Central Excise, Guwahati"], 2018, [2017, 2018], ["(2018) 1 SCC 105", "[2017] 11 SCR 43"], "UNI", "per_incuriam", "the view that an exemption from excise duty also exempts education cess", "B"),
    48: ("S. Azeez Basha v. Union of India", ["S Azeez Basha v. Union of India"], 1967, [1967, 1968], ["[1968] 1 SCR 833", "AIR 1968 SC 662"], "AMU", "overruled", "the view that an educational institution is not established by a minority if it derives its legal character from a statute", "B"),
    49: ("E.V. Chinnaiah v. State of Andhra Pradesh", ["EV Chinnaiah v. State of Andhra Pradesh"], 2005, [2004, 2005], ["[2004] Supp. 5 SCR 972", "(2005) 1 SCC 394"], "DS", "overruled", "the holding that sub-classification of the Scheduled Castes is impermissible", "B"),
    50: ("India Cement Ltd. v. State of Tamil Nadu", [], 1990, [1989, 1990], ["[1989] Supp. 1 SCR 692", "(1990) 1 SCC 12", "AIR 1990 SC 85"], "MADA", "overruled_in_part", "to the extent of the observations made in the present case; India Cement had held royalty to be a tax", "B"),
    51: ("Synthetics & Chemicals Ltd. v. State of U.P.", ["Synthetics and Chemicals Ltd. v. State of U.P."], 1990, [1989, 1990], ["[1989] Supp. 1 SCR 623", "(1990) 1 SCC 109", "AIR 1990 SC 1927"], "LPV", "overruled", None, "B"),
    52: ("Asian Resurfacing of Road Agency Pvt. Ltd. v. CBI", ["Asian Resurfacing of Road Agency Private Limited v. Central Bureau of Investigation"], 2018, [2018], ["[2018] 2 S.C.R. 1045"], "HCBA", "not_approved", "directions in paragraphs 36 and 37 (automatic vacation of stay; day-to-day hearing); the rest of the judgment stands", "B"),
    53: ("New India Assurance Co. Ltd. v. Prabhu Lal", ["New India Assurance Company v. Prabhu Lal"], 2008, [2007, 2008], ["[2007] 12 SCR 724", "(2008) 1 SCC 696"], "RD", "overruled", "the view that a light motor vehicle licence holder needs a separate endorsement to drive a transport vehicle", "B"),
    54: ("New India Assurance Co. Ltd. v. Roshanben Rahemansha Fakir", [], 2008, [2008], ["[2008] 8 SCR 328", "(2008) 8 SCC 253"], "RD", "overruled", "the view that a light motor vehicle licence holder needs a separate endorsement to drive a transport vehicle", "B"),
    55: ("Oriental Insurance Co. Ltd. v. Angad Kol", [], 2009, [2009], ["[2009] 2 SCR 695", "(2009) 11 SCC 356"], "RD", "overruled", "the view that a light motor vehicle licence holder needs a separate endorsement to drive a transport vehicle", "B"),
    56: ("National Insurance Co. Ltd. v. Annappa Irappa Nesaria", ["National Insurance Co. Ltd. v. Annappa Irappa"], 2008, [2008], ["[2008] 1 SCR 1061", "(2008) 3 SCC 464"], "RD", "overruled_in_part", "the view taken on the position after the 1994 amendment", "B"),
    57: ("N.N. Global Mercantile Pvt. Ltd. v. Indo Unique Flame Ltd.", [], 2021, [2021], ["(2021) 4 SCC 379", "[2021] 4 S.C.R. 933"], "NNG2", "overruled", "arbitration agreement in an unstamped instrument", "B"),
    58: ("State of Gujarat v. Choodamani Parmeshwaran Iyer", ["State of Gujarat v. Choodamani Parmeshwaran Iyer and Another"], 2023, [2023], ["[2023] 8 SCR 1139", "2023 SCC OnLine SC 1043"], "RA", "not_binding", "GST decisions contrary to the anticipatory-bail ratio of Sushila Aggarwal", "B"),
    59: ("Bharat Bhushan v. Director General of GST Intelligence", ["Bharat Bhushan v. Director General of GST Intelligence, Nagpur Zonal Unit"], 2024, [2024], [], "RA", "not_binding", "GST decisions contrary to the anticipatory-bail ratio of Sushila Aggarwal; an SLP order (SLP (Crl.) No. 8525/2024)", "B"),
}
FLAGS = {42: ["overruling_case_corrected"], 39: ["list_label_not_supported"], 43: ["not_in_collection"], 33: ["same_strength_bench"], 59: ["order_not_judgment"]}

# sibling decisions: id -> (A name, alts, year, years, cites, court, B key, treatment, scope, court_words, basis, note)
SIB = {
    "D2-BHANUDAS": ("Union of India v. Bhanudas Krishna Gawde", [], 1977, [1977], ["(1977) 1 SCC 834", "[1977] 2 SCR 719"], "SC", "PUTT", "overruled", "followed ADM Jabalpur", "We also overrule the decision in Union of India v Bhanudas Krishna Gawde, which followed ADM Jabalpur", "B", "Omitted by list 2; same judgment as rows 1 to 3."),
    "D2-PRABHULAL-2017": ("New India Assurance Co. Ltd. v. Prabhu Lal", ["New India Assurance Company v. Prabhu Lal"], 2008, [2007, 2008], ["[2007] 12 SCR 724", "(2008) 1 SCC 696"], "SC", "MD", "overruled", "the view that a light motor vehicle licence holder needs a separate endorsement to drive a transport vehicle", "the decision in Prabhu Lal does not lay down correct proposition of law and is hereby overruled", "B", "First overruling (3 judges, 2017); the 5-judge bench of 2024 overruled it again (row 53). Found by a scan; not in list 2."),
    "D2-SREEBALAJI-2018": ("Sree Balaji Nagar Residential Association v. State of Tamil Nadu", ["Sree Balaji Nagar Residents Association v. State of Tamil Nadu", "Shree Balaji Nagar Residential Association v. State of Tamil Nadu"], 2015, [2014, 2015], ["(2015) 3 SCC 353", "[2014] 7 SCR 799"], "SC", "SHA", "overruled", "the reading of section 24(2) of the 2013 Act on lapse of acquisition", "The decision in Shree Balaji (supra) cannot be said to be laying down good law, is overruled", "B", "First overruling (3 judges, 2018); the 5-judge bench of 2020 overruled it again (row 42). Shailendra's own treatment of the proviso to section 24(2) was later said by the 5-judge bench not to have been argued (check its status). Found by a scan; not in list 2."),
    "D2-KADER": ("Kader v. State of Kerala", [], 2001, [2001], ["2001 CriLJ 4044"], "HC", "ML18", "overruled", "an informant who is also the investigator under the NDPS Act", "The view taken by the Kerala High Court in Kader does not meet our approval", "B", "A High Court decision (Division Bench). Found in the same judgment as row 34."),
    "D2-ORISSACEMENT": ("Orissa Cement Ltd. v. State of Orissa", [], 1991, [1991], ["[1991] 2 SCR 105", "(1991) Supp 1 SCC 430"], "SC", "MADA", "overruled_in_part", "to the extent of the observations made in the present case", "overruled to the extent of the observations made in the present case", "B", "One of six decisions overruled in the same paragraph as India Cement (row 50); list 2 names only India Cement."),
    "D2-FEDMINING": ("Federation of Mining Associations of Rajasthan v. State of Rajasthan", [], 1992, [1992], ["(1992) Supp 2 SCC 239"], "SC", "MADA", "overruled_in_part", "to the extent of the observations made in the present case", "overruled to the extent of the observations made in the present case", "B", "As above."),
    "D2-MAHALAXMI": ("State of M.P. v. Mahalaxmi Fabric Mills Ltd.", ["State of Madhya Pradesh v. Mahalaxmi Fabric Mills Ltd."], 1995, [1995], ["[1995] 1 SCR 756", "(1995) Supp 1 SCC 642"], "SC", "MADA", "overruled_in_part", "to the extent of the observations made in the present case", "overruled to the extent of the observations made in the present case", "B", "As above."),
    "D2-SAURASHTRA": ("Saurashtra Cement & Chemical Industries Ltd. v. Union of India", ["Saurashtra Cement and Chemical Industries Ltd. v. Union of India"], 2000, [2000, 2001], ["[2000] Supp. 4 SCR 44", "(2001) 1 SCC 91"], "SC", "MADA", "overruled_in_part", "to the extent of the observations made in the present case", "overruled to the extent of the observations made in the present case", "B", "As above."),
    "D2-MAHANADI-1995": ("State of Orissa v. Mahanadi Coalfields Ltd.", [], 1995, [1995], ["[1995] 3 SCR 639", "(1995) Supp 2 SCC 686"], "SC", "MADA", "overruled_in_part", "to the extent of the observations made in the present case", "overruled to the extent of the observations made in the present case", "B", "As above."),
    "D2-KANNADASAN": ("P. Kannadasan v. State of Tamil Nadu", ["P Kannadasan v. State of Tamil Nadu"], 1996, [1996], ["[1996] Supp. 4 SCR 92", "(1996) 5 SCC 670"], "SC", "MADA", "overruled_in_part", "to the extent of the observations made in the present case", "overruled to the extent of the observations made in the present case", "B", "As above."),
    "D2-DEVARAPALLI": ("Devarapalli Lakshminarayana Reddy v. V. Narayana Reddy", ["Devarapalli Lakshminarayana Reddy & Ors. v. V. Narayana Reddy & Ors."], 1976, [1976], ["(1976) 3 SCC 252", "[1976] Suppl. SCR 524"], "SC", "VIN", "not_good_law", "the statement of the law in paragraph 17 (section 156(3) CrPC investigation is pre-cognizance only)", "the statement of the law contained in paragraph 17 in Devarapalli Lakshminarayana Reddy cannot be relied upon", "B", "A 3-judge decision disapproved by a 3-judge bench: lawyer to confirm. Omitted by list 2; same judgment as rows 15 to 19."),
    "D2-BHADRESH": ("Bhadresh Bipinbhai Sheth v. State of Gujarat", ["Bhadresh Bipinbhai Sheth v. State of Gujarat & Anr"], 2016, [2015, 2016], ["(2016) 1 SCC 152", "[2015] 10 SCR 398"], "SC", "SA", "overruled", "the view that no restrictive conditions at all can be imposed on anticipatory bail", "Bhadresh Bipinbhai Sheth ... - overruled (the report's case-law list for one opinion); the judgment orders 'Mhetre (and other similar decisions)' overruled", "H", "Law-report tag only; the body names Mhetre and 'other similar decisions'. Omitted by list 2."),
    "D2-NRADHAKRISHNAN": ("N. Radhakrishnan v. Maestro Engineers", ["N. Radhakrishnan v. Maestro Engineers and Others"], 2010, [2009, 2010], ["(2010) 1 SCC 72", "[2009] 15 SCR 371"], "SC", "VD", "overruled", "allegations of fraud make a dispute non-arbitrable", "we overrule the ratio in N. Radhakrishnan inter alia observing that allegations of fraud can be made a subject matter of arbitration when they relate to a civil dispute", "B", "Omitted by list 2; same judgment as row 38."),
    "D2-KARWAL": ("Raj Kumar Karwal v. Union of India", [], 1990, [1990], ["(1990) 2 SCC 409", "[1990] 2 SCR 63"], "SC", "TS", "overruled", "a statement under section 67 of the NDPS Act as a confession", "Raj Kumar Karwal ... overruled (the report's case-law list, Para 128)", "H", "Law-report tag only. Tofan Singh (2020, 3 judges) is not on list 2."),
    "D2-KANHAIYALAL": ("Kanhaiyalal v. Union of India", [], 2008, [2008], ["(2008) 4 SCC 668", "[2008] 1 SCR 350"], "SC", "TS", "overruled", "a statement under section 67 of the NDPS Act as a confession", "Kanhaiyalal ... overruled (the report's case-law list, Para 153)", "H", "As above."),
    "D2-NNG2": ("N.N. Global Mercantile Pvt. Ltd. v. Indo Unique Flame Ltd.", [], 2023, [2023], ["(2023) 7 SCC 1", "[2023] 9 S.C.R. 285"], "SC", "INT", "overruled", "arbitration agreement in an unstamped instrument", "The decision in NN Global 2 and SMS Tea Estates are overruled", "B", "The 5-judge Constitution Bench of April 2023 (row 57's overruling case) overruled by the 7-judge bench of December 2023."),
    "D2-SMSTEA": ("SMS Tea Estates Private Limited v. Chandmari Tea Company Private Limited", ["SMS Tea Estates (P) Ltd. v. Chandmari Tea Co. (P) Ltd"], 2011, [2011], ["(2011) 14 SCC 66", "[2011] 9 SCR 382"], "SC", "INT", "overruled", "arbitration agreement in an unstamped instrument", "The decision in NN Global 2 and SMS Tea Estates are overruled", "B", "The 2023 Constitution Bench majority affirmed SMS Tea Estates; the 7-judge bench overruled it."),
    "D2-GARWARE": ("Garware Wall Ropes Limited v. Coastal Marine Constructions & Engineering Limited", ["Garware Wall Ropes Ltd. v. Coastal Marine Constructions & Engg. Ltd."], 2019, [2019], ["(2019) 9 SCC 209", "[2019] 5 SCR 579"], "SC", "INT", "overruled_in_part", "paragraphs 22 and 29 only", "Paragraphs 22 and 29 of Garware Wall Ropes are overruled to that extent", "B", "As above."),
}


def build():
    entries = {}
    for no, (name, alts, yr, yrs, cites, bk, treat, scope, basis) in A.items():
        bn, by, bdate, bbench, bdoc, bcites, split = B[bk]
        e = {"a_name": name, "a_alt_names": alts, "a_year": yr, "a_years": yrs, "a_cites": cites, "b_name": bn, "b_year": by, "b_date": bdate, "b_bench": bbench, "b_doc_key": bdoc, "b_cites": bcites,
             "treatment": treat, "scope": scope, "evidence_basis": basis, "evidence_ref": bdoc or "later judgment not in the collection", "flags": FLAGS.get(no, [])}
        if split:
            e["split"] = split
        entries[str(no)] = e
    sibs = {}
    for sid, (name, alts, yr, yrs, cites, court, bk, treat, scope, words, basis, note) in SIB.items():
        bn, by, bdate, bbench, bdoc, bcites, split = B[bk]
        e = {"a_name": name, "a_alt_names": alts, "a_year": yr, "a_years": yrs, "a_cites": cites, "a_court": court, "b_name": bn, "b_year": by, "b_date": bdate, "b_bench": bbench, "b_doc_key": bdoc,
             "b_cites": bcites, "treatment": treat, "scope": scope, "court_words": words, "evidence_basis": basis, "evidence_ref": bdoc, "flags": [], "note": note}
        if split:
            e["split"] = split
        sibs[sid] = e
    return {"note": "Generated by external_lists/2026-10-07_overruled_after_2015_pdf/tools/make_enrich.py. Citations are only ones printed in the judgments or built from bucket keys.", "entries": entries, "siblings": sibs}


if __name__ == "__main__":
    d = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(len(d["entries"]), "entries,", len(d["siblings"]), "siblings ->", OUT)
