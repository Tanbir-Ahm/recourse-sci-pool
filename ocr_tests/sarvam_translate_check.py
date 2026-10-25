"""Check Sarvam Translate (sarvam-translate:v1) on clean Assamese and Kannada sentences whose English meaning is known.
The sentences are invented witness-statement lines, not from any real case, so this file is safe in the repo.
This tests translation alone, separate from reading: a bad result here is the translator's, not the OCR's.

  pip install sarvamai
  export SARVAM_API_KEY=...
  python sarvam_translate_check.py            # real calls, about Rs 2 per 1,000 characters (docs pricing page)
  python sarvam_translate_check.py --selftest # fake client
Each sentence has key facts the English must keep (date, time, number, object, who did what). The script checks the
simple ones automatically and prints every output so a person can judge the rest. 'hit' versus 'killed' is the
critical trap: Assamese "marile" and Kannada "hodedanu" are 'hit/beat'.
"""
import argparse, os, re, sys, time

CASES = [
    ("kn-IN", "ನಾನು ದಿನಾಂಕ 12.03.2024 ರಂದು ರಾತ್ರಿ 9 ಗಂಟೆಗೆ ಮನೆಯ ಹತ್ತಿರ ಆರೋಪಿಯನ್ನು ನೋಡಿದೆ.",
     "On 12.03.2024 at 9 pm I saw the accused near the house.", [r"12", r"(2024)", r"\b9\b|nine", r"accused"], []),
    ("kn-IN", "ಆತನ ಕೈಯಲ್ಲಿ ಚಾಕು ಇತ್ತು. ಅವನು ನನ್ನ ಸಹೋದರನನ್ನು ಹೊಡೆದನು.",
     "He had a knife in his hand. He hit my brother.", [r"knife", r"brother", r"hit|beat|struck"], [r"kill|murder|stab"]),
    ("kn-IN", "ಪೊಲೀಸರು ನನ್ನ ಹೇಳಿಕೆಯನ್ನು ದಾಖಲಿಸಿಕೊಂಡರು ಮತ್ತು ಸಹಿ ಮಾಡಿಸಿಕೊಂಡರು.",
     "The police recorded my statement and got it signed.", [r"police", r"statement", r"sign"], []),
    ("kn-IN", "ಘಟನೆ ಸ್ಥಳದಲ್ಲಿ ನಾಲ್ಕು ಜನ ಸಾಕ್ಷಿಗಳು ಇದ್ದರು.",
     "There were four witnesses at the scene.", [r"\bfour\b|\b4\b", r"witness"], []),
    ("as-IN", "মই ২০২৪ চনৰ ১২ মাৰ্চ তাৰিখে ৰাতি ৯ বজাত ঘৰৰ ওচৰত আসামীক দেখিছিলোঁ।",
     "On 12 March 2024 at 9 pm I saw the accused near the house.", [r"12", r"march", r"2024", r"\b9\b|nine", r"accused"], []),
    ("as-IN", "তেওঁৰ হাতত এখন ছুৰী আছিল। তেওঁ মোৰ ভায়েকক মাৰিলে।",
     "He had a knife in his hand. He hit my brother.", [r"knife", r"brother", r"hit|beat|struck"], [r"kill|murder|stab"]),
    ("as-IN", "আৰক্ষীয়ে মোৰ জবানবন্দী লিখি লৈছিল আৰু মোৰ চহী লৈছিল।",
     "The police wrote down my statement and took my signature.", [r"police", r"statement", r"sign"], []),
    ("as-IN", "ঘটনাস্থলীত চাৰিজন সাক্ষী আছিল।",
     "There were four witnesses at the scene.", [r"\bfour\b|\b4\b", r"witness"], []),
]


def run(client):
    ok = bad = 0
    for lang, src, ref, must, must_not in CASES:
        for attempt in range(6):
            try:
                out = client.text.translate(input=src, source_language_code=lang, target_language_code="en-IN",
                                            model="sarvam-translate:v1", mode="formal").translated_text
                break
            except Exception as exc:  # noqa: BLE001
                if getattr(exc, "status_code", None) != 429 or attempt == 5:
                    raise
                time.sleep(10)
        low = out.lower()
        missing = [m for m in must if not re.search(m, low)]
        wrong = [m for m in must_not if re.search(m, low)]
        flag = "OK " if not missing and not wrong else "CHECK"
        ok += flag == "OK "; bad += flag != "OK "
        print(f"[{flag}] {lang}\n   reference: {ref}\n   sarvam   : {out}" + (f"\n   missing {missing} wrong {wrong}" if missing or wrong else ""))
    print(f"\nautomatic check: {ok} passed, {bad} need a person's look (the automatic check is crude; read every line)")


def selftest():
    class R:
        def __init__(s, **k): s.__dict__.update(k)
    class Fake:
        def __init__(s): s.text = s
        def translate(s, **k): return R(translated_text="I saw the accused, knife, brother hit, 12 2024 9 March police statement sign four witness")
    run(Fake()); print("selftest OK (fake client; no Sarvam call was made)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--selftest", action="store_true"); a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        if not os.environ.get("SARVAM_API_KEY"):
            sys.exit("SARVAM_API_KEY is not set in this session.")
        from sarvamai import SarvamAI
        run(SarvamAI())
