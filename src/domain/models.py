from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# Campos civis obrigatórios para que um registro seja utilizável em análise entre postos
ESSENTIAL_CIVIL_FIELDS: tuple[str, ...] = ("cpf", "birth_date", "sex", "city")

@dataclass
class ConsultationRecord:
    """Dados brutos de consulta, no formato local de um único posto de saúde"""
    consultation_id: str
    source_post: str

    cpf: Optional[str] = None
    name: Optional[str] = None
    birth_date: Optional[str] = None
    sex: Optional[str] = None
    city: Optional[str] = None

    icd: Optional[str] = None          
    blood_pressure: Optional[str] = None
    weight: Optional[str] = None

    format_inconsistencies: int = 0    # campos entregues fora do padrão
    missing_fields: int = 0            # campos civis essenciais ausentes


@dataclass
class StandardizedRecord:
    """Registro após ser processado pelo banco de dados do SUS (normalizado e padronizado)"""
    consultation_id: str
    source_post: str
    data: dict = field(default_factory=dict)

    corrected_formats: int = 0         # problemas de formato corrigidos com sucesso
    uncorrected_formats: int = 0       # problemas de formato deixados sem resolução
    unresolved_missing: int = 0        # dados civis ausentes não preenchidos
    filled_by_national: int = 0        # campos civis completados pela base nacional (cB)
    analysis_ready: bool = False       # todos os campos civis presentes + padronizados
