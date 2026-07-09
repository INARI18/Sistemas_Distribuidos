"""Cliente que o banco de dados central usa para alcançar a base nacional (Cenário B).
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
    """A resposta da base nacional"""
    filled: dict = field(default_factory=dict)
    identifiable: bool = False
    on_file: bool = False


class NationalClient:
    """Cliente HTTP para a base nacional, usado apenas pelo banco de dados central."""

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
        """Bloqueia até a base nacional responder sua sonda de saúde."""
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
