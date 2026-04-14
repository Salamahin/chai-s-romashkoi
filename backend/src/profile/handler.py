from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from profile.domain import Profile, ProfileEntry, apply_patch, compute_patch, normalise_entry
from profile.repository import ProfileRepository
from profile.tags import STANDARD_TAGS, known_tags
from typing import cast

import boto3

from auth import VerificationError
from session_guard import CORS_HEADERS, get_method, require_session

_SESSION_SECRET = os.environ["SESSION_SECRET"]
_PROFILES_TABLE_NAME = os.environ["PROFILES_TABLE_NAME"]

_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(_PROFILES_TABLE_NAME)
_repo = ProfileRepository(_table)


def handler(event: dict[str, object], context: object) -> dict[str, object]:
    method = get_method(event)
    raw_path = str(event.get("rawPath") or event.get("path") or "/")

    now_utc = int(datetime.now(UTC).timestamp())
    raw_headers = cast(dict[str, str], event.get("headers") or {})

    try:
        claims = require_session(raw_headers, _SESSION_SECRET, now_utc)
    except VerificationError as e:
        return {"statusCode": 401, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}

    user_sub = claims.sub

    if method == "GET" and raw_path == "/profile":
        profile = _repo.get(user_sub)
        entries = [asdict(e) for e in profile.entries]
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"entries": entries})}

    if method == "PUT" and raw_path == "/profile":
        try:
            body = json.loads(cast(str, event.get("body") or "{}"))
            raw_entries: list[dict[str, str]] = body["entries"]
        except (KeyError, ValueError, json.JSONDecodeError):
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "invalid body"})}

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
        new_profile = Profile(user_sub=user_sub, entries=new_entries)
        old_profile = _repo.get(user_sub)
        patch = compute_patch(old_profile, new_profile)
        _repo.apply(user_sub, patch)
        updated = apply_patch(old_profile, patch)
        entries = [asdict(e) for e in updated.entries]
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"entries": entries})}

    if method == "GET" and raw_path == "/profile/tags":
        profile = _repo.get(user_sub)
        tags = sorted(known_tags(profile) | set(STANDARD_TAGS))
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"tags": tags})}

    return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": "not found"})}
