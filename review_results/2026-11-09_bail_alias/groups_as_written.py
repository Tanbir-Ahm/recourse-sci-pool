"""Word groups of the bail entries, as written 2026-11-09 BEFORE the question set was run (PREREGISTRATION.md). Copied unchanged into Recourse statute_aliases.py."""
ARRESTED = (r"(?:\b(?:i|we|he|she|they)\s+(?:was|were|got|am|is|are|have been|has been|had been)\s+(?:arrested|detained|taken into custody|taken to (?:the )?(?:police station|lock-?up))\b|"
            r"\b(?:was|were|got|been|get)\s+(?:arrested|detained)\b|"
            r"\barrested\s+(?:me|my \w+|him|her|them|us)\b|"
            r"\bpolice\s+(?:arrested|detained|picked up|took|have taken|has taken|have arrested|has arrested)\s+(?:me|my \w+|him|her|them|us)\b|"
            r"\b(?:is|am|was|are|were|been|remains?|kept|held|lying)\s+(?:\w+\s+)?(?:in|into)\s+(?:police\s+|judicial\s+)?custody\b|"
            r"\b(?:is|am|was|are|were|been|remains?|kept|held|lying)\s+(?:\w+\s+)?(?:in|inside)\s+(?:the\s+)?(?:jail|lock-?up|prison)\b|"
            r"\bremanded\b)")
BAIL_REFUSED = (r"(?:\bbail\b[^.?!]{0,50}\b(?:refused|rejected|denied|dismissed|declined)\b|\b(?:refused|rejected|denied|dismissed|declined)\b[^.?!]{0,30}\bbail\b)")
HIGHER = r"\b(?:high court|sessions court|session court|sessions judge)\b"
ENTRIES = [
    {"id": "bnss_478_bail_bailable", "act": "BNSS", "section": "478", "groups": [[ARRESTED]]},
    {"id": "bnss_480_bail_nonbailable", "act": "BNSS", "section": "480", "groups": [[ARRESTED]]},
    {"id": "bnss_483_bail_higher_court", "act": "BNSS", "section": "483", "groups": [[BAIL_REFUSED], [r"\bbail\b", HIGHER]]},
]
