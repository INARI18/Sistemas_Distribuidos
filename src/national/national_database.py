"""Núcleo da base nacional:
- Um paciente só pode ser localizado quando o registro traz o cpf
- O registro não contém toda a população.
"""

from __future__ import annotations
import random
import re
import zlib
from dataclasses import dataclass, field
from ..domain import ESSENTIAL_CIVIL_FIELDS

_CANONICAL_CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_CITIES = (
    "Florianopolis", "Joinville", "Blumenau", "Chapeco", "Criciuma", "Alegrete",
    "Pelotas", "Santa Maria", "Caxias do Sul", "Porto Alegre", "Rio de Janeiro",
    "Sao Paulo", "Belo Horizonte", "Brasilia", "Salvador", "Fortaleza",
)


@dataclass(frozen=True)
class ReconciliationResult:
    """Resultado de consultar a base nacional para um único registro"""
    filled: dict = field(default_factory=dict)  
    identifiable: bool = False             # tinha cpf valido      
    on_file: bool = False                  # estava cadastrado na base   


class NationalDatabase:
    """Completa os dados civis que o banco central não conseguiu resolver sozinho"""

    def __init__(self, coverage: float = 0.9):
        self._coverage = max(0.0, min(1.0, coverage))

    def reconcile(self, data: dict) -> ReconciliationResult:
        """Retorna os campos civis canônicos que o BD central ainda não tem."""
        cpf = data.get("cpf")
        if not cpf or not _CANONICAL_CPF.fullmatch(cpf):
            # n tem cpf, nao é identificável
            return ReconciliationResult(identifiable=False, on_file=False)

        if not self._on_file(cpf):
            # identificavel, mas nao ta na base nacional
            return ReconciliationResult(identifiable=True, on_file=False)

        filled = {
            name: self._authoritative_value(name, cpf)
            for name in ESSENTIAL_CIVIL_FIELDS
            if data.get(name) is None
        }
        return ReconciliationResult(filled=filled, identifiable=True, on_file=True)

    def _on_file(self, cpf: str) -> bool:
        bucket = zlib.crc32(b"on-file:" + cpf.encode()) % 1000
        return bucket < int(self._coverage * 1000)

    def _authoritative_value(self, field_name: str, cpf: str) -> str:
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
