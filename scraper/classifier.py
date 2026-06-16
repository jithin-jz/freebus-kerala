import re

ORDINARY_PATTERNS = (
    re.compile(r"\bordinary\b", re.IGNORECASE),
    re.compile(r"\bord\b", re.IGNORECASE),
)

EXCLUDED_PATTERNS = (
    re.compile(r"\bac\b", re.IGNORECASE),
    re.compile(r"\bswift\b", re.IGNORECASE),
    re.compile(r"\bsuper\s*fast\b", re.IGNORECASE),
    re.compile(r"\bfast\s*passenger\b", re.IGNORECASE),
    re.compile(r"\bdeluxe\b", re.IGNORECASE),
    re.compile(r"\bsuper\s*deluxe\b", re.IGNORECASE),
    re.compile(r"\bvolvo\b", re.IGNORECASE),
    re.compile(r"\blow\s*floor\b", re.IGNORECASE),
)


def is_priyadarshini(bus_type: str | None, raw_text: str | None = None) -> bool:
    """Return true only for ordinary-class services eligible for the scheme."""
    haystack = " ".join(part for part in (bus_type or "", raw_text or "") if part).strip()
    if not haystack:
        return False
    if any(pattern.search(haystack) for pattern in EXCLUDED_PATTERNS):
        return False
    return any(pattern.search(haystack) for pattern in ORDINARY_PATTERNS)

