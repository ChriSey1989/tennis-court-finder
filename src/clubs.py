"""
Static configuration for each club in v1 scope.

Surface doesn't change often, so it's stored here as fixed data rather
than scraped live - confirmed directly by the user, not guessed.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Club:
    name: str
    base_url: str          # e.g. "https://reservierung.europahalle.at/reservierung"
    sport_category_id: str  # the "c=" URL parameter for Tennis on this club's system
    default_surface: str    # surface for any court not listed in `court_surface_overrides`
    court_surface_overrides: dict[str, str] = field(default_factory=dict)
    # ^ keyed by the real eTennis `data-cid` value, once known

    def surface_for(self, court_id: str) -> str:
        return self.court_surface_overrides.get(court_id, self.default_surface)


EUROPAHALLE = Club(
    name="Europahalle",
    base_url="https://reservierung.europahalle.at/reservierung",
    sport_category_id="1531",
    default_surface="carpet",
    # All 12 known courts (4927-4938) are carpet - no overrides needed.
)

LA_VILLE = Club(
    name="La Ville",
    base_url="https://reservierung.laville.at/",
    sport_category_id="4903",  # from earlier research - matches the "Halle" category seen on the page
    default_surface="carpet",
    court_surface_overrides={
        # TODO: fill in once we know La Ville's real data-cid for "court 5".
        # Example once known: "XXXX": "rebound ace",
    },
)

# Priority order for v1 (Wienerberg and Suedstadt deferred - see spec.md Section 7)
CLUBS_IN_PRIORITY_ORDER = [EUROPAHALLE, LA_VILLE]
