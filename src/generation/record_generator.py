"""Generation of consultation records carrying regional inconsistencies."""

from __future__ import annotations

import random
from typing import Iterator

from ..domain import ConsultationRecord
from .regional_profile import RegionalProfile

_NAMES = [
    "Ana Souza", "Bruno Lima", "Carla Dias", "Diego Alves", "Elena Rocha",
    "Felipe Castro", "Gabriela Nunes", "Hugo Pereira", "Iara Mendes", "Joao Vaz",
]
_CITIES = ["Florianopolis", "Joinville", "Blumenau", "Chapeco", "Criciuma"]
_ICDS = ["J11", "I10", "E11", "K21", "M54", "R51", "A09"]


def _random_cpf(rng: random.Random) -> str:
    n = [rng.randint(0, 9) for _ in range(11)]
    return f"{n[0]}{n[1]}{n[2]}.{n[3]}{n[4]}{n[5]}.{n[6]}{n[7]}{n[8]}-{n[9]}{n[10]}"


class RecordGenerator:
    """Produces consultation records for a single post using its profile."""

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

        # Birth date
        if rng.random() < self._profile.missing_probability:
            missing += 1
        else:
            value, off_standard = self._profile.format_date(
                rng.randint(1, 28), rng.randint(1, 12), rng.randint(1940, 2015)
            )
            record.birth_date = value
            format_issues += int(off_standard)

        # Sex
        if rng.random() < self._profile.missing_probability:
            missing += 1
        else:
            value, off_standard = self._profile.format_sex(rng.choice(["M", "F"]))
            record.sex = value
            format_issues += int(off_standard)

        # City
        if rng.random() < self._profile.missing_probability:
            missing += 1
        else:
            record.city = rng.choice(_CITIES)

        # Clinical data: always present, contributes to data volume.
        record.icd = rng.choice(_ICDS)
        record.blood_pressure = f"{rng.randint(10, 16)}x{rng.randint(6, 10)}"
        record.weight = str(rng.randint(50, 110))

        record.format_inconsistencies = format_issues
        record.missing_fields = missing
        return record
