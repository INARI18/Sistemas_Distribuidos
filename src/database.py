"""Central SUS database core.

The transport-free heart of the central database: it standardizes the formats
it recognizes, stores each record and keeps the metric counters. It knows
nothing about HTTP or containers -- the network layer (``src/net``) wraps it
and exposes it as the ``sus-database`` service.

In Scenario A there is no national general database, so this core can only fix
*format* inconsistencies. Essential civil data that arrived missing (or in an
unrecognizable form) cannot be filled in, since there is no external
authoritative source to consult.

In Scenario B an authoritative *reconciler* (the national general database) is
injected. After the local standardization the engine consults it to complete
the civil fields it could not resolve on its own. The reconciler is only
referenced through the ``Reconciler`` protocol, so the engine does not care
whether it is an in-process object or an HTTP client to another container
(Dependency Inversion).
"""

from __future__ import annotations

from typing import Protocol

from .domain import ESSENTIAL_CIVIL_FIELDS, ConsultationRecord, StandardizedRecord
from .standardization import FieldNormalizer, default_normalizers

# Simulated cost of processing a single record inside the database.
PROCESSING_DELAY_SECONDS = 0.0005


class Reconciler(Protocol):
    """The authoritative source the engine consults in Scenario B."""

    def reconcile(self, data: dict):
        """Return an object whose ``.filled`` maps field -> canonical value."""
        ...


class IngestionEngine:
    """Standardizes and stores records, tracking the quality counters."""

    def __init__(
        self,
        normalizers: list[FieldNormalizer] | None = None,
        national: Reconciler | None = None,
    ):
        self._normalizers = {n.field_name: n for n in (normalizers or default_normalizers())}
        # Authoritative source for Scenario B; ``None`` means Scenario A.
        self._national = national

        self.stored: list[StandardizedRecord] = []
        self.received = 0
        self.detected_inconsistencies = 0
        self.corrected_inconsistencies = 0

        # Per-field breakdown: how many records arrived with each civil field
        # missing, and how many of those the national database recovered (B).
        self.missing_by_field = {f: 0 for f in ESSENTIAL_CIVIL_FIELDS}
        self.recovered_by_field = {f: 0 for f in ESSENTIAL_CIVIL_FIELDS}

    def ingest(self, record: ConsultationRecord) -> StandardizedRecord:
        self.received += 1
        data: dict = {}
        detected = 0
        corrected = 0
        uncorrected_formats = 0

        for field in ESSENTIAL_CIVIL_FIELDS:
            raw = getattr(record, field)
            if raw is None:
                self.missing_by_field[field] += 1
            normalizer = self._normalizers.get(field)

            if normalizer is None:
                # Field without format variation: only presence matters.
                data[field] = raw
                if raw is None:
                    detected += 1
                continue

            result = normalizer.normalize(raw)
            data[field] = result.value
            if raw is None:
                detected += 1
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

        # Scenario B: consult the national database for the civil fields that
        # the local standardization left unresolved (still ``None``).
        filled = 0
        if self._national is not None:
            outcome = self._national.reconcile(data)
            for civil_field, value in outcome.filled.items():
                if data.get(civil_field) is None and value is not None:
                    data[civil_field] = value
                    filled += 1
                    self.recovered_by_field[civil_field] += 1

        # After any reconciliation, an essential field still ``None`` is data
        # that no actor could supply -- the true residual gap.
        unresolved_missing = sum(1 for f in ESSENTIAL_CIVIL_FIELDS if data.get(f) is None)
        analysis_ready = unresolved_missing == 0

        self.detected_inconsistencies += detected
        self.corrected_inconsistencies += corrected + filled

        standardized = StandardizedRecord(
            consultation_id=record.consultation_id,
            source_post=record.source_post,
            data=data,
            corrected_formats=corrected,
            uncorrected_formats=uncorrected_formats,
            unresolved_missing=unresolved_missing,
            filled_by_national=filled,
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
