import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import cast

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


@dataclass(frozen=True)
class HelloResponse:
    message: str


def make_hello_response() -> HelloResponse:
    return HelloResponse(message="hello from chai-s-romashkoi")


def handler(event: dict[str, object], context: object) -> dict[str, object]:
    secret = os.environ["SESSION_SECRET"]
    now_utc = int(datetime.now(UTC).timestamp())
    raw_headers = cast(dict[str, str], event.get("headers") or {})
    try:
        require_session(raw_headers, secret, now_utc)
    except VerificationError as e:
        return {"statusCode": 401, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}
    response = make_hello_response()
    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps(asdict(response))}
