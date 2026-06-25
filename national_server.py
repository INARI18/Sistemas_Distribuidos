"""Entry point for the national general database container (Scenario B).

The authoritative civil registry. It is started only in Scenario B and is
reached by exactly one actor -- the central SUS database -- which consults it to
complete the civil data it could not resolve on its own. It serves until the
run tears it down.

Environment variables:
    HOST      bind address                                   (default 0.0.0.0)
    PORT      listen port                                    (default 9000)
    COVERAGE  share of identifiable patients on file [0..1]  (default 0.9)
"""

from __future__ import annotations

import os

from src.net.national_server import serve


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "9000"))
    coverage = float(os.environ.get("COVERAGE", "0.9"))
    serve(host=host, port=port, coverage=coverage)


if __name__ == "__main__":
    main()
