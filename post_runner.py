"""Entry point for a health post container.

Each replica of the ``health-post`` service runs this. Its identity and seed
are derived so that many replicas, started from the very same image, behave as
distinct posts (different regional profiles) without any per-replica config.

Environment variables:
    DATABASE_URL    base URL of the SUS database   (default http://sus-database:8000)
    CONSULTATIONS   records this post generates     (default 200)
    BASE_SEED       root seed for the whole run     (default 42)
    POST_INDEX      this post's index (optional)    (default: derived from hostname)
    POST_ID         human label for the post        (default: derived from hostname)

How identity is resolved:

- With ``--scale health-post=N`` every replica gets a distinct container
  hostname, from which a distinct seed is derived -- so each post has its own
  regional profile with zero coordination. ``BASE_SEED`` still shifts the whole
  population, so the same N replicas under the same BASE_SEED stay comparable.
- Set ``POST_INDEX`` explicitly (e.g. one service per post) when you want a run
  that is reproducible down to the exact per-post seed (``BASE_SEED + idx*1000``).
"""

from __future__ import annotations

import os
import socket
import zlib

from src.net.client import run_post


def _resolve_identity(base_seed: int) -> tuple[str, int]:
    """Return (post_id, seed) from POST_INDEX if given, else the hostname."""
    hostname = socket.gethostname()
    explicit = os.environ.get("POST_INDEX")
    if explicit is not None:
        index = int(explicit)
        post_id = os.environ.get("POST_ID", f"post-{index + 1}")
        return post_id, base_seed + index * 1000          # exactly reproducible

    # Scaled replicas: derive a stable, distinct seed from the container id.
    offset = zlib.crc32(hostname.encode()) % 1_000_000
    post_id = os.environ.get("POST_ID", hostname)
    return post_id, base_seed + offset


def main() -> None:
    base_seed = int(os.environ.get("BASE_SEED", "42"))
    post_id, seed = _resolve_identity(base_seed)
    consultations = int(os.environ.get("CONSULTATIONS", "200"))
    base_url = os.environ.get("DATABASE_URL", "http://sus-database:8000")

    run_post(post_id=post_id, consultations=consultations, seed=seed, base_url=base_url)


if __name__ == "__main__":
    main()
