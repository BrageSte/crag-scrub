from __future__ import annotations

import argparse

from cragscrub.pipeline import (
    apply_filters,
    build_scrapers,
    deduplicate_crags,
    load_config,
    run_sources,
    write_geojson,
    write_ndjson,
)


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
    filters = config.get("filters")

    regions, crags = run_sources(scrapers, scope=scope)
    filtered_crags = apply_filters(crags, filters)
    deduped_crags = deduplicate_crags(filtered_crags)
    write_ndjson([*regions, *deduped_crags], args.output)

    if args.geojson:
        write_geojson(deduped_crags, args.geojson)

    passed_count = len([c for c in deduped_crags if c.effective_filter_passed])
    print(
        f"Wrote {len(regions)} regions and {len(deduped_crags)} crags to {args.output}"
    )
    print(f"{passed_count} crags passed filters and {len(deduped_crags) - passed_count} were retained as rejected")
    if args.geojson:
        print(f"Wrote GeoJSON with {passed_count} features to {args.geojson}")


if __name__ == "__main__":
    main()
