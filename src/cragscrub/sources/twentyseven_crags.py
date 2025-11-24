from __future__ import annotations

from typing import Iterable, Optional

from bs4 import BeautifulSoup

from cragscrub.models import Coordinates, Crag, Region
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
                country=area.get("country"),
                municipality=area.get("municipality"),
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
            coords = _coords_from_dict(item)
            yield Crag(
                id=str(item.get("id")),
                name=item.get("name", "Unnamed crag"),
                region_id=str(item.get("area_id")) if item.get("area_id") else None,
                coordinates=coords,
                route_count=item.get("route_count"),
                country=item.get("country"),
                municipality=item.get("municipality"),
                climbing_styles=item.get("styles", []) or [],
                source="27crags",
                source_url=item.get("url"),
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


def _coords_from_dict(data: dict) -> Optional[Coordinates]:
    if not data:
        return None
    lat = data.get("lat") or data.get("latitude")
    lon = data.get("lon") or data.get("longitude")
    if lat is None or lon is None:
        return None
    return Coordinates(lat=lat, lon=lon)


def _parse_int(value: str | None) -> Optional[int]:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return int(digits) if digits else None
