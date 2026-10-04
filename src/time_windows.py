"""
Turns a request like "tomorrow afternoon" or "Wednesday evening" into an
actual date + clock-time range, using the fixed definitions from spec.md
Section 2.

NOTE (see spec.md open items): this file currently does simple rule-based
matching for "today" / "tomorrow" / weekday names. A more flexible version
(handling looser phrasing) would hand the raw text to Claude for extraction
instead - this is a reasonable v1 starting point that covers the example
requests directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

VIENNA_TZ = ZoneInfo("Europe/Vienna")

# Exactly the ranges from spec.md Section 2 - deliberately overlapping by an
# hour at each boundary, per the user's own definition.
TIME_OF_DAY_RANGES: dict[str, tuple[time, time]] = {
    "morning": (time(6, 0), time(11, 0)),
    "noon": (time(10, 0), time(14, 0)),
    "afternoon": (time(13, 0), time(18, 0)),
    "evening": (time(17, 0), time(23, 0)),
}

_WEEKDAYS = {
    "monday": 0, "montag": 0,
    "tuesday": 1, "dienstag": 1,
    "wednesday": 2, "mittwoch": 2,
    "thursday": 3, "donnerstag": 3,
    "friday": 4, "freitag": 4,
    "saturday": 5, "samstag": 5,
    "sunday": 6, "sonntag": 6,
}


@dataclass
class Window:
    label: str       # human-readable, e.g. "tomorrow afternoon"
    day: date
    start_time: time
    end_time: time

    def as_datetimes(self) -> tuple[datetime, datetime]:
        """Returns (start, end) as timezone-aware Vienna-local datetimes -
        "afternoon" means 1-6pm in Vienna, regardless of what timezone the
        underlying slot data happens to be stored in."""
        return (
            datetime.combine(self.day, self.start_time, tzinfo=VIENNA_TZ),
            datetime.combine(self.day, self.end_time, tzinfo=VIENNA_TZ),
        )


def resolve_day(day_phrase: str, today: date) -> date:
    """Resolve a day phrase ("today", "tomorrow", "wednesday", ...) to an
    actual date, relative to `today`. Weekday names always mean the NEXT
    occurrence of that weekday (never today itself, even if today matches -
    "give me Sunday" said on a Sunday means next Sunday, not right now)."""
    phrase = day_phrase.strip().lower()
    if phrase == "today":
        return today
    if phrase == "tomorrow":
        return today + timedelta(days=1)
    if phrase in _WEEKDAYS:
        target = _WEEKDAYS[phrase]
        days_ahead = (target - today.weekday()) % 7
        days_ahead = days_ahead or 7  # 0 would mean "today" - push to next week instead
        return today + timedelta(days=days_ahead)
    raise ValueError(f"Don't recognize day phrase: {day_phrase!r}")


def resolve_window(day_phrase: str, time_of_day: str, today: date) -> Window:
    time_of_day = time_of_day.strip().lower()
    if time_of_day not in TIME_OF_DAY_RANGES:
        raise ValueError(
            f"Unknown time-of-day word: {time_of_day!r}. "
            f"Expected one of: {', '.join(TIME_OF_DAY_RANGES)}"
        )
    day = resolve_day(day_phrase, today)
    start_time, end_time = TIME_OF_DAY_RANGES[time_of_day]
    return Window(
        label=f"{day_phrase} {time_of_day}",
        day=day,
        start_time=start_time,
        end_time=end_time,
    )


if __name__ == "__main__":
    today = date(2026, 10, 4)  # a Sunday, matching this conversation's real date
    for day_phrase, tod in [("tomorrow", "afternoon"), ("wednesday", "evening")]:
        w = resolve_window(day_phrase, tod, today)
        print(f"{day_phrase!r} + {tod!r} -> {w.day} ({w.day.strftime('%A')}), {w.start_time}-{w.end_time}")
