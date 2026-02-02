from __future__ import annotations

from typing import Any, Dict, List, Optional

from .errors import WorldError
from .events import Event, DiagEvent, new_action_id, now_ts
from .models import Room, KnockRequest, NoteObject
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

    def board_read(
        self,
        actor: str,
        room_id: str,
        limit: int = 20,
        offset: int = 0,
        by_actor: Optional[str] = None,
    ) -> tuple[Event, Optional[DiagEvent]]:
        room = self.backend.get_room(room_id)
        if not room:
            err = WorldError("E_BAD_ARG", "Unknown room", {"room_id": room_id})
            return self._fail(actor, "board.read", room_id, err)
        entries = self.backend.read_board(room_id, limit=limit, offset=offset, by_actor=by_actor)
        self._record_success(actor)
        event = self._emit_event(
            actor,
            "board.read",
            room_id,
            True,
            {"entries": entries, "offset": offset, "limit": limit, "by_actor": by_actor},
            None,
        )
        self.backend.append_event(event)
        return event, None

    def object_create(
        self,
        actor: str,
        object_id: str,
        title: str,
        summary: str,
        content: str = "",
        tags: Optional[List[str]] = None,
    ) -> tuple[Event, Optional[DiagEvent]]:
        if self.backend.get_object(object_id):
            err = WorldError("E_CONFLICT", "Object already exists", {"object_id": object_id})
            return self._fail(actor, "obj.create", None, err)
        obj = NoteObject(
            object_id=object_id,
            title=title,
            summary=summary,
            content=content,
            holder=actor,
            tags=tags or [],
            version=1,
        )
        self.backend.put_object(obj)
        self._record_success(actor)
        event = self._emit_event(actor, "obj.create", None, True, {"object_id": object_id}, None)
        self.backend.append_event(event)
        return event, None

    def object_read(self, actor: str, object_id: str) -> tuple[Event, Optional[DiagEvent]]:
        obj = self.backend.get_object(object_id)
        if not obj:
            err = WorldError("E_BAD_ARG", "Unknown object", {"object_id": object_id})
            return self._fail(actor, "obj.read", None, err)
        self._record_success(actor)
        event = self._emit_event(actor, "obj.read", None, True, {"object": obj.__dict__}, None)
        self.backend.append_event(event)
        return event, None

    def object_write(self, actor: str, object_id: str, content: str) -> tuple[Event, Optional[DiagEvent]]:
        obj = self.backend.get_object(object_id)
        if not obj:
            err = WorldError("E_BAD_ARG", "Unknown object", {"object_id": object_id})
            return self._fail(actor, "obj.write", None, err)
        if obj.holder != actor:
            err = WorldError("E_FORBIDDEN", "Only holder can write", {"object_id": object_id})
            return self._fail(actor, "obj.write", None, err)
        obj = self.backend.update_object_content(object_id, content)
        self._record_success(actor)
        event = self._emit_event(actor, "obj.write", None, True, {"object_id": object_id}, None)
        self.backend.append_event(event)
        return event, None

    def object_append(self, actor: str, object_id: str, content: str) -> tuple[Event, Optional[DiagEvent]]:
        obj = self.backend.get_object(object_id)
        if not obj:
            err = WorldError("E_BAD_ARG", "Unknown object", {"object_id": object_id})
            return self._fail(actor, "obj.append", None, err)
        if obj.holder != actor:
            err = WorldError("E_FORBIDDEN", "Only holder can append", {"object_id": object_id})
            return self._fail(actor, "obj.append", None, err)
        obj = self.backend.append_object_content(object_id, content)
        self._record_success(actor)
        event = self._emit_event(actor, "obj.append", None, True, {"object_id": object_id}, None)
        self.backend.append_event(event)
        return event, None

    def object_tags(self, actor: str, object_id: str, tags: List[str]) -> tuple[Event, Optional[DiagEvent]]:
        obj = self.backend.get_object(object_id)
        if not obj:
            err = WorldError("E_BAD_ARG", "Unknown object", {"object_id": object_id})
            return self._fail(actor, "obj.tags", None, err)
        if obj.holder != actor:
            err = WorldError("E_FORBIDDEN", "Only holder can tag", {"object_id": object_id})
            return self._fail(actor, "obj.tags", None, err)
        self.backend.set_object_tags(object_id, tags)
        self._record_success(actor)
        event = self._emit_event(actor, "obj.tags", None, True, {"object_id": object_id}, None)
        self.backend.append_event(event)
        return event, None

    def object_list(self, actor: str, holder: Optional[str] = None) -> tuple[Event, Optional[DiagEvent]]:
        objs = self.backend.list_objects(holder=holder)
        data = {"objects": [o.__dict__ for o in objs]}
        self._record_success(actor)
        event = self._emit_event(actor, "obj.list", None, True, data, None)
        self.backend.append_event(event)
        return event, None

    def object_search(
        self,
        actor: str,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        holder: Optional[str] = None,
        tag_mode: str = "all",
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Event, Optional[DiagEvent]]:
        objs = self.backend.search_objects(
            query=query,
            tags=tags,
            holder=holder,
            tag_mode=tag_mode,
            offset=offset,
            limit=limit,
        )
        data = {"objects": [o.__dict__ for o in objs]}
        self._record_success(actor)
        event = self._emit_event(actor, "obj.search", None, True, data, None)
        self.backend.append_event(event)
        return event, None

    def object_history(
        self,
        actor: str,
        object_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Event, Optional[DiagEvent]]:
        history = self.backend.get_object_history(object_id, offset=offset, limit=limit)
        data = {"object_id": object_id, "history": history}
        self._record_success(actor)
        event = self._emit_event(actor, "obj.history", None, True, data, None)
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
