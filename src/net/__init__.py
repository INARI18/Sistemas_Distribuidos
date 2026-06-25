"""Network transport layer.

The actors of the simulation are real distributed processes that talk over
HTTP, running as separate Docker containers on a shared network. This layer is
just the transport: the meaning lives in the inner layers (``domain``,
``generation``, ``standardization``, ``metrics``) and in the database core
(``src/database.py``).
"""
