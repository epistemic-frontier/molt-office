from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Room:
    room_id: str
    kind: str
    owner: Optional[str]
    requires_knock: bool


@dataclass
class KnockRequest:
    request_id: str
    room_id: str
    actor: str
    msg: Optional[str]
