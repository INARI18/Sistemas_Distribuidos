"""Health post actor.

Each post runs on its own thread, generates local consultations and sends
them to the SUS database. Posts never message one another: the database is
the only reachable actor, mirroring isolated containers on a network.
"""

from __future__ import annotations

import queue
import threading
import time

from ..generation import RecordGenerator, RegionalProfile
from .messages import IngestRequest
from .sus_database import SusDatabase

# Simulated one-way network latency between a post and the database.
NETWORK_LATENCY_SECONDS = 0.0008


class HealthPost(threading.Thread):
    """Generates and submits consultation records to the SUS database."""

    def __init__(self, post_id: str, consultations: int, seed: int, database: SusDatabase):
        super().__init__(name=post_id, daemon=True)
        self.post_id = post_id
        self.consultations = consultations
        self._generator = RecordGenerator(RegionalProfile(seed))
        self._database = database

        self.sent = 0
        self.acknowledged = 0
        self.response_times_ms: list[float] = []

    def run(self) -> None:
        reply: "queue.Queue[bool]" = queue.Queue()
        for record in self._generator.generate(self.post_id, self.consultations):
            start = time.perf_counter()
            time.sleep(NETWORK_LATENCY_SECONDS)            # request travels out
            self._database.inbox.put(IngestRequest(record, reply))
            self.sent += 1
            ok = reply.get()                               # await acknowledgement
            time.sleep(NETWORK_LATENCY_SECONDS)            # response travels back
            self.response_times_ms.append((time.perf_counter() - start) * 1000)
            if ok:
                self.acknowledged += 1
