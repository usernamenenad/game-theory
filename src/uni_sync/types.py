from enum import Enum
from typing import Any, TypedDict


class MessageType(str, Enum):
    COLLECT = "Collect"
    SETUP = "Setup"
    RANDOM = "Random"


class Message(TypedDict):
    message_type: MessageType
    sender_id: int
    payload: Any
