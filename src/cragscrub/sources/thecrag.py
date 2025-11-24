from __future__ import annotations

from typing import Iterable, Optional

from bs4 import BeautifulSoup

from cragscrub.models import Coordinates, Crag, Region
from cragscrub.sources.base import BaseScraper


class TheCragScraper(BaseScraper):
    """Scrape public crag listings from thecrag.com.

    TheCrag exposes a JSON API for search (used here) and HTML pages for
    individual areas. This scraper focuses on the JSON search endpoint so it
    remains lightweight and polite. Scope is provided as a dictionary, e.g.:

    ```python
    {"country": "Norway"}
    ```
    """

    def __init__(self, base_url: str = "https://www.thecrag.com/api", **kwargs) -> None:
        super().__init__(base_url=base_url, **kwargs)

    def iter_regions(self, scope: dict | None = None) -> Iterable[Region]:
        scope = scope or {}
        country = scope.get("country")
        params = {"country": country} if country else {}
        response = self._get("/areas", params=params)
        payload = response.json().get("areas", [])
        for area in payload:
            yield Region(
                id=str(area.get("id")),
                name=area.get("name", "Unknown"),
                country=area.get("country"),
                state=area.get("state"),
                municipality=area.get("locality"),
                parent_id=str(area.get("parentId")) if area.get("parentId") else None,
                source="thecrag",
                source_url=area.get("url"),
            )

    def iter_crags(self, scope: dict | None = None) -> Iterable[Crag]:
        scope = scope or {}
        country = scope.get("country")
        params = {"country": country} if country else {}
        response = self._get("/crags", params=params)
        payload = response.json().get("crags", [])
        for item in payload:
            coords = _coords_from_point(item.get("point"))
            yield Crag(
                id=str(item.get("id")),
                name=item.get("name", "Unnamed crag"),
                region_id=str(item.get("areaId")) if item.get("areaId") else None,
                coordinates=coords,
                municipality=item.get("locality"),
                country=item.get("country"),
                elevation_m=item.get("elevation"),
                climbing_styles=item.get("styles", []) or [],
                route_count=item.get("routeCount"),
                source="thecrag",
                source_url=item.get("url"),
            )

    def scrape_area_page(self, url: str) -> Optional[tuple[Optional[int], list[str]]]:
        """Fetch additional details from a public area page.

        This can be used to enrich route counts or styles in case the API omits
        them. It is intentionally optional to keep the baseline run fast.
        """

        response = self._get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        stats = soup.select_one(".node-statistics")
        if not stats:
            return None
        styles = [tag.get_text(strip=True) for tag in stats.select(".style-name")]
        routes_text = stats.select_one(".route-count")
        route_count = int(routes_text.get_text(strip=True)) if routes_text else None
        return route_count, styles


def _coords_from_point(point: dict | None) -> Optional[Coordinates]:
    if not point:
        return None
    lat = point.get("lat") or point.get("latitude")
    lon = point.get("lon") or point.get("longitude")
    if lat is None or lon is None:
        return None
    return Coordinates(lat=lat, lon=lon)
