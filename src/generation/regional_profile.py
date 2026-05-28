"""Regional profile: how a given health post formats and omits data.

Each post is assigned a profile that decides which (non-canonical) format it
uses for each field and how often it leaves essential fields blank. This is
what makes records from different municipalities incompatible with each other.
"""

from __future__ import annotations

import random


class RegionalProfile:
    """Deterministic per-post formatting behaviour, driven by a seed."""

    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.cpf_style = self.rng.choice(["canonical", "no_punctuation", "spaced"])
        self.date_style = self.rng.choice(["iso", "br_slash", "br_dash"])
        self.sex_style = self.rng.choice(["letter", "number", "spelled_out"])
        # Probability that any single essential civil field is left blank.
        self.missing_probability = self.rng.uniform(0.05, 0.30)

    def format_cpf(self, canonical: str) -> tuple[str, bool]:
        """Return (formatted_value, is_out_of_standard)."""
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
