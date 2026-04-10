from __future__ import annotations

from auth import SessionClaims, VerificationError, verify_session_token

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "content-type,authorization",
}


def require_session(
    headers: dict[str, str],
    secret: str,
    now_utc: int,
) -> SessionClaims:
    auth_header = next(
        (v for k, v in headers.items() if k.lower() == "authorization"),
        None,
    )
    if auth_header is None or not auth_header.startswith("Bearer "):
        raise VerificationError("Missing or invalid Authorization header")
    token = auth_header.removeprefix("Bearer ")
    return verify_session_token(token, secret, now_utc)
