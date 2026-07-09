"""Servidor HTTP que simula o banco de dados do SUS. """
from __future__ import annotations
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from statistics import mean
from ..database import PROCESSING_DELAY_SECONDS, IngestionEngine, Reconciler
from ..metrics import SimulationReport, write_report
from . import protocol

SCENARIO_NAMES = {
    "A": "Scenario A - no national general database (Docker)",
    "B": "Scenario B - with national general database (Docker)",
}


class DatabaseState:
    def __init__(self, scenario: str = "A", national: Reconciler | None = None):
        self.scenario = scenario.upper()
        self._engine = IngestionEngine(national=national)
        self._lock = threading.Lock()

        self.sent_records = 0
        self.response_times_ms: list[float] = []
        self.completed_posts = 0
        self._next_index = 0
        self._last_activity = time.monotonic()

    def _touch(self) -> None:
        self._last_activity = time.monotonic()

    def claim_index(self) -> int:
        """Retorna um índice único para o posto que está iniciando a ingestão de registros"""
        with self._lock:
            index = self._next_index
            self._next_index += 1
            self._touch()
            return index

    def ingest(self, record) -> None:
        # Modela o custo de processamento por registro do banco de dados.
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
                scenario=SCENARIO_NAMES.get(self.scenario, SCENARIO_NAMES["A"]),
                sent_records=self.sent_records,
                received_records=self._engine.received,
                integrated_volume=self._engine.integrated_volume,
                analysis_ready_records=self._engine.analysis_ready_count,
                average_response_time_ms=(
                    mean(self.response_times_ms) if self.response_times_ms else 0.0
                ),
                missing_by_field=dict(self._engine.missing_by_field),
                recovered_by_field=dict(self._engine.recovered_by_field),
            )


def _make_handler(state: DatabaseState):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *args) -> None:
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
            if self.path == protocol.PATH_CLAIM:
                self._send_json(200, {"index": state.claim_index()})
            elif self.path == protocol.PATH_INGEST:
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


def serve(
    host: str,
    port: int,
    idle_timeout: float,
    scenario: str = "A",
    national: Reconciler | None = None,
    report_dir: str | None = None,
) -> None:
   
    state = DatabaseState(scenario=scenario, national=national)
    httpd = ThreadingHTTPServer((host, port), _make_handler(state))

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    print(
        f"[sus-database] listening on {host}:{port}; "
        f"running {SCENARIO_NAMES.get(state.scenario, SCENARIO_NAMES['A'])}; "
        f"will finalize after {idle_timeout:.0f}s of inactivity",
        flush=True,
    )

    while not (state.has_data and state.idle_seconds() >= idle_timeout):
        time.sleep(0.25)

    report = state.build_report()
    print("\n" + report.render() + "\n", flush=True)

    if report_dir:
        _persist_report(report, report_dir, state.scenario)

    httpd.shutdown()
    print(
        f"[sus-database] {state.completed_posts} post(s) reported; shutting down.",
        flush=True,
    )


def _persist_report(report: SimulationReport, report_dir: str, scenario: str) -> None:
    """Grava o relatório em disco"""
    try:
        paths = write_report(report, report_dir, f"report-scenario-{scenario.lower()}")
        print(f"[sus-database] report written to: {', '.join(paths)}", flush=True)
    except OSError as exc:
        print(f"[sus-database] could not write report files: {exc}", flush=True)
