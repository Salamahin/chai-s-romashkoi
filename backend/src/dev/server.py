"""FastAPI dev server for local development."""

from __future__ import annotations

import os
import sys
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated, Any

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

load_dotenv()

# Ensure src/ is first on sys.path so local packages (e.g. `profile`) shadow stdlib modules of the same name.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from profile.domain import Profile, ProfileEntry, apply_patch, compute_patch, normalise_entry  # noqa: E402
from profile.tags import STANDARD_TAGS, known_tags  # noqa: E402

from auth import SessionClaims, VerificationError, sign_session_token, verify_session_token  # noqa: E402
from log.domain import LogEntry, LogEntryPatch, apply_patch, make_entry, to_response_dict  # noqa: E402
from relations.domain import RelationRecord, build_send_records, normalise_label  # noqa: E402
from relations.label_suggestions import known_labels  # noqa: E402

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)

# In-memory store: user_sub -> Profile
_profile_store: dict[str, Profile] = {}

# In-memory store: (owner_email, relation_id) -> RelationRecord
_relations_store: dict[tuple[str, str], RelationRecord] = {}

# In-memory log store: (owner_email, entry_id) -> LogEntry
_log_store: dict[tuple[str, str], LogEntry] = {}

DEV_SUB = "dev"
DEV_EMAIL = "dev@local.dev"


# Seed: one pending-received and one confirmed relation for dev@local.dev on startup
def _seed_relations() -> None:
    _pending_id = "00000000-0000-0000-0000-000000000001"
    _confirmed_id = "00000000-0000-0000-0000-000000000002"
    _ts = "2026-04-10T10:00:00Z"

    pending_received = RelationRecord(
        relation_id=_pending_id,
        owner_email=DEV_EMAIL,
        peer_email="alice@example.com",
        label="friend",
        status="pending",
        direction="received",
        created_at=_ts,
    )
    pending_sent_peer = RelationRecord(
        relation_id=_pending_id,
        owner_email="alice@example.com",
        peer_email=DEV_EMAIL,
        label="friend",
        status="pending",
        direction="sent",
        created_at=_ts,
    )
    confirmed_dev = RelationRecord(
        relation_id=_confirmed_id,
        owner_email=DEV_EMAIL,
        peer_email="bob@example.com",
        label="colleague",
        status="confirmed",
        direction="received",
        created_at=_ts,
    )
    confirmed_peer = RelationRecord(
        relation_id=_confirmed_id,
        owner_email="bob@example.com",
        peer_email=DEV_EMAIL,
        label="colleague",
        status="confirmed",
        direction="sent",
        created_at=_ts,
    )
    for r in (pending_received, pending_sent_peer, confirmed_dev, confirmed_peer):
        _relations_store[(r.owner_email, r.relation_id)] = r


_seed_relations()

_SESSION_SECRET = os.environ["SESSION_SECRET"]
_SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "900"))


def _now_utc() -> int:
    return int(datetime.now(UTC).timestamp())


def _require_session(request: Request) -> SessionClaims:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise VerificationError("Missing or invalid Authorization header")
    token = auth.removeprefix("Bearer ")
    return verify_session_token(token, _SESSION_SECRET, _now_utc())


def _get_profile(user_sub: str) -> Profile:
    return _profile_store.get(user_sub, Profile(user_sub=user_sub, entries=()))


def _list_relations(owner_email: str) -> tuple[RelationRecord, ...]:
    records = [r for (email, _), r in _relations_store.items() if email == owner_email]
    return tuple(sorted(records, key=lambda r: r.created_at))


def _count_pending_received(owner_email: str) -> int:
    return sum(
        1
        for r in _relations_store.values()
        if r.owner_email == owner_email and r.status == "pending" and r.direction == "received"
    )


@app.post("/auth/session")
async def auth_session() -> JSONResponse:
    now_utc = _now_utc()
    claims = SessionClaims(sub=DEV_SUB, email=DEV_EMAIL, exp=0)
    token = sign_session_token(claims, _SESSION_SECRET, now_utc, _SESSION_TTL_SECONDS)
    return JSONResponse({"session_token": token})


@app.get("/")
async def hello(claims: Annotated[SessionClaims, Depends(_require_session)]) -> JSONResponse:
    count = _count_pending_received(claims.email)
    return JSONResponse({"message": "hello from chai-s-romashkoi", "pending_relations_count": count})


@app.get("/profile")
async def get_profile(claims: Annotated[SessionClaims, Depends(_require_session)]) -> JSONResponse:
    profile = _get_profile(claims.sub)
    return JSONResponse({"entries": [asdict(e) for e in profile.entries]})


@app.put("/profile")
async def put_profile(
    request: Request,
    claims: Annotated[SessionClaims, Depends(_require_session)],
) -> JSONResponse:
    try:
        body: dict[str, Any] = await request.json()
        raw_entries: list[dict[str, str]] = body["entries"]
    except (KeyError, ValueError):
        return JSONResponse({"error": "invalid body"}, status_code=400)

    new_entries = tuple(
        normalise_entry(
            ProfileEntry(
                entry_id=str(e["entry_id"]),
                tag=str(e["tag"]),
                text=str(e["text"]),
                updated_at=str(e["updated_at"]),
            )
        )
        for e in raw_entries
    )
    new_profile = Profile(user_sub=claims.sub, entries=new_entries)
    old_profile = _get_profile(claims.sub)
    patch = compute_patch(old_profile, new_profile)
    updated = apply_patch(old_profile, patch)
    _profile_store[claims.sub] = updated
    return JSONResponse({"entries": [asdict(e) for e in updated.entries]})


@app.get("/profile/tags")
async def get_profile_tags(claims: Annotated[SessionClaims, Depends(_require_session)]) -> JSONResponse:
    profile = _get_profile(claims.sub)
    tags = sorted(known_tags(profile) | set(STANDARD_TAGS))
    return JSONResponse({"tags": tags})


@app.get("/relations")
async def get_relations(claims: Annotated[SessionClaims, Depends(_require_session)]) -> JSONResponse:
    records = _list_relations(claims.email)
    return JSONResponse({"relations": [asdict(r) for r in records]})


@app.post("/relations")
async def post_relations(
    request: Request,
    claims: Annotated[SessionClaims, Depends(_require_session)],
) -> JSONResponse:
    try:
        body: dict[str, Any] = await request.json()
        recipient_email = str(body["recipient_email"])
        label = normalise_label(str(body["label"]))
    except (KeyError, ValueError):
        return JSONResponse({"error": "invalid body"}, status_code=400)

    relation_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        sender_copy, recipient_copy = build_send_records(claims.email, recipient_email, label, relation_id, created_at)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    _relations_store[(sender_copy.owner_email, sender_copy.relation_id)] = sender_copy
    _relations_store[(recipient_copy.owner_email, recipient_copy.relation_id)] = recipient_copy
    return JSONResponse(asdict(sender_copy), status_code=201)


@app.post("/relations/{relation_id}/confirm")
async def confirm_relation(
    relation_id: str,
    claims: Annotated[SessionClaims, Depends(_require_session)],
) -> JSONResponse:
    key = (claims.email, relation_id)
    confirmer_record = _relations_store.get(key)
    if confirmer_record is None or confirmer_record.direction != "received" or confirmer_record.status != "pending":
        return JSONResponse({"error": "relation not found or cannot be confirmed"}, status_code=409)

    peer_key = (confirmer_record.peer_email, relation_id)
    peer_record = _relations_store.get(peer_key)
    if peer_record is None:
        return JSONResponse({"error": "peer relation not found"}, status_code=409)

    from relations.domain import build_confirmed_records  # noqa: PLC0415

    confirmed_sent, confirmed_received = build_confirmed_records(peer_record, confirmer_record)
    _relations_store[(confirmed_sent.owner_email, confirmed_sent.relation_id)] = confirmed_sent
    _relations_store[(confirmed_received.owner_email, confirmed_received.relation_id)] = confirmed_received
    return JSONResponse(asdict(confirmed_received))


@app.delete("/relations/{relation_id}")
async def delete_relation(
    relation_id: str,
    claims: Annotated[SessionClaims, Depends(_require_session)],
) -> Response:
    key = (claims.email, relation_id)
    owner_record = _relations_store.get(key)
    if owner_record is None:
        return JSONResponse({"error": "relation not found"}, status_code=409)

    peer_key = (owner_record.peer_email, relation_id)
    _relations_store.pop(key, None)
    _relations_store.pop(peer_key, None)
    return Response(status_code=204)


@app.post("/test/seed-relation")
async def seed_relation(request: Request) -> JSONResponse:
    body: dict[str, Any] = await request.json()
    peer_email = str(body["peer_email"])
    label = normalise_label(str(body["label"]))
    relation_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    received = RelationRecord(
        relation_id=relation_id,
        owner_email=DEV_EMAIL,
        peer_email=peer_email,
        label=label,
        status="pending",
        direction="received",
        created_at=created_at,
    )
    sent = RelationRecord(
        relation_id=relation_id,
        owner_email=peer_email,
        peer_email=DEV_EMAIL,
        label=label,
        status="pending",
        direction="sent",
        created_at=created_at,
    )
    _relations_store[(received.owner_email, received.relation_id)] = received
    _relations_store[(sent.owner_email, sent.relation_id)] = sent
    return JSONResponse({"relation_id": relation_id}, status_code=201)


@app.get("/relations/labels")
async def get_relation_labels(claims: Annotated[SessionClaims, Depends(_require_session)]) -> JSONResponse:
    records = _list_relations(claims.email)
    labels = sorted(known_labels(records))
    return JSONResponse({"labels": labels})


@app.get("/log")
async def get_log(request: Request, claims: Annotated[SessionClaims, Depends(_require_session)]) -> JSONResponse:
    week_start = request.query_params.get("week_start", "")
    week_end = request.query_params.get("week_end", "")
    entries = [
        e
        for (email, _), e in _log_store.items()
        if email == claims.email
        and (not week_start or e.logged_at >= week_start)
        and (not week_end or e.logged_at < week_end)
    ]
    entries_sorted = sorted(entries, key=lambda e: e.logged_at)
    return JSONResponse({"entries": [to_response_dict(e) for e in entries_sorted]})


@app.post("/log")
async def post_log(request: Request, claims: Annotated[SessionClaims, Depends(_require_session)]) -> JSONResponse:
    try:
        body: dict[str, Any] = await request.json()
        text = str(body["text"])
    except (KeyError, ValueError):
        return JSONResponse({"error": "invalid body"}, status_code=400)
    entry_id = str(uuid.uuid4())
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = make_entry(entry_id, claims.email, text, now)
    _log_store[(claims.email, entry_id)] = entry
    return JSONResponse(to_response_dict(entry), status_code=201)


@app.put("/log/{entry_id}")
async def put_log(
    entry_id: str, request: Request, claims: Annotated[SessionClaims, Depends(_require_session)]
) -> JSONResponse:
    key = (claims.email, entry_id)
    entry = _log_store.get(key)
    if entry is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        body: dict[str, Any] = await request.json()
        text = str(body["text"])
    except (KeyError, ValueError):
        return JSONResponse({"error": "invalid body"}, status_code=400)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    patch = LogEntryPatch(raw_text=text, updated_at=now)
    updated = apply_patch(entry, patch)
    _log_store[key] = updated
    return JSONResponse(to_response_dict(updated))


@app.delete("/log/{entry_id}")
async def delete_log(entry_id: str, claims: Annotated[SessionClaims, Depends(_require_session)]) -> Response:
    key = (claims.email, entry_id)
    if key not in _log_store:
        return JSONResponse({"error": "not found"}, status_code=404)
    del _log_store[key]
    return Response(status_code=204)


@app.post("/test/clear-log")
async def clear_log() -> Response:
    _log_store.clear()
    return Response(status_code=204)


@app.post("/test/seed-log-entry")
async def seed_log_entry(request: Request) -> JSONResponse:
    body: dict[str, Any] = await request.json()
    entry_id = str(uuid.uuid4())
    logged_at = str(body.get("logged_at", datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")))
    text = str(body.get("text", "seeded entry"))
    entry = make_entry(entry_id, DEV_EMAIL, text, logged_at)
    _log_store[(DEV_EMAIL, entry_id)] = entry
    return JSONResponse(to_response_dict(entry), status_code=201)


if __name__ == "__main__":
    uvicorn.run("dev.server:app", host="0.0.0.0", port=8000, reload=True)
