"""Entry point for the central SUS database container.

Reads its configuration from the environment (so it can be driven entirely by
docker-compose) and serves until the health posts go quiet, at which point it
prints the final report and exits.

Environment variables:
    HOST          bind address                                  (default 0.0.0.0)
    PORT          listen port                                   (default 8000)
    IDLE_TIMEOUT  seconds of inactivity before finalizing       (default 5)
"""

from __future__ import annotations

import os

from src.net.server import serve


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    idle_timeout = float(os.environ.get("IDLE_TIMEOUT", "5"))
    serve(host=host, port=port, idle_timeout=idle_timeout)


if __name__ == "__main__":
    main()
