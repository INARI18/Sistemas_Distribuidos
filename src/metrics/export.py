"""Persist a :class:`SimulationReport` to disk, alongside the console log.

Two formats, each in its natural shape:

- **JSON** -- the complete report (every metric plus the per-field breakdown),
  handy for tooling or for diffing two runs.
- **CSV** -- just the per-field breakdown table (field, missing, recovered),
  which is genuinely tabular and opens straight in a spreadsheet.

The :class:`SimulationReport` itself stays a pure data object; all file I/O
lives here so the metrics computation has no side effects.
"""

from __future__ import annotations

import csv
import json
import os

from .report import SimulationReport


def write_report(report: SimulationReport, out_dir: str, basename: str) -> list[str]:
    """Write ``<basename>.json`` and ``<basename>.csv`` into ``out_dir``.

    Returns the paths written. Creates ``out_dir`` if needed.
    """
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"{basename}.json")
    csv_path = os.path.join(out_dir, f"{basename}.csv")

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report.as_dict(), fh, indent=2, ensure_ascii=False)

    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["field", "missing", "recovered_by_national"])
        for name, missing in report.missing_by_field.items():
            writer.writerow([name, missing, report.recovered_by_field.get(name, 0)])

    return [json_path, csv_path]
