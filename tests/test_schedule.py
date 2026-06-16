from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.schedule import IST, minutes_until_departure, next_departure_at, parse_time


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

