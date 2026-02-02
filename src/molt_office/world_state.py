from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .models import Room, KnockRequest, NoteObject


@dataclass
class WorldState:
    rooms: Dict[str, Room] = field(default_factory=dict)
    presence: Dict[str, str] = field(default_factory=dict)  # actor -> room_id
    doorbell: Dict[str, List[KnockRequest]] = field(default_factory=dict)
    boards: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    objects: Dict[str, NoteObject] = field(default_factory=dict)
    object_history: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    consecutive_failures: Dict[str, int] = field(default_factory=dict)
    events: List[Any] = field(default_factory=list)
    diag: List[Any] = field(default_factory=list)
