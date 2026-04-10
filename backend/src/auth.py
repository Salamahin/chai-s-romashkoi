from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import cast

import cachetools
import jwt
from jwt import PyJWKSet


class VerificationError(Exception):
    pass


JwksPayload = dict[str, object]


@cachetools.cached(cache=cachetools.TTLCache(maxsize=1, ttl=6 * 3600))
def fetch_jwks(url: str) -> JwksPayload:
    with urllib.request.urlopen(url) as resp:  # noqa: S310
        return cast(JwksPayload, json.loads(resp.read().decode()))


@dataclass(frozen=True)
class SessionClaims:
    sub: str
    email: str
    exp: int


def sign_session_token(
    claims: SessionClaims,
    secret: str,
    now_utc: int,
    ttl_seconds: int,
) -> str:
    payload = {
        "sub": claims.sub,
        "email": claims.email,
        "iat": now_utc,
        "exp": now_utc + ttl_seconds,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_session_token(
    raw_token: str,
    secret: str,
    now_utc: int,
) -> SessionClaims:
    try:
        payload = jwt.decode(
            raw_token,
            secret,
            algorithms=["HS256"],
            options={"verify_exp": False},
        )
        exp = int(payload["exp"])
        if exp <= now_utc:
            raise VerificationError("Session expired")
        return SessionClaims(
            sub=str(payload["sub"]),
            email=str(payload["email"]),
            exp=exp,
        )
    except VerificationError:
        raise
    except Exception as e:
        raise VerificationError(str(e)) from e


VALID_ISSUERS = frozenset(["accounts.google.com", "https://accounts.google.com"])


@dataclass(frozen=True)
class GoogleClaims:
    sub: str
    email: str


def verify_google_id_token(
    raw_token: str,
    jwks: JwksPayload,
    expected_audience: str,
    now_utc: int,
) -> GoogleClaims:
    try:
        jwks_set = PyJWKSet.from_dict(dict(jwks))
        header = jwt.get_unverified_header(raw_token)
        kid = str(header.get("kid", ""))
        signing_key = jwks_set[kid]

        payload = jwt.decode(
            raw_token,
            signing_key,
            algorithms=["RS256"],
            audience=expected_audience,
            options={"verify_exp": False},
        )
        exp = int(payload["exp"])
        if exp <= now_utc:
            raise VerificationError("Token expired")
        iss = str(payload.get("iss", ""))
        if iss not in VALID_ISSUERS:
            raise VerificationError(f"Invalid issuer: {iss}")
        return GoogleClaims(
            sub=str(payload["sub"]),
            email=str(payload["email"]),
        )
    except VerificationError:
        raise
    except Exception as e:
        raise VerificationError(str(e)) from e
