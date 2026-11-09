import os, sys
sys.path.insert(0, "/home/user/recourse"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["CASE_FILE"] = "on"; os.environ["AGE_CARD"] = "on"
import case_file as C
from questions_age_card import POS, NEG
miss = [q for q in POS if C.card_for(None, q) is None]
fire = [q for q in NEG if C.card_for(None, q) is not None]
print("positives that got the card: %d of %d" % (len(POS) - len(miss), len(POS)))
for q in miss: print("  MISSED:", q)
print("negatives that wrongly got the card: %d of %d" % (len(fire), len(NEG)))
for q in fire: print("  FALSE FIRE:", q)
