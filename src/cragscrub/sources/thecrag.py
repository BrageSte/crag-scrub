from __future__ import annotations

import html
import json
import re
from typing import Iterable, Optional

from bs4 import BeautifulSoup

from cragscrub.models import Crag, Region
from cragscrub.sources.base import BaseScraper


class TheCragScraper(BaseScraper):
    """Scrape public crag listings from the HTML map (no API calls).

    The map view on thecrag.com embeds JSON payloads that list nearby areas and
    crags. We fetch the map HTML (e.g., `https://www.thecrag.com/climbing/europe/maps`)
    and parse those embedded structures instead of using the API endpoints.
    Scope is provided as a dictionary; the `map_path` key lets you control which
    map path to fetch (defaults to `europe`).
    """

    def __init__(self, base_url: str = "https://www.thecrag.com", **kwargs) -> None:
        super().__init__(base_url=base_url, **kwargs)

    def iter_regions(self, scope: dict | None = None) -> Iterable[Region]:
        """Yield regions from the HTML map payload when available."""

        for feature in self._iter_map_features(scope):
            if feature.get("type") not in {"area", "region"}:
                continue
            yield Region(
                id=str(feature.get("id")),
                name=feature.get("name", "Unknown"),
                country_code=feature.get("country") or feature.get("country_code"),
                parent_id=str(feature.get("parent_id")) if feature.get("parent_id") else None,
                bbox=feature.get("bbox"),
                source="thecrag",
                source_url=feature.get("url"),
            )

    def iter_crags(self, scope: dict | None = None) -> Iterable[Crag]:
        for feature in self._iter_map_features(scope):
            if feature.get("type") not in {"crag", "node", "point"}:
                continue
            yield Crag(
                source="thecrag",
                source_id=str(feature.get("id")),
                source_url=feature.get("url"),
                name=feature.get("name", "Unnamed crag"),
                region=feature.get("region") or feature.get("area"),
                subregion=feature.get("locality"),
                country_code=feature.get("country") or feature.get("country_code"),
                lat=feature.get("lat") or feature.get("latitude"),
                lon=feature.get("lon") or feature.get("longitude"),
                elevation=feature.get("elevation"),
                climbing_styles=feature.get("styles", []) or [],
                rock_type=feature.get("rock_type"),
                num_routes=feature.get("route_count") or feature.get("routes"),
                quality_score=feature.get("quality") or feature.get("quality_score"),
                is_indoor=bool(feature.get("indoor", False)),
                is_boulder_only=bool(feature.get("boulder", False)),
                access_status=feature.get("access_status", "unknown") or "unknown",
                short_description=feature.get("description"),
                bbox=feature.get("bbox"),
                tags=feature.get("tags", []) or [],
                provenance="thecrag_html_map",
            )

    def _iter_map_features(self, scope: dict | None = None) -> Iterable[dict]:
        """Parse embedded JSON data from the HTML map page.

        The map page includes multiple potential JSON blobs (React props, plain
        script assignments, or data attributes). We inspect them in a few
        patterns and yield any feature dictionaries we find that include
        coordinates.
        """

        path = _scope_to_map_path(scope)
        response = self._get(path)
        soup = BeautifulSoup(response.text, "html.parser")

        # Data attributes with JSON payloads
        for tag in soup.find_all(attrs={"data-map-features": True}):
            raw = html.unescape(tag.get("data-map-features", ""))
            yield from _safe_feature_list(raw)

        for tag in soup.find_all(attrs={"data-react-props": True}):
            raw = html.unescape(tag.get("data-react-props", ""))
            props = _safe_json(raw)
            if not props:
                continue
            features = props.get("features") or props.get("points") or []
            yield from features if isinstance(features, list) else []

        # Inline scripts with assignments like `var mapData = {...};`
        for script in soup.find_all("script"):
            text = script.string or script.get_text() or ""
            match = re.search(r"mapData\s*=\s*(\{.*?\})\s*;", text, re.DOTALL)
            if match:
                data = _safe_json(match.group(1))
                if data:
                    for key in ("features", "points", "items"):
                        if isinstance(data.get(key), list):
                            yield from data[key]

            if script.get("type") == "application/json":
                payload = _safe_json(text)
                if payload:
                    for key in ("features", "points", "items"):
                        if isinstance(payload.get(key), list):
                            yield from payload[key]

        # Last resort: look for any JSON arrays in the body with lat/lon fields.
        body_text = soup.get_text("\n")
        for match in re.finditer(r"\[\{.*?\}\]", body_text, re.DOTALL):
            candidate = _safe_json(match.group(0))
            if isinstance(candidate, list):
                for item in candidate:
                    if isinstance(item, dict) and ("lat" in item or "latitude" in item):
                        yield item


def _scope_to_map_path(scope: Optional[dict]) -> str:
    scope = scope or {}
    map_path = scope.get("map_path")
    if map_path:
        if map_path.startswith("http"):
            return map_path
        return map_path if map_path.startswith("/") else f"/climbing/{map_path.strip('/')}/maps"
    country = scope.get("country") or scope.get("country_slug") or scope.get("country_code")
    if country:
        return f"/climbing/{str(country).lower()}/maps"
    return "/climbing/europe/maps"


def _safe_json(raw: str | None) -> dict | list | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _safe_feature_list(raw: str | None) -> list[dict]:
    payload = _safe_json(raw)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("features", "points", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []
