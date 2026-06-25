"""Health post client.

Each health post runs as its own ``health-post`` container: it generates local
consultations and submits them, one by one, to the central SUS database over
HTTP -- never to a peer. It measures the real round-trip time of each
submission and, when finished, reports its summary so the database can compute
the access-rate and response-time metrics.
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
    """Block until the database's health probe answers (or time out).

    Container start order is not guaranteed, so a freshly started post may race
    ahead of the database. Polling the health endpoint removes that race.
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


def run_post(post_id: str, consultations: int, seed: int, base_url: str) -> None:
    """Generate records and submit them to the database, then report summary."""
    wait_for_database(base_url)

    generator = RecordGenerator(RegionalProfile(seed))
    ingest_url = base_url + protocol.PATH_INGEST

    sent = 0
    response_times_ms: list[float] = []

    print(f"[{post_id}] sending {consultations} records to {base_url}", flush=True)
    for record in generator.generate(post_id, consultations):
        start = time.perf_counter()
        _post_json(ingest_url, protocol.record_to_json(record))   # real round-trip
        response_times_ms.append((time.perf_counter() - start) * 1000)
        sent += 1

    _post_json(
        base_url + protocol.PATH_COMPLETE,
        protocol.completion_payload(post_id, sent, response_times_ms),
    )
    print(f"[{post_id}] done: {sent} records sent.", flush=True)
