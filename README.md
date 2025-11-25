# crag-scrub

`crag-scrub` is a small toolkit for harvesting climbing locations from multiple public sources and producing a unified export (e.g., NDJSON or GeoJSON) that can be ingested by another project. It is intentionally source-agnostic and encourages one scraper implementation per upstream source.

## Features
- Source-specific scraper classes (e.g., `TheCragScraper`, `TwentySevenCragsScraper`) with a shared interface. The TheCrag
  adapter parses the public HTML map (`/climbing/<region>/maps`) instead of the JSON API so you can keep runs within what the
  site already exposes to browsers.
- Normalized `Crag` and `Region` models with coordinates, hierarchy, quality/access metadata, and provenance.
- YAML-based run configuration for repeatable exports (e.g., focus on Europe or a specific country) plus filter rules.
- Deduplication of overlapping crags using canonical keys and simple merge heuristics.
- Pluggable output writers (NDJSON and GeoJSON helpers provided) that mark whether a crag passed filters.
- Retry-aware HTTP client with polite defaults you can tune per source.

## Getting started (zero config)
If you just want to scrape TheCrag's HTML map without editing YAML:

1. Install Python 3.11+ (built-in on macOS via Xcode Command Line Tools is fine), clone/download this repo, then from the folder run:
   ```bash
   python -m pip install -e .
   ```

2. Launch the GUI:
   ```bash
   cragscrub-gui
   # or double-click run-gui.command (chmod +x run-gui.command once)
   ```

3. In the window, leave the config field empty to use the quick setup. Pick a map area (e.g., `europe` or `norway/nissedal`), optional country codes/bounding box, choose filters (min routes, exclude indoor/closed, etc.), select where to save NDJSON (and optional GeoJSON), and click **Run scrape**. The run will pull directly from the public thecrag.com HTML map.

4. The log panel streams progress; when done, the NDJSON is ready for your app. Filter-failed crags remain with `effective_filter_passed=false` so you can audit them separately.

## Getting started (YAML-driven runs)
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

2. Prepare a run configuration (see [`config/europe.example.yml`](config/europe.example.yml)) that lists the sources you want to hit, any geographic scope, and filter rules (e.g., `min_routes`, `exclude_indoor`).

3. Run the CLI:
   ```bash
   python -m cragscrub.cli --config config/europe.example.yml --output data/europe.ndjson
   ```

4. Inspect results with standard JSON tooling or transform them for your target database. Crags that failed filters are still emitted with `effective_filter_passed=false` so you can audit them separately.

## Data model highlights
- **Crag** fields include source identifiers, hierarchy (`country_code`, `region`, `subregion`), coordinates/geometry (`lat`, `lon`, `bbox`), climbing metadata (`rock_type`, `climbing_styles`, `num_routes`, `grade_min/max`, `quality_score`), access/practical info, and internal metadata (`canonical_key`, `effective_filter_passed`, `merged_from`).
- **Region** fields include a hierarchy (`parent_id`, `type`), `country_code`, optional `bbox`, and provenance.
- Canonical keys combine normalized names with country/rounded coordinates to deduplicate across sources; merged crags carry the `merged_from` list for provenance.

## Run from a browser
If you prefer a browser-driven experience, launch the FastAPI app and use the interactive docs:

```bash
uvicorn cragscrub.web:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/docs` in your browser, expand the `/scrape` endpoint, and provide:
- `config`: path to your YAML config (e.g., `config/europe.example.yml`)
- `output`: where to write the NDJSON (directories are created if needed)
- `geojson` (optional): path for an additional GeoJSON export

Successful requests return counts and the output paths; the files are written locally where the server runs.

## Run with a desktop GUI (macOS-friendly)
If you want a point-and-click launcher instead of the CLI, a lightweight Tkinter UI is included. After installing the package, start it with:

```bash
cragscrub-gui
# or
python -m cragscrub.gui
```

From the window you can:
- Leave the config path blank and use the "Quick setup" panel to pick a thecrag.com map area/path and filters without touching YAML.
- Browse to a YAML config file if you prefer a saved setup.
- Choose NDJSON/GeoJSON output paths.
- Check which sources (e.g., `thecrag`, `27crags`) to include for the run.
- Click **Run scrape** to execute the same filter/dedup pipeline as the CLI and see progress in the log panel.

## Project layout
- `src/cragscrub/models.py` – Pydantic data models for `Crag` and `Region` with canonical key helpers.
- `src/cragscrub/sources/` – Scrapers per upstream source and the shared `BaseScraper`.
- `src/cragscrub/pipeline.py` – Orchestration helpers for running sources, applying filters, deduplicating, and writing outputs.
- `src/cragscrub/cli.py` – Entry point that wires config, pipeline, and output writers.
- `config/` – Example YAML configurations demonstrating how to scope regions and set filter rules.

## Notes on scraping ethics
- Always respect each source's terms of service and robots.txt directives.
- Apply sensible rate limits and retries; the defaults in `BaseScraper` are conservative.
- Authenticate with your own tokens where required rather than scraping logged-in pages.

## Next steps
- Flesh out field mappings for each source using their public APIs or HTML structure.
- Add caching and deduplication layers to avoid repeated downloads.
- Expand test coverage with recorded fixtures (e.g., via `pytest` and `vcrpy`).
