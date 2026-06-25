"""Client the central database uses to reach the national database (Scenario B).

This is the network-facing counterpart of :class:`~src.national.NationalDatabase`.
It implements the same ``reconcile(data) -> result`` shape the
:class:`~src.database.IngestionEngine` expects, but each call is a real HTTP
round-trip to the ``national-database`` container. The engine cannot tell the
difference between this client and an in-process national database -- that is
the Dependency Inversion the engine relies on.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from . import protocol


@dataclass(frozen=True)
class RemoteReconciliation:
    """The national DB's reply, in the shape the engine reads (``.filled``)."""

    filled: dict = field(default_factory=dict)
    identifiable: bool = False
    on_file: bool = False


class NationalClient:
    """HTTP client to the national database, used only by the central DB."""

    def __init__(self, base_url: str):
        self._reconcile_url = base_url.rstrip("/") + protocol.PATH_RECONCILE
        self._base_url = base_url

    def reconcile(self, data: dict) -> RemoteReconciliation:
        body = json.dumps(protocol.reconcile_request(data)).encode("utf-8")
        request = urllib.request.Request(
            self._reconcile_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return RemoteReconciliation(
            filled=payload.get("filled", {}),
            identifiable=payload.get("identifiable", False),
            on_file=payload.get("on_file", False),
        )

    def wait_until_ready(self, timeout_s: float = 60.0) -> None:
        """Block until the national database answers its health probe."""
        health_url = self._base_url.rstrip("/") + protocol.PATH_HEALTH
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                with urllib.request.urlopen(health_url, timeout=2.0) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, ConnectionError, OSError):
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"national database at {self._base_url} did not become ready in {timeout_s}s"
                )
            time.sleep(0.5)
