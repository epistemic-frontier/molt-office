from __future__ import annotations

from dataclasses import asdict
import json
from typing import Any, Dict, Iterable, List, Optional

import redis

from .events import Event, DiagEvent
from .models import Room, KnockRequest
from .world_state import WorldState


class StorageBackend:
    def ensure_seeded(self) -> None:
        raise NotImplementedError

    def list_rooms(self) -> List[Room]:
        raise NotImplementedError

    def get_room(self, room_id: str) -> Optional[Room]:
        raise NotImplementedError

    def put_room(self, room: Room) -> None:
        raise NotImplementedError

    def get_presence(self, actor: str) -> Optional[str]:
        raise NotImplementedError

    def set_presence(self, actor: str, room_id: Optional[str]) -> None:
        raise NotImplementedError

    def list_doorbell(self, room_id: str) -> List[KnockRequest]:
        raise NotImplementedError

    def add_doorbell(self, request: KnockRequest) -> None:
        raise NotImplementedError

    def remove_doorbell(self, request_id: str) -> Optional[KnockRequest]:
        raise NotImplementedError

    def append_board(self, room_id: str, entry: Dict[str, Any]) -> None:
        raise NotImplementedError

    def append_event(self, event: Event) -> None:
        raise NotImplementedError

    def append_diag(self, actor: str, diag: DiagEvent) -> None:
        raise NotImplementedError

    def read_events(self, last_id: str, block_ms: int = 0) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def incr_failure(self, actor: str) -> int:
        raise NotImplementedError

    def reset_failure(self, actor: str) -> None:
        raise NotImplementedError

    def get_failures(self, actor: str) -> int:
        raise NotImplementedError


class InMemoryBackend(StorageBackend):
    def __init__(self, state: Optional[WorldState] = None) -> None:
        self.state = state or WorldState()

    def ensure_seeded(self) -> None:
        return None

    def list_rooms(self) -> List[Room]:
        return list(self.state.rooms.values())

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.state.rooms.get(room_id)

    def put_room(self, room: Room) -> None:
        self.state.rooms[room.room_id] = room
        self.state.boards.setdefault(room.room_id, [])
        self.state.doorbell.setdefault(room.room_id, [])

    def get_presence(self, actor: str) -> Optional[str]:
        return self.state.presence.get(actor)

    def set_presence(self, actor: str, room_id: Optional[str]) -> None:
        if room_id is None:
            self.state.presence.pop(actor, None)
        else:
            self.state.presence[actor] = room_id

    def list_doorbell(self, room_id: str) -> List[KnockRequest]:
        return list(self.state.doorbell.get(room_id, []))

    def add_doorbell(self, request: KnockRequest) -> None:
        self.state.doorbell.setdefault(request.room_id, []).append(request)

    def remove_doorbell(self, request_id: str) -> Optional[KnockRequest]:
        for room_id, queue in self.state.doorbell.items():
            for idx, req in enumerate(queue):
                if req.request_id == request_id:
                    return queue.pop(idx)
        return None

    def append_board(self, room_id: str, entry: Dict[str, Any]) -> None:
        self.state.boards.setdefault(room_id, []).append(entry)

    def append_event(self, event: Event) -> None:
        self.state.events.append(event)

    def append_diag(self, actor: str, diag: DiagEvent) -> None:
        self.state.diag.append((actor, diag))

    def read_events(self, last_id: str, block_ms: int = 0) -> List[Dict[str, Any]]:
        _ = last_id
        _ = block_ms
        return []

    def incr_failure(self, actor: str) -> int:
        self.state.consecutive_failures[actor] = self.state.consecutive_failures.get(actor, 0) + 1
        return self.state.consecutive_failures[actor]

    def reset_failure(self, actor: str) -> None:
        self.state.consecutive_failures[actor] = 0

    def get_failures(self, actor: str) -> int:
        return self.state.consecutive_failures.get(actor, 0)


class RedisBackend(StorageBackend):
    def __init__(self, url: str = "redis://localhost:6379/0", prefix: str = "molt") -> None:
        self.client = redis.Redis.from_url(url, decode_responses=True)
        self.prefix = prefix

    def _k(self, suffix: str) -> str:
        return f"{self.prefix}:{suffix}"

    def ensure_seeded(self) -> None:
        return None

    def list_rooms(self) -> List[Room]:
        rooms = []
        for key in self.client.scan_iter(self._k("room:*")):
            data = self.client.hgetall(key)
            if not data:
                continue
            rooms.append(
                Room(
                    room_id=data["room_id"],
                    kind=data["kind"],
                    owner=data.get("owner") or None,
                    requires_knock=data.get("requires_knock", "0") == "1",
                )
            )
        return rooms

    def get_room(self, room_id: str) -> Optional[Room]:
        data = self.client.hgetall(self._k(f"room:{room_id}"))
        if not data:
            return None
        return Room(
            room_id=data["room_id"],
            kind=data["kind"],
            owner=data.get("owner") or None,
            requires_knock=data.get("requires_knock", "0") == "1",
        )

    def put_room(self, room: Room) -> None:
        self.client.hset(
            self._k(f"room:{room.room_id}"),
            mapping={
                "room_id": room.room_id,
                "kind": room.kind,
                "owner": room.owner or "",
                "requires_knock": "1" if room.requires_knock else "0",
            },
        )
        self.client.setnx(self._k(f"board:{room.room_id}:init"), "1")
        self.client.setnx(self._k(f"doorbell:{room.room_id}:init"), "1")

    def get_presence(self, actor: str) -> Optional[str]:
        return self.client.hget(self._k("presence"), actor)

    def set_presence(self, actor: str, room_id: Optional[str]) -> None:
        if room_id is None:
            self.client.hdel(self._k("presence"), actor)
        else:
            self.client.hset(self._k("presence"), actor, room_id)

    def list_doorbell(self, room_id: str) -> List[KnockRequest]:
        ids = self.client.lrange(self._k(f"doorbell:{room_id}"), 0, -1)
        requests = []
        for req_id in ids:
            data = self.client.hgetall(self._k(f"doorbell:req:{req_id}"))
            if not data:
                continue
            requests.append(
                KnockRequest(
                    request_id=req_id,
                    room_id=data["room_id"],
                    actor=data["actor"],
                    msg=data.get("msg") or None,
                )
            )
        return requests

    def add_doorbell(self, request: KnockRequest) -> None:
        self.client.hset(
            self._k(f"doorbell:req:{request.request_id}"),
            mapping={
                "room_id": request.room_id,
                "actor": request.actor,
                "msg": request.msg or "",
            },
        )
        self.client.rpush(self._k(f"doorbell:{request.room_id}"), request.request_id)

    def remove_doorbell(self, request_id: str) -> Optional[KnockRequest]:
        data = self.client.hgetall(self._k(f"doorbell:req:{request_id}"))
        if not data:
            return None
        room_id = data["room_id"]
        self.client.lrem(self._k(f"doorbell:{room_id}"), 0, request_id)
        self.client.delete(self._k(f"doorbell:req:{request_id}"))
        return KnockRequest(
            request_id=request_id,
            room_id=room_id,
            actor=data["actor"],
            msg=data.get("msg") or None,
        )

    def append_board(self, room_id: str, entry: Dict[str, Any]) -> None:
        self.client.rpush(self._k(f"board:{room_id}"), json.dumps(entry))

    def append_event(self, event: Event) -> None:
        self.client.xadd(self._k("events"), _event_fields(event))

    def append_diag(self, actor: str, diag: DiagEvent) -> None:
        payload = {"actor": actor, "cmd": diag.cmd, "details": json.dumps(diag.details)}
        self.client.xadd(self._k("diag"), payload)

    def read_events(self, last_id: str, block_ms: int = 0) -> List[Dict[str, Any]]:
        stream_key = self._k("events")
        result = self.client.xread({stream_key: last_id}, block=block_ms)
        entries: List[Dict[str, Any]] = []
        for _, items in result:
            for entry_id, fields in items:
                entries.append({"id": entry_id, "fields": fields})
        return entries

    def incr_failure(self, actor: str) -> int:
        return int(self.client.hincrby(self._k("failures"), actor, 1))

    def reset_failure(self, actor: str) -> None:
        self.client.hset(self._k("failures"), actor, 0)

    def get_failures(self, actor: str) -> int:
        val = self.client.hget(self._k("failures"), actor)
        return int(val) if val else 0


def _event_fields(event: Event) -> Dict[str, Any]:
    payload = asdict(event)
    payload["data"] = json.dumps(event.data)
    payload["err"] = json.dumps(event.err) if event.err else ""
    payload["ok"] = "1" if event.ok else "0"
    return payload
