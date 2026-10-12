"""Round 2 of the intake (replacement file received 2026-10-12, sha256 404e203b...cebc7): the authorities named for the three replaced questions (N02, N12, N15) and the one added in N20,
read off by hand from the 'Key' sheet of the round-2 workbook. Names only; nothing is searched. PRIVATE (it is part of the answer key).
Same tuple layout as ../authorities.py: (question, role, label, tokens that must all be inside the normalised title, year, years of slack)."""
A2_NEW = [
    ("N02", "primary", "D.K. Basu v. State of West Bengal (1996/97)", ["dkbasu"], 1997, 1),
    ("N02", "acceptable", "Arnesh Kumar v. State of Bihar (2014)", ["arneshkumar"], 2014, 0),
    ("N02", "acceptable", "Joginder Kumar v. State of U.P. (1994)", ["joginderkumar"], 1994, 0),
    ("N12", "primary", "Gian Singh v. State of Punjab (2012)", ["giansingh"], 2012, 0),
    ("N12", "acceptable", "Parbatbhai Aahir v. State of Gujarat (2017)", ["parbatbhai"], 2017, 0),
    ("N12", "acceptable", "Narinder Singh v. State of Punjab (2014)", ["narindersingh"], 2014, 0),
    ("N15", "primary", "Rajnesh v. Neha (2020)", ["rajnesh"], 2020, 1),
    ("N15", "acceptable", "Shyamlal Devda v. Parimala (2020)", ["shyamlal"], 2020, 1),
    ("N15", "acceptable", "Juveria Abdul Majid Patni v. Atif Iqbal Mansoori (2014)", ["juveria"], 2014, 0),
    ("N20", "acceptable", "Mahmood Farooqui v. State (Govt. of NCT of Delhi) (2017)", ["mahmoodfarooqui"], 2017, 0),
]
# Round-1 entries that no longer apply (the three questions were replaced): all rows of N02, N12 and N15 in ../authorities.py.
REPLACED = {"N02", "N12", "N15"}
