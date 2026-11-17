"""HELD-OUT TARGET LIST for the name-reader fix (written 2026-11-17 BEFORE any count was run, and before the reader was changed).
Each target: (label, regex for the first party, regex for the second party, year, [phrase queries for the full-text search: a judgment 'names the case' if its text matches ANY of them]).
The earlier diagnosis cases (Gunmala, S.M.S., HDFC Bank, K.K. Ahuja, Aneeta Hada, Kamalkishor, Bridgestone, Dashrath Rupsingh, Sunita Palita, Damodar Prabhu, Jai Balaji) are NOT here: the fix was designed on them.
Group 'company' = a party name with Ltd / Pvt / Limited / Private / Corporation / Co (the class the old reader lost); group 'control' = ordinary personal or State names (the fix must not lose or invent them).
These are Claude's picks from memory of Indian criminal and quasi-criminal law, not a lawyer's, and the index may not hold every one: a target the names table does not hold is dropped and reported."""
TARGETS = [
 # company-named
 ("Pepsi Foods Ltd v. Special Judicial Magistrate", r"pepsi foods", r"special judicial", 1998, ['"Pepsi Foods" AND "Special Judicial Magistrate"']),
 ("Standard Chartered Bank v. Directorate of Enforcement", r"standard chartered", r"directorate of enforcement", 2005, ['"Standard Chartered Bank" AND "Directorate of Enforcement"']),
 ("Iridium India Telecom Ltd v. Motorola Inc", r"iridium", r"motorola", 2011, ['"Iridium India Telecom" AND "Motorola"']),
 ("Anil Hada v. Indian Acrylic Ltd", r"anil hada", r"indian acrylic", 2000, ['"Anil Hada" AND "Indian Acrylic"']),
 ("Bhaskar Industries Ltd v. Bhiwani Denim & Apparels Ltd", r"bhaskar industries", r"bhiwani denim", 2001, ['"Bhaskar Industries" AND "Bhiwani Denim"']),
 ("Kusum Ingots & Alloys Ltd v. Pennar Peterson Securities Ltd", r"kusum ingots", r"pennar peterson", 2000, ['"Kusum Ingots" AND "Pennar Peterson"']),
 ("Modi Cements Ltd v. Kuchil Kumar Nandi", r"modi cements", r"kuchil kumar", 1998, ['"Modi Cements" AND "Kuchil Kumar"']),
 ("Electronics Trade & Technology Development Corporation Ltd v. Indian Technologists & Engineers", r"electronics trade", r"indian technologists", 1996, ['"Electronics Trade" AND "Indian Technologists"']),
 ("Central Bank of India v. Saxons Farms", r"central bank of india", r"saxons farms", 1999, ['"Saxons Farms"']),
 ("Dalmia Cement (Bharat) Ltd v. Galaxy Traders & Agencies Ltd", r"dalmia cement", r"galaxy traders", 2001, ['"Dalmia Cement" AND "Galaxy Traders"']),
 ("National Small Industries Corporation Ltd v. Harmeet Singh Paintal", r"national small industries", r"harmeet singh paintal", 2010, ['"Harmeet Singh Paintal"']),
 ("M.M.T.C. Ltd v. Medchl Chemicals & Pharma (P) Ltd", r"m\.?m\.?t\.?c", r"medchl", 2002, ['"Medchl Chemicals"']),
 ("Indian Oil Corporation v. NEPC India Ltd", r"indian oil corporation", r"nepc", 2006, ['"Indian Oil Corporation" AND "NEPC India"']),
 ("Trisuns Chemical Industry v. Rajesh Agarwal", r"trisuns chemical", r"rajesh agarwal", 1999, ['"Trisuns Chemical"']),
 ("Thermax Ltd v. K.M. Johny", r"thermax", r"johny", 2011, ['"Thermax" AND "Johny"']),
 ("HMT Watches Ltd v. M.A. Abida", r"hmt watches", r"abida", 2015, ['"HMT Watches" AND "Abida"']),
 ("Union Carbide Corporation v. Union of India", r"union carbide corporation", r"union of india", 1991, ['"Union Carbide Corporation" AND "Union of India"']),
 ("Alpic Finance Ltd v. P. Sadasivan", r"alpic finance", r"sadasivan", 2001, ['"Alpic Finance"']),
 ("Meters and Instruments Private Limited v. Kanchan Mehta", r"meters and instruments", r"kanchan mehta", 2018, ['"Meters and Instruments"']),
 ("Rahul Builders v. Arihant Fertilizers & Chemicals", r"rahul builders", r"arihant fertilizers", 2008, ['"Rahul Builders" AND "Arihant"']),
 ("Prem Chand Vijay Kumar v. Yashpal Singh", r"prem chand vijay kumar", r"yashpal singh", 2005, ['"Prem Chand Vijay Kumar"']),
 ("TRL Krosaki Refractories Ltd v. SMS Asia Pvt Ltd", r"trl krosaki", r"sms asia", 2022, ['"TRL Krosaki"']),
 # control: personal / State names
 ("State of Haryana v. Bhajan Lal", r"state of haryana", r"bhajan lal", 1992, ['"Bhajan Lal" AND "State of Haryana"']),
 ("Lalita Kumari v. Government of Uttar Pradesh", r"lalita kumari", r"government of uttar pradesh", 2013, ['"Lalita Kumari"']),
 ("Arnab Manoranjan Goswami v. State of Maharashtra", r"arnab manoranjan goswami", r"state of maharashtra", 2020, ['"Arnab Manoranjan Goswami" OR "Arnab Goswami"']),
 ("Rupan Deol Bajaj v. Kanwar Pal Singh Gill", r"rupan deol bajaj", r"kanwar pal singh gill", 1995, ['"Rupan Deol Bajaj"']),
 ("Rangappa v. Sri Mohan", r"rangappa", r"mohan", 2010, ['"Rangappa" AND "Sri Mohan"']),
 ("Kaushalya Devi Massand v. Roopkishore Khore", r"kaushalya devi massand", r"roopkishore khore", 2011, ['"Kaushalya Devi Massand"']),
 ("Hiten P. Dalal v. Bratindranath Banerjee", r"hiten p", r"bratindranath", 2001, ['"Bratindranath Banerjee"']),
 ("M.S. Narayana Menon v. State of Kerala", r"narayana menon", r"state of kerala", 2006, ['"Narayana Menon"']),
 ("Sheoratan Agarwal v. State of Madhya Pradesh", r"sheoratan agarwal", r"state of madhya pradesh", 1984, ['"Sheoratan Agarwal"']),
 ("Mohammed Ibrahim v. State of Bihar", r"ibrahim", r"state of bihar", 2009, ['"Ibrahim" AND "State of Bihar" AND "forged"']),
 ("Vineet Narain v. Union of India", r"vineet narain", r"union of india", 1998, ['"Vineet Narain"']),
 ("Parminder Kaur v. State of Uttar Pradesh", r"parminder kaur", r"state of uttar pradesh", 2010, ['"Parminder Kaur"']),
 ("Mehmood Ul Rehman v. Khazir Mohammad Tunda", r"mehmood ul rehman", r"khazir mohammad", 2015, ['"Mehmood Ul Rehman"']),
 ("G. Sagar Suri v. State of Uttar Pradesh", r"sagar suri", r"state of u", 2000, ['"Sagar Suri"']),
 ("Rajesh Bajaj v. State NCT of Delhi", r"rajesh bajaj", r"state", 1999, ['"Rajesh Bajaj"']),
]
