from __future__ import annotations

from typing import Iterable, Optional

from bs4 import BeautifulSoup

from cragscrub.models import Crag, Region
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
                country_code=area.get("countryCode") or area.get("country"),
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
            coords = item.get("point") or {}
            yield Crag(
                source="thecrag",
                source_id=str(item.get("id")),
                source_url=item.get("url"),
                name=item.get("name", "Unnamed crag"),
                region=str(item.get("area")) if item.get("area") else None,
                subregion=item.get("locality"),
                country_code=item.get("countryCode") or item.get("country"),
                lat=coords.get("lat") or coords.get("latitude"),
                lon=coords.get("lon") or coords.get("longitude"),
                elevation=item.get("elevation"),
                climbing_styles=item.get("styles", []) or [],
                num_routes=item.get("routeCount"),
                quality_score=item.get("qualityScore"),
                is_indoor=bool(item.get("indoor", False)),
                is_boulder_only=bool(item.get("boulder", False)),
                access_status=item.get("accessStatus", "unknown") or "unknown",
                short_description=item.get("description"),
                provenance="thecrag_api",
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
