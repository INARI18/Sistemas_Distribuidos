"""
Pega o relatório com as métricas de ambos os cenários e produz uma tabela de comparação
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ComparisonReport:
    report_a: dict  
    report_b: dict 

    posts: int = 0
    consultations_per_post: int = 0
    base_seed: int = 0
    coverage: float = 0.0

    # Retorna a diferença (delta) entre os cenários para uma métrica específica
    def _delta(self, key: str) -> float:
        return self.report_b.get(key, 0) - self.report_a.get(key, 0)
    
    # Retorna um dicionário com todas as métricas e seus valores para os cenários
    def as_dict(self) -> dict:
        return {
            "posts": self.posts,
            "consultations_per_post": self.consultations_per_post,
            "base_seed": self.base_seed,
            "coverage": self.coverage,
            "scenario_a": self.report_a,
            "scenario_b": self.report_b,
            "deltas": {
                "access_rate": self._delta("access_rate"),
                "utilization_rate": self._delta("utilization_rate"),
                "missing_recovery_rate": self._delta("missing_recovery_rate"),
                "integrated_volume": self._delta("integrated_volume"),
                "average_response_time_ms": self._delta("average_response_time_ms"),
            },
        }

    def render(self) -> str:
        """Retorna a tabela de comparacao"""
        a, b = self.report_a, self.report_b
        total = self.posts * self.consultations_per_post

        header = (
            f"=== A x B comparison over the same data "
            f"(seed={self.base_seed}, posts={self.posts}, "
            f"{self.consultations_per_post} records/post = {total} total, "
            f"coverage={self.coverage:.2f}) ==="
        )

        def pct_row(label, key):
            va, vb = a.get(key, 0.0), b.get(key, 0.0)
            return _row(label, f"{va * 100:.2f}%", f"{vb * 100:.2f}%", f"{(vb - va) * 100:+.2f} pp")

        def int_row(label, key):
            va, vb = a.get(key, 0), b.get(key, 0)
            return _row(label, str(va), str(vb), f"{vb - va:+d}")

        def ms_row(label, key):
            va, vb = a.get(key, 0.0), b.get(key, 0.0)
            return _row(label, f"{va:.2f} ms", f"{vb:.2f} ms", f"{vb - va:+.2f} ms")

        lines = [
            header,
            "",
            _row("Metric", "Scenario A", "Scenario B", "B - A", head=True),
            "  " + "-" * 66,
            pct_row("Access rate", "access_rate"),
            pct_row("Utilization rate", "utilization_rate"),
            int_row("Integrated volume", "integrated_volume"),
            pct_row("Missing-data recovery", "missing_recovery_rate"),
            ms_row("Avg response time", "average_response_time_ms"),
        ]
        lines += self._render_recovery()
        lines += [
            "",
            "  Note: both scenarios ran as containers over the same generated data,",
            "  so access rate and integrated volume match; A cannot recover missing",
            "  civil data (no national base), so its utilization and missing-data",
            "  recovery stay lower.",
        ]
        return "\n".join(lines)

    def _render_recovery(self) -> list[str]:
        """Por campo: quanto dos dados civis faltantes de A o B recuperou."""
        missing = self.report_a.get("missing_by_field") or {}
        if not missing:
            return []
        recovered = self.report_b.get("recovered_by_field") or {}
        lines = ["", "  Civil data recovered by the national base (Scenario B):"]
        for name, count in missing.items():
            got = recovered.get(name, 0)
            label = f"{name} ".ljust(14, ".")
            note = " (never recoverable: no CPF, no identity)" if name == "cpf" and got == 0 else ""
            lines.append(f"    {label} {got:>4}/{count:<4} missing recovered{note}")
        return lines


def _row(label: str, a: str, b: str, d: str, head: bool = False) -> str:
    """Uma linha de tabela de largura fixa."""
    label_cell = label if head else f"{label} ".ljust(28, ".")
    return f"  {label_cell:<28} {a:>13} {b:>13} {d:>12}"
