"""Custom US street-address recognizer for Presidio (M3 fix for the ADDRESS gap).
Pure regex, no network. build_recognizer() returns a Presidio PatternRecognizer;
ADDRESS_RE can be unit-tested without Presidio installed."""
import re

ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+"                                   # street number
    r"(?:[A-Za-z0-9.'\-]+\s+){1,5}?"                  # street name words
    r"(?:(?:Apt|Apartment|Suite|Ste|Unit)\.?\s*[A-Za-z0-9\-]+\s+)?"   # optional unit
    r"(?:[A-Za-z.'\-]+\s+){0,4}?"                     # optional city words
    r"[A-Za-z.'\-]+,?\s+(?-i:[A-Z]{2})\s+\d{5}(?:-\d{4})?\b"  # city, ST ZIP (state stays case-sensitive: Presidio compiles with IGNORECASE)
)

MILITARY_RE = re.compile(
    r"\b(?:Unit|PSC|CMR|USS|USNS|USNV|USCGC)\s+[A-Za-z0-9 ,.\-]{1,40}?\s*"
    r"(?:APO|FPO|DPO)\s+(?-i:A[AEP])\s+\d{5}(?:-\d{4})?\b")
COMBINED = "(?:" + MILITARY_RE.pattern + ")|(?:" + ADDRESS_RE.pattern + ")"
COMBINED_RE = re.compile(COMBINED)

def build_recognizer():
    from presidio_analyzer import Pattern, PatternRecognizer
    return PatternRecognizer(
        supported_entity="ADDRESS",
        patterns=[Pattern("us_address", COMBINED, 0.85)],
        name="CustomUSAddressRecognizer")

def add_to(engine):
    engine.registry.add_recognizer(build_recognizer())
    return engine
