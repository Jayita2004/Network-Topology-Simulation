from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class Message:
    kind: str            # "HELLO", "ARP", etc.
    src: str
    dst: str             # neighbor or broadcast '*'
    payload: Any = None
