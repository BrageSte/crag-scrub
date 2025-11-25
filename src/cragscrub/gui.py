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
        self.master.geometry("640x520")
        self.pack(fill=tk.BOTH, expand=True)

        self.config_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.geojson_var = tk.StringVar()

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

        if not config_path or not Path(config_path).exists():
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


def main() -> None:
    root = tk.Tk()
    ScraperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
