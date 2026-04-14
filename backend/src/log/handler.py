from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from typing import cast

import boto3

from auth import VerificationError
from log.domain import LogEntryPatch, make_entry, to_response_dict
from log.repository import LogRepository
from session_guard import CORS_HEADERS, get_method, require_session

_SESSION_SECRET = os.environ["SESSION_SECRET"]
_PROFILES_TABLE_NAME = os.environ["PROFILES_TABLE_NAME"]

_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(_PROFILES_TABLE_NAME)
_repo = LogRepository(_table)


def handler(event: dict[str, object], context: object) -> dict[str, object]:
    method = get_method(event)
    raw_path = str(event.get("rawPath") or event.get("path") or "/")
    now_utc = int(datetime.now(UTC).timestamp())
    raw_headers = cast(dict[str, str], event.get("headers") or {})

    try:
        claims = require_session(raw_headers, _SESSION_SECRET, now_utc)
    except VerificationError as e:
        return {"statusCode": 401, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}

    email = claims.email

    # GET /log?week_start=<ISO>&week_end=<ISO>
    if method == "GET" and raw_path == "/log":
        params = cast(dict[str, str], event.get("queryStringParameters") or {})
        week_start = params.get("week_start", "")
        week_end = params.get("week_end", "")
        entries = _repo.list_window(email, week_start, week_end)
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"entries": [to_response_dict(e) for e in entries]}),
        }

    # POST /log
    if method == "POST" and raw_path == "/log":
        try:
            body = json.loads(cast(str, event.get("body") or "{}"))
            text = str(body["text"])
        except (KeyError, ValueError, json.JSONDecodeError):
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "invalid body"})}
        entry_id = str(uuid.uuid4())
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = make_entry(entry_id, email, text, now)
        _repo.put(entry)
        return {"statusCode": 201, "headers": CORS_HEADERS, "body": json.dumps(to_response_dict(entry))}

    # PUT /log/{entry_id}
    if method == "PUT" and raw_path.startswith("/log/"):
        entry_id = raw_path.removeprefix("/log/")
        if "/" not in entry_id and entry_id:
            try:
                body = json.loads(cast(str, event.get("body") or "{}"))
                text = str(body["text"])
            except (KeyError, ValueError, json.JSONDecodeError):
                return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "invalid body"})}
            now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            patch = LogEntryPatch(raw_text=text, updated_at=now)
            try:
                updated = _repo.update_text(email, entry_id, patch)
            except ValueError as e:
                return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}
            return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps(to_response_dict(updated))}

    # DELETE /log/{entry_id}
    if method == "DELETE" and raw_path.startswith("/log/"):
        entry_id = raw_path.removeprefix("/log/")
        if "/" not in entry_id and entry_id:
            try:
                _repo.delete(email, entry_id)
            except ValueError as e:
                return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}
            return {"statusCode": 204, "headers": CORS_HEADERS, "body": ""}

    return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": "not found"})}
