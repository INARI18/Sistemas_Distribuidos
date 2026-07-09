"""Protocolo de comunicação compartilhado pelo servidor do banco de dados e 
pelos clientes dos postos.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..domain import ConsultationRecord

# Endpoints HTTP expostos pelo servidor do banco de dados central.
PATH_CLAIM = "/claim"          
PATH_INGEST = "/ingest"        
PATH_COMPLETE = "/complete"    
PATH_REPORT = "/report"        
PATH_HEALTH = "/health"        
PATH_RECONCILE = "/reconcile" # base nacional

def record_to_json(record: ConsultationRecord) -> dict[str, Any]:
    """Serializa um registro de consulta para transporte"""
    return asdict(record)

def record_from_json(payload: dict[str, Any]) -> ConsultationRecord:
    """Reconstrói um registro de consulta recebido pela rede"""
    return ConsultationRecord(**payload)

def completion_payload(post_id: str, sent: int, response_times_ms: list[float]) -> dict[str, Any]:
    """Resumo que um posto envia após terminar de enviar seus registros"""
    return {
        "post_id": post_id,
        "sent": sent,
        "response_times_ms": response_times_ms,
    }

def reconcile_request(data: dict[str, Any]) -> dict[str, Any]:
    """Requisição que o banco central envia à base nacional"""
    return {"data": data}

def reconcile_response(filled: dict[str, Any], identifiable: bool, on_file: bool) -> dict[str, Any]:
    """Resposta que a base nacional envia de volta com os campos que conseguiu fornecer"""
    return {"filled": filled, "identifiable": identifiable, "on_file": on_file}
