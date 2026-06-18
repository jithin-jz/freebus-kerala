from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.schedule import (
    IST,
    current_day_code,
    minutes_until_departure,
    next_departure_at,
    parse_time,
)


def test_parse_time_handles_ist_display_formats():
    assert parse_time("06:30").hour == 6
    assert parse_time("6.30 PM").hour == 18


def test_next_departure_rolls_to_tomorrow_after_departure():
    now = datetime(2026, 6, 16, 8, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    departure = next_departure_at("07:30", now=now)
    assert departure.date().day == 17
    assert departure.tzinfo == IST


def test_minutes_until_departure():
    now = datetime(2026, 6, 16, 8, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    assert minutes_until_departure("08:14", now=now) == 14


def test_current_day_code_matches_weekday():
    # 2026-06-15 is a Monday, 2026-06-21 is a Sunday.
    assert current_day_code(datetime(2026, 6, 15, 9, 0, tzinfo=IST)) == "mon"
    assert current_day_code(datetime(2026, 6, 21, 9, 0, tzinfo=IST)) == "sun"

