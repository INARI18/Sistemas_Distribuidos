from __future__ import annotations
import csv
import json
import os
from .comparison import ComparisonReport
from .report import SimulationReport


def write_report(report: SimulationReport, out_dir: str, basename: str) -> list[str]:
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


def write_comparison(
    comparison: ComparisonReport, out_dir: str, basename: str
) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"{basename}.json")
    csv_path = os.path.join(out_dir, f"{basename}.csv")

    data = comparison.as_dict()
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    a, b, deltas = data["scenario_a"], data["scenario_b"], data["deltas"]
    metrics = [
        ("access_rate", a["access_rate"], b["access_rate"], deltas["access_rate"]),
        ("utilization_rate", a["utilization_rate"], b["utilization_rate"], deltas["utilization_rate"]),
        ("integrated_volume", a["integrated_volume"], b["integrated_volume"], deltas["integrated_volume"]),
        ("missing_recovery_rate", a["missing_recovery_rate"], b["missing_recovery_rate"], deltas["missing_recovery_rate"]),
        ("average_response_time_ms", a["average_response_time_ms"], b["average_response_time_ms"], deltas["average_response_time_ms"]),
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["metric", "scenario_a", "scenario_b", "delta_b_minus_a"])
        for name, va, vb, delta in metrics:
            writer.writerow([name, va, vb, delta])

    return [json_path, csv_path]
