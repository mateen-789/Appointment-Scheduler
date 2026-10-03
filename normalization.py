import re
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import dateparser

TZ_NAME = "Asia/Kolkata"
TZ = ZoneInfo(TZ_NAME)

WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tues": 1, "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thurs": 3, "thur": 3, "thu": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}


def _parse_date(phrase: str, today: date) -> Optional[date]:
    p = phrase.lower().strip()

    if p == "today":
        return today
    if p in ("tomorrow", "tmrw"):
        return today + timedelta(days=1)
    if p == "day after tomorrow":
        return today + timedelta(days=2)

    # Weekdays: "friday", "this friday", "next friday", "nxt fri"
    m = re.fullmatch(r"(?:(next|nxt|this|coming)\s+)?([a-z]+)", p)
    if m and m.group(2) in WEEKDAYS:
        target = WEEKDAYS[m.group(2)]
        days_ahead = (target - today.weekday()) % 7
        # "next <weekday>" never means today
        if m.group(1) in ("next", "nxt") and days_ahead == 0:
            days_ahead = 7
        return today + timedelta(days=days_ahead)

    # Everything else ("15 October", "in 3 days", "2026-10-20", "12/11/2026")
    parsed = dateparser.parse(
        p,
        settings={
            "TIMEZONE": TZ_NAME,
            "RELATIVE_BASE": datetime.combine(today, time(12, 0)),
            "PREFER_DATES_FROM": "future",
            "DATE_ORDER": "DMY",  # Indian format: day first
        },
    )
    return parsed.date() if parsed else None


def _parse_time(phrase: str) -> Optional[time]:
    p = phrase.lower().strip()

    if p == "noon":
        return time(12, 0)
    if p == "midnight":
        return time(0, 0)

    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s?(am|pm)?", p)
    if not m:
        return None

    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    meridiem = m.group(3)

    if minute > 59:
        return None
    if meridiem:
        if not 1 <= hour <= 12:
            return None
        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
    elif hour > 23:
        return None

    return time(hour, minute)


def _needs_clarification(message: str) -> dict:
    return {"status": "needs_clarification", "message": message}


def normalize(
    date_phrase: Optional[str],
    time_phrase: Optional[str],
    today: Optional[date] = None,
) -> dict:
    today = today or datetime.now(TZ).date()

    if not date_phrase:
        return _needs_clarification("Missing date: could not find a date in the request.")
    if not time_phrase:
        return _needs_clarification("Missing time: could not find a time in the request.")

    parsed_date = _parse_date(date_phrase, today)
    if parsed_date is None:
        return _needs_clarification(f"Ambiguous date: could not understand '{date_phrase}'.")

    parsed_time = _parse_time(time_phrase)
    if parsed_time is None:
        return _needs_clarification(f"Ambiguous time: could not understand '{time_phrase}'.")

    if parsed_date < today:
        return _needs_clarification(f"Date {parsed_date.isoformat()} is in the past.")

    return {
        "normalized": {
            "date": parsed_date.isoformat(),
            "time": parsed_time.strftime("%H:%M"),
            "tz": TZ_NAME,
        },
        "normalization_confidence": 0.9,
    }