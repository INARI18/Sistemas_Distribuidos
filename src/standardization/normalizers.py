"""Normalização de campos para a forma que o banco do SUS usa"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, Protocol

@dataclass(frozen=True)
class NormalizationResult:
    value: Optional[str]        
    already_standard: bool      # a entrada já estava na forma canônica
    recognized: bool            # a entrada pôde ser convertida para a forma canônica

    @property
    def was_corrected(self) -> bool:
        """True quando um valor fora do padrão foi padronizado com sucesso"""
        return self.recognized and not self.already_standard


class FieldNormalizer(Protocol):
    """Contrato que todo normalizador de campo deve satisfazer"""

    field_name: str

    def normalize(self, raw_value: Optional[str]) -> NormalizationResult:
        ...

_ABSENT = NormalizationResult(value=None, already_standard=True, recognized=True)

class CpfNormalizer:
    field_name = "cpf"
    _CANONICAL = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")

    def normalize(self, raw_value: Optional[str]) -> NormalizationResult:
        if raw_value is None:
            return _ABSENT
        already = bool(self._CANONICAL.fullmatch(raw_value))
        digits = re.sub(r"\D", "", raw_value)
        if len(digits) == 11:
            canon = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
            return NormalizationResult(canon, already, recognized=True)
        return NormalizationResult(None, already, recognized=False)


class BirthDateNormalizer:
    field_name = "birth_date"
    _ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
    _BR = re.compile(r"(\d{2})[/-](\d{2})[/-](\d{4})")

    def normalize(self, raw_value: Optional[str]) -> NormalizationResult:
        if raw_value is None:
            return _ABSENT
        if self._ISO.fullmatch(raw_value):
            return NormalizationResult(raw_value, already_standard=True, recognized=True)
        match = self._BR.fullmatch(raw_value)
        if match:
            day, month, year = match.groups()
            return NormalizationResult(f"{year}-{month}-{day}", False, recognized=True)
        return NormalizationResult(None, already_standard=False, recognized=False)


class SexNormalizer:
    field_name = "sex"
    _ALIASES = {"1": "M", "2": "F", "Male": "M", "Female": "F"}

    def normalize(self, raw_value: Optional[str]) -> NormalizationResult:
        if raw_value is None:
            return _ABSENT
        if raw_value in ("M", "F"):
            return NormalizationResult(raw_value, already_standard=True, recognized=True)
        canon = self._ALIASES.get(raw_value)
        return NormalizationResult(canon, already_standard=False, recognized=canon is not None)


def default_normalizers() -> list[FieldNormalizer]:
    """Fábrica do conjunto de normalizadores do banco do SUS"""
    return [CpfNormalizer(), BirthDateNormalizer(), SexNormalizer()]
