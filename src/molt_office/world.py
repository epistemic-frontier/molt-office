from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .errors import WorldError
from .events import Event, DiagEvent, new_action_id, now_ts


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
class WorldState:
    rooms: Dict[str, Room] = field(default_factory=dict)
    presence: Dict[str, str] = field(default_factory=dict)  # actor -> room_id
    doorbell: Dict[str, List[KnockRequest]] = field(default_factory=dict)
    boards: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    consecutive_failures: Dict[str, int] = field(default_factory=dict)


class World:
    def __init__(self, state: Optional[WorldState] = None) -> None:
        self.state = state or WorldState()
        if not self.state.rooms:
            self._seed_rooms()

    def _seed_rooms(self) -> None:
        self.add_room("lobby", kind="lobby", owner=None, requires_knock=False)
        self.add_room("meeting:public", kind="meeting", owner=None, requires_knock=False)
        self.add_room("coffee:public", kind="coffee", owner=None, requires_knock=False)

    def add_room(self, room_id: str, kind: str, owner: Optional[str], requires_knock: bool) -> None:
        self.state.rooms[room_id] = Room(
            room_id=room_id,
            kind=kind,
            owner=owner,
            requires_knock=requires_knock,
        )
        self.state.boards.setdefault(room_id, [])
        self.state.doorbell.setdefault(room_id, [])

    def ensure_private_office(self, actor: str) -> None:
        room_id = f"office:{actor}"
        if room_id not in self.state.rooms:
            self.add_room(room_id, kind="office", owner=actor, requires_knock=True)

    def _record_failure(self, actor: str) -> None:
        self.state.consecutive_failures[actor] = self.state.consecutive_failures.get(actor, 0) + 1

    def _record_success(self, actor: str) -> None:
        self.state.consecutive_failures[actor] = 0

    def _maybe_hint(self, actor: str, err_code: str) -> Optional[str]:
        if self.state.consecutive_failures.get(actor, 0) <= 3:
            return None
        if err_code == "E_NEED_KNOCK":
            return "Private room. Use room.knock then wait for room.admit."
        if err_code == "E_BAD_ARG":
            return "Check required fields: room_id, actor, message."
        if err_code == "E_CONFLICT":
            return "State conflict. Re-read room state or choose a different option."
        return "Adjust parameters or choose a different action to avoid repeat failure."

    def _emit_event(
        self,
        actor: str,
        cmd: str,
        room_id: Optional[str],
        ok: bool,
        data: Dict[str, Any],
        err: Optional[Dict[str, Any]],
    ) -> Event:
        return Event(
            action_id=new_action_id(),
            actor=actor,
            cmd=cmd,
            room_id=room_id,
            ok=ok,
            data=data,
            err=err,
            ts=now_ts(),
        )

    def _diag_event(self, cmd: str, err: WorldError) -> DiagEvent:
        return DiagEvent(cmd="agent.diag", details={"cmd": cmd, "err": err.to_dict()})

    def room_list(self, actor: str) -> tuple[Event, Optional[DiagEvent]]:
        data = {
            "rooms": [
                {
                    "room_id": r.room_id,
                    "kind": r.kind,
                    "owner": r.owner,
                    "requires_knock": r.requires_knock,
                }
                for r in self.state.rooms.values()
            ]
        }
        self._record_success(actor)
        return self._emit_event(actor, "room.list", None, True, data, None), None

    def room_whereami(self, actor: str) -> tuple[Event, Optional[DiagEvent]]:
        room_id = self.state.presence.get(actor)
        data = {
            "room_id": room_id,
            "room_kind": self.state.rooms[room_id].kind if room_id else None,
        }
        self._record_success(actor)
        return self._emit_event(actor, "room.whereami", room_id, True, data, None), None

    def room_enter(self, actor: str, room_id: str) -> tuple[Event, Optional[DiagEvent]]:
        if room_id not in self.state.rooms:
            err = WorldError("E_BAD_ARG", "Unknown room", {"room_id": room_id})
            return self._fail(actor, "room.enter", room_id, err)

        room = self.state.rooms[room_id]
        if room.requires_knock and room.owner != actor:
            err = WorldError("E_NEED_KNOCK", "Private room requires knock", {"room_id": room_id})
            return self._fail(actor, "room.enter", room_id, err)

        self.state.presence[actor] = room_id
        self._record_success(actor)
        return self._emit_event(actor, "room.enter", room_id, True, {"room_id": room_id}, None), None

    def room_leave(self, actor: str) -> tuple[Event, Optional[DiagEvent]]:
        room_id = self.state.presence.get(actor)
        if not room_id:
            err = WorldError("E_CONFLICT", "Not in a room", {})
            return self._fail(actor, "room.leave", None, err)
        self.state.presence.pop(actor, None)
        self._record_success(actor)
        return self._emit_event(actor, "room.leave", room_id, True, {"room_id": room_id}, None), None

    def room_knock(self, actor: str, room_id: str, msg: Optional[str] = None) -> tuple[Event, Optional[DiagEvent]]:
        if room_id not in self.state.rooms:
            err = WorldError("E_BAD_ARG", "Unknown room", {"room_id": room_id})
            return self._fail(actor, "room.knock", room_id, err)

        room = self.state.rooms[room_id]
        if not room.requires_knock:
            err = WorldError("E_CONFLICT", "Room does not require knock", {"room_id": room_id})
            return self._fail(actor, "room.knock", room_id, err)

        request = KnockRequest(request_id=new_action_id(), room_id=room_id, actor=actor, msg=msg)
        self.state.doorbell[room_id].append(request)
        self._record_success(actor)
        return (
            self._emit_event(
                actor,
                "room.knock",
                room_id,
                True,
                {"request_id": request.request_id, "room_id": room_id, "status": "pending"},
                None,
            ),
            None,
        )

    def room_admit(self, actor: str, request_id: str) -> tuple[Event, Optional[DiagEvent]]:
        for room_id, queue in self.state.doorbell.items():
            for idx, req in enumerate(queue):
                if req.request_id == request_id:
                    room = self.state.rooms[room_id]
                    if room.owner != actor:
                        err = WorldError("E_FORBIDDEN", "Only owner can admit", {"room_id": room_id})
                        return self._fail(actor, "room.admit", room_id, err)
                    queue.pop(idx)
                    self._record_success(actor)
                    return (
                        self._emit_event(
                            actor,
                            "room.admit",
                            room_id,
                            True,
                            {"request_id": request_id, "room_id": room_id, "granted": True},
                            None,
                        ),
                        None,
                    )

        err = WorldError("E_BAD_ARG", "Unknown request_id", {"request_id": request_id})
        return self._fail(actor, "room.admit", None, err)

    def board_write(self, actor: str, room_id: str, message: str) -> tuple[Event, Optional[DiagEvent]]:
        if room_id not in self.state.rooms:
            err = WorldError("E_BAD_ARG", "Unknown room", {"room_id": room_id})
            return self._fail(actor, "board.write", room_id, err)
        entry = {"actor": actor, "message": message, "ts": now_ts()}
        self.state.boards[room_id].append(entry)
        self._record_success(actor)
        return (
            self._emit_event(actor, "board.write", room_id, True, {"entry": entry}, None),
            None,
        )

    def _fail(self, actor: str, cmd: str, room_id: Optional[str], err: WorldError) -> tuple[Event, DiagEvent]:
        self._record_failure(actor)
        hint = self._maybe_hint(actor, err.code)
        data: Dict[str, Any] = {"hint": hint} if hint else {}
        event = self._emit_event(actor, cmd, room_id, False, data, err.to_dict())
        return event, self._diag_event(cmd, err)
