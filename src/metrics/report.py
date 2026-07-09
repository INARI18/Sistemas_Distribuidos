"""Agregação e geração de relatório de métricas.
Calcula as cinco métricas de comparação.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


@dataclass(frozen=True)
class SimulationReport:
    scenario: str

    sent_records: int
    received_records: int
    integrated_volume: int
    analysis_ready_records: int

    average_response_time_ms: float

    # quantos registros chegaram com campos civis faltantes e quantos
    # desses a base nacional recuperou (Cenário A é sempre 0).
    missing_by_field: dict = field(default_factory=dict)
    recovered_by_field: dict = field(default_factory=dict)

    @property
    def access_rate(self) -> float:
        """Fração dos registros enviados que chegaram ao banco de dados central."""
        return _safe_ratio(self.received_records, self.sent_records)

    @property
    def utilization_rate(self) -> float:
        """Fração dos registros integrados utilizáveis para análise."""
        return _safe_ratio(self.analysis_ready_records, self.integrated_volume)

    # Totais dos campos civis faltantes e dos que a base nacional recuperou.
    @property
    def missing_total(self) -> int:
        """Total de campos civis que chegaram faltantes."""
        return sum(self.missing_by_field.values())

    @property
    def recovered_total(self) -> int:
        """Total de campos faltantes que a base nacional recuperou (0 no Cenário A)."""
        return sum(self.recovered_by_field.values())

    @property
    def missing_recovery_rate(self) -> float:
        """Fração dos campos civis faltantes que a base nacional recuperou.

        É 0 no Cenário A (não há a quem consultar) e sobe no Cenário B -- é aqui
        que se vê o impacto da base nacional.
        """
        return _safe_ratio(self.recovered_total, self.missing_total)

    def as_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "access_rate": self.access_rate,
            "utilization_rate": self.utilization_rate,
            "integrated_volume": self.integrated_volume,
            "missing_recovery_rate": self.missing_recovery_rate,
            "average_response_time_ms": self.average_response_time_ms,
            "missing_by_field": dict(self.missing_by_field),
            "recovered_by_field": dict(self.recovered_by_field),
        }

    def render(self) -> str:
        pct = lambda x: f"{x * 100:6.2f}%"
        lines = [
            f"=== Simulation report: {self.scenario} ===",
            "",
            f"  Access rate ............... {pct(self.access_rate)}"
            f"   ({self.received_records}/{self.sent_records} records)",
            f"  Utilization rate .......... {pct(self.utilization_rate)}"
            f"   ({self.analysis_ready_records}/{self.integrated_volume} analysis-ready)",
            f"  Integrated data volume .... {self.integrated_volume} records",
            f"  Missing-data recovery ..... {pct(self.missing_recovery_rate)}"
            f"   ({self.recovered_total}/{self.missing_total} fields filled)",
            f"  Average response time ..... {self.average_response_time_ms:.2f} ms",
        ]
        lines += self._render_breakdown()
        return "\n".join(lines)

    def _render_breakdown(self) -> list[str]:
        """Tabela de faltantes/recuperados por campo"""
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
