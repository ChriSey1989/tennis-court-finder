"""
Parser for eTennis.at reservation pages (used by both Europahalle and La Ville).

The booking calendar is rendered directly into the page HTML - no separate
API call is needed. Each court is a <div class="court" data-cid="...">,
containing one <div class="slot"> per hour, classed either:
  - "av"  = available (bookable) - has data-id=""
  - "res" = reserved/booked       - has a real data-id (the booking's ID)

Each slot has:
  - data-begin: Unix timestamp (seconds) for the slot's start time
  - data-size:  how many consecutive hours this block spans
  - a price-tier class (e.g. "price38541") mapping to a price shown
    elsewhere on the page in a ".pricebox" section

One page load returns TWO days of data side by side.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup


@dataclass
class Slot:
    court_id: str       # the data-cid, e.g. "4927"
    court_label: str | None  # the human-readable name shown on the page, e.g. "Platz 5 Rebound Ace"
    start: datetime      # slot start time, as a timezone-aware datetime
    duration_hours: int  # how many hours this slot/block covers
    available: bool      # True if bookable, False if already reserved
    price_tier: str | None  # e.g. "price38541", or None if not found
    price_eur: float | None  # looked up from the page's price box, if found


# Keywords that reveal surface directly from a club's own court label text
# (not every club includes this - Europahalle's labels are just "1 WEST" etc,
# so for those clubs the caller falls back to a hardcoded default instead).
_SURFACE_KEYWORDS = {
    "teppich": "carpet",
    "rebound ace": "rebound ace",
    "hartplatz": "hard",
    "sand": "sand",
    "asche": "sand",
}


def _guess_surface_from_label(label: str) -> str | None:
    lowered = label.lower()
    for keyword, surface in _SURFACE_KEYWORDS.items():
        if keyword in lowered:
            return surface
    return None


def _parse_price_box(soup: BeautifulSoup) -> dict[str, float]:
    """Map price-tier class names (e.g. 'price38541') to a Euro amount,
    by reading the page's own '.pricebox' section."""
    prices: dict[str, float] = {}
    pricebox = soup.select_one(".pricebox")
    if not pricebox:
        return prices
    for price_div in pricebox.select("div[class*='price']"):
        classes = price_div.get("class", [])
        tier_class = next((c for c in classes if c.startswith("price") and c != "price"), None)
        if not tier_class:
            continue
        text = price_div.get_text(strip=True)
        # text looks like "€ 24" - pull out the number
        digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
        if digits:
            prices[tier_class] = float(digits)
    return prices


def _parse_court_labels(soup: BeautifulSoup) -> dict[str, str]:
    """Map each data-cid to its human-readable label (e.g. "Platz 5 Rebound Ace"),
    by pairing a day block's name header with its court order.
    The same courts repeat for every day shown, so one day block is enough -
    but the page also contains decoy "day" elements (a hidden date-picker
    widget) with no real court data, so we skip past those."""
    for day in soup.select("div.day"):
        court_divs = day.select("div.day-body div.court[data-cid]")
        if not court_divs:
            continue  # decoy / empty day block, keep looking
        first_header = day.select_one("div.day-courts")  # the page repeats this header; use only the first
        names = [c.get_text(strip=True) for c in first_header.select("div.court")] if first_header else []
        cids = []
        for c in court_divs:
            cid = c["data-cid"]
            if cid not in cids:
                cids.append(cid)
        if names and len(names) == len(cids):
            return dict(zip(cids, names))
    return {}


def parse_availability(html: str) -> list[Slot]:
    """Parse one eTennis.at reservation page and return every slot found
    (both available and reserved), across both days shown on the page."""
    soup = BeautifulSoup(html, "html.parser")
    price_lookup = _parse_price_box(soup)
    court_labels = _parse_court_labels(soup)

    slots: list[Slot] = []
    for court_div in soup.select("div.court[data-cid]"):
        court_id = court_div["data-cid"]
        court_label = court_labels.get(court_id)
        for slot_div in court_div.select("div.slot"):
            classes = slot_div.get("class", [])
            is_available = "av" in classes
            is_reserved = "res" in classes
            if not is_available and not is_reserved:
                # Skip anything that's neither (shouldn't normally happen)
                continue

            begin_raw = slot_div.get("data-begin")
            if not begin_raw:
                continue
            start = datetime.fromtimestamp(int(begin_raw), tz=timezone.utc)

            size_raw = slot_div.get("data-size", "1")
            duration_hours = int(size_raw) if size_raw.isdigit() else 1

            tier_class = next(
                (c for c in classes if c.startswith("price") and c != "price"), None
            )
            price_eur = price_lookup.get(tier_class) if tier_class else None

            slots.append(
                Slot(
                    court_id=court_id,
                    court_label=court_label,
                    start=start,
                    duration_hours=duration_hours,
                    available=is_available,
                    price_tier=tier_class,
                    price_eur=price_eur,
                )
            )
    return slots


def surface_for_slot(slot: Slot, default_surface: str) -> str:
    """Best-guess surface for a slot: prefer what the club's own page says
    (e.g. "Rebound Ace" in the label), fall back to the club's configured
    default (e.g. Europahalle, whose labels don't mention surface at all)."""
    if slot.court_label:
        guessed = _guess_surface_from_label(slot.court_label)
        if guessed:
            return guessed
    return default_surface


def available_slots_in_range(
    html: str, earliest: datetime, latest: datetime
) -> list[Slot]:
    """Convenience filter: only available slots whose start time falls
    within [earliest, latest) - both sides must be timezone-aware
    (see time_windows.Window.as_datetimes, which returns Vienna-local
    times; slot.start is stored in UTC and converted here for a fair
    comparison)."""
    if earliest.tzinfo is None or latest.tzinfo is None:
        raise ValueError("earliest/latest must be timezone-aware - naive datetimes are ambiguous")
    all_slots = parse_availability(html)
    return [
        s
        for s in all_slots
        if s.available and earliest <= s.start.astimezone(earliest.tzinfo) < latest
    ]


def _run_test(fixture_name: str, default_surface: str) -> None:
    fixture_path = Path(__file__).parent.parent / "fixtures" / fixture_name
    html = fixture_path.read_text(encoding="utf-8")

    all_slots = parse_availability(html)
    available = [s for s in all_slots if s.available]
    reserved = [s for s in all_slots if not s.available]

    print(f"=== {fixture_name} ===")
    print(f"Parsed {len(all_slots)} total slots: {len(available)} available, {len(reserved)} reserved.")
    print("Courts found:", {s.court_id: s.court_label for s in all_slots[:len(set(s.court_id for s in all_slots))]})
    print()
    print("First 8 AVAILABLE slots (with resolved surface):")
    for s in sorted(available, key=lambda s: s.start)[:8]:
        local_time = s.start.astimezone()
        surface = surface_for_slot(s, default_surface)
        price_part = f"{s.price_eur} EUR" if s.price_eur else "price n/a"
        print(
            f"  Court {s.court_id} ({s.court_label}) | {local_time.strftime('%a %Y-%m-%d %H:%M')} "
            f"| {s.duration_hours}h | {price_part} | surface: {surface}"
        )
    print()


if __name__ == "__main__":
    _run_test("europahalle_sample.html", default_surface="carpet")
    _run_test("laville_sample.html", default_surface="carpet")
