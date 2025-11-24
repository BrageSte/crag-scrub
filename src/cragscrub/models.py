from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, RootModel


class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude in WGS84")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in WGS84")


class BoundingBox(BaseModel):
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float


class Region(BaseModel):
    id: str
    name: str
    country_code: Optional[str] = None
    parent_id: Optional[str] = Field(
        default=None, description="Identifier of the parent region if present",
    )
    bbox: Optional[BoundingBox] = None
    type: Optional[str] = Field(
        default=None,
        description="Hierarchy level: continent | country | region | local",
    )
    source: Optional[str] = Field(
        default=None, description="Name of the upstream provider (e.g., thecrag)",
    )
    source_url: Optional[HttpUrl] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Crag(BaseModel):
    # Identity & source
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    source_id: Optional[str] = None
    source_url: Optional[HttpUrl] = None

    # Name & hierarchy
    name: str
    alternative_names: list[str] = Field(default_factory=list)
    country_code: Optional[str] = None
    region: Optional[str] = None
    subregion: Optional[str] = None
    parent_region_id: Optional[str] = None

    # Location & geometry
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    elevation: Optional[int] = None
    bbox: Optional[BoundingBox] = None
    osm_id: Optional[str] = None

    # Climbing-related metadata
    rock_type: Optional[str] = None
    climbing_styles: list[str] = Field(default_factory=list)
    grade_min: Optional[str] = None
    grade_max: Optional[str] = None
    num_routes: Optional[int] = None
    quality_score: Optional[float] = None
    is_indoor: bool = False
    is_boulder_only: bool = False
    access_status: str = Field(default="unknown")
    seasonality: Optional[str] = None

    # Aspect / wall direction
    aspect_source: str = Field(default="unknown")
    aspect_deg: Optional[int] = Field(default=None, ge=0, le=360)
    aspect_spread: Optional[str] = None

    # Practical info
    short_description: Optional[str] = None
    approach_time_min: Optional[int] = None
    parking_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    parking_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    tags: list[str] = Field(default_factory=list)

    # Internal metadata
    canonical_key: Optional[str] = None
    merged_from: list[str] = Field(default_factory=list)
    effective_filter_passed: bool = True
    last_scraped_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at_source: Optional[datetime] = None
    provenance: Optional[str] = None

    def compute_canonical_key(self) -> Optional[str]:
        """Build a canonical key for deduplication using name/country/rounded coords."""

        if not self.name or not self.country_code or self.lat is None or self.lon is None:
            return None
        normalized_name = re.sub(r"[^a-z0-9]+", "", self.name.lower())
        return f"{normalized_name}_{self.country_code}_{round(self.lat, 3):.3f}_{round(self.lon, 3):.3f}"

    def merge_from(self, other: "Crag") -> "Crag":
        """Merge another crag into this one, preferring existing values."""

        for field in self.__fields__:
            if getattr(self, field) in (None, [], "") and getattr(other, field) not in (None, [], ""):
                setattr(self, field, getattr(other, field))
        if other.id not in self.merged_from:
            self.merged_from.append(f"{other.source}:{other.source_id or other.id}")
        if other.merged_from:
            self.merged_from.extend([m for m in other.merged_from if m not in self.merged_from])
        self.merged_from = list(dict.fromkeys(self.merged_from))
        self.effective_filter_passed = self.effective_filter_passed or other.effective_filter_passed
        return self


class CragCollection(RootModel[list[Crag]]):
    """Simple collection wrapper to allow JSON export via `.model_dump_json()`."""


class RegionCollection(RootModel[list[Region]]):
    """Simple collection wrapper to allow JSON export via `.model_dump_json()`."""
