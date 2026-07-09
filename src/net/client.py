"""Posto de saúde
Gera consultas locais e as envia, uma a uma, ao banco de dados central do SUS
"""

from __future__ import annotations
import json
import time
import urllib.error
import urllib.request
from ..generation import RecordGenerator, RegionalProfile
from . import protocol


def _post_json(url: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_database(base_url: str, timeout_s: float = 60.0) -> None:
    """
    Garante que o banco de dados do SUS esteja pronto para receber registros
    """
    health_url = base_url + protocol.PATH_HEALTH
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            with urllib.request.urlopen(health_url, timeout=2.0) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        if time.monotonic() >= deadline:
            raise TimeoutError(f"database at {base_url} did not become ready in {timeout_s}s")
        time.sleep(0.5)


def claim_index(base_url: str) -> int:
    """Pede ao banco de dados o índice reproduzível deste posto"""
    reply = _post_json(base_url + protocol.PATH_CLAIM, {})
    return int(reply["index"])


def run_post(
    consultations: int,
    base_seed: int,
    base_url: str,
    post_index: int | None = None,
    post_id: str | None = None,
) -> None:
    
    wait_for_database(base_url)

    if post_index is None:
        post_index = claim_index(base_url)
    if post_id is None:
        post_id = f"post-{post_index + 1}"
    seed = base_seed + post_index * 1000

    generator = RecordGenerator(RegionalProfile(seed))
    ingest_url = base_url + protocol.PATH_INGEST

    sent = 0
    response_times_ms: list[float] = []

    print(f"[{post_id}] sending {consultations} records to {base_url}", flush=True)
    for record in generator.generate(post_id, consultations):
        start = time.perf_counter()
        _post_json(ingest_url, protocol.record_to_json(record))   
        response_times_ms.append((time.perf_counter() - start) * 1000)
        sent += 1

    _post_json(
        base_url + protocol.PATH_COMPLETE,
        protocol.completion_payload(post_id, sent, response_times_ms),
    )
    print(f"[{post_id}] done: {sent} records sent.", flush=True)
