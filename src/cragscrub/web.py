from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from cragscrub.pipeline import build_scrapers, load_config, run_sources, write_geojson, write_ndjson


app = FastAPI(
    title="crag-scrub",
    description="Run crag scrapers through a small FastAPI service you can drive from a browser (see /docs)",
)


class ScrapeRequest(BaseModel):
    config: str = Field(..., description="Path to a YAML config file (e.g., config/europe.example.yml)")
    output: str = Field(..., description="Path to write NDJSON results (created if missing)")
    geojson: str | None = Field(None, description="Optional path to also write GeoJSON point features")


class ScrapeResult(BaseModel):
    regions: int
    crags: int
    output: str
    geojson: str | None = None


def _ensure_parent(path: Path) -> None:
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)


def _run_scrape(request: ScrapeRequest) -> ScrapeResult:
    config_path = Path(request.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    output_path = Path(request.output)
    geojson_path = Path(request.geojson) if request.geojson else None

    _ensure_parent(output_path)
    if geojson_path:
        _ensure_parent(geojson_path)

    config = load_config(str(config_path))
    scrapers = build_scrapers(config)
    scope = config.get("scope")

    regions, crags = run_sources(scrapers, scope=scope)
    write_ndjson([*regions, *crags], str(output_path))
    if geojson_path:
        write_geojson(crags, str(geojson_path))

    return ScrapeResult(
        regions=len(regions),
        crags=len(crags),
        output=str(output_path),
        geojson=str(geojson_path) if geojson_path else None,
    )


@app.post("/scrape", response_model=ScrapeResult, summary="Run a scrape with a local config and output paths")
def scrape(request: ScrapeRequest) -> ScrapeResult:
    try:
        return _run_scrape(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:  # pragma: no cover - fallthrough safety
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health", summary="Simple health probe")
def health() -> dict[str, str]:
    return {"status": "ok"}
