"""HTTP server fronting the central SUS database.

This is the network-facing face of :class:`IngestionEngine`. It runs as the
``sus-database`` container and is the only actor a health post may reach: posts
submit records to it over HTTP and never to a peer.

Responsibilities:

- ``POST /ingest``  -- standardize and store one consultation record.
- ``POST /complete`` -- record a post's end-of-run summary (sent count and the
  round-trip times it measured), used for the access-rate and response-time
  metrics that can only be observed at the client.
- ``GET /report``   -- render the aggregated Scenario A metrics report.
- ``GET /health``   -- readiness probe so posts can wait for the DB to be up.

The server does not need to be told how many posts exist: it finalizes when the
traffic goes quiet. Once at least one record has arrived and nothing new has
come in for ``idle_timeout`` seconds, it prints the report and shuts down. That
is what lets ``docker compose up --scale health-post=N`` work with any N, no
coordination required.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from statistics import mean

from ..database import PROCESSING_DELAY_SECONDS, IngestionEngine
from ..metrics import SimulationReport
from . import protocol

SCENARIO_NAME = "Scenario A - no national general database (Docker)"


class DatabaseState:
    """Thread-safe aggregation of everything the report needs.

    The HTTP server is multi-threaded (one thread per connection), so several
    posts can be ingesting at once. A single lock guards both the ingestion
    engine and the client-side counters.
    """

    def __init__(self):
        self._engine = IngestionEngine()
        self._lock = threading.Lock()

        self.sent_records = 0
        self.response_times_ms: list[float] = []
        self.completed_posts = 0
        self._last_activity = time.monotonic()

    def _touch(self) -> None:
        self._last_activity = time.monotonic()

    def ingest(self, record) -> None:
        # Model the database's per-record processing cost.
        time.sleep(PROCESSING_DELAY_SECONDS)
        with self._lock:
            self._engine.ingest(record)
            self._touch()

    def complete(self, sent: int, response_times_ms: list[float]) -> int:
        with self._lock:
            self.sent_records += sent
            self.response_times_ms.extend(response_times_ms)
            self.completed_posts += 1
            self._touch()
            return self.completed_posts

    def idle_seconds(self) -> float:
        with self._lock:
            return time.monotonic() - self._last_activity

    @property
    def has_data(self) -> bool:
        return self._engine.received > 0

    def build_report(self) -> SimulationReport:
        with self._lock:
            return SimulationReport(
                scenario=SCENARIO_NAME,
                sent_records=self.sent_records,
                received_records=self._engine.received,
                integrated_volume=self._engine.integrated_volume,
                analysis_ready_records=self._engine.analysis_ready_count,
                detected_inconsistencies=self._engine.detected_inconsistencies,
                corrected_inconsistencies=self._engine.corrected_inconsistencies,
                average_response_time_ms=(
                    mean(self.response_times_ms) if self.response_times_ms else 0.0
                ),
            )


def _make_handler(state: DatabaseState):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        # Silence the default per-request logging; we log meaningful events.
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
            elif self.path == protocol.PATH_REPORT:
                self._send_json(200, state.build_report().as_dict())
            else:
                self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path == protocol.PATH_INGEST:
                record = protocol.record_from_json(self._read_json())
                state.ingest(record)
                self._send_json(200, {"ok": True})
            elif self.path == protocol.PATH_COMPLETE:
                body = self._read_json()
                done = state.complete(body["sent"], body["response_times_ms"])
                print(
                    f"[sus-database] post '{body['post_id']}' finished "
                    f"({done} post(s) done so far)",
                    flush=True,
                )
                self._send_json(200, {"ok": True})
            else:
                self._send_json(404, {"error": "not found"})

    return Handler


def serve(host: str, port: int, idle_timeout: float) -> None:
    """Serve until traffic goes quiet, then print the report and stop.

    Finalizes once at least one record has been ingested and no request has
    arrived for ``idle_timeout`` seconds -- so the post count never has to be
    declared up front and ``--scale`` works with any number of posts.
    """
    state = DatabaseState()
    httpd = ThreadingHTTPServer((host, port), _make_handler(state))

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    print(
        f"[sus-database] listening on {host}:{port}; "
        f"will finalize after {idle_timeout:.0f}s of inactivity",
        flush=True,
    )

    while not (state.has_data and state.idle_seconds() >= idle_timeout):
        time.sleep(0.25)

    print("\n" + state.build_report().render() + "\n", flush=True)

    httpd.shutdown()
    print(
        f"[sus-database] {state.completed_posts} post(s) reported; shutting down.",
        flush=True,
    )
