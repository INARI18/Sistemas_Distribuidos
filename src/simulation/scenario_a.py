"""Scenario A orchestration.

Wires the actors together, runs the simulation and assembles the metrics
report. This module is the composition point for Scenario A: it owns the
lifecycle of the threads but delegates every real responsibility to the
layers below it.

Scenario A = isolated health posts + a central SUS database, with NO national
general database. It is the baseline against which Scenario B (to be added
later) will be compared.
"""

from __future__ import annotations

from statistics import mean

from ..actors import HealthPost, SusDatabase
from ..config import SimulationConfig
from ..metrics import SimulationReport

SCENARIO_NAME = "Scenario A - no national general database"


class ScenarioA:
    def __init__(self, config: SimulationConfig | None = None):
        self.config = config or SimulationConfig()

    def run(self) -> SimulationReport:
        database = SusDatabase()
        database.start()

        posts = [
            HealthPost(
                post_id=f"post-{i + 1}",
                consultations=self.config.consultations_per_post,
                seed=self.config.post_seed(i),
                database=database,
            )
            for i in range(self.config.post_count)
        ]

        for post in posts:
            post.start()
        for post in posts:
            post.join()

        # All posts done sending: let the database drain its inbox and stop.
        database.request_shutdown()
        database.join()

        return self._build_report(database, posts)

    @staticmethod
    def _build_report(database: SusDatabase, posts: list[HealthPost]) -> SimulationReport:
        response_times = [t for post in posts for t in post.response_times_ms]
        return SimulationReport(
            scenario=SCENARIO_NAME,
            sent_records=sum(p.sent for p in posts),
            received_records=database.received,
            integrated_volume=database.integrated_volume,
            analysis_ready_records=database.analysis_ready_count,
            detected_inconsistencies=database.detected_inconsistencies,
            corrected_inconsistencies=database.corrected_inconsistencies,
            average_response_time_ms=mean(response_times) if response_times else 0.0,
        )
