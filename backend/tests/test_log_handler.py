from __future__ import annotations

import json
import os
import time
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from conftest import TABLE_NAME

from auth import SessionClaims, sign_session_token

OWNER_EMAIL = "alice@example.com"
SESSION_SECRET = "test-secret"


@pytest.fixture
def patched_handler(table: Any) -> Generator[tuple[Any, Any], None, None]:
    from log.repository import LogRepository

    repo = LogRepository(table)
    with patch.dict(os.environ, {"SESSION_SECRET": SESSION_SECRET, "PROFILES_TABLE_NAME": TABLE_NAME}):
        with patch("log.handler._repo", repo):
            with patch("log.handler._SESSION_SECRET", SESSION_SECRET):
                import log.handler as log_handler

                yield log_handler, repo


def _make_token() -> str:
    claims = SessionClaims(sub="dev", email=OWNER_EMAIL, exp=0)
    now = int(time.time())
    return sign_session_token(claims, SESSION_SECRET, now, 900)


def _make_event(
    method: str,
    path: str,
    body: object = None,
    query_params: dict[str, str] | None = None,
    token: str | None = None,
) -> dict[str, object]:
    return {
        "requestContext": {"http": {"method": method}},
        "rawPath": path,
        "headers": {"authorization": f"Bearer {token or _make_token()}"},
        "body": json.dumps(body) if body is not None else None,
        "queryStringParameters": query_params or {},
    }


def test_post_log_creates_entry(patched_handler: tuple[Any, Any]) -> None:
    log_handler, _ = patched_handler
    response = log_handler.handler(_make_event("POST", "/log", body={"text": "My first entry"}), None)
    assert response["statusCode"] == 201
    body = json.loads(str(response["body"]))
    assert body["raw_text"] == "My first entry"
    assert "entry_id" in body
    assert "logged_at" in body
    assert "updated_at" in body


def test_get_log_returns_entries(patched_handler: tuple[Any, Any]) -> None:
    log_handler, repo = patched_handler
    from log.domain import make_entry

    entry = make_entry("e1", OWNER_EMAIL, "Hello", "2026-04-11T10:00:00Z")
    repo.put(entry)

    response = log_handler.handler(
        _make_event(
            "GET",
            "/log",
            query_params={"week_start": "2026-04-11T00:00:00Z", "week_end": "2026-04-12T00:00:00Z"},
        ),
        None,
    )
    assert response["statusCode"] == 200
    body = json.loads(str(response["body"]))
    assert len(body["entries"]) == 1
    assert body["entries"][0]["entry_id"] == "e1"


def test_put_log_updates_entry(patched_handler: tuple[Any, Any]) -> None:
    log_handler, repo = patched_handler
    from log.domain import make_entry

    repo.put(make_entry("e1", OWNER_EMAIL, "Original", "2026-04-11T10:00:00Z"))

    response = log_handler.handler(_make_event("PUT", "/log/e1", body={"text": "Updated text"}), None)
    assert response["statusCode"] == 200
    body = json.loads(str(response["body"]))
    assert body["raw_text"] == "Updated text"
    assert body["entry_id"] == "e1"


def test_delete_log_removes_entry(patched_handler: tuple[Any, Any]) -> None:
    log_handler, repo = patched_handler
    from log.domain import make_entry

    repo.put(make_entry("e1", OWNER_EMAIL, "Hello", "2026-04-11T10:00:00Z"))

    response = log_handler.handler(_make_event("DELETE", "/log/e1"), None)
    assert response["statusCode"] == 204


def test_get_log_unauthorized(patched_handler: tuple[Any, Any]) -> None:
    log_handler, _ = patched_handler
    response = log_handler.handler(_make_event("GET", "/log", token="invalid-token"), None)
    assert response["statusCode"] == 401


def test_post_log_unauthorized(patched_handler: tuple[Any, Any]) -> None:
    log_handler, _ = patched_handler
    response = log_handler.handler(_make_event("POST", "/log", body={"text": "hi"}, token="bad-token"), None)
    assert response["statusCode"] == 401


def test_post_log_missing_text_returns_400(patched_handler: tuple[Any, Any]) -> None:
    log_handler, _ = patched_handler
    response = log_handler.handler(_make_event("POST", "/log", body={"wrong_field": "value"}), None)
    assert response["statusCode"] == 400


def test_post_log_invalid_json_returns_400(patched_handler: tuple[Any, Any]) -> None:
    log_handler, _ = patched_handler
    event: dict[str, object] = {
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/log",
        "headers": {"authorization": f"Bearer {_make_token()}"},
        "body": "not-json{{{{",
        "queryStringParameters": {},
    }
    response = log_handler.handler(event, None)
    assert response["statusCode"] == 400


def test_put_log_missing_text_returns_400(patched_handler: tuple[Any, Any]) -> None:
    log_handler, repo = patched_handler
    from log.domain import make_entry

    repo.put(make_entry("e1", OWNER_EMAIL, "Original", "2026-04-11T10:00:00Z"))

    response = log_handler.handler(_make_event("PUT", "/log/e1", body={"no_text_field": True}), None)
    assert response["statusCode"] == 400


def test_put_log_not_found_returns_404(patched_handler: tuple[Any, Any]) -> None:
    log_handler, _ = patched_handler
    response = log_handler.handler(_make_event("PUT", "/log/nonexistent-id", body={"text": "new text"}), None)
    assert response["statusCode"] == 404


def test_delete_log_not_found_returns_404(patched_handler: tuple[Any, Any]) -> None:
    log_handler, _ = patched_handler
    response = log_handler.handler(_make_event("DELETE", "/log/nonexistent-id"), None)
    assert response["statusCode"] == 404


def test_unknown_route_returns_404(patched_handler: tuple[Any, Any]) -> None:
    log_handler, _ = patched_handler
    response = log_handler.handler(_make_event("GET", "/log/some/nested/path"), None)
    assert response["statusCode"] == 404


def test_get_log_only_returns_own_entries(patched_handler: tuple[Any, Any]) -> None:
    log_handler, repo = patched_handler
    from log.domain import make_entry

    repo.put(make_entry("other-e1", "other@example.com", "Private", "2026-04-11T10:00:00Z"))
    repo.put(make_entry("own-e1", OWNER_EMAIL, "Mine", "2026-04-11T11:00:00Z"))

    response = log_handler.handler(
        _make_event(
            "GET",
            "/log",
            query_params={"week_start": "2026-04-11T00:00:00Z", "week_end": "2026-04-12T00:00:00Z"},
        ),
        None,
    )
    assert response["statusCode"] == 200
    body = json.loads(str(response["body"]))
    assert len(body["entries"]) == 1
    assert body["entries"][0]["entry_id"] == "own-e1"


@pytest.mark.parametrize(
    "method,body",
    [
        ("PUT", {"text": "hacked"}),
        ("DELETE", None),
    ],
)
def test_log_cannot_mutate_other_users_entry(
    patched_handler: tuple[Any, Any], method: str, body: dict[str, Any] | None
) -> None:
    from log.domain import make_entry

    log_handler, repo = patched_handler
    repo.put(make_entry("other-e1", "other@example.com", "Private", "2026-04-11T10:00:00Z"))

    response = log_handler.handler(_make_event(method, "/log/other-e1", body=body), None)
    assert response["statusCode"] == 404
