from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from cragscrub.pipeline import (
    apply_filters,
    build_scrapers,
    deduplicate_crags,
    load_config,
    run_sources,
    write_geojson,
    write_ndjson,
)
from cragscrub.pipeline import SCRAPER_REGISTRY


class ScraperGUI(ttk.Frame):
    """Simple Tk GUI to run scrapes without the CLI."""

    def __init__(self, master: tk.Tk):
        super().__init__(master, padding=10)
        self.master.title("CragScrub Runner")
        self.master.geometry("740x720")
        self.pack(fill=tk.BOTH, expand=True)

        self.config_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.geojson_var = tk.StringVar()

        # Quick inline config fields (no YAML editing required)
        self.map_path_var = tk.StringVar(value="europe")
        self.countries_var = tk.StringVar(value="NO, SE")
        self.min_routes_var = tk.StringVar(value="3")
        self.min_quality_var = tk.StringVar(value="0.2")
        self.require_latlon_var = tk.BooleanVar(value=True)
        self.require_name_var = tk.BooleanVar(value=True)
        self.exclude_indoor_var = tk.BooleanVar(value=True)
        self.exclude_closed_var = tk.BooleanVar(value=True)
        self.include_restricted_var = tk.BooleanVar(value=False)
        self.exclude_via_ferrata_var = tk.BooleanVar(value=True)
        self.exclude_ice_var = tk.BooleanVar(value=True)
        self.bbox_min_lat = tk.StringVar()
        self.bbox_min_lon = tk.StringVar()
        self.bbox_max_lat = tk.StringVar()
        self.bbox_max_lon = tk.StringVar()
        self.base_url_var = tk.StringVar(value="https://www.thecrag.com")

        self.source_vars: dict[str, tk.BooleanVar] = {
            name: tk.BooleanVar(value=True) for name in SCRAPER_REGISTRY
        }

        self._build_form()

    def _build_form(self) -> None:
        row = 0
        ttk.Label(self, text="Config file (YAML)").grid(column=0, row=row, sticky=tk.W)
        ttk.Entry(self, textvariable=self.config_var, width=55).grid(
            column=1, row=row, sticky=tk.EW
        )
        ttk.Button(self, text="Browse", command=self._browse_config).grid(
            column=2, row=row, padx=5
        )
        row += 1

        ttk.Label(self, text="NDJSON output").grid(column=0, row=row, sticky=tk.W)
        ttk.Entry(self, textvariable=self.output_var, width=55).grid(
            column=1, row=row, sticky=tk.EW
        )
        ttk.Button(self, text="Browse", command=self._browse_output).grid(
            column=2, row=row, padx=5
        )
        row += 1

        ttk.Label(self, text="GeoJSON output (optional)").grid(
            column=0, row=row, sticky=tk.W
        )
        ttk.Entry(self, textvariable=self.geojson_var, width=55).grid(
            column=1, row=row, sticky=tk.EW
        )
        ttk.Button(self, text="Browse", command=self._browse_geojson).grid(
            column=2, row=row, padx=5
        )
        row += 1

        ttk.Separator(self, orient=tk.HORIZONTAL).grid(
            column=0, row=row, columnspan=3, sticky=tk.EW, pady=6
        )
        row += 1

        ttk.Label(
            self, text="Quick setup (no YAML needed)", font=("TkDefaultFont", 10, "bold")
        ).grid(column=0, row=row, sticky=tk.W, columnspan=2)
        row += 1

        ttk.Label(self, text="Map area (theCrag path or URL)").grid(
            column=0, row=row, sticky=tk.W
        )
        ttk.Entry(self, textvariable=self.map_path_var, width=55).grid(
            column=1, row=row, sticky=tk.EW
        )
        ttk.Label(self, text="e.g. europe or norway/nissedal").grid(
            column=2, row=row, sticky=tk.W
        )
        row += 1

        ttk.Label(self, text="Countries (comma-separated ISO codes)").grid(
            column=0, row=row, sticky=tk.W
        )
        ttk.Entry(self, textvariable=self.countries_var, width=55).grid(
            column=1, row=row, sticky=tk.EW
        )
        row += 1

        bbox_frame = ttk.LabelFrame(
            self, text="Optional bounding box (min/max lat/lon)", padding=6
        )
        bbox_frame.grid(column=0, row=row, columnspan=3, sticky=tk.EW, pady=4)
        ttk.Entry(bbox_frame, textvariable=self.bbox_min_lat, width=10).grid(
            column=1, row=0, padx=4, pady=2
        )
        ttk.Entry(bbox_frame, textvariable=self.bbox_min_lon, width=10).grid(
            column=2, row=0, padx=4, pady=2
        )
        ttk.Entry(bbox_frame, textvariable=self.bbox_max_lat, width=10).grid(
            column=3, row=0, padx=4, pady=2
        )
        ttk.Entry(bbox_frame, textvariable=self.bbox_max_lon, width=10).grid(
            column=4, row=0, padx=4, pady=2
        )
        ttk.Label(bbox_frame, text="min_lat").grid(column=1, row=1)
        ttk.Label(bbox_frame, text="min_lon").grid(column=2, row=1)
        ttk.Label(bbox_frame, text="max_lat").grid(column=3, row=1)
        ttk.Label(bbox_frame, text="max_lon").grid(column=4, row=1)
        row += 1

        filters_frame = ttk.LabelFrame(self, text="Filters", padding=6)
        filters_frame.grid(column=0, row=row, columnspan=3, sticky=tk.EW)
        ttk.Checkbutton(filters_frame, text="Require name", variable=self.require_name_var).grid(
            column=0, row=0, sticky=tk.W, padx=4, pady=2
        )
        ttk.Checkbutton(filters_frame, text="Require lat/lon", variable=self.require_latlon_var).grid(
            column=1, row=0, sticky=tk.W, padx=4, pady=2
        )
        ttk.Checkbutton(filters_frame, text="Exclude indoor", variable=self.exclude_indoor_var).grid(
            column=0, row=1, sticky=tk.W, padx=4, pady=2
        )
        ttk.Checkbutton(filters_frame, text="Exclude closed", variable=self.exclude_closed_var).grid(
            column=1, row=1, sticky=tk.W, padx=4, pady=2
        )
        ttk.Checkbutton(
            filters_frame, text="Include restricted", variable=self.include_restricted_var
        ).grid(column=2, row=1, sticky=tk.W, padx=4, pady=2)
        ttk.Checkbutton(
            filters_frame, text="Exclude via ferrata", variable=self.exclude_via_ferrata_var
        ).grid(column=0, row=2, sticky=tk.W, padx=4, pady=2)
        ttk.Checkbutton(filters_frame, text="Exclude ice", variable=self.exclude_ice_var).grid(
            column=1, row=2, sticky=tk.W, padx=4, pady=2
        )

        ttk.Label(filters_frame, text="Min routes").grid(column=0, row=3, sticky=tk.W, padx=4)
        ttk.Entry(filters_frame, textvariable=self.min_routes_var, width=8).grid(
            column=1, row=3, sticky=tk.W, padx=4
        )
        ttk.Label(filters_frame, text="Min quality (0-1)").grid(
            column=2, row=3, sticky=tk.W, padx=4
        )
        ttk.Entry(filters_frame, textvariable=self.min_quality_var, width=8).grid(
            column=3, row=3, sticky=tk.W, padx=4
        )
        row += 1

        ttk.Separator(self, orient=tk.HORIZONTAL).grid(
            column=0, row=row, columnspan=3, sticky=tk.EW, pady=6
        )
        row += 1

        ttk.Label(self, text="Sources to include").grid(column=0, row=row, sticky=tk.NW)
        sources_frame = ttk.Frame(self)
        sources_frame.grid(column=1, row=row, sticky=tk.W)
        for idx, (name, var) in enumerate(self.source_vars.items()):
            ttk.Checkbutton(sources_frame, text=name, variable=var).grid(
                column=idx % 2, row=idx // 2, sticky=tk.W, padx=4, pady=2
            )
        row += 1

        ttk.Button(self, text="Run scrape", command=self._run_scrape).grid(
            column=1, row=row, pady=12, sticky=tk.W
        )
        row += 1

        ttk.Label(self, text="Log").grid(column=0, row=row, sticky=tk.NW)
        self.log_text = tk.Text(self, height=15, wrap=tk.WORD)
        self.log_text.grid(column=0, row=row + 1, columnspan=3, sticky=tk.NSEW)

        for i in range(3):
            self.columnconfigure(i, weight=1 if i == 1 else 0)
        self.rowconfigure(row + 1, weight=1)

    def _browse_config(self) -> None:
        path = filedialog.askopenfilename(
            title="Select YAML config", filetypes=[("YAML", "*.yml *.yaml"), ("All", "*.*")]
        )
        if path:
            self.config_var.set(path)

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save NDJSON", defaultextension=".ndjson", filetypes=[("NDJSON", "*.ndjson")]
        )
        if path:
            self.output_var.set(path)

    def _browse_geojson(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save GeoJSON", defaultextension=".geojson", filetypes=[("GeoJSON", "*.geojson")]
        )
        if path:
            self.geojson_var.set(path)

    def _run_scrape(self) -> None:
        config_path = self.config_var.get().strip()
        output_path = self.output_var.get().strip()

        if config_path and not Path(config_path).exists():
            messagebox.showerror("Missing config", "Please select a valid YAML config file.")
            return
        if not output_path:
            messagebox.showerror("Missing output", "Please choose an NDJSON output path.")
            return

        selected_sources = [name for name, var in self.source_vars.items() if var.get()]
        if not selected_sources:
            messagebox.showerror("No sources", "Select at least one source to scrape.")
            return

        thread = threading.Thread(
            target=self._run_scrape_thread,
            args=(config_path, output_path, self.geojson_var.get().strip(), selected_sources),
            daemon=True,
        )
        thread.start()

    def _run_scrape_thread(
        self, config_path: str, output_path: str, geojson_path: str | None, selected_sources: list[str]
    ) -> None:
        try:
            if config_path:
                self._log(f"Loading config: {config_path}")
                config = load_config(config_path)
                configured_sources = config.get("sources", [])
                config["sources"] = [
                    entry for entry in configured_sources if entry.get("name") in selected_sources
                ]
                if not config["sources"]:
                    raise ValueError(
                        "No matching sources in config for the selections you made. Update the YAML or check a different source."
                    )
            else:
                self._log("Using quick setup (theCrag HTML map)")
                config = self._build_quick_config(selected_sources)

            scrapers = build_scrapers(config)
            scope = config.get("scope")
            filters = config.get("filters")

            self._log("Running scrapers...")
            regions, crags = run_sources(scrapers, scope=scope)
            filtered_crags = apply_filters(crags, filters)
            deduped_crags = deduplicate_crags(filtered_crags)

            self._log(f"Writing NDJSON to {output_path}")
            write_ndjson([*regions, *deduped_crags], output_path)

            if geojson_path:
                self._log(f"Writing GeoJSON to {geojson_path}")
                write_geojson(deduped_crags, geojson_path)

            passed_count = len([c for c in deduped_crags if c.effective_filter_passed])
            total = len(deduped_crags)
            self._log(
                f"Done. {passed_count} crags passed filters, {total - passed_count} retained as rejected."
            )
            messagebox.showinfo("Scrape complete", "Scrape finished successfully.")
        except Exception as exc:  # noqa: BLE001
            self._log(f"Error: {exc}")
            messagebox.showerror("Scrape failed", str(exc))

    def _log(self, message: str) -> None:
        def _append() -> None:
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)

        self.log_text.after(0, _append)

    def _build_quick_config(self, selected_sources: list[str]) -> dict:
        def _safe_int(value: str) -> int | None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _safe_float(value: str) -> float | None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        bbox = None
        bbox_inputs = [
            self.bbox_min_lat.get().strip(),
            self.bbox_min_lon.get().strip(),
            self.bbox_max_lat.get().strip(),
            self.bbox_max_lon.get().strip(),
        ]
        if any(bbox_inputs):
            try:
                bbox = {
                    "min_lat": float(self.bbox_min_lat.get()),
                    "min_lon": float(self.bbox_min_lon.get()),
                    "max_lat": float(self.bbox_max_lat.get()),
                    "max_lon": float(self.bbox_max_lon.get()),
                }
            except ValueError:
                raise ValueError("Bounding box values must be numbers (all four fields).")

        countries = [c.strip() for c in self.countries_var.get().split(",") if c.strip()]

        filters = {
            "require_name": self.require_name_var.get(),
            "require_latlon": self.require_latlon_var.get(),
            "exclude_indoor": self.exclude_indoor_var.get(),
            "exclude_closed": self.exclude_closed_var.get(),
            "include_restricted": self.include_restricted_var.get(),
            "exclude_via_ferrata": self.exclude_via_ferrata_var.get(),
            "exclude_ice": self.exclude_ice_var.get(),
        }

        min_routes = _safe_int(self.min_routes_var.get())
        if min_routes is not None:
            filters["min_routes"] = min_routes
        min_quality = _safe_float(self.min_quality_var.get())
        if min_quality is not None:
            filters["min_quality_score"] = min_quality

        scope: dict[str, object] = {"map_path": self.map_path_var.get().strip()}
        if countries:
            scope["countries"] = countries
        if bbox:
            scope["bbox"] = bbox

        sources_config = []
        for name in selected_sources:
            entry = {"name": name, "options": {"base_url": self.base_url_var.get().strip()}}
            sources_config.append(entry)

        return {"sources": sources_config, "scope": scope, "filters": filters}


def main() -> None:
    root = tk.Tk()
    ScraperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
