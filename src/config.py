"""Simulation configuration.

Centralizing the tunable parameters keeps the orchestration code declarative
and makes it trivial to reproduce a run (everything is seed-driven).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    post_count: int = 5                 # number of health posts (actors)
    consultations_per_post: int = 200   # records each post generates
    base_seed: int = 42                 # root seed for reproducibility

    def post_seed(self, index: int) -> int:
        """Deterministic, distinct seed per post."""
        return self.base_seed + index * 1000
