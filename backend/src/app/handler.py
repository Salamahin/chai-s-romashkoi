import json
import os
from datetime import UTC, datetime
from typing import cast

import boto3

from auth import VerificationError
from relations.repository import RelationRepository
from session_guard import CORS_HEADERS, require_session

_SECRET = os.environ["SESSION_SECRET"]
_PROFILES_TABLE_NAME = os.environ["PROFILES_TABLE_NAME"]

_dynamodb = boto3.resource("dynamodb")
_relations_table = _dynamodb.Table(_PROFILES_TABLE_NAME)
_relations_repo = RelationRepository(_relations_table)


def handler(event: dict[str, object], context: object) -> dict[str, object]:
    request_context = cast(dict[str, object], event.get("requestContext") or {})
    http_context = cast(dict[str, object], request_context.get("http") or {})
    method = str(http_context.get("method", ""))
    raw_path = str(event.get("rawPath", ""))

    if method == "GET" and raw_path == "/":
        now_utc = int(datetime.now(UTC).timestamp())
        raw_headers = cast(dict[str, str], event.get("headers") or {})
        try:
            claims = require_session(raw_headers, _SECRET, now_utc)
        except VerificationError as e:
            return {"statusCode": 401, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}
        count = _relations_repo.count_pending_received(claims.email)
        body = {"message": "hello from chai-s-romashkoi", "pending_relations_count": count}
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps(body)}

    return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": "not found"})}
