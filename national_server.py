"""Sobe o container da base nacional (Cenário B)
"""

from __future__ import annotations

import os

from src.net.national_server import serve


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0") # endereço de bind
    port = int(os.environ.get("PORT", "9000")) # porta de escuta
    coverage = float(os.environ.get("COVERAGE", "0.9")) # fração de pacientes identificáveis
    serve(host=host, port=port, coverage=coverage)


if __name__ == "__main__":
    main()
