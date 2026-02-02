from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .storage import InMemoryBackend, RedisBackend, StorageBackend
from .world import World


class EnterRequest(BaseModel):
    actor: str


class KnockRequest(BaseModel):
    actor: str
    msg: Optional[str] = None


class AdmitRequest(BaseModel):
    actor: str
    request_id: str


class LeaveRequest(BaseModel):
    actor: str


class WhereAmIRequest(BaseModel):
    actor: str


class BoardWriteRequest(BaseModel):
    actor: str
    message: str


class ObjectCreateRequest(BaseModel):
    actor: str
    object_id: str
    title: str
    summary: str
    content: str = ""
    tags: Optional[list[str]] = None


class ObjectWriteRequest(BaseModel):
    actor: str
    content: str


class ObjectAppendRequest(BaseModel):
    actor: str
    content: str


class ObjectTagsRequest(BaseModel):
    actor: str
    tags: list[str]


def _event_payload(event, diag) -> Dict[str, Any]:
    payload = asdict(event)
    if diag:
        payload["diag"] = asdict(diag)
    return payload


def create_app(backend: Optional[StorageBackend] = None) -> FastAPI:
    backend = backend or InMemoryBackend()
    world = World(backend=backend)

    app = FastAPI(title="molt-office", version="0.0.1")

    token = os.getenv("MOLT_OFFICE_TOKEN")

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if token:
            auth = request.headers.get("authorization", "")
            if auth != f"Bearer {token}":
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)

    @app.get("/rooms")
    def room_list(actor: str):
        event, diag = world.room_list(actor)
        return _event_payload(event, diag)

    @app.post("/rooms/{room_id}/enter")
    def room_enter(room_id: str, body: EnterRequest):
        event, diag = world.room_enter(body.actor, room_id)
        return _event_payload(event, diag)

    @app.post("/rooms/leave")
    def room_leave(body: LeaveRequest):
        event, diag = world.room_leave(body.actor)
        return _event_payload(event, diag)

    @app.get("/rooms/whereami")
    def room_whereami(actor: str):
        event, diag = world.room_whereami(actor)
        return _event_payload(event, diag)

    @app.post("/rooms/{room_id}/knock")
    def room_knock(room_id: str, body: KnockRequest):
        event, diag = world.room_knock(body.actor, room_id, body.msg)
        return _event_payload(event, diag)

    @app.post("/rooms/admit")
    def room_admit(body: AdmitRequest):
        event, diag = world.room_admit(body.actor, body.request_id)
        return _event_payload(event, diag)

    @app.post("/boards/{room_id}/write")
    def board_write(room_id: str, body: BoardWriteRequest):
        event, diag = world.board_write(body.actor, room_id, body.message)
        return _event_payload(event, diag)

    @app.post("/objects/create")
    def object_create(body: ObjectCreateRequest):
        event, diag = world.object_create(
            actor=body.actor,
            object_id=body.object_id,
            title=body.title,
            summary=body.summary,
            content=body.content,
            tags=body.tags,
        )
        return _event_payload(event, diag)

    @app.get("/objects/{object_id}")
    def object_read(object_id: str, actor: str):
        event, diag = world.object_read(actor, object_id)
        return _event_payload(event, diag)

    @app.post("/objects/{object_id}/write")
    def object_write(object_id: str, body: ObjectWriteRequest):
        event, diag = world.object_write(body.actor, object_id, body.content)
        return _event_payload(event, diag)

    @app.post("/objects/{object_id}/append")
    def object_append(object_id: str, body: ObjectAppendRequest):
        event, diag = world.object_append(body.actor, object_id, body.content)
        return _event_payload(event, diag)

    @app.post("/objects/{object_id}/tags")
    def object_tags(object_id: str, body: ObjectTagsRequest):
        event, diag = world.object_tags(body.actor, object_id, body.tags)
        return _event_payload(event, diag)

    @app.get("/objects")
    def object_list(actor: str, holder: Optional[str] = None):
        event, diag = world.object_list(actor, holder)
        return _event_payload(event, diag)

    @app.get("/objects/search")
    def object_search(actor: str, q: Optional[str] = None, tags: Optional[str] = None, holder: Optional[str] = None):
        tag_list = tags.split(",") if tags else None
        event, diag = world.object_search(actor, query=q, tags=tag_list, holder=holder)
        return _event_payload(event, diag)

    @app.get("/events")
    def events_stream(last_id: str = "0-0", block_ms: int = 0):
        if not isinstance(backend, RedisBackend):
            raise HTTPException(status_code=400, detail="Redis backend required for event stream")
        entries = backend.read_events(last_id=last_id, block_ms=block_ms)
        return {"stream": entries}

    return app
