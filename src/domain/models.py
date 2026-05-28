"""Core domain models.

This is the innermost layer of the project: plain data structures with no
dependencies on other modules. Every other layer may depend on the domain,
but the domain depends on nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Civil fields that are mandatory for a record to be usable in cross-post
# epidemiological analysis. If any of them is missing, records from different
# municipalities cannot be reliably linked.
ESSENTIAL_CIVIL_FIELDS: tuple[str, ...] = ("cpf", "birth_date", "sex", "city")


@dataclass
class ConsultationRecord:
    """Raw consultation data, in the local format of a single health post.

    Because each post follows its own questionnaire standard, the same fields
    may arrive in different formats or simply be absent.
    """

    consultation_id: str
    source_post: str

    # Patient civil data (may arrive in varied formats or empty).
    cpf: Optional[str] = None
    name: Optional[str] = None
    birth_date: Optional[str] = None
    sex: Optional[str] = None
    city: Optional[str] = None

    # Clinical data of the consultation.
    icd: Optional[str] = None          # ICD-10 diagnosis code
    blood_pressure: Optional[str] = None
    weight: Optional[str] = None

    # Quality annotations filled in at generation time. They act as the
    # ground truth used to cross-check the computed metrics.
    format_inconsistencies: int = 0    # fields delivered out of standard
    missing_fields: int = 0            # essential civil fields absent


@dataclass
class StandardizedRecord:
    """A record after being processed by the SUS central database."""

    consultation_id: str
    source_post: str
    data: dict = field(default_factory=dict)

    corrected_formats: int = 0         # format issues successfully fixed
    uncorrected_formats: int = 0       # format issues left unresolved
    unresolved_missing: int = 0        # absent civil data not filled in
    analysis_ready: bool = False       # all civil fields present + standard
