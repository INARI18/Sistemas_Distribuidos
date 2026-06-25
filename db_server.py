"""Entry point for the central SUS database container.

Reads its configuration from the environment (so it can be driven entirely by
docker-compose) and serves until the health posts go quiet, at which point it
prints the final report and exits.

Environment variables:
    HOST          bind address                                  (default 0.0.0.0)
    PORT          listen port                                   (default 8000)
    IDLE_TIMEOUT  seconds of inactivity before finalizing       (default 5)
    SCENARIO      'A' (isolated) or 'B' (national database)     (default A)
    NATIONAL_URL  base URL of the national database (Scenario B)
                                          (default http://national-database:9000)
    REPORT_DIR    directory to also save the report as JSON/CSV (default reports)
"""

from __future__ import annotations

import os

from src.net.national_client import NationalClient
from src.net.server import serve


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    idle_timeout = float(os.environ.get("IDLE_TIMEOUT", "5"))
    scenario = os.environ.get("SCENARIO", "A").upper()
    report_dir = os.environ.get("REPORT_DIR", "reports")

    national = None
    if scenario == "B":
        national_url = os.environ.get("NATIONAL_URL", "http://national-database:9000")
        national = NationalClient(national_url)
        print(f"[sus-database] Scenario B: waiting for national database at {national_url}", flush=True)
        national.wait_until_ready()

    serve(
        host=host,
        port=port,
        idle_timeout=idle_timeout,
        scenario=scenario,
        national=national,
        report_dir=report_dir,
    )


if __name__ == "__main__":
    main()
