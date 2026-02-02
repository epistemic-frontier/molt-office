from __future__ import annotations

from typing import Any, Dict, List, Optional

from .errors import WorldError
from .events import Event, DiagEvent, new_action_id, now_ts
from .models import Room, KnockRequest
from .storage import InMemoryBackend, StorageBackend


class World:
    def __init__(self, backend: Optional[StorageBackend] = None) -> None:
        self.backend = backend or InMemoryBackend()
        self._seed_rooms()

    def _seed_rooms(self) -> None:
        self.backend.ensure_seeded()
        for room_id, kind in (
            ("lobby", "lobby"),
            ("meeting:public", "meeting"),
            ("coffee:public", "coffee"),
        ):
            if not self.backend.get_room(room_id):
                self.add_room(room_id, kind=kind, owner=None, requires_knock=False)

    def add_room(self, room_id: str, kind: str, owner: Optional[str], requires_knock: bool) -> None:
        self.backend.put_room(
            Room(
                room_id=room_id,
                kind=kind,
                owner=owner,
                requires_knock=requires_knock,
            )
        )

    def ensure_private_office(self, actor: str) -> None:
        room_id = f"office:{actor}"
        if not self.backend.get_room(room_id):
            self.add_room(room_id, kind="office", owner=actor, requires_knock=True)

    def _record_failure(self, actor: str) -> int:
        return self.backend.incr_failure(actor)

    def _record_success(self, actor: str) -> None:
        self.backend.reset_failure(actor)

    def _maybe_hint(self, actor: str, err_code: str) -> Optional[str]:
        if self.backend.get_failures(actor) <= 3:
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
                for r in self.backend.list_rooms()
            ]
        }
        self._record_success(actor)
        event = self._emit_event(actor, "room.list", None, True, data, None)
        self.backend.append_event(event)
        return event, None

    def room_whereami(self, actor: str) -> tuple[Event, Optional[DiagEvent]]:
        room_id = self.backend.get_presence(actor)
        room = self.backend.get_room(room_id) if room_id else None
        data = {
            "room_id": room_id,
            "room_kind": room.kind if room else None,
        }
        self._record_success(actor)
        event = self._emit_event(actor, "room.whereami", room_id, True, data, None)
        self.backend.append_event(event)
        return event, None

    def room_enter(self, actor: str, room_id: str) -> tuple[Event, Optional[DiagEvent]]:
        room = self.backend.get_room(room_id)
        if not room:
            err = WorldError("E_BAD_ARG", "Unknown room", {"room_id": room_id})
            return self._fail(actor, "room.enter", room_id, err)

        if room.requires_knock and room.owner != actor:
            err = WorldError("E_NEED_KNOCK", "Private room requires knock", {"room_id": room_id})
            return self._fail(actor, "room.enter", room_id, err)

        self.backend.set_presence(actor, room_id)
        self._record_success(actor)
        event = self._emit_event(actor, "room.enter", room_id, True, {"room_id": room_id}, None)
        self.backend.append_event(event)
        return event, None

    def room_leave(self, actor: str) -> tuple[Event, Optional[DiagEvent]]:
        room_id = self.backend.get_presence(actor)
        if not room_id:
            err = WorldError("E_CONFLICT", "Not in a room", {})
            return self._fail(actor, "room.leave", None, err)
        self.backend.set_presence(actor, None)
        self._record_success(actor)
        event = self._emit_event(actor, "room.leave", room_id, True, {"room_id": room_id}, None)
        self.backend.append_event(event)
        return event, None

    def room_knock(self, actor: str, room_id: str, msg: Optional[str] = None) -> tuple[Event, Optional[DiagEvent]]:
        room = self.backend.get_room(room_id)
        if not room:
            err = WorldError("E_BAD_ARG", "Unknown room", {"room_id": room_id})
            return self._fail(actor, "room.knock", room_id, err)

        if not room.requires_knock:
            err = WorldError("E_CONFLICT", "Room does not require knock", {"room_id": room_id})
            return self._fail(actor, "room.knock", room_id, err)

        request = KnockRequest(request_id=new_action_id(), room_id=room_id, actor=actor, msg=msg)
        self.backend.add_doorbell(request)
        self._record_success(actor)
        event = self._emit_event(
            actor,
            "room.knock",
            room_id,
            True,
            {"request_id": request.request_id, "room_id": room_id, "status": "pending"},
            None,
        )
        self.backend.append_event(event)
        return event, None

    def room_admit(self, actor: str, request_id: str) -> tuple[Event, Optional[DiagEvent]]:
        request = self.backend.remove_doorbell(request_id)
        if not request:
            err = WorldError("E_BAD_ARG", "Unknown request_id", {"request_id": request_id})
            return self._fail(actor, "room.admit", None, err)

        room = self.backend.get_room(request.room_id)
        if not room or room.owner != actor:
            err = WorldError("E_FORBIDDEN", "Only owner can admit", {"room_id": request.room_id})
            return self._fail(actor, "room.admit", request.room_id, err)

        self._record_success(actor)
        event = self._emit_event(
            actor,
            "room.admit",
            request.room_id,
            True,
            {"request_id": request_id, "room_id": request.room_id, "granted": True},
            None,
        )
        self.backend.append_event(event)
        return event, None

    def board_write(self, actor: str, room_id: str, message: str) -> tuple[Event, Optional[DiagEvent]]:
        room = self.backend.get_room(room_id)
        if not room:
            err = WorldError("E_BAD_ARG", "Unknown room", {"room_id": room_id})
            return self._fail(actor, "board.write", room_id, err)
        entry = {"actor": actor, "message": message, "ts": now_ts()}
        self.backend.append_board(room_id, entry)
        self._record_success(actor)
        event = self._emit_event(actor, "board.write", room_id, True, {"entry": entry}, None)
        self.backend.append_event(event)
        return event, None

    def _fail(self, actor: str, cmd: str, room_id: Optional[str], err: WorldError) -> tuple[Event, DiagEvent]:
        self._record_failure(actor)
        hint = self._maybe_hint(actor, err.code)
        data: Dict[str, Any] = {"hint": hint} if hint else {}
        event = self._emit_event(actor, cmd, room_id, False, data, err.to_dict())
        diag = self._diag_event(cmd, err)
        self.backend.append_event(event)
        self.backend.append_diag(actor, diag)
        return event, diag
