"""Entry point do container de um posto de saúde 
"""

from __future__ import annotations

import os

from src.net.client import run_post


def main() -> None:
    base_seed = int(os.environ.get("BASE_SEED", "42"))
    consultations = int(os.environ.get("CONSULTATIONS", "200"))
    base_url = os.environ.get("DATABASE_URL", "http://sus-database:8000")

    explicit = os.environ.get("POST_INDEX")
    post_index = int(explicit) if explicit is not None else None
    post_id = os.environ.get("POST_ID")

    run_post(
        consultations=consultations,
        base_seed=base_seed,
        base_url=base_url,
        post_index=post_index,
        post_id=post_id,
    )


if __name__ == "__main__":
    main()
