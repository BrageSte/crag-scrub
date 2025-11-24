from __future__ import annotations

import json
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


def write_ndjson(items: Iterable[Crag | Region], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item.model_dump(mode="json"), ensure_ascii=False))
            f.write("\n")


def write_geojson(crags: Iterable[Crag], path: str | Path) -> None:
    features = []
    for crag in crags:
        if not crag.coordinates:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [crag.coordinates.lon, crag.coordinates.lat],
                },
                "properties": crag.model_dump(mode="json"),
            }
        )

    collection = {"type": "FeatureCollection", "features": features}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, indent=2)
