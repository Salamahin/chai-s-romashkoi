from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import cast

from auth import SessionClaims, VerificationError, fetch_jwks, sign_session_token, verify_google_id_token

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "content-type,authorization",
}


def handler(event: dict[str, object], context: object) -> dict[str, object]:
    google_client_id = os.environ["GOOGLE_CLIENT_ID"]
    session_secret = os.environ["SESSION_SECRET"]
    jwks_url = os.environ.get("JWKS_URL", "https://www.googleapis.com/oauth2/v3/certs")
    session_ttl_seconds = int(os.environ.get("SESSION_TTL_SECONDS", "900"))

    try:
        body = json.loads(cast(str, event.get("body") or ""))
        credential = str(body["credential"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "missing credential"})}

    now_utc = int(datetime.now(UTC).timestamp())
    try:
        jwks = fetch_jwks(jwks_url)
        google_claims = verify_google_id_token(credential, jwks, google_client_id, now_utc)
    except VerificationError as e:
        return {"statusCode": 401, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}

    session_claims = SessionClaims(sub=google_claims.sub, email=google_claims.email, exp=0)
    session_token = sign_session_token(session_claims, session_secret, now_utc, session_ttl_seconds)
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({"session_token": session_token}),
    }
