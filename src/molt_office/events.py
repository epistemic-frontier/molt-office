from dataclasses import dataclass
from typing import Any, Dict, Optional
import uuid
import time


@dataclass
class Event:
    action_id: str
    actor: str
    cmd: str
    room_id: Optional[str]
    ok: bool
    data: Dict[str, Any]
    err: Optional[Dict[str, Any]]
    ts: float


@dataclass
class DiagEvent:
    cmd: str
    details: Dict[str, Any]
    private: bool = True


def new_action_id() -> str:
    return str(uuid.uuid4())


def now_ts() -> float:
    return time.time()
