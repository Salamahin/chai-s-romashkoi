"""FastAPI dev server for local development."""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import UTC, datetime

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

from app.handler import make_hello_response  # noqa: E402
from auth import SessionClaims, VerificationError, sign_session_token, verify_session_token  # noqa: E402

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)


def _now_utc() -> int:
    return int(datetime.now(UTC).timestamp())


def _extract_bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise VerificationError("Missing or invalid Authorization header")
    return auth.removeprefix("Bearer ")


@app.post("/auth/session")
async def auth_session() -> JSONResponse:
    session_secret = os.environ["SESSION_SECRET"]
    session_ttl_seconds = int(os.environ.get("SESSION_TTL_SECONDS", "900"))

    now_utc = _now_utc()
    claims = SessionClaims(sub="dev", email="dev@local.dev", exp=0)
    token = sign_session_token(claims, session_secret, now_utc, session_ttl_seconds)
    return JSONResponse({"session_token": token})


@app.get("/")
async def hello(request: Request) -> JSONResponse:
    session_secret = os.environ["SESSION_SECRET"]
    now_utc = _now_utc()
    try:
        token = _extract_bearer(request)
        verify_session_token(token, session_secret, now_utc)
    except VerificationError as e:
        return JSONResponse({"error": str(e)}, status_code=401)
    return JSONResponse(asdict(make_hello_response()))


if __name__ == "__main__":
    uvicorn.run("dev.server:app", host="0.0.0.0", port=8000, reload=True)
