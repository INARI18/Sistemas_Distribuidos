"""
Ponto de entrada para o container do banco de dados central do SUS
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
