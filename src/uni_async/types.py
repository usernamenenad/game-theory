from dataclasses import dataclass
from enum import Enum
from typing import Any


class AsyncMessageType(str, Enum):
    COLLECT = "Collect"
    SETUP = "Setup"
    COMMIT = "Commit"
    REVEAL = "Reveal"


@dataclass(order=True)
class PendingMessage:
    deliver_at: int
    seq: int
    source: int
    dest: int
    payload: dict[str, Any]
