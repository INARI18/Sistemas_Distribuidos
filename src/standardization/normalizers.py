"""Field normalization strategies.

Each normalizer knows how to turn one field's many regional formats into a
single canonical form. They all implement the same `FieldNormalizer`
protocol, so the SUS database can hold a list of them and apply each one
without knowing the concrete type (Strategy pattern + Dependency Inversion).

Adding support for a new field means adding a new normalizer here -- no
existing class needs to change (Open/Closed principle).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class NormalizationResult:
    """Outcome of normalizing a single field value."""

    value: Optional[str]        # canonical value, or None if unrecognizable
    already_standard: bool      # input was already in canonical form
    recognized: bool            # input could be parsed into canonical form

    @property
    def was_corrected(self) -> bool:
        """True when a non-standard value was successfully standardized."""
        return self.recognized and not self.already_standard


class FieldNormalizer(Protocol):
    """Contract every field normalizer must satisfy."""

    field_name: str

    def normalize(self, raw_value: Optional[str]) -> NormalizationResult:
        ...


# A value that is absent is reported as standard + recognized so it does not
# count as a *format* error; missing data is tracked separately by the caller.
_ABSENT = NormalizationResult(value=None, already_standard=True, recognized=True)


class CpfNormalizer:
    """Canonical CPF form: 000.000.000-00."""

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
    """Canonical date form: YYYY-MM-DD."""

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
    """Canonical sex form: 'M' / 'F'."""

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
    """Factory for the normalizer set the SUS database uses by default."""
    return [CpfNormalizer(), BirthDateNormalizer(), SexNormalizer()]
