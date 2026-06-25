"""Central SUS database core.

The transport-free heart of the central database: it standardizes the formats
it recognizes, stores each record and keeps the metric counters. It knows
nothing about HTTP or containers -- the network layer (``src/net``) wraps it
and exposes it as the ``sus-database`` service.

In Scenario A there is no national general database, so this core can only fix
*format* inconsistencies. Essential civil data that arrived missing (or in an
unrecognizable form) cannot be filled in, since there is no external
authoritative source to consult.
"""

from __future__ import annotations

from .domain import ESSENTIAL_CIVIL_FIELDS, ConsultationRecord, StandardizedRecord
from .standardization import FieldNormalizer, default_normalizers

# Simulated cost of processing a single record inside the database.
PROCESSING_DELAY_SECONDS = 0.0005


class IngestionEngine:
    """Standardizes and stores records, tracking the quality counters."""

    def __init__(self, normalizers: list[FieldNormalizer] | None = None):
        self._normalizers = {n.field_name: n for n in (normalizers or default_normalizers())}

        self.stored: list[StandardizedRecord] = []
        self.received = 0
        self.detected_inconsistencies = 0
        self.corrected_inconsistencies = 0

    def ingest(self, record: ConsultationRecord) -> StandardizedRecord:
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
