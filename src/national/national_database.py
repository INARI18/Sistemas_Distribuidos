"""National general database core (Scenario B).

The authoritative civil registry of the simulation. It is the new actor that
distinguishes Scenario B from Scenario A: it talks **only** to the central SUS
database and, for each record the central database could not fully complete on
its own, supplies the essential civil fields in canonical form.

Like the central database core, this layer is transport-free: it knows nothing
about HTTP or containers. The ``src/net`` layer wraps it and exposes it as the
``national-database`` service the central database queries over the network.

It is *not* an oracle. Two real-world limits keep Scenario B below a perfect
score, exactly as the proposal expects:

- **Identification.** A patient can only be looked up when the record carries a
  usable identifier. The CPF is that anchor: if it arrived missing (so the
  central database left it ``None``), the patient cannot be matched and the
  record stays incomplete.
- **Coverage.** The registry does not contain the whole population. A fixed
  ``coverage`` fraction of identifiable patients are actually on file; the rest
  cannot be completed even though they were identified. The decision is taken
  deterministically from the CPF, so a run stays reproducible.
"""

from __future__ import annotations

import random
import re
import zlib
from dataclasses import dataclass, field

from ..domain import ESSENTIAL_CIVIL_FIELDS

# Canonical forms the central database produces; the national database must
# return values in the very same forms so they count as standard downstream.
_CANONICAL_CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_CITIES = ("Florianopolis", "Joinville", "Blumenau", "Chapeco", "Criciuma")


@dataclass(frozen=True)
class ReconciliationResult:
    """Outcome of consulting the national database for a single record."""

    filled: dict = field(default_factory=dict)  # field -> canonical value supplied
    identifiable: bool = False                   # patient could be matched (usable CPF)
    on_file: bool = False                        # patient was present in the registry


class NationalDatabase:
    """Completes the civil data the central database could not resolve alone."""

    def __init__(self, coverage: float = 0.9):
        # Share of identifiable patients the registry actually holds on file.
        self._coverage = max(0.0, min(1.0, coverage))

    def reconcile(self, data: dict) -> ReconciliationResult:
        """Return the canonical civil fields the central DB still lacks.

        ``data`` is the record as the central database standardized it: an
        essential field set to ``None`` means it arrived missing (or in an
        unrecognizable form) and could not be completed locally.
        """
        cpf = data.get("cpf")
        if not cpf or not _CANONICAL_CPF.fullmatch(cpf):
            # No usable identifier -> the patient cannot be looked up.
            return ReconciliationResult(identifiable=False, on_file=False)

        if not self._on_file(cpf):
            # Identifiable, but not in the national registry's coverage.
            return ReconciliationResult(identifiable=True, on_file=False)

        filled = {
            name: self._authoritative_value(name, cpf)
            for name in ESSENTIAL_CIVIL_FIELDS
            if data.get(name) is None
        }
        return ReconciliationResult(filled=filled, identifiable=True, on_file=True)

    def _on_file(self, cpf: str) -> bool:
        """Deterministic, reproducible coverage gate keyed on the CPF."""
        bucket = zlib.crc32(b"on-file:" + cpf.encode()) % 1000
        return bucket < int(self._coverage * 1000)

    def _authoritative_value(self, field_name: str, cpf: str) -> str:
        """The registry's canonical value for one field of an identified patient.

        Values are derived deterministically from the CPF so the same patient
        always resolves to the same civil data across records and runs.
        """
        rng = random.Random(zlib.crc32(f"{field_name}:{cpf}".encode()))
        if field_name == "cpf":
            return cpf
        if field_name == "birth_date":
            return f"{rng.randint(1940, 2015):04d}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        if field_name == "sex":
            return rng.choice(("M", "F"))
        if field_name == "city":
            return rng.choice(_CITIES)
        return ""
