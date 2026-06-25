"""Metrics aggregation and reporting.

Computes the five comparison metrics from the proposal diagram out of the raw
counters collected by the actors. Kept free of any threading/transport
concern so it can be unit-tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


@dataclass(frozen=True)
class SimulationReport:
    """The five metrics tracked by the proposal, plus their raw inputs."""

    scenario: str

    sent_records: int
    received_records: int
    integrated_volume: int
    analysis_ready_records: int

    detected_inconsistencies: int   # format issues + missing civil fields
    corrected_inconsistencies: int

    average_response_time_ms: float

    # Per civil field: how many records arrived with it missing, and how many
    # of those the national database recovered (always 0 in Scenario A).
    missing_by_field: dict = field(default_factory=dict)
    recovered_by_field: dict = field(default_factory=dict)

    # -- the five headline metrics ------------------------------------- #

    @property
    def access_rate(self) -> float:
        """Share of sent records that reached the central database."""
        return _safe_ratio(self.received_records, self.sent_records)

    @property
    def utilization_rate(self) -> float:
        """Share of integrated records usable for analysis."""
        return _safe_ratio(self.analysis_ready_records, self.integrated_volume)

    @property
    def inconsistency_correction_rate(self) -> float:
        """Share of detected inconsistencies that were corrected."""
        return _safe_ratio(self.corrected_inconsistencies, self.detected_inconsistencies)

    def as_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "access_rate": self.access_rate,
            "utilization_rate": self.utilization_rate,
            "integrated_volume": self.integrated_volume,
            "inconsistency_correction_rate": self.inconsistency_correction_rate,
            "average_response_time_ms": self.average_response_time_ms,
            "missing_by_field": dict(self.missing_by_field),
            "recovered_by_field": dict(self.recovered_by_field),
        }

    def render(self) -> str:
        """Human-readable summary for the console."""
        pct = lambda x: f"{x * 100:6.2f}%"
        lines = [
            f"=== Simulation report: {self.scenario} ===",
            "",
            f"  Access rate ............... {pct(self.access_rate)}"
            f"   ({self.received_records}/{self.sent_records} records)",
            f"  Utilization rate .......... {pct(self.utilization_rate)}"
            f"   ({self.analysis_ready_records}/{self.integrated_volume} analysis-ready)",
            f"  Integrated data volume .... {self.integrated_volume} records",
            f"  Inconsistency correction .. {pct(self.inconsistency_correction_rate)}"
            f"   ({self.corrected_inconsistencies}/{self.detected_inconsistencies} fixed)",
            f"  Average response time ..... {self.average_response_time_ms:.2f} ms",
        ]
        lines += self._render_breakdown()
        return "\n".join(lines)

    def _render_breakdown(self) -> list[str]:
        """Per-field missing/recovered table, shown when there is data for it."""
        if not self.missing_by_field:
            return []
        lines = [
            "",
            "  Missing civil data by field (recovered by national base):",
        ]
        for name, missing in self.missing_by_field.items():
            recovered = self.recovered_by_field.get(name, 0)
            label = f"{name} ".ljust(14, ".")
            lines.append(
                f"    {label} {missing:>4} missing, {recovered:>4} recovered"
            )
        return lines
