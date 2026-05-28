"""Domain layer: core data structures shared across the simulation."""

from .models import (
    ESSENTIAL_CIVIL_FIELDS,
    ConsultationRecord,
    StandardizedRecord,
)

__all__ = [
    "ESSENTIAL_CIVIL_FIELDS",
    "ConsultationRecord",
    "StandardizedRecord",
]
