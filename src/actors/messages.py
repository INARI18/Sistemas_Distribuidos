"""Message types exchanged between actors over their queues."""

from __future__ import annotations

import queue
from dataclasses import dataclass

from ..domain import ConsultationRecord


@dataclass
class IngestRequest:
    """A record sent by a post to the SUS database, plus a reply channel.

    The reply queue lets the database acknowledge ingestion so the sending
    post can measure the round-trip response time.
    """

    record: ConsultationRecord
    reply_to: "queue.Queue[bool]"
