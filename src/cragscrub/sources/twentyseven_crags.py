from __future__ import annotations

from typing import Iterable, Optional

from bs4 import BeautifulSoup

from cragscrub.models import Crag, Region
from cragscrub.sources.base import BaseScraper


class TwentySevenCragsScraper(BaseScraper):
    """Scrape public crag listings from 27crags.com.

    27crags exposes a country filter via query parameters on `/crags`. The
    current implementation scrapes that HTML table and can be extended to fetch
    per-crag pages for richer metadata (e.g., approach time).
    """

    def __init__(self, base_url: str = "https://27crags.com", **kwargs) -> None:
        super().__init__(base_url=base_url, **kwargs)

    def iter_regions(self, scope: dict | None = None) -> Iterable[Region]:
        scope = scope or {}
        country = scope.get("country")
        params = {"country": country} if country else {}
        response = self._get("/areas.json", params=params)
        payload = response.json().get("areas", [])
        for area in payload:
            yield Region(
                id=str(area.get("id")),
                name=area.get("name", "Unknown"),
                country_code=area.get("country_code") or area.get("country"),
                parent_id=str(area.get("parent_id")) if area.get("parent_id") else None,
                source="27crags",
                source_url=area.get("url"),
            )

    def iter_crags(self, scope: dict | None = None) -> Iterable[Crag]:
        scope = scope or {}
        country = scope.get("country")
        params = {"country": country} if country else {}
        response = self._get("/crags.json", params=params)
        for item in response.json().get("crags", []):
            yield Crag(
                source="27crags",
                source_id=str(item.get("id")),
                source_url=item.get("url"),
                name=item.get("name", "Unnamed crag"),
                region=item.get("area"),
                subregion=item.get("municipality"),
                country_code=item.get("country_code") or item.get("country"),
                lat=item.get("lat") or item.get("latitude"),
                lon=item.get("lon") or item.get("longitude"),
                num_routes=item.get("route_count"),
                climbing_styles=item.get("styles", []) or [],
                is_boulder_only=bool(item.get("boulder", False)),
                access_status=item.get("access_status") or "unknown",
                quality_score=item.get("quality_score"),
                short_description=item.get("short_description"),
                approach_time_min=item.get("approach_time_min"),
                tags=item.get("tags", []) or [],
                provenance="27crags_api",
            )

    def enrich_from_html(self, url: str) -> Optional[dict]:
        """Parse additional details from the public crag page."""

        response = self._get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        meta = {}
        approach = soup.find(string=lambda s: isinstance(s, str) and "Approach" in s)
        if approach and approach.parent:
            meta["approach_minutes"] = _parse_int(approach.parent.get_text())
        style_badges = soup.select(".badge.style")
        if style_badges:
            meta["climbing_styles"] = [badge.get_text(strip=True) for badge in style_badges]
        return meta or None


def _parse_int(value: str | None) -> Optional[int]:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return int(digits) if digits else None
