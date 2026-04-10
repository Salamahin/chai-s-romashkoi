from __future__ import annotations

import json
import profile.handler as profile_handler
from typing import cast

import app.handler as app_handler
import auth_handler
from session_guard import CORS_HEADERS


def _get_method(event: dict[str, object]) -> str:
    request_context = cast(dict[str, object], event.get("requestContext") or {})
    http = cast(dict[str, object], request_context.get("http") or {})
    method = http.get("method")
    if method:
        return str(method)
    return str(event.get("httpMethod", "GET"))


def handler(event: dict[str, object], context: object) -> dict[str, object]:
    method = _get_method(event)
    raw_path = str(event.get("rawPath") or event.get("path") or "/")

    if method == "POST" and raw_path == "/auth/session":
        return auth_handler.handler(event, context)

    if method == "GET" and raw_path == "/":
        return app_handler.handler(event, context)

    if raw_path in ("/profile", "/profile/tags"):
        return profile_handler.handler(event, context)

    return {
        "statusCode": 404,
        "headers": CORS_HEADERS,
        "body": json.dumps({"error": "not found"}),
    }
