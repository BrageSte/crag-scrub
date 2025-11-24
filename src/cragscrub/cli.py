from __future__ import annotations

import argparse

from cragscrub.pipeline import build_scrapers, load_config, run_sources, write_geojson, write_ndjson


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape climbing crags from multiple sources")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to a YAML config file declaring sources and scope",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the NDJSON output file",
    )
    parser.add_argument(
        "--geojson",
        help="Optional path to write GeoJSON with point features",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    scrapers = build_scrapers(config)
    scope = config.get("scope")

    regions, crags = run_sources(scrapers, scope=scope)
    write_ndjson([*regions, *crags], args.output)

    if args.geojson:
        write_geojson(crags, args.geojson)

    print(f"Wrote {len(regions)} regions and {len(crags)} crags to {args.output}")
    if args.geojson:
        print(f"Wrote GeoJSON with {len(crags)} features to {args.geojson}")


if __name__ == "__main__":
    main()
