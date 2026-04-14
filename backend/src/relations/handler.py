from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import cast

import boto3

from auth import VerificationError
from relations.domain import build_send_records, normalise_label
from relations.label_suggestions import known_labels
from relations.repository import RelationRepository
from session_guard import CORS_HEADERS, get_method, require_session

_SESSION_SECRET = os.environ["SESSION_SECRET"]
_PROFILES_TABLE_NAME = os.environ["PROFILES_TABLE_NAME"]

_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(_PROFILES_TABLE_NAME)
_repo = RelationRepository(_table)


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

    if method == "GET" and raw_path == "/relations":
        records = _repo.list_for_owner(email)
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"relations": [asdict(r) for r in records]}),
        }

    if method == "POST" and raw_path == "/relations":
        try:
            body = json.loads(cast(str, event.get("body") or "{}"))
            recipient_email = str(body["recipient_email"])
            label = normalise_label(str(body["label"]))
        except (KeyError, ValueError, json.JSONDecodeError):
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "invalid body"})}

        relation_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            sender_copy, recipient_copy = build_send_records(email, recipient_email, label, relation_id, created_at)
        except ValueError as e:
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}

        try:
            _repo.put_pair(sender_copy, recipient_copy)
        except ValueError as e:
            return {"statusCode": 409, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}
        return {"statusCode": 201, "headers": CORS_HEADERS, "body": json.dumps(asdict(sender_copy))}

    if method == "GET" and raw_path == "/relations/labels":
        records = _repo.list_for_owner(email)
        labels = sorted(known_labels(records))
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"labels": labels})}

    # POST /relations/{id}/confirm
    if method == "POST" and raw_path.startswith("/relations/") and raw_path.endswith("/confirm"):
        relation_id = raw_path.removeprefix("/relations/").removesuffix("/confirm")
        try:
            confirmed = _repo.confirm_pair(email, relation_id)
        except ValueError as e:
            return {"statusCode": 409, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps(asdict(confirmed))}

    # DELETE /relations/{id}
    if method == "DELETE" and raw_path.startswith("/relations/"):
        relation_id = raw_path.removeprefix("/relations/")
        if "/" not in relation_id and relation_id:
            try:
                _repo.delete_pair(email, relation_id)
            except ValueError as e:
                return {"statusCode": 409, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}
            return {"statusCode": 204, "headers": CORS_HEADERS, "body": ""}

    return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": "not found"})}
