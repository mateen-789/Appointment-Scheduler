import re
from typing import Optional

# Keyword -> canonical department name (used in the final output in Step 5)
DEPARTMENT_MAP = {
    "dentist": "Dentistry",
    "dental": "Dentistry",
    "dentistry": "Dentistry",
    "cardiologist": "Cardiology",
    "cardiology": "Cardiology",
    "dermatologist": "Dermatology",
    "dermatology": "Dermatology",
    "orthopedic": "Orthopedics",
    "orthopaedic": "Orthopedics",
    "pediatrician": "Pediatrics",
    "paediatrician": "Pediatrics",
    "ophthalmologist": "Ophthalmology",
    "neurologist": "Neurology",
    "gynecologist": "Gynecology",
    "physiotherapist": "Physiotherapy",
    "physio": "Physiotherapy",
}

# Building blocks for the patterns below
WEEKDAY = (
    r"(?:monday|mon|tuesday|tues|tue|wednesday|wed|thursday|thurs|thur|thu"
    r"|friday|fri|saturday|sat|sunday|sun)"
)
MONTH = (
    r"(?:january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul"
    r"|august|aug|september|sept|sep|october|oct|november|nov|december|dec)"
)

# Tried in order; the first pattern that matches wins.
# "nxt" is included because OCR/shorthand often writes it that way.
DATE_PATTERNS = [
    r"\bday after tomorrow\b",
    r"\b(?:today|tomorrow|tmrw)\b",
    r"\b(?:next|nxt|this|coming)\s+" + WEEKDAY + r"\b",
    r"\b" + WEEKDAY + r"\b",
    r"\bin\s+\d+\s+(?:days?|weeks?)\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+" + MONTH + r"\b(?:,?\s+\d{4})?",
    r"\b" + MONTH + r"\s+\d{1,2}(?:st|nd|rd|th)?\b(?:,?\s+\d{4})?",
]

TIME_PATTERNS = [
    r"\b\d{1,2}(?::\d{2})?\s?(?:am|pm)\b",  # 3pm, 3 pm, 10:30 am
    r"\b\d{1,2}:\d{2}\b",                    # 15:00
    r"\b(?:noon|midnight)\b",
]

DEPARTMENT_PATTERN = r"\b(?:" + "|".join(DEPARTMENT_MAP) + r")\b"


def _find_first(patterns: list, text: str) -> Optional[str]:
    """Return the first matching phrase (original spelling), or None."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def extract_entities(raw_text: str) -> dict:
    date_phrase = _find_first(DATE_PATTERNS, raw_text)
    time_phrase = _find_first(TIME_PATTERNS, raw_text)

    dept_match = re.search(DEPARTMENT_PATTERN, raw_text, re.IGNORECASE)
    department = dept_match.group(0).lower() if dept_match else None

    # Simple heuristic confidence: the more entities we found, the more sure we are
    found = sum(x is not None for x in (date_phrase, time_phrase, department))
    confidence = {3: 0.85, 2: 0.5, 1: 0.25, 0: 0.0}[found]

    return {
        "entities": {
            "date_phrase": date_phrase,
            "time_phrase": time_phrase,
            "department": department,
        },
        "entities_confidence": confidence,
    }