from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


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


@dataclass
class NoteObject:
    object_id: str
    title: str
    summary: str
    content: str
    holder: str
    tags: List[str] = field(default_factory=list)
