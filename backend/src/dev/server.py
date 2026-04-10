"""FastAPI dev server for local development."""

from __future__ import annotations

import os
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated, Any

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

# Ensure src/ is first on sys.path so local packages (e.g. `profile`) shadow stdlib modules of the same name.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from profile.domain import Profile, ProfileEntry, apply_patch, compute_patch, normalise_entry  # noqa: E402
from profile.tags import STANDARD_TAGS, known_tags  # noqa: E402

from app.handler import make_hello_response  # noqa: E402
from auth import SessionClaims, VerificationError, sign_session_token, verify_session_token  # noqa: E402

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)

# In-memory store: user_sub -> Profile
_profile_store: dict[str, Profile] = {}

DEV_SUB = "dev"

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


@app.post("/auth/session")
async def auth_session() -> JSONResponse:
    now_utc = _now_utc()
    claims = SessionClaims(sub=DEV_SUB, email="dev@local.dev", exp=0)
    token = sign_session_token(claims, _SESSION_SECRET, now_utc, _SESSION_TTL_SECONDS)
    return JSONResponse({"session_token": token})


@app.get("/")
async def hello(claims: Annotated[SessionClaims, Depends(_require_session)]) -> JSONResponse:
    return JSONResponse(asdict(make_hello_response()))


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


if __name__ == "__main__":
    uvicorn.run("dev.server:app", host="0.0.0.0", port=8000, reload=True)
