from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, RootModel


class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude in WGS84")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in WGS84")


class Region(BaseModel):
    id: str
    name: str
    country: Optional[str] = None
    state: Optional[str] = None
    municipality: Optional[str] = None
    parent_id: Optional[str] = Field(
        default=None, description="Identifier of the parent region if present"
    )
    source: str = Field(..., description="Name of the upstream provider (e.g., thecrag)")
    source_url: Optional[HttpUrl] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Crag(BaseModel):
    id: str
    name: str
    region_id: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    elevation_m: Optional[int] = None
    municipality: Optional[str] = None
    country: Optional[str] = None
    climbing_styles: list[str] = Field(default_factory=list)
    approach_minutes: Optional[int] = None
    route_count: Optional[int] = None
    source: str
    source_url: Optional[HttpUrl] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CragCollection(RootModel[list[Crag]]):
    """Simple collection wrapper to allow JSON export via `.model_dump_json()`."""


class RegionCollection(RootModel[list[Region]]):
    """Simple collection wrapper to allow JSON export via `.model_dump_json()`."""
