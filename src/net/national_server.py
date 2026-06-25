"""HTTP server fronting the national general database (Scenario B).

The network-facing face of :class:`~src.national.NationalDatabase`. It runs as
the ``national-database`` container and is reachable by exactly one actor -- the
central SUS database -- mirroring the proposal's rule that the national database
talks only to the central database, never to a post.

Endpoints:

- ``POST /reconcile`` -- given one record as the central DB standardized it,
  return the essential civil fields the national DB can supply.
- ``GET /health``     -- readiness probe so the central DB can wait for it.

Unlike the central database, the national database does not finalize on its own:
it stays up serving reconcile requests until the run tears it down, because it
has no view of when the posts go quiet.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..national import NationalDatabase
from . import protocol


def _make_handler(national: NationalDatabase):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args) -> None:  # noqa: D401
            pass

        def _send_json(self, status: int, body: dict) -> None:
            payload = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            return json.loads(raw.decode("utf-8"))

        def do_GET(self) -> None:
            if self.path == protocol.PATH_HEALTH:
                self._send_json(200, {"status": "ok"})
            else:
                self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path == protocol.PATH_RECONCILE:
                data = self._read_json().get("data", {})
                result = national.reconcile(data)
                self._send_json(
                    200,
                    protocol.reconcile_response(
                        filled=result.filled,
                        identifiable=result.identifiable,
                        on_file=result.on_file,
                    ),
                )
            else:
                self._send_json(404, {"error": "not found"})

    return Handler


def serve(host: str, port: int, coverage: float) -> None:
    """Serve reconcile requests until the container is stopped."""
    national = NationalDatabase(coverage=coverage)
    httpd = ThreadingHTTPServer((host, port), _make_handler(national))
    print(
        f"[national-database] listening on {host}:{port}; "
        f"registry coverage {coverage:.0%}",
        flush=True,
    )
    httpd.serve_forever()
