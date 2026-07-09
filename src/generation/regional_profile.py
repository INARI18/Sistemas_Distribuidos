"""Perfil regional: como um determinado posto de saúde formata e omite dados.
Cada posto recebe um perfil que decide qual formato ele usa
para cada campo e com que frequência deixa campos essenciais em branco. 
"""

from __future__ import annotations
import random

class RegionalProfile:
    """Comportamento de formatação determinístico por posto (seed)"""

    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.cpf_style = self.rng.choice(["canonical", "no_punctuation", "spaced"])
        self.date_style = self.rng.choice(["iso", "br_slash", "br_dash"])
        self.sex_style = self.rng.choice(["letter", "number", "spelled_out"])
        # Probabilidade de qualquer campo civil essencial ser deixado em branco.
        self.missing_probability = self.rng.uniform(0.05, 0.30)

    def format_cpf(self, canonical: str) -> tuple[str, bool]:
        """Retorna (valor_formatado, esta_fora_do_padrao)."""
        if self.cpf_style == "canonical":
            return canonical, False
        if self.cpf_style == "no_punctuation":
            return canonical.replace(".", "").replace("-", ""), True
        return canonical.replace(".", " ").replace("-", " "), True

    def format_date(self, day: int, month: int, year: int) -> tuple[str, bool]:
        if self.date_style == "iso":
            return f"{year:04d}-{month:02d}-{day:02d}", False
        if self.date_style == "br_slash":
            return f"{day:02d}/{month:02d}/{year:04d}", True
        return f"{day:02d}-{month:02d}-{year:04d}", True

    def format_sex(self, canonical: str) -> tuple[str, bool]:
        if self.sex_style == "letter":
            return canonical, False
        if self.sex_style == "number":
            return ("1" if canonical == "M" else "2"), True
        return ("Male" if canonical == "M" else "Female"), True
