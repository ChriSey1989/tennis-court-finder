"""
Main entry point: checks Europahalle and La Ville for free courts within
one or more requested day/time-of-day windows, and prints the result in
the format from spec.md Section 4.

Live fetching uses the real HTTP request eTennis.at's own page makes
(see clubs.py for the URL pattern) - this needs normal internet access,
which this development sandbox doesn't have (see conversation notes).
It's written to work correctly once run somewhere with real internet
access (e.g. the rented server) - `--fixture` lets us keep testing the
logic here in the meantime using the real pages you already captured.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

from clubs import CLUBS_IN_PRIORITY_ORDER, Club
from etennis_parser import Slot, available_slots_in_range, surface_for_slot
from time_windows import VIENNA_TZ, Window, resolve_window


FIXTURE_MAP = {
    "Europahalle": Path(__file__).parent.parent / "fixtures" / "europahalle_sample.html",
    "La Ville": Path(__file__).parent.parent / "fixtures" / "laville_sample.html",
}


def fetch_club_page(club: Club, day: date, use_fixtures: bool) -> str:
    """Get the raw HTML for a club's reservation page covering `day`.
    With use_fixtures=True, reads the saved real sample instead of making
    a live request (for testing without internet access)."""
    if use_fixtures:
        return FIXTURE_MAP[club.name].read_text(encoding="utf-8")

    # Real live request - this is what actually runs once deployed.
    timestamp = int(datetime.combine(day, datetime.min.time()).timestamp())
    url = f"{club.base_url}?c={club.sport_category_id}&t={timestamp}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.text


def find_slots_for_window(club: Club, window: Window, use_fixtures: bool) -> list[Slot]:
    html = fetch_club_page(club, window.day, use_fixtures)
    start_dt, end_dt = window.as_datetimes()
    return available_slots_in_range(html, start_dt, end_dt)


def format_results(windows: list[Window], results: dict[str, dict[str, list[Slot]]]) -> str:
    """results: {window_label: {club_name: [Slot, ...]}} - matches spec.md Section 4."""
    lines: list[str] = []
    for window in windows:
        lines.append(f"**{window.label.capitalize()}:**")
        club_results = results[window.label]
        any_found = any(slots for slots in club_results.values())
        if not any_found:
            lines.append("- No free slots found at either club.")
        else:
            for club_name, slots in club_results.items():
                if not slots:
                    continue
                for s in sorted(slots, key=lambda s: s.start):
                    local_time = s.start.astimezone(VIENNA_TZ).strftime("%H:%M")
                    surface = surface_for_slot(s, default_surface="carpet")
                    court_desc = f" ({s.court_label})" if s.court_label else ""
                    lines.append(f"- {club_name} — {local_time}{court_desc} ({surface})")
        lines.append("")
    return "\n".join(lines).strip()


def check(day_time_pairs: list[tuple[str, str]], today: date, use_fixtures: bool) -> str:
    windows = [resolve_window(day, tod, today) for day, tod in day_time_pairs]

    results: dict[str, dict[str, list[Slot]]] = {}
    for window in windows:
        results[window.label] = {}
        for club in CLUBS_IN_PRIORITY_ORDER:
            results[window.label][club.name] = find_slots_for_window(club, window, use_fixtures)

    return format_results(windows, results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check Europahalle/La Ville tennis availability.")
    parser.add_argument("--fixtures", action="store_true", help="Use saved sample pages instead of live requests.")
    args = parser.parse_args()

    # Using the real example from spec.md, with "today" fixed to match the
    # fixtures we captured (2026-10-04) so results actually line up.
    today = date(2026, 10, 4)
    result = check(
        day_time_pairs=[("tomorrow", "afternoon"), ("wednesday", "evening")],
        today=today,
        use_fixtures=args.fixtures,
    )
    print(result)
