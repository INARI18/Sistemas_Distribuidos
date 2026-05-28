"""Central SUS database actor.

Runs on its own thread and is the only actor a health post may talk to. It
receives records, standardizes the formats it recognizes and stores them.

In Scenario A there is no national general database, so this actor can only
fix *format* inconsistencies. Essential civil data that arrived missing (or
in an unrecognizable form) cannot be filled in, since there is no external
authoritative source to consult.
"""

from __future__ import annotations

import queue
import threading
import time

from ..domain import ESSENTIAL_CIVIL_FIELDS, ConsultationRecord, StandardizedRecord
from ..standardization import FieldNormalizer, default_normalizers
from .messages import IngestRequest

# Simulated cost of processing a single record inside the database.
PROCESSING_DELAY_SECONDS = 0.0005


class SusDatabase(threading.Thread):
    """Aggregates and standardizes records coming from the health posts."""

    def __init__(self, normalizers: list[FieldNormalizer] | None = None):
        super().__init__(name="SusDatabase", daemon=True)
        self.inbox: "queue.Queue[IngestRequest]" = queue.Queue()
        self._normalizers = {n.field_name: n for n in (normalizers or default_normalizers())}
        self._shutdown = threading.Event()

        self.stored: list[StandardizedRecord] = []
        self.received = 0
        self.detected_inconsistencies = 0
        self.corrected_inconsistencies = 0

    def request_shutdown(self) -> None:
        """Signal the actor to stop once its inbox has drained."""
        self._shutdown.set()

    def run(self) -> None:
        while not (self._shutdown.is_set() and self.inbox.empty()):
            try:
                request = self.inbox.get(timeout=0.05)
            except queue.Empty:
                continue
            time.sleep(PROCESSING_DELAY_SECONDS)
            self._ingest(request.record)
            request.reply_to.put(True)
            self.inbox.task_done()

    # ------------------------------------------------------------------ #

    def _ingest(self, record: ConsultationRecord) -> StandardizedRecord:
        self.received += 1
        data: dict = {}
        detected = 0
        corrected = 0
        uncorrected_formats = 0
        missing = 0

        for field in ESSENTIAL_CIVIL_FIELDS:
            raw = getattr(record, field)
            normalizer = self._normalizers.get(field)

            if normalizer is None:
                # Field without format variation: only presence matters.
                data[field] = raw
                if raw is None:
                    detected += 1
                    missing += 1
                continue

            result = normalizer.normalize(raw)
            data[field] = result.value
            if raw is None:
                detected += 1
                missing += 1
            elif result.was_corrected:
                detected += 1
                corrected += 1
            elif not result.recognized:
                detected += 1
                uncorrected_formats += 1
            # already-standard values are not inconsistencies

        # Non-essential fields are stored as received.
        data["name"] = record.name
        data["icd"] = record.icd
        data["blood_pressure"] = record.blood_pressure
        data["weight"] = record.weight

        analysis_ready = all(data.get(f) is not None for f in ESSENTIAL_CIVIL_FIELDS)

        self.detected_inconsistencies += detected
        self.corrected_inconsistencies += corrected

        standardized = StandardizedRecord(
            consultation_id=record.consultation_id,
            source_post=record.source_post,
            data=data,
            corrected_formats=corrected,
            uncorrected_formats=uncorrected_formats,
            unresolved_missing=missing,
            analysis_ready=analysis_ready,
        )
        self.stored.append(standardized)
        return standardized

    @property
    def integrated_volume(self) -> int:
        return len(self.stored)

    @property
    def analysis_ready_count(self) -> int:
        return sum(1 for r in self.stored if r.analysis_ready)
