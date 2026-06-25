"""Wire protocol shared by the database server and the post clients.

Keeps the HTTP endpoint paths and the (de)serialization of the messages in one
place, so the server and the client can never disagree about the format. The
payloads are plain JSON built from the existing domain dataclasses -- the wire
is just a transport, the meaning lives in ``src/domain``.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..domain import ConsultationRecord

# HTTP endpoints exposed by the central database server.
PATH_INGEST = "/ingest"        # POST: a single consultation record
PATH_COMPLETE = "/complete"    # POST: a post's end-of-run summary
PATH_REPORT = "/report"        # GET:  the aggregated metrics report
PATH_HEALTH = "/health"        # GET:  readiness probe

# HTTP endpoint exposed by the national database server (Scenario B). The
# central database is the only actor that calls it.
PATH_RECONCILE = "/reconcile"  # POST: complete the civil data of one record


def record_to_json(record: ConsultationRecord) -> dict[str, Any]:
    """Serialize a consultation record for transport."""
    return asdict(record)


def record_from_json(payload: dict[str, Any]) -> ConsultationRecord:
    """Rebuild a consultation record received over the wire."""
    return ConsultationRecord(**payload)


def completion_payload(post_id: str, sent: int, response_times_ms: list[float]) -> dict[str, Any]:
    """Summary a post sends once it has finished submitting its records."""
    return {
        "post_id": post_id,
        "sent": sent,
        "response_times_ms": response_times_ms,
    }


def reconcile_request(data: dict[str, Any]) -> dict[str, Any]:
    """Request the central DB sends to the national DB for one record."""
    return {"data": data}


def reconcile_response(filled: dict[str, Any], identifiable: bool, on_file: bool) -> dict[str, Any]:
    """Reply the national DB sends back with the fields it could supply."""
    return {"filled": filled, "identifiable": identifiable, "on_file": on_file}
