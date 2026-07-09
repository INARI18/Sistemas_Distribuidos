"""Núcleo do banco de dados central do SUS.
Padroniza os formatos que reconhece, armazena cada registro e mantém os
contadores de métricas. 
"""

from __future__ import annotations
from typing import Protocol
from .domain import ESSENTIAL_CIVIL_FIELDS, ConsultationRecord, StandardizedRecord
from .standardization import FieldNormalizer, default_normalizers

PROCESSING_DELAY_SECONDS = 0.0005


class Reconciler(Protocol):
    """Consulta o banco nacional para preencher campos civis faltantes de um registro"""
    def reconcile(self, data: dict):
        ...


class IngestionEngine:
    """Padroniza e armazena registros, controlando os contadores de qualidade"""
    def __init__(
        self,
        normalizers: list[FieldNormalizer] | None = None,
        national: Reconciler | None = None,
    ):
        self._normalizers = {n.field_name: n for n in (normalizers or default_normalizers())}
        self._national = national
        self.stored: list[StandardizedRecord] = []
        self.received = 0
        self.detected_inconsistencies = 0
        self.corrected_inconsistencies = 0

        # quantos registros chegaram com cada campo
        # civil faltante, e quantos desses a base nacional recuperou 
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

        # Campos não essenciais são armazenados como recebidos
        data["name"] = record.name
        data["icd"] = record.icd
        data["blood_pressure"] = record.blood_pressure
        data["weight"] = record.weight

        filled = 0
        if self._national is not None:
            outcome = self._national.reconcile(data)
            for civil_field, value in outcome.filled.items():
                if data.get(civil_field) is None and value is not None:
                    data[civil_field] = value
                    filled += 1
                    self.recovered_by_field[civil_field] += 1

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
