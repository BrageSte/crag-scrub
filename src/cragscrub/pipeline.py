from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

import yaml

from cragscrub.models import Crag, Region
from cragscrub.sources.base import BaseScraper
from cragscrub.sources.thecrag import TheCragScraper
from cragscrub.sources.twentyseven_crags import TwentySevenCragsScraper

SCRAPER_REGISTRY = {
    "thecrag": TheCragScraper,
    "27crags": TwentySevenCragsScraper,
}


def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_scrapers(config: dict) -> list[BaseScraper]:
    scrapers: list[BaseScraper] = []
    for entry in config.get("sources", []):
        name = entry.get("name")
        scraper_cls = SCRAPER_REGISTRY.get(name)
        if not scraper_cls:
            raise ValueError(f"Unknown scraper '{name}'")
        kwargs = entry.get("options", {})
        scrapers.append(scraper_cls(**kwargs))
    return scrapers


def run_sources(
    scrapers: Sequence[BaseScraper],
    scope: dict | None = None,
) -> tuple[list[Region], list[Crag]]:
    regions: list[Region] = []
    crags: list[Crag] = []
    for scraper in scrapers:
        region_scope = (scope or {}).get(scraper.__class__.__name__, scope)
        regions.extend(list(scraper.iter_regions(region_scope)))
        crags.extend(list(scraper.iter_crags(region_scope)))
    return regions, crags


def apply_filters(crags: Iterable[Crag], filters: dict | None = None) -> list[Crag]:
    filters = filters or {}
    min_routes = filters.get("min_routes")
    min_quality_score = filters.get("min_quality_score")
    min_star_rating = filters.get("min_star_rating")
    exclude_indoor = filters.get("exclude_indoor", False)
    exclude_via_ferrata = filters.get("exclude_via_ferrata", False)
    exclude_ice = filters.get("exclude_ice", False)
    require_latlon = filters.get("require_latlon", False)
    require_name = filters.get("require_name", False)
    exclude_closed = filters.get("exclude_closed", False)
    include_restricted = filters.get("include_restricted", True)

    filtered: list[Crag] = []
    for crag in crags:
        passed = True
        if require_name and not crag.name:
            passed = False
        if require_latlon and (crag.lat is None or crag.lon is None):
            passed = False
        if min_routes is not None and (crag.num_routes is None or crag.num_routes < min_routes):
            passed = False
        if min_quality_score is not None and (
            crag.quality_score is None or crag.quality_score < min_quality_score
        ):
            passed = False
        if min_star_rating is not None and (
            crag.quality_score is None or crag.quality_score < min_star_rating
        ):
            passed = False
        if exclude_indoor and crag.is_indoor:
            passed = False
        if exclude_via_ferrata and "via_ferrata" in (crag.tags or []):
            passed = False
        if exclude_ice and "ice" in (crag.tags or []):
            passed = False
        if exclude_closed and crag.access_status == "closed":
            passed = False
        if not include_restricted and crag.access_status == "restricted":
            passed = False
        crag.effective_filter_passed = passed
        filtered.append(crag)
    return filtered


def deduplicate_crags(crags: Iterable[Crag]) -> list[Crag]:
    buckets: dict[str, list[Crag]] = defaultdict(list)
    singleton: list[Crag] = []

    for crag in crags:
        crag.canonical_key = crag.canonical_key or crag.compute_canonical_key()
        if crag.canonical_key:
            buckets[crag.canonical_key].append(crag)
        else:
            singleton.append(crag)

    merged: list[Crag] = []
    for key, items in buckets.items():
        if len(items) == 1:
            merged.append(items[0])
            continue
        items.sort(key=_crag_quality_score, reverse=True)
        base = items[0]
        base.merged_from = [f"{item.source}:{item.source_id or item.id}" for item in items]
        for extra in items[1:]:
            base.merge_from(extra)
        base.canonical_key = key
        merged.append(base)

    merged.extend(singleton)
    return merged


def _crag_quality_score(crag: Crag) -> float:
    non_null_fields = sum(
        1
        for field in [
            crag.name,
            crag.country_code,
            crag.region,
            crag.subregion,
            crag.lat,
            crag.lon,
            crag.rock_type,
            crag.grade_min,
            crag.grade_max,
            crag.num_routes,
            crag.quality_score,
        ]
        if field not in (None, "")
    )
    return non_null_fields + (crag.quality_score or 0)


def write_ndjson(items: Iterable[Crag | Region], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item.model_dump(mode="json"), ensure_ascii=False))
            f.write("\n")


def write_geojson(crags: Iterable[Crag], path: str | Path) -> None:
    features = []
    for crag in crags:
        if crag.lat is None or crag.lon is None or not crag.effective_filter_passed:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [crag.lon, crag.lat],
                },
                "properties": crag.model_dump(mode="json"),
            }
        )

    collection = {"type": "FeatureCollection", "features": features}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, indent=2)
