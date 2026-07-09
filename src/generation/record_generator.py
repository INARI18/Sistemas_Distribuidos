"""Geração de registros de consulta contendo inconsistências regionais"""

from __future__ import annotations
import random
from typing import Iterator
from ..domain import ConsultationRecord
from .regional_profile import RegionalProfile

_NAMES = [
    "Ana Souza", "Bruno Lima", "Carla Dias", "Diego Alves", "Elena Rocha",
    "Felipe Castro", "Gabriela Nunes", "Hugo Pereira", "Iara Mendes", "Joao Vaz",
    "Karla Silva", "Lucas Costa", "Mariana Teixeira", "Nicolas Fernandes",
    "Olivia Martins", "Paulo Cardoso", "Quintino Ribeiro",
]
_CITIES = ["Florianopolis", "Joinville", "Blumenau", "Chapeco", "Criciuma", "Alegrete", 
           "Pelotas", "Santa Maria", "Caxias do Sul", "Porto Alegre", "Rio de Janeiro", "Sao Paulo", 
           "Belo Horizonte", "Brasilia", "Salvador", "Fortaleza"
]
_ICDS = ["J11", "I10", "E11", "K21", "M54", "R51", "A09"] 

# gera um cpf aleatório para atribuir a um paciente
def _random_cpf(rng: random.Random) -> str:
    n = [rng.randint(0, 9) for _ in range(11)]
    return f"{n[0]}{n[1]}{n[2]}.{n[3]}{n[4]}{n[5]}.{n[6]}{n[7]}{n[8]}-{n[9]}{n[10]}"


class RecordGenerator:
    """Produz registros de consulta para um único posto usando seu perfil"""
    def __init__(self, profile: RegionalProfile):
        self._profile = profile
        self._rng = profile.rng 

    def generate(self, post_id: str, count: int) -> Iterator[ConsultationRecord]:
        for index in range(count):
            yield self._build_one(post_id, index)

    def _build_one(self, post_id: str, index: int) -> ConsultationRecord:
        rng = self._rng
        record = ConsultationRecord(
            consultation_id=f"{post_id}-{index:04d}",
            source_post=post_id,
            name=rng.choice(_NAMES),
        )
        format_issues = 0
        missing = 0

        # CPF
        if rng.random() < self._profile.missing_probability:
            missing += 1
        else:
            value, off_standard = self._profile.format_cpf(_random_cpf(rng))
            record.cpf = value
            format_issues += int(off_standard)

        # Data de nascimento
        if rng.random() < self._profile.missing_probability:
            missing += 1
        else:
            value, off_standard = self._profile.format_date(
                rng.randint(1, 28), rng.randint(1, 12), rng.randint(1940, 2015)
            )
            record.birth_date = value
            format_issues += int(off_standard)

        # Sexo
        if rng.random() < self._profile.missing_probability:
            missing += 1
        else:
            value, off_standard = self._profile.format_sex(rng.choice(["M", "F"]))
            record.sex = value
            format_issues += int(off_standard)

        # Cidade
        if rng.random() < self._profile.missing_probability:
            missing += 1
        else:
            record.city = rng.choice(_CITIES)

        # Dados clínicos
        record.icd = rng.choice(_ICDS)
        record.blood_pressure = f"{rng.randint(10, 16)}x{rng.randint(6, 10)}"
        record.weight = str(rng.randint(50, 110))

        record.format_inconsistencies = format_issues
        record.missing_fields = missing
        return record
