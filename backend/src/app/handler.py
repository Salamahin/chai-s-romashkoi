import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import cast

from auth import VerificationError
from session_guard import CORS_HEADERS, require_session


@dataclass(frozen=True)
class HelloResponse:
    message: str


def make_hello_response() -> HelloResponse:
    return HelloResponse(message="hello from chai-s-romashkoi")


def handler(event: dict[str, object], context: object) -> dict[str, object]:
    request_context = cast(dict[str, object], event.get("requestContext") or {})
    http_context = cast(dict[str, object], request_context.get("http") or {})
    method = str(http_context.get("method", ""))
    raw_path = str(event.get("rawPath", ""))

    if method == "GET" and raw_path == "/":
        secret = os.environ["SESSION_SECRET"]
        now_utc = int(datetime.now(UTC).timestamp())
        raw_headers = cast(dict[str, str], event.get("headers") or {})
        try:
            require_session(raw_headers, secret, now_utc)
        except VerificationError as e:
            return {"statusCode": 401, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}
        response = make_hello_response()
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps(asdict(response))}

    return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": "not found"})}
