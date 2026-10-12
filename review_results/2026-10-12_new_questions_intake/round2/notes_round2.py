"""Claude's notes for the SECOND version of the key review sheet (round 2, 2026-10-12). Starts from the round-1 notes (../notes.py) and overrides what the writer's replacements and the owner's decisions changed. Private."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
from notes import CHECK as CHECK1, FLAGS as FLAGS1, OPEN_POINTS as OPEN1

CHECK = dict(CHECK1)
FLAGS = dict(FLAGS1)

CHECK["N02"] = ("Arnesh Kumar (doc 41736) states the rule in its own reasoning: a person arrested must be produced before the Magistrate 'in no circumstances beyond 24 hours excluding the time necessary for the journey', and can be kept beyond 24 hours only when the Magistrate authorises it under s.167 CrPC. "
                "D.K. Basu (doc 14580) mentions the 24-hour rule only in a recital of the constitutional safeguards ('Clause (2) of Article 22 directs that the person arrested ... shall be produced before the nearest Magistrate within a period of 24 hours'); its holding is the list of arrest and custody requirements. "
                "Both SCC citations are repeated by other judgments in the index. Joginder Kumar is not in the index (a 2020 judgment quotes a High Court order that cites it).")
CHECK["N12"] = "DROPPED by the owner on 12 October 2026 (it repeated the sealed question R13). Nothing to review."
CHECK["N15"] = ("Rajnesh v. Neha (doc 1000252794) deals with interim maintenance, overlapping proceedings under the DV Act, s.125 CrPC and the personal laws, and discusses interim maintenance under s.23 read with s.20(1)(d) of the DV Act (through a Bombay High Court decision it approves). "
                "Juveria (doc 1000004478) lists the s.20 monetary relief and the s.23 interim orders; its facts include an interim maintenance order. "
                "Shyamlal Devda (doc 1000252355) is a judgment on TERRITORIAL JURISDICTION under s.27 DV Act (a Bengaluru Magistrate); it mentions s.20 in one sentence and does not discuss interim maintenance or maintenance as social justice, which the key attributes to it. "
                "Other indexed judgments cite Rajnesh as (2021) 2 SCC 324; the key says (2020) 15 SCC 17.")
CHECK["N19"] = CHECK1["N19"] + " (Round 2: the writer now lists Rishipal Singh Solanki as a primary authority next to Yuvaprakash. Another indexed judgment cites Vinod Katara as 2022 SCC OnLine SC 1204; the key gives '2024 LiveLaw (SC) 210', a year that does not fit the judgment in the index.)"
CHECK["N20"] = CHECK1["N20"] + " Round 2 adds Mahmood Farooqui v. State (Govt. of NCT of Delhi) as an acceptable authority with '(2017) 6 SCC 631': that is not in the index, and in later judgments (2017) 6 SCC 631 is the citation of Vasanta Sampat Dupare v. State of Maharashtra. I believe the Farooqui judgment is a Delhi High Court decision (not checkable here)."

FLAGS["N02"] = ("NEW (replacement for the first N02). Soft overlap by authority, kept by the owner: D.K. Basu is the key of the sealed R03 and Arnesh Kumar the key of R02 and of ruler topic T01; the point here is different (the 24-hour rule). "
                "(1) Which should be primary: D.K. Basu (the writer's choice) or Arnesh Kumar (states the rule in its reasoning)? (2) The key says 'BNSS s.58(2)'; I believe s.58 has no sub-section (2): please confirm, and the old s.57 CrPC. (3) Confirm that the 24 hours run from arrest and that holding a person who has not been formally arrested is also unlawful. (4) Joginder Kumar: not in the index.")
FLAGS["N12"] = "DROPPED by the owner on 12 October 2026 (hard duplicate of the sealed R13; its premise that cheating is not compoundable was probably wrong). Nothing to review."
FLAGS["N15"] = ("NEW (replacement for the first N15). Twin of N17 (same facts; this one asks for interim maintenance under the DV Act). (1) Citation: Rajnesh v. Neha is cited elsewhere as (2021) 2 SCC 324, not (2020) 15 SCC 17. "
                "(2) Shyamlal Devda is a jurisdiction case under s.27 and says nothing on interim maintenance: keep it as an acceptable authority or remove it? (3) The key bases the answer on s.20; Rajnesh and Juveria also point to s.23 (interim and ex parte orders): please confirm which sections the answer should rest on. "
                "(4) Confirm that the 'aggrieved woman forced out of the in-laws' house' can claim monetary relief under s.20(1)(d) without proving a separate domestic relationship issue.")
FLAGS["N19"] = "Both Yuvaprakash and Rishipal Singh Solanki are now listed as primary authorities. Yuvaprakash is about the age of a victim; Solanki is the accused's juvenility case. Keep both as primary, or make Solanki the only primary? Vinod Katara: the key's citation year (2024) does not fit the judgment in the index (2022)."
FLAGS["N20"] = "Only pre-2013 Supreme Court authority is offered, plus Mahmood Farooqui, which is not in the index and whose citation belongs to another case (I believe it is a Delhi High Court decision): please check it and remove it from the Supreme Court authorities if so; add modern authority if it exists."
FLAGS["N29"] = "The writer changed Conf to G (verified on secondary sources only). Please confirm that no Supreme Court judgment on or before 30 June 2026 deals with the effect of not recording a search under s.105 BNSS (outside the index)."
for q in ("N10", "N14", "N17", "N24", "NR2"):
    FLAGS[q] = FLAGS1.get(q, "") + " Round 2: the writer now writes 'Confirmed: no other acceptable authority' without showing a search: please confirm, or add."
for q, why in (("N04", "R25 is not involved; ruler topic T08"), ("N06", "earlier R25"), ("N07", "ruler topic T15"), ("N13", "ruler topic T10 and earlier R14")):
    FLAGS[q] = FLAGS1.get(q, "") + " The owner has decided to KEEP this overlap (12 October); results will be reported with and without it."

OPEN_POINTS = [
 ("all", "The citations in this key were found with an AI tool (owner, 12 October: the questions and the key were written by a person; the AI tool only helped to find the citations and cases). AI-found citations are the usual place for wrong or invented cases. Please check that EVERY authority named in the key exists as cited (case name, court, date, citation) and is the case the key says it is, not only what it holds. "
         "NEW: the sheet 'Citations (pre-check)' shows, for every citation in the key, whether other judgments in the index repeat it with the same case name. It is a mechanical aid, not a verification; start with the rows marked CHECK. "
         "Authorities not in the index (a name that is not in the index may be a real case outside the collection or a wrong citation): Siddharth, Aman Preet Singh, Joginder Kumar, Dilip Singh, U.N. Gupta, Womb Laboratories, K. Bhaskaran, Mohan Lal v. State of Rajasthan (2015), Sorabkhan Gandhkhan Pathan, Sarabjit Kaur, Rajinder Singh v. State of Punjab (2015), Suresh v. State of U.P. (2024), Surendra Bangali, Jagtar Singh (2023), Radheshyam, Mahmood Farooqui, Jagdish Lakra (2026), Vishnu Kumar Gupta (2026)."),
 ("N02 NEW", "Primary authority for the 24-hour rule: D.K. Basu (the writer) or Arnesh Kumar (states the rule in its reasoning)? Is it 'BNSS s.58' or 's.58(2)'? Does the 24-hour rule apply in the same way to a person who has not been formally arrested?"),
 ("N15 NEW", "Shyamlal Devda is a territorial-jurisdiction case under s.27 DV Act: remove it as an acceptable authority for interim maintenance, or keep it? Should the answer rest on s.20(1)(d) read with s.23? Confirm the citation of Rajnesh v. Neha ((2021) 2 SCC 324 elsewhere; the key says (2020) 15 SCC 17)."),
 ("N19", "Which is the primary authority for an ACCUSED's age claim: P. Yuvaprakash (2023, a victim's age) or Rishipal Singh Solanki (2022, an accused's juvenility claim)? The writer now lists both as primary. Is Aadhaar really outside the list in s.94(2)? Vinod Katara: the key gives '2024 LiveLaw (SC) 210'; another judgment cites it as 2022 SCC OnLine SC 1204."),
 ("N16, N17, N25, N27", "The key calls Appasaheb, Abraham Ajith / Ramesh v. State of T.N., B. Jayaraj and Satya Pal Singh 'not a counted trap'. Should any of them count as a stale ruling (Supreme Court ruling overruled, modified or replaced)? Only rulings that count will be scored as stale."),
 ("N14", "Is the answer (the IT Act s.67 charge excludes IPC s.292 for the same act) still right after the Bombay High Court Full Bench the writer mentions?"),
 ("N27", "The decision in Mallikarjun Kodagali is 2:1 and Satya Pal Singh was not formally overruled. Is the position settled?"),
 ("N24", "Manharibhai (2012) as the 'older ruling': is it right to treat it as replaced for complaints filed from 1 July 2024? Is anything else on the s.223 BNSS hearing decided by the Supreme Court before 30 June 2026?"),
 ("N29", "Confirm on SCC Online or Manupatra that no Supreme Court judgment on or before 30 June 2026 deals with non-compliance with s.105 BNSS (audio-video recording of search and seizure). The writer used web searches only."),
 ("N10, N14, N17, N24, NR2", "The key now says 'Confirmed: no other acceptable authority' without showing the search. Please confirm, or add."),
 ("N20", "Is there modern Supreme Court authority on 'no resistance / earlier relationship is not consent' to add besides Mango Ram (2000) and Gurmit Singh (1996)? Is Mahmood Farooqui a Supreme Court judgment (the key says (2017) 6 SCC 631) or a Delhi High Court decision?"),
 ("N26", "Please read Bilkis Yakub Rasool (8 Jan 2024) and confirm the key; the key rests on secondary reports. Confirm that the review petitions were dismissed (Sept 2024)."),
 ("N01", "Confirm the citation of Siddharth v. State of U.P. (the key says (2022) 1 SCC 676; the Antil judgment cites it as 2021 SCC OnLine SC 615)."),
 ("N01, N05, N11, N13", "Authorities the writer did not open (Aman Preet Singh, Ramesh Kumar, U.N. Gupta, Sarabjit Kaur, Delhi Race Club, Independent Thought ...): confirm they are right or remove them from the list of acceptable authorities. Several are in the index and can be read there (see 'Authorities in the index')."),
 ("all", "Confirm the CrPC to BNSS section mappings used in the key (170 to 190, 179 to 199, 372 to 413, 439 to 483, 438 to 482, 57 to 58)."),
 ("NR1", "Is the day of the first remand counted in the 60 days under s.187 BNSS, as Kapil Wadhawan (2023) held for the CrPC? Is the name clash with the earlier 'CBI v. Kapil Wadhawan' (2024) harmless?"),
]
